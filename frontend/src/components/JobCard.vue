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
<button :disabled="matching" @click="emit('match')">{{ matching?'匹配中...' : '开始匹配' }}</button>
<!-- 【框架提供】，向父页面发出名为match的消息 -->
</div>

</template>

<script setup>
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
    matching:Boolean
    // Boolean：【语言固定】，只有true或false。
})
const emit = defineEmits(['match'])
</script>

<style scoped>
.card{
    border:1px solid #ddd;
    padding: 20px;
    margin-top: 20px;
    width: 300px;
    }
</style>