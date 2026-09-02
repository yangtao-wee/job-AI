<template>
    <section>
        <h2>岗位定制建议</h2>
        <input v-model="resumeId" placeholder="简历编号，例如 1">
        <input v-model="jobTitle" placeholder="岗位名称">
        <input v-model="company" placeholder="公司名称">
        <textarea v-model="jd" placeholder="粘贴岗位JD，至少20个字"></textarea>
        <button :disabled="loading || !resumeId || !jd.trim() || !jobTitle.trim() || !company.trim()"  @click="run">{{ loading ? '分析中...' : '开始分析' }}</button>
        <p v-if="err">{{ err }}</p>
        <div v-if="res">
            <p>匹配分：{{ res.score }}</p>
            <p>已具备：{{ res.matched_skills.join('、') }}</p>
            <p>缺少的：{{ res.missing_skills.join('、') }}</p>
            <h3>简历怎么改</h3>
            <p>{{ res.tailoring.summary }}</p>
            <ul>
                <li v-for="item in res.tailoring.suggestions" :key="item.requirement">
                    <p>岗位要求：{{ item.requirement }}</p>
                    <p>你的建议：{{ item.evidence }}</p>
                    <p>建议写成：{{ item.rewrite }}</p>
                </li>
            </ul>
            <h3>打招呼语</h3>
            <p>{{ res.greeting }}</p>
        </div>
    </section>
</template>

<script setup>
import {ref} from 'vue'
import { assistJob } from '../api/jobAssist';

const resumeId=ref('')
const jobTitle=ref('')
const company=ref('')
const jd=ref('')
const loading=ref(false)
const res=ref(null)
const err=ref('')

async function run() {
    loading.value=true
    res.value=null
    err.value=''
    try{
        const response = await assistJob(Number(resumeId.value),jobTitle.value,company.value,jd.value)
        res.value=response.data
    }catch(error){
        err.value=error.response?.data?.detail ?? '分析失败'
    }finally{
        loading.value=false
    }
}
</script>