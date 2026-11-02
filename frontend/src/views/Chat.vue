<template>
  <div class="chat-workspace" :class="{ 'has-messages': messages.length }">
    <Teleport to="#chat-history">
      <div class="history-heading"><span>对话</span><button class="history-manage" @click="batchDeleteMode = !batchDeleteMode">{{ batchDeleteMode ? '取消' : '管理' }}</button></div>
      <div v-if="batchDeleteMode" class="history-batch"><el-button type="danger" size="small" :disabled="!selectedSessions.length || sending" @click="deleteSelectedSessions">删除所选</el-button></div>
      <div v-for="session in sessions" :key="session.session_uid" class="history-row" :class="{ active: currentSessionId === session.session_uid }">
        <el-checkbox v-if="batchDeleteMode" v-model="selectedSessions" :value="session.session_uid" :aria-label="'选择对话：' + session.title" />
        <button class="history-title" :disabled="sending" @click="batchDeleteMode ? (selectedSessions.includes(session.session_uid) ? selectedSessions.splice(selectedSessions.indexOf(session.session_uid), 1) : selectedSessions.push(session.session_uid)) : loadSession(session)">{{ session.title || '新建对话' }}</button>
        <button v-if="!batchDeleteMode" class="icon-button history-delete" :disabled="sending" :aria-label="'删除对话：' + session.title" @click="deleteSession(session.session_uid)"><UiIcon name="close" :size="14" /></button>
      </div>
      <p v-if="!sessions.length" class="history-empty">暂无对话</p>
    </Teleport>
    <div class="chat-context-bar">
      <el-select v-model="selectedAssistant" clearable placeholder="选择助手" aria-label="选择助手" @change="onAssistantChange" :disabled="sending" class="context-select">
        <el-option v-for="item in assistants" :key="item.id" :label="item.name" :value="item.id" />
      </el-select>
      <el-select v-if="!selectedAssistant" v-model="selectedKB" clearable placeholder="选择知识库" aria-label="选择知识库" :disabled="sending" class="context-select">
        <el-option v-for="item in kbs" :key="item.id" :label="item.name" :value="item.id" />
      </el-select>
      <button class="icon-button" v-if="currentAssistant" @click="settingsOpen = true" title="对话设置" aria-label="对话设置"><UiIcon name="settings" /></button>
    </div>
    <div ref="messagesContainer" class="conversation-scroll">
      <div v-if="!messages.length" class="chat-empty"><p v-if="currentGreeting">{{ currentGreeting }}</p></div>
      <div v-else class="conversation-thread" role="log" aria-label="对话记录" aria-live="polite" :aria-busy="sending">
        <article v-for="(msg, index) in messages" :key="index" class="conversation-message" :class="msg.role">
          <span class="sr-only">{{ msg.role === 'user' ? '你' : msg.role === 'system' ? '提示' : '助手' }}</span>
          <div v-if="msg.content" class="conversation-content">{{ msg.content }}</div>
          <ExecutionTrace v-if="msg.trace" :trace="msg.trace" :live="msg.pending" />
          <details v-if="msg.sources?.length" class="conversation-sources"><summary>参考来源 · {{ msg.sources.length }}</summary><ul><li v-for="(source, sourceIndex) in msg.sources" :key="source.id || sourceIndex">{{ source.text }}<span v-if="Number.isFinite(source.score)" class="source-score">相关度 {{ source.score.toFixed(2) }}</span></li></ul></details>
        </article>
      </div>
    </div>
    <form class="composer-area" @submit.prevent="sendMessage">
      <div class="composer">
        <el-input v-model="inputQuery" type="textarea" :autosize="{ minRows: 1, maxRows: 7 }" resize="none" placeholder="输入问题" aria-label="输入问题" @keydown="onComposerKey" />
        <div class="composer-bottom"><button class="send-button" type="submit" :disabled="!inputQuery.trim() || sending" :aria-label="sending ? '正在生成回答' : '发送消息'"><span v-if="sending" class="quiet-spinner" /><UiIcon v-else name="arrow" /></button></div>
      </div>
      <p class="composer-hint">Enter 发送，Shift + Enter 换行</p>
    </form>
    <el-drawer v-model="settingsOpen" title="对话设置" size="360px"><div v-if="currentAssistant" class="conversation-settings">
        <div style="display: flex; justify-content: space-between; align-items: center;">
            <h3>{{ currentAssistant.name }}</h3>
            <el-button type="primary" size="small" @click="saveAssistantConfig" v-if="hasConfigChanges">保存</el-button>
        </div>
        <el-divider />
        
        <el-form label-position="top" size="small">
             <el-tabs v-model="configTab">
                 <el-tab-pane label="基础设置" name="basic">
                     <el-form-item label="系统提示词">
                         <el-input type="textarea" v-model="currentAssistant.system_prompt" :rows="4" @input="onConfigChange" />
                     </el-form-item>
                     <el-form-item label="温度系数">
                         <el-slider v-model="currentAssistant.temperature" :min="0" :max="1" :step="0.1" @input="onConfigChange" />
                     </el-form-item>
                 </el-tab-pane>
                 <el-tab-pane label="检索增强" name="rag">
                     <el-form-item label="召回数量">
                         <el-slider v-model="currentAssistant.rag_config.top_k" :min="1" :max="20" @input="onConfigChange" />
                     </el-form-item>
                     <el-form-item label="重排序">
                         <el-switch v-model="currentAssistant.rag_config.enable_rerank" @change="onConfigChange" />
                     </el-form-item>
                 </el-tab-pane>
                 <el-tab-pane label="版本管理" name="versions">
                     <div class="version-list">
                         <div v-for="ver in assistantVersions" :key="ver.version" class="version-item">
                             <span>{{ ver.version }}</span>
                             <el-button size="small" type="text" @click="restoreVersion(ver)">恢复</el-button>
                         </div>
                     </div>
                 </el-tab-pane>
             </el-tabs>
        </el-form>
        <el-button type="primary" plain size="small" style="width: 100%; margin-top: 10px;" @click="changeAssistant">切换助手</el-button>
      </div></el-drawer>
  </div>
