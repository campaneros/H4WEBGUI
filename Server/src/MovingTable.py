from .Fsm import Fsm
from .DBGuiInterface import DBGUIInterface
from .ConfigInterface import ConfigInterface
from .AppControl import AppControl
from functools import wraps
from .Run import Run
import traceback
import time
import datetime
import requests
from .Notification import NotificationInterface
import logging
import io



class MovingTable:
    def __init__(self,new_socket, log_text_loglevel):
        self.fsm = Fsm()
        self.dbgui_interface = None
        self.config_interface = None
        self.apps_control = None
        self.mysocket = new_socket
        self.run = None


        self.firstautorestart = datetime.datetime.utcnow()
        self.notification_interface = NotificationInterface("critical")

        self.logger = logging.getLogger('webgui_logger')
        self.log_capture_string = io.StringIO()
        self.ch = logging.StreamHandler(self.log_capture_string)
        self.log_text_loglevel = log_text_loglevel
        self.ch.setLevel(self.log_text_loglevel)
        self.formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        self.ch.setFormatter(self.formatter)
        self.logger.addHandler(self.ch)

    def initialize(self):
        print("Initialize action begin")
        # self.notification_interface.critical("Init")
        if(self.fsm.checkFromState("initialize")):
            try:
                self.dbgui_interface = DBGUIInterface()
                self.config_interface = ConfigInterface(self.dbgui_interface)
                self.loadLastConfiguration()
                self.apps_control= AppControl(self.mysocket,self.config_interface.base_path)
                # self.createLastMessage("Initialized!")
                self.logger.info("Initialized!")
                print("Initialize action end")
                return self.fsm.setNewState("initialize"), self.lastMessage
            except Exception as e:
                # self.createLastMessage("[RunControl][Initialize] Initialize failed with:")
                # self.createLastMessage(str(e))
                self.logger.error("Initialize failed with:")
                self.logger.error(str(e))
                return self.fail("Failed Initialize action")
        else:
            self.lastMessage = "Transition not allowed!"
            return self.fsm.state, self.lastMessage


