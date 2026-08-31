<template>
    <section>
        <h2>AI求职助手</h2>
        <textarea v-model="goal" placeholder="请输入求职目标"></textarea>
        <button :disabled="loading || !goal.trim()" @click="run">{{ loading? '执行中':'执行' }}</button>
        <p v-if="answer">{{ answer }}</p>
    </section>
</template>

<script setup>
import {ref} from 'vue'
import { askAgent } from '../api/agent'
const goal = ref('')
const answer = ref('')
const loading =ref(false)
async function run(){
    loading.value=true
    answer.value=''
    try{
        const res=await askAgent(goal.value)
        answer.value=res.data.answer
    }catch(error){
        answer.value=error.response?.data?.detail ?? '执行失败'
    }finally{
        loading.value=false
    }
}
</script>