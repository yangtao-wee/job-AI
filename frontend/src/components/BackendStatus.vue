<template>
  <div class="backend-status">
    <span
      class="status-dot"
      :class="{ offline: connected === false }"
    ></span>

    <span>{{ message }}</span>
  </div>
</template>

<script setup>
import { ref,onMounted } from 'vue'
import request from '../api/request'
const message = ref('检测服务器中...')
const connected = ref(null)
async function checkBackend(){
    try{
        const response = await request.get('/health')
        if(response.data.status==='ok'){
            message.value = '系统已连接'
            connected.value = true
        }
    }catch(error){
        message.value = '系统连接失败'
        connected.value = false
    }
}

onMounted(()=>{
    checkBackend()
})
</script>



