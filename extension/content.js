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

// 工资：列表卡片上一般是 .job-salary，详情页是 .salary；都找不到就在卡片文字里找「7-12K」这种写法
// BOSS 可能用特殊字体显示数字，原样传给后端，由后端换回数字
function readSalary(card) {
  const el = card.querySelector('.job-salary, .salary, [class*="salary"]')
  const text = el?.innerText?.trim()
  if (text) return text.slice(0, 50)
  const line = card.innerText.split('\n').find(s => /[\d\ue031-\ue03a]\s*[-~]\s*[\d\ue031-\ue03a]+\s*[Kk千]/.test(s))
  return (line || '').trim().slice(0, 50)
}

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
// 投递队列低于这个分才提醒：55 分以上是「可投可不投」，也算能投
const APPLY_PASS = 55
const DRY_RUN = false
const DAILY_MAX = 1500
const APPLY_MIN = 3
const MAX_DEEP = 3
const API = 'http://127.0.0.1:8000'
const QUEUE_KEY = 'jm_apply_queue'
// 补读 JD 队列：岗位池页面点「补读JD」交过来（bridge.js 存进来），插件挨个打开详情页读
const READ_KEY = 'jm_read_queue'
const READ_META = 'jm_read_meta'
const APPLY_GAP = 10000
const JD_GAP = 3000
const JD_GAP_MAX = 5000
const SCROLL_GAP = 2000
// 连续获取岗位 10 分钟就停 1 分钟再接着抓：一直不停地翻页、点详情页最容易被风控
const RUN_MS = 10 * 60 * 1000
const REST_MS = 60 * 1000
let runStart = 0
let lastFirst = ''
let TOKEN = ''
let RESUME_ID = null
let SCAN_ON = false
let SCANNING = false   
let STOPPED = false
let aborter = new AbortController()
let scrollTimer = null

// 重新开始。一个中断控制器只能用一次，所以要换新的。
function resume() {
  STOPPED = false
  aborter = new AbortController()
}

