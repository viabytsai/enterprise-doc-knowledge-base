import { useCallback, useEffect, useState } from 'react'
import { X } from 'lucide-react'
import { api } from './lib/api'
import { Sidebar } from './components/Sidebar'
import { Topbar } from './components/Topbar'
import { KnowledgeView } from './components/KnowledgeView'
import { ChatView } from './components/ChatView'
import { DebugView } from './components/DebugView'

export default function App() {
  const [active, setActive] = useState('knowledge')
  const [documents, setDocuments] = useState([])
  const [stats, setStats] = useState({})
  const [health, setHealth] = useState(null)
  const [busy, setBusy] = useState(false)
  const [notice, setNotice] = useState(null)

  const refresh = useCallback(async () => {
    try {
      const [documentData, statData, healthData] = await Promise.all([api.documents(), api.stats(), api.health()])
      setDocuments(documentData); setStats(statData); setHealth(healthData)
    } catch (error) { setNotice({ tone: 'error', message: `无法连接后端：${error.message}` }) }
  }, [])

  useEffect(() => { refresh() }, [refresh])

  const upload = async (file) => {
    setBusy(true)
    try { await api.upload(file); setNotice({ tone: 'success', message: `${file.name} 已完成解析与索引` }); await refresh() }
    catch (error) { setNotice({ tone: 'error', message: error.message }) }
    finally { setBusy(false) }
  }

  const remove = async (document) => {
    if (!window.confirm(`确认删除“${document.name}”及其全部索引吗？`)) return
    try { await api.removeDocument(document.id); setNotice({ tone: 'success', message: '文档已删除' }); await refresh() }
    catch (error) { setNotice({ tone: 'error', message: error.message }) }
  }

  const reindex = async (id) => {
    setBusy(true)
    try { await api.reindexDocument(id); setNotice({ tone: 'success', message: '索引已重建' }); await refresh() }
    catch (error) { setNotice({ tone: 'error', message: error.message }) }
    finally { setBusy(false) }
  }

  return (
    <div className="app-shell">
      <Sidebar active={active} onChange={setActive} stats={stats} />
      <main className="workspace">
        <Topbar active={active} health={health} />
        <div className={active === 'chat' ? 'content-area chat-content' : 'content-area'}>
          {active === 'knowledge' && <KnowledgeView documents={documents} stats={stats} onUpload={upload} onDelete={remove} onReindex={reindex} busy={busy} />}
          {active === 'chat' && <ChatView onAsk={api.streamChat} readyCount={stats.ready_documents || 0} />}
          {active === 'debug' && <DebugView onDebug={api.debug} readyCount={stats.ready_documents || 0} />}
        </div>
      </main>
      {notice && <div className={`toast ${notice.tone}`}><span>{notice.message}</span><button title="关闭" onClick={() => setNotice(null)}><X size={16} /></button></div>}
    </div>
  )
}

