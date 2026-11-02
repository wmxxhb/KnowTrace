<template>
  <details class="execution-trace" :open="expanded" @toggle="expanded = $event.target.open">
    <summary class="trace-heading"><UiIcon name="activity" :size="16" /><span>执行过程</span><span class="trace-state" :class="trace.status">{{ statusText(trace.status) }}</span><span v-if="trace.status !== 'running' && trace.duration_ms != null" class="trace-time">{{ duration(trace.duration_ms) }}</span><UiIcon class="trace-chevron" name="down" :size="14" /></summary>
    <div v-if="!trace.steps?.length" class="trace-waiting">正在连接服务</div>
    <ol class="trace-timeline" aria-label="问答执行步骤" aria-live="polite">
      <li v-for="step in trace.steps" :key="step.id" class="trace-node" :class="step.status">
        <details class="trace-step">
          <summary><span class="trace-dot" /><span class="trace-title">{{ step.title }}</span><span class="trace-state" :class="step.status">{{ statusText(step.status) }}</span><span v-if="step.duration_ms != null" class="trace-time">{{ duration(step.duration_ms) }}</span></summary>
          <div class="trace-step-body">
            <dl class="trace-facts"><template v-for="fact in facts(step)" :key="fact.label"><dt>{{ fact.label }}</dt><dd>{{ fact.value }}</dd></template></dl>
            <p v-if="step.message" class="trace-message">{{ step.message }}</p>
            <p v-if="step.error" class="trace-error">{{ step.error }}</p>
            <p v-if="step.output?.reason" class="trace-message">{{ step.output.reason }}</p>
            <ol v-if="step.output?.queries" class="trace-queries"><li v-for="(query, index) in step.output.queries" :key="index">{{ query }}</li></ol>
            <div v-if="step.output?.comparison?.length" class="trace-comparison">
              <p class="trace-score-hint">L2 距离越小越近；重排相关性越高越相关。未返回的分数不作推测。</p>
              <table><thead><tr><th>原排名</th><th>新排名</th><th>文档与片段</th><th>L2 距离</th><th>重排相关性</th><th>结果</th></tr></thead><tbody><tr v-for="doc in step.output.comparison" :key="doc.id" :class="{ 'trace-discarded': !doc.selected }"><td>{{ doc.rank_before }}</td><td>{{ doc.rank_after ?? '—' }}</td><td><details><summary>{{ sourceName(doc) }}</summary><p class="trace-chunk-id">片段 {{ doc.id }}</p><pre>{{ doc.text }}</pre></details></td><td>{{ score(doc.distance) }}</td><td>{{ score(doc.relevance) }}</td><td>{{ doc.selected ? '保留' : '未保留' }}</td></tr></tbody></table>
            </div>
            <div v-else-if="step.output?.candidates?.length" class="trace-candidates">
              <details v-for="doc in step.output.candidates" :key="doc.id" class="trace-document"><summary><span>{{ doc.rank }}.</span><span class="trace-source-name">{{ sourceName(doc) }}</span><span class="trace-document-score">{{ doc.metric === 'relevance' ? '相关性' : 'L2 距离' }} {{ score(doc.score) }}</span></summary><p class="trace-chunk-id">片段 {{ doc.id }}</p><pre>{{ doc.text }}</pre></details>
            </div>
            <p v-if="step.kind === 'retrieval' && step.status === 'completed' && step.output?.count === 0" class="trace-message">未检索到片段</p>
            <details v-if="step.output?.messages?.length" class="trace-text"><summary>实际读取的对话历史</summary><div v-for="(message, index) in step.output.messages" :key="index"><span class="trace-chunk-id">{{ message.role === 'user' ? '用户' : '助手' }}</span><pre>{{ message.content }}</pre></div></details>
            <details v-if="step.kind === 'context' && step.output" class="trace-text"><summary>实际使用的上下文</summary><pre>{{ step.output.context || '未使用历史或知识库上下文' }}</pre></details>
            <details v-if="step.input?.prompt" class="trace-text"><summary>发送给模型的输入</summary><p class="trace-chunk-id">系统指令</p><pre>{{ step.input.system_prompt }}</pre><p class="trace-chunk-id">用户输入与上下文</p><pre>{{ step.input.prompt }}</pre></details>
            <details v-if="step.output?.answer" class="trace-text"><summary>模型最终输出</summary><pre>{{ step.output.answer }}</pre></details>
          </div>
        </details>
      </li>
    </ol>
    <p v-if="trace.error" class="trace-error trace-final-error">{{ trace.error }}</p>
  </details>
