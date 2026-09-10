const panel = document.createElement('div')
panel.style.cssText = [
  'position:fixed;bottom:22px;left:22px;z-index:2147483647',
  'width:286px;padding:14px 16px 15px;box-sizing:border-box',
  'background:rgba(11,15,24,.94);backdrop-filter:blur(14px)',
  'border:1px solid rgba(255,255,255,.09);border-radius:15px',
  'box-shadow:0 14px 40px rgba(0,0,0,.42)',
  'font:13px/1.65 -apple-system,"Microsoft YaHei",sans-serif;color:#e8ecf5'
].join(';')

const dot = document.createElement('span')
dot.style.cssText = 'width:7px;height:7px;border-radius:50%;background:#4a5570;flex:0 0 7px'

const head = document.createElement('div')
head.style.cssText = 'display:flex;align-items:center;gap:8px;margin-bottom:9px'
const brand = document.createElement('span')
brand.textContent = '求职助手'
brand.style.cssText = 'font-weight:700;font-size:11px;letter-spacing:.18em;color:#7b88a6'
head.append(dot, brand)

const tipEl = document.createElement('div')
tipEl.style.cssText = 'min-height:34px;margin-bottom:12px;color:#c8d1e4;overflow-wrap:anywhere'

const row = document.createElement('div')
row.style.cssText = 'display:flex;gap:8px'

panel.append(head, tipEl, row)
document.body.appendChild(panel)

const tip = {
  set textContent(v) { tipEl.textContent = String(v).replace(/^\[求职助手\]\s*/, '') },
  get textContent() { return tipEl.textContent }
}
tip.textContent = '启动中…'

function setDot(color) { dot.style.background = color }

function makeBtn(text, color) {
  const b = document.createElement('button')
  b.textContent = text
  b.style.cssText = [
    'flex:1;padding:9px 0;border:0;border-radius:10px',
    'font:600 12.5px/1 -apple-system,"Microsoft YaHei",sans-serif',
    'color:#fff;cursor:pointer;transition:filter .15s,transform .1s',
    `background:${color}`
  ].join(';')
  b.onmouseenter = () => { b.style.filter = 'brightness(1.18)' }
  b.onmouseleave = () => { b.style.filter = '' }
  b.onmousedown = () => { b.style.transform = 'scale(.97)' }
  b.onmouseup = () => { b.style.transform = '' }
  row.appendChild(b)
  return b
}

const PASS = 60
const DRY_RUN = false
const DAILY_MAX = 40
const APPLY_MIN = 3
const MAX_DEEP = 3
const API = 'http://127.0.0.1:8000'
const QUEUE_KEY = 'jm_apply_queue'
const APPLY_GAP = 10000
let lastFirst = ''
let TOKEN = ''
let RESUME_ID = null
let SCAN_ON = false
let SCANNING = false   

chrome.storage.local.get(['token', 'resume_id'])
  .then(async data => {
    TOKEN = data.token || ''
    RESUME_ID = data.resume_id || null
    if (isDetailPage()) {
      runQueue().catch(e => { tip.textContent = `[求职助手] 投递失败：${e.message}` })
      return
    }
    const q = (await chrome.storage.local.get(QUEUE_KEY))[QUEUE_KEY] || []
    if (q.length && location.pathname.includes('/chat')) {
      skipChatted().catch(e => { tip.textContent = `[求职助手] ${e.message}` })
      return
    }
    addScanButton()
    addStartButton()
    tip.textContent = q.length
      ? `[求职助手] 投递队列还剩 ${q.length} 个 · 点「开始投递」继续`
      : '[求职助手] 待命中 · 点下方「获取岗位」'
  })
  .catch(e => { tip.textContent = `[求职助手] 读取Token失败：${e.message}` })

chrome.storage.onChanged.addListener(changes => {
  if (changes.resume_id) RESUME_ID = changes.resume_id.newValue || null
  if (!changes.token) return
  TOKEN = changes.token.newValue || ''
  SCAN_ON = false
  tip.textContent = TOKEN
    ? '[求职助手] 已切换账号 · 点下方「获取岗位」'
    : '[求职助手] 已退出登录 · 点插件图标登录'
})

