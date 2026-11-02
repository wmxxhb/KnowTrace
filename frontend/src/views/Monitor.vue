<template>
  <div>
    <div class="page-header"><h1>任务与文件</h1></div>
    
    <el-tabs v-model="activeTab">
      <el-tab-pane label="任务监控" name="queue">
        <div class="monitor-summary" aria-label="任务状态汇总">
          <div class="monitor-summary-item"><strong>{{ stats.total_pending }}</strong><span>待处理</span></div>
          <div class="monitor-summary-item"><strong>{{ stats.total_processing }}</strong><span>处理中</span></div>
          <div class="monitor-summary-item"><strong>{{ stats.total_completed }}</strong><span>已完成</span></div>
          <div class="monitor-summary-item"><strong>{{ stats.total_failed }}</strong><span>失败</span></div>
        </div>

        <div class="filter-bar">
          <el-radio-group v-model="filterStatus" @change="fetchQueue">
            <el-radio-button label="">全部</el-radio-button>
            <el-radio-button label="pending">待处理</el-radio-button>
            <el-radio-button label="processing">处理中</el-radio-button>
            <el-radio-button label="failed">失败</el-radio-button>
          </el-radio-group>
          <el-button @click="fetchQueue" icon="Refresh" circle style="margin-left: 10px;"></el-button>
          <div style="flex: 1"></div>
          <el-button type="danger" @click="batchDelete" :disabled="!selectedQueueItems.length">批量删除</el-button>
        </div>

        <el-table :data="queueItems" style="width: 100%" v-loading="loading" @selection-change="handleQueueSelectionChange">
          <el-table-column type="selection" width="55" />
          <el-table-column prop="filename" label="文件名" />
          <el-table-column prop="kb_name" label="知识库" />
          <el-table-column prop="status" label="状态">
            <template #default="scope">
              <el-tag :type="getStatusType(scope.row.status)">{{ ({ PENDING: '待处理', STARTED: '已启动', PROCESSING: '处理中', RETRY: '重试中', SUCCESS: '已完成', FAILURE: '失败' })[scope.row.status] || scope.row.status }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column label="进度">
             <template #default="scope">
                 <el-progress :percentage="scope.row.progress" :status="scope.row.status === 'FAILURE' ? 'exception' : (scope.row.status === 'SUCCESS' ? 'success' : '')"></el-progress>
             </template>
          </el-table-column>
          <el-table-column prop="message" label="消息" show-overflow-tooltip />
          <el-table-column prop="created_at" label="时间">
              <template #default="scope">
                  {{ new Date(scope.row.created_at).toLocaleString('zh-CN') }}
              </template>
          </el-table-column>
          <el-table-column label="操作">
              <template #default="scope">
                  <el-button size="small" type="danger" @click="deleteQueueItem(scope.row)">删除</el-button>
              </template>
          </el-table-column>
        </el-table>
      </el-tab-pane>
      
    <el-tab-pane label="文件存储" name="minio">
        <div>
            <div class="filter-bar">
               <el-input v-model="minioPrefix" placeholder="搜索文件名称" style="width: 200px; margin-right: 10px;" @keyup.enter="fetchMinioFiles" />
               <el-button @click="fetchMinioFiles" icon="Refresh" circle></el-button>
               <el-button type="danger" @click="batchDeleteMinio" :disabled="!selectedMinioFiles.length">批量删除</el-button>
            </div>
            
            <el-table :data="minioFiles" style="width: 100%" v-loading="minioLoading" @selection-change="handleMinioSelectionChange">
               <el-table-column type="selection" width="55" />
               <el-table-column prop="object_name" label="文件名称" />
               <el-table-column prop="size" label="大小">
                   <template #default="scope">
                       {{ (scope.row.size / 1024).toFixed(2) }} KB
                   </template>
               </el-table-column>
               <el-table-column prop="last_modified" label="最后修改时间">
                   <template #default="scope">
                       {{ new Date(scope.row.last_modified).toLocaleString('zh-CN') }}
                   </template>
               </el-table-column>
               <el-table-column label="操作">
                   <template #default="scope">
                       <el-button size="small" @click="downloadFile(scope.row.object_name)">下载</el-button>
                       <el-button size="small" @click="viewFile(scope.row.object_name)">查看</el-button>
                   </template>
               </el-table-column>
            </el-table>
        </div>
      </el-tab-pane>
    </el-tabs>
    
    <!-- Preview Dialog -->
    <el-dialog v-model="previewVisible" title="文件预览" width="80%" top="5vh" class="preview-dialog">
        <div class="preview-header">
            <h3>{{ currentPreviewFile }}</h3>
        </div>
        <div class="preview-content">
            <iframe :src="previewUrl" style="width: 100%; height: 80vh; border: none;"></iframe>
        </div>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, watch } from 'vue'
import api from '../api' // Assuming api.js exists and exports axios instance
import { Refresh } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'

const activeTab = ref('queue')

// Queue Logic
const stats = ref({
  total_pending: 0,
  total_processing: 0,
  total_failed: 0,
  total_completed: 0
})
const queueItems = ref([])
const selectedQueueItems = ref([])
const loading = ref(false)
const filterStatus = ref('')
let pollTimer = null
const previewVisible = ref(false)
const previewUrl = ref('')
const currentPreviewFile = ref('')

