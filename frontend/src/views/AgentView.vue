<template>
  <section class="agent-page">
    <header class="page-head">
      <div>
        <p class="page-kicker">AI 求职智能体</p>
        <h2>AI 助手</h2>
      </div>
    </header>

    <div class="assistant-shell">
      <div class="conversation-area">
        <div
          v-if="!lastGoal"
          class="assistant-empty"
        >
          <span class="assistant-glyph">
            <svg viewBox="0 0 24 24">
              <path
                d="m12 3 2 5 5 2-5 2-2 5-2-5-5-2 5-2 2-5Z"
              />
              <path
                d="m19 16 1 2 2 1-2 1-1 2-1-2-2-1 2-1 1-2Z"
              />
            </svg>
          </span>

          <h3>有什么可以帮你？</h3>

          <p>
            我可以帮你分析简历、理解岗位要求、
            规划投递策略和整理求职行动。
          </p>
        </div>

        <div
          v-else
          class="assistant-thread"
        >
          <article class="agent-message user-message">
            <span class="message-avatar user-avatar">
              我
            </span>

            <div class="message-body">
              <span class="message-role">你的目标</span>
              <p>{{ lastGoal }}</p>
            </div>
          </article>

          <article class="agent-message">
            <span class="message-avatar agent-avatar">
              AI
            </span>

            <div
              class="message-body"
              :class="{ error: err }"
            >
              <span class="message-role">
                AI 求职助手
              </span>

              <p v-if="loading" class="thinking">
                正在分析你的目标
                <span></span>
                <span></span>
                <span></span>
              </p>

              <p v-else-if="err">
                {{ err }}
              </p>

              <p v-else class="answer">
                {{ answer }}
              </p>
            </div>
          </article>
        </div>
      </div>

      <form
        class="assistant-input"
        @submit.prevent="run"
      >
        <input
          v-model="goal"
          type="text"
          placeholder="输入你的求职目标..."
          autocomplete="off"
        >

        <button
          class="send-button"
          type="submit"
          :disabled="loading || !goal.trim()"
          aria-label="发送求职目标"
        >
          <svg viewBox="0 0 24 24">
            <path d="M22 2 11 13" />
            <path d="m22 2-7 20-4-9-9-4 20-7Z" />
          </svg>
        </button>
      </form>
    </div>
  </section>
</template>

<script setup>
import { ref } from 'vue'
import { askAgent } from '../api/agent'

const goal = ref('')
const lastGoal = ref('')
const answer = ref('')
const err = ref('')
const loading = ref(false)

async function run() {
    const text = goal.value.trim()

    if (!text || loading.value) return

    lastGoal.value = text
    answer.value = ''
    err.value = ''
    loading.value = true

    try {
        const response = await askAgent(text)
        answer.value = response.data.answer
    } catch (error) {
        err.value =
            error.response?.data?.detail
            ?? '执行失败，请稍后重试'
    } finally {
        loading.value = false
    }
}
</script>

<style scoped>
.agent-page {
  height: calc(100vh - 48px);
}

.assistant-shell {
  max-width: 900px;
  height: calc(100vh - 165px);
  display: flex;
  flex-direction: column;
}

.conversation-area {
  min-height: 0;
  flex: 1;
  overflow-y: auto;
}

.assistant-empty {
  height: 100%;
  min-height: 360px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  text-align: center;
}

.assistant-glyph {
  width: 68px;
  height: 68px;
  margin-bottom: 20px;
  display: grid;
  place-items: center;
  border-radius: 20px;
  background:
    linear-gradient(
      135deg,
      var(--primary),
      var(--accent-2)
    );
  box-shadow:
    0 18px 35px -14px
    rgba(76, 141, 255, 0.55);
}

.assistant-glyph svg {
  width: 30px;
  height: 30px;
  fill: none;
  stroke: #0a0d14;
  stroke-width: 1.8;
  stroke-linecap: round;
  stroke-linejoin: round;
}

.assistant-empty h3 {
  margin: 0 0 10px;
  color: var(--text);
  font-size: 19px;
}

.assistant-empty p {
  max-width: 440px;
  margin: 0;
  color: var(--muted);
  font-size: 13px;
  line-height: 1.8;
}

.assistant-thread {
  padding: 20px 4px 36px;
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.agent-message {
  margin: 0;
  padding: 0;
  display: flex;
  align-items: flex-start;
  gap: 12px;
  border: 0;
  background: transparent;
  box-shadow: none;
}

.message-avatar {
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

.agent-avatar {
  color: var(--primary);
  border: 1px solid
    rgba(76, 141, 255, 0.28);
  background: var(--panel-strong);
}

.message-body {
  min-width: 0;
  max-width: 760px;
  padding: 15px 18px;
  border: 1px solid var(--border);
  border-radius: 14px;
  background: var(--panel);
}

.user-message .message-body {
  background: var(--panel-strong);
}

.message-body.error {
  border-color:
    rgba(240, 104, 122, 0.3);
  background:
    rgba(240, 104, 122, 0.06);
}

.message-role {
  display: block;
  margin-bottom: 7px;
  color: var(--muted);
  font-size: 11px;
}

.message-body p {
  margin: 0;
  color: var(--text);
  line-height: 1.75;
}

.message-body .answer {
  white-space: pre-wrap;
}

.thinking {
  display: flex;
  align-items: center;
  gap: 5px;
}

.thinking span {
  width: 5px;
  height: 5px;
  border-radius: 50%;
  background: var(--primary);
  animation: thinking 1.2s infinite;
}

.thinking span:nth-child(2) {
  animation-delay: 0.15s;
}

.thinking span:nth-child(3) {
  animation-delay: 0.3s;
}

@keyframes thinking {
  0%,
  60%,
  100% {
    opacity: 0.3;
    transform: translateY(0);
  }

  30% {
    opacity: 1;
    transform: translateY(-3px);
  }
}

.assistant-input {
  width: 100%;
  padding: 6px 6px 6px 19px;
  display: flex;
  align-items: center;
  gap: 10px;
  border: 1px solid var(--border);
  border-radius: 999px;
  background: var(--panel);
  box-shadow:
    0 16px 38px
    rgba(0, 0, 0, 0.22);
}

.assistant-input:focus-within {
  border-color: var(--primary);
}

.assistant-input input {
  min-width: 0;
  min-height: 42px;
  flex: 1;
  padding: 0;
  border: 0;
  background: transparent;
  box-shadow: none;
}

.assistant-input input:focus {
  border: 0;
}

.assistant-input .send-button {
  width: 42px;
  height: 42px;
  flex: 0 0 42px;
  padding: 0;
  display: grid;
  place-items: center;
  border-radius: 50%;
}

.send-button svg {
  width: 17px;
  height: 17px;
  fill: none;
  stroke: #0a0d14;
  stroke-width: 2;
  stroke-linecap: round;
  stroke-linejoin: round;
}

@media (max-width: 600px) {
  .agent-page,
  .assistant-shell {
    height: auto;
    min-height: calc(100vh - 150px);
  }

  .assistant-empty {
    min-height: 380px;
  }

  .message-body {
    padding: 13px;
  }
}
</style>