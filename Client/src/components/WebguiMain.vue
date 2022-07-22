<template>
  <div class="web-gui">
    <!-- <div v-for="warningText in warnings" :key="warningText">
      <div v-if="warningText !== ''">
        <b-message type="is-danger" has-icon>
          {{warningText}}
        </b-message>
      </div>
    </div> -->
    <div class="columns">
      <div class="column is-half">
        <div id="status">
          <div class="columns">
            <div class="column">
              <span id="runstatus">Run: {{runNumber}}</span>
            </div>
            <div class="column">
              <span id="spillstatus">Spill: {{spillNumber}}</span>
            </div>
            <div v-if="RCorEBmissing" class="column">
              <span id="RCEBMissing">RC or EB missing!</span>
            </div>
          </div>
        </div>
        <div id="appsListDiv">
          <table class="table">
            <thead>
              <tr>
                <th>Application</th>
                <th>Status</th>
                <th>Active</th>
                <th>Triggers</th>
                <th>Timestamp</th>
                <th>Host Name</th>
                <th>Pid</th>
                <th>Log</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(app, index) in appsList" :key="index">
                <td>{{app.appName}}</td>
                <td>{{app.status}}</td>
                <td v-if="isActive(app.timestamp, now)" class="active">Yes</td>
                <td v-else class="warning">No</td>
                <td> {{app.evinspill}}</td>
                <td>{{getDateStringFromSec(app.timestamp)}}</td>
                <td>{{app.hostName}}</td>
                <td>{{app.pid}}</td>
                <td v-if="app.logFile != undefined"> <a :href="buildLogLink(app)" target="_blank">log</a></td>
                <td v-else></td>
              </tr>
            </tbody>
          </table>
        </div>
        <div v-show="h4setup()">
          <table class="table">
            <thead>
              <tr>
                <th>Merged ev. in run</th>
                <th>Run ev. rate (Hz)</th>
                <th>Nr. of bad spills</th>
                <th>Start Time</th>
                <th>Stop Time</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td>{{mergedEvNumTot}}</td>
                <td>{{runRate}}</td>
                <td>{{badSpillNum}}</td>
                <td>{{getDateSrting(startTime)}}</td>
                <td>{{getDateSrting(stopTime)}}</td>
              </tr>
            </tbody>
          </table>
        </div>
        <div v-show="h4setup()">
          <table class="table">
            <thead>
              <tr>
                <th>Merged ev. in spill</th>
                <th>Trigger rate (Hz)</th>
                <th>Spill duration (s)</th>
                <th>Spill size (MB)</th>
                <th>Transfer rate (MB/s)</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td>{{mergedEvNum}}</td>
                <td>{{triggerRate}}</td>
                <td>{{spillDuration}}</td>
                <td>{{spillSize}}</td>
                <td>{{transferRate}}</td>
              </tr>
            </tbody>
          </table>
        </div>
        <div v-show="h4setup()">
          <table class="table">
            <thead>
              <tr>
                <th>Table pos. (mm)</th>
                <th>Sensors temp. (°C)</th>
                <th>Humidity (%)</th>
                <th>Dew point (°C)</th>
                <th>Lauda temp. (°C)</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td>{{tablePos}}</td>
                <td>{{temperature}}</td>
                <td>{{humidity}}</td>
                <td>{{dewPoint}}</td>
                <td>{{laudaTemp}}</td>
              </tr>
            </tbody>
          </table>
        </div>
        <div><b>Log Text: </b></div>
        <div class="control">
          <textarea id="logtextarea" class="textarea is-info" v-model="logText" type="text" readonly rows="10"></textarea>
        </div>
        <div class="column">
          <label class="label">Select Log Level</label>
          <div id="loglevel" class="select">
            <select v-model="selectedLogLevel">
              <option v-for="tag in logLevelList" :key="tag">{{tag}}</option>
            </select>
          </div>
        </div>
      </div>
      <div class="column is-half">
        <section class="section">
          <div class="columns">
            <div class="column is-5">
              <input class="is-checkradio is-block is-warning" id="checkautorestart" name="checkautorestart" type="checkbox" v-model="autorestart" @click="toggleAutoRestart()" :disabled='disableNotRunning()'>
              <label for="checkautorestart">
                Auto Restart
              </label>
            </div>
            <div class="column is-2">
              <span v-show="socketsNb > 1" id=clientsnb>Sockets: {{socketsNb}}</span>
            </div>
            <div class="column is-2 is-offset-3">
              <button id="resetButton" class="button" @click="resetServer()">Reset Server</button>
            </div>
          </div>
          <div class="columns is-0">
            <div :class="['column','fsmstate', getfsmstate('Initialized')]">Initialized</div>
            <div :class="['column','fsmstate', getfsmstate('Configured')]">Configured</div>
            <div :class="['column','fsmstate', getfsmstate('Running')]">Running</div>
            <div :class="['column','fsmstate', getfsmstate('Paused')]">Paused</div>
            <div :class="['column','fsmstate', getfsmstate('Error')]">Error</div>
          </div>
          <div v-if="Object.keys(this.actions).length > 0">
            <button id="initialize" class="button" @click="step('initialize')" :disabled="disabledStep('initialize')">Initialize</button>
            <button id="configure" class="button" @click="step('configure')" :disabled="disabledStep('configure')">Configure</button>
            <button id="start" class="button" @click="step('start')" :disabled="disabledStep('start')">Start</button>
            <button id="pause" class="button" @click="step('pause')" :disabled="disabledStep('pause')">Pause</button>
            <button id="resume" class="button" @click="step('resume')" :disabled="disabledStep('resume')">Resume</button>
            <button id="stop" class="button" @click="step('stop')" :disabled="disabledStep('stop')">Stop</button>
          </div>
          <div class="columns">
            <div class="column">
              <div>
                <label class="label">Read the database and fill the Run Key and Service Key menus:</label>
                <button :disabled='disableNotInit()' class="button" @click="getConfigurationFromDB()">Read/Refresh DB</button>
              </div>
              <div>
                <label class="label">Choose Service Key tag and version:</label>
                <div id="servicestagsmenu" class="select">
                  <select :disabled='disableNotInit()' v-model="selectedSCTag">
                    <option v-for="tag in sconfigsTagsList" :key="tag">{{tag}}</option>
                  </select>
                </div>
                <div id="servicesversmenu" class="select">
                  <select :disabled='disableNotInit()' v-model="selectedSCVer">
                    <option v-for="ver in sconfigsVersList" :key="ver">{{ver}}</option>
                  </select>
                </div>
              </div>
              <div>
                <label class="label">Choose Run Key tag and version:</label>
                <div id="runkeystagsmenu" class="select">
                  <select :disabled='disableNotInit()' v-model="selectedRKTag">
                    <option v-for="tag in runkeysTagsList" :key="tag">{{tag}}</option>
                  </select>
                </div>
                <div id="runkeysversmenu" class="select">
                  <select :disabled='disableNotInit()' v-model="selectedRKVer">
                    <option v-for="ver in runkeysVersList" :key="ver">{{ver}}</option>
                  </select>
                </div>
              </div>
              <div v-show="h4setup()">
                <label class="label">DRs list:</label>
                <div v-if="DRsList.length == 0">
                  No DRs available...
                </div>
                <div v-else class="columns is-multiline">
                  <div class="column is-narrow" v-for="(drId) in DRsList" :key="drId">
                    <input class="is-checkradio is-block is-success" :disabled='disableNotInit()' :id="drId" :value="drId" type="checkbox" checked="checked" v-model="activeDRs">
                    <label :for="drId">{{drId}}</label>
                  </div>
                </div>
                <div v-if="stDowntime != 0">
                    Trigger generator enable with divider {{stDowntime}} - Trigger inputs below will be ignored
                </div>
                <label class="label">Input Ports list:</label>
                <div v-if="InputList.length == 0">
                  No Input Ports available...
                </div>
                <div v-else class="columns is-multiline">
                  <div class="column is-narrow" v-for="(inputId) in InputList" :key="inputId">
                    <input class="is-checkradio is-block is-success" :disabled='disableNotInit()' :id="inputId" :value="inputId" type="checkbox" checked="checked" v-model="activeInputs">
                    <label :for="inputId">Channel ID {{inputId}}</label>
                  </div>
                </div>
              </div>
            </div>
          </div>
          <div class="columns" v-show="h4setup()">
            <div class="column">
              <label class="label">Choose run type:</label>
              <div id="runtypemenu" class="select">
                <select :disabled='disableNotConfigured()' v-model="selectedRunType">
                  <option v-for="type in runTypesList" :key="type">{{type}}</option>
                </select>
              </div>
            </div>
            <div class="column">
              <label class="label">Events per spill:</label>
              <div id="eventsPerSpill" class="control">
                <b-field>
                  <b-input :disabled='disableNotConfigured()' type="number" v-model="eventsPerSpill"/>
                </b-field>
              </div>
            </div>
            <div class="column">
              <label class="label">Choose beam type:</label>
              <div id="beamtypemenu" class="select">
                <select :disabled='disableNotConfigured()' v-model="selectedBeamType">
                  <option v-for="type in beamTypeList" :key="type">{{type}}</option>
                </select>
              </div>
            </div>
            <div class="column">
              <label class="label">Beam Energy (GeV)  :</label>
              <div id="beamEnergy" class="control">
                <b-field :type="beamEnergyValidation()">
                  <b-input type="text" v-model="beamEnergy" :disabled='disableNotConfigured()'/>
                </b-field>
              </div>
            </div>
          </div>
          <div class="columns" v-show="h4setup()">
            <div class="column">
              <label class="label">Table X:</label>
              <div class="control">
                <b-field>
                  <b-input id="tableX" :disabled='disableNotConfigured()' type="number" v-model="tableX"/>
                </b-field>
              </div>
            </div>
            <div class="column">
              <label class="label">Table Y:</label>
              <div class="control">
                <b-field>
                  <b-input id="tableY" :disabled='disableNotConfigured()' type="number" v-model="tableY"/>
                </b-field>
              </div>
            </div>
            <div class="column">
              <label class="label">Table Position Tag</label>
              <div id="tablepostag" class="select">
                <select :disabled='disableNotConfigured()' v-model="selectedTablePosTag">
                  <option v-for="tag in tablePosTagsList" :key="tag">{{tag}}</option>
                </select>
              </div>
            </div>
            <div class="column">
              <label class="label">Table Position</label>
              <div id="tablepos" class="select">
                <select :disabled='disableNotConfigured()' v-model="selectedTablePos">
                  <option v-for="(value, key) in tablePosList" :key="key" :value="key">{{key}} ({{value.x}},{{value.y}})</option>
                </select>
              </div>
            </div>
            <div class="column">
              <div id="moveTable" class="control">
                <button id="moveTableButton" class="button" @click="moveTable()" :disabled="disableTable()">Move Table</button>
              </div>
            </div>
          </div>
          <div class="columns" v-show="h4setup()">
            <div class="column">
              <label class="label">Testbeam Campaign</label>
              <div id="tbcamp" class="select">
                <select :disabled='disableNotConfigured()' v-model="selectedTbCamp">
                  <option v-for="tag in tbCampList" :key="tag">{{tag}}</option>
                </select>
              </div>
            </div>
          </div>
        </section>
      </div>
    </div>
    <!-- these br are needed to ease the expansion of the logtextarea -->
    <br/>
    <br/>
    <br/>
    <br/>
    <br/>
  </div>
