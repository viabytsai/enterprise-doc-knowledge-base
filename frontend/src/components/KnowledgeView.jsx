import { useRef, useState } from 'react'
import { File, FileText, LoaderCircle, RefreshCw, Search, Trash2, UploadCloud } from 'lucide-react'

const statusMap = {
  ready: ['已就绪', 'success'],
  processing: ['处理中', 'processing'],
  failed: ['失败', 'danger'],
}

export function KnowledgeView({ documents, stats, onUpload, onDelete, onReindex, busy }) {
  const inputRef = useRef(null)
  const [dragging, setDragging] = useState(false)
  const [query, setQuery] = useState('')
  const filtered = documents.filter((doc) => doc.name.toLowerCase().includes(query.toLowerCase()))

  const handleFiles = (files) => {
    if (files?.[0]) onUpload(files[0])
  }

  return (
    <div className="view-stack">
      <section className="metrics-grid" aria-label="知识库统计">
        <div className="metric"><span>文档总数</span><strong>{stats.documents || 0}</strong><small>本地知识库文件</small></div>
        <div className="metric"><span>可用文档</span><strong>{stats.ready_documents || 0}</strong><small>已完成解析与索引</small></div>
        <div className="metric"><span>知识片段</span><strong>{stats.chunks || 0}</strong><small>用于语义检索</small></div>
      </section>

      <section
        className={dragging ? 'upload-zone dragging' : 'upload-zone'}
        onDragOver={(event) => { event.preventDefault(); setDragging(true) }}
        onDragLeave={() => setDragging(false)}
        onDrop={(event) => { event.preventDefault(); setDragging(false); handleFiles(event.dataTransfer.files) }}
      >
        <input ref={inputRef} type="file" accept=".pdf,.docx,.md,.txt" hidden onChange={(event) => handleFiles(event.target.files)} />
        <span className="upload-icon"><UploadCloud size={23} /></span>
        <div><strong>上传企业文档</strong><p>支持 PDF、DOCX、Markdown、TXT，单文件不超过 20 MB</p></div>
        <button className="primary-button" disabled={busy} onClick={() => inputRef.current?.click()}>
          {busy ? <LoaderCircle size={17} className="spin" /> : <UploadCloud size={17} />}
          {busy ? '正在处理' : '选择文件'}
        </button>
      </section>

      <section className="data-section">
        <div className="section-toolbar">
          <div><h2>文档列表</h2><p>{filtered.length} 项结果</p></div>
          <label className="search-field"><Search size={17} /><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="搜索文档名称" /></label>
        </div>
        <div className="table-shell">
          <table>
            <thead><tr><th>文档</th><th>状态</th><th>页/章节</th><th>知识片段</th><th>上传时间</th><th aria-label="操作" /></tr></thead>
            <tbody>
              {filtered.map((doc) => {
                const [label, tone] = statusMap[doc.status] || [doc.status, 'neutral']
                return (
                  <tr key={doc.id}>
                    <td><div className="document-name"><span><FileText size={18} /></span><div><strong>{doc.name}</strong><small>{doc.file_type.toUpperCase()}</small></div></div></td>
                    <td><span className={`status ${tone}`}><i />{label}</span>{doc.error_message && <small className="error-note">{doc.error_message}</small>}</td>
                    <td>{doc.page_count || '—'}</td>
                    <td>{doc.chunk_count || '—'}</td>
                    <td>{formatDate(doc.created_at)}</td>
                    <td><div className="row-actions"><button title="重建索引" onClick={() => onReindex(doc.id)}><RefreshCw size={16} /></button><button className="danger-action" title="删除文档" onClick={() => onDelete(doc)}><Trash2 size={16} /></button></div></td>
                  </tr>
                )
              })}
              {!filtered.length && <tr><td colSpan="6"><div className="empty-table"><File size={28} /><strong>暂无文档</strong><span>上传一份企业资料开始构建知识库</span></div></td></tr>}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  )
}

function formatDate(value) {
  if (!value) return '—'
  return new Intl.DateTimeFormat('zh-CN', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' }).format(new Date(value))
}

