<template>
  <section class="ap">
    <header class="head">
      <div>
        <p class="kicker">求职进度跟踪</p>
        <h2>投递管理</h2>
      </div>
      <button class="btn" :disabled="loading" @click="load">
        {{ loading ? '刷新中…' : '刷新' }}
      </button>
    </header>

    <p v-if="error" class="err">{{ error }}</p>

    <div class="tiles">
      <div class="tile"><b>{{ s.total }}</b><span>岗位池总数</span></div>
      <div class="tile"><b>{{ s.to_apply }}</b><span>待投递</span></div>
      <div class="tile hi"><b>{{ s.applied }}</b><span>已投递</span></div>
      <div class="tile"><b>{{ s.skipped }}</b><span>已跳过</span></div>
    </div>

    <div v-if="!loading && !rows.length" class="empty">
      <div class="empty-t">还没有投递记录</div>
      <div class="empty-s">
        去「岗位池」标记要投的岗位，再用浏览器插件点「开始投递」。
      </div>
    </div>

    <template v-else>
      <p class="tip">
        共 <b>{{ rows.length }}</b> 条投递记录，按投递时间从新到旧。
        点岗位名可回到 BOSS 页面查看沟通进展。
      </p>

      <ul class="list">
        <li v-for="l in rows" :key="l.id" class="row">
          <div class="score" :class="tone(l.quick_score)">{{ l.quick_score }}</div>

          <div class="mid">
            <a :href="l.url" target="_blank" rel="noopener" class="title">{{ l.title }}</a>
            <div class="meta">
              <span class="company">{{ l.company || '未标公司' }}</span>
              <span v-for="t in l.tags" :key="t" class="tag">{{ t }}</span>
            </div>
          </div>

          <div class="deep">
            <router-link
              v-if="l.report_id"
              :to="'/report/' + l.report_id"
              class="deeplink"
            >
              <b class="ok">{{ l.deep_ok }}</b> 有依据
              <b class="part">{{ l.deep_part }}</b> 部分
              <span class="dim">/ {{ l.deep_total }}</span>
              <span class="go">›</span>
            </router-link>
            <span v-else class="dim">未精判</span>
          </div>

          <div class="when">{{ when(l.updated_at) }}</div>
        </li>
      </ul>
    </template>
  </section>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import request from '../api/request'

const rows = ref([])
const s = ref({ total: 0, to_apply: 0, applied: 0, skipped: 0 })
const loading = ref(false)
const error = ref('')

function tone(score) {
  if (score >= 60) return 'high'
  if (score >= 30) return 'mid'
  return 'low'
}

function when(value) {
  if (!value) return ''
  const d = new Date(value)
  const pad = n => String(n).padStart(2, '0')
  return `${d.getMonth() + 1}月${d.getDate()}日 ${pad(d.getHours())}:${pad(d.getMinutes())}`
}

async function load() {
  loading.value = true
  error.value = ''
  try {
    const [list, stat] = await Promise.all([
      request.get('/leads', { params: { status: '已投递', limit: 200 } }),
      request.get('/leads/stats'),
    ])
    rows.value = [...list.data.items].sort(
      (a, b) => new Date(b.updated_at) - new Date(a.updated_at)
    )
    s.value = stat.data
  } catch (e) {
    error.value = e.response?.data?.detail || '读取失败，请点刷新重试'
  } finally {
    loading.value = false
  }
}

onMounted(load)
</script>

<style scoped>
.ap { max-width: 940px; padding-bottom: 64px; }

.head { display: flex; align-items: flex-end; justify-content: space-between; margin-bottom: 26px; }
.kicker { margin: 0 0 6px; font-size: 12px; letter-spacing: .2em; text-transform: uppercase; color: var(--muted); }
.head h2 { margin: 0; font-size: 27px; }
.btn {
  padding: 9px 18px; border: 1px solid var(--border); border-radius: 10px;
  background: var(--panel); color: var(--text); cursor: pointer; font-size: 13px;
}
.btn:hover:not(:disabled) { border-color: var(--primary); }
.btn:disabled { opacity: .6; cursor: default; }

.err { padding: 12px 16px; border-radius: 10px; background: rgba(255,90,90,.1); color: #ff9a8f; }

.tiles { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 14px; margin-bottom: 26px; }
.tile { padding: 18px 20px; border: 1px solid var(--border); border-radius: 16px; background: var(--panel); }
.tile b { display: block; font-size: 30px; line-height: 1.15; font-variant-numeric: tabular-nums; }
.tile span { display: block; margin-top: 6px; font-size: 12.5px; color: var(--muted); }
.tile.hi { border-color: rgba(37,208,196,.4); }
.tile.hi b { color: var(--cyan); }

.tip { margin: 0 0 16px; font-size: 13px; color: var(--muted); line-height: 1.8; }
.tip b { color: var(--text); }

.empty { border: 1px dashed var(--border); border-radius: 16px; padding: 56px 24px; text-align: center; }
.empty-t { color: var(--text); font-size: 15px; font-weight: 600; margin-bottom: 8px; }
.empty-s { color: var(--muted); font-size: 12.5px; line-height: 1.8; }

.list { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: 8px; }
.row {
  display: flex; align-items: center; gap: 14px;
  padding: 12px 16px; border: 1px solid var(--border);
  border-left-width: 3px; border-left-color: var(--cyan);
  border-radius: 12px; background: var(--panel);
}

.score { flex: 0 0 42px; text-align: center; font-size: 17px; font-weight: 700; color: var(--muted); font-variant-numeric: tabular-nums; }
.score.high { color: var(--cyan); }
.score.mid { color: var(--salary); }

.mid { flex: 1; min-width: 0; }
.title {
  display: inline-block; max-width: 100%; color: var(--text); font-size: 14px;
  text-decoration: underline; text-decoration-color: var(--border); text-underline-offset: 3px;
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}
.title:hover { color: var(--cyan); text-decoration-color: var(--cyan); }
.meta { display: flex; align-items: center; gap: 8px; margin-top: 5px; flex-wrap: wrap; }
.company { color: var(--muted); font-size: 12px; }
.tag { color: var(--muted); font-size: 11px; border: 1px solid var(--border); border-radius: 4px; padding: 1px 6px; }

.deep { flex: 0 0 172px; font-size: 12px; color: var(--muted); white-space: nowrap; }
.deeplink { color: inherit; text-decoration: none; display: inline-flex; align-items: center; gap: 5px; }
.deeplink:hover .go { transform: translateX(2px); }
.deeplink .go { color: var(--cyan); font-size: 16px; line-height: 1; transition: transform .15s; }
.ok { color: var(--cyan); }
.part { color: var(--salary); }
.dim { color: var(--muted); opacity: .7; }

.when { flex: 0 0 120px; text-align: right; font-size: 12px; color: var(--muted); font-variant-numeric: tabular-nums; }

@media (max-width: 720px) {
  .row { flex-wrap: wrap; }
  .deep, .when { flex: 0 0 auto; text-align: left; }
}
</style>
