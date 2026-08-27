<template>
    <h2>岗位列表</h2>
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
    <p v-if="matchError">{{ matchError }}</p>
    <JobCard 
    v-for="job in jobs"
    :key="job.id"
    :title="job.title"
    :salary="job.salary"
    :current-score="job.currentScore"
    :current-max-score="job.currentMaxScore"
    :score="job.score"
    :matched-skills="job.matchedSkills"
    :missing-skills="job.missingSkills"
    :keyword-score=job.keywordScore
    :matched-keywords=job.matchedKeywords
    :missing-keywords=job.missingKeywords
    :matching="matchingId === job.id"
    @match="handleMatch(job)"
    />
</template>

<script setup>
import { ref,onMounted } from 'vue'
import {fetchJobs,matchJob} from '../api/jobs.js'
import JobCard from '../components/JobCard.vue'
import { fetchMyResumes } from '../api/resumes.js'
const jobs = ref([])
const resumes = ref([])
const selectedResumeId = ref(null)
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
            const response = await matchJob(selectedResumeId.value,job.id)
            const skillMatch = response.data.skill_match
            job.score=skillMatch.score
            job.matchedSkills = skillMatch.matched_skills
            job.missingSkills = skillMatch.missing_skills
            const keywordMatch = response.data.keyword_match
            job.keywordScore = keywordMatch.score
            job.matchedKeywords = keywordMatch.matched_keywords
            job.missingKeywords = keywordMatch.missing_keywords
            job.currentScore=response.data.current_score
            job.currentMaxScore=response.data.current_max_score
        }catch(error){
            matchError.value=error.response?.data?.detail ?? '岗位匹配失败'
        }finally{
            matchingId.value=null
        }
       
    }
    onMounted(()=>{
        getJobs()
        getMyResumes()
    })
    
    
</script>