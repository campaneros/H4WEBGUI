<template>
<div class="movingTable">
 <div class="columns">
      <div class="column is-one-third">
        	<button id="Initialize" class="button is-large" @click="Initialize()">Initialize</button>
           	<button id="Connect" class="button is-large" @click="Connect()" :disabled="disableNotInit()">Connect</button>
	<div class="container">
	<b-field grouped>
        <b-field label="Step X" id="Step_type">
            <b-numberinput  msize="is-large" placeholder="Step X" min="0" max="1000" :controls="false" v-model="Step_x_sel">
            </b-numberinput>
        </b-field>
        <b-field label="Step Y">
            <b-numberinput  msize="is-large" placeholder="Step Y" min="0" max="1000" :controls="false" v-model="Step_y_sel">
            </b-numberinput>
        </b-field>
	</b-field>
	</div>
	<b-field grouped>
        <b-field label="Crystal">
            <b-select placeholder="Crystal number" v-model ="crystal">
                <option
	v-for="option in crystals"
	:value="option.id"
	:key="option.id">
	{{ option.crystal.xnumber }}
                </option>
            </b-select>
        </b-field>
	<b-field label="Confirm">
	<b-button size="is-medium" rounded @click="TableCoord()"> Confirm </b-button>
	</b-field>
	</b-field>
     </div>
     <div class="column">
	<h2 class="title">Current Postion</h2>
	<div class="column is-full">	
		 <b-field label="Step X">
		<span id="Step X">Current position: {{Step_x}} --- Moving to {{Step_x_sel}}</span>
		</b-field>
	</div>
	<div class="column is-full">
		 <b-field label="Step Y">
		<span id="Step Y">Current position: {{Step_y}} --- Moving to {{Step_y_sel}}</span>
		</b-field>
	</div>
	<div class="column is-half">
		<span id="Running statu">Running</span>
	</div>
     </div>
     <div class="column">
	<h2 class="title">Alarms</h2>
		<div class="column is-full">
		<span id="End X">End X</span>
		<button id="End 0" class="button is-warning" :disabled="disabledStep(Step_x,'min')">   Zero </button>
		<button id="End Inf" class="button is-warning" :disabled="disabledStep(Step_x,'max')">   Inf </button>
		</div>
		<div class="column is-full">
		<span id="End X">End Y</span>
		<button id="End 0" class="button is-warning" :disabled="disabledStep(Step_y,'min')">   Zero </button>
		<button id="End inf" class="button is-warning" :disabled="disabledStep(Step_y,'max')"> Inf </button>	
		</div>
		<div class="column is-full">	
		<span id="Error">Error</span>
		<button id="End 0" class="button is-danger" disabled>   </button>
		</div>
     </div>
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
</template>




<script>
import axios from 'axios'


var config = {
  headers: { 'Content-Type': 'application/json', 'Cache-Control': 'no-cache' }
}



const crystals= [{"id":1,"crystal":{"xnumber":"1","step_x":200,"step_y":300}},{"id":2,"crystal":{"xnumber":"2","step_x":400,"step_y":500}}]

export default {
  name: 'MovingTable',
  data () {
    return {
	Step_g: -1,
	Step_y_sel: 10,
	Step_x_sel: 20,
	Step_x:0,
	Step_y:0,
	state:'zio',
	crystal: 0,
	logText: '',
	selectedLogLevel: '',
	logLevelList: ['INFO', 'DEBUG'],
	logLevelReverseMap: { 'DEBUG': 10, 'INFO': 20 },
	logLevelMap: { 10: 'DEBUG', 20: 'INFO' }, // https://docs.python.org/3/howto/logging.html
	appsList: [],
	crystals
	}
  },
	watch:{
	
    	selectedLogLevel: function (val) {
      		axios.post('/api/setLogLevel',
        	{ logLevel: this.logLevelReverseMap[this.selectedLogLevel] }
      		)
        	.then(r => {
        	  this.lastMsg = r.data.msg
    		    })
    		},
	    logText: function (val) {
      		this.logtextheight()
    		}


	},
	methods:{
	Initialize() {
                console.log('Initialize')
		 	
      		var postMsg = {
        		tableX: this.Step_x_sel,
			tableY: this.Step_y_sel,
   		   }
      		axios.post('/api/initialize_BigTable', postMsg).then(r => {
        	console.log(r.data)
      		})
	
            },
	    disableNotInit: function () {
		console.log(this.state)
		
      		if (this.state !== 'Initialized') {
        	return true
      		}
      		return false
    		},

	Connect() {
                console.log('Connect')

		 
			
      		var postMsg = {
        		tableX: this.Step_x_sel,
			tableY: this.Step_y_sel,
   		   }
      		axios.post('/api/connect_BigTable',postMsg).then(r => {
        	console.log(r.data)
      		})
            },
	
	checkInput: function (x,y){
		if (x<0 || y<0 || x>1000 || y>1000) {
		return false
		} else
		{ return true
		}
		
	},
	
	TableCoord() {
		if (this.checkInput(this.Step_x_sel,this.Step_y_sel) === false){
		console.log("wrong input")
		this.$buefy.dialog.alert({
			title: 'Error',
			type: 'is-danger',
			message: 'Wrong coordinates inserted, check again and insert right ones'
			})	
		} else {
		this.$buefy.dialog.confirm({
                    message: `<p> Are you sure of the number inserted? step x = ${this.Step_x_sel} step y = ${this.Step_y_sel}</p>`,
                    onConfirm: () => {
			this.Step_x=this.Step_x_sel,
			this.Step_y=this.Step_y_sel,
			this.$buefy.toast.open('User confirmed')
			}
                	})
		     console.log('Sending coordinates')
		}
	},
	updateAll: function (response) {
      		// this.hiddenTable()
      		this.logText = response.data.msg
      		// this.logText = this.logText.replace(/,/g, '\n')
      		this.state = response.data.currentstate
      		this.autorestart = response.data.autorestart
      		this.performingAction = response.data.performingAction
      		this.selectedLogLevel = this.logLevelMap[response.data.logTextLogLevel]
		},

    	StepValidation: function (val) {
		console.log(val)
      		if (val === undefined) {
        	return
      		}
		let matchNumber = /^[-]?[0-9]+(\.[0-9]+)?$/g
                if (val.toString().match(matchNumber)) {
			if (val>0 && val<1000){
			console.log('zio caro')
        		return 'is-success' 
      			} else {
        	return 'is-warning'
      			}
		} else 
		{
		return 'is-danger'
		}
		},
	 disabledStep: function (val,lim) {
		if (val >= 0 && val <=1000) {
        	return true // button disabled
		}
		else if (lim === "min" && val <=0){
		return false
		} else if (lim === "max" && val >= 1000) {
      		  return false // button enabled
      		} else {
		return true
		}
    	},

	},
   mounted () {
  
    axios.get('/api/state_BigTable').then(r=> {
                        console.log(r.data.Table_state)
                        this.state=r.data.Table_state})


    axios.get('/api/getfsm', config).then(r => {
      this.states = r.data.states
      this.actions = r.data.actions
    })

    axios.get('/api/updateAll', config).then(r => {
      this.updateAll(r)
    })

    // Creating the socket for updates notifications

    // Callback for update event

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

#cssMovingTable td {
  text-align: center;
  vertical-align: middle;
}

.center {
  text-align: center;
  width: 70%;
}

</style>
