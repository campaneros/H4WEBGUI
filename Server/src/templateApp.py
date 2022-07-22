from Fsm import Fsm
import threading
import sys
import argparse
import time
from bs4 import BeautifulSoup as Soup
from zmq import *
import socket


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
      'ERROR': 14,
      'STEP':15
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

    # Thread for periodic actions
    # The idea is to start it in the initialization phase and then make it depending on
    # self.status variable 
    self.theThread = threading.Thread(target=self.thread_function, args=())
    self.runningFlag = False

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

    # Redirecting output to log file
    sys.stdout = open(self.log_file_path, 'w')


  def listen_socket(self):
    print("Entering in socket cycle")
    while self.socket_cycle_running:
      try:
        # Limiting the loop rate with 1 sec sleep
        time.sleep(1)
        # Sending state
        status_msg = "STATUS statuscode="+str(self.rsdictReverse[self.status])
        print("Sending status msg: ",status_msg)
        self.pub.send_string(status_msg)

        # Polling for messages
        socks = dict(self.poller.poll(1))
        if socks.get(self.sub):
          message = self.sub.recv()
          self.proc_message(message.decode("utf-8"))

        # It seems that python is not flushing "print" each time it is called.
        # Forcing to do it once per cycle.

        sys.stdout.flush()
      except:
        print("Error in the loop. Breaking...")
        self.socket_cycle_running = False
        sys.stdout.flush()


  def proc_message(self, msg):
    # here you can check the command string and launch the 
    # correspondent callback like the following KILL_APP.
    # Keep KILL_APP if you want the closing of the application controlled by the GUI (suggested)
    print('Message from subscription:', msg)
    if 'GUI_STARTRUN' in msg:
      self.start()
    if 'KILL_APP' in msg:
      self.exit()
    if 'GUI_STOPRUN' in msg:
      self.stop()
    if 'BLABLABLA' in msg:
      print('A new command...')
    


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
        self.parse_custom_params(soup)
      
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
      self.sub.connect("tcp://"+url)
    self.sub.setsockopt(SUBSCRIBE,b'')
    self.poller.register(self.sub,POLLIN)

    # Second: generate socket to send status
    self.pub = self.context.socket(PUB)
    new_url = "tcp://*:"
    port_index = self.status_port.find(":")
    new_url = new_url + self.status_port[port_index+1:]
    print("Url to publish app status: ", new_url)
    self.pub.bind(new_url)
    self.poller.register(self.pub,POLLIN)

  # Function used by the thread
  def thread_function(self):
    counter = 0
    while self.runningFlag:
      if self.status == 'INITIALIZED':
        print('Do something when INITIALIZED...')
      if self.status == 'CLEARED':
        print('Do something when CLEARED...')
      for i in range(10):
        time.sleep(1)
        if not self.runningFlag:
          break

### Actions - from FSM list ###

  def initialize(self):
    print("initialize action begin")
    self.parse_configure_file()
    self.initialize_zmq_channels()
    self.socket_cycle_running = True
    self.status='INITIALIZED'

    # Thread for periodic actions
    self.runningFlag = True
    self.theThread.start()
    print("initialize action end")

  def configure(self):
    print("configure action begin")
    print("configure action end")

  def start(self):
    print("start action begin")
    self.status = 'CLEARED'
    print("start action end")

  def stop(self):
    print("stop action begin")
    self.status = 'INITIALIZED'
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

  def exit(self):
    print("exit action begin")
    self.socket_cycle_running = False
    self.runningFlag = False
    self.status = 'BYE'
    print("exit action end")


### Main ###

def main(argv):
  print(argv)
  newApp = TemplateApp(argv)

  newApp.initialize()
  newApp.listen_socket()

if __name__ == '__main__':
  main(sys.argv)