</template>

<script setup>
import { reactive, ref, onMounted, nextTick, computed, watch } from 'vue'
import api from '../api'
import { streamChat } from '../api/chat'
import ExecutionTrace from '../components/ExecutionTrace.vue'
import UiIcon from '../components/UiIcon.vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useRoute } from 'vue-router'

const route = useRoute()
const settingsOpen = ref(false)
const sending = ref(false)
function onComposerKey(event) {
  if (event.key === 'Enter' && !event.shiftKey && !event.isComposing) { event.preventDefault(); sendMessage() }
}
const kbs = ref([])
const assistants = ref([])
const selectedKB = ref(null)
const selectedAssistant = ref(null)
const sessions = ref([])
const currentSessionId = ref(null)
const messages = ref([])
const inputQuery = ref('')
const messagesContainer = ref(null)

// Delete features
const batchDeleteMode = ref(false)
const selectedSessions = ref([])

const configTab = ref('basic')
const hasConfigChanges = ref(false)
const assistantVersions = ref([])

const onConfigChange = () => {
    hasConfigChanges.value = true
}

const saveAssistantConfig = async () => {
    try {
        // Increment version logic
        // Simple string increment: v1.0.0 -> v1.0.1
        // We need to fetch current version or assume
        let nextVer = 'v1.0.0'
        if (assistantVersions.value.length > 0) {
            const lastVer = assistantVersions.value[0].version
            const parts = lastVer.replace('v', '').split('.').map(Number)
            parts[2]++
            if (parts[2] >= 10) {
                parts[2] = 0
                parts[1]++
            }
            if (parts[1] >= 10) {
                parts[1] = 0
                parts[0]++
            }
            nextVer = `v${parts.join('.')}`
        }
        
        // Save current state as new version
        const payload = {
            ...currentAssistant.value,
            version: nextVer
        }
        
        await api.put(`/assistants/${currentAssistant.value.id}`, payload)
        await api.post(`/assistants/${currentAssistant.value.id}/versions`, {
            version: nextVer,
            config: payload
        })
        
        ElMessage.success(`已保存为 ${nextVer}`)
        hasConfigChanges.value = false
        fetchVersions()
    } catch (e) {
        ElMessage.error('保存失败')
    }
}

const fetchVersions = async () => {
    if (!currentAssistant.value) return
    try {
        const res = await api.get(`/assistants/${currentAssistant.value.id}/versions`)
        assistantVersions.value = res.data
    } catch (e) {
        // Ignore if endpoint not exists yet
    }
}

