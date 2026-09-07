<script setup>
import { ref, computed, onMounted } from 'vue'
import request from '../api/request'

const leads = ref([])
const loading = ref(false)
const error = ref('')
const filter = ref('')

// 状态筛选项。'' 表示不筛选，看全部。
const FILTERS = [
  { value: '', label: '全部' },
  { value: '新抓取', label: '新抓取' },
  { value: '待投递', label: '待投递' },
  { value: '已投递', label: '已投递' },
  { value: '已跳过', label: '已跳过' },
]

async function load() {
  loading.value = true
  error.value = ''
  try {
    const res = await request.get('/leads', {
      params: filter.value ? { status: filter.value } : {},
    })
    leads.value = res.data
  } catch (e) {
    error.value = e.response?.data?.detail || e.message || '加载失败'
  } finally {
    loading.value = false
  }
}

function pick(value) {
  filter.value = value
  load()
}

onMounted(load)

// 分数分档：和插件里卡片左边那条色条用同一套阈值，保持一致
function tone(score) {
  if (score >= 60) return 'high'
  if (score >= 30) return 'mid'
  return 'low'
}

const counts = computed(() => {
  const c = {}
  for (const l of leads.value) c[l.status] = (c[l.status] || 0) + 1
  return c
})
</script>

<template>
  <div class="wrap">
    <div class="head">
      <div>
        <h2>岗位池</h2>
        <p class="sub">
          插件在招聘页面抓到的岗位会自动存到这里。分数是规则粗筛的结果，只看职位名和标签，不代表最终判断。
        </p>
      </div>
      <button class="btn" :disabled="loading" @click="load">
        {{ loading ? '加载中…' : '刷新' }}
      </button>
    </div>

    <div class="bar">
      <button
        v-for="f in FILTERS"
        :key="f.value"
        class="chip"
        :class="{ on: filter === f.value }"
        @click="pick(f.value)"
      >
        {{ f.label }}
        <span v-if="f.value && counts[f.value]" class="n">{{ counts[f.value] }}</span>
      </button>
      <span class="total">共 {{ leads.length }} 条</span>
    </div>

    <p v-if="error" class="err">{{ error }}</p>

    <div v-if="!loading && !leads.length" class="empty">
      <div class="empty-t">还没有抓到岗位</div>
      <div class="empty-s">
        打开 BOSS 直聘搜索岗位，插件会自动打分并把结果存到这里。
      </div>
    </div>

    <ul v-else class="list">
      <li v-for="l in leads" :key="l.id" class="row" :class="tone(l.quick_score)">
        <div class="score">{{ l.quick_score }}</div>
        <div class="mid">
          <a :href="l.url" target="_blank" rel="noopener" class="title">{{ l.title }}</a>
          <div class="meta">
            <span class="company">{{ l.company || '未标公司' }}</span>
            <span v-for="t in l.tags" :key="t" class="tag">{{ t }}</span>
          </div>
        </div>
        <div class="status" :class="'st-' + l.status">{{ l.status }}</div>
      </li>
    </ul>
  </div>
</template>

<style scoped>
.wrap { max-width: 980px; margin: 0 auto; padding: 4px 0 40px; }

.head { display: flex; align-items: flex-start; justify-content: space-between; gap: 20px; }
h2 { margin: 0 0 6px; font-size: 1.5rem; }
.sub { margin: 0 0 16px; color: #7f8aa3; font-size: 12.5px; line-height: 1.7; max-width: 640px; }

.btn {
  padding: 8px 18px;
  border: 1px solid #0b7a4b;
  background: #0b7a4b;
  color: #fff;
  border-radius: 8px;
  cursor: pointer;
  font-size: 13px;
  white-space: nowrap;
}
.btn:disabled { opacity: .6; cursor: default; }

.bar { display: flex; align-items: center; gap: 8px; margin-bottom: 14px; flex-wrap: wrap; }
.chip {
  padding: 5px 14px;
  border: 1px solid #2a3348;
  background: #0f1425;
  color: #9aa5bd;
  border-radius: 999px;
  cursor: pointer;
  font-size: 12px;
}
.chip.on { border-color: #0b7a4b; background: #0b7a4b; color: #fff; }
.n { opacity: .75; margin-left: 4px; }
.total { color: #6b7590; font-size: 12px; margin-left: auto; }

.err { color: #ff8a80; font-size: 13px; }

.empty {
  border: 1px dashed #2a3348;
  border-radius: 14px;
  padding: 56px 24px;
  text-align: center;
}
.empty-t { color: #c3ccdf; font-size: 15px; font-weight: 600; margin-bottom: 8px; }
.empty-s { color: #6b7590; font-size: 12.5px; line-height: 1.8; }

.list { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: 8px; }

.row {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 12px 16px;
  border: 1px solid #212a3d;
  border-left-width: 3px;
  border-radius: 10px;
  background: #0e1320;
}
.row.high { border-left-color: #0b7a4b; }
.row.mid  { border-left-color: #b6791a; }
.row.low  { border-left-color: #39425a; }

.score {
  flex: 0 0 46px;
  text-align: center;
  font-size: 17px;
  font-weight: 700;
  color: #c3ccdf;
}
.row.high .score { color: #35c48a; }
.row.mid .score  { color: #e0a03a; }

.mid { flex: 1; min-width: 0; }
.title {
  color: #e8ecf5;
  font-size: 14px;
  text-decoration: none;
  display: inline-block;
  max-width: 100%;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.title:hover { color: #35c48a; text-decoration: underline; }

.meta { display: flex; align-items: center; gap: 8px; margin-top: 5px; flex-wrap: wrap; }
.company { color: #8390aa; font-size: 12px; }
.tag {
  color: #6b7590;
  font-size: 11px;
  border: 1px solid #232c40;
  border-radius: 4px;
  padding: 1px 6px;
}

.status {
  flex: 0 0 auto;
  font-size: 12px;
  padding: 3px 10px;
  border-radius: 999px;
  border: 1px solid #2a3348;
  color: #8390aa;
  white-space: nowrap;
}
.status.st-待投递 { border-color: #0b7a4b; color: #35c48a; }
.status.st-已投递 { border-color: #2f5fb8; color: #6f9bff; }
.status.st-已跳过 { border-color: #3a3f52; color: #656e86; }
</style>
