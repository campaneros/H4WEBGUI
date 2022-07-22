
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

class RunControl:
    def __init__(self,new_socket, log_text_loglevel):
        print("[RunControl][init] CTORING begin")
        self.fsm = Fsm()
        self.lastMessage = ""
        self.logMessages = ""
        self.dbgui_interface = None
        self.config_interface = None
        self.apps_control = None
        self.mysocket = new_socket
        self.run = None
        self.lastRunTemp = None # dict, not a Run object
        self.autorestart = False
        self.autorestartcounter = 0
        self.maxautorestart = 3
        self.scan_run = False
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

        print("[RunControl][init] CTORING end")

# ACTIONS
    def initialize(self):
        print("[RunControl][initialize] Initialize action begin")
        # self.notification_interface.critical("Init")
        if(self.fsm.checkFromState("initialize")):
            try:
                self.dbgui_interface = DBGUIInterface()
                self.config_interface = ConfigInterface(self.dbgui_interface)
                self.loadLastConfiguration()
                self.apps_control= AppControl(self.mysocket,self.config_interface.base_path)
                # self.createLastMessage("Initialized!")
                self.logger.info("Initialized!")
                print("[RunControl][initialize] Initialize action end")
                return self.fsm.setNewState("initialize"), self.lastMessage
            except Exception as e:
                # self.createLastMessage("[RunControl][Initialize] Initialize failed with:")
                # self.createLastMessage(str(e))
                self.logger.error("[RunControl][Initialize] Initialize failed with:")
                self.logger.error(str(e))
                return self.fail("Failed Initialize action")
        else:
            self.lastMessage = "Transition not allowed!"
            return self.fsm.state, self.lastMessage


    def configure(self,params):
        print("[RunControl][configure] Configure action begin")
        if(self.fsm.checkFromState("configure")):
            try:
                self.apps_control.findAndKillOldApps()
                self.config_interface.prepareConfiguration(params)
                # We check if the config include a delay scan
                if self.config_interface.scan_params != None:
                    self.autorestart = True
                    self.maxautorestart = int(self.config_interface.scan_params['scan_steps'])
                    self.scan_run = True
                    print("In [RunControl::configure]",self.autorestart,self.maxautorestart)
                self.apps_control.startApplications()
                if not self.waitAllAppsAreStopped(59):
                   raise Exception("One or more applications are not configured!")
                self.createRun(params)
                self.logger.info("Configured!")
                print("[RunControl][configure] Configure action end")
                return self.fsm.setNewState("configure"), self.lastMessage
            except Exception as e:
                self.logger.error("[RunControl][Configure] Configure failed with:")
                self.logger.error(str(e))
                traceback.print_exc()
                return self.fail("Failed configure action")
        else:
            self.lastMessage = "Transition not allowed!"
            return self.fsm.state, self.lastMessage

    def start(self, params):
        print("[RunControl][start] Start action begin")
        if(self.fsm.checkFromState("start")):
            try:
                runNumber = int(self.dbgui_interface.getLastRunNumber() + 1)
                print("New run number: ",runNumber)
                self.run._id = runNumber
                self.run.startTime = int(time.time())*1000
                # We reset stopTime in case we have pushed "start" after "start and stop".
                # In this case a run was already existing and it is like creating a new run
                # instead of desotrying this instance and create a new one.
                # If we arrive from a "start and stop", the configuration is still the same
                # and only the timestamps have to be modified.
                self.run.stopTime = 0
                self.startRun(params)
                self.apps_control.runApps(self.run)
                if not self.waitAllAppsAreRunning(15):
                    raise Exception("One or more applications haven't started.")
                # self.createLastMessage("Running!")
                self.logger.info("Running!")
                print("[RunControl][start] Start action end")
                return self.fsm.setNewState("start"), self.lastMessage
            except Exception as e:
                # self.createLastMessage("[RunControl][start] Start failed with:")
                # self.createLastMessage(str(e))
                self.logger.error("[RunControl][start] Start failed with:")
                self.logger.error(str(e))
                return self.fail("Failed start action")
        else:
            self.lastMessage = "Transition not allowed!"
            return self.fsm.state, self.lastMessage

    def stop(self):
        print("[RunControl][stop] Stop action begin")
        if(self.fsm.checkFromState("stop")):
            try:
                self.apps_control.stopApps()
                if not self.waitAllAppsAreStopped(60):
                   raise Exception("One or more applications haven't stopped.")
                self.saveRunOnDB()
                # self.createLastMessage("Stopped!")
                self.logger.info("Stopped!")
                print("[RunControl][stop] Stop action end")
                return self.fsm.setNewState("stop"), self.lastMessage
            except Exception as e:
                # self.createLastMessage("[RunControl][stop] Stop failed with:")
                # self.createLastMessage(str(e))
                self.logger.error("[RunControl][stop] Stop failed with:")
                self.logger.error(str(e))
                return self.fail("Failed stop action")
        else:
            self.lastMessage = "Transition not allowed!"
            return self.fsm.state, self.lastMessage

    def pause(self):
        print("[RunControl][pause] Pause action begin")
        if(self.fsm.checkFromState("pause")):
            try:
                self.apps_control.pauseApps()
                print("[RunControl][pause] Doing my pausing...")
                # self.createLastMessage("Paused!")
                self.logger.info("Paused")
                print("[RunControl][pause] Pause action end")
                return self.fsm.setNewState("pause"), self.lastMessage
            except Exception as e:
                # self.createLastMessage("[RunControl][pause] Pause failed with:")
                # self.createLastMessage(str(e))
                self.logger.error("[RunControl][pause] Pause failed with:")
                self.logger.error(str(e))
                return self.fail("Failed pause action")

    def resume(self):
        print("[RunControl][resume] Resume action begin")
        if(self.fsm.checkFromState("resume")):
            try:
                self.apps_control.resumeApps()
                print("[RunControl][resume] Doing my resuming...")
                # self.createLastMessage("Running!")
                self.logger.info("Running")
                print("[RunControl][resume] Resume action end")
                return self.fsm.setNewState("resume"), self.lastMessage
            except Exception as e:
                # self.createLastMessage("[RunControl][resume] Resume failed with:")
                # print(str(e))
                self.logger.error("[RunControl][resume] Resume failed with:")
                self.logger.error(str(e))
                return self.fail("Failed resume action")

        else:
            self.lastMessage = "Transition not allowed!"
            return self.fsm.state, self.lastMessage

    def fail(self, errorMsg):
        print("[RunControl][fail] Fail action begin")
        # If there was a run ongoing we close and save it
        if self.run != None and self.run.startTime != 0 and self.run.stopTime == 0:
          self.run.failed = True
          self.saveRunOnDB()
        # self.createLastMessage(errorMsg)
        self.logger.error(errorMsg)
        self.notification_interface.critical("[Fail Action] " + errorMsg)
        print("[RunControl][fail] Fail action end")
        return self.fsm.setNewState("fail"), self.lastMessage

    def step(self, counter):
        print("[RunControl][step] Step {} action begin".format(str(counter)))
        # If there was a run ongoing we close and save it
        if self.run != None and self.run.startTime != 0 and self.run.stopTime == 0:
          self.run.failed = False
          self.saveRunOnDB()
        # self.createLastMessage(errorMsg)
        print("[RunControl][step] Step {} action end".format(str(counter)))
        return self.fsm.setNewState("step"), self.lastMessage

    def reset(self):
        print("[RunControl][reset] Reset action begin")
        if(self.fsm.checkFromState("reset")):
            try:
                if self.run != None and self.run.startTime != 0 and self.run.stopTime == 0:
                    self.run.failed = False
                    self.saveRunOnDB()
                # self.fsm = Fsm()
                # self.lastMessage = ""
                # self.logMessages = ""
                self.dbgui_interface = None
                self.config_interface = None
                self.apps_control = None
                # self.mysocket = new_socket
                self.run = None
                self.lastRunTemp = None # dict, not a Run object
                # self.autorestart = False
                # self.autorestartcounter = 0
                # self.createLastMessage("Resetted!")
                self.logger.info("Resetted")
                return self.fsm.setNewState("reset"), self.lastMessage
            except Exception as e:
                # self.createLastMessage("[RunControl][reset] Reset failed with:")
                # self.createLastMessage(str(e))
                self.logger.error("[RunControl][reset] Reset failed with:")
                self.logger.error(str(e))
                return self.fail("Failed reset action")

