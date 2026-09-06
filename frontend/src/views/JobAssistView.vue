<template>
  <section class="advice-page">
    <header class="page-head">
      <div>
        <p class="page-kicker">岗位适配分析</p>
        <h2>岗位定制建议</h2>
      </div>
    </header>

    <div class="advice-content">
      <p class="advice-note">
        以下判断由 AI 生成，引用来自 PDF 解析文本，请对照原文件核对；
        未找到依据不代表你一定不会。
      </p>

      <section class="advice-form">
        <div class="field">
          <label for="assist-resume">选择简历</label>
          <select
            id="assist-resume"
            v-model.number="resumeId"
            :disabled="loading || !resumes.length"
          >
            <option disabled value="">请选择简历</option>
            <option
              v-for="item in resumes"
              :key="item.id"
              :value="item.id"
            >
              {{ item.original_filename }}
            </option>
          </select>
        </div>

        <div class="field-grid">
          <div class="field">
            <label for="job-title">岗位名称</label>
            <input
              id="job-title"
              v-model.trim="jobTitle"
              placeholder="例如：AI 应用开发工程师"
            >
          </div>

          <div class="field">
            <label for="company">公司名称</label>
            <input
              id="company"
              v-model.trim="company"
              placeholder="例如：某科技公司"
            >
          </div>
        </div>

        <div class="field">
          <label for="job-jd">岗位 JD</label>
          <textarea
            id="job-jd"
            v-model="jd"
            rows="8"
            placeholder="粘贴完整岗位职责和任职要求，至少 20 个字"
          ></textarea>
          <span class="field-hint">
            已输入 {{ jd.trim().length }} 个字，至少需要 20 个字
          </span>
        </div>

        <button
          class="analyze-button"
          :disabled="
            loading ||
            !resumeId ||
            jd.trim().length < 20 ||
            !jobTitle.trim() ||
            !company.trim()
          "
          @click="run"
        >
          {{ loading ? '分析中...' : '开始分析' }}
        </button>
      </section>

      <p v-if="err" class="notice error">{{ err }}</p>

      <section class="history-section">
        <div class="history-head">
          <div>
            <p class="section-kicker">REPORT HISTORY</p>
            <h3>历史报告</h3>
          </div>

          <button
            class="ghost-button"
            :disabled="loading || historyBusy"
            @click="loadHistory"
          >
            {{ historyBusy ? '读取中...' : '刷新历史' }}
          </button>
        </div>

        <p class="history-note">
          打开历史报告会恢复当时的表单和分析结果，不会重新调用模型。
        </p>

        <p v-if="historyErr" class="notice error">{{ historyErr }}</p>
        <p v-if="adding || applyMsg" class="notice success" role="status">
          {{ adding ? '正在加入投递管理...' : applyMsg }}
        </p>

        <div
          v-if="!historyBusy && !historyErr && !history.length"
          class="empty-state"
        >
          <span class="empty-icon">⌁</span>
          <strong>还没有历史报告</strong>
          <p>完成第一次岗位分析后，报告会保存在这里。</p>
        </div>

        <div v-else class="history-list">
          <article
            v-for="item in history"
            :key="item.id"
            class="history-row"
          >
            <span class="report-icon">#{{ item.id }}</span>

            <div class="history-info">
              <strong>{{ item.title }}</strong>
              <span>{{ item.company }} · {{ formatDate(item.created_at) }}</span>
            </div>

            <div class="history-actions">
              <button
                class="ghost-button"
                :disabled="loading || historyBusy"
                @click="openReport(item.id)"
              >
                打开报告
              </button>

              <button
                class="primary-small"
                :disabled="adding || loading || historyBusy"
                @click="addApply(item.id)"
              >
                加入投递管理
              </button>
            </div>
          </article>
        </div>
      </section>

      <section v-if="res" class="report-section">
        <div class="report-head">
          <div>
            <p class="section-kicker">MATCH REPORT</p>
            <h3>岗位逐条对照</h3>
          </div>
          <span class="report-count">{{ res.checks.length }} 项判断</span>
        </div>

        <div v-if="!res.needs.length" class="empty-state">
          本次未提取到明确要求，请检查岗位内容是否完整。
        </div>

        <div v-else class="check-list">
          <article
            v-for="item in res.checks"
            :key="item.need_id"
            class="check-card"
          >
            <div class="check-head">
              <div>
                <span class="need-kind">
                  {{ getNeed(item.need_id)?.kind || '岗位要求' }}
                </span>
                <h4>
                  {{ getNeed(item.need_id)?.text || '未找到对应要求' }}
                </h4>
              </div>

              <span
                class="check-status"
                :class="statusClass(item.status)"
              >
                {{ item.status }}
              </span>
            </div>

            <p class="check-note">{{ item.note }}</p>

            <div class="proof-links">
              <a
                v-for="id in item.proof_ids"
                :key="id"
                class="proof-link"
                :href="'#proof-' + id"
              >
                查看资料 {{ id + 1 }}
              </a>

              <span v-if="!item.proof_ids.length" class="no-proof">
                未提供相关引用
              </span>
            </div>
          </article>
        </div>

        <section class="proof-section">
          <div class="report-head">
            <div>
              <p class="section-kicker">RESUME EVIDENCE</p>
              <h3>简历资料引用</h3>
            </div>
          </div>

          <p v-if="!res.proofs.length" class="empty-state">
            没有可展示的简历资料。
          </p>

          <ol v-else class="proof-list">
            <li
              v-for="(text, index) in res.proofs"
              :id="'proof-' + index"
              :key="index"
            >
              <span class="proof-number">{{ index + 1 }}</span>
              <p>{{ text }}</p>
            </li>
          </ol>
        </section>
      </section>
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

