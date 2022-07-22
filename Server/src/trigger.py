#!/usr/bin/python
import sys
import ctypes
from bs4 import BeautifulSoup as Soup
from zmq import *
import time
import argparse
import socket

class ConnectionError(Exception):
  pass

class DT5495:
   #constructor
  def __init__(self,argv):
    #parse arguments
    parser = argparse.ArgumentParser()
    parser.add_argument("-c", "--configurefile", type=str, help="Configuration file", required=True)
    parser.add_argument("-l", "--logfile", type=str, help="Log file", required=True)
    args = parser.parse_args()
    self.configure_file_path = args.configurefile
    self.log_file_path = args.logfile
    
    sys.stdout = open(self.log_file_path, 'w')	#print to log file
    
    #board communication parameters
    self.PubLib = ctypes.cdll.LoadLibrary('/usr/lib/libCAEN_PLU.so')
    self.led_cont = ctypes.c_uint16(0x1810)
    self.led_no = ctypes.c_uint32(0)
    self.handle = ctypes.c_int()
    self.readReg = ctypes.c_uint32()
    self.board_serial_number = "0023"
    self.board_ip_address = "192.168.0.90"
    #self.board_ip_address = "192.168.122.1"
    self.connection = None

    self.connectionDict = {
      'USB': 0,
      'ETHERNET': 1
    }

    #Control Registers
    self.enabled_ports_register = 0x1808  #write 8 bits
    self.control_port_register = 0x1809   #write 4 bits
    self.full_delay_register = 0x180C     #write 32 bits
    self.busy_flag_register = 0x1810      #write 1 bit 

    #Trigger Board Parameters
    self.busy_flag = 0

    #GDG parameters
    self.enabled_port_list=[] #numbered from 1 to 8
    self.delays=[]            #position is relative to enabled_port_list          
    self.gates=[]             #position is relative to enabled_port_list

    self.control_port = 0     #When 0, no control port chosen
    self.full_delay_time = 0  #Will be taken from the delay list, depending on the chosen port

    self.enabled_ports_value = 0   #value to be sent over the register (enabled_port_register)
    
    #zmq parameters
    self.context = None
    self.sub = None
    self.sub_url=[]
    self.status_port = None
    self.pub = None
    self.poller = None
    
    #Program parameters
    self.rsdictReverse = { #imported from H4DAQ/interface/Command.hpp
      'START': 0,
      'INIT': 1,
      'INITIALIZED': 2,
      'BEGINSPILL': 3,
      'CLEARED': 4,
      'WAITFORREADY': 5,
      'CLEARBUSY': 6,
      'WAITTRIG': 7,
      'READ': 8,
      'ENDSPILL': 9,
      'RECVBUFFER': 10,
      'SENTBUFFER': 11,
      'SPILLCOMPLETED': 12,
      'BYE': 13,
      'ERROR': 14
    }

    self.run_flag = False
    self.status = 'INIT'
  
  #destructor
  def __del__(self):
    #self.PubLib.CAEN_PLU_CloseDevice(self.handle)
    print("Connection to trigger board is CLOSED")

  #self functions
  def gdg_control(self):

    #Initialize the gdg
    error_code = self.PubLib.CAEN_PLU_InitGateAndDelayGenerators(self.handle)
    print("Initialize GDG error code: ", error_code)
    if error_code != 0:
      raise ConnectionError("Failed to Initialize GDG")

    #Loop over list of enabled ports
    for i in len(self.enabled_port_list):

      #get full value of enabled ports to write to the register (int)
      self.enabled_ports_value = self.enabled_ports_value + (2**self.enabled_port_list[i])

      #get control port delay
      if self.enabled_port_list[i] == self.control_port:
        self.full_delay_time = self.delays[i]

      #Set each GDG line
      error_code = self.PubLib.CAEN_PLU_SetGateAndDelayGenerator(
        self.handle, 
        int(self.enabled_port_list[i]), 
        1,
        int(self.gates[i]),
        int(self.delays[i]),
        1)
      print("Set GDG line error: ", error_code)
      if error_code != 0:
        raise ConnectionError("Failed to Set GDG Line for port: ", self.enabled_port_list[i])
    
    #Write to Register 0x1808 to give choice of enabled ports
    error_code = self.PubLib.CAEN_PLU_WriteReg(handle, self.enabled_ports_register, self.enabled_ports_value)
    print("Error Code writing to register: ", error_code)

    #Write to Register 0x1809 to give choice of control ports
    error_code = self.PubLib.CAEN_PLU_WriteReg(handle, self.control_port_register, self.control_port)
    print("Error Code writing to register: ", error_code)

    #Write to Register 0x180C to give full delay time
    error_code = self.PubLib.CAEN_PLU_WriteReg(handle, self.full_delay_register, self.full_delay_time)
    print("Error Code writing to register: ", error_code)

    #Send Control Port Information
    error_code = self.PubLib.CAEN_PLU_WriteReg(handle, self.full_delay_register, self.full_delay_time)

  def initialize_zmq_channels(self):
    self.context = Context()
    self.poller = Poller()
    self.sub = self.context.socket(SUB)
    
    gui_hostname = socket.gethostname()
    for url in self.sub_url:
      new_url = "tcp://"
      if gui_hostname in url:
        url = url.replace(gui_hostname,"localhost")
      new_url += url
      print(new_url)
      self.sub.connect(new_url)
    self.sub.setsockopt(SUBSCRIBE,b'')
    self.poller.register(self.sub,POLLIN)
    
    self.pub = self.context.socket(PUB)
    new_url = "tcp://*:" + self.status_port
    print("status: " + new_url)
    print("Url to publish app status: ", new_url)
    self.pub.bind(new_url)

  def led_change(self):
      error_write = self.PubLib.CAEN_PLU_WriteReg(self.handle, self.led_cont, self.led_no)
      error_read = self.PubLib.CAEN_PLU_ReadReg(self.handle, self.led_cont, ctypes.byref(self.readReg))

      if error_write != 0:
        raise ConnectionError("Failed to write on the register")
      if error_read != 0:
        raise ConnectionError("Failed to read from the register")
      if self.readReg.value != self.led_no.value:
        raise ConnectionError("Value read is different from value written")

      print ("Number written on the Register is: {}".format(bin(self.readReg.value))) 

  def parse_configure_file(self):
    try:
      print("Configure file path sent by AppControl: ",self.configure_file_path)
      with open(self.configure_file_path) as fp:
        soup = Soup(fp, "xml")
        self.parse_standard_params(soup)
    except:
      raise Exception("Parsing Configuration file FAILED")
  
  def parse_standard_params(self,soup):
    try:
      #Port tags
      port_list=[]
      for tag in soup.find_all("ListenPort"):
        port_list.append(tag.string)
      self.status_port = port_list[1]

      for tag in soup.find_all("ConnectTo"):
        self.sub_url.append(tag.string)
    
      #Hardware tags
      for tag in soup.find_all("LedControl"):
        hex_str = tag.string
        hex_int = int(hex_str,16)
        self.led_cont = ctypes.c_uint16(hex_int)
        print("Controller register: ",self.led_cont.value)
      for tag in soup.find_all("LedNo"):
        self.led_no = ctypes.c_uint32(int(tag.string)) 
      for tag in soup.find_all("SerialNo"):
        self.board_serial_number = tag.string
      for tag in soup.find_all("ConnectionType"):
        self.connection = tag.string
      for tag in soup.find_all("IPAddress"):
        self.board_ip_address = tag.string

      #GDG tags
      for tag in soup.find_all("EnablePort"):
        self.enabled_port_list.append(int(tag.string))
      for tag in soup.find_all("PortDelay"):
        self.delays.append(int(tag.string))
      for tag in soup.find_all("PortGate"):
        self.gates.append(int(tag.string))
      for tag in soup.find_all("ControlPort"):
        self.control_port = int(tag.string)

    except:
      raise Exception("Parsing Parameters FAILED")
      
  def proc_message(self, msg):
    if 'KILL_APP' in msg:
      print("Killing App requested")
      self.run_flag = False

    if 'READ' in msg:
      print("Reading Data")
      self.busy_flag = 1
      self.read_data()
    
  def read_date(self):
    print("Reading Data")
    error_code = self.PubLib.CAEN_PLU_WriteReg(handle, self.busy_flag_register, self.busy_flag)
    print("Error Code writing to register: ", error_code)

  #watching for messages to kill the application + send signal that app is running
  def polling(self):
    print("polling for messages/n")
    while self.run_flag:
      try:
        time.sleep(3)
        status_msg = "STATUS statuscode="+str(self.rsdictReverse[self.status])
        print("Sending status msg: ", status_msg)
        self.pub.send_string(status_msg)
        
        socks = dict(self.poller.poll(1))
        if socks.get(self.sub):
          message = self.sub.recv()
          message = message.decode("utf-8")
          self.proc_message(message)
        
        sys.stdout.flush()
        
      except:
        print("Error in the polling loop. Breaking...")
        self.run_flag = False
        sys.stdout.flush()
  
  #Fsm actions
  def initialize(self):
    print("Initialization Action Begins")

    #parse the parameters
    self.parse_configure_file()
    if (self.control_port != 0) and (self.control_port not in self.enabled_port_list):
      print("ERROR: The control port must be enabled")
      raise Exception("Control Port not enabled")

    #Initialize zmq
    self.initialize_zmq_channels()

    print("Connecton type: ",self.connectionDict[self.connection])
    print("Board serial: ",self.board_serial_number)
   
    #open connection with trigger board
    if self.connection == 'USB':
      error_code = self.PubLib.CAEN_PLU_OpenDevice(
        self.connectionDict[self.connection], 
        bytes(str(self.board_serial_number),'ascii'), 
        0, #VME link number, unimportant for USB or ETHERNET connection
        0, #VME conet node, unimportant for USB or ETHERNET connection
        ctypes.byref(self.handle)
       )
    elif self.connection == 'ETHERNET':
      error_code = self.PubLib.CAEN_PLU_OpenDevice(
        self.connectionDict[self.connection], 
        bytes(str(self.board_ip_address),'ascii'), 
        0, #VME link number, unimportant for USB or ETHERNET connection
        0, #VME conet node, unimportant for USB or ETHERNET connection
        ctypes.byref(self.handle)
       )
 
    print("Open Device Error Code: ", error_code)
    if error_code != 0:
      raise ConnectionError("Connection to the Logic Unit FAILED")
    
    self.run_flag = True
    self.status = 'INITIALIZED'
    print("Initialization Action End")
    
  ##MAIN##
def main(argv):
  print(argv)
  newBoard = DT5495(argv)
  try:
    newBoard.initialize()
    newBoard.gdg_control()
    newBoard.polling()
    newBoard.PubLib.CAEN_PLU_CloseDevice(newBoard.handle)
  except ConnectionError as error:
    newBoard.PubLib.CAEN_PLU_CloseDevice(newBoard.handle)
    raise error
    

if __name__=='__main__':
  main(sys.argv)
