<script setup>
import { ref, computed, watch, onMounted, onUnmounted } from 'vue'
import request from '../api/request'
import ScorePicker from '../components/ScorePicker.vue'

const leads = ref([])
const total = ref(0)
const offset = ref(0)
const pageSize = 50
const resumes = ref([])
const loading = ref(false)
const error = ref('')
const filter = ref('')
const minShow = ref(0)
// 排序方式。这三个名字必须和后端 lead_service.py 里 ORDERS 的键一模一样。
const ORDER_OPTIONS = ['分数高', '分数低', '最新']
const order = ref('分数高')
// 搜索和分类：关键词搜标题、公司（勾选后也搜 JD 正文）；分档、方向由后端按分数和标题现算
const keyword = ref('')
const inJd = ref(false)
const kind = ref('')
const tierPick = ref('')
const kinds = ref({})
const tiers = ref({})
const filtering = computed(() => Boolean(keyword.value.trim() || kind.value || tierPick.value || filter.value || minShow.value))
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

const stats = ref(null)
// 补读 JD：交给插件在 BOSS 上挨个打开详情页读取，一次读多少个自己选
const READ_LIMITS = [20, 50, 100, 200, 500]
const readLimit = ref(50)
const reading = ref(false)

async function loadStats() {
  try {
    const res = await request.get('/leads/stats')
    stats.value = res.data
  } catch (e) {
    stats.value = null
  }
}

function countOf(value) {
  const s = stats.value
  if (!s) return ''
  if (!value) return s.total
  if (value === '待投递') return s.to_apply
  if (value === '已投递') return s.applied
  if (value === '已跳过') return s.skipped
  return s.total - s.to_apply - s.applied - s.skipped
}

