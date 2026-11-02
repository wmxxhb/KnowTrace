<template>
  <div>
    <div class="page-header"><h1>助手</h1><el-button type="primary" @click="openDialog()">新建助手</el-button></div>
    
    <el-table :data="assistants" style="width: 100%; margin-top: 20px;">
      <el-table-column prop="name" label="名称" width="180" />
      <el-table-column prop="description" label="描述" />
      <el-table-column prop="llm_model" label="模型" />
      <el-table-column label="操作">
        <template #default="scope">
          <el-button size="small" @click="startChat(scope.row)">智能问答</el-button>
          <el-button size="small" @click="openDialog(scope.row)">编辑</el-button>
          <el-button size="small" type="danger" @click="deleteAssistant(scope.row.id)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-dialog v-model="dialogVisible" :title="isEdit ? '编辑助手' : '创建助手'" width="60%">
      <el-form :model="form" label-width="140px">
        <el-tabs v-model="activeTab">
            <el-tab-pane label="基本信息" name="basic">
                <el-form-item label="名称">
                  <el-input v-model="form.name" />
                </el-form-item>
                <el-form-item label="描述">
                  <el-input v-model="form.description" />
                </el-form-item>
                <el-form-item label="模型">
                  <el-select v-model="form.llm_model">
                    <el-option label="Qwen 3.7 Plus" value="qwen3.7-plus" />
                  </el-select>
                </el-form-item>
                <el-form-item label="系统提示词">
                  <el-input type="textarea" v-model="form.system_prompt" :rows="4" />
                </el-form-item>
                <el-form-item label="开场白">
                  <el-input type="textarea" v-model="form.greeting_message" :rows="2" placeholder="对话开始时显示的消息" />
                </el-form-item>
                <el-form-item label="温度系数">
                  <el-slider v-model="form.temperature" :min="0" :max="1" :step="0.1" show-input />
                </el-form-item>
            </el-tab-pane>
            
            <el-tab-pane label="记忆设置" name="memory">
                <el-form-item label="短期记忆">
                    <el-switch v-model="form.memory_config.enable_short_term" />
                </el-form-item>
                <el-form-item label="记忆轮数" v-if="form.memory_config.enable_short_term">
                    <el-input-number v-model="form.memory_config.window_size" :min="1" :max="20" />
                </el-form-item>
                <el-form-item label="长期记忆">
                    <el-switch v-model="form.memory_config.enable_long_term" />
                </el-form-item>
            </el-tab-pane>
            
            <el-tab-pane label="检索与知识库" name="rag">
                <el-form-item label="知识库">
                  <el-select v-model="form.kb_ids" multiple placeholder="选择知识库">
                    <el-option
                      v-for="item in kbs"
                      :key="item.id"
                      :label="item.name"
                      :value="item.id"
                    />
                  </el-select>
                </el-form-item>
                
                <el-divider content-position="left">检索设置</el-divider>
                
                <el-form-item label="召回数量">
                    <el-slider v-model="form.rag_config.top_k" :min="1" :max="20" show-input />
                </el-form-item>
                
                <el-form-item label="混合检索权重">
                    <el-tooltip content="此功能尚未实现（取值 0.0～1.0）" placement="top">
                        <el-slider v-model="form.rag_config.hybrid_weight" :min="0" :max="1" :step="0.1" show-input />
                    </el-tooltip>
                </el-form-item>
                
                <el-form-item label="启用重排序">
                    <el-switch v-model="form.rag_config.enable_rerank" />
                </el-form-item>
                
                <el-form-item label="重排序保留数量" v-if="form.rag_config.enable_rerank">
                    <el-input-number v-model="form.rag_config.rerank_top_n" :min="1" :max="20" />
                </el-form-item>
            </el-tab-pane>
        </el-tabs>
      </el-form>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="dialogVisible = false">取消</el-button>
          <el-button type="primary" @click="saveAssistant">确认</el-button>
        </span>
      </template>
    </el-dialog>

    <!-- Full Screen Chat Interface -->
    <div v-if="chatVisible" class="full-screen-chat">
        <div class="chat-header">
            <div class="header-left">
                <el-button icon="Back" circle @click="chatVisible = false" style="margin-right: 10px;" />
                <h3>{{ currentChatAssistant?.name }}</h3>
                <el-tag v-if="currentVersion" type="info" style="margin-left: 10px;">{{ currentVersion }}</el-tag>
            </div>
            <div class="header-right"><el-button @click="assistantSettingsOpen = true">助手设置</el-button>
                 <el-select v-model="chatModel" placeholder="模型" style="width: 150px; margin-right: 10px;">
                    <el-option label="Qwen 3.7 Plus" value="qwen3.7-plus" />
                 </el-select>
                 <el-select v-model="currentVersion" placeholder="版本" style="width: 120px; margin-right: 10px;" @change="restoreVersion">
                    <el-option v-for="v in assistantVersions" :key="v.version" :label="v.version" :value="v.version" />
                 </el-select>
                 <el-button type="primary" @click="saveNewVersion">保存版本</el-button>
                 <el-button @click="startNewChat" type="success" plain style="margin-left: 10px;">新建对话</el-button>
                 <el-button @click="clearHistory" type="danger" plain style="margin-left: 10px;">清空历史</el-button>
            </div>
        </div>
        
        <div class="chat-body">
            <!-- Left Panel: Assistant Info -->
            <el-drawer v-model="assistantSettingsOpen" title="助手设置" size="400px"><div class="info-panel">
                <el-scrollbar>
                    <div style="padding: 20px;">
                        <el-form :model="form" label-width="120px" label-position="top">
                            <el-tabs v-model="activeTab">
                                <el-tab-pane label="基本信息" name="basic">
                                    <el-form-item label="名称">
                                      <el-input v-model="form.name" />
                                    </el-form-item>
                                    <el-form-item label="描述">
                                      <el-input v-model="form.description" />
                                    </el-form-item>
                                    <el-form-item label="系统提示词">
                                      <el-input type="textarea" v-model="form.system_prompt" :rows="6" />
                                    </el-form-item>
                                    <el-form-item label="开场白">
                                      <el-input type="textarea" v-model="form.greeting_message" :rows="3" />
                                    </el-form-item>
                                    <el-form-item label="温度系数">
                                      <el-slider v-model="form.temperature" :min="0" :max="1" :step="0.1" show-input />
                                    </el-form-item>
                                </el-tab-pane>
                                
                                <el-tab-pane label="记忆设置" name="memory">
                                <el-form-item label="短期记忆">
                                    <el-switch v-model="form.memory_config.enable_short_term" />
                                </el-form-item>
                                <el-form-item label="记忆轮数" v-if="form.memory_config.enable_short_term">
                                    <el-input-number v-model="form.memory_config.window_size" :min="1" :max="20" />
                                    <div class="form-tip">保留最近的对话轮数（建议 5～10 轮）</div>
                                </el-form-item>
                                <el-form-item label="长期记忆">
                                    <el-switch v-model="form.memory_config.enable_long_term" />
                                    <div class="form-tip">根据语义相似度从向量库检索相关历史</div>
                                </el-form-item>
                            </el-tab-pane>
                            
                            <el-tab-pane label="检索与知识库" name="rag">
                                    <el-form-item label="知识库">
                                      <el-select v-model="form.kb_ids" multiple placeholder="选择知识库" style="width: 100%;">
                                        <el-option
                                          v-for="item in kbs"
                                          :key="item.id"
                                          :label="item.name"
                                          :value="item.id"
                                        />
                                      </el-select>
                                    </el-form-item>
                                    
                                    <el-divider content-position="left">检索设置</el-divider>
                                    
                                    <el-form-item label="召回数量">
                                        <el-slider v-model="form.rag_config.top_k" :min="1" :max="20" show-input />
                                    </el-form-item>
                                    
                                    <el-form-item label="混合检索权重">
                                        <el-slider v-model="form.rag_config.hybrid_weight" :min="0" :max="1" :step="0.1" show-input />
                                    </el-form-item>
                                    
                                    <el-form-item label="启用重排序">
                                        <el-switch v-model="form.rag_config.enable_rerank" />
                                    </el-form-item>
                                    
                                    <el-form-item label="重排序保留数量" v-if="form.rag_config.enable_rerank">
                                        <el-input-number v-model="form.rag_config.rerank_top_n" :min="1" :max="20" />
                                    </el-form-item>
                                </el-tab-pane>
                            </el-tabs>
                        </el-form>
                    </div>
                </el-scrollbar>
            </div>
            
            </el-drawer>
            <!-- Right Panel: Chat Interface -->
            <div class="chat-panel">
                <div class="chat-greeting" v-if="form.greeting_message">
                    <el-alert :title="form.greeting_message" type="info" :closable="false" show-icon />
                </div>
                
                <div class="kb-info" v-if="chatLinkedKBs.length" style="padding: 10px 20px; border-bottom: 1px solid var(--line);">
                    <span style="color: var(--text-secondary); font-size: 0.9em; margin-right: 10px;">关联知识库：</span>
                    <el-tag v-for="kb in chatLinkedKBs" :key="kb.id" size="small" style="margin-right: 5px;">{{ kb.name }}</el-tag>
                </div>
                
                <div class="messages" ref="messagesContainer">
                    <div v-for="(msg, index) in chatMessages" :key="index" :class="['message', msg.role]">
                      <div v-if="msg.content" class="message-content" style="white-space: pre-wrap;">{{ msg.content }}</div>
                      <ExecutionTrace v-if="msg.trace" :trace="msg.trace" :live="msg.pending" />
                      <div v-if="msg.sources && msg.sources.length" class="sources">
                        <small>参考来源：</small>
                        <ul>
                          <li v-for="src in msg.sources" :key="src.id">
                            {{ src.text.substring(0, 50) }}...
                          </li>
                        </ul>
                      </div>
                    </div>
                </div>
                
                <div class="input-area">
                    <el-input 
                      v-model="inputQuery" 
                      placeholder="请输入你的问题…" 
                      @keyup.enter="sendMessage"
                      :rows="3"
                      type="textarea"
                      resize="none"
                    >
                    </el-input>
                    <div style="text-align: right; margin-top: 10px;">
                        <el-button type="primary" @click="sendMessage" icon="Position">发送</el-button>
                    </div>
                </div>
            </div>
        </div>
    </div>


  </div>
