from flask import Blueprint, jsonify, current_app
from src.RunControl import RunControl
from flask_socketio import emit, join_room, leave_room
from flask import request
from . import socketio
import time
import logging
from bs4 import BeautifulSoup as Soup
from src.MovingTable import MovingTable

pw_address = "128.141.147.80::5035"
rc_router = Blueprint("rc_router", __name__)
run_control = RunControl(socketio, logging.INFO)
moving_table = MovingTable(socketio, logging.INFO)
res = None

clients = 0
@socketio.on("connect", namespace="/")
def connect():
    global clients
    clients += 1
    print("CLIENTS ", clients)
    socketio.emit('updateSockets', {"clients": clients})

@socketio.on("disconnect", namespace="/")
def disconnect():
    global clients
    clients -= 1
    print("CLIENTS ", clients)
    socketio.emit('updateSockets', {"clients": clients})

### ACTIONS ###

@rc_router.route('/actions/initialize',methods=['POST'])
def initialize():
    result, msg = run_control.initialize()
    socketio.emit('updateAll')
    return jsonify({"newstate":result, "msg":msg})

@rc_router.route('/actions/configure',methods=['POST'])
def configure():
    params = request.get_json(force=True)
    result, msg = run_control.configure(params)
    socketio.emit('updateAll')
    return jsonify({"newstate":result, "msg":msg})

@rc_router.route('/actions/start',methods=['POST'])
def start():
    params = request.get_json(force=True)
    result, msg = run_control.start(params)
    socketio.emit('updateAll')
    return jsonify({"newstate":result, "msg":msg})

@rc_router.route('/actions/stop',methods=['POST'])
def stop():
    result, msg = run_control.stop()
    socketio.emit('updateAll')
    return jsonify({"newstate":result, "msg":msg})

@rc_router.route('/actions/pause',methods=['POST'])
def pause():
    result, msg = run_control.pause()
    socketio.emit('updateAll')
    return jsonify({"newstate":result, "msg":msg})

@rc_router.route('/actions/resume',methods=['POST'])
def resume():
    result, msg = run_control.resume()
    socketio.emit('updateAll')
    return jsonify({"newstate":result, "msg":msg})

### END ACTIONS ###

### Configuration buttons ###

@rc_router.route('/getSConfigsTagsList')
def getSConfigsTagsList():
    sconfigsTagsList = run_control.getSConfigsTagsList()
    return jsonify({"sconfigsTagsList":sconfigsTagsList, "msg":"SConfigs Tags List retrieved from DB"})

@rc_router.route('/getSConfigsVersList',methods=['POST'])
def getSConfigsVersList():
    params = request.get_json(force=True)
    sconfigsVersList = run_control.getSConfigsVersList(params['tag'])
    return jsonify({"sconfigsVersList":sconfigsVersList, "msg":"SConfigs Vers List retrieved from DB"})

@rc_router.route('/getRunKeysTagsList')
def getRunKeysTagsList():
    runkeysTagsList = run_control.getRunKeysTagsList()
    return jsonify({"runkeysTagsList":runkeysTagsList, "msg":"RunKeys Tags List retrieved from DB"})

@rc_router.route('/getRunKeysVersList',methods=['POST'])
def getRunKeysVersList():
    params = request.get_json(force=True)
    runkeysVersList = run_control.getRunKeysVersList(params['tag'])
    return jsonify({"runkeysVersList":runkeysVersList, "msg":"RunKeys Vers List retrieved from DB"})

@rc_router.route('/getDRsList',methods=['POST'])
def getDRsList():
    params = request.get_json(force=True)
    DRsList = run_control.getDRsList(params['scTag'],params['scVer'])
    return jsonify({"DRsList":DRsList, "msg":"DR List retrieved from the configuration"})

@rc_router.route('/getInputList',methods=['POST'])
def getInputList():
    params = request.get_json(force=True)
    inputList, stDowntime = run_control.getInputListAndTrigger(params['rkTag'],params['rkVer'])
    return jsonify({"InputList":inputList, "stDowntime": stDowntime, "msg":"Input List retrieved from the configuration"})

@rc_router.route('/getTablePosTagsList')
def getTablePosTagsList():
    tablePosTagsList = run_control.getTablePosTagsList()
    return jsonify({"tablePosTagsList":tablePosTagsList, "msg":"TablePos Tags List retrieved from DB"})

@rc_router.route('/getTablePosList',methods=['POST'])
def getTablePosList():
    params = request.get_json(force=True)
    tablePosList = run_control.getTablePosList(params['tag'])
    return jsonify({"tablePosList":tablePosList, "msg":"TablePos List retrieved from DB"})

