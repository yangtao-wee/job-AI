<template>
  <section class="rp">
    <router-link to="/leads" class="back">← 回岗位池</router-link>

    <p v-if="error" class="err">{{ error }}</p>
    <p v-else-if="loading" class="tip">加载中…</p>

    <template v-else-if="rep">
      <header class="head">
        <h2>{{ rep.title }}</h2>
        <p class="company">{{ rep.company }}</p>
      </header>

      <div class="sum">
        <button class="s ok" :class="{ on: pick === '有依据' }" @click="toggle('有依据')">
          有依据 <b>{{ count('有依据') }}</b>
        </button>
        <button class="s part" :class="{ on: pick === '部分支持' }" @click="toggle('部分支持')">
          部分支持 <b>{{ count('部分支持') }}</b>
        </button>
        <button class="s lack" :class="{ on: pick === 'lack' }" @click="toggle('lack')">
          未找到依据 <b>{{ lackCount }}</b>
        </button>
        <button class="s all" :class="{ on: pick === '' }" @click="pick = ''">
          共 <b>{{ checks.length }}</b> 条要求
        </button>
      </div>

      <p class="how">
        简历被拆成 <b>{{ proofs.length }}</b> 行并编号，只把编号交给模型。
        模型输出只能引用编号，后端拿编号回查原文——<b>查不到就丢弃该条</b>。
        下面每条「依据」都是回查成功后取出的简历原文。
      </p>

      <p v-if="!shown.length" class="none-tip">
        这份报告里没有「{{ pickLabel }}」的条目。
      </p>

      <ul class="list">
        <li v-for="c in shown" :key="c.need_id" :class="tone(c.status)">
          <div class="top">
            <span class="kind">{{ needOf(c.need_id).kind || '要求' }}</span>
            <span class="badge">{{ c.status }}</span>
          </div>

          <p class="need">{{ needOf(c.need_id).text }}</p>

          <div v-if="c.proof_ids && c.proof_ids.length" class="proofs">
            <span class="plab">简历依据</span>
            <p v-for="pid in c.proof_ids" :key="pid" class="proof">
              <span class="pid">#{{ pid }}</span>{{ proofs[pid] }}
            </p>
          </div>
          <div v-else class="proofs none">
            <span class="plab">简历依据</span>
            <p class="proof empty">没有可引用的简历内容，该条不计入匹配。</p>
          </div>

          <p v-if="c.note" class="note">{{ c.note }}</p>
        </li>
      </ul>
    </template>
  </section>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import request from '../api/request'

const route = useRoute()
const rep = ref(null)
const loading = ref(true)
const error = ref('')

const checks = computed(() => rep.value?.content?.checks || [])
const needs = computed(() => rep.value?.content?.needs || [])
const proofs = computed(() => rep.value?.content?.proofs || [])

const pick = ref('')

const lackCount = computed(
  () => checks.value.length - count('有依据') - count('部分支持')
)

const shown = computed(() => {
  if (!pick.value) return checks.value
  if (pick.value === 'lack') {
    return checks.value.filter(
      c => c.status !== '有依据' && c.status !== '部分支持'
    )
  }
  return checks.value.filter(c => c.status === pick.value)
})

const pickLabel = computed(() => (pick.value === 'lack' ? '未找到依据' : pick.value))

function toggle(value) {
  pick.value = pick.value === value ? '' : value
}

function count(status) {
  return checks.value.filter(c => c.status === status).length
}

function needOf(id) {
  return needs.value.find(n => n.id === id) || { text: `要求 #${id}`, kind: '' }
}

function tone(status) {
  if (status === '有依据') return 'ok'
  if (status === '部分支持') return 'part'
  return 'lack'
}

onMounted(async () => {
  try {
    const res = await request.get(`/jobs/reports/${route.params.id}`)
    rep.value = res.data
  } catch (e) {
    error.value = e.response?.data?.detail || '报告拿不到，可能已被删除'
  } finally {
    loading.value = false
  }
})
</script>

<style scoped>
.rp { max-width: 840px; padding-bottom: 64px; }

.back { display: inline-block; margin-bottom: 22px; color: var(--muted); text-decoration: none; font-size: 13px; }
.back:hover { color: var(--cyan); }

.err { padding: 12px 16px; border-radius: 10px; background: rgba(255,90,90,.1); color: #ff9a8f; }
.tip { color: var(--muted); }

.head { margin-bottom: 20px; }
.head h2 { margin: 0 0 6px; font-size: 24px; line-height: 1.35; }
.company { margin: 0; color: var(--muted); font-size: 13.5px; }

.sum { display: flex; flex-wrap: wrap; gap: 10px; margin-bottom: 18px; }
.s {
  padding: 7px 14px; border-radius: 9px; font-size: 13px; font-family: inherit;
  background: var(--panel); border: 1px solid var(--border); color: var(--muted);
  cursor: pointer; transition: background .15s, border-color .15s;
}
.s:hover { background: var(--panel-strong); }
.s b { font-size: 15px; font-variant-numeric: tabular-nums; }
.s.ok { color: var(--cyan); border-color: rgba(37,208,196,.35); }
.s.part { color: var(--salary); border-color: rgba(255,174,74,.35); }
.s.lack b, .s.all b { color: var(--text); }
.s.on { background: var(--panel-strong); }
.s.ok.on { border-color: var(--cyan); }
.s.part.on { border-color: var(--salary); }
.s.lack.on, .s.all.on { border-color: var(--primary); color: var(--text); }

.none-tip {
  padding: 28px; text-align: center; color: var(--muted);
  border: 1px dashed var(--border); border-radius: 14px;
}

.how {
  margin: 0 0 28px; padding: 14px 18px; border-radius: 12px;
  background: var(--panel); border-left: 3px solid var(--primary);
  color: var(--muted); font-size: 13px; line-height: 1.85;
}
.how b { color: var(--text); }

.list { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: 12px; }
.list li {
  padding: 20px 22px; border: 1px solid var(--border);
  border-left-width: 3px; border-radius: 16px; background: var(--panel);
}
.list li.ok { border-left-color: var(--cyan); }
.list li.part { border-left-color: var(--salary); }
.list li.lack { border-left-color: var(--border); }

.top { display: flex; align-items: center; gap: 10px; margin-bottom: 10px; }
.kind {
  padding: 2px 9px; border-radius: 6px; background: var(--panel-strong);
  color: var(--muted); font-size: 11.5px;
}
.badge { margin-left: auto; font-size: 12.5px; font-weight: 700; }
.list li.ok .badge { color: var(--cyan); }
.list li.part .badge { color: var(--salary); }
.list li.lack .badge { color: var(--muted); }

.need { margin: 0 0 16px; font-size: 14.5px; line-height: 1.8; color: var(--text); }

.proofs { padding: 12px 14px; border-radius: 10px; background: var(--panel-strong); }
.plab {
  display: block; margin-bottom: 8px; font-size: 11px;
  letter-spacing: .14em; color: var(--muted);
}
.proof { margin: 0 0 7px; font-size: 13px; line-height: 1.75; color: var(--text); }
.proof:last-child { margin-bottom: 0; }
.pid {
  display: inline-block; margin-right: 8px; padding: 1px 7px; border-radius: 5px;
  background: rgba(85,114,243,.18); color: #9fb2ff;
  font-size: 11.5px; font-variant-numeric: tabular-nums;
}
.proof.empty { color: var(--muted); font-style: normal; }

.note {
  margin: 14px 0 0; padding-top: 12px; border-top: 1px solid var(--border);
  color: var(--muted); font-size: 13px; line-height: 1.85;
}
</style>
