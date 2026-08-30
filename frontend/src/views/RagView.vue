<template>
    <section>
        <h2>求职知识问答</h2>
        <textarea v-model="q" placeholder="请输入问题"></textarea>
        <button :disabled="loading || !q.trim()" @click="ask">{{ loading ? '回答中...':'提问' }}</button>
        <!-- trim 是【语言固定】JavaScript字符串方法，用来去掉首尾空格，避免用户只输入空格也能提交。 -->
         <!-- || 表示任意一个条件成立就禁用按钮。 -->
        <p v-if="err">{{ err }}</p>
        <div v-if="res">
            <p>{{ res.answer }}</p>
            <p>资料足够：{{ res.enough?'是':'否' }}</p>
            <ul>
                <li v-for="source in res.sources" :key="source.text">{{ source.text }}(相似度：{{ source.score.toFixed(2) }})</li>
                <!-- toFixed(2)：【语言固定】JavaScript数字方法，保留两位小数。 -->
            </ul>
        </div>
    </section>
</template>

<script setup>
import {ref} from 'vue'
import { askRag } from '../api/rag';
const q=ref('')
const loading=ref(false)
const res=ref(null)
const err=ref('')
async function ask() {
    loading.value=true
    res.value=null
    err.value=''
    try{
        const response=await askRag(q.value)
        res.value=response.data
    }catch(error){
        err.value=error.response?.data?.detail ?? '回答失败'
    }finally{
        loading.value=false
    }
}
</script>