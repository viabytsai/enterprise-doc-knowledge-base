# 企业文档知识库

一个面向企业制度、流程和技术文档的本地 Agentic RAG 应用。它把文档管理、语义检索、重排序和可追溯问答放在同一个工作台中，适合在本地验证企业知识库、RAG 检索链路和 LangGraph Agent 工作流。

## 特性

- 支持上传和解析 PDF、DOCX、Markdown、TXT 文档。
- 按标题、页面和语义边界切分文档，并保留来源、页码和段落元数据。
- 使用 `BAAI/bge-small-zh-v1.5` 中文向量模型和 `BAAI/bge-reranker-v2-m3` 重排序模型。
- 使用 LangGraph 编排 `Agent -> ToolNode -> Agent -> END` 工作流。
- 内置 `search_knowledge`、`get_source`、文档列表和原文获取工具。
- 支持 Chroma 向量存储；未安装机器学习依赖时自动回退到 SQLite + 512 维哈希嵌入演示模式。
- 支持兼容 OpenAI Chat Completions 协议的 LLM 服务；没有 API Key 时仍可使用可追溯的抽取式演示回答。
- React 工作台提供知识库管理、流式问答、引用展示和检索调试。
- 所有文档和索引默认保存在本地 `data/` 目录，不依赖云端数据库。

## 技术栈

| 层次 | 技术 |
| --- | --- |
| 前端 | React 19、Vite、Lucide React |
| API | FastAPI、Uvicorn |
| Agent | LangGraph、LangChain Core、LangChain OpenAI |
| 文档解析 | pypdf、python-docx、Markdown/TXT 原生解析 |
| 检索 | BGE Embedding、BGE Reranker、Chroma / SQLite |
| 持久化 | SQLite（文档、分块、会话与消息） |

## 快速开始

### 环境要求

- Python 3.11–3.13：推荐用于完整机器学习模式。
- Python 3.14：可以运行核心功能和演示模式，但部分 PyTorch/Chroma 版本可能暂未提供对应 wheel。
- Node.js 18+ 和 npm。

### 1. 安装后端

```bash
cp .env.example .env

python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements-dev.txt
```

启动 API 服务：

```bash
cd backend
uvicorn app.main:app --reload --port 8000
```

后端地址：`http://localhost:8000`  
Swagger API 文档：`http://localhost:8000/docs`  
健康检查：`http://localhost:8000/api/health`

### 2. 安装并启动前端

在另一个终端执行：

```bash
cd frontend
npm install
npm run dev
```

打开 `http://localhost:5173`，即可使用知识库管理、智能问答和检索调试页面。前端默认请求 `http://localhost:8000/api`；如需修改，可设置 `VITE_API_BASE_URL`。

## 模型模式

项目默认使用 `MODEL_MODE=auto`：检测到本地模型和相关依赖时启用完整 RAG，否则自动回退到轻量演示模式。

### 演示模式

适合快速体验和运行测试，不下载大模型：

```dotenv
MODEL_MODE=demo
VECTOR_STORE=sqlite
```

### 完整 RAG 模式

在 Python 3.11–3.13 环境中安装机器学习依赖：

```bash
pip install -r backend/requirements-ml.txt
```

然后在 `.env` 中启用：

```dotenv
MODEL_MODE=full
VECTOR_STORE=chroma
```

首次索引文档时会下载 `BAAI/bge-small-zh-v1.5` 和 `BAAI/bge-reranker-v2-m3`。模型加载状态可通过 `/api/health` 查看。

## 配置 LLM

项目支持所有兼容 OpenAI Chat Completions 协议的服务。在 `.env` 中填写：

```dotenv
LLM_BASE_URL=https://api.openai.com/v1
LLM_MODEL=gpt-4.1-mini
LLM_API_KEY=your-key
```

`LLM_API_KEY` 只由后端读取，不会发送到浏览器，也不会写入业务日志。未配置 Key 时，Agent 会使用本地检索结果生成抽取式演示回答。

## Agent 工作流

```text
用户问题
  -> Agent 判断是否需要检索
  -> ToolNode 执行 search_knowledge / get_source 等工具
  -> Agent 综合工具结果并生成答案
  -> 返回答案、引用、工具轨迹和耗时
```

当检索结果不足以支持回答时，系统会保留引用依据并拒绝无依据扩展，避免把模型猜测当成企业制度。

## API 概览

| 方法 | 路径 | 用途 |
| --- | --- | --- |
| `GET` | `/api/health` | 查看 embedding、reranker、向量库、LLM 和 Agent 模式 |
| `GET` | `/api/stats` | 查看文档、就绪文档和分块数量 |
| `GET` | `/api/documents` | 列出已上传文档 |
| `POST` | `/api/documents` | 上传并索引文档 |
| `POST` | `/api/documents/{id}/reindex` | 重建文档索引 |
| `DELETE` | `/api/documents/{id}` | 删除文档及索引 |
| `POST` | `/api/retrieval/debug` | 查看候选片段、重排序结果和延迟 |
| `POST` | `/api/chat/stream` | 以 Server-Sent Events 流式返回问答结果 |

完整请求和响应格式请打开 `/docs` 查看。

## 验证

运行后端测试：

```bash
source .venv/bin/activate
cd backend
pytest
```

检查前端构建和代码规范：

```bash
cd frontend
npm run lint
npm run build
```

仓库中的 `examples/` 提供两份模拟企业资料，可直接上传验证文档解析、问答、引用和重排序流程。

## 项目结构

```text
backend/
  app/
    agent/       LangGraph Agent 与工具
    api/         FastAPI 路由
    core/        配置与 SQLite 初始化
    services/    解析、嵌入、检索、重排序和 LLM 服务
  tests/         后端测试
frontend/
  src/
    components/  知识库、问答、调试和布局组件
    lib/          后端 API 客户端
data/
  uploads/       上传文档（运行时生成）
  chroma/        Chroma 索引（运行时生成）
docs/            产品需求文档
examples/        示例企业文档
```

## 数据与安全

- `.env`、本地数据库、上传文件、Chroma 索引和模型缓存默认不会提交到 Git。
- 生产环境请使用独立的密钥管理方案，并限制 API 服务的网络访问范围。
- 这是一个本地验证项目，未内置用户认证、权限管理或多租户隔离，不建议直接暴露到公网。

## 许可

当前仓库未附带许可证文件。公开使用或二次分发前，请先补充适合项目的 License。

产品需求和设计说明见 [docs/PRD.md](docs/PRD.md)。
