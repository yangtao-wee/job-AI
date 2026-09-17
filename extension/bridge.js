// 只在岗位池网页（本机 5173 / 8080）上运行：网页点「补读JD」，把要读的岗位交给插件。
// 插件把队列存起来，BOSS 详情页上的 content.js 看到队列就挨个读。
document.documentElement.dataset.jmBridge = '1'

// 只收 BOSS 的岗位详情页链接，别的网址一律不去
const JOB_URL = /^https:\/\/www\.zhipin\.com\/job_detail\/[\w~-]+\.html(\?.*)?$/

function reply(data) {
  window.postMessage({ source: 'jm-ext', type: 'read-jd', ...data }, location.origin)
}

window.addEventListener('message', async event => {
  if (event.source !== window || event.data?.source !== 'jm-pool' || event.data.type !== 'read-jd') return
  const queue = (Array.isArray(event.data.queue) ? event.data.queue : [])
    .filter(j => j && Number.isInteger(j.id) && JOB_URL.test(j.url || ''))
    .map(j => ({ id: j.id, url: j.url, title: String(j.title || '') }))
  if (!queue.length) return reply({ ok: false, error: '没有可以补读的岗位链接' })
  const { token, resume_id } = await chrome.storage.local.get(['token', 'resume_id'])
  if (!token || !resume_id) return reply({ ok: false, error: '插件还没登录或没选简历：点浏览器右上角的插件图标登录' })
  await chrome.storage.local.set({
    jm_read_queue: queue,
    jm_read_meta: { runStart: Date.now(), done: 0, closed: 0, failed: 0 }
  })
  reply({ ok: true, count: queue.length })
})
