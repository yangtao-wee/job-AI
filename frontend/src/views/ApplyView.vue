<template>
  <section class="apply-page">
    <header class="page-head apply-head">
      <div>
        <p class="page-kicker">求职进度跟踪</p>
        <h2>投递管理</h2>
      </div>

      <button
        class="ghost-button"
        :disabled="busy || saving"
        @click="load"
      >
        {{ busy ? '刷新中...' : '刷新列表' }}
      </button>
    </header>

    <div class="apply-content">
      <section class="stats-grid">
        <article class="stat-card">
          <span>全部岗位</span>
          <strong>{{ stats.all }}</strong>
        </article>

        <article class="stat-card">
          <span>待投递</span>
          <strong>{{ stats.pending }}</strong>
        </article>

        <article class="stat-card">
          <span>已投递</span>
          <strong>{{ stats.applied }}</strong>
        </article>

        <article class="stat-card">
          <span>面试中</span>
          <strong class="highlight">{{ stats.interviewing }}</strong>
        </article>
      </section>

      <p v-if="saving || msg" class="notice" role="status">
        {{ saving ? '正在保存修改...' : msg }}
      </p>

      <div v-if="busy" class="empty-state">
        <span class="empty-icon">↻</span>
        <strong>正在读取投递记录</strong>
      </div>

      <div v-else-if="err" class="empty-state error-state">
        <span class="empty-icon">!</span>
        <strong>读取失败</strong>
        <p>{{ err }}</p>
        <button class="ghost-button" @click="load">重新读取</button>
      </div>

      <div v-else-if="!rows.length" class="empty-state">
        <span class="empty-icon">➤</span>
        <strong>还没有投递记录</strong>
        <p>请在岗位分析报告中点击“加入投递管理”。</p>
      </div>

      <div v-else class="application-list">
        <article
          v-for="item in rows"
          :key="item.id"
          class="application-card"
        >
          <header class="card-head">
            <div>
              <span class="application-id">投递记录 #{{ item.id }}</span>
              <h3>{{ item.title }}</h3>
              <p>{{ item.company }}</p>
            </div>

            <span
              class="status-tag"
              :class="statusClass(item.status)"
            >
              {{ item.status }}
            </span>
          </header>

          <div class="time-info">
            <span>创建于 {{ formatDate(item.created_at) }}</span>
            <span>更新于 {{ formatDate(item.updated_at) }}</span>
          </div>

          <div class="editor-grid">
            <div class="field">
              <label :for="'status-' + item.id">当前进度</label>
              <select
                :id="'status-' + item.id"
                v-model="item.status"
                :disabled="saving"
              >
                <option>待投递</option>
                <option>已投递</option>
                <option>面试中</option>
                <option>已结束</option>
              </select>
            </div>

            <div class="field note-field">
              <label :for="'note-' + item.id">跟进备注</label>
              <textarea
                :id="'note-' + item.id"
                v-model="item.note"
                :disabled="saving"
                maxlength="2000"
                rows="4"
                placeholder="记录投递时间、沟通结果、面试安排等信息"
              ></textarea>
              <span class="note-count">
                {{ item.note?.length || 0 }} / 2000
              </span>
            </div>
          </div>

          <footer class="card-footer">
            <span class="save-tip">修改状态或备注后记得保存</span>
            <button
              class="save-button"
              :disabled="saving"
              @click="save(item)"
            >
              {{ saving ? '保存中...' : '保存修改' }}
            </button>
          </footer>
        </article>
      </div>
    </div>
  </section>
</template>

<script setup>
import { computed, ref, onMounted } from 'vue'
import { listApply,updateApply } from '../api/apply.js'
const rows = ref([])
const stats = computed(() => ({
  all: rows.value.length,
  pending: rows.value.filter(item => item.status === '待投递').length,
  applied: rows.value.filter(item => item.status === '已投递').length,
  interviewing: rows.value.filter(item => item.status === '面试中').length
}))
const busy = ref(false)
const err = ref('')
async function load() {
  busy.value = true
  err.value = ''
  try {
    rows.value = (await listApply()).data
  } catch {
    err.value = '读取失败，请点击刷新列表重试'
  } finally {
    busy.value = false
  }
}
const saving = ref(false)
const msg = ref('')
async function save(item) {
  saving.value = true
  msg.value = ''
  try {
    await updateApply(item.id, { status: item.status, note: item.note })
    msg.value = '保存成功'
  } catch {
    msg.value = '保存失败，修改尚未确认保存，请重试'
  } finally {
    saving.value = false
  }
}

function statusClass(status) {
  const classes = {
    待投递: 'status-pending',
    已投递: 'status-applied',
    面试中: 'status-interview',
    已结束: 'status-ended'
  }
  return classes[status] ?? 'status-pending'
}

function formatDate(value) {
  return value ? new Date(value).toLocaleString() : '暂无时间'
}

onMounted(load)
</script>

<style scoped>
.apply-page {
  width: 100%;
}

.apply-content {
  width: min(100%, 1120px);
}

.apply-head {
  width: min(100%, 1120px);
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 24px;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 14px;
  margin: 30px 0 24px;
}

.stat-card {
  display: flex;
  min-height: 104px;
  padding: 20px;
  flex-direction: column;
  justify-content: space-between;
  border: 1px solid var(--border);
  border-radius: 16px;
  background: var(--panel);
}