const restoreVersion = async (ver) => {
    try {
        await ElMessageBox.confirm(`确定恢复到 ${ver.version} 吗？`, '确认')
        // Apply config
        const config = ver.config
        // Update currentAssistant locally
        currentAssistant.value.system_prompt = config.system_prompt
        currentAssistant.value.temperature = config.temperature
        currentAssistant.value.rag_config = config.rag_config
        
        // Save to backend
        await api.put(`/assistants/${currentAssistant.value.id}`, config)
        ElMessage.success('已恢复')
        hasConfigChanges.value = false
    } catch (e) {
        if (e !== 'cancel') ElMessage.error('恢复失败')
    }
}

const changeAssistant = () => {
    settingsOpen.value = false
    selectedAssistant.value = null
    currentSessionId.value = null
    messages.value = []
    hasConfigChanges.value = false
}

const currentAssistant = computed(() => {
    if (selectedAssistant.value) {
        return assistants.value.find(a => a.id === selectedAssistant.value)
    }
    return null
})

const currentGreeting = computed(() => {
    if (selectedAssistant.value) {
        const assistant = assistants.value.find(a => a.id === selectedAssistant.value)
        return assistant ? assistant.greeting_message : null
    }
    return null
})

const fetchKBs = async () => {
  const res = await api.get('/knowledge-bases/')
  kbs.value = res.data
}

const fetchAssistants = async () => {
  const res = await api.get('/assistants/')
  assistants.value = res.data
}

const fetchSessions = async () => {
  const res = await api.get('/chat/sessions')
  sessions.value = res.data
}

const onAssistantChange = () => {
  selectedKB.value = null
  // Show greeting if new chat
  if (!currentSessionId.value && currentGreeting.value) {
      // Logic handled in template, but maybe we want to push it as a message?
      // For now, simple banner is fine.
  }
}

const deleteSession = async (uid) => {
    try {
        await ElMessageBox.confirm('确定删除此对话吗？', '提示', { type: 'warning' })
        await api.delete(`/chat/sessions/${uid}`)
        fetchSessions()
        if (currentSessionId.value === uid) {
            newChat()
        }
        ElMessage.success('已删除')
    } catch (e) {
        if (e !== 'cancel') ElMessage.error('失败')
    }
}

const deleteSelectedSessions = async () => {
    try {
        await ElMessageBox.confirm(`确定删除所选的 ${selectedSessions.value.length} 个对话吗？`, '提示', { type: 'warning' })
        await api.delete('/chat/sessions', { data: selectedSessions.value })
        fetchSessions()
        selectedSessions.value = []
        batchDeleteMode.value = false
        newChat()
        ElMessage.success('已批量删除')
    } catch (e) {
        if (e !== 'cancel') ElMessage.error('失败')
    }
}

const loadSession = async (session) => {
  currentSessionId.value = session.session_uid
  selectedAssistant.value = session.assistant_id
  const res = await api.get(`/chat/sessions/${session.session_uid}/messages`)
  messages.value = []
  res.data.forEach(m => {
    messages.value.push({ role: 'user', content: m.query })
    messages.value.push({ role: m.status === 'failed' ? 'system' : 'assistant', content: m.error || m.answer, sources: m.source_documents || [], trace: m.execution_trace })
  })
  scrollToBottom()
}

const newChat = () => {
  if (sending.value) return
  currentSessionId.value = null
  messages.value = []
}

const sendMessage = async () => {
  if (!inputQuery.value.trim() || sending.value) return
  sending.value = true
  const query = inputQuery.value.trim()
  messages.value.push({ role: 'user', content: query })
  const message = reactive({ role: 'assistant', content: '', pending: true, sources: [], trace: { status: 'running', steps: [] } })
  messages.value.push(message)
  inputQuery.value = ''
  scrollToBottom()
  const payload = { query, session_id: currentSessionId.value }
  if (selectedAssistant.value) payload.assistant_id = selectedAssistant.value
  else if (selectedKB.value) payload.kb_id = selectedKB.value
  try {
    const result = await streamChat(payload, trace => {
      const container = messagesContainer.value
      const follow = !container || container.scrollHeight - container.scrollTop - container.clientHeight < 120
      message.trace = trace
      if (follow) scrollToBottom()
    })
    currentSessionId.value = result.session_id
    Object.assign(message, { content: result.answer, sources: result.source_documents, trace: result.execution_trace })
  } catch (error) {
    message.role = 'system'
    message.content = error.message
    message.trace = error.executionTrace || { ...message.trace, status: error.requestFailed ? 'failed' : 'interrupted', error: error.message }
    if (error.sessionId) currentSessionId.value = error.sessionId
  } finally {
    message.pending = false
    sending.value = false
    scrollToBottom()
    fetchSessions()
  }
}

