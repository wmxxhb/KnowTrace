<template>
  <div>
    <div class="page-header">
      <h1>知识库</h1>
      <el-button type="primary" @click="dialogVisible = true"><UiIcon name="plus" :size="16" /><span>新建知识库</span></el-button>
    </div>
    <div class="library-toolbar"><el-input v-model="search" placeholder="搜索知识库" clearable aria-label="搜索知识库"><template #prefix><UiIcon name="search" :size="16" /></template></el-input><span>{{ filteredKBs.length }} 个知识库</span></div>
    <div v-loading="loading" class="library-list">
      <div v-for="kb in filteredKBs" :key="kb.id" class="library-row">
        <router-link :to="`/knowledge-bases/${kb.id}`" class="library-entry"><span class="library-info"><strong>{{ kb.name }}</strong><span v-if="kb.description">{{ kb.description }}</span></span></router-link>
        <span class="library-date">{{ formatDate(kb.created_at) }}</span>
        <div class="library-actions"><button class="icon-button" :aria-label="'编辑知识库：' + kb.name" title="编辑" @click="openEditDialog(kb)"><UiIcon name="settings" :size="18" /></button><button class="icon-button" :aria-label="'删除知识库：' + kb.name" title="删除" @click="deleteKB(kb.id)"><UiIcon name="close" :size="18" /></button></div>
      </div>
      <div v-if="!loading && !filteredKBs.length" class="empty-state"><p>{{ search ? '未找到知识库' : '暂无知识库' }}</p><el-button v-if="!search" text @click="dialogVisible = true">新建知识库</el-button></div>
    </div>

    <!-- Create KB Dialog -->
    <el-dialog v-model="dialogVisible" title="创建知识库">
      <el-form :model="form" label-width="120px">
        <el-form-item label="名称">
          <el-input v-model="form.name" />
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="form.description" />
        </el-form-item>
        
        <el-divider>分块策略</el-divider>
        <el-form-item label="分块方式">
            <el-select v-model="form.chunking_config.method">
                <el-option label="递归分块（推荐）" value="recursive" />
                <el-option label="固定长度" value="fixed" />
                <el-option label="分隔符" value="separator" />
                <el-option label="语义分块" value="semantic" />
            </el-select>
        </el-form-item>
        <el-form-item label="分块长度">
            <el-input-number v-model="form.chunking_config.chunk_size" :min="100" :max="2000" :step="100" />
        </el-form-item>
        <el-form-item label="重叠长度">
            <el-input-number v-model="form.chunking_config.chunk_overlap" :min="0" :max="500" :step="10" />
        </el-form-item>
        <el-form-item label="分隔符" v-if="form.chunking_config.method === 'separator'">
            <el-input v-model="form.chunking_config.separator" placeholder="\n\n" />
        </el-form-item>
      </el-form>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="dialogVisible = false">取消</el-button>
          <el-button type="primary" @click="createKB">确认</el-button>
        </span>
      </template>
    </el-dialog>

    <!-- Edit KB Dialog -->
    <el-dialog v-model="editDialogVisible" title="编辑知识库">
      <el-form :model="editForm" label-width="120px">
        <el-form-item label="名称">
          <el-input v-model="editForm.name" />
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="editForm.description" />
        </el-form-item>
        
        <el-divider>分块策略</el-divider>
        <el-form-item label="分块方式">
            <el-select v-model="editForm.chunking_config.method">
                <el-option label="递归分块（推荐）" value="recursive" />
                <el-option label="固定长度" value="fixed" />
                <el-option label="分隔符" value="separator" />
                <el-option label="语义分块" value="semantic" />
            </el-select>
        </el-form-item>
        <el-form-item label="分块长度">
            <el-input-number v-model="editForm.chunking_config.chunk_size" :min="100" :max="2000" :step="100" />
        </el-form-item>
        <el-form-item label="重叠长度">
            <el-input-number v-model="editForm.chunking_config.chunk_overlap" :min="0" :max="500" :step="10" />
        </el-form-item>
        <el-form-item label="分隔符" v-if="editForm.chunking_config.method === 'separator'">
            <el-input v-model="editForm.chunking_config.separator" placeholder="\n\n" />
        </el-form-item>
      </el-form>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="editDialogVisible = false">取消</el-button>
          <el-button type="primary" @click="updateKB">保存</el-button>
        </span>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import api from '../api'