</template>

<script setup>
import { ref, reactive, onMounted, nextTick, computed } from 'vue'
import { useRouter } from 'vue-router'
import api from '../api'
import { streamChat } from '../api/chat'
import ExecutionTrace from '../components/ExecutionTrace.vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Back, Position } from '@element-plus/icons-vue'

const router = useRouter()
const assistants = ref([])
const kbs = ref([])
const agents = ref([])
const dialogVisible = ref(false)
const isEdit = ref(false)
const currentId = ref(null)
const activeTab = ref('basic')

// Chat Drawer State
const chatVisible = ref(false)
const assistantSettingsOpen = ref(false)
const currentChatAssistant = ref(null)
const chatMessages = ref([])
const inputQuery = ref('')
const currentSessionId = ref(null)
const messagesContainer = ref(null)
const chatModel = ref('qwen3.7-plus')
const currentVersion = ref('v1.0.0')
const assistantVersions = ref([])

const form = reactive({
  name: '',
  description: '',
  llm_model: 'qwen3.7-plus',
  temperature: 0.7,
  system_prompt: '',
  greeting_message: '',
  kb_ids: [],
  agent_ids: [],
  memory_config: {
      enable_short_term: true,
      window_size: 10,
      enable_long_term: false
  },
  rag_config: {
      top_k: 5,
      hybrid_weight: 0.5,
      enable_rerank: false,
      rerank_top_n: 5
  }
})