function statusClass(status) {
    const classes = {
        '有依据': 'status-good',
        '部分支持': 'status-partial',
        '未找到依据': 'status-missing',
        '待核对': 'status-review'
    }
    return classes[status] ?? 'status-review'
}

function formatDate(value) {
    return new Date(value).toLocaleString()
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
.advice-page {
    width: 100%;
}

.advice-content {
    width: min(100%, 980px);
}

.advice-note {
    margin: 20px 0 24px;
    padding: 14px 18px;
    color: var(--muted);
    line-height: 1.7;
    border: 1px solid var(--border);
    border-radius: 14px;
    background: rgba(76, 141, 255, 0.05);
}

.advice-form {
    padding: 28px;
    border: 1px solid var(--border);
    border-radius: 20px;
    background: var(--panel);
}

.field {
    display: flex;
    flex-direction: column;
    gap: 9px;
}

.field + .field,
.field-grid + .field {
    margin-top: 20px;
}

.field-grid {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 18px;
    margin-top: 20px;
}

.field label {
    color: var(--text);
    font-weight: 600;
}

.field input,
.field select,
.field textarea {
    width: 100%;
    margin: 0;
    color: var(--text);
    border: 1px solid var(--border);
    border-radius: 12px;
    background: var(--panel-soft, #0b1423);
}

.field textarea {
    min-height: 190px;
    resize: vertical;
    line-height: 1.7;
}

.field input:focus,
.field select:focus,
.field textarea:focus {
    border-color: var(--primary);
    box-shadow: 0 0 0 3px rgba(76, 141, 255, 0.13);
}

.field-hint {
    align-self: flex-end;
    color: var(--muted);
    font-size: 0.82rem;
}

.analyze-button {
    width: 100%;
    margin: 24px 0 0;
}

.notice {
    margin: 16px 0 0;
    padding: 12px 16px;
    border-radius: 12px;
}

.notice.error {
    color: #ff9aab;
    border: 1px solid rgba(255, 91, 117, 0.28);
    background: rgba(255, 91, 117, 0.08);
}

.notice.success {
    color: #62e5be;
    border: 1px solid rgba(45, 212, 167, 0.25);
    background: rgba(45, 212, 167, 0.08);
}

.history-section,
.report-section {
    margin-top: 34px;
}

.history-head,
.report-head {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 20px;
}

.history-head h3,
.report-head h3 {
    margin: 3px 0 0;
    font-size: 1.35rem;
}

.section-kicker {
    margin: 0;
    color: var(--primary);
    font-size: 0.72rem;
    font-weight: 700;
    letter-spacing: 0.12em;
}

.history-note {
    margin: 10px 0 18px;
    color: var(--muted);
}

.ghost-button,
.primary-small {
    width: auto;
    min-width: 104px;
    margin: 0;
    padding: 10px 16px;
    border-radius: 10px;
}

.ghost-button {
    color: #a9bce0;
    border: 1px solid var(--border);
    background: transparent;
}

.ghost-button:hover:not(:disabled) {
    color: var(--text);
    border-color: var(--primary);
    background: rgba(76, 141, 255, 0.08);
}

.primary-small {
    color: #08101f;
    border: 0;
    background: linear-gradient(135deg, var(--primary), var(--accent-2));
}

.history-list {
    overflow: hidden;
    border: 1px solid var(--border);
    border-radius: 18px;
    background: var(--panel);
}

.history-row {
    display: grid;
    grid-template-columns: 52px minmax(0, 1fr) auto;
    align-items: center;
    gap: 16px;
    padding: 18px 20px;
}

.history-row + .history-row {
    border-top: 1px solid var(--border);
}

.report-icon {
    display: grid;
    width: 46px;
    height: 46px;
    place-items: center;
    color: #89aaff;
    font-size: 0.78rem;
    font-weight: 700;
    border: 1px solid rgba(76, 141, 255, 0.3);
    border-radius: 12px;
    background: rgba(76, 141, 255, 0.1);
}

.history-info {
    display: flex;
    min-width: 0;
    flex-direction: column;
    gap: 5px;
}

.history-info strong {
    overflow: hidden;
    color: var(--text);
    text-overflow: ellipsis;
    white-space: nowrap;
}

.history-info span {
    color: var(--muted);
    font-size: 0.86rem;
}

.history-actions {
    display: flex;
    gap: 10px;
}

.empty-state {
    display: grid;
    min-height: 170px;
    padding: 28px;
    place-items: center;
    align-content: center;
    gap: 8px;
    color: var(--muted);
    text-align: center;
    border: 1px dashed var(--border);
    border-radius: 18px;
}

.empty-state p {
    margin: 0;
}

.empty-icon {
    display: grid;
    width: 48px;
    height: 48px;
    place-items: center;
    color: var(--primary);
    font-size: 1.5rem;
    border-radius: 14px;
    background: rgba(76, 141, 255, 0.1);
}

.report-count {
    padding: 7px 12px;
    color: #9cb6ec;
    font-size: 0.82rem;
    border: 1px solid var(--border);
    border-radius: 999px;
    background: var(--panel);
}

.check-list {
    display: grid;
    gap: 14px;
    margin-top: 18px;
}

.check-card {
    padding: 22px;
    border: 1px solid var(--border);
    border-radius: 16px;
    background: var(--panel);
}

.check-head {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: 18px;
}

.check-head h4 {
    margin: 7px 0 0;
    font-size: 1.05rem;
    line-height: 1.55;
}

.need-kind {
    color: var(--primary);
    font-size: 0.78rem;
    font-weight: 700;
}

.check-status {
    flex: 0 0 auto;
    padding: 6px 11px;
    font-size: 0.78rem;
    font-weight: 700;
    border: 1px solid;
    border-radius: 999px;
}

.status-good {
    color: #45d9ac;
    border-color: rgba(69, 217, 172, 0.3);
    background: rgba(69, 217, 172, 0.08);
}

.status-partial {
    color: #f6bb54;
    border-color: rgba(246, 187, 84, 0.3);
    background: rgba(246, 187, 84, 0.08);
}

.status-missing {
    color: #ff7c91;
    border-color: rgba(255, 124, 145, 0.3);
    background: rgba(255, 124, 145, 0.08);
}

.status-review {
    color: #9eb2d8;
    border-color: var(--border);
    background: rgba(158, 178, 216, 0.07);
}

.check-note {
    margin: 16px 0;
    color: var(--muted);
    line-height: 1.75;
}

.proof-links {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
}

.proof-link {
    padding: 6px 10px;
    color: #8eabff;
    font-size: 0.8rem;
    text-decoration: none;
    border: 1px solid rgba(76, 141, 255, 0.25);
    border-radius: 8px;
    background: rgba(76, 141, 255, 0.07);
}

.proof-link:hover {
    border-color: var(--primary);
}

.no-proof {
    color: #ff8da0;
    font-size: 0.82rem;
}

.proof-section {
    margin-top: 30px;
}

.proof-list {
    display: grid;
    gap: 12px;
    padding: 0;
    list-style: none;
}

.proof-list li {
    display: grid;
    grid-template-columns: 34px minmax(0, 1fr);
    gap: 14px;
    padding: 17px;
    border: 1px solid var(--border);
    border-radius: 14px;
    background: var(--panel);
    scroll-margin-top: 24px;
}

.proof-list li:target {
    border-color: var(--primary);
    background: rgba(76, 141, 255, 0.09);
    box-shadow: 0 0 0 3px rgba(76, 141, 255, 0.08);
}

.proof-number {
    display: grid;
    width: 32px;
    height: 32px;
    place-items: center;
    color: var(--primary);
    font-weight: 700;
    border-radius: 9px;
    background: rgba(76, 141, 255, 0.1);
}

.proof-list p {
    margin: 2px 0 0;
    color: var(--muted);
    line-height: 1.75;
}

@media (max-width: 900px) {
    .field-grid {
        grid-template-columns: 1fr;
    }

    .history-row {
        grid-template-columns: 46px minmax(0, 1fr);
    }

    .history-actions {
        grid-column: 1 / -1;
    }
}

@media (max-width: 600px) {
    .advice-form,
    .check-card {
        padding: 18px;
    }

    .history-actions {
        flex-direction: column;
    }

    .history-actions button {
        width: 100%;
    }

    .check-head {
        flex-direction: column;
    }
}
</style>