chrome.storage.local.get(['token', 'resume_id'])
  .then(async data => {
    TOKEN = data.token || ''
    RESUME_ID = data.resume_id || null
    if (await guardRisk()) return
    const rq = (await chrome.storage.local.get(READ_KEY))[READ_KEY] || []
    if (rq.length) {
      addStopButton()
      runReadQueue().catch(e => {
        if (STOPPED || e?.name === 'AbortError') return
        tip.textContent = `[求职助手] 补读JD出错：${e.message} · 刷新页面会接着读`
      })
      return
    }
    const q = (await chrome.storage.local.get(QUEUE_KEY))[QUEUE_KEY] || []
    if (isDetailPage()) {
      addStopButton()
      const task = q.length ? runQueue() : saveCurrentJd()
      task.catch(e => {
        if (STOPPED || e?.name === 'AbortError') return
        tip.textContent = `[求职助手] ${e.message}`
      })
      return
    }
    if (q.length && location.pathname.includes('/chat')) {
      addStopButton()
      skipChatted().catch(e => {
        if (STOPPED || e?.name === 'AbortError') return
        tip.textContent = `[求职助手] ${e.message}`
      })
      return
    }
    addScanButton()
    addStartButton()
    addStopButton()
    if (q.length) {
      tip.textContent = `投递队列还剩 ${q.length} 个 · 3 秒后自动继续`
      await sleep(3000)
      await startApply()
      return
    }
    tip.textContent = '待命中 · 点下方「获取岗位」'
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

// 跳到页面底部，让 BOSS 加载下一页，等 2 秒再自己扫一次。
// 不靠「页面有没有变化」来触发，所以不会卡在「已全部处理」。
function nextPage() {
  if (!SCAN_ON || STOPPED || scrollTimer) return
  scrollTimer = setTimeout(() => {
    scrollTimer = null
    if (!SCAN_ON || SCANNING) return
    window.scrollTo({ top: document.body.scrollHeight, behavior: 'smooth' })
    setTimeout(scan, 2000)
  }, SCROLL_GAP)
}

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
  if (riskPage()) {
    guardRisk()
    return
  }
  if (Date.now() - runStart >= RUN_MS) {
    SCANNING = true
    restIfDue().finally(() => { SCANNING = false; scan() })
    return
  }
  const cards = [...document.querySelectorAll('.job-card-box')]
    .filter(c => !c.dataset.jmDone)
  if (!cards.length) {
    const message = '[求职助手] 这一屏处理完了，正在翻下一页…'
    if (tip.textContent !== message) tip.textContent = message
    nextPage()
    return
  }
  cards.forEach(c => { c.dataset.jmDone = '1' })

  const list = cards.map(c => ({
    el: c,
    name: c.querySelector('.job-name')?.innerText,
    url: c.querySelector('.job-name')?.href || '',
    company:c.querySelector('.boss-name')?.innerText || '未知',
    tags: [...c.querySelectorAll('.tag-list li')].map(li => li.innerText),
    // 工资原文：BOSS 的数字用了特殊字体，原样传给后端换回数字
    salary: readSalary(c)
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
      jobs: list.map(j => ({ name: j.name, tags: j.tags, salary: j.salary }))
    }),
    signal: aborter.signal
  })
      .then(r => {
      if (r.status === 401) return Promise.reject('请点插件图标登录')
      return r.ok ? r.json() : Promise.reject(`打分失败：HTTP ${r.status}`)
    })
    .then(async scores => {
      scores.forEach((s, i) => mark(list[i].el, s))
      // 读到工资的个数：是 0 说明页面结构变了，工资规则用不上
      const paid = list.filter(j => j.salary).length
      tip.textContent = `[求职助手] 已打分 ${scores.length} 个岗位 · 读到工资 ${paid} 个`
      let doneJd = []
      try {
        const saved = await uploadLeads(list, scores)
        doneJd = saved.has_jd || []
        tip.textContent += ` · 新增 ${saved.added} 个、更新 ${saved.updated} 个`
      } catch (e) {
        tip.textContent += ` · 入库失败：${e.message}`
      }
      try {
        const n = await collectJds(list, scores, doneJd)
        tip.textContent = `[求职助手] 已读取并重评 ${n} 份JD · 跳过已读 ${doneJd.length} 个 · 读到工资 ${paid} 个`
      } catch (e) {
        tip.textContent += ` · JD补全失败：${e.message}`
      }
    })
      .catch(e => {
        // 用户点了停止 —— 这不是错误，别吓人
        if (STOPPED || e?.name === 'AbortError') return
        tip.textContent = `[求职助手] ${e}`
      })
      .finally(() => {
        SCANNING = false
        nextPage()
      })
}

