<script setup>
import { ref, computed } from 'vue'
import { t, loadAgents, modelGroups } from '../store.js'
import { post, patch } from '../api.js'

const props = defineProps({
  agent: { type: Object, default: null }
})
const emit = defineEmits(['saved', 'cancel'])

const TOOL_OPTS = ['web_search', 'knowledge_search']
// Model options come from the configured providers (grouped by provider).
const modelOpts = computed(() => {
  const out = []
  for (const g of modelGroups.value) {
    for (const m of g.models) out.push({ name: m.name, group: g.name })
  }
  return out
})

const saving = ref(false)
const errMsg = ref('')
const editingId = ref(props.agent ? props.agent.id : null)

const form = ref(emptyForm())
function emptyForm() {
  return {
    name: '', display_name: '', description: '',
    system_prompt: '', tools: ['web_search', 'knowledge_search'],
    model: modelOpts.value[0]?.name || 'deepseek-flash', thinking: true, reasoning_effort: 'high', temperature: 0.7
  }
}
if (props.agent) {
  form.value = {
    name: props.agent.name, display_name: props.agent.display_name, description: props.agent.description,
    system_prompt: props.agent.system_prompt,
    tools: Array.isArray(props.agent.tools) ? props.agent.tools : safeJson(props.agent.tools),
    model: props.agent.model, thinking: !!props.agent.thinking, reasoning_effort: props.agent.reasoning_effort,
    temperature: props.agent.temperature
  }
}

function safeJson(v) {
  try { const d = JSON.parse(v); return Array.isArray(d) ? d : [] } catch { return [] }
}

function toggleTool(name) {
  const s = new Set(form.value.tools)
  if (s.has(name)) s.delete(name); else s.add(name)
  form.value.tools = [...s]
}

async function save() {
  if (!form.value.name.trim() || !form.value.display_name.trim()) {
    errMsg.value = t('nameRequired')
    return
  }
  saving.value = true
  errMsg.value = ''
  try {
    if (editingId.value) {
      await patch('/agents/' + editingId.value, form.value)
    } else {
      const r = await post('/agents', form.value)
      if (!r) { errMsg.value = t('nameTaken'); saving.value = false; return }
    }
    await loadAgents()
    emit('saved')
  } catch (e) {
    errMsg.value = e.message || 'Error'
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <form class="agent-form" @submit.prevent="save">
    <div class="form-grid">
      <div class="field">
        <label>{{ t('agentName') }} <span v-if="!editingId" class="req">*</span></label>
        <input v-model="form.name" :disabled="!!editingId" :placeholder="t('agentNamePh')" maxlength="50" />
      </div>
      <div class="field">
        <label>{{ t('displayName') }} <span class="req">*</span></label>
        <input v-model="form.display_name" maxlength="50" />
      </div>
      <div class="field span2">
        <label>{{ t('agentDesc') }}</label>
        <input v-model="form.description" maxlength="300" />
      </div>
      <div class="field span2">
        <label>{{ t('sysPrompt') }}</label>
        <textarea v-model="form.system_prompt" rows="4"></textarea>
      </div>
      <div class="field">
        <label>{{ t('model') }}</label>
        <select v-model="form.model">
          <optgroup v-for="g in modelGroups" :key="g.id" :label="g.name">
            <option v-for="m in g.models" :key="m.name" :value="m.name">{{ m.name }}</option>
          </optgroup>
        </select>
      </div>
      <div class="field">
        <label>{{ t('reasoningEffort') }}</label>
        <select v-model="form.reasoning_effort">
          <option value="low">{{ t('effortLow') }}</option>
          <option value="high">{{ t('effortHigh') }}</option>
          <option value="max">{{ t('effortMax') }}</option>
        </select>
      </div>
      <div class="field">
        <label>{{ t('temperature') }}</label>
        <input v-model.number="form.temperature" type="number" min="0" max="2" step="0.1" />
      </div>
      <div class="field">
        <label>{{ t('thinkingMode') }}</label>
        <div class="toggle-track" :class="{ on: form.thinking }" @click="form.thinking = !form.thinking"><div class="toggle-knob"></div></div>
      </div>
      <div class="field span2">
        <label>{{ t('tools') }}</label>
        <div class="tool-checks">
          <label v-for="tl in TOOL_OPTS" :key="tl" class="tool-check">
            <input type="checkbox" :checked="form.tools.includes(tl)" @change="toggleTool(tl)" />
            <span>{{ tl }}</span>
          </label>
        </div>
      </div>
    </div>
    <div v-if="errMsg" class="err">{{ errMsg }}</div>
    <div class="form-actions">
      <button class="btn primary" type="submit" :disabled="saving">{{ saving ? '…' : t('save') }}</button>
      <button class="btn" type="button" @click="emit('cancel')">{{ t('cancel') }}</button>
    </div>
  </form>
</template>

<style scoped>
.agent-form { border-radius: var(--radius-lg); padding: 1.2rem; background: var(--surface); }
.form-grid { display: grid; grid-template-columns: 1fr 1fr; gap: .9rem; }
.field { display: flex; flex-direction: column; gap: .3rem; }
.field.span2 { grid-column: 1 / -1; }
.field label { font-size: 12.5px; color: var(--text-secondary); }
.field .req { color: var(--danger); }
.field input, .field textarea, .field select {
  padding: .5rem .6rem; border-radius: 8px; border: 1px solid var(--border-strong);
  background: var(--bg); color: var(--text); font-size: 13px; font-family: var(--font); outline: none;
}
.field input:focus, .field textarea:focus, .field select:focus { border-color: var(--accent); }
.field textarea { resize: vertical; line-height: 1.5; }
.toggle-track { width: 38px; height: 22px; border-radius: 12px; background: var(--border); position: relative; cursor: pointer; transition: background .2s; }
.toggle-track.on { background: var(--accent); }
.toggle-knob { position: absolute; top: 2px; left: 2px; width: 18px; height: 18px; border-radius: 50%; background: #fff; transition: left .2s var(--ease); }
.toggle-track.on .toggle-knob { left: 18px; }
.tool-checks { display: flex; gap: 1rem; flex-wrap: wrap; }
.tool-check { display: flex; align-items: center; gap: .4rem; font-size: 13px; color: var(--text-secondary); cursor: pointer; }
.tool-check input { accent-color: var(--accent); }
.form-actions { display: flex; gap: .5rem; margin-top: 1rem; }
.err { color: var(--danger); font-size: 12.5px; margin-top: .6rem; }
</style>