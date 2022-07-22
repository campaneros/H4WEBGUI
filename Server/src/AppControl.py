import glob
import subprocess, os, shlex
import time
from zmq import *
from threading import Thread
import copy
import logging
import socket
from .runregistry import RunRegistry

class AppControl:
    def __init__(self, new_socket, basePath):
        self.status={
            'localstatus': 'STARTED',
            'runnumber': 0,
            'spillnumber': 0,
            'evinrun': 0,
            'evinspill': 0,
            'eventsmerged': 0,
            'badspills': 0,
            'spillsize': 0,
            'transferRate': 0,
            'spillduration': 0,
            'trigrate': 0,
            'temperatures': [],
            'humidity': 0,
            'dewpoint': 0,
            'laudatemp': 0
            }
        self.gui_out_messages={
            'startrun': 'GUI_STARTRUN',
            'pauserun': 'GUI_PAUSERUN',
            'restartrun': 'GUI_RESTARTRUN',
            'stoprun': 'GUI_STOPRUN',
            'die': 'GUI_DIE',
            'reconfig': 'GUI_RECONFIG'
            }
        self.gui_in_messages={
            'status': 'STATUS',
            'log': 'GUI_LOG',
            'error': 'GUI_ERROR',
            'sps': 'GUI_SPS',
            'tablepos': 'TAB_IS',
            'tablemoving': 'TAB_MOVING',
            'tabledone': 'TAB_DONE',
            'transfer': 'TRANSFER',
            'spillduration': 'SPILLDURATION'
            }
        self.rsdict={ #imported from H4DAQ/interface/Command.hpp
            0:'START',
            1:'INIT',
            2:'INITIALIZED',
            3:'BEGINSPILL',
            4:'CLEARED',
            5:'WAITFORREADY',
            6:'CLEARBUSY',
            7:'WAITTRIG',
            8:'READ',
            9:'ENDSPILL',
            10:'RECVBUFFER',
            11:'SENTBUFFER',
            12:'SPILLCOMPLETED',
            13:'BYE',
            14:'ERROR',
            15:'STEP'
            }
        self.rsdictReverse={ #imported from H4DAQ/interface/Command.hpp
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
            'STEP': 15
            }
        self.remotestatus_endofspill=9
        self.remotestatuses_datataking=[6,7,8]
        self.remotestatuses_running=[3,4,5,6,7,8,9,10,11,12]
        self.remotestatuses_stopped=[0,1,2,13,14]

	# TODO: define some variables in RunControl?
        self.autostop_max_events=-1

        self.base_path = basePath
        self.configFilesList = []
        self.appsList = []
        self.launchCommands = {
            "DRCV":"/home/cmsdaq/DAQ/H4DAQ/bin/datareceiver",
            "RC":"/home/cmsdaq/DAQ/H4DAQ/bin/runcontrol",
            "EB":"/home/cmsdaq/DAQ/H4DAQ/bin/eventbuilder",
            "DR":"/home/cmsdaq/DAQ/H4DAQ/bin/datareadout",
            "DAQKILL":"/home/cmsdaq/DAQ/H4DAQ/bin/daqkill",
        }
        self.context = None
        self.poller = None
        self.pub = None
        self.pubsocket_bind_address='tcp://*:5566' # address of GUI PUB socket
        self.poll_sockets_running = False
        self.thread_timer = 0
        self.mysocket = new_socket
        self.logger = logging.getLogger('webgui_logger')
        self.run_registry = RunRegistry()
        
    def __del__(self):
        print("[AppControl][Destructor] Closing threads...")
        self.stop_network()

    # 1) Look for the configurations in the "latest" folder
    # 2) Launch the corresponding applications and check if pid available.
    # 2) Raise an error if the applications are not properly started (pid = 0)
    # 3) Activate intercommunication thread.
    def startApplications(self):
        self.logger.debug("startApplications")
        self.collectAppsList()
        self.launchAllApplications()
        counter = 0
        while len(self.getAppsPid()):
            if counter == 3:
                raise Exception("Application with no pid")
            counter = counter + 1
            time.sleep(5)
        self.start_network()

    def findAndKillOldApps(self):
        self.collectAppsList()
        self.getAppsPid()
        self.killApps()

    # It looks in the "latest" folder where the xml are created and create the apps list
    def collectAppsList(self):
        self.appsList = []
        print("[AppControl][collectAppsList] Get list of apps files from latest folder")
        self.configFilesList = glob.glob(self.base_path + "latest" + "/*.xml")
        if len(self.configFilesList) == 0:
            print("[AppControl][collectAppsList] Latest folder not found... skipping.")

        # Looking for RC file and putting it as first in the list
        RC_ind = None
        for ind, file_name in enumerate(self.configFilesList):
            if self.configFilesList[ind].find("_RC_") != -1:
                RC_ind = ind
                RC_file = self.configFilesList[ind]
        if RC_ind == None:
            print("[AppControl][collectAppsList] Are you running with no RC? if you will use this config you will see a warning in the GUI.")
            #return
        else:
            del(self.configFilesList[RC_ind])
            self.configFilesList.insert(0,RC_file)

        # Create apps list from config files names
        for filename in self.configFilesList:
            logfile = filename[:-4].replace('config', 'log')+".log"
            indexHost = filename.find("_")+1
            indexHost2 = filename.find("_",indexHost+1)
            hostName = filename[indexHost:indexHost2]

            indexPort = filename.rfind("_")+1
            indexPort2 = filename.rfind(".xml")
            portNumber = filename[indexPort:indexPort2]
            appName = filename[indexHost2+1:indexPort-1]

            gui_hostname = socket.gethostname()
            newindex = gui_hostname.find(".")
            if newindex > 0:
               gui_hostname = gui_hostname[0:newindex]
            address = 'tcp://'+hostName+":"+portNumber
            if gui_hostname == hostName:
                address = address.replace(hostName,"localhost")
            self.appsList.append({
                "appName": appName,
                "hostName": hostName,
                "portNumber": portNumber,
                "fileName": filename,
                "logFile": logfile,
                "address": address,
                "status": 'None',
		        "pid": 0,
                "socket": None,
                "timestamp": 0})
        # the moving table is controlled like an application
        # IMPORTANT: PID = -1 in order to skip PID check
        tableApp = {
                "appName": 'Table',
                "hostName": "",
                "portNumber": "",
                "fileName": "",
                "address": 'tcp://128.141.77.125:6999',
                "status":'TAB_DONE',
                "pid":0,
                "socket": None,
                "timestamp":0,
                "posX": 0,
                "posY": 0
        }
        #FIXME when the table will be available as python application configurable from DB, 
        # everything about tableApp hardcoded in the code should be removed.
        # For example the line self.appsList.append(tableApp) should be removed
        # as well as the others.

        #self.appsList.append(tableApp)

    def launchAllApplications(self):

        for app in self.appsList:
            onlyFileName = app["fileName"][ app["fileName"].rfind("/")+1:]
            # Get machine name from file
            machineName = app["hostName"] + ".cern.ch"

            # If the service has the initcmd defined we use that one instead of /bin/blabla
            initCommand = self.getInitCmd(app["fileName"])
            # Creating launch command
            command = ""

            gui_hostname = socket.gethostname()
            newindex = gui_hostname.find(".")
            if newindex > 0:
                gui_hostname = gui_hostname[0:newindex]
            remoteApp = True
            print(app["hostName"],gui_hostname)
            if app["hostName"] == gui_hostname:
                remoteApp = False
            if remoteApp:
                command += "ssh cmsdaq@"+machineName+" '"

            if initCommand != "":
                print("initCommand not null: ",initCommand)
                
                command += initCommand
                command += " -c " + app["fileName"]
                command += " -l " + app["logFile"]
                

                if remoteApp:
                    command += "'"

                command += " &"
            else:   
                if app["appName"] == "RC":
                    command += self.launchCommands["RC"]
                elif app["appName"] == "EB":
                    command += self.launchCommands["EB"]
                elif "DRCV" in app["appName"]:
                    command += self.launchCommands["DRCV"]
                elif "DR" in app["appName"]:
                    command += self.launchCommands["DR"]

                command += " -d -c " + app["fileName"]
                command += " -v 3 -l " + app["logFile"]
                command += " > /tmp/H4/log_h4daq_start_"+app["appName"]+"_"+onlyFileName[7:-4]+"_"+str(int(time.time()))+".log"
                if remoteApp:
                    command += "'"
                command += " 2>&1 | tee  /tmp/H4/log_h4daq_update_"+app["appName"]+"_"+onlyFileName[7:-4]+"_"+str(int(time.time()))+".log"
                # TODO test adding bashrc
                command = 'source ~/.bashrc; ' + command

            print(command)
            # TODO remove shell=True??
            # TODO capture here the remote command PID
            # TODO use popen instead of call()

            #os.environ["LD_LIBRARY_PATH"] = "/usr/local/lib64/:" + os.environ["LD_LIBRARY_PATH"]
            #new_env = os.environ.copy()
            #new_env["LD_LIBRARY_PATH"] = "/usr/local/lib64/:" + new_env["LD_LIBRARY_PATH"]

            #split_args = shlex.split(command)
            #print("Split up Arguments: ", split_args)
            #subprocess.Popen(split_args, env=new_env, shell=True)
            subprocess.call(command, shell=True)

    def getInitCmd(self,fileName):
        initCmd = ""
        with open(fileName, 'r') as myfile:
            data=myfile.read()
            initIndex1 = data.find("<initcmd>")+9
            initIndex2 = data.find("</initcmd>")
            if (initIndex1 != -1 and initIndex2 != -1):
                initCmd = data[initIndex1:initIndex2]
        return initCmd

    # Look for apps pid based on xml config file name
    # Return a list of the applications with no pid for error reporting
    def getAppsPid(self):
        appsNoPid = []
        for app in self.appsList:
            print(app)
            # Again, exception for applications running in the same machine of the H4WEBGUI
            gui_hostname = socket.gethostname()
            newindex = gui_hostname.find(".")
            if newindex > 0:
                gui_hostname = gui_hostname[0:newindex]
            p = None
            
            if app["hostName"] == gui_hostname:
                print(app["fileName"])
                p = subprocess.Popen(('pgrep', "-f", app["fileName"]), shell=False, stdout=subprocess.PIPE, close_fds=True)
            else: 
                machineName = app["hostName"] + ".cern.ch"
                p = subprocess.Popen(('ssh', "cmsdaq@"+machineName, " pgrep -f "+ app["fileName"]), shell=False, stdout=subprocess.PIPE, close_fds=True)
                # We should react in case pid is missing
            lines=p.stdout.readlines()
            print(lines)
            if len(lines) == 2:
                app["pid"] = int(lines[1][:-1])
                print("[AppControl][getAppsPid] Pid", app["pid"], "found for app", app["appName"], "on machine", app["hostName"])
            elif len(lines) == 1:
                app["pid"] = int(lines[0][:-1])
                print("[AppControl][getAppsPid] Pid", app["pid"], "found for app", app["appName"], "on machine", app["hostName"])
            else:
                print("[AppControl][getAppsPid] ERROR! No pid found for app", app["appName"], "on machine", app["hostName"])
                appsNoPid.append(app["appName"])
        return appsNoPid

    def killApps(self):
        for app in self.appsList:
            print("Killing app", app["appName"], "with pid", app["pid"], "if pid is different from 0.")
            if app["pid"] != 0:
            	machineName = app["hostName"] + ".cern.ch"
            	p = subprocess.Popen(('ssh', "cmsdaq@"+machineName, " "+self.launchCommands["DAQKILL"]+" "+str(app["pid"])), shell=False, stdout=subprocess.PIPE, close_fds=True)
        # Command to close apps answering to this command
        self.send_message('KILL_APP')

    def start_network(self):
        # The AppControl is subscribing to the application socket created to send the status
        # This is done for each application in the list.
        self.context = Context()
        self.poller = Poller()
        for app in self.appsList:
            app['socket'] = self.context.socket(SUB)
            print(app['address'],app['socket'])
            app['socket'].connect(app['address'])
            app['socket'].setsockopt(SUBSCRIBE,b'')
            self.poller.register(app['socket'],POLLIN)

        self.pub = self.context.socket(PUB)
        self.pub.bind(self.pubsocket_bind_address)

        # Is there a better way to handle these threads?
        self.poll_sockets_running = True
        pool_socket_thread = Thread(target = self.poll_sockets)
        pool_socket_thread.start()

    def poll_sockets(self):
        while self.poll_sockets_running:
            socks = dict(self.poller.poll(1))
            timeToUpdate = False
            for app in self.appsList:
                if (socks.get(app['socket'])):
                    message = app['socket'].recv()
                    tempStatus = app['status']
                    self.proc_message(app,message.decode("utf-8"))
                    if tempStatus != app['status'] or int(time.time()) - self.thread_timer > 0.5:
                        self.thread_timer = int(time.time())
                        timeToUpdate = True
                    if app['appName']=='RC' and app['statuscode']==self.remotestatus_endofspill:
                        self.run_registry.logSpill(app['spillnumber'], nevents=app["evinspill"], trigrate=app["trigrate"])
            if timeToUpdate:
                self.mysocket.emit('updateApps')

    def send_message(self,msg,param='',forcereturn=None):
        mymsg=msg
        print('[AppControl][send_message] Contents of param: ', str(param))
        if not param=='':
            mymsg=str().join([str(mymsg),' ',str(param)])
        # if (self.debug):
        #     self.Log(str(' ').join(('Sending message:',str(mymsg))))
        print("[AppControl][send_message] Sending message:",mymsg)
        if self.pub != None:
          self.pub.send_string(mymsg)
        else:
          print("[AppControl][send_message] Trying to send a message to the applications with no pub defined, why?")
        if not forcereturn==None:
            return forcereturn

    def proc_message(self,app,msg):
        print('Processing message from',app["appName"],':',msg)
        app["timestamp"]=int(time.time())
        parts = msg.split(' ')
        if len(parts)<1:
            return
        tit = parts[0]
        parts = parts[1:]
        if tit==self.gui_in_messages['status']:
            oldstatus=app["status"]
            for part in parts:
                if part.find('=')<0:
                    continue
                key,val=part.split('=')
                try:
                    app[key]=int(val)
                except ValueError:
                    print('Impossible to interpret message: <'+msg+'>')
                    True
            app["status"]=self.rsdict[app["statuscode"]]
            if app["statuscode"] in self.remotestatuses_datataking:
                app["status"]='DATATAKING'
            if not oldstatus==app["status"]:
            	print('Status change for '+str(app["appName"])+': '+str(oldstatus)+' -> '+app["status"])
            # if app["appName"]=='RC':
            #     self.processrccommand(app["status"])
            #     self.send_stop_pause_messages()
        elif tit==self.gui_in_messages['log']:
            mymsg = 'Log from '+app["appName"]+':'
            for p in parts:
                mymsg+=' '+str(p)
            mymsg=mymsg.replace('\n','')
            #self.Log(mymsg)
        elif tit==self.gui_in_messages['error']:
            lev = int(parts[0])
            for p in parts[1:]:
                mymsg+=' '+str(p)
        # elif tit==self.gui_in_messages['sps']:
            # TODo was this an alarm?
            # self.flash_sps(str(parts[0]))
        if app["appName"]=='thetable':
            if tit==self.gui_in_messages['tablepos']:
                # FIXME
                # infinite value is not accepted by JSON, to be investigated
                app["posX"] = str(float(parts[0]))
                app["posY"] = str(float(parts[1]))
            elif tit==self.gui_in_messages['tablemoving']:
                app["status"] = "TAB_MOVING"
            elif tit==self.gui_in_messages['tabledone']:
                app["status"] = "TAB_DONE"
        elif tit==self.gui_in_messages['transfer']:
            if app["appName"]=='EB':
                for part in parts:
                    if part.find('=')<0:
                        continue
                    key,val=part.split('=')
                    app[key]=val
                    # if key=='badspills':
                    #     app[key]=int(val)
                    # elif key=='eventsmerged':
                    #     app[key]=int(val)
                    # elif key=='transferTime':
                    #     app[key]=val # in usec
                    # elif key=='transrate_size':
                    #     app[key]=val # in bytes
                    # elif key=='evinrun':
                    #     app[key]=val
                rate = float(app['transrate_size'])/1.048576/float(app['transferTime']) # MB/s
                app['spillsize']=round(float(app['transrate_size'])/1048576.,2) # MB
                app['transferRate']=round(rate,2)
                self.status['evinrun'] = app['evinrun']
        elif tit==self.gui_in_messages['spillduration']:
            if app["appName"]=='RC':
                for part in parts:
                    if part.find('=')<0:
                        continue
                    key,val=part.split('=')
                    if key=='runnumber' and app[key]!=int(val):
                        break
                    if key=='spillnumber' and app[key]!=int(val):
                        break
                    if key=='spillduration':
                        app[key]=round(float(val)/1000000.,2) # in seconds
                        if val!=0:
                            app['trigrate']=round(float(app["evinspill"])/app[key],2)
                        else:
                            app['trigrate']=0