function scan() {
  if (!SCAN_ON || SCANNING) return
  if (!TOKEN){
    const message = '[求职助手] 请先点击插件图标保存Token'
    if(tip.textContent !== message){
        tip.textContent = message
    }
    return
  }
  if (!RESUME_ID) {
    tip.textContent = '[求职助手] 请点插件图标选择一份简历'
    return
  }
  const cards = [...document.querySelectorAll('.job-card-box')]
    .filter(c => !c.dataset.jmDone)
  if (!cards.length) {
    tip.textContent = '[求职助手] 当前已全部处理，往下滚动加载更多岗位'
    return
  }
  cards.forEach(c => { c.dataset.jmDone = '1' })

  const list = cards.map(c => ({
    el: c,
    name: c.querySelector('.job-name')?.innerText,
    url: c.querySelector('.job-name')?.href || '',
    company:c.querySelector('.boss-name')?.innerText || '未知',
    tags: [...c.querySelectorAll('.tag-list li')].map(li => li.innerText)
  }))
  SCANNING = true  
  tip.textContent = `[求职助手] 正在给 ${list.length} 个岗位打分…`
  fetch('http://127.0.0.1:8000/jobs/quick-score', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${TOKEN}`
    },
    body: JSON.stringify({
      resume_id: RESUME_ID,
      jobs: list.map(j => ({ name: j.name, tags: j.tags }))
    })
  })
      .then(r => {
      if (r.status === 401) return Promise.reject('请点插件图标登录')
      return r.ok ? r.json() : Promise.reject(`打分失败：HTTP ${r.status}`)
    })
    .then(async scores => {
      scores.forEach((s, i) => mark(list[i].el, s))
      tip.textContent = `[求职助手] 已打分 ${scores.length} 个岗位`
      try {
        const n = await uploadLeads(list, scores)
        tip.textContent += ` · 入库 ${n} 个新岗位`
      } catch (e) {
        tip.textContent += ` · 入库失败：${e.message}`
      }
      try {
        const n = await collectJds(list)
        tip.textContent = `[求职助手] 已入库 ${scores.length} 个岗位，补全 ${n} 份JD。去「岗位池」页面开始精判`
      } catch (e) {
        tip.textContent += ` · JD补全失败：${e.message}`
      }
    })
      .catch(e => { tip.textContent = `[求职助手] ${e}` })
      .finally(() => { SCANNING = false })
}

function mark(el, s) {
  el.querySelector('.jm-badge')?.remove()

  el.style.borderLeft = s.score >= 60 ? '4px solid #0B7A4B'
                      : s.score >= 30 ? '4px solid #B6791A'
                      : '4px solid #ccc'

  const b = document.createElement('div')
  b.className = 'jm-badge'
   b.textContent = s.matched.length
    ? `${s.score}分 · 命中 ${s.matched.join(' ')}`
    : `${s.score}分 · 仅按职位名`
  b.style.cssText = 'font-size:12px;color:#0B7A4B;padding:2px 10px;font-weight:600'
  el.appendChild(b)
}

async function uploadLeads(list, scores) {
  const leads = list
    .map((j, i) => ({
      title: j.name || '',
      company: j.company === '未知' ? '' : j.company,
      url: j.url,
      tags: j.tags,
      quick_score: scores[i].score
    }))
    .filter(l => l.title && l.url)
  if (!leads.length) return 0
  const r = await fetch('http://127.0.0.1:8000/leads/batch', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${TOKEN}` },
    body: JSON.stringify({ leads })
  })
  if (!r.ok) throw new Error(r.status === 401 ? '请点插件图标登录' : `HTTP ${r.status}`)
  const d = await r.json()
  return d.added
}


function sleep(ms) {
  return new Promise(r => setTimeout(r, ms))
}

async function waitJd(prev) {
  for (let i = 0; i < 20; i++) {
    const jd = document.querySelector('.job-detail-body')?.innerText || ''
    if (jd.length > 50 && jd !== prev) return jd
    await sleep(300)
  }
  return null
}