@rc_router.route('/getTbCampList')
def getTbCampList():
    tbCampList = run_control.getTbCampList()
    return jsonify({"tbCampList":tbCampList, "msg":"TB Camp Tags List retrieved from DB"})


### End Configuration buttons ###

@rc_router.route('/getfsm')
def getfsm():
    return jsonify({"states":run_control.fsm.states, "actions":run_control.fsm.actions})

@rc_router.route('/updateAll')
def updateAll():
    jsonFromRunControl = run_control.getJsonUpdateAll()
    jsonFromRunControl['completeh4setup'] = current_app.config['H4SETUP']
    return jsonify(jsonFromRunControl)

@rc_router.route('/updateApps')
def updateApps():
    return jsonify(run_control.getJsonUpdateApps())

@rc_router.route('/updateLog')
def updateLog():
    return jsonify(run_control.log_capture_string.getvalue())

@rc_router.route('/moveTable',methods=['POST'])
def moveTable():
    params = request.get_json(force=True)
    msg = run_control.moveTable(params)
    socketio.emit('updateAll')
    return jsonify({"msg":msg}) 

@rc_router.route('/reset')
def reset():
    print("Resetting GUI...")
    type = request.args.get("type")
    if run_control.apps_control != None:
      run_control.apps_control.closeApps()
      time.sleep(5)
      # Wait for closing apps properly then kill them in case they are still running
      run_control.apps_control.stop_network()
      run_control.apps_control.findAndKillOldApps()
      print("Waiting after killing apps")
      time.sleep(5)
    # check on number of restart is already done in getJsonUpdateApps
    if type == "auto" and run_control.autorestart:
        # if it is a scan run we save the parameters of the scan
        scan_params = None
        if run_control.scan_run:
            scan_params = run_control.config_interface.scan_params
        run_control.reset()
        socketio.emit('updateAll')
        run_control.initialize()
        # Ater initialize() config_interface is initialized again and we can copy
        # there the scan_params of the last run. scan_params can be None if the last
        # run was not configured as scan run.
        run_control.config_interface.scan_params = scan_params
        socketio.emit('updateAll')
        # building params for configure action
        configure_params = {}
        configure_params["scTag"] =  run_control.config_interface.sConfigTag
        configure_params["scVer"] =  run_control.config_interface.sConfigVer
        configure_params["rkTag"] =  run_control.config_interface.runKeyTag
        configure_params["rkVer"] =  run_control.config_interface.runKeyVer
        configure_params["activeDRs"] =  run_control.config_interface.DRsList
        configure_params["activeInputs"] =  run_control.config_interface.InputsList
        run_control.configure(configure_params)
        socketio.emit('updateAll')
        # building params for start action
        start_params = {}
        start_params["eventsPerSpill"] = run_control.lastRunTemp["eventsPerSpill"]
        start_params["beamEnergy"] = run_control.lastRunTemp["beamEnergy"]
        start_params["runType"] = run_control.lastRunTemp["runType"]
        start_params["beamType"] = run_control.lastRunTemp["beamType"]
        start_params["tablePosTag"] = run_control.lastRunTemp["tablePosTag"]
        start_params["tablePos"] = run_control.lastRunTemp["tablePos"]
        start_params["tableX"] = run_control.lastRunTemp["tableX"]
        start_params["tableY"] = run_control.lastRunTemp["tableY"]
        run_control.start(start_params)
        run_control.autorestartcounter += 1
        run_control.logger.info("auto restart counter: " +  str(run_control.autorestartcounter))
        if run_control.scan_run:
            message = "step info: parameter "
            message += str(run_control.config_interface.scan_params['scan_name'])
            message += " value "
            message += str(run_control.config_interface.scan_params['scan_starting_val'])
            run_control.logger.info(message)
        socketio.emit('updateAll')
    else:
        # type == "manual" or run_control.autorestart == False
        run_control.__init__(socketio, logging.INFO)
    socketio.emit('reloadPage')
    #socketio.emit('updateAll')
    print("End resetting GUI...")
    return jsonify({"currentstate":run_control.fsm.state, "msg":run_control.logMessages})

