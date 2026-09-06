<template>
<article
  class="card"
  :class="{ top: currentScore >= 80, featured }"
>
    <div class="card-top">
        <div class="card-id">
            <h3>{{ title }}</h3>
            <p class="card-meta">{{ company }} · {{ location }}</p>
        </div>
        <div class="score-ring" :style="{ '--score': `${currentScore ?? 0}%` }">
            <strong>{{ currentScore ?? '--' }}</strong>
            <span>匹配度</span>
        </div>
    </div>
    <p class="salary">薪资：{{ salary }}</p>
    <p class="card-desc">{{ description }}</p>
    <details
    v-if="currentScore !== undefined"
    class="match-detail"
>
    <summary>查看完整匹配报告</summary>
    <div class="match-detail-body">
<p>已完成维度合计：{{ currentScore }}/{{ currentMaxScore }}</p>
<p v-if="score !== undefined">技能匹配：{{ score }}/35</p>
<p v-if="matchedSkills?.length">
    已匹配：{{ matchedSkills.join('、') }}
</p>
<p v-if="missingSkills?.length">
    待补充：{{ missingSkills.join('、') }}
    <!-- 【语言固定的数组方法】，把数组连接成中文顿号分隔的文字。 -->
</p>
<p v-if="keywordScore !== undefined">关键词覆盖：{{ keywordScore }}/10</p>
<p v-if="matchedKeywords?.length">已覆盖关键词：{{ matchedKeywords.join('、') }}</p>
<p v-if="missingKeywords?.length">缺失关键词：{{ missingKeywords.join('、') }}</p>
<p v-if="requiredSkillScore !== undefined">AI必备技能参考(不计总分):{{ requiredSkillScore }}/15</p>
<p v-if="matchedRequiredSkills?.length">已满足必备技能：{{matchedRequiredSkills.join('、')}}</p>
<p v-if="missingRequiredSkills?.length">缺失必备技能：{{ missingRequiredSkills.join('、') }}</p>

<p v-if="expScore !== undefined">经历匹配：{{ expScore }}/30</p>
<p v-if="roleScore !== undefined">岗位方向：{{ roleScore }}/10</p>
<p v-if="prefScore !== undefined">求职偏好：{{ prefScore }}/15</p>
<div v-if="sem">
    <p>语义参考值：{{ sem.sim.toFixed(3) }}</p>
    <p>模型：{{ sem.model }}</p>
    <p>{{ sem.note }}</p>
</div>
<div v-if="aiNote">
    <h4>AI岗位建议</h4>
    <p>{{ aiNote.summary }}</p>
    <p v-if="aiNote.reasons?.length">推荐理由：{{ aiNote.reasons.join('、') }}</p>
    <p v-if="aiNote.gaps?.length">能力缺口：{{ aiNote.gaps.join('、') }}</p>
    <p v-if="aiNote.actions?.length">行动建议：{{ aiNote.actions.join('、') }}</p>
</div>
<p v-for="note in prefNotes" :key="note">{{ note }}</p>
<p v-if="roleNote">方向说明：{{ roleNote }}</p>
<div v-for="hit in expHits" :key="hit.responsibility">
    <p>岗位职责：{{ hit.responsibility }}</p>
    <p>简历证据：{{ hit.resume_evidence }}</p>
</div>
<p v-if="expMiss?.length">待补经历：{{ expMiss.join('、') }}</p>
<div v-if="requirements">
    <h4>岗位结构化要求</h4>
    <p>岗位职责：{{ requirements.responsibilities.join('、') || '未说明' }}</p>
    <p>必备技能：{{ requirements.required_skills.join('、') || '未说明'}}</p>
    <p>工作经验：{{ requirements.experience.join('、') || '未说明'}}</p>
    <p>学历要求：{{ requirements.education.join('、') || '未说明'}}</p>
    <p>加分项：{{ requirements.bonus_points.join('、') || '未说明'}}</p>

</div>
    </div>
</details>
<div class="card-actions">
    <button :disabled="matching" @click="emit('match')">
        {{ matching ? '匹配中...' : '开始匹配' }}
    </button>
</div>
<!-- 【框架提供】，向父页面发出名为match的消息 -->
</article>
</template>

