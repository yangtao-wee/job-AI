<template>
  <section class="rag-page">
    <header class="page-head">
      <div>
        <p class="page-kicker">求职知识库</p>
        <h2>知识问答</h2>
      </div>
    </header>

    <div class="qa-shell">
      <div class="qa-composer">
        <textarea
          v-model="q"
          placeholder="请输入求职问题，例如：项目经历应该怎么写？"
          @keydown.ctrl.enter.prevent="ask"
        ></textarea>

        <button
          class="qa-submit"
          :disabled="loading || !q.trim()"
          @click="ask"
        >
          {{ loading ? '检索中...' : '提问' }}
        </button>
      </div>

      <p class="keyboard-hint">
        按 Ctrl + Enter 也可以发送
      </p>

      <div class="question-chips">
        <button
          v-for="question in suggestions"
          :key="question"
          class="question-chip"
          @click="chooseQuestion(question)"
        >
          {{ question }}
        </button>
      </div>

      <p
        v-if="err"
        class="qa-error"
      >
        {{ err }}
      </p>

      <div
        v-if="res"
        class="thread"
      >
        <article class="message user-message">
          <span class="avatar user-avatar">我</span>

          <div class="message-content">
            <span class="message-name">你的问题</span>
            <p>{{ lastQuestion }}</p>
          </div>
        </article>

        <article class="message ai-message">
          <span class="avatar ai-avatar">AI</span>

          <div class="message-content">
            <div class="answer-heading">
              <span class="message-name">知识库回答</span>

              <span
                class="answer-status"
                :class="{ enough: res.enough }"
              >
                {{
                  res.enough
                    ? '资料充分'
                    : '资料有限'
                }}
              </span>
            </div>

            <p class="answer-text">
              {{ res.answer }}
            </p>

            <details
              v-if="res.sources?.length"
              class="sources"
            >
              <summary>
                查看资料来源（{{ res.sources.length }}）
              </summary>

              <ol>
                <li
                  v-for="source in res.sources"
                  :key="source.text"
                >
                  <p>{{ source.text }}</p>

                  <span>
                    相似度：
                    {{
                      Number(source.score ?? 0)
                        .toFixed(2)
                    }}
                  </span>
                </li>
              </ol>
            </details>
          </div>
        </article>
      </div>

      <div
        v-else
        class="qa-empty"
      >
        <span class="empty-icon">?</span>
        <h3>从一个求职问题开始</h3>

        <p>
          系统会先检索知识库资料，再根据找到的内容生成回答。
        </p>
      </div>
    </div>
  </section>
</template>

<script setup>
import {ref} from 'vue'
import { askRag } from '../api/rag';
const q=ref('')
const lastQuestion = ref('')

const suggestions = [
    '如何写好项目经历？',
    '面试常见问题有哪些？',
    '薪资应该怎么谈？',
    '转行应该如何准备简历？'
]

function chooseQuestion(question) {
    q.value = question
}
const loading=ref(false)
const res=ref(null)
const err=ref('')
async function ask() {
    const question = q.value.trim()

    if (!question || loading.value) return

    lastQuestion.value = question
    loading.value=true
    res.value=null
    err.value=''
    try{
        const response = await askRag(question)
        res.value=response.data
    }catch(error){
        err.value=error.response?.data?.detail ?? '回答失败'
    }finally{
        loading.value=false
    }
}
</script>

<style scoped>
.qa-shell {
  max-width: 780px;
}

.qa-composer {
  position: relative;
}

.qa-composer textarea {
  min-height: 140px;
  padding: 18px 130px 58px 18px;
  border-radius: 18px;
  background: var(--panel);
  line-height: 1.7;
}

.qa-submit {
  position: absolute;
  right: 12px;
  bottom: 12px;
  min-width: 96px;
}

.keyboard-hint {
  margin: 8px 4px 0;
  color: #5a6577;
  font-size: 11px;
}