@rc_router.route('/getTriggerOptions', methods=['GET'])
def getTriggerOptions():
    channelList = []
    selfTriggerEnabled = 0
    stDowntime = 0
    stUptime = 0
    if run_control.apps_control!=None:
        print('Apps update: ')
        print(run_control.apps_control.getAppsUpdate())
        appsUpdateList = run_control.apps_control.getAppsUpdate()
        for i in range(0,len(appsUpdateList)):
            if appsUpdateList[i]['appName']=='RC' and (appsUpdateList[i]['status'] in ['INITIALIZED','CONFIGURED']):
                print(appsUpdateList[i]['fileName'])
                if appsUpdateList[i]['fileName']!='':
                    with open(appsUpdateList[i]['fileName']) as xmlConfigFile:
                        contents = xmlConfigFile.read()
                        soup = Soup(contents, 'xml')
                        for board in soup.find_all("board"):
                            for board_type in board.find_all("type"):
                                if board_type.string == "CAEN_DT5495":
                                    for each_channel in soup.find_all('Channel'):
                                        channelParams = {child.name: child.text for child in each_channel.findChildren()}
                                        channelList.append(channelParams)
                                    for tag in soup.find_all("selfTriggerEnabled"):
                                        selfTriggerEnabled = int(tag.string)
                                    for tag in soup.find_all("stDowntime"):
                                        stDowntime = int(tag.string)
                                    for tag in soup.find_all("stUptime"):
                                        stUptime = int(tag.string)
                                    
    return jsonify({"channelList":channelList, "selfTriggerEnabled": selfTriggerEnabled, "stDowntime": stDowntime, "stUptime": stUptime})


@rc_router.route('/setTriggerOptions', methods=['POST'])
def setTriggerOptions():
    params = request.get_json(force=True)
    print("setting new trigger params", params)
    run_control.apps_control.sendTriggerUpdate(params)
    return jsonify({"msg": "Update request sent"})

@rc_router.route('/toggleAutoRestart', methods=['POST'])
def toggleAutoRestart():
    params = request.get_json(force=True)
    print("toggling autorestart: ", params['autorestart'])
    msg = run_control.setAutoRestart(params['autorestart'])
    socketio.emit('updateAll')
    return jsonify({"msg": msg})

@rc_router.route('/setLogLevel', methods=['POST'])
def selectLogLevel():
    params = request.get_json(force=True)
    print("selcting loglevel: ", params['logLevel'])
    msg = run_control.setLogTextLogLevel( params['logLevel'])
    return jsonify({"msg": msg})

@rc_router.route('/isCompleteGui', methods=['GET'])
def isCompleteGui():
    return jsonify({"isCompleteGui": current_app.config['H4SETUP']})


############### Section for power supply HMP4040 #############################
try:
    import HMP4040
    from .DBGuiInterface import DBGUIInterface
except ImportError:
    print("Python library to contorl HMP4040 has not been found! Disabling related functions...")
