<template>
  <div class="workspace" :class="{ 'sidebar-collapsed': collapsed, 'mobile-open': mobileOpen }">
    <button v-if="mobileOpen" class="sidebar-scrim" aria-label="关闭导航" @click="closeMobile" />
    <aside ref="sidebarElement" id="workspace-sidebar" class="workspace-sidebar" :role="mobile ? 'dialog' : undefined" :aria-modal="mobileOpen ? true : undefined" aria-label="工作区导航" :inert="sidebarHidden" :aria-hidden="sidebarHidden">
      <div class="sidebar-top">
        <button class="icon-button" aria-label="收起导航" title="收起导航" @click="toggleSidebar"><UiIcon name="panel" /></button>
      </div>
      <button class="new-chat-link" @click="startChat"><UiIcon name="compose" /><span>新建对话</span></button>
      <nav class="workspace-nav" aria-label="主导航">
        <router-link v-for="item in navigation" :key="item.path" :to="item.path" :class="{ selected: route.path.startsWith(item.path) }"><UiIcon :name="item.icon" /><span>{{ item.label }}</span></router-link>
      </nav>
      <div id="chat-history" class="sidebar-history" v-show="route.path === '/chat'" />
      <div class="sidebar-bottom">
        <el-dropdown trigger="click" placement="top-start" @command="setTheme">
          <button class="theme-button"><UiIcon :name="theme === 'dark' ? 'moon' : theme === 'light' ? 'sun' : 'monitor'" /><span>外观</span><span class="theme-value">{{ themeNames[theme] }}</span><UiIcon name="down" :size="14" /></button>
          <template #dropdown><el-dropdown-menu><el-dropdown-item v-for="(label, value) in themeNames" :key="value" :command="value" :class="{ 'is-theme-selected': theme === value }">{{ label }}<span v-if="theme === value" class="theme-check">✓</span></el-dropdown-item></el-dropdown-menu></template>
        </el-dropdown>
      </div>
    </aside>
    <div class="workspace-body" :inert="mobileOpen && mobile">
      <header v-if="sidebarHidden" class="workspace-toolbar">
        <button ref="sidebarToggle" class="icon-button expand-sidebar" aria-label="展开导航" aria-controls="workspace-sidebar" :aria-expanded="!sidebarHidden" @click="toggleSidebar"><UiIcon name="panel" /></button>
      </header>
      <main id="main-content" class="workspace-main" :class="{ 'is-chat': route.path === '/chat' }">
        <router-view v-slot="{ Component }"><component :is="Component" class="page-view" /></router-view>
      </main>
    </div>
  </div>
</template>
<script setup>
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import UiIcon from './components/UiIcon.vue'
const route = useRoute()
const router = useRouter()
function startChat() { router.push({ path: '/chat', query: { new: String(Date.now()) } }) }
const collapsed = ref(localStorage.getItem('sidebar-collapsed') === 'true')
const mobileOpen = ref(false)
const mobile = ref(window.innerWidth < 768)
const sidebarToggle = ref(null)
const sidebarElement = ref(null)
const themeNames = { light: '浅色', dark: '深色', system: '跟随系统' }
const savedTheme = localStorage.getItem('workspace-theme')
const theme = ref(savedTheme in themeNames ? savedTheme : 'light')
const colorScheme = window.matchMedia('(prefers-color-scheme: dark)')
const sidebarHidden = computed(() => mobile.value ? !mobileOpen.value : collapsed.value)
const navigation = [
  { path: '/chat', label: '智能问答', icon: 'chat' },
  { path: '/knowledge-bases', label: '知识库', icon: 'folder' },
  { path: '/assistants', label: '助手', icon: 'assistant' },
  { path: '/agents', label: '智能体', icon: 'layers' },
  { path: '/evaluation', label: '评测', icon: 'chart' },
  { path: '/monitor', label: '任务与文件', icon: 'activity' },
]
function applyTheme() {
  document.documentElement.dataset.theme = theme.value === 'system' ? (colorScheme.matches ? 'dark' : 'light') : theme.value
}
function setTheme(value) { theme.value = value; localStorage.setItem('workspace-theme', value); applyTheme() }
function closeMobile() { mobileOpen.value = false; sidebarToggle.value?.focus() }
function toggleSidebar() {
  if (mobile.value) mobileOpen.value = !mobileOpen.value
  else {
    collapsed.value = !collapsed.value
    localStorage.setItem('sidebar-collapsed', String(collapsed.value))
    if (collapsed.value) nextTick(() => sidebarToggle.value?.focus())
  }
}
function resize() { mobile.value = window.innerWidth < 768; if (!mobile.value) mobileOpen.value = false }
function escape(event) {
  if (!mobileOpen.value) return
  if (event.key === 'Escape') closeMobile()
  if (event.key === 'Tab') {
    const elements = sidebarElement.value?.querySelectorAll('a[href], button:not(:disabled), input:not(:disabled), [tabindex="0"]')
    if (!elements?.length) return
    const first = elements[0], last = elements[elements.length - 1]
    if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last.focus() }
    else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus() }
  }
}
watch(mobileOpen, async (open) => { if (open) { await nextTick(); sidebarElement.value?.querySelector('button')?.focus() } })
watch(() => route.fullPath, () => { if (mobileOpen.value) closeMobile() })
applyTheme()
onMounted(() => { window.addEventListener('resize', resize); window.addEventListener('keydown', escape); colorScheme.addEventListener('change', applyTheme) })
onUnmounted(() => { window.removeEventListener('resize', resize); window.removeEventListener('keydown', escape); colorScheme.removeEventListener('change', applyTheme) })
</script>
