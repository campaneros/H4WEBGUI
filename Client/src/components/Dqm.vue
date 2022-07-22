<template>
  <div id="dqm">
    <div class="section">
      <div class="columns" >
        <div class="column is-12" >
        <object id="loader" type="text/html" data="https://project-cms-ecal-calibration.web.cern.ch/project-cms-ecal-calibration/h4dqm/">
        </object>
      </div>
      </div>
    </div>
  </div>
</template>

<script>

export default {
  name: 'dqm',

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
