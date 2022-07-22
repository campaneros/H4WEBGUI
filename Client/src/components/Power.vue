<template>
  <div class="Power">
    <div class="columns">
      <div class="column is-half">

        <div style="margin-left:15px"> <span id="big_title"> Load Power Supply Configuration </span> </div>
        <table class="table">
	  <thead>
	    <tr>
	      <td> tag </td>
	      <td> version </td>
	    </tr>
	  </thead>
          <tr>
            <td>
	      <div id="servicestagsmenu" class="select">
                <select v-model="selectedPSTag">
                  <option v-for="tag in psTagsList" :key="tag">{{tag}}</option>
                </select>
              </div>
	    </td>
	    <td>
              <div id="servicesversmenu" class="select">
                <select v-model="selectedPSVer">
                  <option v-for="ver in psVersList" :key="ver">{{ver}}</option>
                </select>
              </div>
	    </td>
          </tr>
        </table>

        <div style="margin-left:15px"> <span id="big_title"> General Switch </span> </div>
        <table class="table">
	  <thead> <tr></tr></thead>
          <tr>
            <td> <button class="button" @click="generalPowerON()">Switch ON </button> </td>
            <td> <button class="button" @click="generalPowerOFF()">Switch OFF</button> </td>
            <td> <button class="button" id="readEnable" @click="switchRead(),setColor('readEnable', toggleRead)">Read Enable</button> </td>
          </tr>
        </table>

        <div style="margin-left:15px"> <span id="big_title" > Channels </span> </div>
        <table class="table" id="cssTable">
          <col width="140px" />
          <col width="140px" />
          <col width="140px" />
          <col width="140px" />
          <col width="140px" />
          <thead>
            <tr>
              <td> Switch </td>
              <td> <button class="button" id="btnCh1" @click="toggleChannel(1),setColor('btnCh1', statusChannels[0])"> Ch1 </button> </td>
              <td> <button class="button" id="btnCh2" @click="toggleChannel(2),setColor('btnCh2', statusChannels[1])"> Ch2 </button> </td>
              <td> <button class="button" id="btnCh3" @click="toggleChannel(3),setColor('btnCh3', statusChannels[2])"> Ch3 </button> </td>
              <td> <button class="button" id="btnCh4" @click="toggleChannel(4),setColor('btnCh4', statusChannels[3])"> Ch4 </button> </td>
            </tr>
          </thead>
            <tr>
              <td> Voltage (V) meas. / set   </td>
              <td> {{voltageCh1}} / <span style="color:grey"> {{VsetList[0]}} </span> </td>
              <td> {{voltageCh2}} / <span style="color:grey"> {{VsetList[1]}} </span> </td>
              <td> {{voltageCh3}} / <span style="color:grey"> {{VsetList[2]}} </span> </td>
              <td> {{voltageCh4}} / <span style="color:grey"> {{VsetList[3]}} </span> </td>
            </tr>
            <tr>
              <td> Current (A) meas. / set   </td>
              <td> {{currentCh1}} / <span style="color:grey"> {{IsetList[0]}} </span> </td>
              <td> {{currentCh2}} / <span style="color:grey"> {{IsetList[1]}} </span> </td>
              <td> {{currentCh3}} / <span style="color:grey"> {{IsetList[2]}} </span> </td>
              <td> {{currentCh4}} / <span style="color:grey"> {{IsetList[3]}} </span> </td>
            </tr>
        </table>
      </div>
    </div>
  </div>

</template>

// EXAMPLE OF WRITEABLE INPUT FIELD
// <b-input id="tableX"  type="number" v-model="inputV"/>

<script>
import axios from 'axios'

var config = {
  headers: { 'Content-Type': 'application/json', 'Cache-Control': 'no-cache' }
}

