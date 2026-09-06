<template>
  <section class="resume-page">
    <header class="page-head">
      <div>
        <p class="page-kicker">求职工作台</p>
        <h2>我的简历</h2>
      </div>
    </header>

    <div class="resume-content">
      <label class="dropzone">
        <input
          class="file-input"
          type="file"
          accept=".pdf,.docx"
          @change="handleFileChange"
        >

        <span class="upload-icon">
          <svg viewBox="0 0 24 24">
            <path d="M12 16V3M6 9l6-6 6 6M5 21h14" />
          </svg>
        </span>

        <strong>点击选择你的简历</strong>

        <span class="upload-description">
          支持 PDF、DOCX 文件
        </span>

        <span class="choose-button">
          选择文件
        </span>
      </label>

      <div
        v-if="selectedFile"
        class="upload-ready"
      >
        <div>
          <span class="ready-label">已选择文件</span>
          <strong>{{ selectedFile.name }}</strong>
        </div>

        <button
          :disabled="uploading"
          @click="uploadResume"
        >
          {{ uploading ? '上传中...' : '上传简历' }}
        </button>
      </div>

      <p
        v-if="successMessage"
        class="notice success"
      >
        {{ successMessage }}
      </p>

      <p
        v-if="errorMessage"
        class="notice error"
      >
        {{ errorMessage }}
      </p>

      <div class="section-heading">
        <span></span>
        <h3>已上传简历</h3>
      </div>

      <p
        v-if="loadingList"
        class="empty-message"
      >
        正在读取简历列表...
      </p>

      <p
        v-else-if="resumes.length === 0"
        class="empty-message"
      >
        还没有简历，请先在上方选择并上传文件。
      </p>

      <div
        v-else
        class="resume-list"
      >
        <article
          v-for="resume in resumes"
          :key="resume.id"
          class="resume-card"
        >
          <span class="file-icon">
            <svg viewBox="0 0 24 24">
              <path d="M7 3h7l5 5v13H6V4Z" />
              <path d="M14 3v5h5" />
            </svg>
          </span>

          <div class="resume-info">
            <strong>{{ resume.original_filename }}</strong>

            <span>
              编号 {{ resume.id }}
              · {{ formatFileSize(resume.file_size) }}
              · {{ formatDate(resume.created_at) }}
            </span>
          </div>

          <div class="resume-actions">
            <button
              class="ghost-button"
              :disabled="analyzingId === resume.id"
              @click="analyzeResume(resume.id)"
            >
              {{
                analyzingId === resume.id
                  ? '分析中...'
                  : '分析简历'
              }}
            </button>

            <button
              class="ghost-button"
              :disabled="aiAnalyzingId === resume.id"
              @click="analyzeResumeWithAI(resume.id)"
            >
              {{
                aiAnalyzingId === resume.id
                  ? 'AI分析中...'
                  : 'AI深度分析'
              }}
            </button>

            <button
              class="ghost-button"
              :disabled="downloadingId === resume.id"
              @click="downloadResume(resume)"
            >
              {{
                downloadingId === resume.id
                  ? '下载中...'
                  : '下载'
              }}
            </button>

            <button
              class="ghost-button danger-button"
              :disabled="deletingId === resume.id"
              @click="deleteResume(resume.id)"
            >
              {{
                deletingId === resume.id
                  ? '删除中...'
                  : '删除'
              }}
            </button>
          </div>
        </article>
      </div>

      <article
        v-if="analysisResult"
        class="result-panel"
      >
        <div class="section-heading">
          <span></span>
          <h3>简历解析结果</h3>
        </div>

        <p class="result-meta">
          共提取
          <strong>
            {{ analysisResult.character_count }}
          </strong>
          个字符
        </p>

        <pre>{{ analysisResult.text }}</pre>
      </article>

      <article
        v-if="aiAnalysisResult"
        class="result-panel ai-result"
      >
        <div class="section-heading">
          <span></span>
          <h3>AI 简历分析结果</h3>
        </div>

        <section class="summary-block">
          <h4>总体评价</h4>
          <p>{{ aiAnalysisResult.summary }}</p>
        </section>

        <div class="analysis-grid">
          <section>
            <h4>技能</h4>
            <ul>
              <li
                v-for="skill in aiAnalysisResult.skills"
                :key="skill"
              >
                {{ skill }}
              </li>
            </ul>
          </section>

          <section>
            <h4>提取的经历</h4>
            <ul>
              <li
                v-for="(item, index) in aiAnalysisResult.work_experience"
                :key="index"
              >
                {{ item }}
              </li>
            </ul>
          </section>

          <section>
            <h4>候选人优势</h4>
            <ul>
              <li
                v-for="strength in aiAnalysisResult.strengths"
                :key="strength"
              >
                {{ strength }}
              </li>
            </ul>
          </section>

          <section>
            <h4>改进建议</h4>
            <ul>
              <li
                v-for="item in aiAnalysisResult.improvement_suggestions"
                :key="item"
              >
                {{ item }}
              </li>
            </ul>
          </section>
        </div>

        <section class="position-block">
          <h4>推荐岗位</h4>

          <div class="position-tags">
            <span
              v-for="position in aiAnalysisResult.recommended_positions"
              :key="position"
            >
              {{ position }}
            </span>
          </div>
        </section>
      </article>
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
  const confirmed = window.confirm(
  '确认删除这份简历吗？关联的分析、报告和投递记录也会一起删除。'
)
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