async function collectJds(list) {
  const items = []
  let prev = document.querySelector('.job-detail-body')?.innerText || ''
  for (let i = 0; i < list.length && items.length < 20; i++) {
    if (!SCAN_ON) break
    const t = list[i]
    if (!t.url) continue
    tip.textContent = `[求职助手] 读取JD ${i + 1}/${list.length}`
    t.el.click()
    const jd = await waitJd(prev)
    if (!jd || jd.length < 20) continue
    prev = jd
    items.push({ url: t.url, jd_text: jd.slice(0, 20000) })
  }
  if (!items.length) return 0
  const r = await fetch('http://127.0.0.1:8000/leads/jd', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${TOKEN}` },
    body: JSON.stringify({ items })
  })
  if (!r.ok) throw new Error(`HTTP ${r.status}`)
  const d = await r.json()
  return d.updated
}



async function deepCheck(list, scores) {
  const targets = list.filter((_, i) => scores[i].score >= PASS).slice(0, MAX_DEEP)
  if (!targets.length) {
    tip.textContent += ' | 本屏无达标岗位'
    return
  }

  let prev = document.querySelector('.job-detail-body')?.innerText || ''

  for (let i = 0; i < targets.length; i++) {
    const t = targets[i]
    tip.textContent = `[求职助手] 精判 ${i + 1}/${targets.length}：${t.name}`

    const openTitle = document.querySelector('.job-detail-header .job-name')?.innerText.trim()
    const waitFrom = openTitle === t.name.trim() ? '':prev
    t.el.click()
    const jd = await waitJd(waitFrom)
    if (!jd) continue
    prev = jd

    try {
      const r = await fetch('http://127.0.0.1:8000/jobs/report', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${TOKEN}` },
        body: JSON.stringify({ resume_id: RESUME_ID, job_title: t.name, company: t.company, jd_text: jd })
      })
      if (!r.ok) throw new Error(`HTTP ${r.status}`)
      const rep = await r.json()
      const ok = rep.checks.filter(c => c.status === '有依据').length
      const part = rep.checks.filter(c => c.status === '部分支持').length
      const st = ok >= APPLY_MIN ? await tryApply(t) : '⏭分数不够'
      addDeep(t.el, `精判：${ok} 有依据 / ${part} 部分 · ${st}`)
      if (st === '✅已投递') await logApply(rep.report_id)
    } catch (e) {
      addDeep(t.el, `精判失败：${e.message}`)
    }

    await sleep(1000)
  }
  tip.textContent = `[求职助手] 精判完成，共 ${targets.length} 个`
}

function addDeep(el, text) {
  el.querySelector('.jm-deep')?.remove()
  const d = document.createElement('div')
  d.className = 'jm-deep'
  d.textContent = text
  d.style.cssText = 'font-size:12px;color:#B6791A;padding:2px 10px;font-weight:600'
  el.appendChild(d)
}



function findApplyBtn(name) {
  const title = document.querySelector('.job-detail-header .job-name')?.innerText.trim()
  if (title !== name.trim()) return null
  const b = document.querySelector('.job-detail-op .op-btn-chat')
  if (!b) return null
  if (b.className.includes('is-disabled')) return null
  return b
}



function todayKey() {
  return 'jm_' + new Date().toLocaleDateString()
}

function usedToday() {
  return Number(localStorage.getItem(todayKey()) || 0)
}

function addUsed() {
  localStorage.setItem(todayKey(), usedToday() + 1)
}


async function closeDialog() {
  for (let i = 0; i < 20; i++) {
    const c = document.querySelector('.greet-boss-footer .cancel-btn') ||
      [...document.querySelectorAll('button')].find(
        b => b.textContent.trim() === '留在此页'
      )
    if (c) { c.click(); return true }
    await sleep(300)
  }
  return false
}


function isDetailPage() {
  return location.pathname.includes('/job_detail/')
}

async function skipChatted() {
  const data = await chrome.storage.local.get(QUEUE_KEY)
  const queue = data[QUEUE_KEY] || []
  if (!queue.length) return
  const cur = queue.shift()
  await fetch(`${API}/leads/${cur.id}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${TOKEN}` },
    body: JSON.stringify({ status: '已投递' })
  }).catch(() => {})
  if (!queue.length) {
    await chrome.storage.local.remove(QUEUE_KEY)
    tip.textContent = '[求职助手] 队列全部完成'
    return
  }
  await chrome.storage.local.set({ [QUEUE_KEY]: queue })
  tip.textContent = `[求职助手] 这个之前已沟通过 · 3 秒后投下一个（还剩 ${queue.length}）`
  await sleep(3000)
  location.href = queue[0].url
}


function titleKey(s) {
  return (s || '').replace(/\s/g, '').slice(0, 10)
}

async function applyHere(expectTitle, leadId) {
  const h1 = document.querySelector('h1')?.innerText.trim()
  if (!h1) return '⛔页面没加载好'
  if (titleKey(h1) !== titleKey(expectTitle)) return `⛔标题对不上：${h1}`
  if (document.body.innerText.includes('职位已关闭')) return '⏭岗位已关闭'
  const btn = document.querySelector('.btn-startchat')
  if (!btn) return '⛔没找到沟通按钮'
  if (!DRY_RUN && usedToday() >= DAILY_MAX) return '⛔今日已达上限'
  if (DRY_RUN) return '🧪演练·本该投出'
  // 先记账再点击：点击可能让 BOSS 跳到聊天页，之后的代码不保证能跑完
  await fetch(`${API}/leads/${leadId}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${TOKEN}` },
    body: JSON.stringify({ status: '已投递' })
  }).catch(() => {})
  btn.click()
  addUsed()
  const closed = await closeDialog()
  return closed ? '✅已投递' : '⚠️投了但弹窗没关'
}

