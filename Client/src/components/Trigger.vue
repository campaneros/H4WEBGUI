<template>
  <div class="trigger">
    <div class="columns is-multiline is-mobile is-centered">
      <div class="column is-one-quarter">
        <h1>CAEN DT5495 control page</h1>
        <span>Attention! The information shown in this page every time you load it are taken from the configuration file. 
        They could be different from the parameters currently loaded in the board</span>
      </div>
    </div>
    <div class="columns is-multiline is-mobile is-centered">
      <div class="column is-one-quarter" v-for="channel in channelList" :key="channel.Port">
        ID: {{channel.ID}} <br>
        Type: {{channel.Type}} <br>
        Port: {{channel.Port}} <br>
            <div>
              <label class="label">Delay (ns):</label>
              <div class="control">
                <b-field>
                  <b-input type="number" v-model="channel.Delay"/>
                </b-field>
              </div>
            </div>
            <div>
              <label class="label">Gate (ns):</label>
              <div class="control">
                <b-field>
                  <b-input type="number" v-model="channel.Gate"/>
                </b-field>
              </div>
            </div>
      </div>
    </div>
    <div class="columns is-multiline is-mobile is-centered">
        <div class="column is-one-quarter">
            <div>
                <b-checkbox v-model="selfTriggerEnabled"> Enable self triggers </b-checkbox>
            </div>
        </div>
        <div class="column is-one-quarter">
            <div>
                <label class="label">Period (ns):</label>
                <div class="control">
                    <b-field>
                        <b-input type="number" v-model="stDowntime"/>
                    </b-field>
                </div>
            </div>
            <div>
                <label class="label">Duration (ns):</label>
                <div class="control">
                    <b-field>
                        <b-input type="number" v-model="stUptime"/>
                    </b-field>
                </div>
            </div>
        </div>
    </div>
    <div>
      <button class="button" @click="updateTriggerGUI()">Update Trigger</button>
    </div>
  </div>
</template>

<script>
import axios from 'axios'

var config = {
  headers: { 'Content-Type': 'application/json', 'Cache-Control': 'no-cache' }
}

export default {
  name: 'Trigger',
  data () {
    return {
      msg: 'Welcome to Your Vue.js App',
      channelList: [],
      selfTriggerEnabled: false,
      stDowntime: 0,
      stUptime:0
    }
  },

  methods: {
    updateTriggerGUI: function () {
      // console.log(this.channelList)
      let options = {
        channelList: this.channelList,
        selfTriggerEnabled: this.selfTriggerEnabled ? 1 : 0,
        stDowntime: this.stDowntime,
        stUptime: this.stUptime        
      }
      axios.post('/api/setTriggerOptions', options).then(r => {
        console.log('Trigger Update completed!')
      })
    }
  },
  mounted () {
    console.log('Hello!')
    axios.get('/api/getTriggerOptions', config).then(r => {
      this.channelList = r.data.channelList
      this.selfTriggerEnabled = parseInt(r.data.selfTriggerEnabled) ? true : false
      this.stDowntime = parseInt(r.data.stDowntime)
      this.stUptime = parseInt(r.data.stUptime)
    })
  }
}
</script>

<!-- Add "scoped" attribute to limit CSS to this component only -->
<style scoped>
</style>
