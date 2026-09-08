<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import request from '../api/request'

const leads = ref([])
const total = ref(0)
const offset = ref(0)
const pageSize = 50
const resumes = ref([])
const loading = ref(false)
const error = ref('')
const filter = ref('')
const minShow = ref(0)
// 精判参数
const resumeId = ref(null)
const minScore = ref(60)

// 精判进行中的状态
const running = ref(false)
const stopped = ref(false)
const doneCount = ref(0)
const lastTitle = ref('')
const remaining = ref(0)

const FILTERS = [
  { value: '', label: '全部' },
  { value: '新抓取', label: '新抓取' },
  { value: '待投递', label: '待投递' },
  { value: '已投递', label: '已投递' },
  { value: '已跳过', label: '已跳过' },
]

async function load() {
  loading.value = true
  error.value = ''
  try {
    const params = {
      offset: offset.value,
      limit: pageSize,
      status: filter.value || undefined,
    }
    const res = await request.get('/leads', { params })
    leads.value = res.data.items
    total.value = res.data.total
  } catch (e) {
    error.value = e.response?.data?.detail || e.message || '加载失败'
  } finally {
    loading.value = false
  }
}

async function loadResumes() {
  try {
    const res = await request.get('/resumes/me')
    resumes.value = res.data
    if (!resumeId.value && res.data.length) resumeId.value = res.data[0].id
  } catch (e) {
    // 简历列表拿不到不影响看岗位池
  }
}

onMounted(() => { load(); loadResumes() })
onUnmounted(() => { stopped.value = true })
function pick(value) {
  filter.value = value
  offset.value = 0
  load()
}

// 单条改状态。改完只更新本地这一行，不重新拉整个列表。
async function setStatus(lead, status) {
  try {
    const res = await request.patch(`/leads/${lead.id}`, { status })
    Object.assign(lead, res.data)
  } catch (e) {
    error.value = e.response?.data?.detail || '状态更新失败'
  }
}

async function markAbove() {
  
  try {
    const res = await request.post('/leads/mark-above', { above: minScore.value })
    error.value = ''
    await load()
    lastTitle.value = res.data.marked
      ? `已标记 ${res.data.marked} 个岗位为待投递`
      : `没有符合条件的岗位（需要：状态是「新抓取」且分数 ≥ ${minScore.value}）`
  } catch (e) {
    error.value = e.response?.data?.detail || '批量标记失败'
  }
}

async function unmarkAll() {
  if (!confirm('把所有「待投递」的岗位撤回「新抓取」？已投递的不动。')) return
  try {
    const res = await request.post('/leads/unmark')
    error.value = ''
    await load()
    lastTitle.value = `已撤销 ${res.data.unmarked} 个待投递标记`
  } catch (e) {
    error.value = e.response?.data?.detail || '撤销失败'
  }
}


// 精判：一次一个，循环调用。前端驱动，随时可停。
async function runAnalyze() {
  if (!resumeId.value) {
    error.value = '请先选择一份简历'
    return
  }
  running.value = true
  stopped.value = false
  doneCount.value = 0
  error.value = ''
  try {
    while (!stopped.value) {
      const res = await request.post(
        '/leads/analyze',
        { resume_id: resumeId.value, min_score: minScore.value },
        { timeout: 300000 },   // 单次精判可能 20-70 秒，默认 5 秒远远不够
      )
      const d = res.data
      if (!d.analyzed) {
        lastTitle.value = doneCount.value ? '全部精判完成' : '没有符合条件的岗位'
        remaining.value = 0
        break
      }
      doneCount.value += 1
      lastTitle.value = d.title
      remaining.value = d.remaining
      // 把结果写回列表里对应那一行，不用重新拉整个列表
      const row = leads.value.find(l => l.id === d.lead_id)
      if (row) {
        row.deep_ok = d.deep_ok
        row.deep_part = d.deep_part
        row.deep_total = d.deep_total
        row.deep_at = new Date().toISOString()
      }
    }
  } catch (e) {
    error.value = e.response?.data?.detail || e.message || '精判失败'
  } finally {
    running.value = false
  }
}

function tone(score) {
  if (score >= 60) return 'high'
  if (score >= 30) return 'mid'
  return 'low'
}

const shown = computed(() =>
  leads.value.filter(l =>
    l.quick_score >= minShow.value &&
    (!filter.value || l.status === filter.value)
  )
)
</script>