export default {
  name: 'Power',
  data () {
    return {
      msg: 'Welcome to Your Vue.js App',

      psTagsList: [],
      selectedPSTag: '',
      psVersList: [],
      selectedPSVer: '',

      ChStatusList: [ 0, 0, 0, 0 ],

      VsetList: [ '0', '0', '0', '0' ],
      IsetList: [ '0', '0', '0', '0' ],

      VmonList: [ '0', '0', '0', '0' ],
      ImonList: [ '0', '0', '0', '0' ],

      // VsetList: [ 12.0, 1.25, 10, 5.0 ],
      // IsetList: [ 0.2, 0.60, 4.0, 8.5 ],

      voltageCh1: '0',
      voltageCh2: '0',
      voltageCh3: '0',
      voltageCh4: '0',

      currentCh1: '0',
      currentCh2: '0',
      currentCh3: '0',
      currentCh4: '0',

      InvervalVar: '',
      toggleRead: true,
      channelSettings: {}
    }
  },
 
  watch: {
      selectedPSTag: function (val) {
       console.log('get ps config vers')		     
       axios
        .post('/api/getPSVersList', { tag: this.selectedPSTag })
        .then(r => {
          this.lastMsg = r.data.msg
          this.psVersList = r.data.psVersList
	  this.selectedPSVer = ''
        })
      },

      selectedPSVer: function (val) {
       console.log('Load voltage ad current settings')		     
       axios
        .post('/api/getVISettings', { tag: this.selectedPSTag, ver: this.selectedPSVer })
        .then(r => {
          this.lastMsg = r.data.msg
          this.VsetList = r.data.VsetList
          this.IsetList = r.data.IsetList
        })
      }

  },

  methods: {

    generalPowerON: function () {
      this.ChStatusList = [ 1, 1, 1, 1 ]
      this.setColor('btnCh1', this.ChStatusList[0])
      this.setColor('btnCh2', this.ChStatusList[1])
      this.setColor('btnCh3', this.ChStatusList[2])
      this.setColor('btnCh4', this.ChStatusList[3])
      axios.post('/api/generalPowerON', { "VsetList":this.VsetList, "IsetList":this.IsetList}).then(r => {
        console.log('Power ON all channels')
      })
    },

    generalPowerOFF: function () {
      this.ChStatusList = [ 0, 0, 0, 0 ]
      this.setColor('btnCh1', this.ChStatusList[0])
      this.setColor('btnCh2', this.ChStatusList[1])
      this.setColor('btnCh3', this.ChStatusList[2])
      this.setColor('btnCh4', this.ChStatusList[3])
      axios.get('/api/generalPowerOFF', config).then(r => {
        console.log('Power OFF all channels')
      })
    },

    readChannelV: function () {
      axios.get('/api/readChannelV')
        .then(r => {
          console.log('Reading voltage')
          this.voltageCh1 = r.data.voltageCh1
          this.voltageCh2 = r.data.voltageCh2
          this.voltageCh3 = r.data.voltageCh3
          this.voltageCh4 = r.data.voltageCh4

          this.currentCh1 = r.data.currentCh1
          this.currentCh2 = r.data.currentCh2
          this.currentCh3 = r.data.currentCh3
          this.currentCh4 = r.data.currentCh4

	  this.ChStatusList = r.data.ChStatusList
        })
    },

    switchRead: function () {
      if (this.toggleRead) {
        this.toggleRead = false
        clearInterval(this.IntervalVar)
      } else {
        this.toggleRead = true
        this.IntervalVar = setInterval(this.readChannelV.bind(this), 2000)
      }
      console.log('Read Enable: ' + this.toggleRead)
    },

    toggleChannel: function (ch) {
      this.channelSettings = {
        'channel': ch,
        'Vset': this.VsetList[ch - 1],
        'Iset': this.IsetList[ch - 1]
      }

      if (!this.ChStatusList[ch - 1]) {
        this.ChStatusList[ch - 1] = 1
        axios.post('/api/powerOnChannel', this.channelSettings)
          .then(r => {
            this.msg = r.data.msg
            console.log(this.msg)
          })
      } else {
        this.ChStatusList[ch - 1] = 0
        axios.post('/api/powerOffChannel', this.channelSettings)
          .then(r => {
            this.msg = r.data.msg
            console.log(this.msg)
          })
      }
      console.log(this.ChStatusList[ch - 1])
    },

    setColor: function (btn, status) {
      if (status) {
        document.getElementById(btn).style.backgroundColor = 'Green'
        document.getElementById(btn).style.color = 'White'
      } else {
        document.getElementById(btn).style.backgroundColor = 'White'
        document.getElementById(btn).style.color = 'Black'
      }
    },
    
    getPSTagList: function() {
      axios.get('/api/getPSTagsList').then(r => {
          this.lastMsg = r.data.msg
          this.psTagsList = r.data.psTagsList
        })
    }
  },

  mounted () {
    this.IntervalVar = setInterval(this.readChannelV.bind(this), 2000)
    this.setColor('readEnable', this.toggleRead)
    this.getPSTagList()

  },

  beforeDestroy () {
    clearInterval(this.IntervalVar)
  }
}

</script>

<!-- Add "scoped" attribute to limit CSS to this component only -->
<style scoped>
h1, h2 {
  font-weight: normal;
}

ul {
  list-style-type: none;
  padding: 0;
}
li {
  display: inline-block;
  margin: 0 10px;
}
a {
  color: #42b983;
}

#big_title{
 font-size: 25pt;
 color: black;
 text-align: center;
 font-weight: bold;
}

#leftpadding {
  margin-left: 25px;
}

#cssTable td {
  text-align: center;
  vertical-align: middle;
}

.center {
  text-align: center;
  width: 70%;
}

</style>
