import { CircleHelp, Server } from 'lucide-react'

const titles = {
  knowledge: ['知识库管理', '维护企业制度、流程与技术资料'],
  chat: ['智能问答', '从已入库资料中检索并生成有引用的回答'],
  debug: ['检索调试', '检查向量召回、重排序与最终上下文'],
}

export function Topbar({ active, health }) {
  const [title, subtitle] = titles[active]
  const isReady = health?.status === 'ok'
  return (
    <header className="topbar">
      <div>
        <h1>{title}</h1>
        <p>{subtitle}</p>
      </div>
      <div className="top-actions">
        <span className={isReady ? 'service-state online' : 'service-state'}>
          <Server size={15} />{isReady ? '服务正常' : '连接中'}
        </span>
        <button className="icon-button" title="帮助"><CircleHelp size={19} /></button>
      </div>
    </header>
  )
}

