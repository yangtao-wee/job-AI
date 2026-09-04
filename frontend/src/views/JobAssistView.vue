<template>
    <section>
        <h2>岗位定制建议</h2>
        <p>以下判断由AI生成，引用来自PDF解析文本，请对照原文件核对；未找到依据不代表你一定不会。</p>
        <select v-model.number="resumeId" :disabled="loading || !resumes.length" aria-label="选择简历">
            <option disabled value="">请选择简历</option>
            <option v-for="item in resumes" :key="item.id" :value="item.id">{{ item.original_filename }}</option>
        </select>
        <input v-model="jobTitle" placeholder="岗位名称">
        <input v-model="company" placeholder="公司名称">
        <textarea v-model="jd" placeholder="粘贴岗位JD，至少20个字"></textarea>
        <button :disabled="loading || !resumeId || !jd.trim() || !jobTitle.trim() || !company.trim()"  @click="run">{{ loading ? '分析中...' : '开始分析' }}</button>
        <p v-if="err">{{ err }}</p>
        <section>
    <h3>历史报告（最近20份）</h3>
    <p>打开历史会恢复当时的表单和报告，不重新调用模型。</p>
    <button :disabled="loading || historyBusy" @click="loadHistory">
        {{ historyBusy ? '读取中...' : '刷新历史' }}
    </button>
    <p v-if="historyErr">{{ historyErr }}</p>
        <p role="status">{{ adding ? '加入中...' : applyMsg }}</p>
    <p v-if="!historyBusy && !historyErr && !history.length">暂无已保存报告。</p>
    <ul>
        <li v-for="item in history" :key="item.id">
            {{ item.title }} · {{ item.company }} · {{ item.created_at }}
            <button :disabled="loading || historyBusy" @click="openReport(item.id)">打开报告</button>
                        <button :disabled="adding || loading || historyBusy" @click="addApply(item.id)">
                加入投递管理
            </button>
        </li>
    </ul>
</section>
        <div v-if="res">
    <h3>岗位逐条对照</h3>
    <p v-if="!res.needs.length">本次未提取到明确要求，请核对岗位内容。</p>
    <ul>
        <li v-for="item in res.checks" :key="item.need_id">
            <p>{{ getNeed(item.need_id)?.kind }}：{{ getNeed(item.need_id)?.text }}</p>
            <p>模型判断：{{ item.status }}</p>
            <p>判断理由：{{ item.note }}</p>
            <a v-for="id in item.proof_ids" :key="id" :href="'#proof-' + id">
                查看资料{{ id + 1 }}
            </a>
            <span v-if="!item.proof_ids.length">未提供相关引用</span>
        </li>
    </ul>
    <h3>简历资料（PDF解析文本）</h3>
    <p v-if="!res.proofs.length">没有可展示的简历资料。</p>
    <ol>
        <li v-for="(text, i) in res.proofs" :key="i" :id="'proof-' + i">
            {{ text }}
        </li>
    </ol>
</div>
    </section>
</template>

<script setup>
import {ref,onMounted} from 'vue'
import { assistJob,fetchRoprt,fetchRoprts } from '../api/jobAssist';
import { fetchMyResumes } from '../api/resumes';
import { createApply } from '../api/apply';
const resumeId=ref('')
const resumes=ref([])
const jobTitle=ref('')
const company=ref('')
const jd=ref('')
const loading=ref(false)
const res=ref(null)
const err=ref('')
const history=ref([])
const historyBusy=ref(false)
const historyErr=ref('')
const adding = ref(false)
const applyMsg = ref('')
async function addApply(id) {
    if (adding.value) return
    adding.value = true
    applyMsg.value = ''
    try {
        await createApply(id)
        applyMsg.value = '已加入投递管理，可点击顶部“投递管理”查看'
    } catch {
        applyMsg.value = '加入失败，请重试'
    } finally {
        adding.value = false
    }
}

async function loadHistory() {
    if(historyBusy.value) return
    historyBusy.value=true
    historyErr.value=''
    try{
        const response = await fetchRoprts()
        history.value = response.data 
    }catch(error){
        historyErr.value='历史列表读取失败，请点击刷新历史重试'
    }finally{
        historyBusy.value=false
    }
}

async function openReport(id) {
    if(loading.value) return
    loading.value=true
    err.value=''
    res.value=null
    try{
        const response = await fetchRoprt(id)
        const row = response.data
        resumeId.value=row.resume_id
        jobTitle.value=row.title
        company.value=row.company
        jd.value=row.jd
        res.value=row.content
    }catch(error){
        err.value='报告读取失败，请确认记录仍存在且属于当前账号'
    }finally{
        loading.value=false
    }
}



function getNeed(id){
    return res.value.needs.find(item=>item.id===id)
}

onMounted(async()=>{
    loadHistory()
    try{
        const response=await fetchMyResumes()
        resumes.value=response.data
    }catch(error){
        err.value=error.response?.data?.detail ?? '简历列表加载失败'
    }
})

async function run() {
    loading.value=true
    res.value=null
    err.value=''
    try{
        const response = await assistJob(Number(resumeId.value),jobTitle.value,company.value,jd.value)
        res.value=response.data
        await loadHistory()
    }catch(error){
        err.value=error.response?.data?.detail ?? '分析失败'
    }finally{
        loading.value=false
    }
}
</script>

<style scoped>
li:target {
    background-color: #fff3bf;
    outline: 2px solid #e0a800;
    scroll-margin-top: 24px;
}
</style>