<template>
  <div id="webcam">
    <div class="section">
      <div class="columns" >
        <div class="column is-12" >
        <object id="loader" type="text/html" data="http://axisminn02.cern.ch/view/viewer_index.shtml?id=9">
        </object>
      </div>
      </div>
    </div>
  </div>
</template>

<script>

export default {
  name: 'webcam',

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
