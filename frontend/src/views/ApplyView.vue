<template>
  <section>
    <h2>投递管理</h2>
    <button :disabled="busy || saving"  @click="load">刷新列表</button>
    <p role="status">{{ saving? '保存中...' : msg }}</p>
    <p v-if="busy">读取中...</p>
    <p v-else-if="err">{{ err }}</p>
    <p v-else-if="!rows.length">暂无投递记录，请从历史报告添加。</p>
    <ul v-else>
      <li v-for="item in rows" :key="item.id">
        {{ item.title }} · {{ item.company }} · {{ item.status }}
                <fieldset :disabled="saving">
          <legend>编辑投递记录</legend>
          <select v-model="item.status">
            <option>待投递</option>
            <option>已投递</option>
            <option>面试中</option>
            <option>已结束</option>
          </select>
          <textarea v-model="item.note" maxlength="2000" aria-label="备注"></textarea>
          <button @click="save(item)">保存</button>
        </fieldset>
      </li>
    </ul>
  </section>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { listApply,updateApply } from '../api/apply.js'
const rows = ref([])
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

onMounted(load)
</script>