import { createApp, h } from 'vue'
import ElementPlus from 'element-plus'
import zhCn from 'element-plus/es/locale/lang/zh-cn'
import 'element-plus/dist/index.css'
import * as ElementPlusIconsVue from '@element-plus/icons-vue'
import App from './App.vue'
import UiIcon from './components/UiIcon.vue'
import './styles/workspace.css'
import router from './router'
import { createPinia } from 'pinia'

const app = createApp(App)

const iconNames = { Menu: 'panel', ChatDotRound: 'chat', Document: 'file', Folder: 'folder', User: 'assistant', Cpu: 'layers', Monitor: 'monitor', DataAnalysis: 'chart', Plus: 'plus', Edit: 'edit', Delete: 'trash', Upload: 'upload', UploadFilled: 'upload', Download: 'download', Back: 'back', Refresh: 'refresh', RefreshRight: 'refresh', Position: 'arrow', Search: 'search', Close: 'close', Check: 'check', ArrowDown: 'down', More: 'more', Setting: 'settings' }
for (const [key, component] of Object.entries(ElementPlusIconsVue)) {
  app.component(key, iconNames[key] ? { render: () => h(UiIcon, { name: iconNames[key], size: 18 }) } : component)
}

app.use(createPinia())
app.use(router)
app.use(ElementPlus, { locale: zhCn })
app.mount('#app')
