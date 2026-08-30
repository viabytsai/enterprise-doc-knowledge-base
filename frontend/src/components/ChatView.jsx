import { useEffect, useRef, useState } from 'react'
import { BookOpenText, Bot, ChevronDown, ChevronUp, CornerDownLeft, FileText, LoaderCircle, Plus, Sparkles } from 'lucide-react'

const starters = ['差旅住宿标准是多少？', '发布生产环境前要完成哪些检查？', '试用期员工可以申请年假吗？']

export function ChatView({ onAsk, readyCount }) {
  const [messages, setMessages] = useState([])
  const [value, setValue] = useState('')
  const [loading, setLoading] = useState(false)
  const [conversationId, setConversationId] = useState(null)
  const bottomRef = useRef(null)

  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior: 'smooth' }) }, [messages])

  const submit = async (question = value) => {
    const clean = question.trim()
    if (!clean || loading || readyCount === 0) return
    setValue('')
    setLoading(true)
    setMessages((items) => [...items, { role: 'user', content: clean }, { role: 'assistant', content: '', citations: [], pending: true }])
    try {
      await onAsk(clean, conversationId, {
        meta: (data) => {
          setConversationId(data.conversation_id)
          setMessages((items) => updateLast(items, { citations: data.citations, toolTrace: data.tool_trace, agentMode: data.agent_mode }))
        },
        token: (data) => setMessages((items) => updateLast(items, { content: `${items.at(-1).content}${data.content}` })),
        done: (data) => setMessages((items) => updateLast(items, { pending: false, latency: data.latency_ms })),
        error: (data) => setMessages((items) => updateLast(items, { pending: false, error: data.message })),
      })
    } catch (error) {
      setMessages((items) => updateLast(items, { pending: false, error: error.message }))
    } finally {
      setLoading(false)
    }
  }

  const reset = () => { setMessages([]); setConversationId(null); setValue('') }

  return (
    <div className="chat-layout">
      <aside className="conversation-panel">
        <button className="secondary-button full" onClick={reset}><Plus size={17} />新建会话</button>
        <div className="conversation-label">今天</div>
        <button className="conversation-item active"><MessagePreview messages={messages} /></button>
        <div className="model-note"><Sparkles size={16} /><div><strong>知识库模式</strong><span>回答严格依据已入库资料</span></div></div>
      </aside>
      <section className="chat-main">
        <div className="message-list">
          {!messages.length ? (
            <div className="chat-empty">
              <span><BookOpenText size={26} /></span>
              <h2>从企业资料中找到可靠答案</h2>
              <p>{readyCount ? `当前有 ${readyCount} 份可用文档，回答会附带原文引用。` : '请先在知识库管理中上传文档。'}</p>
              <div className="starter-grid">
                {starters.map((item) => <button key={item} disabled={!readyCount} onClick={() => submit(item)}>{item}</button>)}
              </div>
            </div>
          ) : messages.map((message, index) => <Message key={index} message={message} />)}
          <div ref={bottomRef} />
        </div>
        <div className="composer-wrap">
          <div className="composer">
            <textarea value={value} onChange={(event) => setValue(event.target.value)} onKeyDown={(event) => { if (event.key === 'Enter' && !event.shiftKey) { event.preventDefault(); submit() } }} placeholder={readyCount ? '询问制度、流程或技术资料…' : '上传文档后即可提问'} disabled={!readyCount || loading} rows="1" />
            <button title="发送问题" disabled={!value.trim() || loading || !readyCount} onClick={() => submit()}>{loading ? <LoaderCircle size={18} className="spin" /> : <CornerDownLeft size={18} />}</button>
          </div>
          <small>回答由知识库资料生成，请通过引用原文核验重要结论。</small>
        </div>
      </section>
    </div>
  )
}

function updateLast(items, updates) {
  return items.map((item, index) => index === items.length - 1 ? { ...item, ...updates } : item)
}

function MessagePreview({ messages }) {
  return messages.find((item) => item.role === 'user')?.content || '新会话'
}

function Message({ message }) {
  const [expanded, setExpanded] = useState(false)
  if (message.role === 'user') return <div className="user-message">{message.content}</div>
  return (
    <article className="assistant-message">
      <span className="assistant-avatar"><Bot size={18} /></span>
      <div className="assistant-body">
        <div className="assistant-meta"><strong>知页助手</strong>{message.toolTrace?.length > 0 && <span className="agent-badge"><Bot size={11} />Agent · {message.toolTrace.find((item) => item.type === 'tool_call')?.name || '工具调用'}</span>}{message.latency && <span>{message.latency} ms</span>}</div>
        {message.error ? <p className="message-error">{message.error}</p> : <div className="answer-text">{message.content || '正在检索知识库…'}{message.pending && <i className="typing-cursor" />}</div>}
        {!!message.citations?.length && (
          <div className="citation-area">
            <button className="citation-toggle" onClick={() => setExpanded(!expanded)}><FileText size={16} />引用来源 · {message.citations.length}{expanded ? <ChevronUp size={15} /> : <ChevronDown size={15} />}</button>
            {expanded && <div className="citation-list">{message.citations.map((item) => <div className="citation" key={item.chunk_id}><div><span>[{item.index}]</span><strong>{item.file_name}</strong><small>{item.page_number ? `第 ${item.page_number} 页` : item.section_title || '原文片段'}</small></div><p>{item.content}</p></div>)}</div>}
          </div>
        )}
      </div>
    </article>
  )
}
