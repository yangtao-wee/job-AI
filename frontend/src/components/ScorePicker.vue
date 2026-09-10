<template>
  <div class="pick" ref="root">
    <input
      class="pin"
      type="number"
      :min="min"
      max="100"
      :value="modelValue"
      :disabled="disabled"
      @input="emit('update:modelValue', clamp($event.target.value))"
      @focus="open = true"
    >
    <button class="arrow" type="button" :disabled="disabled" @click="open = !open">
      <svg viewBox="0 0 12 12" width="10" height="10">
        <path d="M2 4.5 6 8.5 10 4.5" fill="none" stroke="currentColor" stroke-width="1.6"
              stroke-linecap="round" stroke-linejoin="round" />
      </svg>
    </button>

    <ul v-if="open" class="menu">
      <li
        v-for="o in OPTIONS"
        :key="o.value"
        :class="{ on: o.value === modelValue }"
        @mousedown.prevent="choose(o.value)"
      >
        <b>{{ o.value }}</b>
        <span>{{ o.note }}</span>
      </li>
    </ul>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'

const props = defineProps({
  modelValue: { type: Number, default: 0 },
  disabled: { type: Boolean, default: false },
  min: { type: Number, default: 0 },
})
const emit = defineEmits(['update:modelValue'])

const ALL = [
  { value: 80, note: '方向高度吻合' },
  { value: 70, note: '比较对口' },
  { value: 60, note: '值得看一眼' },
  { value: 40, note: '偏弱' },
  { value: 0, note: '全部' },
]
const OPTIONS = computed(() => ALL.filter(o => o.value >= props.min))

const open = ref(false)
const root = ref(null)

function clamp(raw) {
  const n = Number(raw)
  if (Number.isNaN(n)) return 0
  return Math.min(100, Math.max(props.min, n))
}

function choose(value) {
  emit('update:modelValue', value)
  open.value = false
}

function onOutside(e) {
  if (root.value && !root.value.contains(e.target)) open.value = false
}

onMounted(() => document.addEventListener('mousedown', onOutside))
onUnmounted(() => document.removeEventListener('mousedown', onOutside))
</script>

<style scoped>
.pick { position: relative; display: inline-block; width: 108px; }

.pin {
  width: 100%;
  box-sizing: border-box;
  background: #0f1425;
  border: 1px solid #2a3348;
  border-radius: 7px;
  padding: 7px 26px 7px 10px;
  font-size: 13px;
  color: #e8ecf5;
  outline: none;
}
.pin:focus { border-color: #35c48a; }
.pin:disabled { opacity: .5; }
/* 去掉数字框自带的上下箭头，右边留给我们自己的箭头 */
.pin::-webkit-outer-spin-button,
.pin::-webkit-inner-spin-button { -webkit-appearance: none; margin: 0; }
.pin { -moz-appearance: textfield; }

.arrow {
  position: absolute;
  top: 50%;
  right: 6px;
  transform: translateY(-50%);
  display: grid;
  place-items: center;
  width: 18px;
  height: 18px;
  padding: 0;
  border: 0;
  border-radius: 4px;
  background: transparent;
  color: #6b7590;
  cursor: pointer;
}
.arrow:hover:not(:disabled) { color: #35c48a; }
.arrow:disabled { opacity: .4; cursor: default; }

.menu {
  position: absolute;
  z-index: 40;
  top: calc(100% + 6px);
  left: 0;
  width: 168px;
  margin: 0;
  padding: 4px;
  list-style: none;
  background: #131b2c;
  border: 1px solid #2a3348;
  border-radius: 9px;
  box-shadow: 0 12px 30px rgba(0, 0, 0, .45);
}
.menu li {
  display: flex;
  align-items: baseline;
  gap: 8px;
  padding: 7px 10px;
  border-radius: 6px;
  cursor: pointer;
}
.menu li:hover { background: #1c2740; }
.menu li.on { background: #122f24; }
.menu b {
  min-width: 22px;
  font-size: 13px;
  color: #e8ecf5;
  font-variant-numeric: tabular-nums;
}
.menu li.on b { color: #35c48a; }
.menu span { font-size: 11.5px; color: #7b88a6; }
</style>