</template>
<script setup>
import { ref } from 'vue'
import UiIcon from './UiIcon.vue'
const props = defineProps({ trace: { type: Object, required: true }, live: Boolean })
const expanded = ref(props.live)
const statusText = status => ({ running: '进行中', completed: '已完成', failed: '失败', degraded: '已降级', skipped: '已跳过', interrupted: '连接中断' })[status] || status
const duration = milliseconds => milliseconds < 1000 ? `${milliseconds} ms` : `${(milliseconds / 1000).toFixed(2)} s`
const score = value => Number.isFinite(value) ? value.toFixed(4) : '—'
function sourceName(doc) {
  const metadata = doc.metadata || {}
  const page = metadata.page ?? metadata.page_num
  return `${metadata.filename || metadata.file_name || '文档'}${page != null && page > 0 ? ` · 第 ${page} 页` : ''}`
}
function facts(step) {
  const input = step.input || {}, output = step.output || {}
  const values = { model: input.model || output.model, query: input.query, method: input.method || output.method,
    storage: input.storage, mode: output.mode, dimension: output.dimension ?? input.dimension,
    kb_ids: input.kb_ids || output.kb_ids, top_k: input.top_k ?? output.top_k,
    top_n: input.top_n ?? output.rerank_top_n, temperature: input.temperature,
    thinking: input.thinking == null ? undefined : input.thinking ? '开启' : '关闭',
    rerank_enabled: output.rerank_enabled == null ? undefined : output.rerank_enabled ? '开启' : '关闭',
    input_count: input.count, count: output.count, characters: output.characters,
    first_token: output.first_token_latency == null ? undefined : duration(Math.round(output.first_token_latency * 1000)),
    total: output.total_latency == null ? undefined : duration(Math.round(output.total_latency * 1000)) }
  const labels = { model: '模型', query: '查询', method: '检索方式', storage: '向量存储', mode: '执行方式', dimension: '向量维度', kb_ids: '知识库 ID', top_k: '召回上限', top_n: '保留上限', temperature: '温度', thinking: '思考模式', rerank_enabled: '重排序', input_count: '输入片段数', count: step.kind === 'memory' || step.kind === 'memory_write' ? '消息数' : '输出片段数', characters: '输出字数', first_token: '首字耗时', total: '生成耗时' }
  return Object.entries(values).filter(([, value]) => value != null && (!Array.isArray(value) || value.length)).map(([key, value]) => ({ label: labels[key], value: Array.isArray(value) ? value.join('、') : value }))
}
</script>
<style scoped>
.execution-trace { border: 1px solid var(--line); border-radius: var(--radius); margin-top: var(--space-4); font-size: var(--text-sm); color: var(--text-secondary); background: var(--surface); }
.trace-heading { display: flex; align-items: center; gap: var(--space-2); padding: var(--space-3); cursor: pointer; list-style: none; user-select: none; }
summary::-webkit-details-marker { display: none; }
.trace-heading:hover { background: var(--surface-secondary); border-radius: var(--radius); }
.trace-chevron { margin-left: auto; }
.execution-trace[open] > summary .trace-chevron { transform: rotate(180deg); }
.trace-time { color: var(--text-muted); white-space: nowrap; font-size: var(--text-xs); font-variant-numeric: tabular-nums; }
.trace-state { font-size: var(--text-xs); white-space: nowrap; color: var(--text-muted); }
.trace-state.failed, .trace-error { color: var(--danger); }
.trace-state.degraded { color: var(--warning); }
.trace-state.running { color: var(--text); }
.trace-timeline { list-style: none; margin: 0; padding: var(--space-2) var(--space-4) var(--space-3); }
.trace-node { border-left: 1px solid var(--line); padding-left: var(--space-4); position: relative; }
.trace-node:last-child { border-left-color: transparent; }
.trace-step > summary { display: flex; gap: var(--space-2); align-items: center; padding: var(--space-2) 0; cursor: pointer; list-style: none; }
.trace-title { color: var(--text); flex: 1; }
.trace-dot { position: absolute; left: -4px; width: 7px; height: 7px; border-radius: 50%; background: var(--text-secondary); }
.trace-node.running .trace-dot { outline: 3px solid var(--selected); }
.trace-node.failed .trace-dot { background: var(--danger); }
.trace-node.degraded .trace-dot { background: var(--warning); }
.trace-node.skipped .trace-dot { background: var(--surface); border: 1px solid var(--border); }
.trace-step-body { padding: var(--space-2) 0 var(--space-4); min-width: 0; }
.trace-facts { margin: 0; display: grid; grid-template-columns: max-content minmax(0, 1fr); gap: var(--space-1) var(--space-4); }
.trace-facts dt { color: var(--text-muted); }
.trace-facts dd { margin: 0; color: var(--text); white-space: pre-wrap; overflow-wrap: anywhere; }
.trace-message, .trace-error { margin-top: var(--space-2); white-space: pre-wrap; overflow-wrap: anywhere; }
.trace-queries { margin: var(--space-3) 0; padding-left: var(--space-5); }
.trace-candidates, .trace-comparison, .trace-text { margin-top: var(--space-3); }
.trace-document { padding: var(--space-2) 0; border-bottom: 1px solid var(--line); }
.trace-document > summary { display: flex; gap: var(--space-2); cursor: pointer; }
.trace-source-name { min-width: 0; flex: 1; overflow-wrap: anywhere; color: var(--text); }
.trace-document-score { white-space: nowrap; font-variant-numeric: tabular-nums; }
.trace-chunk-id { font-size: var(--text-xs); color: var(--text-muted); margin-top: var(--space-2); overflow-wrap: anywhere; }
pre { font: inherit; white-space: pre-wrap; overflow-wrap: anywhere; margin: var(--space-2) 0 0; padding: var(--space-3); background: var(--surface-secondary); border-radius: var(--radius-sm); color: var(--text); line-height: 1.65; }
.trace-score-hint { color: var(--text-muted); font-size: var(--text-xs); margin-bottom: var(--space-2); }
.trace-comparison { overflow-x: auto; }
table { width: 100%; min-width: 580px; border-collapse: collapse; font-size: var(--text-xs); }
th, td { padding: var(--space-2); text-align: left; vertical-align: top; border-bottom: 1px solid var(--line); }
th { font-weight: var(--weight-medium); white-space: nowrap; }
td:nth-child(3) { min-width: 160px; }
.trace-discarded { color: var(--text-muted); }
.trace-comparison summary, .trace-text > summary { cursor: pointer; color: var(--text); }
.trace-waiting, .trace-final-error { padding: var(--space-3); }
@media (max-width: 767px) { .trace-timeline { padding-left: var(--space-3); padding-right: var(--space-3); } .trace-facts { gap: var(--space-1) var(--space-2); } .trace-document > summary { flex-wrap: wrap; } .trace-document-score { width: 100%; padding-left: var(--space-4); } }
</style>