function mark(el, s, final = false) {
  el.querySelector('.jm-badge')?.remove()

  el.style.borderLeft = s.read_jd === false ? '4px solid #999'
                      : final || s.screen === 'priority' ? '4px solid #0B7A4B'
                      : '4px solid #B6791A'

  const b = document.createElement('div')
  b.className = 'jm-badge'
  if (s.read_jd === false) {
    b.textContent = `跳过 · ${s.reason || '明显不符合'}`
  } else if (!final) {
    const step = s.screen === 'priority' ? '标题符合 · 优先读JD' : '标题模糊 · 仍读JD'
    b.textContent = `初筛 ${s.score}分 · ${step}`
  } else {
    const note = (s.flags?.length ? s.flags : s.hits || []).slice(0, 2).join('、')
    b.textContent = `${s.score}分 · JD已读${note ? ` · ${note}` : ''}`
  }
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
      salary: j.salary,
      quick_score: scores[i].score
    }))
    .filter(l => l.title && l.url)
  if (!leads.length) return { added: 0, updated: 0 }
  const r = await fetch('http://127.0.0.1:8000/leads/batch', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${TOKEN}` },
    body: JSON.stringify({ leads, resume_id: RESUME_ID }),
    signal: aborter.signal
  })
  if (!r.ok) throw new Error(r.status === 401 ? '请点插件图标登录' : `HTTP ${r.status}`)
  return r.json()
}


function sleep(ms) {
  return new Promise((resolve, reject) => {
    if (STOPPED) return reject(new Error('已停止'))
    const t = setTimeout(resolve, ms)
    aborter.signal.addEventListener('abort', () => {
      clearTimeout(t)
      reject(new Error('已停止'))
    }, { once: true })
  })
}

function detailTitle() {
  const selectors = [
    '.job-detail-header .job-name',
    '.job-detail-info .name',
    '.job-detail-info h1',
    '.job-detail-box h1',
    'h1'
  ]
  for (const selector of selectors) {
    const text = document.querySelector(selector)?.innerText?.trim()
    if (text) return text
  }
  return ''
}


// 读岗位介绍：列表页右侧是 .job-detail-body；详情页结构不一样，
// 找不到时从整页文字里截「职位描述」到「工作地址 / 竞争力分析 / 公司介绍」这一段（带上招聘者活跃状态）
function readDetailJd() {
  const panel = document.querySelector('.job-detail-body')?.innerText || ''
  if (panel.trim().length > 50) return panel
  const all = document.body.innerText
  const start = all.indexOf('职位描述')
  if (start >= 0) {
    const rest = all.slice(start)
    const end = rest.search(/\n(工作地址|竞争力分析|公司介绍|公司基本信息)/)
    const text = end > 0 ? rest.slice(0, end) : rest.slice(0, 5000)
    if (text.trim().length > 50) return text
  }
  return document.querySelector('.job-sec-text')?.innerText || ''
}

async function waitJd(prev, expectedTitle) {
  for (let i = 0; i < 20; i++) {
    const jd = readDetailJd()
    const currentTitle = detailTitle()
    const isExpected = titleMatch(currentTitle, expectedTitle)
    // 标题对上、正文也换了才算这个岗位的JD：BOSS 常常标题先变、正文还停在上一个岗位。
    const ready = expectedTitle ? (isExpected && jd !== prev) : jd !== prev
    if (jd.length > 50 && ready) return jd
    await sleep(300)
  }
  return null
}


async function collectJds(list, scores, doneJd = []) {
  // 已经读过 JD 的不再点开：重复点详情页是账号被风控的主要原因
  const done = new Set(doneJd)
  const targets = list
    .map((item, i) => ({ ...item, screen: scores[i]?.screen || 'review', order: i }))
    .filter((item, i) => item.url && !done.has(item.url) && scores[item.order]?.read_jd !== false)
    .sort((a, b) => Number(b.screen === 'priority') - Number(a.screen === 'priority') || a.order - b.order)
  let updated = 0
  let prev = document.querySelector('.job-detail-body')?.innerText || ''
  for (let i = 0; i < targets.length; i++) {
    if (STOPPED || !SCAN_ON) break
    if (await guardRisk()) break
    if (!(await restIfDue())) break
    const t = targets[i]
    if (!t.url) continue
    const step = t.screen === 'priority' ? '标题符合' : '标题模糊'
    tip.textContent = `[求职助手] 读取JD ${i + 1}/${targets.length}（${step}）`
    await sleep(jdGap())
    t.el.click()
    const jd = await waitJd(prev, t.name)
    if (!jd || jd.length < 20) continue
    prev = jd
    const saved = await uploadJds([{ url: t.url, jd_text: jd.slice(0, 20000) }])
    updated += saved.updated
    const final = saved.items?.find(item => item.url === t.url)
    if (final?.skip) mark(t.el, { ...final, read_jd: false }, true)
    else if (final) mark(t.el, { ...final, read_jd: true }, true)
    tip.textContent = `[求职助手] 已读取并重评 ${i + 1}/${targets.length}`
  }
  return updated
}

async function uploadJds(items) {
  const r = await fetch('http://127.0.0.1:8000/leads/jd', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${TOKEN}` },
    body: JSON.stringify({ items, resume_id: RESUME_ID }),
    signal: aborter.signal
  })
  if (!r.ok) throw new Error(`HTTP ${r.status}`)
  return r.json()
}

async function saveCurrentJd() {
  tip.textContent = '[求职助手] 正在读取当前JD…'
  const title = detailTitle()
  if (!title) throw new Error('未读到当前岗位标题')
  const jd = await waitJd('', title)
  if (!jd) throw new Error('未读到当前岗位介绍')
  const url = location.href.split('?')[0].split('#')[0]
  const saved = await uploadJds([{ url, jd_text: jd.slice(0, 20000) }])
  tip.textContent = saved.missed
    ? '岗位池未找到这个岗位，请先从列表页抓取'
    : '当前JD已保存并重新评分'
}