function addScanButton() {
  const b = makeBtn('获取岗位', '#1f6f4a')
  b.addEventListener('click', () => {
    SCAN_ON = !SCAN_ON
    b.textContent = SCAN_ON ? '停止获取' : '获取岗位'
    b.style.background = SCAN_ON ? '#8a3030' : '#1f6f4a'
    setDot(SCAN_ON ? '#35c48a' : '#4a5570')
    if (SCAN_ON) {
      lastFirst = ''
      scan()
    } else {
      tip.textContent = '正在收尾，当前这个岗位读完就停'
    }
  })
}


function addStartButton() {
  const b = makeBtn('开始投递', '#96651a')
  b.addEventListener('click', () => {
    setDot('#e0a03a')
    startApply().catch(e => { tip.textContent = e.message })
  })
}

async function startApply() {
  const r = await fetch(`${API}/leads?status=待投递`, {
    headers: { 'Authorization': `Bearer ${TOKEN}` }
  })
  if (!r.ok) throw new Error(`HTTP ${r.status}`)
  const data = await r.json()
  const list = data.items
  if (!Array.isArray(list)) {
    throw new Error('岗位接口返回格式错误')
  }
  if (!list.length) {
    tip.textContent = '[求职助手] 没有「待投递」的岗位，先去岗位池标记'
    return
  }
  const bad = list.filter(l => l.quick_score < 60)
  if (bad.length) {
    tip.textContent = `⚠️队列里有 ${bad.length} 个 60 分以下的岗位（如「${bad[0].title}」），请回岗位池核对后再投`
    return
  }
  const left = Math.max(DAILY_MAX - usedToday(), 0)
  if (!DRY_RUN && left === 0) {
    tip.textContent = '[求职助手] 今日已达投递上限'
    return
  }
  const jobs = DRY_RUN ? list : list.slice(0, left)
  const queue = jobs.map(l => ({ id: l.id, url: l.url, title: l.title }))
  await chrome.storage.local.set({ [QUEUE_KEY]: queue })
  tip.textContent = `[求职助手] 队列 ${queue.length} 个，开始投递…`
  location.href = queue[0].url
}

async function runQueue() {
  const data = await chrome.storage.local.get(QUEUE_KEY)
  const queue = data[QUEUE_KEY] || []
  if (!queue.length) return
  const cur = queue[0]
  if (!location.href.startsWith(cur.url.split('?')[0])) return
  tip.textContent = `[求职助手] 投递中，还剩 ${queue.length} 个`
  const st = await applyHere(cur.title, cur.id)
  if (st.startsWith('⛔')) {
    tip.textContent = `[求职助手] ${st} · 已暂停，岗位仍在队列`
    return
  }
  if (st.startsWith('⏭')) {
    await fetch(`${API}/leads/${cur.id}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${TOKEN}` },
      body: JSON.stringify({ status: '已跳过' })
    }).catch(() => {})
  }
  queue.shift()
  if (!queue.length) {
    await chrome.storage.local.remove(QUEUE_KEY)
    tip.textContent = `[求职助手] ${st} · 队列全部完成`
    return
  }
  await chrome.storage.local.set({ [QUEUE_KEY]: queue })
  tip.textContent = `[求职助手] ${st} · ${APPLY_GAP / 1000} 秒后投下一个（还剩 ${queue.length}）`
  await sleep(APPLY_GAP)
  location.href = queue[0].url
}

async function tryApply(t) {
  if (usedToday() >= DAILY_MAX) return '🛑今日已达上限'
  const btn = findApplyBtn(t.name)
  if (!btn) return '⛔已投过'
  const go = window.confirm(`确认分析岗位「${t.name}」？`)
  if (!go) return '✋已取消'
  if (DRY_RUN) return '🧪演练·本该投出'
  btn.click()
  addUsed()
  const closed = await closeDialog()
  return closed ? '✅已投递' : '⚠️投了但弹窗没关'
}

async function logApply(reportId) {
  const h = { 'Content-Type': 'application/json', 'Authorization': `Bearer ${TOKEN}` }
  const r = await fetch('http://127.0.0.1:8000/applications', {
    method: 'POST', headers: h,
    body: JSON.stringify({ report_id: reportId })
  })
  if (!r.ok) return false
  const a = await r.json()
  await fetch(`http://127.0.0.1:8000/applications/${a.id}`, {
    method: 'PATCH', headers: h,
    body: JSON.stringify({ status: '已投递', note: '插件自动投递' })
  })
  return true
}



let scanTimer = null

const observer = new MutationObserver(() => {
  clearTimeout(scanTimer)
  scanTimer = setTimeout(scan, 500)
})

observer.observe(document.body, { childList: true, subtree: true })
