# 企业文档知识库

面向企业制度、流程和技术文档的本地 Agentic RAG 应用。系统支持多格式文档导入、512 维中文嵌入、候选片段重排序、LangGraph 工具编排、引用溯源、无依据拒答和检索调试。

## 当前功能

- 上传并解析 PDF、DOCX、Markdown、TXT。
- 按标题、页面和语义边界分块，保留来源元数据。
- 使用 `BAAI/bge-small-zh-v1.5` 嵌入与 `BAAI/bge-reranker-v2-m3` 重排序。
- 使用 LangGraph 构建 `Agent -> ToolNode -> Agent -> END` 有状态工作流，提供知识检索、原文获取、文档列表和文档内容工具。
- Chroma 本地持久化；未安装 ML 依赖时自动使用 SQLite + 512 维哈希嵌入进行演示。
- 调用兼容 OpenAI Chat Completions 的 LLM API；未配置 Key 时使用可追溯的抽取式演示回答。
- React 工作台：知识库管理、智能问答、检索调试。

## 本地启动

推荐使用 Python 3.11 至 3.13 安装完整 ML 依赖；Python 3.14 可以运行核心与演示模式，但部分 PyTorch/Chroma 版本可能尚无可用 wheel。

```bash
cp .env.example .env

python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements-dev.txt

# 正式 BGE、Chroma 和 LangGraph API 模式
pip install -r backend/requirements-ml.txt

cd frontend
npm install
```

分别启动后端和前端：

```bash
source .venv/bin/activate
cd backend
uvicorn app.main:app --reload --port 8000
```

```bash
cd frontend
npm run dev
```

访问 `http://localhost:5173`。API 文档位于 `http://localhost:8000/docs`。

## 启用正式 RAG 模型

在 Python 3.11 至 3.13 环境中执行：

```bash
pip install -r backend/requirements-ml.txt
```

然后在 `.env` 中设置：

```dotenv
MODEL_MODE=full
VECTOR_STORE=chroma
```

首次索引时会下载 `bge-small-zh-v1.5` 和 `bge-reranker-v2-m3`。模型准备完成后，`GET /api/health` 会显示实际启用的 embedding、reranker、vector store、LLM 与 Agent 模式。

## 配置 LLM API

在 `.env` 填写兼容 OpenAI 协议的服务地址、模型和密钥：

```dotenv
LLM_BASE_URL=https://api.openai.com/v1
LLM_MODEL=gpt-4.1-mini
LLM_API_KEY=your-key
```

API Key 只由后端读取，不会发送到前端或写入业务日志。

## Agent 工作流

LangGraph 负责状态和循环，LangChain Tools 负责工具定义，现有 `rag.py` 负责检索实现：

```text
用户问题
  -> Agent 节点判断是否需要工具
  -> ToolNode 执行 search_knowledge / get_source 等工具
  -> Agent 节点根据工具结果继续判断
  -> 最终回答与引用
```

没有配置 `LLM_API_KEY` 时，Agent 仍会通过 LangGraph 的演示节点调用 `search_knowledge`，并返回抽取式回答；配置支持 Tool Calling 的 OpenAI-compatible API 后，切换为真实 Agent 决策。

## 验证

```bash
source .venv/bin/activate
cd backend
pytest

cd ../frontend
npm run build
```

仓库中的 `examples/` 提供两份模拟企业资料，可用于验证上传、问答、引用和重排序流程。

产品需求见 [docs/PRD.md](docs/PRD.md)。
