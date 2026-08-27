<template>
    <div class='staus'>

    
    <p>{{ message }}</p>
    </div >
</template>

<script setup>
import { ref,onMounted } from 'vue'
import request from '../api/request'
const message = ref('检测服务器中...')
async function checkBackend(){
    try{
        const response = await request.get('/health')
        if(response.data.status==='ok'){
            message.value='🟢后端接收成功'
        }
    }catch(error){
        message.value="🔴后端连接失败"
    }
}

onMounted(()=>{
    checkBackend()
})
</script>

<style>
.status{
    margin-top: 20px;
    font-size: 20px;
}
</style>