### END OF ACTIONS ###

### CONFIGURATION GUI SECTION ###

    def getSConfigsTagsList(self):
        print("Getting the list of Services Configurations Tags...")
        sconfigsTagsList = self.dbgui_interface.getSConfigsTagsList()
        return sconfigsTagsList

    def getSConfigsVersList(self,tag):
        print("Getting the list of Services Configurations Vers...")
        sconfigsVersList = self.dbgui_interface.getSConfigsVersList(tag)
        return sconfigsVersList

    def getRunKeysTagsList(self):
        print("Getting the list of Run Keys Tags...")
        runkeysTagsList = self.dbgui_interface.getRunKeysTagsList()
        return runkeysTagsList

    def getRunKeysVersList(self,tag):
        print("Getting the list of Run Keys Vers...")
        runkeysVersList = self.dbgui_interface.getRunKeysVersList(tag)
        return runkeysVersList

    def getDRsList(self,scTag,scVer):
        print("Getting the list of DRs in Service Configuration", scTag, "ver",scVer)
        DRsList = self.config_interface.getDRsList(scTag,scVer)
        return DRsList

    def getInputListAndTrigger(self,rkTag,rkVer):
        print("Getting the list of Inputs in Application Configuration",rkTag, "ver",rkVer)
        inputList, stDowntime = self.config_interface.getInputListAndTrigger(rkTag,rkVer)
        return inputList, stDowntime

    def getTablePosTagsList(self):
        print("Getting the list of Table Positions Tags...")
        tablePosTagsList = self.dbgui_interface.getTablePosTagsList()
        return tablePosTagsList

    def getTablePosList(self, tag):
        tablePosList = self.dbgui_interface.getTablePosList(tag)
        return tablePosList

    def getTbCampList(self):
        tbCampList = self.dbgui_interface.getTbCampList()
        return tbCampList