</template>

<script>
import axios from 'axios'
import io from 'socket.io-client'

var config = {
  headers: { 'Content-Type': 'application/json', 'Cache-Control': 'no-cache' }
}

export default {
  name: 'WebGui',
  data () {
    return {
      completeh4setup: true,
      warnings: {},
      lastMsg: ' ',
      logText: '',
      state: '',
      states: [],
      performingAction: '',
      actions: {},
      autorestart: false,
      logLevelList: ['INFO', 'DEBUG'],
      selectedLogLevel: '',
      logLevelMap: { 10: 'DEBUG', 20: 'INFO' }, // https://docs.python.org/3/howto/logging.html
      logLevelReverseMap: { 'DEBUG': 10, 'INFO': 20 },
      // Configuration
      sconfigsTagsList: [],
      selectedSCTag: '',
      sconfigsVersList: [],
      selectedSCVer: '',
      runkeysTagsList: [],
      selectedRKTag: '',
      runkeysVersList: [],
      selectedRKVer: '',
      DRsList: [],
      activeDRs: [],
      tempDRs: 0,
      InputList: [],
      activeInputs: [],
      tempInputs: 0,
      tempSCTag: '',
      tempRKTag: '',
      tempSCVer: '',
      tempRKVer: '',
      appsList: [],
      RCorEBmissing: false,
      eventsPerSpill: 0,
      runTypesList: ['PHYSICS', 'PEDESTAL', 'LED'],
      selectedRunType: 'PHYSICS',
      beamTypeList: ['Electrons', 'Muons', 'Pions', 'N.A.'],
      selectedBeamType: 'Electrons',
      beamEnergy: -1,
      selectedTablePosTag: '',
      tablePosTagsList: [],
      tempTablePosTag: '',
      selectedTablePos: '',
      tablePosList: [],
      tempTablePos: '',
      selectedTbCamp: '',
      tbCampList: [],
      tempTbCamp: '',
      // Run status values
      runNumber: 0,
      startTime: 0,
      stopTime: 0,
      spillNumber: 0,
      mergedEvNum: 0,
      mergedEvNumTot: 0,
      runRate: 0,
      badSpillNum: 0,
      triggerRate: 0,
      tablePos: '',
      tablePosX: 0, // returned by the table
      tablePosY: 0,
      tbCamp: '',
      spillDuration: 0,
      spillSize: 0,
      transferRate: 0,
      temperature: 0,
      humidity: 0,
      dewPoint: 0,
      laudaTemp: 0,
      tableX: 0.0, // selected on the GUI
      tableY: 0.0,
      interval: {},
      now: 0,
      socketsNb: '',
      stDowntime: 0
    }
  },

  watch: {
    selectedSCTag: function (val) {
      axios
        .post('/api/getSConfigsVersList', { tag: this.selectedSCTag })
        .then(r => {
          this.lastMsg = r.data.msg
          this.sconfigsVersList = r.data.sconfigsVersList
          if (this.tempSCVer !== '') {
            this.selectedSCVer = this.tempSCVer
            this.tempSCVer = ''
          } else {
            // fixing bug related to checkign the Dr only when changing the version number
            // not the tag
            if (this.selectedSCVer === this.sconfigsVersList[0]) {
              axios
                .post('/api/getDRsList', {
                  scTag: this.selectedSCTag,
                  scVer: this.selectedSCVer
                })
                .then(r => {
                  this.lastMsg = r.data.msg
                  this.DRsList = r.data.DRsList.slice(0)
                  if (this.tempDRs !== 0) {
                    this.activeDRs = this.tempDRs.slice(0)
                    this.tempDRs = 0
                  } else {
                    this.activeDRs = r.data.DRsList.slice(0)
                  }
                })
            } else {
              this.selectedSCVer = this.sconfigsVersList[0]
            }
          }
        })
    },

    selectedSCVer: function (val) {
      axios
        .post('/api/getDRsList', {
          scTag: this.selectedSCTag,
          scVer: this.selectedSCVer
        })
        .then(r => {
          this.lastMsg = r.data.msg
          this.DRsList = r.data.DRsList.slice(0)
          if (this.tempDRs !== 0) {
            this.activeDRs = this.tempDRs.slice(0)
            this.tempDRs = 0
          } else {
            this.activeDRs = r.data.DRsList.slice(0)
          }
        })
    },

    selectedRKTag: function (val) {
      axios
        .post('/api/getRunKeysVersList', { tag: this.selectedRKTag })
        .then(r => {
          this.lastMsg = r.data.msg
          this.runkeysVersList = r.data.runkeysVersList
          if (this.tempRKVer !== '') {
            this.selectedRKVer = this.tempRKVer
            this.tempRKVer = ''
          } else {
            // fixing bug related to checkign the inputs only when changing the version number
            // not the tag
            if (this.selectedRKVer === this.runkeysVersList[0]) {
              axios
                .post('/api/getInputList', {
                  rkTag: this.selectedRKTag,
                  rkVer: this.selectedRKVer
                })
                .then(r => {
                  this.stDowntime = parseInt(r.data.stDownDivider)
                  this.lastMsg = r.data.msg
                  this.InputList = r.data.InputList.slice(0)
                  if (this.tempInputs !== 0) {
                    this.activeInputs = this.tempInputs.slice(0)
                    this.tempInputs = 0
                  } else {
                    this.activeInputs = r.data.InputList.slice(0)
                  }
                })
            } else {
              this.selectedRKVer = this.runkeysVersList[0]
            }
          }
        })
    },

    selectedRKVer: function (val) {
      axios
        .post('/api/getInputList', {
          rkTag: this.selectedRKTag,
          rkVer: this.selectedRKVer
        })
        .then(r => {
          this.stDowntime = parseInt(r.data.stDowntime)
          this.lastMsg = r.data.msg
          this.InputList = r.data.InputList.slice(0)
          if (this.tempInputs !== 0) {
            this.activeInputs = this.tempInputs.slice(0)
            this.tempInputs = 0
          } else {
            this.activeInputs = r.data.InputList.slice(0)
          }
        })
    },

    selectedLogLevel: function (val) {
      axios.post('/api/setLogLevel',
        { logLevel: this.logLevelReverseMap[this.selectedLogLevel] }
      )
        .then(r => {
          this.lastMsg = r.data.msg
        })
    },

    selectedTablePosTag: function (val) {
      if (this.selectedTablePosTag === '') {
        this.tablePosList = []
        this.selectedTablePos = ''
        this.tempTablePos = ''
        return
      }
      axios
        .post('/api/getTablePosList', { tag: this.selectedTablePosTag })
        .then(r => {
          this.tablePosList = r.data.tablePosList
          if (this.tempTablePos !== '') {
            this.selectedTablePos = this.tempTablePos
            this.tempTablePos = ''
          } else {
            this.selectedTablePos = this.tablePosList[0]
          }
        })
    },

    selectedTablePos: function (val) {
      if (this.tablePosList[this.selectedTablePos] !== undefined) {
        this.tableX = this.tablePosList[this.selectedTablePos]['x']
        this.tableY = this.tablePosList[this.selectedTablePos]['y']
      }
    },

    selectedTbCamp: function (val) {
      if (this.selectedTbCamp === '') {
        this.tbCampList = []
        this.tempTbCamp = ''
        return
      }
      this.tbCamp = this.tbCampList[this.selectedTbCamp]
    },

    tableX: function (val) {
      var tableXEl = document.getElementById('tableX')
      if (document.activeElement === tableXEl) {
        this.selectedTablePosTag = ''
        this.selectedTablePos = ''
      }
    },

    tableY: function (val) {
      var tableYEl = document.getElementById('tableY')
      if (document.activeElement === tableYEl) {
        this.selectedTablePosTag = ''
        this.selectedTablePos = ''
      }
    },

    logText: function (val) {
      this.logtextheight()
    },

    appsList: function () {
      if (this.state !== 'Initialized' && this.state !== 'None') {
        let hasRC = false
        let hasEB = false
        for (var i in this.appsList) {
          if (this.appsList[i].appName === 'RC') {
            hasRC = true
          }
          if (this.appsList[i].appName === 'EB') {
            hasEB = true
          }
        }
        this.RCorEBmissing = !(hasRC && hasEB)
      } else {
        this.RCorEBmissing = false
      }
    }
  },

  methods: {

    h4setup: function () {
      return this.completeh4setup
    },

    disableNotInit: function () {
      if (this.state !== 'Initialized' || this.autorestart === true) {
        return true
      }
      return false
    },

    disableNotConfigured: function () {
      if (this.state !== 'Configured' || this.autorestart === true) {
        return true
      }
      return false
    },

    disableNotRunning: function () {
      if (this.state !== 'Running' && this.state !== 'Error') {
        return true
      }
      return false
    },

    isActive: function (thetime, nowTime) {
      if (nowTime - thetime < 30) {
        // this.warnings.notActive = 'Application not active'
        return true
      }
      // this.warnings.notActive = 'Application not active'
      return false
    },

    step: function (action) {
      var postMsg = config
      if (action === 'configure') {
        if (
          this.selectedSCTag === '' ||
          this.selectedSCVer === '' ||
          this.selectedRKTag === '' ||
          this.selectedRKVer === ''
        ) {
          this.lastMsg = 'Configuration not correct.'
          return
        } else {
          postMsg = {
            scTag: this.selectedSCTag,
            scVer: this.selectedSCVer,
            rkTag: this.selectedRKTag,
            rkVer: this.selectedRKVer,
            activeDRs: this.activeDRs,
            activeInputs: this.activeInputs
          }
        }
      } else if (action === 'start') {
        if (
          this.selectedRunType === '' ||
          parseInt(this.eventsPerSpill) === 0 ||
          this.selectedBeamType === '' ||
          this.beamEnergyValidation() === 'is-danger'
          // this.tablePosX !== this.tableX ||
          // this.tablePosY !== this.tableY
        ) {
          // WARNING
          return
        }
        postMsg = {
          eventsPerSpill: this.eventsPerSpill,
          beamEnergy: this.beamEnergy,
          runType: this.selectedRunType,
          beamType: this.selectedBeamType,
          tablePosTag: (this.selectedTablePosTag === undefined) ? '' : this.selectedTablePosTag,
          tablePos: (this.selectedTablePos === undefined) ? '' : this.selectedTablePos,
          tbCamp: (this.selectedTbCamp === undefined) ? '' : this.selectedTbCamp,
          tableX: this.tableX,
          tableY: this.tableY
        }
      }
      document.getElementById(action).classList.add('is-loading')
      axios.post('/api/actions/' + action, postMsg).then(r => {
        this.lastMsg = r.data.msg
        this.state = r.data.newstate
        document.getElementById(action).classList.remove('is-loading')
      })
    },

    disabledStep: function (action) {
      if (this.performingAction !== 'None') {
        return true // button disabled
      } else if (this.actions[action]['from'].includes(this.state)) {
        return false // button enabled
      } else {
        return true // button disabled
      }
    },

    hiddenTable: function () {
      document.getElementById('moveTableButton').style.visibility = 'hidden'
      document.getElementById('tableX').style.visibility = 'hidden'
      document.getElementById('tableY').style.visibility = 'hidden'
      document.getElementById('tablepostag').style.visibility = 'hidden'
      document.getElementById('tablepos').style.visibility = 'hidden'
    },

    disableTable: function () {
      if (this.state === 'Configured') {
        for (var i in this.appsList) {
          if (this.appsList[i].status === 'TAB_MOVING') {
            return true // button disabled
          } else {
            return false // button enabled
          }
        }
      } else {
        return true // button disabled
      }
    },

    getfsmstate: function (statebox) {
      if (statebox === 'Initialized' && this.state === 'Initialized') {
        return { fsminit: true }
      } else if (statebox === 'Configured' && this.state === 'Configured') {
        return { fsmconf: true }
      } else if (statebox === 'Running' && this.state === 'Running') {
        return { fsmrun: true }
      } else if (statebox === 'Paused' && this.state === 'Paused') {
        return { fsmpause: true }
      } else if (statebox === 'Error' && this.state === 'Error') {
        return { fsmerror: true }
      }
    },

    // Return a Promise in case you need to add a success/failure callbacks
    getConfigurationFromDB: function () {
      var p1 = new Promise((resolve, reject) => {
        axios.get('/api/getSConfigsTagsList', config).then(r => {
          this.lastMsg = r.data.msg
          this.sconfigsTagsList = r.data.sconfigsTagsList
          if (this.sconfigsTagsList.length > 0) {
            if (this.tempSCTag !== '') {
              this.selectedSCTag = this.tempSCTag
              this.tempSCTag = ''
            } else {
              this.selectedSCTag = this.sconfigsTagsList[0]
            }
          }
          resolve(1)
        })
      })
      var p2 = new Promise((resolve, reject) => {
        axios.get('/api/getRunKeysTagsList', config).then(r => {
          this.lastMsg = r.data.msg
          this.runkeysTagsList = r.data.runkeysTagsList
          if (this.runkeysTagsList.length > 0) {
            if (this.tempRKTag !== '') {
              this.selectedRKTag = this.tempRKTag
              this.tempRKTag = ''
            } else {
              this.selectedRKTag = this.runkeysTagsList[0]
            }
          }
          resolve(1)
        })
      })
      var p3 = new Promise((resolve, reject) => {
        axios.get('/api/getTablePosTagsList', config).then(r => {
          this.lastMsg = r.data.msg
          this.tablePosTagsList = r.data.tablePosTagsList
          if (this.tablePosTagsList.length > 0) {
            if (this.tempTablePosTag !== '') {
              this.selectedTablePosTag = this.tempTablePosTag
              this.tempTablePosTag = ''
            } else {
              this.selectedTablePosTag = this.tablePosTagsList[0]
            }
          }
          resolve(1)
        })
      })
      var p4 = new Promise((resolve, reject) => {
        axios.get('/api/getTbCampList', config).then(r => {
          this.lastMsg = r.data.msg
          this.tbCampList = r.data.tbCampList
          if (this.tbCampList.length > 0) {
            if (this.tempTbCamp !== '') {
              this.selectedTbCamp = this.tempTbCamp
              this.tempTbCamp = ''
            } else {
              this.selectedTbCamp = this.tbCampList[0]
            }
          }
          resolve(1)
        })
      })
      return Promise.all([p1, p2, p3, p4])
    },

    resetServer: function () {
      document.getElementById('resetButton').classList.add('is-loading')
      axios.get('/api/reset?type=manual', config).then(r => {
        console.log('Reset request sent')
      })
    },
    // Reset of the server always allowed if allowResetServer disabled
    /* allowResetServer: function () {
      if (this.state === 'Error') {
        return false
      } else {
        return true
      }
    }, */

    // We need to create two update function.
    // 1) 'updateAll' to load the complete GUI, to be called when:
    //    - open/refresh the page
    //    - change of state
    // 2) 'updateApps' is just for new information from the apps.
    updateAll: function (response) {
      // this.hiddenTable()
      this.logText = response.data.msg
      // this.logText = this.logText.replace(/,/g, '\n')
      this.state = response.data.currentstate
      this.autorestart = response.data.autorestart
      this.performingAction = response.data.performingAction
      this.selectedLogLevel = this.logLevelMap[response.data.logTextLogLevel]
      this.updateApps(response)
      if (response.data.run) {
        this.runNumber = response.data.run.runNumber
        this.eventsPerSpill = response.data.run.eventsPerSpill
        this.beamEnergy = response.data.run.beamEnergy
        this.selectedRunType = response.data.run.runType
        this.selectedBeamType = response.data.run.beamType
        this.tableX = response.data.run.tableX
        this.tableY = response.data.run.tableY
        this.startTime = response.data.run.startTime
        this.stopTime = response.data.run.stopTime
        this.tempTablePosTag = response.data.run.tablePosTag
        this.tempTablePos = response.data.run.tablePos
        this.tempTbCamp = response.data.run.tbCamp
      }
      if (
        'sConfigTag' in response.data &&
        'sConfigVer' in response.data &&
        'runKeyTag' in response.data &&
        'runKeyVer' in response.data &&
        'activeDRs' in response.data
      ) {
        if (response.data.activeDRs === 0) {
          response.data.activeDRs = []
        }
        if (
          this.selectedSCTag !== response.data.sConfigTag ||
          this.selectedSCVer !== response.data.sConfigVer ||
          this.selectedRKTag !== response.data.runKeyTag ||
          this.selectedRKVer !== response.data.runKeyVer ||
          !this.compareLists(this.activeDRs, response.data.activeDRs)
        ) {
          this.tempDRs = response.data.activeDRs
          this.tempSCTag = response.data.sConfigTag
          this.tempRKTag = response.data.runKeyTag
          this.tempSCVer = response.data.sConfigVer
          this.tempRKVer = response.data.runKeyVer
          this.getConfigurationFromDB()
        }
      }
      console.log(response.data)
      if ('completeh4setup' in response.data) {
        this.completeh4setup = response.data.completeh4setup
      }
    },

    logtextheight: function () {
      var textarea = document.getElementById('logtextarea')
      textarea.scrollTop = textarea.scrollHeight
    },

    updateApps: function (response) {
      if ('apps' in response.data) {
        this.appsList = response.data.apps
      }
      let tableAppPresent = false
      for (var i in this.appsList) {
        if (this.appsList[i].appName === 'RC') {
          this.spillNumber = this.appsList[i].spillnumber
          this.triggerRate = this.appsList[i].trigrate
          this.spillDuration = this.appsList[i].spillduration
        }
        if (this.appsList[i].appName === 'EB') {
          this.mergedEvNum = this.appsList[i].eventsmerged
          this.transferRate = this.appsList[i].transferRate
          this.spillSize = this.appsList[i].spillsize
          this.badSpillNum = this.appsList[i].badspills
          this.mergedEvNumTot = this.appsList[i].evinrun
          let now = new Date()
          this.runRate = (
            this.mergedEvNumTot /
            (now.getTime() - this.startTime) *
            1000
          ).toFixed(2)
        }
        if (this.appsList[i].status === 'BYE') {
          this.appsList[i].timestamp = 0
        }
        if (this.appsList[i].appName === 'thetable') {
          tableAppPresent = true
          if (this.appsList[i].posX === '-inf') {
            this.appsList[i].posX = -1
          }
          if (this.appsList[i].posY === '-inf') {
            this.appsList[i].posY = -1
          }
          this.tablePosX = Number(this.appsList[i].posX)
          this.tablePosY = Number(this.appsList[i].posY)
          this.tablePos = 'x: ' + this.tablePosX + ', y: ' + this.tablePosY
          if (this.appsList[i].status === 'TAB_MOVING') {
            document
              .getElementById('moveTableButton')
              .setAttribute('disabled', 'disabled')
            document
              .getElementById('start')
              .setAttribute('disabled', 'disabled')
          } else if (!this.disabledStep('start') && this.appsList[i].status === 'TAB_DONE') {
            document.getElementById('start').removeAttribute('disabled')
          }
        }
      }
      if (!tableAppPresent) {
        //this.hiddenTable()
      }
    },

    compareLists: function (list1, list2) {
      if (list1.length !== list2.length) {
        return false
      }
      if (list1.length !== 0) {
        for (var el in list1) {
          if (list2.indexOf(el) === -1) {
            return false
          }
        }
      }
      return true
    },

    moveTable: function () {
      var postMsg = {
        tableX: this.tableX,
        tableY: this.tableY
      }
      axios.post('/api/moveTable', postMsg).then(r => {
        this.lastMsg = r.data.msg
      })
    },

    getDateStringFromSec: function (timeSec) {
      if (timeSec === 0) {
        return 'N.A.'
      }
      return new Date(timeSec * 1000).toLocaleString('en-GB', {
        timeZoneName: 'short'
      })
    },

    getDateSrting: function (timeMilliSec) {
      if (timeMilliSec === 0) {
        return 'N.A.'
      }
      return new Date(timeMilliSec).toLocaleString('en-GB', {
        timeZoneName: 'short'
      })
    },

    buildLogLink: function (app) {
      return 'http://' + app.hostName + app.logFile
    },

    toggleAutoRestart: function () {
      // ACHTUNG! This function is called just before the autorestart variable
      // is changed, so we invert the meaning of true and false in this
      // function
      axios.post('/api/toggleAutoRestart', {autorestart: !this.autorestart})
    },

    beamEnergyValidation: function () {
      if (this.beamEnergy === undefined) {
        return
      }
      let matchNumber = /^[-]?[0-9]+(\.[0-9]+)?$/g
      if (this.beamEnergy.toString().match(matchNumber)) {
        return 'is-success'
      } else {
        return 'is-danger'
      }
    }
    /* alarms: function(){
      1) timestamp too old or active = false since configure status
      5) No events built in the last minute, evinrun
      6) You have set a number of triggers per spill to 0
    } */
  },

  mounted () {
    axios.get('/api/getfsm', config).then(r => {
      this.states = r.data.states
      this.actions = r.data.actions
    })

    axios.get('/api/updateAll', config).then(r => {
      this.updateAll(r)
    })

    // Creating the socket for updates notifications
    this.socket = io()

    // Callback for update event
    this.socket.on('updateAll', () => {
      axios.get('/api/updateAll', config).then(r => {
        this.updateAll(r)
      })
    })

    // Callback for update event
    this.socket.on('updateApps', () => {
      axios.get('/api/updateApps', config).then(r => {
        this.updateApps(r)
      })
    })

    // Callback for update event
    this.socket.on('updateSockets', (data) => {
      this.socketsNb = data['clients']
    })

    // Callback when someone resets the server
    this.socket.on('reloadPage', (data) => {
      window.location.reload(true)
    })

    this.interval = setInterval(function () {
      // If the loglevel selected is lower than INFO
      // (logging.INFO == 20, logging.DEBUG == 10)
      // then ask the log to the server every 10s
      if (this.logLevelReverseMap[this.selectedLogLevel] < 15) {
        axios.get('/api/updateLog', config).then(r => {
          this.logText = r.data
        })
      }
      // Refreshing the timer used to check if an app is active
      if (this.appsList.length > 0) {
        this.now = Math.floor(new Date().getTime() / 1000)
      }
    }.bind(this), 10000)

    // window.addEventListener('beforeunload', (e) => {
    // this.socket.close()
    // })
  },

  updated () {
    // This scrolled the text area too often.
    // Now we scroll it only when we update the logText variable
    // this.logtextheight()
  },

  // beforeRouteLeave (to, from, next) {
  //   this.socket.close()
  //   next()
  // },

  beforeDestroy () {
    console.log('before destroy')
    clearInterval(this.interval)
    this.socket.close()
  }

}
</script>

