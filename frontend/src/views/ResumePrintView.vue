<script setup>
import { reactive, ref, computed, onMounted } from 'vue'
import request from '../api/request'

const STORE_KEY = 'resume_builder_v3'

// 三套模板：结构完全一样，只换样式类。
// 这样加模板只需要写 CSS，不用碰渲染逻辑。
const TEMPLATES = [
  { id: 'plain', name: '简约', desc: '黑白细线，最保守，投国企和传统公司稳' },
  { id: 'solid', name: '稳重', desc: '深色姓名区，标题带竖条，层次清楚' },
  { id: 'accent', name: '现代', desc: '主色强调，适合互联网和创业公司' },
]
const tpl = ref('plain')

// raw：你自己写的原始材料。姓名、联系方式、经历、学校全写在里面。
const raw = ref('')
const target = ref('')
// profile：模型整理出来的结构化档案。有什么就渲染什么，没有的整段不出现。
const profile = reactive({
  name: '',
  target: '',
  city: '',
  phone: '',
  email: '',
  link: '',
  summary: '',
  skills: [],
  projects: [],
  works: [],
  education: [],
})

const loading = ref(false)
const error = ref('')

// 没生成过就不渲染那张 A4 纸——空白纸悬在暗色界面里很难看
const hasContent = computed(() =>
  !!(profile.summary || profile.works.length || profile.projects.length || profile.name)
)

function save() {
  try {
    localStorage.setItem(STORE_KEY, JSON.stringify({
  raw: raw.value, target: target.value, profile, tpl: tpl.value
}))
  } catch (e) {
    // 存储被禁用时忽略
  }
}

onMounted(() => {
  try {
    const saved = JSON.parse(localStorage.getItem(STORE_KEY) || 'null')
    if (saved) {
      raw.value = saved.raw || ''
      target.value = saved.target || ''
      tpl.value = saved.tpl || 'plain'
      Object.assign(profile, saved.profile || {})
    }
  } catch (e) {
    // 存的东西坏了就当没存过
  }
})

async function build() {
  if (raw.value.trim().length < 10) {
    error.value = '材料太短了，至少写 10 个字'
    return
  }
  loading.value = true
  error.value = ''
  try {
    const res = await request.post(
      '/resumes/profile/build',
      { raw: raw.value, target: target.value },
      { timeout: 120000 }   // 默认 5 秒不够，生成要 20 秒左右
    )
    const d = res.data
    // 全空 = 后端判定这段材料不是「本人经历」（多半是把 JD 粘进来了）
    if (!d.summary && !(d.works || []).length && !(d.projects || []).length) {
      error.value = '没能从材料里认出你的经历。这里要写你自己做过什么，不是岗位的招聘要求。'
      return
    }
    Object.assign(profile, {
      name: d.name || '',
      target: d.target || '',
      city: d.city || '',
      phone: d.phone || '',
      email: d.email || '',
      link: d.link || '',
      summary: d.summary || '',
      skills: d.skills || [],
      projects: d.projects || [],
      works: d.works || [],
      education: d.education || [],
    })
    save()
  } catch (e) {
    error.value = e.response?.data?.detail || e.message || '生成失败'
  } finally {
    loading.value = false
  }
}

function printResume() {
  window.print()
}
</script>

<template>
  <div class="wrap no-print">
    <h2 class="h2">简历生成</h2>
  <label class="raw-label">
  求职意向：
  <input
    v-model.trim="target"
    class="target-input"
    maxlength="50"
    placeholder="例如：Python后端开发工程师"
    @change="save"
  >
</label>
    <label class="raw-label">
      把你的情况写在这里：姓名、联系方式、求职意向、工作经历、项目、学校，有什么写什么。
      口语、碎片都行；写得越具体，生成的越可信。没写的内容不会出现在简历上。
      <textarea
        v-model="raw"
        @change="save"
        rows="14"
        placeholder="格式示例（改成你自己的）：

张明，深圳，手机 138xxxxxxxx，邮箱 xxx@qq.com
想找后端开发工程师

2022.03-2024.06 在XX科技做后端开发。
负责订单系统接口开发，日均处理20万单；
把慢查询从3秒优化到200毫秒；带过2个实习生。