.stat-card span {
  color: var(--muted);
  font-size: 0.86rem;
}

.stat-card strong {
  color: var(--text);
  font-size: 1.8rem;
}

.stat-card .highlight {
  color: #8b7aff;
}

.ghost-button,
.save-button {
  width: auto;
  min-width: 112px;
  margin: 0;
  padding: 11px 18px;
  border-radius: 10px;
}

.ghost-button {
  color: #9db1d6;
  border: 1px solid var(--border);
  background: transparent;
}

.ghost-button:hover:not(:disabled) {
  color: var(--text);
  border-color: var(--primary);
  background: rgba(76, 141, 255, 0.08);
}

.notice {
  margin: 0 0 18px;
  padding: 13px 16px;
  color: #67dfb8;
  border: 1px solid rgba(45, 212, 167, 0.25);
  border-radius: 12px;
  background: rgba(45, 212, 167, 0.08);
}

.application-list {
  display: grid;
  gap: 18px;
}

.application-card {
  overflow: hidden;
  border: 1px solid var(--border);
  border-radius: 18px;
  background: var(--panel);
  transition:
    transform 0.2s ease,
    border-color 0.2s ease;
}

.application-card:hover {
  border-color: rgba(76, 141, 255, 0.38);
  transform: translateY(-2px);
}

.card-head {
  display: flex;
  padding: 24px 26px 18px;
  align-items: flex-start;
  justify-content: space-between;
  gap: 20px;
}

.application-id {
  color: var(--primary);
  font-size: 0.75rem;
  font-weight: 700;
  letter-spacing: 0.06em;
}

.card-head h3 {
  margin: 7px 0 5px;
  color: var(--text);
  font-size: 1.25rem;
}

.card-head p {
  margin: 0;
  color: var(--muted);
}

.status-tag {
  flex: 0 0 auto;
  padding: 7px 13px;
  font-size: 0.8rem;
  font-weight: 700;
  border: 1px solid;
  border-radius: 999px;
}

.status-pending {
  color: #f2b84b;
  border-color: rgba(242, 184, 75, 0.3);
  background: rgba(242, 184, 75, 0.09);
}

.status-applied {
  color: #79a7ff;
  border-color: rgba(76, 141, 255, 0.3);
  background: rgba(76, 141, 255, 0.09);
}

.status-interview {
  color: #b898ff;
  border-color: rgba(139, 92, 246, 0.3);
  background: rgba(139, 92, 246, 0.09);
}

.status-ended {
  color: #8997ad;
  border-color: var(--border);
  background: rgba(137, 151, 173, 0.07);
}

.time-info {
  display: flex;
  gap: 22px;
  padding: 0 26px 18px;
  color: var(--muted);
  font-size: 0.78rem;
}

.editor-grid {
  display: grid;
  grid-template-columns: 220px minmax(0, 1fr);
  gap: 18px;
  padding: 22px 26px;
  border-top: 1px solid var(--border);
  background: rgba(5, 12, 24, 0.22);
}

.field {
  display: flex;
  min-width: 0;
  flex-direction: column;
  gap: 9px;
}

.field label {
  color: var(--text);
  font-size: 0.86rem;
  font-weight: 600;
}

.field select,
.field textarea {
  width: 100%;
  margin: 0;
  color: var(--text);
  border: 1px solid var(--border);
  border-radius: 11px;
  background: var(--panel-soft, #0b1423);
}

.field select {
  height: 50px;
}

.field textarea {
  min-height: 105px;
  resize: vertical;
  line-height: 1.65;
}

.field select:focus,
.field textarea:focus {
  border-color: var(--primary);
  box-shadow: 0 0 0 3px rgba(76, 141, 255, 0.12);
}

.note-field {
  position: relative;
}

.note-count {
  align-self: flex-end;
  color: var(--muted);
  font-size: 0.74rem;
}

.card-footer {
  display: flex;
  padding: 16px 26px 22px;
  align-items: center;
  justify-content: space-between;
  gap: 20px;
}

.save-tip {
  color: var(--muted);
  font-size: 0.78rem;
}

.save-button {
  color: #07101e;
  font-weight: 700;
  border: 0;
  background: linear-gradient(135deg, var(--primary), var(--accent-2));
}

.empty-state {
  display: grid;
  min-height: 280px;
  padding: 30px;
  place-items: center;
  align-content: center;
  gap: 10px;
  color: var(--muted);
  text-align: center;
  border: 1px dashed var(--border);
  border-radius: 18px;
}

.empty-state strong {
  color: var(--text);
}

.empty-state p {
  margin: 0;
}

.empty-icon {
  display: grid;
  width: 52px;
  height: 52px;
  place-items: center;
  color: var(--primary);
  font-size: 1.35rem;
  border: 1px solid rgba(76, 141, 255, 0.25);
  border-radius: 15px;
  background: rgba(76, 141, 255, 0.1);
}

.error-state {
  color: #ff8fa3;
  border-color: rgba(255, 91, 117, 0.25);
}

@media (max-width: 900px) {
  .stats-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .editor-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 600px) {
  .apply-head,
  .card-head,
  .card-footer {
    align-items: stretch;
    flex-direction: column;
  }

  .stats-grid {
    grid-template-columns: 1fr;
  }

  .time-info {
    flex-direction: column;
    gap: 5px;
  }

  .save-button,
  .ghost-button {
    width: 100%;
  }
}
</style>