import { createElement } from 'react'
import { BookOpen, Database, MessageSquareText, SearchCode, Settings2 } from 'lucide-react'

const navItems = [
  { id: 'knowledge', label: '知识库管理', icon: Database },
  { id: 'chat', label: '智能问答', icon: MessageSquareText },
  { id: 'debug', label: '检索调试', icon: SearchCode },
]

export function Sidebar({ active, onChange, stats }) {
  return (
    <aside className="sidebar">
      <div className="brand">
        <span className="brand-mark"><BookOpen size={20} /></span>
        <div><strong>知页</strong><span>企业知识库</span></div>
      </div>
      <nav className="nav-list" aria-label="主导航">
        {navItems.map((item) => (
          <button key={item.id} className={active === item.id ? 'nav-item active' : 'nav-item'} onClick={() => onChange(item.id)}>
            {createElement(item.icon, { size: 18 })}
            <span>{item.label}</span>
          </button>
        ))}
      </nav>
      <div className="sidebar-summary">
        <span>当前知识库</span>
        <strong>{stats.ready_documents || 0} 份文档</strong>
        <small>{stats.chunks || 0} 个可检索片段</small>
      </div>
      <button className="nav-item settings" title="系统设置尚未开放">
        <Settings2 size={18} /><span>系统设置</span>
      </button>
    </aside>
  )
}
