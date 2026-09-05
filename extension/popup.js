const input = document.querySelector('#token')
const status = document.querySelector('#status')

chrome.storage.local.get('token').then(data => {
  input.value = data.token || ''
})

document.querySelector('#save').addEventListener('click', async () => {
  await chrome.storage.local.set({ token: input.value.trim() })
  status.textContent = '已保存，请刷新招聘页面'
})