const fetchAssistants = async () => {
  const res = await api.get('/assistants/')
  assistants.value = res.data
}

const fetchKBs = async () => {
  const res = await api.get('/knowledge-bases/')
  kbs.value = res.data
}

const fetchAgents = async () => {
  const res = await api.get('/agents/')
  agents.value = res.data
}

const chatLinkedKBs = computed(() => {
    if (!currentChatAssistant.value || !currentChatAssistant.value.kb_ids) return []
    return kbs.value.filter(kb => currentChatAssistant.value.kb_ids.includes(kb.id))
})

const startChat = async (row) => {
    currentChatAssistant.value = row
    chatModel.value = row.llm_model
    chatMessages.value = []
    currentSessionId.value = null
    inputQuery.value = ''
    
    // Load History
    try {
        // Fetch all sessions first
        const res = await api.get('/chat/sessions')
        // Filter sessions for this assistant
        const sessions = res.data.filter(s => s.assistant_id === row.id)
        
        if (sessions.length > 0) {
            // Sort by created_at desc to get the latest session
            sessions.sort((a, b) => new Date(b.created_at) - new Date(a.created_at))
            const latest = sessions[0]
            currentSessionId.value = latest.session_uid
            
            // Fetch messages for this session
            const msgRes = await api.get(`/chat/sessions/${latest.session_uid}/messages`)
            console.log('Chat History Response:', msgRes.data)
            
            // Backend returns [{query:..., answer:..., created_at:...}]
            // We need to flatten this to chatMessages format: {role: 'user', content: ...}, {role: 'assistant', content: ...}
            const history = []
            if (Array.isArray(msgRes.data)) {
                msgRes.data.forEach(item => {
                    if (item.query) {
                        history.push({ role: 'user', content: item.query })
                    }
                    if (item.answer || item.execution_trace || item.error) {
                        history.push({ 
                            role: item.status === 'failed' ? 'system' : 'assistant',
                            content: item.error || item.answer,
                            trace: item.execution_trace,
                            sources: item.source_documents || [] // Map sources if available
                        })
                    }
                })
            }
            chatMessages.value = history
            
            scrollToBottom()
        } else {
             // No history, create new session or wait for first message?
             // Usually we wait for first message to create session, OR create one now.
             // Let's create one now to ensure session ID exists
             currentSessionId.value = null
             
             // Add greeting if exists
             if (row.greeting_message) {
                 // chatMessages.value.push({ role: 'assistant', content: row.greeting_message })
             }
        }
    } catch (e) {
        console.error("加载历史记录失败", e)
    }
    
    // Fetch Versions
    await fetchVersions(row.id)
    if (assistantVersions.value.length > 0) {
        currentVersion.value = assistantVersions.value[assistantVersions.value.length - 1].version
    } else {
        currentVersion.value = 'v1.0.0'
    }

    // Populate form for Info Panel
    const data = JSON.parse(JSON.stringify(row))
    if (!data.rag_config) {
        data.rag_config = {
            top_k: 5,
            hybrid_weight: 0.5,
            enable_rerank: false,
            rerank_top_n: 5
        }
    }
    if (!data.memory_config) {
        data.memory_config = {
            enable_short_term: true,
            window_size: 10,
            enable_long_term: false
        }
    }
    Object.assign(form, data)
    
    chatVisible.value = true
}