<!-- Add 'scoped' attribute to limit CSS to this component only -->
<style scoped>
.fsmstate {
  border: 1px solid #000000;
  background-color: #b3b3b3;
  text-align: center;
  vertical-align: middle;
}

.fsminit {
  background-color: #039be5;
}

.fsmconf {
  background-color: #87cefa;
}

.fsmrun {
  background-color: #00ff00;
}

.fsmpause {
  background-color: #ffff00;
}

.fsmerror {
  background-color: red;
}

@-webkit-keyframes demo {
  0% {
    background-color: #fff59d;
    opacity: 1;
  }
  33% {
    background-color: #fdd835;
  }
  66% {
    background-color: #fdd835;
  }
  100% {
    background-color: #fff59d;
  }
}

.warning {
  -webkit-animation-name: demo;
  -webkit-animation-duration: 3000ms;
  -webkit-animation-iteration-count: infinite;
  -webkit-animation-timing-function: ease-in-out;
}

.active {
  background-color: #AED581
}

#status {
  margin-top: 20px;
  margin-bottom: 20px;
  margin-left: 50px;
}

#runstatus {
  font-size: 30pt;
  color: blue;
}
#spillstatus {
  font-size: 30pt;
  color: blue;
}
#RCEBMissing {
  font-size: 15pt;
  color: grey;
  animation: blink 2s infinite;
}
#clientsnb {
  font-size: 15pt;
  color: grey;
  animation: blinkwarning 3s infinite;
}

@keyframes blink {
  from { background-color: white; }
  to { background-color: red; }
}

@keyframes blinkwarning {
  from { background-color: white; }
  to { background-color: yellow; }
}
</style>
