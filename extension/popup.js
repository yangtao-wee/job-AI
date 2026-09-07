const tokenInput = document.querySelector('#token')
const resumeSel = document.querySelector('#resume')
const statusEl = document.querySelector('#status')

async function loadResumes() {
  const token = tokenInput.value.trim()
  if (!token) {
    statusEl.textContent = '请先填 Token'
    return
  }
  statusEl.textContent = '加载中…'
  try {
    const r = await fetch('http://127.0.0.1:8000/resumes/me', {
      headers: { 'Authorization': `Bearer ${token}` }
    })
    if (!r.ok) throw new Error(`HTTP ${r.status}`)
    const list = await r.json()
    const saved = (await chrome.storage.local.get('resume_id')).resume_id
    resumeSel.innerHTML = ''
    for (const x of list) {
      const o = document.createElement('option')
      o.value = x.id
      o.textContent = `#${x.id} ${x.original_filename}`
      if (x.id === saved) o.selected = true
      resumeSel.appendChild(o)
    }
    statusEl.textContent = `找到 ${list.length} 份简历`
  } catch (e) {
    statusEl.textContent = `加载失败：${e.message}`
  }
  
}

document.querySelector('#load').addEventListener('click', loadResumes)

document.querySelector('#save').addEventListener('click', async () => {
  await chrome.storage.local.set({
    token: tokenInput.value.trim(),
    resume_id: Number(resumeSel.value) || null
  })
  statusEl.textContent = '已保存，请刷新招聘页面'
})

chrome.storage.local.get('token').then(data => {
  tokenInput.value = data.token || ''
  if (tokenInput.value) loadResumes()
})