// 打字很快时会连发好几次请求，只认最后一次的结果，免得旧结果盖掉新结果
let loadSeq = 0
async function load() {
  const seq = ++loadSeq
  loading.value = true
  error.value = ''
  try {
    const params = {
      offset: offset.value,
      limit: pageSize,
      status: filter.value || undefined,
      min_score: minShow.value || undefined,
      order: order.value,
      q: keyword.value.trim() || undefined,
      in_jd: inJd.value || undefined,
      kind: kind.value || undefined,
      tier: tierPick.value || undefined,
    }
    const res = await request.get('/leads', { params })
    if (seq !== loadSeq) return
    leads.value = res.data.items
    total.value = res.data.total
    kinds.value = res.data.kinds || {}
    tiers.value = res.data.tiers || {}
  } catch (e) {
    if (seq !== loadSeq) return
    error.value = e.response?.data?.detail || e.message || '加载失败'
  } finally {
    if (seq === loadSeq) {
      loading.value = false
      loadStats()
    }
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

// 从 BOSS 看完岗位切回这个标签页时自动刷新：插件在详情页读到 JD 会重新打分，不刷新还显示旧分
function onVisible() {
  if (document.visibilityState === 'visible' && !running.value) load()
}

onMounted(() => {
  load()
  loadResumes()
  document.addEventListener('visibilitychange', onVisible)
})
onUnmounted(() => {
  stopAnalyze()
  clearTimeout(searchTimer)
  document.removeEventListener('visibilitychange', onVisible)
})
function pick(value) {
  filter.value = value
  offset.value = 0
  load()
}

// 分档、方向的「全部」对应空值
function pickTier(name) {
  tierPick.value = name === '全部' ? '' : name
  offset.value = 0
  load()
}

function pickKind(name) {
  kind.value = name === '全部' ? '' : name
  offset.value = 0
  load()
}

function isOn(picked, name) {
  return (name === '全部' ? '' : name) === picked
}

// 停止打字 0.3 秒后再搜，不用每敲一个字就查一次
let searchTimer = null
watch(keyword, () => {
  clearTimeout(searchTimer)
  searchTimer = setTimeout(() => { offset.value = 0; load() }, 300)
})
watch(inJd, () => {
  if (!keyword.value.trim()) return
  offset.value = 0
  load()
})

// 单条改状态。改完只更新本地这一行，不重新拉整个列表。
async function setStatus(lead, status) {
  try {
    const res = await request.patch(`/leads/${lead.id}`, { status })
    Object.assign(lead, res.data)
    loadStats()
  } catch (e) {
    error.value = e.response?.data?.detail || '状态更新失败'
  }
}

// 删除一条岗位。已投递的后端会拒（409），这里也不显示按钮，双保险。
async function removeLead(lead) {
  if (!confirm(`确定删除「${lead.title}」？\n删掉后插件再抓到它，会当成没见过的新岗位重新收进来。`)) return
  try {
    await request.delete(`/leads/${lead.id}`)
    leads.value = leads.value.filter(l => l.id !== lead.id)
    total.value -= 1
    error.value = ''
    loadStats()
  } catch (e) {
    error.value = e.response?.data?.detail || '删除失败'
  }
}

// 一键删除未投递：跟着当前选中的标签走。
// 「全部」删所有未投递的；「新抓取 / 待投递 / 已跳过」只删这一类；「已投递」不让删。
async function deleteUnapplied() {
  if (filter.value === '已投递') return
  if (!stats.value) await loadStats()
  const n = filter.value ? countOf(filter.value) : countOf('') - countOf('已投递')
  const label = filter.value ? `「${filter.value}」` : '所有未投递'
  if (!n) {
    lastTitle.value = `没有${label}的岗位可删`
    return
  }
  const ok = confirm(
    `即将删除${label}的 ${n} 个岗位。\n\n` +
    `· 「已投递」的一个都不会动\n` +
    `· 删除后无法恢复\n` +
    `· 插件下次抓到它们，会当成没见过的新岗位重新收进来\n\n` +
    `确定删除？`
  )
  if (!ok) return
  try {
    const res = await request.post('/leads/delete-unapplied', { status: filter.value || null })
    error.value = ''
    offset.value = 0
    await load()
    lastTitle.value = `已删除 ${res.data.deleted} 个岗位`
  } catch (e) {
    error.value = e.response?.data?.detail || '批量删除失败'
  }
}

async function deleteWithoutJd() {
  const n = stats.value?.without_jd || 0
  if (!n) {
    lastTitle.value = '没有未获取岗位介绍的岗位'
    return
  }
  const ok = confirm(
    `即将删除 ${n} 个未获取岗位介绍的岗位。\n\n` +
    `· 已投递岗位不会删除\n` +
    `· 删除后无法恢复\n` +
    `· 插件以后再次抓到时，会重新加入岗位池\n\n` +
    `确定删除？`
  )
  if (!ok) return
  try {
    const res = await request.post('/leads/delete-without-jd')
    error.value = ''
    offset.value = 0
    await load()
    lastTitle.value = `已删除 ${res.data.deleted} 个未获取岗位介绍的岗位`
  } catch (e) {
    error.value = e.response?.data?.detail || '删除未获取岗位介绍的岗位失败'
  }
}

// 岗位池网页和插件的传话：网页把要读的岗位发给插件（bridge.js），插件存好队列后回信
function askExtension(queue) {
  return new Promise((resolve, reject) => {
    const timer = setTimeout(() => {
      window.removeEventListener('message', onReply)
      reject(new Error('插件没有响应：在 Chrome 扩展页把「求职助手」重新加载，再刷新本页'))
    }, 3000)
    function onReply(event) {
      if (event.source !== window || event.data?.source !== 'jm-ext' || event.data.type !== 'read-jd') return
      clearTimeout(timer)
      window.removeEventListener('message', onReply)
      if (event.data.ok) resolve(event.data)
      else reject(new Error(event.data.error || '插件拒绝了补读'))
    }
    window.addEventListener('message', onReply)
    window.postMessage({
      source: 'jm-pool',
      type: 'read-jd',
      queue: queue.map(j => ({ id: j.id, url: j.url, title: j.title })),
    }, window.location.origin)
  })
}

async function startReadJd() {
  if (document.documentElement.dataset.jmBridge !== '1') {
    error.value = '没检测到插件：在 Chrome 扩展页把「求职助手」重新加载，再刷新本页'
    return
  }
  // 新标签页必须在点击的瞬间打开，否则会被浏览器当成弹窗拦掉；先开空白页，队列交给插件后再跳到 BOSS
  const tab = window.open('about:blank', '_blank')
  if (!tab) {
    error.value = '浏览器拦截了新标签页，请允许本页打开弹出窗口'
    return
  }
  reading.value = true
  error.value = ''
  try {
    const res = await request.get('/leads/unread-jd', { params: { limit: readLimit.value } })
    const queue = res.data.items
    if (!queue.length) {
      tab.close()
      lastTitle.value = '没有要补读的岗位'
      return
    }
    await askExtension(queue)
    tab.opener = null
    tab.location.href = queue[0].url
    lastTitle.value = `已交给插件补读 ${queue.length} 个岗位（在新打开的 BOSS 标签页里，连续读 10 分钟歇 1 分钟）`
  } catch (e) {
    tab.close()
    error.value = e.response?.data?.detail || e.message || '补读失败'
  } finally {
    reading.value = false
  }
}

// 岗位池每行的标签：合适 / 不合适的点（旧数据没有时退回 JD 能力项和门槛）
function prosOf(l) {
  return l.pros ?? l.jd_hits ?? []
}

function consOf(l) {
  return l.cons ?? l.jd_flags ?? []
}

// 分数怎么来的：先按标题打分，读过 JD 再按 JD 加减
function scoreNote(l) {
  if (l.base_score == null || !l.quick_score) return ''
  return l.has_jd ? `标题${l.base_score}分 → 看完JD ${l.quick_score}分` : `标题${l.base_score}分，读了JD才算数`
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


let aborter = null
const sleep = ms => new Promise(r => setTimeout(r, ms))

function stopAnalyze() {
  stopped.value = true
  aborter?.abort()
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
      aborter = new AbortController()
      let res
      try {
        res = await request.post(
          '/leads/analyze',
          { resume_id: resumeId.value, min_score: minScore.value },
          { timeout: 300000, signal: aborter.signal },
        )
      } catch (e) {
        if (e.code === 'ERR_CANCELED') break
        if (e.response?.status === 503) {
          lastTitle.value = '上一个还在收尾，3 秒后自动重试…'
          await sleep(3000)
          continue
        }
        throw e
      }
      const d = res.data
      if (!d.analyzed) {
        lastTitle.value = doneCount.value ? '全部精判完成' : '没有符合条件的岗位'
        remaining.value = 0
        break
      }
      doneCount.value += 1
      lastTitle.value = d.title
      remaining.value = d.remaining
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
    aborter = null
    if (stopped.value) {
      lastTitle.value = `已停止（本次完成 ${doneCount.value} 个）`
    }
  }
}

// 分档：没读 JD 的先不算数；55 分以上可投可不投；60 分以上建议投
function tier(l) {
  if (!l.has_jd) return '待读JD'
  if (l.quick_score >= 60) return '建议投'
  if (l.quick_score >= 55) return '可投可不投'
  return '先不看'
}

function tone(score) {
  if (score >= 60) return 'high'
  if (score >= 30) return 'mid'
  return 'low'
}

watch(minShow, () => { offset.value = 0; load() })
// 换排序方式要回到第一页，否则会停在一个不存在的页码上。
watch(order, () => { offset.value = 0; load() })
</script>

<template>
  <div class="wrap">
    <div class="head">
      <div>
        <h2>岗位池</h2>
        <p class="sub">
          插件抓到的岗位会存到这里。已读 JD 显示最终粗筛分，未读 JD 只显示临时初筛分。
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
      <ScorePicker v-model="minScore" :min="40" :disabled="running" />
      </label>

      <button v-if="!running" class="btn" @click="runAnalyze">开始精判</button>
      <button v-else class="btn stop" @click="stopAnalyze">停止</button>

      <button class="btn go" :disabled="running" @click="markAbove">
        ↑ 标记 {{ minScore }} 分以上
      </button>

      <button class="btn ghost" :disabled="running" @click="unmarkAll">
        ↩ 全部撤销待投
      </button>

      <button class="btn ghost" :disabled="running || !stats?.without_jd" @click="deleteWithoutJd">
        清理未读JD {{ stats?.without_jd || 0 }}
      </button>

      <label class="f">
        每次补读
        <select v-model="readLimit" class="sort" :disabled="running || reading">
          <option v-for="n in READ_LIMITS" :key="n" :value="n">{{ n }} 个</option>
        </select>
      </label>
      <button class="btn go" :disabled="running || reading || !stats?.unread_jd" @click="startReadJd">
        📖 补读JD {{ stats?.unread_jd || 0 }}
      </button>

      <button class="btn danger" :disabled="running || filter === '已投递'" @click="deleteUnapplied">
        🗑 {{ filter ? `删除「${filter}」` : '删除未投递' }}
      </button>
      <div v-if="running || lastTitle" class="progress">
        <span v-if="running" class="dot"></span>
        <span v-if="doneCount">已完成 {{ doneCount }} 个</span>
        <span v-if="remaining">· 还剩 {{ remaining }}</span>
        <span v-if="lastTitle" class="cur">· {{ lastTitle }}</span>
      </div>
    </div>

    <div class="filters">
      <div class="search">
        <input
          v-model="keyword"
          class="kw"
          type="search"
          placeholder="搜岗位名或公司，空格隔开多个词，比如：亚马逊 助理"
        />
        <label class="injd"><input v-model="inJd" type="checkbox" /> 也搜JD正文</label>
      </div>
      <div class="facet">
        <span class="facet-t">分档</span>
        <button
          v-for="(n, name) in tiers"
          :key="'tier-' + name"
          class="chip"
          :class="{ on: isOn(tierPick, name) }"
          :disabled="!n && !isOn(tierPick, name)"
          @click="pickTier(name)"
        >
          {{ name }}<span class="n">{{ n }}</span>
        </button>
      </div>
      <div class="facet">
        <span class="facet-t">方向</span>
        <button
          v-for="(n, name) in kinds"
          :key="'kind-' + name"
          class="chip"
          :class="{ on: isOn(kind, name) }"
          :disabled="!n && !isOn(kind, name)"
          @click="pickKind(name)"
        >
          {{ name }}<span class="n">{{ n }}</span>
        </button>
      </div>
    </div>

    <div class="bar">
      <span class="facet-t">状态</span>
      <button
        v-for="f in FILTERS"
        :key="f.value"
        class="chip"
        :class="{ on: filter === f.value }"
        @click="pick(f.value)"
      >
        {{ f.label }}
          <span class="n">{{ countOf(f.value) }}</span>
      </button>
      <label class="minshow">
        分数 ≥
          <ScorePicker v-model="minShow" />
      </label>
      <label class="minshow">
        排序
        <select class="sort" v-model="order">
          <option v-for="o in ORDER_OPTIONS" :key="o" :value="o">{{ o }}</option>
        </select>
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
                第 {{ offset + 1 }}–{{ offset + leads.length }} 条 / 共 {{ total }} 条
      </span>
    </div>

    <p v-if="error" class="err">{{ error }}</p>

    <div v-if="!loading && !leads.length" class="empty">
      <template v-if="filtering">
        <div class="empty-t">没有符合条件的岗位</div>
        <div class="empty-s">换个关键词，或把分档、方向、状态改回「全部」试试。</div>
      </template>
      <template v-else>
        <div class="empty-t">这里还没有岗位</div>
        <div class="empty-s">打开 BOSS 直聘搜索岗位，插件会自动打分并把结果存到这里。</div>
      </template>
    </div>

    <ul v-else class="list">
      <li
        v-for="l in leads"
        :key="l.id"
        class="row"
        :class="[tone(l.quick_score), { off: l.status === '已跳过' }]"
      >
        <div class="score">
          {{ l.quick_score }}
          <div class="tier">{{ tier(l) }}</div>
        </div>

        <div class="mid">
          <a :href="l.url" target="_blank" rel="noopener" class="title">{{ l.title }}</a>
          <div class="meta">
            <span class="company">{{ l.company || '未标公司' }}</span>
            <span v-if="l.salary" class="salary">{{ l.salary }}</span>
            <span v-for="t in l.tags" :key="t" class="tag">{{ t }}</span>
            <span v-if="scoreNote(l)" class="tag note">{{ scoreNote(l) }}</span>
          </div>
          <div v-if="prosOf(l).length" class="points">
            <span class="points-t good">合适</span>
            <span v-for="p in prosOf(l)" :key="'pro-' + p" class="tag hit">✓ {{ p }}</span>
          </div>
          <div v-if="consOf(l).length" class="points">
            <span class="points-t bad">不合适</span>
            <span v-for="c in consOf(l)" :key="'con-' + c" class="tag flag">✗ {{ c }}</span>
          </div>
        </div>

                <div class="deep">
          <router-link v-if="l.deep_at" :to="'/report/' + l.report_id" class="deeplink">
            <span class="ok">{{ l.deep_ok }}</span> 有依据
            <span class="part">{{ l.deep_part }}</span> 部分
            <span class="dim">/ {{ l.deep_total }}</span>
            <span class="go">›</span>
          </router-link>
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
          <button
            v-if="l.status !== '已投递'"
            class="mini del"
            :disabled="running"
            @click="removeLead(l)"
          >删除</button>
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
.btn.danger { background: transparent; border-color: #8a2f2f; color: #ff8a80; }
.btn.danger:hover:not(:disabled) { background: #8a2f2f; color: #fff; }

.progress { color: #9aa5bd; font-size: 12.5px; display: flex; align-items: center; gap: 6px; }
.cur { color: #35c48a; }
.dot {
  width: 7px; height: 7px; border-radius: 50%;
  background: #35c48a;
  animation: blink 1s infinite;
}
@keyframes blink { 0%,100% { opacity: 1 } 50% { opacity: .25 } }

.filters { display: flex; flex-direction: column; gap: 8px; margin-bottom: 10px; }
.search { display: flex; align-items: center; gap: 12px; flex-wrap: wrap; }
.kw {
  flex: 1; min-width: 220px; max-width: 460px;
  background: #0f1425; border: 1px solid #2a3348; border-radius: 8px;
  padding: 8px 12px; font-size: 13px; color: #e8ecf5; font-family: inherit;
}
.kw:focus { outline: none; border-color: #0b7a4b; }
.injd { display: flex; align-items: center; gap: 6px; font-size: 12px; color: #9aa5bd; cursor: pointer; white-space: nowrap; }
/* 全局样式把输入框设成了整行宽、46px 高，勾选框要改回正常大小 */
.injd input { width: 15px; height: 15px; min-height: 0; padding: 0; accent-color: #0b7a4b; cursor: pointer; }
.facet { display: flex; align-items: center; gap: 6px; flex-wrap: wrap; }
.facet-t { flex: 0 0 30px; font-size: 12px; color: #6b7590; }
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
.minshow { display: flex; align-items: center; gap: 6px; font-size: 12px; color: #9aa5bd; }
/* 筛选条上的下拉框要窄，不能用上面 select 的 190px */
.sort { min-width: 96px; padding: 6px 8px; font-size: 12px; }
.chip.on { border-color: #0b7a4b; background: #0b7a4b; color: #fff; }
.chip:disabled { opacity: .35; cursor: default; }
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

.score { flex: 0 0 58px; text-align: center; font-size: 17px; font-weight: 700; color: #c3ccdf; }
.tier { margin-top: 2px; font-size: 10px; font-weight: 500; color: #8a94ab; white-space: nowrap; }
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
.salary { color: #f0a35e; font-size: 12px; font-weight: 600; }
.tag { color: #6b7590; font-size: 11px; border: 1px solid #232c40; border-radius: 4px; padding: 1px 6px; }
/* JD 粗筛命中的门槛，红色显示 */
.tag.flag { color: #ff9a8f; border-color: #6b2f2f; background: rgba(255, 90, 90, .08); }
/* JD 粗筛命中的能力项，绿色显示 */
.tag.hit { color: #6ee7b7; border-color: #1f5b43; background: rgba(53, 196, 138, .08); }
/* 分数来自哪套求职方案，绿色显示 */
.tag.target { color: #7fd6ae; border-color: #1f5b43; background: rgba(53, 196, 138, .08); }
.tag.done { color: #6ee7b7; border-color: #1f5b43; }
.tag.note { color: #9aa5bd; border-style: dashed; }
/* 合适 / 不合适各占一行 */
.points { display: flex; align-items: center; gap: 6px; margin-top: 6px; flex-wrap: wrap; }
.points-t { flex: 0 0 auto; font-size: 11px; font-weight: 600; margin-right: 2px; }
.points-t.good { color: #35c48a; }
.points-t.bad { color: #ff8a80; }
.tag.pending { color: #f5c06f; border-color: #6a5127; }

.deep { flex: 0 0 165px; font-size: 12px; color: #8390aa; white-space: nowrap; }
.deeplink { color: inherit; text-decoration: none; display: inline-flex; align-items: center; gap: 5px; }
.deeplink:hover .go { transform: translateX(2px); }
.deeplink .go { color: #35c48a; font-size: 17px; line-height: 1; transition: transform .15s; }
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
.mini.del:hover { border-color: #8a2f2f; color: #ff8a80; }
.mini:disabled { opacity: .4; cursor: default; }
</style>
