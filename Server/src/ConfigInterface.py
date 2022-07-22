import json
import copy
import subprocess
from bs4 import BeautifulSoup as Soup
import time
import socket
import sys

class ConfigInterface:

    def __init__(self, newDbInterface):
        self.dbInterface = newDbInterface
        self.sConfigTag = None
        self.sConfigVer = None
        self.runKeyTag = None
        self.runKeyVer = None
        self.DRsList = []
        self.scan_params = None
        self.inputList = None
        self.selfTriggerEnabled = 0
        self.stDowntime = 0
        # List of services extracted from Services Configuration table
        self.machines_services_db = []
        # List of services from Service Configuration table && selected DR in GUI
        self.machines_services = []

        self.base_path = "/tmp/H4/"
        self.tag_path = ""
    def getDRsList(self,scTag,scVer):
        print(scTag,scVer)
        services_config = self.dbInterface.getSCbyTagbyVer(scTag,scVer)
        DRsList = []
        if services_config == None:
          return DRsList
        try:
            machines_services = json.loads(services_config["machines"])
        except:
            print("Error Parsing the JSON file of the service configuration")
            return DRsList
        for service in machines_services["services"]:
            if "DR" in service["appname"]:
                button_label = service["appname"] + "-" + service["hostname"]
                if "crateId" in service:
                    button_label = button_label + "-"
                    button_label = button_label + str(service["crateId"])
                DRsList.append(button_label)
        print("Returning")
        return DRsList

    def getInputListAndTrigger(self,rkTag,rkVer):
        if self.inputList!=None:
            return self.inputList, self.stDowntime
        inputList = []
        selfTriggerEnabled = 0
        stDowntime = 0
        runkey_config = self.dbInterface.getRKbyTagbyVer(rkTag,rkVer)
        if "rc" in runkey_config:
            acTag = "RC"
            acVer = runkey_config["rc"]
            app_config = self.dbInterface.getAppConfigByVersion(acTag,acVer)
            print("App config: ",app_config)
            if app_config == None:
                return inputList, stDowntime
            try:
                soup = Soup(app_config["conf"], "xml")
            except:
                print("Error Parsing the XML file of the service configuration")
                return inputList, stDowntime
            for board in soup.find_all("board"):
                for board_type in board.find_all("type"):
                    if board_type.string == "CAEN_DT5495":
                        for tag in board.find_all("Channel"):
                            for ID in tag.find_all("ID"):
                                inputList.append(ID.string)
                        for tag in soup.find_all("selfTriggerEnabled"):
                            selfTriggerEnabled = int(tag.string)
                            if selfTriggerEnabled:
                                for tag in soup.find_all("stDowntime"):
                                    stDowntime = int(tag.string)
            print("XML Port List: ", soup.find_all("ID"), "Returned Inputs List: ", inputList)
            print("Returning")
        return inputList, stDowntime

    def prepareConfiguration(self,params):
        print("[RunControl][configure] Configuration params:")
        print("[RunControl][configure] Services Configuration:", params['scTag'], "version", params['scVer'])
        print("[RunControl][configure] Run Key Configuration:", params['rkTag'], "version", params['rkVer'])
        print("[RunControl][configure] DRs chosen:", params['activeDRs'])
        print("[RunControl][configure] Inputs chosen:", params['activeInputs'])
        self.sConfigTag =  params['scTag']
        self.sConfigVer = params['scVer']
        self.runKeyTag = params['rkTag']
        self.runKeyVer = params['rkVer']
        self.DRsList = params['activeDRs']
        self.inputList = params['activeInputs']
        services_config = self.dbInterface.getSCbyTagbyVer(self.sConfigTag,self.sConfigVer)
        self.machines_services_db = json.loads(services_config["machines"])
        new_services_config = []
        # Remove DRs deactivated from GUI
        print("services in DB: ", self.machines_services_db)
        for service in self.machines_services_db["services"]:
            if "DR" in service["appname"]:
                print("DR :" + service["appname"])
                createdName =  service["appname"] + "-" + service["hostname"]
                print("created name: ", createdName)
                if "crateId" in service:
                    createdName = createdName + "-"
                    createdName = createdName + str(service["crateId"])
                    print(" created name - edit: ", createdName)
                for activeDR in self.DRsList:
                    if activeDR == createdName:
                        print("Active in DR:", service)
                        new_services_config.append(service)
            else:
                new_services_config.append(service)

        self.machines_services = copy.deepcopy(new_services_config)
        print("====================================================")
        print("Final list of services:")
        for service in self.machines_services:
            print("Application:",service["appname"],"on",service["hostname"])
        print("====================================================")

        run_key = self.dbInterface.getRKbyTagbyVer(self.runKeyTag,self.runKeyVer)

        # create Folders + empty it
        return_code = self.createConfigFolder()
        if return_code:
            raise Exception("Error creating configuration folder")
        print("Temp folder for configuration files created!")

        # create files with name from list of services and fill them
        return_code = self.createConfigFiles(run_key)
        if return_code:
            raise Exception("Error creating configuration files")
        print("Configuration files created in temp folder!")

        # distribute XML folder all over the machines
        # move only required config files or the full folder?
        return_code = self.distributeConfigFiles()
        if return_code:
            raise Exception("Error moving configuration files on other machines")
        print("Configuration files copied on the other machines!")


    def createConfigFolder(self):
        self.tag_path = self.base_path + self.sConfigTag + '_' + str(int(time.time()))
        print("TAG PATH: ", self.tag_path)
        subprocess.call("rm "+self.base_path+"latest", shell=True)
        return_code = subprocess.call("mkdir -p "+self.tag_path, shell=True)
        if return_code:
            return_code = subprocess.call("rm -rf "+self.tag_path, shell=True)
            return_code = subprocess.call("mkdir -p "+self.tag_path, shell=True)
            subprocess.call("rm "+self.base_path+"latest", shell=True)
            time.sleep(1)
        return_code += subprocess.call("ln -s "+self.tag_path+" "+self.base_path+"latest", shell=True)
        return return_code

    def createConfigFiles(self, run_key):

        return_code = 0
        # check if EB and RC exist
        RC_present = False
        EB_present = False
        for service in self.machines_services:
            if service["appname"] == "RC":
                RC_present = True
            if service["appname"] == "EB":
                EB_present = True
        print(self.machines_services)
        if not RC_present or not EB_present:
            print("Missing EB or RC in the list of services. Something wrong! Or it is done on purpose?")
            # We don't need to raise an error... a warning should be shown in the GUI 


        # Creating networks
        # extended_services contains also the network connections details for each application
        extended_services = self.createNetworkMap(self.machines_services)
        self.machines_services = copy.deepcopy(extended_services)
        # Counters required for the config files of EB and RC
        DRs_number_for_RC = 0
        events_number_for_EB = 1
        for service in extended_services:
            # if service["appname"] == "DR":
            if "DR_" in service["appname"]:
                if not ("noRCConnect" in service.keys() and service["noRCConnect"]):
                    DRs_number_for_RC = DRs_number_for_RC + 1
                if not ("noEBConnect" in service.keys() and service["noEBConnect"]):
                    events_number_for_EB = events_number_for_EB + 1
        for service in extended_services:
            file_name = "config_" + service["hostname"] + "_" + service["appname"] + "_" + str(service["localNet"]["status"]) + ".xml"
            file_path = self.tag_path+"/"+file_name
            # Temporary trick. The host name in the configuration is used both to
            # create the file name and the ConnectTo tags in the xml
            # But the file name doesn't use .cern.ch while ConnectTo requires it.
            new_file_path = file_path.replace(".cern.ch","")

            return_code += subprocess.call("touch "+new_file_path, shell=True)
            if return_code:
                break
            print(run_key)
            print(service["appname"].lower())
            if service["appname"].lower() not in run_key:
            #if service["appname"] not in run_key:
                print("Application", service["appname"], "missing in the chosen run key version. Check the configuration!")
                return 1
            app_version = run_key[service["appname"].lower()]
            app_config = self.dbInterface.getAppConfigByVersion(service["appname"],app_version)
            soup = Soup(app_config["conf"], "xml")
            for key,value in service.items():