2024.07至今 独立做了一个记账小程序。
Python + FastAPI + MySQL，微信小程序前端。
做了账单自动分类和月度统计图表，自己用了半年。

2018-2022 XX大学 计算机科学与技术 本科"
      ></textarea>
    </label>

    <div class="actions">
      <button class="btn" :disabled="loading" @click="build">
        {{ loading ? '生成中…约 20 秒' : '生成简历' }}
      </button>
      <button class="btn ghost" @click="printResume">导出 PDF</button>
      <span v-if="error" class="err">{{ error }}</span>
    </div>

    <div class="tpls">
      <span class="tpls-label">模板</span>
      <button
        v-for="t in TEMPLATES"
        :key="t.id"
        class="tpl-btn"
        :class="{ on: tpl === t.id }"
        :title="t.desc"
        @click="tpl = t.id; save()"
      >{{ t.name }}</button>
      <span class="tpl-desc">{{ TEMPLATES.find(t => t.id === tpl).desc }}</span>
    </div>

    <p class="tip">
      下面的简历正文可以直接点进去改（改动只用于本次打印，不会保存）。
      导出时在打印窗口选「另存为 PDF」，边距选「无」。
    </p>
  </div>

  <!-- 空状态：跟暗色界面一致，不用那张刺眼的白纸 -->
  <div v-if="!hasContent" class="placeholder no-print">
    <svg viewBox="0 0 24 24" class="ph-icon">
      <path d="M7 3h7l5 5v13H6V4Z" />
      <path d="M14 3v5h5M9 13h6M9 17h4" />
    </svg>
    <div class="ph-title">还没有生成简历</div>
    <div class="ph-text">
      把你的情况写在上面的框里 —— 姓名、联系方式、求职意向、工作经历、项目、学校，<br>
      有什么写什么，然后点「生成简历」。没写的内容不会出现在简历上。
    </div>
  </div>

  <article v-else class="resume-page" :class="'tpl-' + tpl">
    <!-- spellcheck=false：关掉浏览器的红色波浪线，
         SQLAlchemy 这种技术词会被误判成拼写错误 -->
    <div contenteditable="true" spellcheck="false" class="body">
      <header class="head" v-if="profile.name || profile.phone || profile.email">
        <h1 class="name" v-if="profile.name">{{ profile.name }}</h1>
        <div class="target" v-if="profile.target">求职意向：{{ profile.target }}</div>
        <div class="contact">
          <!-- filter(Boolean) 去掉没填的项，再用分隔符连接，
               避免最后一项后面留一个孤零零的竖线 -->
          <template
            v-for="(v, i) in [profile.city, profile.phone, profile.email, profile.link].filter(Boolean)"
            :key="i"
          >
            <span v-if="i" class="sep">|</span>{{ v }}
          </template>
        </div>
      </header>

      <section v-if="profile.summary">
        <h2>个人概况</h2>
        <p class="summary">{{ profile.summary }}</p>
      </section>

      <section v-if="profile.projects.length">
        <h2>项目经历</h2>
        <div v-for="(p, pi) in profile.projects" :key="pi" class="block">
          <div class="row">
            <span class="strong">{{ p.name }}</span>
            <span class="dim" v-if="p.role">{{ p.role }}</span>
            <span class="period" v-if="p.period">{{ p.period }}</span>
          </div>
          <div v-if="p.stack" class="stack">技术栈：{{ p.stack }}</div>
          <ul v-if="p.items.length">
            <li v-for="(it, i) in p.items" :key="i">{{ it }}</li>
          </ul>
        </div>
      </section>

      <section v-if="profile.works.length">
        <h2>工作经历</h2>
        <div v-for="(w, wi) in profile.works" :key="wi" class="block">
          <div class="row">
            <span class="strong" v-if="w.company">{{ w.company }}</span>
            <span class="dim" v-if="w.title">{{ w.title }}</span>
            <span class="period" v-if="w.period">{{ w.period }}</span>
          </div>
          <ul v-if="w.items.length">
            <li v-for="(it, i) in w.items" :key="i">{{ it }}</li>
          </ul>
        </div>
      </section>

      <section v-if="profile.skills.length">
        <h2>专业技能</h2>
        <div v-for="(s, si) in profile.skills" :key="si" class="skill">
          <span class="skill-group">{{ s.group }}</span>
          <span class="skill-text">{{ s.text }}</span>
        </div>
      </section>

      <section v-if="profile.education.length">
        <h2>教育背景</h2>
        <div v-for="(e, ei) in profile.education" :key="ei" class="row edu">
          <span class="strong" v-if="e.school">{{ e.school }}</span>
          <span class="dim">{{ [e.major, e.degree].filter(Boolean).join(' · ') }}</span>
          <span class="period" v-if="e.period">{{ e.period }}</span>
        </div>
      </section>

      <p v-if="!profile.summary && !profile.works.length && !profile.projects.length" class="empty">
        把你的情况写在上面，点「生成简历」。
      </p>
    </div>
  </article>
