const API = 'http://127.0.0.1:8000'
const formBox = document.querySelector('#form')
const doneBox = document.querySelector('#done')
const userInput = document.querySelector('#username')
const passInput = document.querySelector('#password')
const statusEl = document.querySelector('#status')

function show(text, bad = false) {
  statusEl.textContent = text
  statusEl.className = bad ? 'bad' : ''
}

function setLogged(yes) {
  formBox.hidden = yes
  doneBox.hidden = !yes
}

async function pickResume(token) {
  const r = await fetch(`${API}/resumes/me`, {
    headers: { 'Authorization': `Bearer ${token}` }
  })
  if (!r.ok) {
    throw new Error(r.status === 401 ? '登录已过期，请重新登录' : `HTTP ${r.status}`)
  }
  const list = await r.json()
  if (!list.length) throw new Error('你还没有上传简历')
  const newest = list.reduce((a, b) => (b.id > a.id ? b : a))
  await chrome.storage.local.set({ resume_id: newest.id })
  return newest
}

async function login() {
  const username = userInput.value.trim()
  const password = passInput.value
  if (!username || !password) {
    show('账号和密码都要填', true)
    return
  }
  show('登录中…')
  try {
    const r = await fetch(`${API}/users/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password })
    })
    if (!r.ok) {
      throw new Error(r.status === 401 ? '用户名或密码错误' : `HTTP ${r.status}`)
    }
    const token = (await r.json()).access_token
    passInput.value = ''
    await chrome.storage.local.set({ token, username })
    const resume = await pickResume(token)
    setLogged(true)
    show(`${username} · 用简历 #${resume.id} ${resume.original_filename}\n请刷新招聘页面`)
  } catch (e) {
    show(e.message, true)
  }
}

document.querySelector('#login').addEventListener('click', login)

document.querySelector('#logout').addEventListener('click', async () => {
  await chrome.storage.local.remove(['token', 'resume_id'])
  setLogged(false)
  show('已退出，请重新登录')
})

document.querySelector('#clearq').addEventListener('click', async () => {
  await chrome.storage.local.remove('jm_apply_queue')
  show('投递队列已清空')
})

chrome.storage.local.get(['token', 'username']).then(async data => {
  userInput.value = data.username || ''
  if (!data.token) return
  try {
    const resume = await pickResume(data.token)
    setLogged(true)
    show(`${data.username || ''} · 用简历 #${resume.id} ${resume.original_filename}`)
  } catch (e) {
    setLogged(false)
    show(e.message, true)
  }
})