const startNewChat = () => {
    if (chatLoading.value) return
    currentSessionId.value = null
    chatMessages.value = []
    inputQuery.value = ''
}

const clearHistory = async () => {
    if (!currentSessionId.value) return
    try {
        await ElMessageBox.confirm('确定清空对话历史吗？', '提示', { type: 'warning' })
        await api.delete(`/chat/sessions/${currentSessionId.value}`)
        chatMessages.value = []
        currentSessionId.value = null
        ElMessage.success('历史记录已清空')
    } catch (e) {
        if (e !== 'cancel') ElMessage.error('清空历史记录失败')
    }
}

const fetchVersions = async (id) => {
    try {
        const res = await api.get(`/assistants/${id}/versions`)
        assistantVersions.value = res.data
    } catch (e) {
        assistantVersions.value = []
    }
}

const saveNewVersion = async () => {
    if (!currentChatAssistant.value) return
    try {
        const nextVer = incrementVersion(currentVersion.value)
        
        // Use form state for the new config
        // Also update currentChatAssistant.value locally to reflect changes immediately
        const updatedConfig = {
            ...currentChatAssistant.value, // Keep ID, user_id etc
            name: form.name,
            description: form.description,
            system_prompt: form.system_prompt,
            greeting_message: form.greeting_message,
            temperature: form.temperature,
            memory_config: form.memory_config,
            rag_config: form.rag_config,
            kb_ids: form.kb_ids,
            llm_model: chatModel.value
        }
        
        // UPDATE ASSISTANT CONFIG FIRST
        await api.put(`/assistants/${currentChatAssistant.value.id}`, {
            name: form.name,
            description: form.description,
            system_prompt: form.system_prompt,
            greeting_message: form.greeting_message,
            temperature: form.temperature,
            memory_config: form.memory_config,
            rag_config: form.rag_config,
            kb_ids: form.kb_ids,
            llm_model: chatModel.value
        })

        await api.post(`/assistants/${currentChatAssistant.value.id}/versions`, {
            version: nextVer,
            config: updatedConfig
        })
        
        ElMessage.success(`已保存版本 ${nextVer} 并更新助手`)
        currentVersion.value = nextVer
        fetchVersions(currentChatAssistant.value.id)
        // Refresh main list
        fetchAssistants()
    } catch (e) {
        ElMessage.error('保存版本失败')
    }
}

