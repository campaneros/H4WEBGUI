from pymongo import MongoClient, DESCENDING
import socket
import copy
import json

class DBGUIInterface:

    def __init__(self):
        self.client = MongoClient('mongodb://localhost:27017/')
        self.db = self.client['test']
        self.SConfigs = self.db['services_configs']
        self.RunKeys = self.db['run_keys']
        self.AppConfigs = self.db['apps_configs']
        self.TablePos = self.db['table_pos']
        self.TbCamp = self.db['tb_camps']
        if not 'runs_infos' in self.db.collection_names():
            self.db.create_collection('runs_infos')
        self.RunInfos = self.db['runs_infos']
        self.PSconfigs = self.db['power_supply_configs']

    def getSConfigsTagsList(self):
        return self.SConfigs.distinct("tag")

    def getRunKeysTagsList(self):
        return self.RunKeys.distinct("tag")

    def getSConfigsVersList(self,mytag):
        firstList = self.SConfigs.find({"tag": mytag}, {"v":1,"_id":0})
        sortedList = []
        for ver in firstList:
            sortedList.append(ver["v"])
        sortedList.sort()
        reversList = sortedList[::-1]
        return reversList

    def getRunKeysVersList(self,mytag):
        firstList = self.RunKeys.find({"tag": mytag}, {"v":1,"_id":0})
        sortedList = []
        for ver in firstList:
            sortedList.append(ver["v"])
        sortedList.sort()
        reversList = sortedList[::-1]
        return reversList

    def getRKmaxTag(self,mytag):
        for post in self.RunKeys.aggregate([{ "$sort": { "v": -1 } },{ "$match": { "tag": mytag }},{ "$group": { "_id": "$tag", "v": { "$first": "$v" } } }]):
            singleRow = post
        return self.RunKeys.find_one({"tag": mytag, "v": singleRow["v"]})

    def getRKbyTagbyVer(self,mytag,myver):
        runkey = self.RunKeys.find_one({"tag": mytag, "v": int(myver)})
        if "applications" in runkey:
            return json.loads(runkey["applications"])
        return runkey

    def getSCmaxTag(self,mytag):
        for post in self.SConfigs.aggregate([{ "$sort": { "v": -1 } },{ "$match": { "tag": mytag }},{ "$group": { "_id": "$tag", "v": { "$first": "$v" } } }]):
            singleRow = post
        return self.SConfigs.find_one({"tag": mytag, "v": singleRow["v"]})

    def getSCbyTagbyVer(self,mytag,myver):
        return self.SConfigs.find_one({"tag": mytag, "v": int(myver)})

    def getAppConfigByVersion(self,appname,appversion):
        return self.AppConfigs.find_one({"appl": appname, "v": appversion})

    def getLocalPorts(self,machines,hostname):
        if machines[hostname]['data'] == 0:
             machines[hostname] = {'data':7000,'status':7002,'cmd':7004}
             return machines[hostname]
        else:
            machines[hostname]['data'] = machines[hostname]['data']+10
            machines[hostname]['status'] = machines[hostname]['status']+10
            machines[hostname]['cmd'] = machines[hostname]['cmd']+10
            return machines[hostname]

    def getLastRunNumber(self):
        result = self.RunInfos.find_one(sort=[("_id", -1)])
        if result == None:
            return 0 
        else:
            return result["_id"]

    def getLastRun(self):
        return self.RunInfos.find_one(sort=[("_id", -1)])

    def saveRun(self,run):
        # Activate following line to write the run on DB
        run['beamEnergy'] = float(run['beamEnergy'])
        run['evinrun'] = float(run['evinrun'])
        run['tableX'] = float(run['tableX'])
        run['tableY'] = float(run['tableY'])
        self.RunInfos.insert_one(run)

    def getTablePosTagsList(self):
        return self.TablePos.distinct("tag")

    def getTbCampList(self):
        return self.TbCamp.find({"open": True}).distinct("tag")


    ### Interface with Power Supply Settings    
    def getTablePosList(self, mytag):
        for post in self.TablePos.aggregate([{ "$sort": { "v": -1 } },{ "$match": { "tag": mytag }},{ "$group": { "_id": "$tag", "v": { "$first": "$v" } } }]):
            singleRow = post
        return json.loads(self.TablePos.find_one({"tag": mytag, "v": singleRow["v"]})['pos'])

    def getPSTagsList(self):
        return self.PSconfigs.distinct("tag")

    def getPSVersList(self,mytag):
        firstList = self.PSconfigs.find({"tag": mytag}, {"v":1,"_id":0})
        sortedList = []
        for ver in firstList:
            sortedList.append(ver["v"])
        sortedList.sort()
        reversList = sortedList[::-1]
        return reversList

    def getVISettings(self, mytag, myver):
        print(mytag, myver)
        settings = self.PSconfigs.find({"tag":mytag, "v":int(myver)})
        s = settings[0]
        VIsetList = [ s["V1"], s["V2"], s["V3"], s["V4"], s['I1'], s['I2'], s['I3'], s['I4'] ]
        return VIsetList
