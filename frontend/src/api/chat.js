export async function streamChat(payload, onTrace) {
  const response = await fetch('/api/v1/chat/stream', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
  if (!response.ok) {
    const body = await response.json().catch(() => ({}))
    const error = new Error(typeof body.detail === 'string' ? body.detail : body.detail?.message || '请求失败')
    error.requestFailed = true
    throw error
  }
  if (!response.body) throw new Error('当前浏览器不支持读取执行过程')
  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''
  try {
    while (true) {
      const { done, value } = await reader.read()
      buffer += decoder.decode(value, { stream: !done })
      let boundary
      while ((boundary = buffer.indexOf('\n\n')) >= 0) {
        const frame = buffer.slice(0, boundary)
        buffer = buffer.slice(boundary + 2)
        const data = frame.split('\n').filter(line => line.startsWith('data:')).map(line => line.slice(5).trimStart()).join('\n')
        if (!data) continue
        const event = JSON.parse(data)
        if (event.type === 'trace') onTrace?.(event.trace)
        if (event.type === 'complete') return event.result
        if (event.type === 'error') {
          const error = new Error(event.message || '问答执行失败')
          error.requestFailed = true
          error.executionTrace = event.execution_trace
          error.sessionId = event.session_id
          throw error
        }
      }
      if (done) throw new Error('执行过程连接已中断，请在历史对话中查看结果')
    }
  } finally {
    await reader.cancel().catch(() => {})
    reader.releaseLock()
  }
}