const incrementVersion = (ver) => {
    if (!ver) return 'v1.0.0'
    // Format vX.Y.Z
    const parts = ver.replace('v', '').split('.').map(Number)
    if (parts.length !== 3) return 'v1.0.0'
    
    let [major, minor, patch] = parts
    
    patch += 1
    if (patch >= 10) {
        patch = 0
        minor += 1
    }
    if (minor >= 10) {
        minor = 0
        major += 1
    }
    
    return `v${major}.${minor}.${patch}`
}

const restoreVersion = async (verStr) => {
    // Find version config
    const verObj = assistantVersions.value.find(v => v.version === verStr)
    if (verObj && verObj.config) {
        try {
            await ElMessageBox.confirm(`确定将助手恢复到 ${verStr} 吗？`, '确认')
            await api.put(`/assistants/${currentChatAssistant.value.id}`, verObj.config)
            ElMessage.success('已恢复')
            // Update local state
            chatModel.value = verObj.config.llm_model
            fetchAssistants() // Refresh table
        } catch (e) {
             // cancel
        }
    }
}

const chatLoading = ref(false)

const sendMessage = async () => {
  if (!inputQuery.value.trim() || chatLoading.value) return
  const query = inputQuery.value.trim()
  chatMessages.value.push({ role: 'user', content: query })
  const message = reactive({ role: 'assistant', content: '', pending: true, sources: [], trace: { status: 'running', steps: [] } })
  chatMessages.value.push(message)
  inputQuery.value = ''
  chatLoading.value = true
  scrollToBottom()
  try {
    const result = await streamChat({ query, session_id: currentSessionId.value, assistant_id: currentChatAssistant.value.id, llm_model: chatModel.value }, trace => {
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
    chatLoading.value = false
    scrollToBottom()
  }
}

const scrollToBottom = () => {
  nextTick(() => {
    if (messagesContainer.value) {
      messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight
    }
  })
}

const openDialog = (row = null) => {
  activeTab.value = 'basic'
  if (row) {
    isEdit.value = true
    currentId.value = row.id
    // Deep copy to avoid reference issues, and handle missing rag_config
    const data = JSON.parse(JSON.stringify(row))
    if (!data.rag_config) {
        data.rag_config = {
            top_k: 5,
            hybrid_weight: 0.5,
            enable_rerank: false,
            rerank_top_n: 5
        }
    }
    Object.assign(form, data)
  } else {
    isEdit.value = false
    currentId.value = null
    Object.assign(form, {
      name: '',
      description: '',
      llm_model: 'qwen3.7-plus',
      temperature: 0.7,
      system_prompt: '',
      greeting_message: '',
      kb_ids: [],
      agent_ids: [],
      rag_config: {
          top_k: 5,
          hybrid_weight: 0.5,
          enable_rerank: false,
          rerank_top_n: 5
      }
    })
  }
  dialogVisible.value = true
}

const saveAssistant = async () => {
  try {
    if (isEdit.value) {
      await api.put(`/assistants/${currentId.value}`, form)
    } else {
      await api.post('/assistants/', form)
    }
    dialogVisible.value = false
    fetchAssistants()
    ElMessage.success('助手已保存')
  } catch (e) {
    console.error(e)
    ElMessage.error('操作失败')
  }
}

const deleteAssistant = async (id) => {
  try {
    await ElMessageBox.confirm('确定删除此助手吗？', '删除助手', { type: 'warning' })
    await api.delete(`/assistants/${id}`)
    fetchAssistants()
    ElMessage.success('助手已删除')
  } catch (error) {
    if (error !== 'cancel' && error !== 'close') ElMessage.error('删除失败')
  }
}

onMounted(() => {
  fetchAssistants()
  fetchKBs()
  fetchAgents()
})
</script>

<style scoped>
.full-screen-chat { position: fixed; inset: 0; height: 100dvh; z-index: 1000; background: var(--surface); display: flex; flex-direction: column; }
.chat-header { min-height: 60px; display: flex; align-items: center; justify-content: space-between; padding: var(--space-3) var(--space-6); gap: var(--space-4); }
.header-left, .header-right { display: flex; align-items: center; gap: var(--space-2); }
.header-left h3 { font-size: var(--text-body); }
.chat-body { flex: 1; min-height: 0; display: flex; overflow: hidden; }
.info-panel { display: flex; flex-direction: column; width: 100%; min-width: 0; }
.info-panel .el-scrollbar { height: 100%; }
.chat-panel { flex: 1; min-width: 0; display: flex; flex-direction: column; background: var(--surface); }
.chat-greeting { max-width: 816px; width: 100%; margin: 0 auto; padding: var(--space-3) var(--space-6); }
.messages { flex: 1; min-height: 0; overflow-y: auto; padding: var(--space-6); }
.message { margin-bottom: var(--space-8); font-size: var(--text-body); line-height: 1.75; overflow-wrap: anywhere; }
.message.user { margin-left: auto; max-width: 80%; width: fit-content; background: var(--surface-secondary); padding: var(--space-3) var(--space-5); border-radius: var(--radius-composer); }
.message.assistant { background: transparent; }
.input-area { padding: var(--space-3) var(--space-6) var(--space-5); background: var(--surface); }
.sources { margin-top: var(--space-3); font-size: var(--text-sm); color: var(--text-secondary); }
.typing-dot { font-size: var(--text-lg); margin: 0 var(--space-1); color: var(--text-secondary); }
@media (max-width: 767px) { .messages { padding: var(--space-4); } .input-area { padding: var(--space-3); } .chat-header { padding: var(--space-3); } }
</style>