else:
    dbgui_interface = DBGUIInterface()
    @rc_router.route('/generalPowerON', methods=['POST'])
    def generalPowerON():
        print("Calling power on for all channels")

        params = request.get_json(force=True)
        VsetList = params["VsetList"]
        IsetList = params["IsetList"]

        print(VsetList,IsetList)
        
        global res
        if res == None:
            res = HMP4040.HMP4040(f"TCPIP0::{pw_address}::SOCKET",1000)

        print(VsetList[0],VsetList[1],VsetList[2],VsetList[3])
        res.setVoltage(VsetList[0], 1)
        res.setVoltage(VsetList[1], 2)
        res.setVoltage(VsetList[2], 3)
        res.setVoltage(VsetList[3], 4)

        res.setCurrent(IsetList[0], 1)
        res.setCurrent(IsetList[1], 2)
        res.setCurrent(IsetList[2], 3)
        res.setCurrent(IsetList[3], 4)
        
        time.sleep(1)
        res.activateOutput(1)
        time.sleep(1)
        res.activateOutput(2)
        time.sleep(1)
        res.activateOutput(3)
        time.sleep(1)
        res.activateOutput(4)

        # res = None

        return jsonify({"msg":'power ON'})

    @rc_router.route('/generalPowerOFF', methods=['GET'])
    def generalPowerOFF():
        print("Calling power OFF for all channels")

        global res
        if res == None:
            res = HMP4040.HMP4040(f"TCPIP0::{pw_address}::SOCKET",1000)

        res.deactivateOutput(1)
        time.sleep(1)
        res.deactivateOutput(2)
        time.sleep(1)
        res.deactivateOutput(3)
        time.sleep(1)
        res.deactivateOutput(4)
        
        # res = None

        return jsonify({"msg":'power OFF'})

    @rc_router.route('/powerOnChannel', methods=['POST'])
    def powerOnChannel():
        print("Power On selected channel")

        global res
        if res == None:
            res = HMP4040.HMP4040(f"TCPIP0::{pw_address}::SOCKET",1000)
    
        params = request.get_json(force=True)
        Ch = int(params['channel'])
        Vset = float(params['Vset'])
        Iset = float(params['Iset'])

        print("Ch: ", Ch, "Vset: ", Vset, "Iset: ",  Iset)
        res.setVoltage(Vset, Ch)
        res.setCurrent(Iset, Ch)
        time.sleep(1)
        res.activateOutput(Ch)
        
        # res = None

        return jsonify({"msg":'power ON channel'})

    @rc_router.route('/powerOffChannel', methods=['POST'])
    def powerOffChannel():

        global res
        if res == None:
            res = HMP4040.HMP4040(f"TCPIP0::{pw_address}::SOCKET",1000)
    
        params = request.get_json(force=True)
        Ch = int(params['channel'])
        print("Power Off Ch "+str(Ch))
        res.deactivateOutput(Ch)
        
        # res = None

        return jsonify({"msg":'power OFF channel '+str(Ch)})

    @rc_router.route('/readChannelV', methods=['GET'])
    def readChannelV():
        print("Reading Channels V/I...")

        global res
        if res == None:
            res = HMP4040.HMP4040(f"TCPIP0::{pw_address}::SOCKET",1000)

        Vch1 = res.measureVoltage(1)
        Vch2 = res.measureVoltage(2)
        Vch3 = res.measureVoltage(3)
        Vch4 = res.measureVoltage(4)

        Ich1 = res.measureCurrent(1)
        Ich2 = res.measureCurrent(2)
        Ich3 = res.measureCurrent(3)
        Ich4 = res.measureCurrent(4)

        ChStatusList = [None] * 4
        ChStatusList[0] = res.getChStatus(1)
        ChStatusList[1] = res.getChStatus(2)
        ChStatusList[2] = res.getChStatus(3)
        ChStatusList[3] = res.getChStatus(4)
        print("ch satus: ", ChStatusList)

        # res = None
        
        return jsonify({"voltageCh1":Vch1, 
                        "voltageCh2":Vch2, 
                        "voltageCh3":Vch3, 
                        "voltageCh4":Vch4,
                
                        "currentCh1":Ich1,
                        "currentCh2":Ich2,
                        "currentCh3":Ich3,
                        "currentCh4":Ich4,

                        "ChStatusList":ChStatusList
                    })

    @rc_router.route('/getPSTagsList', methods=['GET'])
    def getPSTagsList():
        psTagsList = dbgui_interface.getPSTagsList()
        return jsonify({"psTagsList":psTagsList, "msg":"PS configs Tags List retrieved from DB"})

    @rc_router.route('/getPSVersList', methods=['POST'])
    def getPSVersList():
        params = request.get_json(force=True)
        psVersList = dbgui_interface.getPSVersList(params['tag'])
        return jsonify({"psVersList":psVersList, "msg":"PS configs versions retrieved from DB"})

    @rc_router.route('/getVISettings', methods=['POST'])
    def getVISettings():
        params = request.get_json(force=True)
        VIsetList = dbgui_interface.getVISettings(params['tag'], params['ver'])
        VsetList = VIsetList[0:4]
        IsetList = VIsetList[4:8]
        for i,I in enumerate(IsetList):
            if I <= 0:
                IsetList[i] = 0.001
        return jsonify({"VsetList":VsetList, "IsetList":IsetList, "msg":"PS configs versions retrieved from DB"})
    
############### END Section for power supply HMP4040 #############################


############### Start Section for moving Big Table ##############################`L:
@rc_router.route('/moveBigTable',methods=['POST'])
def moveBigTable():
    params = request.get_json(force=True)
    print ("Moving Table Position ",params['tableX', 'tableY'])
    return jsonify({"msg":"ciao"})

@rc_router.route('/inputValue',methods=['POST'])
def inputValue():
    params = request.get_json(force=True)
    print ("Moving Table Position ",params['tableX','tableY'])
    return jsonify({"msg":"ciao"})



@rc_router.route('/connect_BigTable',methods=['POST'])
def connect_BigTable():
    params = request.get_json(force=True)
    print ("Connecting ")
    return jsonify({"msg":"Connected"})


@rc_router.route('/state_BigTable',methods=['GET'])
def state_BigTable():
    print ("Connecting ")   
    return jsonify({"Table_state":state_table})


@rc_router.route('/initialize_BigTable',methods=['POST'])
def initialize_BigTable():
    params = request.get_json(force=True)
    print ("Initializing")
    global state_table
    state_table= "Initizialized"
    return jsonify({"Table_state":state_table})