<template>
  <div class="wrap">
    <div class="head">
      <div>
        <h2>岗位池</h2>
        <p class="sub">
          插件抓到的岗位会存到这里。分数是规则粗筛的结果（只看职位名和标签）。
          先把不想投的标为「跳过」，再对剩下的做精判——精判会调大模型，每个约 20-70 秒。
        </p>
      </div>
      <button class="btn ghost" :disabled="loading || running" @click="load">
        {{ loading ? '加载中…' : '刷新' }}
      </button>
    </div>

    <!-- 精判控制条 -->
    <div class="panel">
      <label class="f">
        简历
        <select v-model="resumeId" :disabled="running">
          <option v-for="r in resumes" :key="r.id" :value="r.id">
            {{ r.original_filename || ('简历 #' + r.id) }}
          </option>
        </select>
      </label>
      <label class="f">
        最低分数
        <input v-model.number="minScore" type="number" min="0" max="100" :disabled="running">
      </label>

      <button v-if="!running" class="btn" @click="runAnalyze">开始精判</button>
      <button v-else class="btn stop" :disabled="stopped" @click="stopped = true">
  {{ stopped ? '正在停止…' : '停止' }}
</button>

      <button class="btn go" :disabled="running" @click="markAbove">
        ↑ 标记 {{ minScore }} 分以上
      </button>

      <button class="btn ghost" :disabled="running" @click="unmarkAll">
        ↩ 全部撤销待投
      </button>
      <div v-if="running || lastTitle" class="progress">
        <span v-if="running" class="dot"></span>
        <span v-if="doneCount">已完成 {{ doneCount }} 个</span>
        <span v-if="remaining">· 还剩 {{ remaining }}</span>
        <span v-if="lastTitle" class="cur">· {{ lastTitle }}</span>
      </div>
    </div>

    <div class="bar">
      <button
        v-for="f in FILTERS"
        :key="f.value"
        class="chip"
        :class="{ on: filter === f.value }"
        @click="pick(f.value)"
      >
        {{ f.label }}
        <span v-if="f.value && filter === f.value" class="n">{{ total }}</span>
      </button>
      <label class="minshow">
        分数 ≥
        <input v-model.number="minShow" type="number" min="0" max="100">
      </label>
      <button class="chip" :disabled="offset === 0 || loading"
        @click="offset = Math.max(0, offset - pageSize); load()">
        上一页
      </button>
      <button class="chip" :disabled="offset + pageSize >= total || loading"
        @click="offset += pageSize; load()">
        下一页
      </button>
      <span class="total">
        显示 {{ shown.length }} / 本页 {{ leads.length }} / 共 {{ total }} 条
      </span>
    </div>

    <p v-if="error" class="err">{{ error }}</p>

    <div v-if="!loading && !leads.length" class="empty">
      <div class="empty-t">这里还没有岗位</div>
      <div class="empty-s">打开 BOSS 直聘搜索岗位，插件会自动打分并把结果存到这里。</div>
    </div>

    <ul v-else class="list">
      <li
        v-for="l in shown"
        :key="l.id"
        class="row"
        :class="[tone(l.quick_score), { off: l.status === '已跳过' }]"
      >
        <div class="score">{{ l.quick_score }}</div>

        <div class="mid">
          <a :href="l.url" target="_blank" rel="noopener" class="title">{{ l.title }}</a>
          <div class="meta">
            <span class="company">{{ l.company || '未标公司' }}</span>
            <span v-for="t in l.tags" :key="t" class="tag">{{ t }}</span>
          </div>
        </div>

        <div class="deep">
          <template v-if="l.deep_at">
            <span class="ok">{{ l.deep_ok }}</span> 有依据
            <span class="part">{{ l.deep_part }}</span> 部分
            <span class="dim">/ {{ l.deep_total }}</span>
          </template>
          <span v-else class="dim">未精判</span>
        </div>

        <div class="status" :class="'st-' + l.status">{{ l.status }}</div>

        <div class="ops">
          <button
      v-if="l.status !== '已投递'"
      class="mini"
      :disabled="running"
      @click="setStatus(l, '已投递')"
      >已投</button>
            
          <button
            v-if="l.status !== '已跳过'"
            class="mini"
            :disabled="running"
            @click="setStatus(l, '已跳过')"
          >跳过</button>
          <button
            v-else
            class="mini"
            :disabled="running"
            @click="setStatus(l, '新抓取')"
          >恢复</button>
          <button
            v-if="l.status !== '待投递'"
            class="mini go"
            :disabled="running"
            @click="setStatus(l, '待投递')"
          >要投</button>
        </div>
      </li>
    </ul>
  </div>
</template>

<style scoped>
.wrap { max-width: 1080px; margin: 0 auto; padding: 4px 0 40px; }