# TODO check when applications go to stop by themselves
    # def send_stop_pause_messages(self):
    #    rc=self.remote[('statuscode','RC')]
    #    if rc in self.remotestatuses_running:
    #     if self.wanttostop:
    #         self.stoprun()
    #     elif self.wanttopause:
    #         self.pauserun()

    # def processrccommand(self,command):
    #     # Look for RC app
    #     RC_app = None
    #     for app in self.appsList:
    #         if app["appName"] == 'RC':
    #             RC_app = app
    #     if RC_app['status'] == 'paused':
    #         self.gotostatus('PAUSED')
    #     elif RC_app['statuscode'] in self.remotestatuses_stopped:
    #         if self.status['localstatus'] in ['RUNNING','PAUSED']:
    #             self.gotostatus('STOPPED')
        # TODO this was only a noisy print
        # else:
        #     self.gotostatus('RUNNING')
        # if RC_app['statuscode']==self.remotestatus_endofspill:
        #     if (self.autostop_max_events > 0) and (int(self.status['evinrun']) > int(self.autostop_max_events)):
        #         print(self.status['evinrun'],self.autostop_max_events)
                # TODO: define stop action
                #self.on_stopbutton_clicked()

    # def gotostatus(self,newstatus):
    #     print("[AppControl][gotostatus] Going to status", newstatus)

    def stop_network(self):
        self.poll_sockets_running = False

    # Prepare the information about the apps to be published online
    def getAppsUpdate(self):
        simplified_list = []
        for app in self.appsList:
            appCopy = copy.deepcopy(app)
            appCopy.pop('socket', None)
            simplified_list.append(appCopy)
        return simplified_list

    def pauseApps(self):
        self.send_message(self.gui_out_messages['pauserun'])

    def resumeApps(self):
        self.send_message(self.gui_out_messages['restartrun'])

    def stopApps(self):
        self.send_message(self.gui_out_messages['stoprun'])
        self.run_registry.logRunStop()

    def closeApps(self):
        print('closeApps -- SENDING DIE MESSAGE')
        self.send_message(self.gui_out_messages['die'])

    def runApps(self, run):
        self.send_message(str(' ').join([str(self.gui_out_messages['startrun']),str(run._id),str(run.runType),str(run.eventsPerSpill)]))
        self.run_registry.logRunStart(run._id, trigtype=run.runType, campaign=run.tbCamp)
        
    def areAppsRunning(self):
        running = True
        for app in self.appsList:
            # we do not want to ckeck the table for changing the run status
            # otherwise if the table has a problem the run is blocked
            if app["appName"] == 'thetable' or app["appName"] == 'triggerapp':
                continue
            elif 'DRCV' in app["appName"]:
                if app["status"] == 'RECVBUFFER' and app["status"] == 'SENTBUFFER':
                    continue
            elif app["status"] != 'DATATAKING' and app["status"] != 'CLEARED':
            # elif self.rsdictReverse[app["status"]] in self.remotestatuses_running:
                running = False
        return running

    def areAppsStopped(self):
        stop = True
        for app in self.appsList:
            if app["appName"] == 'thetable' or app["appName"] == 'triggerapp':
                continue
            elif 'DRCV' in app["appName"]:
                if app["status"] != 'RECVBUFFER':
                    stop = False
            elif app["status"] != 'INITIALIZED' and app["status"] != 'CLEARED':
            # elif self.rsdictReverse[app["status"]] in self.remotestatuses_stopped:
                stop = False
        return stop

    def isTableDone(self):
        for app in self.appsList:
            if app["appName"] == 'thetable':
                if app['status'] == 'TAB_DONE':
                    return True
                else:
                    return False    

    def moveTable(self, position):
        newx = max(float(position['tableX']), 0.)
        newy = max(float(position['tableY']), 0.)
        print('Moving Table: ', newx, newy)
        self.pub.send_string('SET_TABLE_POSITION %s %s' % (newx,newy,))

    def sendTriggerUpdate(self, params):
            # Expected channelList like:
            # [{u'Delay': u'13000', u'Gate': u'1234', u'Type': u'ControlSig', u'ID': u'0', u'Port': u'7'}, {u'Delay': u'1', u'Gate': u'2000', u'Type': u'TriggerInput', u'ID': u'1', u'Port': u'6'}, {u'Delay': u'200', u'Gate': u'1001', u'Type': u'TriggerOutput', u'ID': u'2', u'Port': u'0'}]
            cmd = "GUI_GDG "
            cmd += "," + "selfTriggerEnabled" + ":" + str(params['selfTriggerEnabled'])
            cmd += "," + "stDowntime" + ":" + str(params['stDowntime'])
            cmd += "," + "stUptime" + ":" + str(params['stUptime'])
            channelList = params['channelList']
            print("selfTriggerEnabled=1", "GUI_GDG", channelList)
            for channel in channelList:
                if channel['Type'] != "TriggerInput":
                    cmd += "," + "ID" + ":" + channel['ID']
                    cmd += "," + "Type" + ":" + channel['Type']
                    cmd += "," + "Port" + ":" + channel['Port']
                    cmd += "," + "Gate" + ":" + channel['Gate']
                    cmd += "," + "Delay" + ":" + channel['Delay']
            print("Sending command to update trigger board DT_5495")
            print(cmd)
            self.pub.send_string(cmd)


    def checkDRCVs(self):
        for app in self.appsList:
            if int(time.time()) - app["timestamp"] > 10:
                # restart DRCV if dead during run
                onlyFileName = app["fileName"][ app["fileName"].rfind("/")+1:]
                # Get machine name from file
                machineName = app["hostName"] + ".cern.ch"

                # If the service has the initcmd defined we use that one instead of /bin/blabla
                initCommand = self.getInitCmd(app["fileName"])

                command = ""
                command += "ssh cmsdaq@"+machineName+" '"
                if initCommand != "":
                    command += initCommand
                else:
                    command += self.launchCommands["DRCV"]

                command += " -d -c " + app["fileName"]
                command += " -v 3 -l " + app["logFile"]
                command += " > /tmp/H4/log_h4daq_start_"+app["appName"]+"_"+onlyFileName[7:-4]+"_"+str(int(time.time()))+".log"
                command += "' 2>&1 | tee  /tmp/H4/log_h4daq_update_"+app["appName"]+"_"+onlyFileName[7:-4]+"_"+str(int(time.time()))+".log"

                subprocess.call(command, shell=True)
                
                p = subprocess.Popen(('ssh', "cmsdaq@"+machineName, " pgrep -f "+ app["fileName"]), shell=False, stdout=subprocess.PIPE, close_fds=True)
            
                # We should react in case pid is missing
                lines=p.stdout.readlines()
                if len(lines) == 2:
                    app["pid"] = int(lines[1][:-1])
                    print("[AppControl][getAppsPid] Pid", app["pid"], "found for app", app["appName"], "on machine", app["hostName"])
                elif len(lines) == 1:
                    app["pid"] = int(lines[0][:-1])
                    print("[AppControl][getAppsPid] Pid", app["pid"], "found for app", app["appName"], "on machine", app["hostName"])

    def isError(self):
        for app in self.appsList:
            if not 'DRCV' in app["appName"]:
                if app["status"] == "ERROR":
                    return True
        return False
    
    def isStep(self):
        for app in self.appsList:
            if not 'DRCV' in app["appName"]:
                if app["status"] == "STEP":
                    return True
        return False