<style scoped>
.resume-content {
  max-width: 900px;
}

.dropzone {
  min-height: 230px;
  padding: 42px 24px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 10px;
  border: 1.5px dashed var(--border);
  border-radius: 20px;
  background: rgba(11, 17, 27, 0.72);
  color: var(--muted);
  cursor: pointer;
  transition:
    border-color 0.2s ease,
    background 0.2s ease;
}

.dropzone:hover {
  border-color: var(--primary);
  background: rgba(76, 141, 255, 0.04);
}

.dropzone strong {
  color: var(--text);
  font-size: 16px;
}

.file-input {
  position: absolute;
  width: 1px !important;
  height: 1px;
  min-height: 0 !important;
  padding: 0 !important;
  overflow: hidden;
  opacity: 0;
  pointer-events: none;
}

.upload-icon,
.file-icon {
  display: grid;
  place-items: center;
  color: var(--primary);
  background:
    linear-gradient(
      160deg,
      rgba(76, 141, 255, 0.18),
      rgba(139, 92, 246, 0.1)
    );
  border: 1px solid
    rgba(76, 141, 255, 0.25);
}

.upload-icon {
  width: 54px;
  height: 54px;
  border-radius: 14px;
}

.upload-icon svg,
.file-icon svg {
  width: 22px;
  height: 22px;
  fill: none;
  stroke: currentColor;
  stroke-width: 1.8;
  stroke-linecap: round;
  stroke-linejoin: round;
}

.upload-description {
  color: var(--muted);
  font-size: 13px;
}

.choose-button {
  margin-top: 8px;
  padding: 8px 15px;
  border: 1px solid var(--border);
  border-radius: 8px;
  color: var(--text);
  background: var(--panel-strong);
  font-size: 13px;
}

.upload-ready {
  margin-top: 16px;
  padding: 16px 18px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 20px;
  border: 1px solid var(--border);
  border-radius: 12px;
  background: var(--panel);
}

