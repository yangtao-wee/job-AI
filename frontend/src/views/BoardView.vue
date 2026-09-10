<template>
  <section class="board">
    <header class="head">
      <div>
        <p class="kicker">求职工作台</p>
        <h2>求职看板</h2>
      </div>
      <button class="btn" :disabled="loading" @click="load">
        {{ loading ? '加载中…' : '刷新' }}
      </button>
    </header>

    <p v-if="error" class="err">{{ error }}</p>

    <div v-if="s && !s.total" class="empty">
      岗位池还是空的。打开 BOSS 直聘，插件会自动抓取并打分。
    </div>

    <template v-else-if="s">
      <div class="tiles">
        <div class="tile">
          <b>{{ s.total }}</b><span>插件抓取的岗位</span>
        </div>
        <div class="tile">
          <b>{{ s.analyzed }}</b><span>已做精判（调过大模型）</span>
        </div>
        <div class="tile">
          <b>{{ s.to_apply }}</b><span>标记为待投递</span>
        </div>
        <div class="tile">
          <b>{{ s.applied }}</b><span>已投递</span>
        </div>
      </div>

      <h3 class="sec">求职漏斗</h3>
      <p class="sub">每一层都比上一层窄——这就是「便宜的操作全量跑，昂贵的操作只跑筛过的」。</p>
      <ul class="funnel">
        <li v-for="f in funnel" :key="f.label">
          <span class="fl">{{ f.label }}</span>
          <span class="ft">
            <span class="fbar" :style="{ width: pct(f.n, s.total) + '%' }"></span>
          </span>
          <span class="fn">{{ f.n }}</span>
          <span class="fc">{{ f.note }}</span>
        </li>
      </ul>

      <h3 class="sec">精判核对结果</h3>
      <p class="sub">
        {{ s.analyzed }} 份报告，共核对 <b>{{ s.need_total }}</b> 条岗位要求。
        依据必须能在简历里逐字查到，查不到就归入「缺依据」——不硬凑。
      </p>
      <div class="stack">
        <span class="sg ok" :style="{ width: pct(s.need_ok, s.need_total) + '%' }"></span>
        <span class="sg part" :style="{ width: pct(s.need_part, s.need_total) + '%' }"></span>
        <span class="sg lack" :style="{ width: pct(lack, s.need_total) + '%' }"></span>
      </div>
      <ul class="legend">
        <li><i class="ok"></i>有依据<b>{{ s.need_ok }}</b><em>{{ pct(s.need_ok, s.need_total) }}%</em></li>
        <li><i class="part"></i>部分支持<b>{{ s.need_part }}</b><em>{{ pct(s.need_part, s.need_total) }}%</em></li>
        <li><i class="lack"></i>缺依据<b>{{ lack }}</b><em>{{ pct(lack, s.need_total) }}%</em></li>
      </ul>

      <h3 class="sec">粗筛分数分布</h3>
      <p class="sub">规则打分，只看职位名和技能标签，本地计算、零成本、毫秒级。</p>
      <div class="scores">
        <div class="sc high">
          <b>{{ s.high }}</b><span>80 分以上</span><em>方向高度吻合</em>
        </div>
        <div class="sc mid">
          <b>{{ s.mid }}</b><span>60 – 79 分</span><em>值得看一眼</em>
        </div>
        <div class="sc low">
          <b>{{ s.low }}</b><span>60 分以下</span><em>不花钱精判</em>
        </div>
      </div>
    </template>
  </section>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import request from '../api/request'

const s = ref(null)
const loading = ref(false)
const error = ref('')

const lack = computed(() =>
  s.value ? s.value.need_total - s.value.need_ok - s.value.need_part : 0
)

const funnel = computed(() => {
  if (!s.value) return []
  return [
    { label: '插件抓取', n: s.value.total, note: '打开招聘页面时采集' },
    { label: '采到 JD', n: s.value.with_jd, note: '有岗位描述才能精判' },
    { label: '粗筛过线', n: s.value.passed, note: '60 分以上' },
    { label: '已精判', n: s.value.analyzed, note: '调大模型，40–70 秒/个' },
    { label: '待投递', n: s.value.to_apply, note: '人工确认要投的' },
    { label: '已投递', n: s.value.applied, note: '插件按队列执行' },
  ]
})