const scrollToBottom = () => {
  nextTick(() => {
    if (messagesContainer.value) {
      messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight
    }
  })
}

onMounted(async () => {
  await fetchKBs()
  await fetchAssistants()
  await fetchSessions()
  
  if (route.query.assistant_id) {
      selectedAssistant.value = parseInt(route.query.assistant_id)
      fetchVersions()
  }
})

watch(selectedAssistant, (newVal) => {
    if (newVal) fetchVersions()
})

watch(() => route.query.new, () => { newChat() })
</script>

<style scoped>
.chat-workspace { height: 100%; display: flex; flex-direction: column; max-width: none; }
.chat-context-bar { display: flex; gap: var(--space-2); align-items: center; padding: 0 var(--space-6); flex-shrink: 0; min-height: 44px; }
.context-select { width: 180px; }
.context-select :deep(.el-select__wrapper) { box-shadow: none; background: transparent; padding-left: var(--space-2); }
.context-select :deep(.el-select__wrapper:hover) { background: var(--hover); }
.conversation-scroll { flex: 1; min-height: 0; overflow-y: auto; padding: var(--space-6); }
.chat-empty { height: 100%; display: flex; flex-direction: column; justify-content: flex-end; align-items: center; gap: var(--space-4); padding-bottom: var(--space-8); }
.chat-empty p { max-width: 640px; color: var(--text-secondary); }
.chat-workspace:not(.has-messages) .composer-area { margin-bottom: clamp(80px, 26vh, 280px); }
.conversation-thread { max-width: 768px; margin: 0 auto; }
.conversation-message { margin: var(--space-3) 0 var(--space-8); line-height: 1.75; font-size: var(--text-body); overflow-wrap: anywhere; }
.conversation-message.user { margin-left: auto; max-width: 80%; width: fit-content; background: var(--surface-secondary); border-radius: var(--radius-composer); padding: var(--space-3) var(--space-5); }
.conversation-message.assistant { padding: var(--space-2) 0; }
.conversation-message.system { color: var(--danger); font-size: var(--text-base); }
.conversation-content { white-space: pre-wrap; }
.conversation-sources { margin-top: var(--space-4); font-size: var(--text-sm); color: var(--text-secondary); }
.conversation-sources summary { cursor: pointer; width: fit-content; border: 1px solid var(--line); border-radius: var(--radius-lg); padding: var(--space-1) var(--space-3); }
.conversation-sources ul { padding-left: var(--space-5); }
.conversation-sources li { margin-top: var(--space-3); }
.source-score { display: block; font-size: var(--text-xs); color: var(--text-muted); }
.composer-area { width: 100%; max-width: 816px; padding: var(--space-3) var(--space-6) var(--space-3); margin: 0 auto; flex-shrink: 0; }
.composer { border: 1px solid var(--border); border-radius: var(--radius-composer); padding: var(--space-3) var(--space-3) var(--space-2); box-shadow: 0 2px 8px #00000005; background: var(--surface); }
.composer:focus-within { border-color: var(--text-muted); }
.composer :deep(.el-textarea__inner) { background: transparent; box-shadow: none; border-radius: 0; padding: var(--space-2) var(--space-2); font-size: var(--text-body); line-height: 1.6; }
.composer-bottom { display: flex; align-items: center; justify-content: flex-end; gap: var(--space-3); margin-top: var(--space-2); }
.send-button { background: var(--action); color: var(--action-text); border: 0; border-radius: 50%; height: 36px; width: 36px; display: grid; place-items: center; flex-shrink: 0; }
.send-button:hover:not(:disabled) { opacity: .85; }
.send-button:disabled { background: var(--selected); color: var(--text-muted); opacity: 1; }
.composer-hint { color: var(--text-muted); text-align: center; font-size: var(--text-xs); margin-top: var(--space-2); }
.response-loading { display: flex; align-items: center; gap: var(--space-3); font-size: var(--text-sm); color: var(--text-secondary); margin-bottom: var(--space-6); }
.conversation-settings { display: grid; gap: var(--space-4); }
@media (max-width: 767px) { .chat-context-bar { padding: 0 var(--space-3); } .context-select { width: 150px; max-width: 48%; } .conversation-scroll { padding: var(--space-5) var(--space-4); } .composer-area { padding: var(--space-3); } .chat-workspace:not(.has-messages) .composer-area { margin-bottom: 20vh; } .conversation-message { font-size: 15px; } }
</style>
