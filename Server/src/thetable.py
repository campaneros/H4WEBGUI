from threading import Thread
import math
import sys
import argparse
import time
from bs4 import BeautifulSoup as Soup
from zmq import *
import socket
import serial
 
class TableContError(Exception):
  pass

### Table Controller ###
class TableController:
  def __init__(self):
    
    self.log_file = None

    #Table Controller Parameters
    self.delay_time = 0		#milliseconds
    self.table_display = None	#string
    self.drives = []		#2 elements

    #Table limits
    self.x_lower = -5.34
    self.x_upper = 404.50
    self.z_lower = 0.00
    self.z_upper = 338.00 #limit with the pipe in the way
        
    #flags
    self.run = False
    self.table_sim = False		
    
    #position data
    self.move_pos = [-math.inf, -math.inf]		#2 elements 
    self.actual_pos = [-math.inf, -math.inf]	#2 elements
    
    #serial data
    self.port_pub = 0		#long - for the visa i think    
    self.visa_in = None		#string
    self.serial_name = None
    
	
  def delay(self):
    time.sleep(self.delay_time/1000)	#delay is in ms
    return

  def get_position(self):
    try:
      return_pos = -(math.inf)
      #position feedback command
      message = self.visa_wr("PF\r") 
      parts = message.split(":")
      if parts[0] == "PF":
        return_pos = int(parts[1]) / 100
    except TableContError as error:
      raise error

    return return_pos
  
  def init_table(self):
    try:
      self.visa_in = serial.Serial(
        port = self.serial_name,  
        baudrate = 19200 
     )
      for index in 0, 1:
        self.select_drive(index)
        #initialize the drive
        message = self.visa_wr("DC2\r")
        self.actual_pos[index] = self.get_position()   
    except ValueError as error:
      raise error
    except serial.SerialException as error:
      raise error
    except TableContError as error:
      raise error
          
  def initialize_tab_cont(self):
    self.delay_time = 100
    self.drives = ["2","1"] #X=2, Z=1
    sys.stdout = open(self.log_file, 'w')    
    if not self.table_sim:
      self.init_table() 
      self.visa_in.close()

  def move_drive(self, drives_index, pos_index):
    try:
      self.select_drive(drives_index)
      #enables the drive
      message = self.visa_wr("MA\r")
      self.set_position(self.move_pos[pos_index])
    except TableContError as error:
      raise error
    print("exiting move_drive")

  def move_to_pos(self):
    print("Moving table to: ",self.move_pos)
    try:
      if (self.move_pos[0] > self.x_upper) or (self.move_pos[0] < self.x_lower) or (self.move_pos[1] > self.z_upper) or (self.move_pos[1] < self.z_lower):
        raise TableContError("Specified location is out of bounds.")
        return
      self.init_table()
      for index in 0, 1:
        self.move_drive(index, index)

      last_pos = [-9999,-9999]    
      while True:
        for index in 0, 1:
          self.select_drive(index)
          self.actual_pos[index] = self.get_position()
        if self.run == False or last_pos == self.actual_pos:
          break
        print("exited while loop")
        last_pos = self.actual_pos[:]

      #close the visa
      self.visa_in.close()

      if self.move_pos != self.actual_pos:
        raise TableContError("Table did not move to specified location.")

      if self.run == False:         
        for index in 0, 1:
          self.select_drive(index)
          #stops the  drive
          message = self.visa_wr("AR\r")
          self.actual_pos[index] = self.get_position()
            
        raise TableContError("Operation cancelled by user.")
          
    except TableContError as error:
      raise error

  def select_drive(self, drives_index):
    try:
      #initialize communication with specified drive
      message = self.visa_wr("AD" + self.drives[drives_index] + "\r") 
    except TableContError as error:
      raise error
    return

  def set_position(self, pos):
    try:
      pos_string = str(int(pos*100))
      message = self.visa_wr("MP" + pos_string + "\r")
    except TableContError as error:
      raise error
    
  def visa_wr(self, command):
    try:
      self.visa_in.write(command.encode('utf-8'))
      print("Writing to Visa: " + command)
      self.delay()
      message = self.visa_in.read(self.visa_in.in_waiting)
      message = message.decode("utf-8")
      print("Answer from Visa: " + message+"")
    except:
      raise TableContError("Visa could not write properly.")
      
    if message == None:
      raise TableContError("Visa did not write/read properly!")
    else:
      message = message.split('\n', 1)[0]
    
    #PF is the only command sent where we expect a response
    if not command == "PF\r":
      parts = message.split(":")
      if len(parts) >= 2 and parts[1] != "\r":
        raise TableContError("Command not recognized")
    return message

  