.question-chips {
  margin: 20px 0 36px;
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.question-chips .question-chip {
  padding: 8px 13px;
  color: var(--muted);
  border: 1px solid var(--border);
  border-radius: 999px;
  background: var(--panel);
  font-size: 12px;
  font-weight: 400;
}

.question-chips .question-chip:hover {
  color: var(--text);
  border-color: var(--primary);
  background: rgba(76, 141, 255, 0.07);
  filter: none;
}

.qa-error {
  margin-bottom: 20px;
  padding: 12px 15px;
  color: #f0687a;
  border: 1px solid rgba(240, 104, 122, 0.3);
  border-radius: 10px;
  background: rgba(240, 104, 122, 0.07);
}

.thread {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.message {
  margin: 0;
  padding: 0;
  display: flex;
  align-items: flex-start;
  gap: 12px;
  border: 0;
  background: transparent;
  box-shadow: none;
}

.avatar {
  width: 34px;
  height: 34px;
  flex: 0 0 34px;
  display: grid;
  place-items: center;
  border-radius: 10px;
  font-size: 11px;
  font-weight: 700;
}

.user-avatar {
  color: #0a0d14;
  background:
    linear-gradient(
      135deg,
      var(--primary),
      var(--accent-2)
    );
}

.ai-avatar {
  color: var(--primary);
  border: 1px solid
    rgba(76, 141, 255, 0.25);
  background: var(--panel-strong);
}

.message-content {
  min-width: 0;
  flex: 1;
  padding: 15px 18px;
  border: 1px solid var(--border);
  border-radius: 14px;
  background: var(--panel);
}

.user-message .message-content {
  background: var(--panel-strong);
}

.message-name {
  display: block;
  margin-bottom: 7px;
  color: var(--muted);
  font-size: 11px;
}

.message-content p {
  margin: 0;
  color: var(--text);
  line-height: 1.75;
}

.answer-heading {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
}

.answer-status {
  padding: 4px 9px;
  color: var(--salary);
  border: 1px solid rgba(242, 184, 75, 0.25);
  border-radius: 999px;
  background: rgba(242, 184, 75, 0.07);
  font-size: 10px;
}

.answer-status.enough {
  color: #34d399;
  border-color: rgba(52, 211, 153, 0.25);
  background: rgba(52, 211, 153, 0.07);
}

.sources {
  margin-top: 18px;
  padding-top: 14px;
  border-top: 1px solid var(--border);
}

.sources summary {
  color: var(--primary);
  cursor: pointer;
  font-size: 12px;
}

.sources ol {
  margin: 14px 0 0;
  padding-left: 22px;
}

.sources li {
  margin-bottom: 14px;
}

.sources li p {
  color: var(--muted);
  font-size: 13px;
}

.sources li span {
  color: #5a6577;
  font-family:
    "JetBrains Mono",
    Consolas,
    monospace;
  font-size: 10px;
}

.qa-empty {
  min-height: 260px;
  padding: 32px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  border: 1px dashed var(--border);
  border-radius: 18px;
  text-align: center;
}

.empty-icon {
  width: 48px;
  height: 48px;
  margin-bottom: 14px;
  display: grid;
  place-items: center;
  color: var(--primary);
  border: 1px solid
    rgba(76, 141, 255, 0.25);
  border-radius: 14px;
  background: rgba(76, 141, 255, 0.07);
  font-size: 20px;
  font-weight: 700;
}

.qa-empty h3 {
  margin: 0 0 8px;
  color: var(--text);
  font-size: 16px;
}

.qa-empty p {
  max-width: 430px;
  margin: 0;
  color: var(--muted);
  font-size: 13px;
}

@media (max-width: 600px) {
  .qa-composer textarea {
    padding-right: 18px;
  }

  .qa-submit {
    position: static;
    width: 100%;
    margin-top: 10px;
  }

  .message-content {
    padding: 13px;
  }
}
</style>