.upload-ready div {
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.upload-ready strong {
  overflow: hidden;
  color: var(--text);
  text-overflow: ellipsis;
  white-space: nowrap;
}

.ready-label {
  color: var(--muted);
  font-size: 12px;
}

.notice {
  margin-top: 16px;
  padding: 12px 15px;
  border: 1px solid;
  border-radius: 10px;
}

.notice.success {
  color: #34d399;
  border-color: rgba(52, 211, 153, 0.3);
  background: rgba(52, 211, 153, 0.07);
}

.notice.error {
  color: #f0687a;
  border-color: rgba(240, 104, 122, 0.3);
  background: rgba(240, 104, 122, 0.07);
}

.section-heading {
  margin: 32px 0 16px;
  display: flex;
  align-items: center;
  gap: 9px;
}

.section-heading > span {
  width: 3px;
  height: 17px;
  border-radius: 999px;
  background:
    linear-gradient(
      var(--primary),
      var(--accent-2)
    );
}

.section-heading h3 {
  margin: 0;
  color: var(--text);
  font-size: 16px;
}

.empty-message {
  padding: 28px;
  border: 1px dashed var(--border);
  border-radius: 12px;
  text-align: center;
}

.resume-list {
  display: grid;
  gap: 12px;
}

.resume-card {
  margin: 0;
  padding: 20px;
  display: grid;
  grid-template-columns: 46px minmax(0, 1fr) auto;
  align-items: center;
  gap: 20px;
  border: 1px solid var(--border);
  border-radius: 16px;
  background: var(--panel);
  box-shadow: none;
}

.file-icon {
  width: 46px;
  height: 46px;
  border-radius: 12px;
}

.resume-info {
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 5px;
}

.resume-info strong {
  overflow: hidden;
  color: var(--text);
  font-size: 15px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.resume-info span {
  color: #5a6577;
  font-family:
    "JetBrains Mono",
    Consolas,
    monospace;
  font-size: 12px;
}

.resume-actions {
  display: flex;
  flex-wrap: wrap;
  justify-content: flex-end;
  gap: 8px;
}

.resume-actions .ghost-button {
  padding: 8px 12px;
  color: var(--muted);
  border: 1px solid var(--border);
  background: transparent;
  font-size: 12px;
}

.resume-actions .ghost-button:hover {
  color: var(--text);
  background: var(--panel-strong);
}

.resume-actions .danger-button {
  color: #f0687a;
}

.result-panel {
  margin: 24px 0 0;
  padding: 24px;
  color: var(--muted);
  border: 1px solid var(--border);
  border-radius: 20px;
  background: var(--panel);
  box-shadow: none;
}

.result-panel .section-heading {
  margin-top: 0;
}

.result-meta strong {
  color: var(--text);
  font-family:
    "JetBrains Mono",
    Consolas,
    monospace;
}

.result-panel pre {
  max-height: 420px;
  margin: 16px 0 0;
  padding: 18px;
  overflow: auto;
  color: var(--muted);
  border: 1px solid var(--border);
  border-radius: 12px;
  background: var(--bg);
  white-space: pre-wrap;
}

.summary-block {
  padding: 18px;
  border: 1px solid
    rgba(76, 141, 255, 0.2);
  border-radius: 12px;
  background: rgba(76, 141, 255, 0.05);
}

.summary-block h4,
.analysis-grid h4,
.position-block h4 {
  margin: 0 0 10px;
  color: var(--text);
}

.analysis-grid {
  margin-top: 18px;
  display: grid;
  grid-template-columns:
    repeat(2, minmax(0, 1fr));
  gap: 14px;
}

.analysis-grid section {
  padding: 18px;
  border: 1px solid var(--border);
  border-radius: 12px;
  background: var(--bg);
}

.analysis-grid ul {
  margin: 0;
  padding-left: 20px;
}

.analysis-grid li {
  margin-bottom: 7px;
}

.position-block {
  margin-top: 20px;
}

.position-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.position-tags span {
  padding: 7px 11px;
  color: var(--primary);
  border: 1px solid
    rgba(76, 141, 255, 0.25);
  border-radius: 999px;
  background: rgba(76, 141, 255, 0.08);
  font-size: 12px;
}

@media (max-width: 760px) {
  .resume-card {
    grid-template-columns: 46px minmax(0, 1fr);
  }

  .resume-actions {
    grid-column: 1 / -1;
    justify-content: flex-start;
  }

  .analysis-grid {
    grid-template-columns: 1fr;
  }

  .upload-ready {
    align-items: stretch;
    flex-direction: column;
  }
}
</style>