### Template APP ### 
class TemplateApp:
  def __init__(self,argv):
    # For the moment we don't include a FSM, even if it is raccomended to 
    # develop one for python custom apps
    #self.final_state_machine = Fsm()
    
    self.socket_cycle_running = False

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

    self.status = 'INIT'

    self.data_port = 0
    self.status_port = 0
    self.cmd_port = 0

    self.sub = None # Receives commands
    self.pub = None # Send status 
    self.context = None
    self.poller = None
    self.sub_urls = []
    
    self.tableCont = TableController()
    self.move_table = False	#flag for if message contains command to move table, handeled in proc_message
    
    
    # Parsing arguments coming from the AppControl
    # We expect -c and the configuration file path
    # and -l with the log file path
    # An error occurs if they are missing 
    parser = argparse.ArgumentParser()
    parser.add_argument("-c", "--configurefile", type=str, help="Configuration file", required=True)
    parser.add_argument("-l", "--logfile", type=str, help="Log file", required=True)
    args = parser.parse_args()
    self.configure_file_path = args.configurefile
    self.log_file_path = args.logfile
    self.tableCont.log_file = self.log_file_path

    # Redirecting output to log file
    sys.stdout = open(self.log_file_path, 'w')


  def listen_socket(self):
    print("Entering in socket cycle")
    while self.socket_cycle_running:
      try:
        # Limiting the loop rate with 5 sec sleep
        time.sleep(5)
        # Sending state
        status_msg = "STATUS statuscode="+str(self.rsdictReverse[self.status])
        print("Sending status msg: ",status_msg)
        self.pub.send_string(status_msg)

        # Polling for messages
        socks = dict(self.poller.poll(1))
        if socks.get(self.sub):
          message = self.sub.recv()
          message = message.decode("utf-8")
          self.proc_message(message)

        # It seems that python is not flushing "print" each time it is called.
        # Forcing to do it once per cycle.

        sys.stdout.flush()
      except:
        print("Error in the loop. Breaking...")
        self.socket_cycle_running = False
        sys.stdout.flush()
              
      ###Table controller while loop###
      try:
        
        if self.move_table:	#flag changed in proc_message
          if not self.tableCont.table_sim:           
            self.tableCont.init_table()
            #Assuming visa close done in init_table
          #set actual position taken care of in init_table or automatic if sim
          #send actual position zmq
          table_pos_data = "TAB_IS " + str(self.tableCont.actual_pos[0]) + " " + str(self.tableCont.actual_pos[1])
          self.pub.send_string(table_pos_data) #SEND TO THE GUI 
          index_pos = message.find("SET_TABLE_POSITION ")
          if index_pos >=0:
            self.tableCont.run = True
             #SEND STATUS TO GUI
            self.tableCont.table_display = "TAB_MOVING"
            self.pub.send_string(self.tableCont.table_display) #SEND TO GUI
            #set move position
            mes_pos = message.replace('SET_TABLE_POSITION ', '')
            self.tableCont.move_pos = [float(i) for i in (mes_pos.split(" "))]
            #check if table simulation
            if self.tableCont.table_sim:
              time.sleep(5)
              self.tableCont.actual_pos = self.tableCont.move_pos[:]
            else:	#if not, move the table
              time.sleep(2)
              self.tableCont.move_to_pos()
            #finished moving table
            self.tableCont.run = False
            self.tableCont.table_display = "TAB_DONE"
            self.pub.send_string(self.tableCont.table_display)
            self.move_table = False
            print("Table Position: ",self.tableCont.actual_pos)
            print("Sending last position to the GUI")
            table_pos_data = "TAB_IS " + str(self.tableCont.actual_pos[0]) + " " + str(self.tableCont.actual_pos[1])
            self.pub.send_string(table_pos_data) #SEND TO THE GUI
        else:
          # We update table pos at each status update if the table is not moving
          table_pos_data = "TAB_IS " + str(self.tableCont.actual_pos[0]) + " " + str(self.tableCont.actual_pos[1])
          self.pub.send_string(table_pos_data) #SEND TO THE GUI

      except TableContError as error:
        print(str(error))
        self.socket_cycle_running = False
        sys.stdout.flush()
      except ValueError as error:
        print('ValueeRROR', str(error))
      except serial.SerialException as error:
        print('Serial exception', str(error))
      except:
        print("Error moving table. Breaking...", str)
        self.socket_cycle_running = False
        sys.stdout.flush()
          
  def proc_message(self, msg):
    print(msg) 
    if 'SET_TABLE_POSITION' in msg:
      print('Request to move the table.') 
      
      #change flag to move table
      self.move_table = True
      print('movetableflagsettotrue')
    if 'KILL_APP' in msg:
      print('Request to kill the app')
      self.socket_cycle_running = False


  def parse_standard_params(self, soup):
    # We parse the config file to extracts port numbers.
    print("Looking for ports...")
    port_list = []
    for tag in soup.find_all("ListenPort"):
      port_list.append(tag.string)
    self.data_port = port_list[0]
    self.status_port = port_list[1]
    self.cmd_port = port_list[2]
    print("Data port: ",self.data_port," - Status port: ",self.status_port," - Cmd port: ",self.cmd_port)

    # Url list for ZMQ to subscribe to:
    for tag in soup.find_all("ConnectTo"):
      self.sub_urls.append(tag.string)
     
    for tag in soup.find_all("SerialName"):
      self.tableCont.serial_name = tag.string


  # In this function you can extract other parameters from the config file
  def parse_custom_params(self, soup):
    print("Parsing custom params...")
    # Write here


  def parse_configure_file(self):
    try:
      print("Configure file path sent by AppControl: ",self.configure_file_path)
      with open(self.configure_file_path) as fp:
        soup = Soup(fp, "xml")
        self.parse_standard_params(soup)
        #self.parse_custom_params(soup)
      
    except:
      raise Exception("parse_configure_file failed")


  def initialize_zmq_channels(self):
    self.context = Context()
    self.poller = Poller()
    self.sub = self.context.socket(SUB)
  
    # If the application run in local... do we need to rename the url
    # with localhost instead of machine name? Let's do it...

    # First: subscription to the sockets where the application receives commands
    gui_hostname = socket.gethostname()
    for url in self.sub_urls:
      new_url = "tcp://"
      if gui_hostname in url:
        url = url.replace(gui_hostname,"localhost")
      new_url += url
      self.sub.connect(new_url)
    self.sub.setsockopt(SUBSCRIBE,b'')
    self.poller.register(self.sub,POLLIN)

    # Second: generate socket to send status
    self.pub = self.context.socket(PUB)
    new_url = "tcp://*:"
 #   port_index = self.status_port.find(":")