.head { display: flex; align-items: flex-start; justify-content: space-between; gap: 20px; }
h2 { margin: 0 0 6px; font-size: 1.5rem; }
.sub { margin: 0 0 16px; color: #7f8aa3; font-size: 12.5px; line-height: 1.75; max-width: 700px; }

.panel {
  display: flex;
  align-items: flex-end;
  gap: 12px;
  flex-wrap: wrap;
  padding: 14px 16px;
  border: 1px solid #212a3d;
  border-radius: 12px;
  background: #0e1320;
  margin-bottom: 14px;
}
.f { display: flex; flex-direction: column; gap: 5px; font-size: 12px; color: #9aa5bd; }
select, input[type=number] {
  background: #0f1425;
  border: 1px solid #2a3348;
  border-radius: 7px;
  padding: 7px 10px;
  font-size: 13px;
  color: #e8ecf5;
  font-family: inherit;
}
input[type=number] { width: 92px; }
select { min-width: 190px; }

.btn {
  padding: 8px 18px;
  border: 1px solid #0b7a4b;
  background: #0b7a4b;
  color: #fff;
  border-radius: 8px;
  cursor: pointer;
  font-size: 13px;
  white-space: nowrap;
}
.btn:disabled { opacity: .5; cursor: default; }
.btn.ghost { background: transparent; color: #35c48a; }
.btn.stop { background: #8a2f2f; border-color: #8a2f2f; }
.btn.go { background: #1d5fb8; border-color: #1d5fb8; }

.progress { color: #9aa5bd; font-size: 12.5px; display: flex; align-items: center; gap: 6px; }
.cur { color: #35c48a; }
.dot {
  width: 7px; height: 7px; border-radius: 50%;
  background: #35c48a;
  animation: blink 1s infinite;
}
@keyframes blink { 0%,100% { opacity: 1 } 50% { opacity: .25 } }

.bar { display: flex; align-items: center; gap: 8px; margin-bottom: 12px; flex-wrap: wrap; }
.chip {
  padding: 5px 14px;
  border: 1px solid #2a3348;
  background: #0f1425;
  color: #9aa5bd;
  border-radius: 999px;
  cursor: pointer;
  font-size: 12px;
}
.chip.on { border-color: #0b7a4b; background: #0b7a4b; color: #fff; }
.n { opacity: .75; margin-left: 4px; }
.total { color: #6b7590; font-size: 12px; margin-left: auto; }

.err { color: #ff8a80; font-size: 13px; }

.empty { border: 1px dashed #2a3348; border-radius: 14px; padding: 56px 24px; text-align: center; }
.empty-t { color: #c3ccdf; font-size: 15px; font-weight: 600; margin-bottom: 8px; }
.empty-s { color: #6b7590; font-size: 12.5px; line-height: 1.8; }

.list { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: 8px; }

.row {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 11px 16px;
  border: 1px solid #212a3d;
  border-left-width: 3px;
  border-radius: 10px;
  background: #0e1320;
}
.row.high { border-left-color: #0b7a4b; }
.row.mid  { border-left-color: #b6791a; }
.row.low  { border-left-color: #39425a; }
.row.off  { opacity: .45; }

.score { flex: 0 0 42px; text-align: center; font-size: 17px; font-weight: 700; color: #c3ccdf; }
.row.high .score { color: #35c48a; }
.row.mid .score  { color: #e0a03a; }

.mid { flex: 1; min-width: 0; }
.title {
  color: #e8ecf5; font-size: 14px; text-decoration: none;
  display: inline-block; max-width: 100%;
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}
.title:hover { color: #35c48a; text-decoration: underline; }
.meta { display: flex; align-items: center; gap: 8px; margin-top: 5px; flex-wrap: wrap; }
.company { color: #8390aa; font-size: 12px; }
.tag { color: #6b7590; font-size: 11px; border: 1px solid #232c40; border-radius: 4px; padding: 1px 6px; }

.deep { flex: 0 0 150px; font-size: 12px; color: #8390aa; white-space: nowrap; }
.deep .ok { color: #35c48a; font-weight: 700; }
.deep .part { color: #e0a03a; font-weight: 700; }
.dim { color: #5c6580; }

.status {
  flex: 0 0 auto; font-size: 12px; padding: 3px 10px;
  border-radius: 999px; border: 1px solid #2a3348; color: #8390aa; white-space: nowrap;
}
.status.st-待投递 { border-color: #0b7a4b; color: #35c48a; }
.status.st-已投递 { border-color: #2f5fb8; color: #6f9bff; }
.status.st-已跳过 { border-color: #3a3f52; color: #656e86; }

.ops { flex: 0 0 auto; display: flex; gap: 6px; }
.mini {
  padding: 4px 10px; font-size: 12px;
  border: 1px solid #2a3348; background: transparent;
  color: #9aa5bd; border-radius: 6px; cursor: pointer; white-space: nowrap;
}
.mini:hover { border-color: #3d4863; color: #c3ccdf; }
.mini.go:hover { border-color: #0b7a4b; color: #35c48a; }
.mini:disabled { opacity: .4; cursor: default; }
</style>