function pct(n, total) {
  if (!total) return 0
  return Math.round((n / total) * 100)
}

async function load() {
  loading.value = true
  error.value = ''
  try {
    const res = await request.get('/leads/stats')
    s.value = res.data
  } catch (e) {
    error.value = e.response?.data?.detail || '统计数据拉取失败'
  } finally {
    loading.value = false
  }
}

onMounted(load)
</script>

<style scoped>
.board { max-width: 880px; padding-bottom: 64px; }

.head { display: flex; align-items: flex-end; justify-content: space-between; margin-bottom: 28px; }
.kicker { margin: 0 0 6px; font-size: 12px; letter-spacing: .2em; text-transform: uppercase; color: var(--muted); }
.head h2 { margin: 0; font-size: 27px; }
.btn {
  padding: 9px 18px; border: 1px solid var(--border); border-radius: 10px;
  background: var(--panel); color: var(--text); cursor: pointer; font-size: 13px;
}
.btn:hover:not(:disabled) { border-color: var(--primary); }
.btn:disabled { opacity: .6; cursor: default; }

.err { padding: 12px 16px; border-radius: 10px; background: rgba(255,90,90,.1); color: #ff9a8f; }
.empty { padding: 40px; text-align: center; color: var(--muted); border: 1px dashed var(--border); border-radius: 16px; }

.tiles { display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: 14px; margin-bottom: 44px; }
.tile { padding: 18px 20px; border: 1px solid var(--border); border-radius: 16px; background: var(--panel); }
.tile b { display: block; font-size: 30px; line-height: 1.15; font-variant-numeric: tabular-nums; }
.tile span { display: block; margin-top: 6px; font-size: 12.5px; color: var(--muted); }

.sec { margin: 0 0 6px; font-size: 17px; }
.sub { margin: 0 0 18px; font-size: 13px; color: var(--muted); line-height: 1.8; max-width: 64ch; }
.sub b { color: var(--text); }

.funnel { list-style: none; margin: 0 0 44px; padding: 0; display: flex; flex-direction: column; gap: 8px; }
.funnel li { display: grid; grid-template-columns: 86px 1fr 44px 168px; align-items: center; gap: 14px; }
.fl { font-size: 13px; color: var(--text); }
.ft { height: 26px; border-radius: 7px; background: var(--panel); overflow: hidden; }
.fbar { display: block; height: 100%; border-radius: 7px; background: linear-gradient(90deg, var(--primary), var(--cyan)); min-width: 3px; }
.fn { font-size: 16px; font-weight: 700; text-align: right; font-variant-numeric: tabular-nums; }
.fc { font-size: 12px; color: var(--muted); }

.stack { display: flex; height: 30px; border-radius: 9px; overflow: hidden; background: var(--panel); margin-bottom: 16px; }
.sg { display: block; height: 100%; }
.sg.ok { background: var(--cyan); }
.sg.part { background: var(--salary); }
.sg.lack { background: var(--panel-strong); }

.legend { list-style: none; margin: 0 0 44px; padding: 0; display: flex; gap: 26px; flex-wrap: wrap; }
.legend li { display: flex; align-items: center; gap: 8px; font-size: 13px; color: var(--muted); }
.legend i { width: 11px; height: 11px; border-radius: 3px; }
.legend i.ok { background: var(--cyan); }
.legend i.part { background: var(--salary); }
.legend i.lack { background: var(--panel-strong); border: 1px solid var(--border); }
.legend b { color: var(--text); font-size: 15px; font-variant-numeric: tabular-nums; }
.legend em { font-style: normal; color: var(--muted); }

.scores { display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 14px; }
.sc { padding: 20px; border: 1px solid var(--border); border-left-width: 3px; border-radius: 16px; background: var(--panel); }
.sc.high { border-left-color: var(--cyan); }
.sc.mid { border-left-color: var(--salary); }
.sc.low { border-left-color: var(--border); }
.sc b { display: block; font-size: 27px; line-height: 1.2; font-variant-numeric: tabular-nums; }
.sc span { display: block; margin-top: 5px; font-size: 13px; color: var(--text); }
.sc em { display: block; margin-top: 3px; font-style: normal; font-size: 12px; color: var(--muted); }

@media (max-width: 700px) {
  .funnel li { grid-template-columns: 76px 1fr 40px; }
  .fc { display: none; }
}
</style>
