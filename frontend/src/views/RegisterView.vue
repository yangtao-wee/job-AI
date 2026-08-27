<template>
  <main>
    <h2>用户注册</h2>

    <form @submit.prevent="handleRegister">
      <label for="username">用户名</label>
      <input
        id="username"
        v-model="form.username"
        type="text"
        required
      >

      <label for="email">邮箱</label>
      <input
        id="email"
        v-model="form.email"
        type="email"
        required
      > 
      <label for="password">密码</label>
      <input
        id="password"
        v-model="form.password"
        type="password"
        minlength="6"
        required
      >

      <button type="submit" :disabled="isLoading">{{isLoading ? '注册中...' : '注册'}}</button>
    </form>
    <p v-if="errorMessage">
        {{ errorMessage }}
    </p>
    <p>
      已有账号？
      <RouterLink :to="{ name: 'login' }">返回登录</RouterLink>
    </p>
  </main>
</template>

<script setup>
import { reactive,ref } from 'vue'
import request  from '../api/request'
import {useRouter} from 'vue-router'
const form = reactive({
  username: '',
  email: '',
  password: ''
})
const errorMessage=ref('')
const router=useRouter()
const isLoading = ref(false)
async function handleRegister() {
    if(isLoading.value) return
     isLoading.value=true
    errorMessage.value=""
  try{
    const response = await request.post('/users/register',{
        username:form.username,
        email:form.email,
        password:form.password
    })
    console.log('注册成功',response.data)
    await router.push({name:'login'})
  }catch(error){
    errorMessage.value=
    error.response?.data.detail || '注册失败,请稍后重试'
    console.log('注册失败：',error.response?.data)
  }finally{
    isLoading.value=false
  }

}
</script>