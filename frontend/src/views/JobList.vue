<template>
    <section class="jobs-page">
    <header class="page-head">
  <div>
    <p class="page-kicker">求职工作台</p>
    <h2>岗位列表</h2>
  </div>

  <span class="job-count">
    共 {{ jobs.length }} 个岗位
  </span>
</header>

    <div class="jobs-layout">
    <aside class="filter-panel">
        <h3>筛选条件</h3>
    <div>
    <label for="resume-select">选择简历：</label> 
    <select id="resume-select" v-model.number="selectedResumeId"
    :disabled="resumes.length === 0"
    >
    <option :value="null" disabled>
        请选择简历
    </option>
    <option v-for='resume in resumes' :key="resume.id" :value="resume.id">
        {{ resume.original_filename }}
    </option>
    </select>
    <p v-if="resumes.length===0">请先上传简历</p>
    </div>
    <div>
        <label>期望城市：</label>
        <input v-model.trim="city" placeholder="例如：深圳">
        <label>最低月薪(K)：</label>
        <input v-model.number="minPay" type="number" min="0">
    </div>
    <p v-if="matchError">{{ matchError }}</p>
        </aside>

    <section class="job-area">
        <h3>为你推荐</h3>
        <div class="job-grid">
<JobCard 
    v-for="(job, index) in jobs"
    :key="job.id"
    :featured="index === 0"
    :title="job.title"
    :company="job.company"
    :location="job.location"
    :salary="job.salary"
    :description="job.description"
    :current-score="job.currentScore"
    :current-max-score="job.currentMaxScore"
    :score="job.score"
    :matched-skills="job.matchedSkills"
    :missing-skills="job.missingSkills"
    :keyword-score=job.keywordScore
    :matched-keywords=job.matchedKeywords
    :missing-keywords=job.missingKeywords
    :matching="matchingId === job.id"
    :requirements="job.requirements"
    :required-skill-score="job.requiredSkillScore"
    :matched-required-skills="job.matchedRequiredSkills"
    :missing-required-skills="job.missingRequiredSkills"
    :exp-score="job.expScore"
    :exp-hits="job.expHits"
    :exp-miss="job.expMiss"
    :role-score="job.roleScore"
    :role-note="job.roleNote"
    :pref-score="job.prefScore"
    :pref-notes="job.prefNotes"
    :sem="job.sem"
    :ai-note="job.aiNote"
    @match="handleMatch(job)"
    />
            </div>
    </section>
    </div>
</section>
</template>

<script setup>
import { ref,onMounted } from 'vue'
import {fetchJobs,matchJob} from '../api/jobs.js'
import JobCard from '../components/JobCard.vue'
import { fetchMyResumes } from '../api/resumes.js'

const jobs = ref([])
const resumes = ref([])
const selectedResumeId = ref(null)
const city = ref('深圳')
const minPay = ref(15)
const matchingId = ref(null)
const matchError = ref('')

async function getJobs(){
    const response = await fetchJobs()
    jobs.value=response.data
}

async function getMyResumes() {
    const response = await fetchMyResumes()
    resumes.value=response.data
    selectedResumeId.value=resumes.value[0]?.id ?? null
}

async function handleMatch(job) {
    if(!selectedResumeId.value)return
    matchingId.value=job.id
    matchError.value=''
    try{
        const response = await matchJob(selectedResumeId.value,job.id,city.value,minPay.value)
        job.requirements = response.data.job_requirements
        const skillMatch = response.data.skill_match
        job.score=skillMatch.score
        job.matchedSkills = skillMatch.matched_skills
        job.missingSkills = skillMatch.missing_skills
        const keywordMatch = response.data.keyword_match
        const requiredSkillMatch = response.data.required_skill_match
        job.requiredSkillScore = requiredSkillMatch.score
        job.matchedRequiredSkills=requiredSkillMatch.matched_skills
        job.missingRequiredSkills=requiredSkillMatch.missing_skills
        job.keywordScore = keywordMatch.score
        job.matchedKeywords = keywordMatch.matched_keywords
        job.missingKeywords = keywordMatch.missing_keywords
        job.currentScore=response.data.current_score
        job.currentMaxScore=response.data.current_max_score
        const exp =response.data.experience_match
        job.expScore=exp.score
        job.expHits=exp.matches
        job.expMiss=exp.missing_responsibilities
        const role=response.data.role_match
        job.roleScore=role.score
        job.roleNote=role.note
        const pref =response.data.pref_match
        job.prefScore=pref.score
        job.prefNotes=pref.notes
        job.sem=response.data.sem_match
        job.aiNote=response.data.ai_explain
    }catch(error){
        matchError.value=error.response?.data?.detail ?? error.message ?? '岗位匹配失败'
    }finally{
        matchingId.value=null
    }
    
}


onMounted(()=>{
    getJobs()
    getMyResumes()
})
    
    
</script>

