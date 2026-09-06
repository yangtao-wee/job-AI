import ResumePrintView from '../views/ResumePrintView.vue'
import {createRouter,createWebHistory} from 'vue-router'
// createRouter创建路由管理器。createWebHistory负责管理浏览器地址。
import JobList from '../views/JobList.vue'
import LoginView from '../views/LoginView.vue' 
import RegisterView from '../views/RegisterView.vue'
import ResumeView from '../views/ResumeView.vue'
import RagView  from '../views/RagView.vue'
import AgentView from '../views/AgentView.vue'
import JobAssistView from '../views/JobAssistView.vue'
import ApplyView  from '../views/ApplyView.vue'
const router=createRouter({
history:createWebHistory(),
    routes:[
        {
        path:'/',
        name:'home',
        component:JobList
    },

        
        {
        path:'/jobs',
        name:'jobs',
        component:JobList,
        meta:{
            requiresAuth:true
// meta：给路由附加说明，像在办公室门上贴标签。
// requiresAuth：表示该页面需要登录。
// // true：确认必须检查登录状态。
        }
    },
    {
        path:'/resumes',
        name:'resumes',
        component:ResumeView,
        meta:{
            requiresAuth:true
        }

    },
        {
        path:'/resume-print',
        name:'resume-print',
        component:ResumePrintView,
        meta:{requiresAuth:true}
    },
    {
        path:'/rag',
        name:'rag',
        component:RagView,
        meta:{requiresAuth:true}
    },
    {
        path:'/agent',
        name:'agent',
        component:AgentView,
        meta:{requiresAuth:true}
    },
    {
        path:'/assist',
        name:'assist',
        component:JobAssistView,
        meta:{requiresAuth:true}
    },
    {
        path:'/login',
        name:'login',
        component:LoginView
    },
    {
        path:'/applications',
        name:'applications',
        component:ApplyView,
        meta:{requiresAuth:true}
    },
    {
        path:'/register',
        name:'register',
        component:RegisterView
    }
    

]
})

router.beforeEach((to)=>{
    const token = localStorage.getItem('access_token')
    if(to.meta.requiresAuth && !token){
        return {name:'login'}
    }
// beforeEach：每次页面跳转之前都会执行，像办公区入口保安。
// to：用户准备前往的路由。
// getItem()：读取浏览器中保存的 Token。
// to.meta.requiresAuth：目标页面是否要求登录。
// &&：两个条件必须同时成立。
// !token：当前没有 Token。
// return { name: 'login' }：阻止原跳转，改去登录页面。
// 条件不成立时函数正常结束，允许继续进入目标页面。
})
export default router