#    new_url = new_url + self.status_port[port_index+1:]
    new_url = new_url + self.status_port
    print("Url to publish app status: ", new_url)
    self.pub.bind(new_url)


### Actions - from FSM list ###

  def initialize(self):
    print("initialize action begin")
    self.parse_configure_file()
    self.initialize_zmq_channels()
    self.socket_cycle_running = True
    
    #Do initialize table controller stuff
    self.tableCont.initialize_tab_cont()
   
    # After initialize_tab_cont, the table is initialized and the current position has been updated
    # So actual_pos should contain updated data
    table_pos_data = "TAB_IS " + str(self.tableCont.actual_pos[0]) + " " + str(self.tableCont.actual_pos[1])
    self.pub.send_string(table_pos_data) #SEND TO THE GUI 

    self.status='INITIALIZED'
    print("initialize action end")

  def configure(self):
    print("configure action begin")
    print("configure action end")

  def start(self):
    print("start action begin")
    print("start action end")

  def stop(self):
    print("stop action begin")
    print("stop action end")

  def pause(self):
    print("pause action begin")
    print("pause action end")

  def resume(self):
    print("resume action begin")
    print("resume action end")

  def fail(self):
    print("fail action begin")
    self.socket_cycle_running = False
    print("fail action end")

  def reset(self):
    print("reset action begin")
    print("reset action end")



### Main ###

def main(argv):
  #Transferring frame 0 from labview pseudocode
  print(argv)
  newApp = TemplateApp(argv)
  
  # At first, the idea was to have a separate thread listening to the 
  # sockets and sending info. But if the application is killed the thread
  # would have continued to run.
  # So it has been moved inside function listen_socket.
  newApp.initialize()
  newApp.listen_socket()
  


if __name__ == '__main__':
  main(sys.argv)

