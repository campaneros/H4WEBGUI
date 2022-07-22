<template>
  <div id="dqmmon">
    <div class="section">
      <div class="columns" >
        <div class="column is-12" >
        <object id="loader" type="text/html" data="https://dpg-ecal-calib.web.cern.ch/blue/organizations/jenkins/H4DQM/activity">
        </object>
      </div>
      </div>
    </div>
  </div>
</template>

<script>

export default {
  name: 'dqmmon',

  data () {
    return {
      html: '<p>Loading...</p>'
    }
  }

}
</script>

<style scoped>
#loader {
  height: 90vh;
  width: 100%;
}
</style>
