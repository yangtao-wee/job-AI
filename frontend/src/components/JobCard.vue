<template>
<div class="card">
<h3>{{ title }}</h3>
<p>薪资：{{ salary }}</p>
<p v-if="currentScore !== undefined">已完成维度合计：{{ currentScore }}/{{ currentMaxScore }}</p>
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
<button :disabled="matching" @click="emit('match')">{{ matching?'匹配中...' : '开始匹配' }}</button>

<button :disabled="analyzing"  @click="emit('analyze')">
    {{ analyzing ? '分析中...' : '分析岗位' }}
</button>
<!-- 【框架提供】，向父页面发出名为match的消息 -->
</div>

</template>

<script setup>
// defineProps() 是 Vue 3 提供的固定语法；这个子组件允许父组件传这些数据进来，并且规定每个数据应该是什么类型。括号里面的 prop 名称是你自己定义的，类型 String/Number/Array/Boolean/Object 是 JavaScript 提供的。
defineProps({
    title:String,
    salary:String,
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
    analyzing:Boolean,
    expScore:Number,
    expHits:Array,
    expMiss:Array,
    roleScore:Number,
    roleNote:String,
    prefScore:Number,
    prefNotes:Array
    // Boolean：【语言固定】，只有true或false。
})
const emit = defineEmits(['match','analyze'])
// 【框架提供】，登记组件允许发送的事件。

</script>

<style scoped>
.card{
    border:1px solid #ddd;
    padding: 20px;
    margin-top: 20px;
    width: 300px;
    }
</style>