#TODO - check the ors(should be ands?)
                if key != "appname" or key != "hostname" or key != "localNet" or key != "externalNet":
                    for tag in soup.findAll(key):
                        tag.string = str(value)
                if key == "initcmd":
                    service['initcmd'] = value
            if service["appname"] == "RC":
                for tag in soup.findAll("waitForDR"):
                    tag.string = str(DRs_number_for_RC)
            if service["appname"] == "EB":
                for tag in soup.findAll("recvEvent"):
                    tag.string = str(events_number_for_EB)
            if service["appname"] == "DR_VFE":
                if "crateId" not in service.keys():
                    print("Invalid configuration: no crateId specified for VFE")
                    return 1
                for tag in soup.findAll("Device"):
                    tag.string = "vice.udp."+str(service["crateId"])
                for tag in soup.findAll("dumpDirName"):
                    tag.string = "/tmp/raw/dr"+str(service["crateId"])+"/"
                for board in soup.findAll("board"):
                    if "ECAL" in board.type.string:
                        board.ID.string = str(service["crateId"])
            # Adding the network parameters to the xml
            for tag in soup.findAll("Network"):
                for localport in "data", "status", "cmd":
                    new_tag = soup.new_tag("ListenPort")
                    new_tag.append(str(service["localNet"][localport]))
                    print(new_tag)
                    tag.append(new_tag)
                for externalport in service["externalNet"]:
                    new_tag = soup.new_tag("ConnectTo")
                    new_tag.append(str(externalport))
                    tag.append(new_tag)
            
            scan_tag = soup.find(scan='1')
            if scan_tag != None:
                # If True it means that it is still the first time you configure a scan run
                # or it is not a scan run at all, so we check if there is scan in attributes of the xml 
                if self.scan_params == None: 
                    print("Found a tag requiring a scan")
                    print("TAG WITH SCAN=1",scan_tag)
                    attr_dict = scan_tag.attrs
                    if 'steps' in attr_dict and 'delta' in attr_dict:
                        self.scan_params = {}
                        self.scan_params['scan_steps'] = attr_dict['steps']
                        self.scan_params['scan_delta'] = attr_dict['delta']
                        self.scan_params['scan_name'] = scan_tag.name
                        self.scan_params['scan_starting_val'] = scan_tag.string
                        print(self.scan_params)
                    else:
                        print("steps or/and delta attributes are missing. Correct the configuration and retry. meanwhile starting normal run...")
                # If False it means that there as been already at least one step of a scan run 
                # In this case we need to increase the parameter of the scan
                else:
                    newValue = float(self.scan_params['scan_starting_val'])
                    delta = float(self.scan_params['scan_delta'])
                    newValue = newValue + delta
                    # we update the val of the parameter to scan in case there is an other step ahead of us
                    self.scan_params['scan_starting_val'] = newValue
                    if scan_tag.name == self.scan_params['scan_name']:
                        scan_tag.string = str(newValue)
            # Removing unused ports
            if service["appname"] == "RC":
                self.removeGuiDisabledPort(soup)
                self.saveSelfTriggerInfo(soup)
            f = open(new_file_path, 'w')
            f.write(str(soup))
            f.close()
        # Create description file
        file_path = self.tag_path+"/config_version.jsn"
        config_version = {}
        config_version["services_tag"] = self.sConfigTag
        config_version["services_ver"] = self.sConfigVer
        config_version["runkey_tag"] = self.runKeyTag
        config_version["runkey_ver"] = self.runKeyVer
        config_version["DR_list"] = self.DRsList
        with open(file_path, 'w') as fp:
            json.dump(config_version, fp)
        return return_code

    def distributeConfigFiles(self):

        gui_hostname = socket.gethostname()

        all_machines = []
        for service in self.machines_services:
            all_machines.append(service["hostname"])
        list_of_machines = set(all_machines)
        return_code = 0
        for machine in list_of_machines:
            if gui_hostname in machine:
                continue
            subprocess.call("ssh cmsdaq@"+machine+" mkdir "+self.base_path, shell=True)
            copy_string = "scp -r "+self.tag_path+" cmsdaq@"+machine+":"+self.base_path
            return_code += subprocess.call(copy_string, shell=True)
            subprocess.call("ssh cmsdaq@"+machine+" rm "+self.base_path+"latest", shell=True)
            time.sleep(1)
            return_code += subprocess.call("ssh cmsdaq@"+machine+" ln -s "+self.tag_path+" "+self.base_path+"latest", shell=True)
        return return_code
    
    # Remove the unused trigger ports from the xml before writing it on file
    def removeGuiDisabledPort(self, soup):
        for tag in soup.findAll("Channel"):
            for idtag in tag.findAll("ID"):
                found = False
                print("Printing ===============================================================================================================")
                print(idtag.text)
                print(self.inputList)
                for channel in self.inputList:
                    if channel == idtag.text:
                        found = True
                if not found:
                    print("Channel to remove ID:", idtag.text)
                    tag.decompose()

    #TODO not very useful at the moment. selfTriggerEnabled and stDowntime are already defined
    # But it can be used to modify the two values if the GUI allows that before the configuration action.
    def saveSelfTriggerInfo(self, soup):
        for tag in soup.find_all("selfTriggerEnabled"):
            self.selfTriggerEnabled = int(tag.string)
        if self.selfTriggerEnabled:
            for tag in soup.find_all("stDowntime"):
                self.stDowntime = int(tag.string)

    # Create the network map from the configuration of the services
    def createNetworkMap(self, sconf):
        services = copy.deepcopy(sconf)
        print("services")
        list_of_machines = {}
        # data: channel where data are produced and EB can obtain them
        # status: channel read by the GUI to get application status
        # cmd: channel used to receive commands from RC
        for service in services:
            list_of_machines[service["hostname"]] = {'data':0,'status':0,'cmd':0}

        # Inserting services and local ports in network map
        for service in services:
            service["localNet"]=copy.deepcopy(self.getLocalPorts(list_of_machines,service["hostname"]))

        rc_i = None
        eb_i = None

        for service in services:
            if service["appname"] == "RC":
                rc_i = services.index(service)
            elif service["appname"] == "EB":
                eb_i = services.index(service)
            service['externalNet'] = []

        # Adding external ports in the network map
        for service in services:
            if "DRCV" in service["appname"]:
                if "connectTo" in service.keys():
                    for other_service in services:
                        if other_service["name"] == service["connectTo"]:                            
                            service['externalNet'].append(other_service['hostname']+":"+str(other_service['localNet']['data']))
                            break
                else:
                    # Generally all the applications send data to the EB
                    service['externalNet'].append(services[eb_i]['hostname']+":"+str(services[eb_i]['localNet']['data']))
            if service["appname"] != "RC":
                if not ("noRCConnect" in service.keys() and service["noRCConnect"]):
                    # RC has to know the cmd channel of each application if:
                    # - it is not an RC
                    # - in the service config there isn't 'noRCConnect: 1' specified
                    services[rc_i]['externalNet'].append(service["hostname"]+":"+str(service["localNet"]['cmd']))
            if service["appname"] != "EB" and "DRCV" not in service["appname"]:
                if not ("noEBConnect" in service.keys() and service["noEBConnect"]):
                    # EB has to know the data channel of each application if:
                    # - it is not an EB
                    # - it is not a DRCV
                    # - in the service config there isn't 'noEBConnect: 1' specified
                    services[eb_i]['externalNet'].append(service["hostname"]+":"+str(service["localNet"]['data']))
            if service["appname"] != "RC" and service["appname"] != "EB":
                if not ("noRCConnect" in service.keys() and service["noRCConnect"]):
                    # Generally all the applications listen to commands coming from RC
                    service['externalNet'].append(services[rc_i]['hostname']+":"+str(services[rc_i]['localNet']['cmd']))
                
            # all applications are connected to emergency command channel
            service['externalNet'].append(socket.gethostname()+":5567") # Emergency CML

            # If the application in the service config list has the key controlledByGUI = 1
            # the application will be connected to the GUI command port.
            # In its software the application has to subscribe to this port.
            # The RC doesn't need it because it is controlled by GUI by default
            if service.get("controlledByGUI",0):
                service['externalNet'].append(socket.gethostname()+":5566") # GUI

        # Adding standard ports
        if rc_i != None:
            # RC listens to commands coming from GUI
            services[rc_i]['externalNet'].append(socket.gethostname()+":5566") # GUI
        if eb_i != None:
            # EB listens to commands coming from RC
            services[eb_i]['externalNet'].append(services[rc_i]['hostname']+":"+str(services[rc_i]['localNet']['cmd'])) 

        print("##########################")
        for service in services:
            print(service["appname"],service["hostname"],service["localNet"],service["externalNet"])

        return services

    def getLocalPorts(self,machines,hostname):
        if machines[hostname]['data'] == 0:
             machines[hostname] = {'data':7000,'status':7002,'cmd':7004}
             return machines[hostname]
        else:
            machines[hostname]['data'] = machines[hostname]['data']+10
            machines[hostname]['status'] = machines[hostname]['status']+10
            machines[hostname]['cmd'] = machines[hostname]['cmd']+10
            return machines[hostname]

    # Look for the last run saved on the database,
    # and initialize config interface class with
    # the retrieved configuration
    def loadLastConfiguration(self, lastRun):
        if lastRun != None:
            self.sConfigTag = lastRun["scTag"]
            self.sConfigVer = lastRun["scVer"]
            self.runKeyTag = lastRun["rkTag"]
            self.runKeyVer = lastRun["rkVer"]
            self.DRsList = lastRun["activeDRs"]