<script setup>
// defineProps() 是 Vue 3 提供的固定语法；这个子组件允许父组件传这些数据进来，并且规定每个数据应该是什么类型。括号里面的 prop 名称是你自己定义的，类型 String/Number/Array/Boolean/Object 是 JavaScript 提供的。
defineProps({
    featured:Boolean,
    title:String,
    company:String,
    location:String,
    salary:String,
    description:String,
    currentScore:Number,
    currentMaxScore:Number,
    score:Number,
    matchedSkills:Array,
    missingSkills:Array,
    keywordScore:Number,
    matchedKeywords:Array,
    missingKeywords:Array,
    requiredSkillScore:Number,
    matchedRequiredSkills:Array,
    missingRequiredSkills:Array,
    matching:Boolean,
    requirements:Object,
    expScore:Number,
    expHits:Array,
    expMiss:Array,
    roleScore:Number,
    roleNote:String,
    prefScore:Number,
    prefNotes:Array,
    sem:Object,
    aiNote:Object
    // Boolean：【语言固定】，只有true或false。
})
const emit = defineEmits(['match'])
// 【框架提供】，登记组件允许发送的事件。

</script>

<style scoped>
.card {
    min-width: 0;
    min-height: 280px;
    margin: 0;
    padding: 22px;
    display: flex;
    flex-direction: column;
    gap: 16px;
    border: 1px solid var(--border);
    border-radius: 20px;
    background: var(--panel);
    transition: transform .18s ease, border-color .18s ease, background .18s ease;
}
.card:hover {
    transform: translateY(-3px);
    border-color: #3b4774;
    background: var(--panel-strong);
}
.card.top {
    border-color: #4564df;
    box-shadow: 0 18px 40px -28px #5b7cff;
}
.card-top {
    display: flex;
    justify-content: space-between;
    gap: 16px;
}
.card-id { min-width: 0; }
.card-id h3 {
    margin: 0;
    font-size: 1.15rem;
    line-height: 1.4;
}
.card-meta {
    margin: 7px 0 0;
    color: var(--muted);
    font-size: .85rem;
}
.score-ring {
    --score: 0%;
    position: relative;
    width: 62px;
    height: 62px;
    flex: 0 0 62px;
    display: grid;
    place-content: center;
    text-align: center;
    border-radius: 50%;
    background: conic-gradient(var(--cyan) var(--score), var(--border) 0);
}
.score-ring::before {
    content: "";
    position: absolute;
    inset: 6px;
    border-radius: 50%;
    background: var(--panel);
}
.score-ring strong,
.score-ring span {
    position: relative;
    z-index: 1;
}
.score-ring strong { font-size: 1rem; line-height: 1; }
.score-ring span { margin-top: 3px; color: var(--muted); font-size: .6rem; }
.salary {
    margin: 0;
    color: var(--salary);
    font-size: 1.3rem;
    font-weight: 700;
}
.card-desc {
    min-height: 60px;
    margin: 0;
    color: var(--muted);
    line-height: 1.6;
    display: -webkit-box;
    overflow: hidden;
    -webkit-line-clamp: 3;
    -webkit-box-orient: vertical;
}
.card p { line-height: 1.65; }
.card-actions {
    display: flex;
    gap: 10px;
    margin-top: auto;
}
.card-actions button {
    flex: 1;
    min-width: 0;
    margin: 0;
    padding: 11px 14px;
}
.card-actions button + button {
    color: #aebcff;
    border-color: var(--border);
    background: transparent;
}
.card {
  color: var(--text);
  background: var(--panel);
  box-shadow: none;
}

.card.featured {
  grid-column: 1 / -1;
  min-height: 330px;
  padding: 32px;
  background:
    radial-gradient(
      circle at 90% 10%,
      rgba(76, 141, 255, 0.12),
      transparent 36%
    ),
    linear-gradient(160deg, var(--panel-strong), var(--panel));
  border-color: rgba(76, 141, 255, 0.45);
}

.card.featured .card-id h3 {
  font-size: 1.6rem;
}

.card.featured .score-ring {
  width: 82px;
  height: 82px;
  flex-basis: 82px;
}

.card.featured .salary {
  font-size: 1.55rem;
}

.card:not(.featured) {
  min-height: 250px;
  border-radius: 12px;
}

.card p {
  color: var(--muted);
}

.card .salary {
  color: var(--salary);
}

.card-actions button + button {
  color: var(--muted);
  border: 1px solid var(--border);
  background: transparent;
}

.card-actions button + button:hover {
  color: var(--text);
  background: var(--panel-strong);
}
.match-detail {
    padding-top: 14px;
    border-top: 1px solid var(--border);
}

.match-detail summary {
    cursor: pointer;
    color: #aebcff;
    font-weight: 600;
}

.match-detail-body {
    padding-top: 14px;
}
</style>