async function deepCheck(list, scores) {
  const targets = list.filter((_, i) => scores[i].score >= PASS).slice(0, MAX_DEEP)
  if (!targets.length) {
    tip.textContent += ' | 本屏无达标岗位'
    return
  }

  let prev = document.querySelector('.job-detail-body')?.innerText || ''

  for (let i = 0; i < targets.length; i++) {
    if (STOPPED) return
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
        body: JSON.stringify({ resume_id: RESUME_ID, job_title: t.name, company: t.company, jd_text: jd }),
        signal: aborter.signal
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


// 抓满 10 分钟就原地歇 1 分钟（倒计时显示在提示条上）；歇的时候点了停止就返回 false
async function restIfDue() {
  if (Date.now() - runStart < RUN_MS) return true
  for (let left = REST_MS / 1000; left > 0; left--) {
    if (STOPPED || !SCAN_ON) return false
    tip.textContent = `[求职助手] 已连续获取 10 分钟，休息 ${left} 秒后自动继续`
    await sleep(1000)
  }
  runStart = Date.now()
  return !STOPPED && SCAN_ON
}

// 读 JD 的间隔随机 3-5 秒：固定节奏最容易被风控盯上
function jdGap() {
  return JD_GAP + Math.floor(Math.random() * (JD_GAP_MAX - JD_GAP + 1))
}

// BOSS 弹安全验证、或把账号登出了：立刻全停，继续点只会让风控升级
const RISK_WORDS = ['安全验证', '完成验证', '账号可能存在异常', '异常访问行为', '访问过于频繁', '操作过于频繁', '请先登录', '重新登录', '登录已失效',
  // 第三级：「访问受限 · 您的账户存在异常行为，已暂时被限制访问」
  '访问受限', '限制访问', '存在异常行为', '暂时被限制', '恢复正常']
function riskPage() {
  const text = document.body?.innerText || ''
  // 验证页和登录页内容都很短；正常列表页、详情页有几千字，避免把带这些字的 JD 误判
  const hit = text.length < 2000 ? RISK_WORDS.find(w => text.includes(w)) : ''
  if (hit) return hit
  if (/^\/(login|safe|verify)/.test(location.pathname)) return '被跳到登录或验证页'
  return ''
}

async function guardRisk() {
  const hit = riskPage()
  if (!hit) return false
  await stopAll(`[求职助手] BOSS 触发风控（${hit}）· 已全部停止。请手动处理，缓一会儿再用插件。`)
  return true
}

async function stopAll(message) {
  STOPPED = true
  SCAN_ON = false
  SCANNING = false
  aborter.abort()
  clearTimeout(scanTimer)
  clearTimeout(scrollTimer)
  scrollTimer = null
  await chrome.storage.local.remove([QUEUE_KEY, READ_KEY, READ_META])
  setDot('#4a5570')
  tip.textContent = message
}

function titleKey(s) {
  return (s || '').replace(/\s/g, '').slice(0, 10)
}

// 列表页标题常被截短：「海外项目技术支持」要能对上详情页的「海外项目技术支持（出差美国）」
function titleMatch(a, b) {
  const x = titleKey(a), y = titleKey(b)
  if (!x || !y) return false
  if (x === y) return true
  const short = x.length <= y.length ? x : y
  return short.length >= 6 && x.startsWith(short) && y.startsWith(short)
}

async function applyHere(expectTitle, leadId) {
  const h1 = document.querySelector('h1')?.innerText.trim()
  if (!h1) return '⛔页面没加载好'
  const pageText = document.body.innerText
  const missingPage =
    h1 === 'Oops!' ||
    pageText.includes('您访问的页面不存在')
  if (missingPage) return '⏭岗位不存在'
  if (!titleMatch(h1, expectTitle)) return `⛔标题对不上：${h1}`
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
      resume()
      runStart = Date.now()
      lastFirst = ''
      // 清掉这一页上次打过分的标记，重新打分、重新入库（上次入库失败也能补回来）
      document.querySelectorAll('.job-card-box').forEach(c => {
        delete c.dataset.jmDone
        c.querySelector('.jm-badge')?.remove()
      })
      scan()
    } else {
      tip.textContent = '正在收尾，当前这个岗位读完就停'
    }
  })
}

