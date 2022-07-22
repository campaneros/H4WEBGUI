import Vue from 'vue'
import Router from 'vue-router'
import HelloWorld from '@/components/HelloWorld'
import WebguiMain from '@/components/WebguiMain'
import MovingTable from '@/components/MovingTable'
import Webcam from '@/components/Webcam'
import Dqm from '@/components/Dqm'
import DqmMon from '@/components/DqmMon'
import Trigger from '@/components/Trigger'
import Power from '@/components/Power'

Vue.use(Router)

export default new Router({
    routes: [
	{
	    path: '/hello-world',
	    name: 'hello-world',
	    component: HelloWorld
	},
	{
	    path: '/webgui-main',
	    name: 'webgui-main',
	    component: WebguiMain
	},
	{
	    path: '/table',
	    name: 'table',
	    component: MovingTable
	},
	{
	    path: '/webcam',
	    name: 'webcam',
	    component: Webcam
	},
	{
	    path: '/dqm',
	    name: 'dqm',
	    component: Dqm
	},
	{
	    path: '/dqmmon',
	    name: 'dqmmon',
	    component: DqmMon
	},
	{
	    path: '/trigger',
	    name: 'trigger',
	    component: Trigger
	},
	{
	    path: '/power',
	    name: 'power',
	    component: Power
	}
    ]
})