const fetchStats = async () => {
  try {
      const res = await api.get('/monitor/stats')
      stats.value = res.data
  } catch (e) {
      console.error(e)
  }
}

const fetchQueue = async () => {
  loading.value = true
  try {
    const res = await api.get('/monitor/', { params: { status_filter: filterStatus.value || undefined } })
    queueItems.value = res.data
  } catch (e) {
      console.error(e)
  } finally {
    loading.value = false
  }
}

const refreshAll = async () => {
    if (activeTab.value !== 'queue') return
    await fetchStats()
    // Don't show loading on poll
    const res = await api.get('/monitor/', { params: { status_filter: filterStatus.value || undefined } })
    queueItems.value = res.data
}

const getStatusType = (status) => {
    if (status === 'SUCCESS') return 'success'
    if (status === 'FAILURE') return 'danger'
    if (status === 'PROCESSING') return 'warning'
    return 'info'
}

const handleQueueSelectionChange = (val) => {
    selectedQueueItems.value = val
}

const deleteQueueItem = async (row) => {
    try {
        await ElMessageBox.confirm('确定删除此任务记录吗？', '提示', { type: 'warning' })
        // Need backend API support for deleting task records
        // Assuming DELETE /monitor/tasks/{id}
        await api.delete(`/monitor/tasks/${row.task_id}`)
        ElMessage.success('已删除')
        fetchQueue()
        fetchStats()
    } catch (e) {
        if (e !== 'cancel') ElMessage.error('删除失败')
    }
}

const batchDelete = async () => {
    try {
        await ElMessageBox.confirm(`确定删除所选的 ${selectedQueueItems.value.length} 个任务吗？`, '提示', { type: 'warning' })
        const ids = selectedQueueItems.value.map(item => item.task_id)
        await api.post('/monitor/tasks/batch-delete', { task_ids: ids })
        ElMessage.success('已批量删除')
        fetchQueue()
        fetchStats()
    } catch (e) {
        if (e !== 'cancel') ElMessage.error('删除失败')
    }
}

// MinIO Logic
const minioFiles = ref([])
const minioLoading = ref(false)
const minioPrefix = ref('') // Used as search query now
const selectedMinioFiles = ref([])
const handleMinioSelectionChange = (val) => {
    selectedMinioFiles.value = val
}

const batchDeleteMinio = async () => {
    try {
        await ElMessageBox.confirm(`确定删除所选的 ${selectedMinioFiles.value.length} 个文件吗？`, '提示', { type: 'warning' })
        const objectNames = selectedMinioFiles.value.map(item => item.object_name)
        await api.post('/storage/batch-delete', { object_names: objectNames })
        ElMessage.success('已批量删除')
        fetchMinioFiles()
    } catch (e) {
        if (e !== 'cancel') ElMessage.error('删除失败')
    }
}

const fetchMinioFiles = async () => {
    minioLoading.value = true
    try {
        // Use prefix as search query for fuzzy search
        const res = await api.get('/storage/files', { 
            params: { 
                search_query: minioPrefix.value,
                sort_by: 'last_modified',
                order: 'desc'
            } 
        })
        minioFiles.value = res.data.files
    } catch (e) {
        console.error(e)
        ElMessage.error('获取文件列表失败')
    } finally {
        minioLoading.value = false
    }
}

const downloadFile = async (objectName) => {
    try {
        // Use proxy download endpoint
        const url = `/api/v1/storage/download/${encodeURIComponent(objectName)}`
        window.open(url, '_blank')
    } catch (e) {
        console.error(e)
        ElMessage.error('下载文件失败')
    }
}

const viewFile = async (objectName) => {
    try {
        currentPreviewFile.value = objectName
        // Use proxy preview endpoint
        // We need full URL for iframe
        const baseUrl = import.meta.env.VITE_API_BASE_URL || '/api/v1'
        // If baseUrl is relative, prepend origin
        let fullBase = baseUrl
        if (baseUrl.startsWith('/')) {
            fullBase = window.location.origin + baseUrl
        }
        
        previewUrl.value = `${fullBase}/storage/preview/${encodeURIComponent(objectName)}`
        previewVisible.value = true
    } catch (e) {
        console.error(e)
        ElMessage.error('打开文件失败')
    }
}

onMounted(() => {
  fetchStats()
  fetchQueue()
  
  if (activeTab.value === 'minio') fetchMinioFiles()
  
  pollTimer = setInterval(refreshAll, 3000)
})

watch(activeTab, (newTab) => { if (newTab === 'minio') fetchMinioFiles() })

onUnmounted(() => {
    if (pollTimer) clearInterval(pollTimer)
})
</script>

<style scoped>
.stat-value {
    font-size: 24px;
    font-weight: bold;
    text-align: center;
}
.processing { color: var(--warning); }
.failed { color: var(--danger); }
.success { color: var(--success); }
.filter-bar {
    margin-bottom: 20px;
    display: flex;
    align-items: center;
}
</style>
