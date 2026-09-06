const tip = document.createElement('div')
tip.textContent = '[求职助手] 启动中…'
tip.style.cssText = 'position:fixed;top:0;left:0;z-index:99999;background:#0B7A4B;color:#fff;padding:6px 12px;font-size:14px'
document.body.appendChild(tip)

const RESUME_ID = 3
const PASS = 60
const DRY_RUN = true
const DAILY_MAX = 1
const APPLY_MIN = 3
const MAX_DEEP = 3
let lastFirst = ''
let TOKEN = ''

chrome.storage.local.get('token')
  .then(data => { TOKEN = data.token || ''; scan() })
  .catch(e => { tip.textContent = `[求职助手] 读取Token失败：${e.message}` })

function scan() {
  if (!TOKEN){
    const message = '[求职助手] 请先点击插件图标保存Token'
    if(tip.textContent !== message){
        tip.textContent = message
    }
    return
  }
  const cards = document.querySelectorAll('.job-card-box')
  if (cards.length === 0) return
  const first = cards[0].querySelector('.job-name')?.innerText
  if (first === lastFirst) return
  lastFirst = first

  const list = [...cards].map(c => ({
    el: c,
    name: c.querySelector('.job-name')?.innerText,
    company:c.querySelector('.boss-name')?.innerText || '未知',
    tags: [...c.querySelectorAll('.tag-list li')].map(li => li.innerText)
  }))

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
    .then(r => r.ok ? r.json() : Promise.reject(`HTTP ${r.status}`))
    .then(scores => {
      scores.forEach((s, i) => mark(list[i].el, s))
      tip.textContent = `[求职助手] 已打分 ${scores.length} 个岗位`
      deepCheck(list,scores)
    })
    .catch(e => { tip.textContent = `[求职助手] 打分失败：${e}` })
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
    const c = document.querySelector('.greet-boss-footer .cancel-btn')
    if (c) { c.click(); return true }
    await sleep(300)
  }
  return false
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