### END CONFIGURATION SECTION ###

### HELPERS ###

    # def createLastMessage(self, msg):
    #     self.lastMessage = datetime.datetime.now().strftime("[%Y-%m-%d %H:%M:%S] ")
    #     self.lastMessage += msg
    #     self.logMessages += "," + self.lastMessage

    def getJsonUpdateAll(self):
        jsonObject = {}
        jsonObject["logTextLogLevel"] = self.log_text_loglevel
        jsonObject["currentstate"] = self.fsm.state
        jsonObject["performingAction"] = self.fsm.performingAction
        # jsonObject["msg"]= self.logMessages
        jsonObject["msg"] = self.log_capture_string.getvalue()
        jsonObject["run"] = {}
        jsonObject["autorestart"] = self.autorestart
        if self.run != None:
            jsonObject["run"].update({
                "runNumber": self.run._id,
                "startTime": self.run.startTime,
                "stopTime": self.run.stopTime
            })
            if self.run.runType != "":
                jsonObject["run"].update({
                    "eventsPerSpill": self.run.eventsPerSpill,
                    "runType": self.run.runType,
                    "beamEnergy": self.run.beamEnergy,
                    "beamType": self.run.beamType,
                    "tablePosTag": self.run.tablePosTag,
                    "tablePos": self.run.tablePos,
                    "tbCamp": self.run.tbCamp,
                    "tableX": self.run.tableX,
                    "tableY": self.run.tableY
                })
            else:
                jsonObject["run"].update({
                    "eventsPerSpill": self.lastRunTemp['eventsPerSpill'],
                    "runType": self.lastRunTemp['runType'],
                    "beamEnergy": self.lastRunTemp['beamEnergy'],
                    "beamType": self.lastRunTemp['beamType'],
                    "tableX": self.lastRunTemp['tableX'],
                    "tableY": self.lastRunTemp['tableY'],
                    "tablePosTag": self.lastRunTemp['tablePosTag'],
                    "tablePos": self.lastRunTemp['tablePos'],
                    "tbCamp": self.lastRunTemp.get('tbCamp',"")
                })
        elif self.lastRunTemp != None:
            print("lastRunTemp: ", self.lastRunTemp)
            jsonObject["run"].update({
                "runNumber": 0,
                "eventsPerSpill": self.lastRunTemp['eventsPerSpill'],
                "runType": self.lastRunTemp['runType'],
                "beamEnergy": self.lastRunTemp['beamEnergy'],
                "beamType": self.lastRunTemp['beamType'],
                "tableX": self.lastRunTemp['tableX'],
                "tableY": self.lastRunTemp['tableY'],
                "tablePosTag": self.lastRunTemp['tablePosTag'],
                "tablePos": self.lastRunTemp['tablePos'],
                "tbCamp": self.lastRunTemp.get('tbCamp',"")
            })
        if self.apps_control:
            jsonObject["apps"]= self.apps_control.getAppsUpdate()
        if self.config_interface:
            print("DR list",self.config_interface.DRsList)
            if self.config_interface.sConfigTag != None:
                jsonObject["sConfigTag"] =  self.config_interface.sConfigTag
            if self.config_interface.sConfigVer != None:
                jsonObject["sConfigVer"] =  self.config_interface.sConfigVer
            if self.config_interface.runKeyTag != None:
                jsonObject["runKeyTag"] =  self.config_interface.runKeyTag
            if self.config_interface.runKeyVer != None:
                jsonObject["runKeyVer"] =  self.config_interface.runKeyVer
            if len(self.config_interface.DRsList) != 0:
                jsonObject["activeDRs"] =  self.config_interface.DRsList
            else:
                jsonObject["activeDRs"] = 0
        return jsonObject

    def getJsonUpdateApps(self):
        jsonObject = {}
        if self.apps_control:
            if self.apps_control.isError() and self.fsm.state != 'Error':
                self.fail("Application in Error")
                # if this is the first autorestart, we record its time
                if self.autorestart and self.autorestartcounter == 0:
                    self.firstautorestart = datetime.datetime.utcnow()
                # if more than 10min passed from the first autorestart
                # we reset the counter and we proceed with the autorestart
                now = datetime.datetime.utcnow()
                deltaautorestart = datetime.timedelta(minutes=10)
                if (now - self.firstautorestart) > deltaautorestart:
                    self.autorestartcounter = 0
                if self.autorestart and self.autorestartcounter >= 3:
                    print("Zeroing reset")
                    self.autorestart = False
                    self.autorestartcounter = 0
                self.mysocket.emit("updateAll")
                if self.autorestart and self.autorestartcounter < 3:
                    r = requests.get("http://127.0.0.1:5000/api/reset?type=auto")
                    print("reset request response: ", r.text)
                    self.notification_interface.critical("Automatic restart")
            #If at lest an application is asking for a step but the system has to be in Running
            if self.apps_control.isStep() and self.fsm.state == 'Running':
                self.step(self.autorestartcounter)
                if self.autorestart:
                    if self.autorestartcounter >= self.maxautorestart:
                        print("Zeroing reset")
                        self.autorestart = False
                        self.autorestartcounter = 0
                    else:
                        r = requests.get("http://127.0.0.1:5000/api/reset?type=auto")
                        print("Reset request response: ", r.text)
                        self.notification_interface.critical("Automatic restart for stepping")
            if self.apps_control.areAppsRunning():
                self.apps_control.checkDRCVs()
            jsonObject["apps"]= self.apps_control.getAppsUpdate()
        return jsonObject

    def loadLastConfiguration(self):
        self.lastRunTemp = self.dbgui_interface.getLastRun()
        self.config_interface.loadLastConfiguration(self.lastRunTemp)

    def createRun(self,params):
        runNumber = int(self.dbgui_interface.getLastRunNumber() + 1)
        print("[RunControl][createRun] Creating run with number: ",runNumber)
        self.run = Run()
        self.run._id = runNumber
        self.run.scTag = params['scTag']
        self.run.scVer = int(params['scVer'])
        self.run.rkTag = params['rkTag']
        self.run.rkVer = int(params['rkVer'])
        self.run.activeDRs = params['activeDRs']

    def startRun(self,params):
        print("[RunControl][startRun] Starting run.")
        self.run.eventsPerSpill = int(params['eventsPerSpill'])
        self.run.runType = params['runType']
        self.run.beamEnergy = float(params['beamEnergy'])
        self.run.beamType = params['beamType']
        self.run.tablePosTag = params['tablePosTag']
        self.run.tablePos = params['tablePos']
        if 'tbCamp' in params:
            self.run.tbCamp = params['tbCamp']
        self.run.tableX = float(params['tableX'])
        self.run.tableY = float(params['tableY'])
        print("[RunControl][startRun] End of function")

    def saveRunOnDB(self):
        print("[RunControl][saveRunOnDB] Saving run on DB...")
        print("Saving ",self.run.tablePos)
        self.run.stopTime = int(time.time())*1000
        #  TODO FIXME this may crash if the propery does not exist
        self.run.evinrun = self.apps_control.status['evinrun']
        self.dbgui_interface.saveRun(self.run.__dict__)

    def setAutoRestart(self, new_autorestart):
        self.autorestart = new_autorestart
        return "set new autorestart: " + str(self.autorestart)

    def waitAllAppsAreRunning(self, timeout):
        everythingFine = True
        startTimer = time.time()
        while not self.apps_control.areAppsRunning():
            time.sleep(1)
            if (time.time() - startTimer) > timeout:
                print("[RunControl][waitAllAppsAreRunning] Timeout occurred while waiting that all apps were moving to Running...")
                everythingFine = False
                break
        return everythingFine

    def waitAllAppsAreStopped(self, timeout):
        everythingFine = True
        startTimer = time.time()
        while not self.apps_control.areAppsStopped():
            time.sleep(1)
            if (time.time() - startTimer) > timeout:
                print("[RunControl][waitAllAppsAreStopped] Timeout occurred while waiting that all apps were moving to Stop...")
                everythingFine = False
                break
        return everythingFine

    def moveTable(self, position):
        self.apps_control.moveTable(position)
        time.sleep(3)
        if (self.waitTableIsDone(90)):
            msg = 'Table Moved in the new position'
            self.run.tableX = max(float(position['tableX']), 0.)
            self.run.tableY = max(float(position['tableY']), 0.)
            # self.createLastMessage(msg)
            self.logger.info(msg)
            return msg
        msg = 'Error or timeout moving table'
        # self.createLastMessage(msg)
        self.logger.error(msg)
        return msg

    def waitTableIsDone(self, timeout):
        everythingFine = True
        startTimer = time.time()
        while not self.apps_control.isTableDone():
            time.sleep(1)
            if (time.time() - startTimer) > timeout:
                print("[AppControl][waitIsTableDone] Timeout occurred while waiting that the table is moving...")
                everythingFine = False
                break
        return everythingFine

    def setLogTextLogLevel(self, logTextLogLevel):
        self.log_text_loglevel = logTextLogLevel
        self.ch.setLevel(self.log_text_loglevel)
        self.mysocket.emit("updateAll")
        return logTextLogLevel