</template>

<style scoped>
.wrap { max-width: 210mm; margin: 18px auto 10px; }
.h2 { font-size: 16px; margin: 0 0 12px; }

label { display: flex; flex-direction: column; gap: 6px; font-size: 12px; color: #9aa5bd; line-height: 1.6; }
/* 全局是暗色主题，输入框背景是深色，所以文字必须用浅色，
   否则深底 + 深字 = 看不见 */
.target-input,
textarea {
  background: #0f1425;
  border: 1px solid #2a3348;
  border-radius: 6px;
  padding: 10px 12px;
  font-size: 13px;
  font-family: inherit;
  color: #e8ecf5;
  resize: vertical;
  line-height: 1.7;
}
.target-input::placeholder,
textarea::placeholder { color: #4e5772; }

.target-input:focus,
textarea:focus { outline: none; border-color: #0b7a4b; }
.raw-label { margin-bottom: 12px; }

.actions { display: flex; align-items: center; gap: 10px; margin-bottom: 8px; }
.btn {
  padding: 8px 18px;
  border: 1px solid #0b7a4b;
  background: #0b7a4b;
  color: #fff;
  border-radius: 6px;
  cursor: pointer;
  font-size: 13px;
}
.btn:disabled { opacity: .6; cursor: default; }
.btn.ghost { background: #fff; color: #0b7a4b; }
.err { color: #ff8a80; font-size: 12px; }
.tip { color: #7f8aa3; font-size: 12px; margin: 0 0 14px; line-height: 1.6; }

/* A4：210mm × 297mm，四周 15-16mm 是中文简历的常规边距 */
.resume-page {
  width: 210mm;
  min-height: 297mm;
  margin: 0 auto 40px;
  padding: 16mm 15mm;
  box-sizing: border-box;
  background: #fff;
  color: #1a1a1a;
  border-radius: 3px;
  /* 两层阴影：近处一层压边，远处一层做浮起，在暗色底上更像一张纸 */
  box-shadow: 0 2px 5px rgba(0, 0, 0, .28), 0 18px 50px rgba(0, 0, 0, .45);
  font-family: "Microsoft YaHei", "PingFang SC", "Hiragino Sans GB",
               "Source Han Sans SC", "Noto Sans CJK SC", sans-serif;
  font-size: 10.5pt;
  line-height: 1.55;
}
.body:focus { outline: 1px dashed #c8d3dd; outline-offset: 6px; }

/* 全局暗色主题有 h1,h2,h3,h4 { color: var(--text) }，
   简历要打到白纸上，这里必须显式写死深色，否则被覆盖成浅灰 */
.resume-page,
.resume-page h1,
.resume-page h2,
.resume-page p,
.resume-page li,
.resume-page div,
.resume-page span { color: #1a1a1a; }

.head { margin-bottom: 12px; }
.name { font-size: 19pt; font-weight: 700; margin: 0 0 4px; letter-spacing: 1px; }
.target { font-size: 11pt; margin-bottom: 4px; }
.contact { font-size: 9.5pt; }
.contact, .period, .stack, .dim { color: #444 !important; }
.sep { color: #bbb !important; margin: 0 8px; }
.empty { color: #999 !important; }

h2 {
  font-size: 11pt;
  font-weight: 700;
  margin: 14px 0 6px;
  padding-bottom: 3px;
  border-bottom: 1px solid #333;
  letter-spacing: 1px;
}

.summary { margin: 0; text-align: justify; }
.block { margin-bottom: 10px; break-inside: avoid; }
.row { display: flex; align-items: baseline; gap: 10px; margin-bottom: 2px; }
.strong { font-weight: 700; }
.period { margin-left: auto; font-size: 9.5pt; white-space: nowrap; }
.stack { font-size: 9.5pt; margin-bottom: 3px; }

ul { margin: 3px 0 0; padding-left: 17px; }
li { margin-bottom: 2px; text-align: justify; }

.skill { display: flex; gap: 12px; margin-bottom: 3px; }
/* nowrap + min-width 防止「测试与部署」这类四字以上分组名被折行 */
.skill-group { flex: 0 0 auto; min-width: 60px; font-weight: 700; white-space: nowrap; }
.skill-text { flex: 1; }

.edu { margin-bottom: 3px; }

/* ── 空状态 ───────────────────────────────── */
.placeholder {
  max-width: 210mm;
  margin: 0 auto 40px;
  padding: 64px 32px;
  text-align: center;
  border: 1px dashed #2a3348;
  border-radius: 14px;
  background: linear-gradient(180deg, rgba(255, 255, 255, .022), rgba(255, 255, 255, 0));
}
.ph-icon {
  width: 40px; height: 40px;
  fill: none;
  stroke: #3a4560;
  stroke-width: 1.5;
  stroke-linecap: round;
  stroke-linejoin: round;
  margin-bottom: 14px;
}
.ph-title { color: #c3ccdf; font-size: 15px; font-weight: 600; margin-bottom: 8px; }
.ph-text { color: #6b7590; font-size: 12.5px; line-height: 1.9; }

/* ── 模板选择器 ───────────────────────────── */
.tpls { display: flex; align-items: center; gap: 8px; margin: 4px 0 12px; flex-wrap: wrap; }
.tpls-label { color: #9aa5bd; font-size: 12px; }
.tpl-btn {
  padding: 5px 14px;
  border: 1px solid #2a3348;
  background: #0f1425;
  color: #9aa5bd;
  border-radius: 999px;
  cursor: pointer;
  font-size: 12px;
}
.tpl-btn.on { border-color: #0b7a4b; color: #fff; background: #0b7a4b; }
.tpl-desc { color: #6b7590; font-size: 12px; }

/* ── 模板二：稳重（深色姓名区 + 标题竖条）───── */
.tpl-solid { padding: 0 0 16mm; }
.tpl-solid .body { padding: 0 15mm; }
.tpl-solid .head {
  background: #1f2937;
  /* 负边距把深色块拉到纸张边缘，做出通栏效果 */
  margin: 0 -15mm 14px;
  padding: 13mm 15mm 9mm;
  /* 打印时默认会去掉背景色，这行强制保留 */
  -webkit-print-color-adjust: exact;
  print-color-adjust: exact;
}
.tpl-solid .head .name { color: #fff !important; }
.tpl-solid .head .target { color: #cbd5e1 !important; }
.tpl-solid .head .contact { color: #a9b6c9 !important; }
.tpl-solid .head .sep { color: #64748b !important; }
.tpl-solid h2 {
  border-bottom: none;
  border-left: 3px solid #1f2937;
  padding: 0 0 0 8px;
  margin: 16px 0 7px;
}

/* ── 模板三：现代（主色强调）──────────────── */
.tpl-accent .name { color: #0b7a4b !important; }
.tpl-accent h2 {
  color: #0b7a4b !important;
  border-bottom: 2px solid #0b7a4b;
  font-size: 10.5pt;
  letter-spacing: 3px;
  margin: 16px 0 7px;
}
.tpl-accent .strong { color: #0f172a !important; }
.tpl-accent .skill-group { color: #0b7a4b !important; }
.tpl-accent .head { border-bottom: 1px solid #e2e8f0; padding-bottom: 10px; }
</style>

<style>
/* 打印规则不能加 scoped —— 它要作用到 body 上 */
@page {
  size: A4;
  margin: 0;
}

@media print {
  body * { visibility: hidden !important; }
  .resume-page, .resume-page * { visibility: visible !important; }
  .resume-page {
    position: absolute;
    left: 0;
    top: 0;
    margin: 0;
    box-shadow: none;
  }
  .body:focus { outline: none !important; }
  .no-print { display: none !important; }
}
</style>
