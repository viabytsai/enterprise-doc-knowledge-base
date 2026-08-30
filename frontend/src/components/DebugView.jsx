import { useState } from 'react'
import { ArrowDown, Check, FileSearch, LoaderCircle, Search } from 'lucide-react'

export function DebugView({ onDebug, readyCount }) {
  const [question, setQuestion] = useState('')
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const run = async () => {
    if (!question.trim() || loading) return
    setLoading(true); setError('')
    try { setResult(await onDebug(question.trim())) } catch (err) { setError(err.message) } finally { setLoading(false) }
  }

  return (
    <div className="debug-view">
      <section className="debug-query">
        <div><h2>测试检索链路</h2><p>输入问题后查看向量召回和 BGE 重排序结果</p></div>
        <div className="debug-input"><Search size={18} /><input value={question} onChange={(event) => setQuestion(event.target.value)} onKeyDown={(event) => event.key === 'Enter' && run()} placeholder="例如：出差住宿标准是多少？" disabled={!readyCount} /><button className="primary-button" disabled={!question.trim() || loading || !readyCount} onClick={run}>{loading ? <LoaderCircle className="spin" size={17} /> : <FileSearch size={17} />}运行检索</button></div>
        {error && <p className="message-error">{error}</p>}
      </section>
      {!result ? <div className="debug-empty"><FileSearch size={32} /><strong>{readyCount ? '等待检索问题' : '知识库暂无可用文档'}</strong><span>{readyCount ? '运行后将展示每个候选片段的排名与分数' : '请先上传并索引文档'}</span></div> : (
        <>
          <div className="debug-summary"><span>召回 <strong>{result.candidates.length}</strong> 个候选</span><ArrowDown size={16} /><span>选取 <strong>{result.selected_chunk_ids.length}</strong> 个上下文</span><span className="latency">{result.latency_ms} ms</span></div>
          <div className="result-columns">
            <ResultColumn title="向量召回" subtitle="bge-small-zh-v1.5 · Top 20" items={result.candidates} scoreKey="vector_score" selected={[]} />
            <ResultColumn title="重排序结果" subtitle="bge-reranker-v2-m3 · 精排" items={result.ranked} scoreKey="rerank_score" selected={result.selected_chunk_ids} />
          </div>
        </>
      )}
    </div>
  )
}

function ResultColumn({ title, subtitle, items, scoreKey, selected }) {
  return <section className="result-column"><header><div><h3>{title}</h3><p>{subtitle}</p></div><span>{items.length}</span></header><div className="result-list">{items.map((item, index) => <article key={item.id} className={selected.includes(item.id) ? 'result-item selected' : 'result-item'}><div className="result-head"><span className="rank">{index + 1}</span><div><strong>{item.file_name}</strong><small>{item.page_number ? `第 ${item.page_number} 页` : item.section_title || '原文片段'}</small></div>{selected.includes(item.id) && <span className="selected-mark"><Check size={13} />入选</span>}</div><p>{item.content}</p><div className="score-line"><span>{scoreKey === 'vector_score' ? '相似度' : '重排分'}</span><div><i style={{ width: `${Math.max(4, Math.min(100, Math.abs(item[scoreKey]) * 100))}%` }} /></div><strong>{Number(item[scoreKey] || 0).toFixed(3)}</strong></div></article>)}</div></section>
}

