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
        <h3>求职方案</h3>
      </div>

      <div class="positions-box">
        <p class="positions-tip">
          每个岗位按每套方案各打一次分，取分最高的那套，岗位池里会标出是哪套。每一栏一行写一个。<br />
          「只投初级 / 助理」里的方向，岗位标题要带 初级、助理、应届 才给分；
          JD 要求的经验达到「经验上限」就压到 50 分；加分词出现在标题、标签或 JD 里，每个加 5 分，最多 10 分。
        </p>
        <p v-if="!newestResume" class="empty-message">先上传简历并做一次 AI 分析。</p>
        <template v-else>
          <div v-for="(t, i) in targets" :key="i" class="target-card">
            <div class="target-head">
              <input v-model="t.name" class="target-name" maxlength="20" placeholder="方案名，比如 简历A" />
              <label class="target-years">
                经验上限
                <input v-model.number="t.max_years" type="number" min="1" max="15" placeholder="按简历" />
                年
              </label>
              <label class="target-years">
                最低月薪
                <input v-model.number="t.min_pay" type="number" min="1" max="100" placeholder="不限" />
                K
              </label>
              <button class="target-remove" @click="targets.splice(i, 1)">删除这套</button>
            </div>
            <div class="target-grid">
              <label>求职方向<textarea v-model="t.positions" rows="8" class="positions-input"></textarea></label>
              <label>只投初级 / 助理<textarea v-model="t.junior" rows="8" class="positions-input"></textarea></label>
              <label>备选方向（扣5分）<textarea v-model="t.backup" rows="8" class="positions-input"></textarea></label>
              <label>加分词<textarea v-model="t.good_words" rows="8" class="positions-input"></textarea></label>
            </div>
          </div>
          <div class="positions-actions">
            <button v-if="targets.length < 5" class="target-add" @click="addTarget">加一套方案</button>
            <button :disabled="savingTargets" @click="saveTargets">
              {{ savingTargets ? '重新打分中，大约要一分钟…' : '保存并重新打分' }}
            </button>
            <span v-if="targetsMessage" class="positions-message">{{ targetsMessage }}</span>
          </div>
        </template>
      </div>

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
            <h4>工作经历</h4>
            <ul>
              <li
                v-for="(item, index) in aiAnalysisResult.work_experience"
                :key="index"
              >
                {{ item }}
              </li>
            </ul>
          </section>

          <section v-if="aiAnalysisResult.projects?.length">
            <h4>项目经历</h4>
            <ul>
              <li
                v-for="(item, index) in aiAnalysisResult.projects"
                :key="`project-${index}`"
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
import {ref ,onMounted, computed, watch} from 'vue'
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

// ---------- 求职方案 ----------
const targets = ref([])
const savingTargets = ref(false)
const targetsMessage = ref('')
// 插件用编号最大的那份简历，重新打分也用它读学历和年限
const newestResume = computed(() =>
  resumes.value.reduce((a, b) => (!a || b.id > a.id ? b : a), null)
)

// 输入框里一行一个 ↔ 接口里是列表
const toText = list => (list || []).join('\n')
const toList = text => text.split('\n').map(s => s.trim()).filter(Boolean)

async function loadTargets() {
  try {
    const res = await request.get('/targets')
    targets.value = res.data.targets.map(t => ({
      name: t.name,
      max_years: t.max_years ?? '',
      min_pay: t.min_pay ?? '',
      positions: toText(t.positions),
      junior: toText(t.junior),
      backup: toText(t.backup),
      good_words: toText(t.good_words),
    }))
  } catch (error) {
    const detail = error.response?.data?.detail
    targetsMessage.value = typeof detail === 'string' ? detail : '读取求职方案失败'
  }
}

function addTarget() {
  targets.value.push({ name: `方案${targets.value.length + 1}`, max_years: '', min_pay: '', positions: '', junior: '', backup: '', good_words: '' })
}

async function saveTargets() {
  const body = targets.value.map(t => ({
    name: t.name.trim(),
    max_years: t.max_years === '' || t.max_years == null ? null : Number(t.max_years),
    min_pay: t.min_pay === '' || t.min_pay == null ? null : Number(t.min_pay),
    positions: toList(t.positions),
    junior: toList(t.junior),
    backup: toList(t.backup),
    good_words: toList(t.good_words),
  }))
  if (!body.length) {
    targetsMessage.value = '至少留一套方案'
    return
  }
  const empty = body.find(t => !t.positions.length)
  if (empty) {
    targetsMessage.value = `方案「${empty.name}」至少填一个求职方向`
    return
  }
  savingTargets.value = true
  targetsMessage.value = ''
  try {
    await request.put('/targets', { targets: body })
    // 全部岗位重新打分要几十秒，单独放宽超时
    const res = await request.post('/leads/rescore', { resume_id: newestResume.value.id }, { timeout: 300000 })
    targetsMessage.value = `已保存。岗位池 ${res.data.total} 个岗位重新打分，60 分以上 ${res.data.passed} 个`
    await loadTargets()
  } catch (error) {
    const detail = error.response?.data?.detail
    targetsMessage.value = typeof detail === 'string' ? detail : '保存失败'
  } finally {
    savingTargets.value = false
  }
}

loadTargets()


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
        timeout:180000
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

/* ---------- 求职方向 ---------- */
.positions-box {
  padding: 18px 20px;
  border: 1px solid var(--border, #232c40);
  border-radius: 14px;
  background: var(--panel, #0e1320);
  margin-bottom: 28px;
}
.positions-tip { margin: 0 0 10px; font-size: 12.5px; line-height: 1.8; color: var(--muted, #8a94ab); }
.positions-for { margin: 0 0 8px; font-size: 13px; color: var(--text, #e8ecf5); }
.positions-input {
  width: 100%;
  box-sizing: border-box;
  padding: 10px 12px;
  border: 1px solid var(--border, #2a3348);
  border-radius: 10px;
  background: #0f1425;
  color: #e8ecf5;
  font: inherit;
  font-size: 14px;
  line-height: 1.7;
  resize: vertical;
}
.positions-input:focus { outline: none; border-color: var(--primary, #35c48a); }
.positions-actions { display: flex; align-items: center; gap: 12px; margin-top: 10px; flex-wrap: wrap; }
.positions-message { font-size: 13px; color: var(--muted, #8a94ab); }
.target-card { padding: 14px 16px; border: 1px solid var(--border, #2a3348); border-radius: 12px; margin-bottom: 12px; }
.target-head { display: flex; align-items: center; gap: 12px; flex-wrap: wrap; margin-bottom: 10px; }
.target-name,
.target-years input {
  padding: 6px 10px;
  border: 1px solid var(--border, #2a3348);
  border-radius: 8px;
  background: #0f1425;
  color: #e8ecf5;
  font: inherit;
  font-size: 14px;
}
.target-name { flex: 1 1 160px; max-width: 220px; }
.target-years { display: flex; align-items: center; gap: 6px; font-size: 13px; color: var(--muted, #8a94ab); }
.target-years input { width: 80px; }
.target-remove { margin-left: auto; }
.target-grid { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 12px; }
.target-grid label { display: flex; flex-direction: column; gap: 6px; font-size: 13px; color: var(--muted, #8a94ab); }
@media (max-width: 760px) {
  .target-grid { grid-template-columns: 1fr; }
}
</style>
