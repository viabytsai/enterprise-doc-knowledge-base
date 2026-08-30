const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api'

async function request(path, options = {}) {
  const response = await fetch(`${API_BASE}${path}`, options)
  if (!response.ok) {
    let message = '请求失败'
    try {
      const body = await response.json()
      message = body.detail || message
    } catch {
      message = response.statusText || message
    }
    throw new Error(message)
  }
  if (response.status === 204) return null
  return response.json()
}

export const api = {
  health: () => request('/health'),
  stats: () => request('/stats'),
  documents: () => request('/documents'),
  upload: (file) => {
    const data = new FormData()
    data.append('file', file)
    return request('/documents', { method: 'POST', body: data })
  },
  removeDocument: (id) => request(`/documents/${id}`, { method: 'DELETE' }),
  reindexDocument: (id) => request(`/documents/${id}/reindex`, { method: 'POST' }),
  debug: (question, topK = 20) => request('/retrieval/debug', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ question, top_k: topK }),
  }),
  streamChat: async (question, conversationId, handlers) => {
    const response = await fetch(`${API_BASE}/chat/stream`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ question, conversation_id: conversationId }),
    })
    if (!response.ok || !response.body) throw new Error('问答服务暂时不可用')
    const reader = response.body.getReader()
    const decoder = new TextDecoder()
    let buffer = ''
    while (true) {
      const { value, done } = await reader.read()
      if (done) break
      buffer += decoder.decode(value, { stream: true })
      const packets = buffer.split('\n\n')
      buffer = packets.pop() || ''
      for (const packet of packets) {
        let event = 'message'
        let data = null
        for (const line of packet.split('\n')) {
          if (line.startsWith('event: ')) event = line.slice(7)
          if (line.startsWith('data: ')) data = JSON.parse(line.slice(6))
        }
        if (data) handlers[event]?.(data)
      }
    }
  },
}