import UiIcon from '../components/UiIcon.vue'
import { ElMessage, ElMessageBox } from 'element-plus'

const router = useRouter()
const kbs = ref([])
const search = ref('')
const loading = ref(false)
const filteredKBs = computed(() => kbs.value.filter(kb => `${kb.name} ${kb.description || ''}`.toLowerCase().includes(search.value.toLowerCase())))
const dialogVisible = ref(false)
const editDialogVisible = ref(false)
const currentKbId = ref(null)

const form = reactive({
  name: '',
  description: '',
  chunking_config: {
      method: 'recursive',
      chunk_size: 500,
      chunk_overlap: 50,
      separator: ''
  }
})

const editForm = reactive({
  name: '',
  description: '',
  chunking_config: {
      method: 'recursive',
      chunk_size: 500,
      chunk_overlap: 50,
      separator: ''
  }
})

const fetchKBs = async () => {
  loading.value = true
  try {
    const res = await api.get('/knowledge-bases/')
    kbs.value = res.data
  } catch (error) {
    ElMessage.error('加载知识库失败')
  } finally { loading.value = false }
}

const createKB = async () => {
  try {
      await api.post('/knowledge-bases/', form)
      dialogVisible.value = false
      fetchKBs()
      ElMessage.success('知识库已创建')
  } catch (e) {
      ElMessage.error('创建知识库失败')
  }
}

const openEditDialog = (kb) => {
    currentKbId.value = kb.id
    editForm.name = kb.name
    editForm.description = kb.description
    // Deep copy to avoid reference issues
    editForm.chunking_config = JSON.parse(JSON.stringify(kb.chunking_config || {
        method: 'recursive',
        chunk_size: 500,
        chunk_overlap: 50,
        separator: ''
    }))
    editDialogVisible.value = true
}

const updateKB = async () => {
    try {
        await api.put(`/knowledge-bases/${currentKbId.value}`, editForm)
        editDialogVisible.value = false
        fetchKBs()
        ElMessage.success('知识库已更新')
    } catch (e) {
        ElMessage.error('更新知识库失败')
    }
}

const deleteKB = async (id) => {
    try {
        await ElMessageBox.confirm("确定删除此知识库吗？", "提示", {
            type: 'warning'
        })
        await api.delete(`/knowledge-bases/${id}`)
        fetchKBs()
        ElMessage.success('知识库已删除')
    } catch (e) {
        if (e !== 'cancel') ElMessage.error('删除失败')
    }
}

const goToDetail = (id) => {
    router.push(`/knowledge-bases/${id}`)
}

const formatDate = (dateStr) => {
    return new Date(dateStr).toLocaleDateString('zh-CN')
}

onMounted(fetchKBs)
</script>

<style scoped>
.library-toolbar { display: flex; align-items: center; justify-content: space-between; gap: var(--space-4); padding-bottom: var(--space-5); border-bottom: 1px solid var(--line); }
.library-toolbar .el-input { max-width: 320px; }
.library-toolbar > span { color: var(--text-muted); font-size: var(--text-sm); white-space: nowrap; }
.library-row { display: flex; align-items: center; gap: var(--space-6); padding: var(--space-5) var(--space-3); border-bottom: 1px solid var(--line); }
.library-row:hover { background: var(--surface-secondary); }
.library-entry { display: flex; gap: var(--space-4); align-items: center; flex: 1; min-width: 0; }
.library-info { display: grid; gap: var(--space-1); min-width: 0; }
.library-info strong { font-weight: var(--weight-medium); font-size: var(--text-body); }
.library-info > span { color: var(--text-secondary); font-size: var(--text-sm); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.library-date { color: var(--text-muted); font-size: var(--text-sm); }
.library-actions { display: flex; gap: var(--space-1); }
@media (max-width: 767px) { .library-row { gap: var(--space-2); padding-left: 0; padding-right: 0; } .library-date { display: none; } }
</style>
