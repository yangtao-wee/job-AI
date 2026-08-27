<template>
    <h2>用户登录</h2>
    <!-- @submit.prevent="handleLogin"会阻止页面刷新，然后调用登录函数。 -->
    <form @submit.prevent="handleLogin">
        <label for="username">用户名</label>
        <input id="username" v-model="form.username" type="text" required>
        <label for="password">密码</label>
        <input type="password"  id="password" v-model="form.password" required>
        <button type="submit" :disabled="isLoading">{{ isLoading? '登录中...' : '登录' }}</button>
    </form>
    <p>还没有账号？<RouterLink :to="{name:'register'}">立即注册</RouterLink></p>
    <p v-if="errorMessage">{{ errorMessage }}</p>
    <p v-if="currentUser">
        欢迎{{ currentUser.username }}
    </p>
</template>

<script setup>
// reactive：让 Vue 追踪 form里的数据变化，像实时更新的登记表。
import { reactive,ref } from 'vue';
import request from '../api/request';
import { useRouter } from 'vue-router';
// useRouter：取得 Vue Router 的导航功能。
const form = reactive({
    username:"",
    password:""
})
const currentUser = ref(null)
const errorMessage = ref('')
const isLoading = ref(false)
const router = useRouter()
async function handleLogin(){
    if(isLoading.value)return
    isLoading.value=true
    errorMessage.value=''
    // 第二次登录时先清除上一次的错误，像重新办理业务前清空旧提示。
    try{
        const response= await request.post('/users/login',{
            username:form.username,
            password:form.password
        })
        const token = response.data.access_token
        // .access_token：从返回数据中取出身份令牌。token：需要保存的实际内容。
        localStorage.setItem('access_token',token)
        // setItem()：把数据放进储物柜。
        const userResponse = await request.get('/users/me')
        currentUser.value=userResponse.data
        await router.push({name:'jobs'})
        console.log('登录成功',response.data)
    }catch(error){
        errorMessage.value=error.response?.data?.detail || '登录失败,请稍后重试'
        // 某层数据不存在时不会再次报错。
        console.log('登录失败',error.response?.data)
        // ?.避免没有响应时再次报错。
    }finally{
        // finally：无论登录成功还是失败，最后都会执行。
        isLoading.value=false
    }

}
</script>