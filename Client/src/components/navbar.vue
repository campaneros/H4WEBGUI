<template>
<nav class="navbar is-link" role="navigation" aria-label="main navigation">
  <router-link to="/hello-world" class="navbar-item" active-class="is-active">Documentation</router-link>
  <router-link to="/webgui-main" class="navbar-item" active-class="is-active">Web GUI</router-link>
  <router-link to="/table" class="navbar-item" active-class="is-active">Table</router-link>
  <router-link to="/webcam" class="navbar-item" active-class="is-active">Webcam</router-link>
  <router-link to="/dqm" class="navbar-item" active-class="is-active">DQM</router-link>
  <router-link to="/dqmmon" class="navbar-item" active-class="is-active">DQM-Monitoring</router-link>
  <router-link to="/trigger" class="navbar-item" active-class="is-active" v-if="isCompleteGui">Trigger</router-link>
  <router-link to="/power" class="navbar-item" active-class="is-active" v-if="isCompleteGui">Power</router-link>
</nav>
</template>

<script>
import axios from 'axios'

export default {
  name: 'navbar',
  data () {
    return {
      isCompleteGui: false
    }
  },
  mounted () {
    axios.get('/api/isCompleteGui').then(r => {
      this.isCompleteGui = r.data.isCompleteGui
      console.log(r.data.isCompleteGui)
    })
  }
}
</script>

<style>
</style>
