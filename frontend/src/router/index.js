import { createRouter, createWebHistory } from 'vue-router'
import Chat from '../views/Chat.vue'
import KnowledgeBase from '../views/KnowledgeBase.vue'
import KnowledgeBaseDetail from '../views/KnowledgeBaseDetail.vue'
import Evaluation from '../views/Evaluation.vue'
import Assistant from '../views/Assistant.vue'
import Agent from '../views/Agent.vue'
import Monitor from '../views/Monitor.vue'

const routes = [
  { path: '/', redirect: '/chat' },
  { path: '/chat', component: Chat },
  { path: '/knowledge-bases', component: KnowledgeBase },
  { path: '/knowledge-bases/:id', component: KnowledgeBaseDetail },
  { path: '/evaluation', component: Evaluation },
  { path: '/assistants', component: Assistant },
  { path: '/agents', component: Agent },
  { path: '/monitor', component: Monitor },
  { path: '/:pathMatch(.*)*', redirect: '/chat' },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

export default router
