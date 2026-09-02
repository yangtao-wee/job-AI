<template>
  <section>
    <h2>我的简历</h2>

    <input
      type="file"
      accept=".pdf,.docx"
      @change="handleFileChange"
    >

    <button
      :disabled="!selectedFile || uploading"
      @click="uploadResume"
    >
      {{ uploading ? '上传中...' : '上传简历' }}
    </button>

    <p v-if="successMessage">{{ successMessage }}</p>
    <p v-if="errorMessage">{{ errorMessage }}</p>
        <h3>已上传简历</h3>

    <p v-if="loadingList">加载中...</p>
    <p v-else-if=" resumes.length === 0">暂无简历</p>

    <ul v-else>
      <li
        v-for="resume in resumes"
        :key="resume.id"
      >
      编号{{ resume.id }} ·
        {{ resume.original_filename }}
        · {{ formatFileSize(resume.file_size) }}
        · {{ formatDate(resume.created_at) }}
        <button 
        :disabled='analyzingId === resume.id' @click='analyzeResume(resume.id)'
        >
      {{ analyzingId === resume.id ? '分析中...': '分析简历' }}
        </button>



        <button
        :disabled="aiAnalyzingId  ===resume.id" @click="analyzeResumeWithAI(resume.id)">
      {{ aiAnalyzingId  ===resume.id ? 'AI分析中...' : 'AI深度分析' }}
      </button>
                <button
          :disabled="downloadingId === resume.id"
          @click="downloadResume(resume)"
        >
          {{ downloadingId === resume.id ? '下载中...' : '下载' }}
        </button>
                <button
          :disabled="deletingId === resume.id"
          @click="deleteResume(resume.id)"
        >
          {{ deletingId === resume.id ? '删除中...' : '删除' }}
        </button>
      </li>
    </ul>
    <div v-if="analysisResult">
      <h3>简历解析结果</h3>
    <p>
      字符数量：{{ analysisResult.character_count }}
    </p>
    <pre>{{ analysisResult.text }}</pre>
    </div>
    <div v-if="aiAnalysisResult">
      <h3>AI简历分析结果</h3>
      <h4>总体评价</h4>
      <p>{{ aiAnalysisResult.summary }}</p>
      
      <h4>技能</h4>
      <ul>
        <li
        v-for="skill in aiAnalysisResult.skills" :key="skill">
        {{ skill }}
        </li>
      </ul>
      <h4>候选人优势</h4>
      <ul>
        <li
        v-for="strength in aiAnalysisResult.strengths" :key="strength">
      {{ strength }}
      </li>
      </ul>
      <h4>改进建议</h4>
      <ul>
        <li v-for="suggestion in aiAnalysisResult.improvement_suggestions" :key="suggestion">
          {{ suggestion }}
        </li>
      </ul>
      <h4>推荐岗位</h4>
      <ul>
        <li v-for="position in aiAnalysisResult.recommended_positions" :key="position">
          {{ position }}
        </li>
      </ul>
    </div>
  </section>
</template>

<script setup>
import {ref ,onMounted} from 'vue'
import request from '../api/request';

const selectedFile=ref(null)
const uploading=ref(false)
const successMessage=ref('')
const errorMessage=ref('')
const resumes = ref([])
const loadingList = ref(false)
const deletingId = ref(null)
const downloadingId = ref(null)
const analyzingId = ref(null)
const analysisResult =ref(null)
const aiAnalyzingId   = ref (null)
const aiAnalysisResult =ref(null)


function handleFileChange(event){
    selectedFile.value=event.target.files[0] ?? null
    successMessage.value=''
    errorMessage.value=''
}
async function getMyResumes() {
  loadingList.value=true
  try{
    const response = await request.get('/resumes/me')
    resumes.value = response.data
  }catch(error){
    errorMessage.value=error.response?.data?.detail ?? '简历列表加载失败'
  }finally{
    loadingList.value=false
  }
}

async function deleteResume(resumeId) {
  const confirmed = window.confirm('确认删除这份简历吗')
  if(!confirmed)return
  deletingId.value = resumeId
  successMessage.value=''
  errorMessage.value=''

  try{
    await request.delete(`/resumes/${resumeId}`)
    successMessage.value = '简历删除成功'
    await getMyResumes()
  }catch(error){
    errorMessage.value=
      error.response?.data?.detail ?? '删除失败,请稍后重试'
  }finally{
    deletingId.value=null
  }
}
async function downloadResume(resume) {
  downloadingId.value = resume.id
  successMessage.value=''
  errorMessage.value=''
  try{
    const response = await request.get(`/resumes/${resume.id}/download`,
      {
        responseType:'blob'
      }
    )
    const fileUrl = URL.createObjectURL(response.data)
    const link = document.createElement('a')
    link.href = fileUrl
    link.download=resume.original_filename

    document.body.appendChild(link)
    link.click()
    link.remove()
    setTimeout(() => {
       URL.revokeObjectURL(fileUrl)
    }, 1000);
   

  }catch(error){
    errorMessage.value=
    error.response?.data?.detail ?? '下载失败,请稍后重试'
  }finally{
    downloadingId.value=null
  }
}

async function analyzeResume(resumeId) {
    analyzingId.value=resumeId
    analysisResult.value=null
    successMessage.value=''
    errorMessage.value=''

    try{
      const response = await request.post(
        `/resumes/${resumeId}/analyze`
      )
      analysisResult.value = response.data
      successMessage.value=`解析成功,共提取${response.data.character_count}个字符`
    }catch(error){
      errorMessage.value=error.response?.data?.detail ?? '简历分析失败'
    }finally{
      analyzingId.value=null
    }
}

async function analyzeResumeWithAI(resumeId) {
  aiAnalyzingId .value=resumeId
  aiAnalysisResult.value=null
  successMessage.value=''
  errorMessage.value=''
  try{
    const response = await request.post(
      `/resumes/${resumeId}/analyze?use_ai=true`,null,{
        timeout:60000
      }
    ) 
    const data=response.data
    if(data.ai_ok){
      aiAnalysisResult.value=data
      successMessage.value='AI分析完成'
    }else{
      errorMessage.value=data.summary}  
  }catch(error){
    errorMessage.value=error.response?.data?.detail ?? 'AI分析失败'
  }finally{
    aiAnalyzingId .value=null
  }
}

function formatFileSize(size){
  return `${(size / 1024).toFixed(1)}KB`
}
function formatDate(value){
  return new Date(value).toLocaleString()
}
async function uploadResume(){
    if(!selectedFile.value) return

    uploading.value=true
    successMessage.value=''
    errorMessage.value=''

    const formData = new FormData()
    formData.append('file',selectedFile.value)

    try{
        const response = await request.post('/resumes/upload',formData)
        successMessage.value =  `上传成功：${response.data.filename}`
        await getMyResumes()
    }catch(error){
        errorMessage.value=error.response?.data?.detail ?? '上传失败,请稍后重试'
    }finally{
        uploading.value=false
    }
}
onMounted(getMyResumes)
</script>