function addStopButton() {
  const b = makeBtn('■ 全部停止', '#8a2f2f')
  b.addEventListener('click', () => stopAll('[求职助手] 已全部停止，投递队列已清空'))
}

function addStartButton() {
  const b = makeBtn('开始投递', '#96651a')
  b.addEventListener('click', () => {
    resume()
    setDot('#e0a03a')
    startApply().catch(e => { tip.textContent = e.message })
  })
}

async function startApply() {
  const r = await fetch(`${API}/leads?status=待投递`, {
    headers: { 'Authorization': `Bearer ${TOKEN}` },
    signal: aborter.signal
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
  const bad = list.filter(l => l.quick_score < APPLY_PASS)
  if (bad.length) {
    tip.textContent = `⚠️队列里有 ${bad.length} 个 ${APPLY_PASS} 分以下的岗位（如「${bad[0].title}」），请回岗位池核对后再投`
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
  if (STOPPED) return
  location.href = queue[0].url
}

// 补读 JD：在队列第一个岗位的详情页读 JD、存进岗位池（后端顺带重新打分），歇 3-5 秒跳下一个。
// 连续读 10 分钟歇 1 分钟；岗位已关闭的标成「已跳过」；读不到的记一笔跳过，不卡住整个队列
async function runReadQueue() {
  const store = await chrome.storage.local.get([READ_KEY, READ_META])
  const queue = store[READ_KEY] || []
  const meta = { runStart: Date.now(), done: 0, closed: 0, failed: 0, ...store[READ_META] }
  if (!queue.length) return
  if (!TOKEN || !RESUME_ID) {
    tip.textContent = '[求职助手] 补读JD要先点插件图标登录并选好简历'
    return
  }
  setDot('#35c48a')
  const cur = queue[0]
  if (!location.href.startsWith(cur.url.split('?')[0])) {
    // 还没到这个岗位的页面就跳过去；跳过去了还对不上（链接失效被 BOSS 转走），算没读到
    if (meta.jumped !== cur.id) {
      meta.jumped = cur.id
      await chrome.storage.local.set({ [READ_META]: meta })
      location.href = cur.url
      return
    }
    meta.failed += 1
  } else {
    if (Date.now() - meta.runStart >= RUN_MS) {
      for (let left = REST_MS / 1000; left > 0; left--) {
        tip.textContent = `[求职助手] 已连续补读 10 分钟，休息 ${left} 秒后继续（还剩 ${queue.length} 个）`
        await sleep(1000)
      }
      meta.runStart = Date.now()
    }
    tip.textContent = `[求职助手] 补读JD：${cur.title}（还剩 ${queue.length} 个）`
    const st = await readHere(cur)
    meta[st] += 1
    if (st === 'closed') {
      await fetch(`${API}/leads/${cur.id}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${TOKEN}` },
        body: JSON.stringify({ status: '已跳过' })
      }).catch(() => {})
    }
  }
  queue.shift()
  if (!queue.length) {
    await chrome.storage.local.remove([READ_KEY, READ_META])
    setDot('#4a5570')
    tip.textContent = `[求职助手] 补读完成 · 读到 ${meta.done} 个 · 岗位已关闭 ${meta.closed} 个 · 没读到 ${meta.failed} 个`
    return
  }
  meta.jumped = queue[0].id
  await chrome.storage.local.set({ [READ_KEY]: queue, [READ_META]: meta })
  tip.textContent = `[求职助手] 已读 ${meta.done} 个 · 几秒后读下一个（还剩 ${queue.length} 个）`
  await sleep(jdGap())
  if (await guardRisk()) return
  location.href = queue[0].url
}

async function readHere(cur) {
  const jd = await waitJd('', cur.title)
  if (!jd) {
    // 读不到 JD 时再看是不是岗位没了；先判「关闭」容易把正常页面误标成已跳过
    const gone = document.querySelector('h1')?.innerText.trim() === 'Oops!' ||
      /您访问的页面不存在|职位已关闭/.test(document.body.innerText)
    return gone ? 'closed' : 'failed'
  }
  const saved = await uploadJds([{ url: cur.url, jd_text: jd.slice(0, 20000) }])
  return saved.missed ? 'failed' : 'done'
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
  scanTimer = setTimeout(scan, 1500)
})

observer.observe(document.body, { childList: true, subtree: true })
