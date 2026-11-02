# KnowTrace

## 简介

KnowTrace 是一个基于RAG的知识库问答应用，支持文档上传与分块、向量检索、重排序、助手配置和自动评测。问答时可实时查看执行步骤、召回片段、重排前后排名、最终上下文及模型输入输出，执行记录随会话保存。

提供浅色与深色主题，默认支持 Windows 本地运行。

## 使用说明

### 安装与配置

准备 Python 3.11、Node.js 20 或更高版本，以及具备相应模型调用权限的阿里云百炼 DashScope API Key。在项目根目录执行：

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
npm --prefix frontend ci
Copy-Item .env.example .env
```

编辑 `.env`，填写自己的密钥。默认配置如下：

```dotenv
LOCAL_MODE=True
DASHSCOPE_API_KEY=填写自己的密钥
LLM_MODEL=qwen3.7-plus
LLM_ENABLE_THINKING=False
EMBEDDING_MODEL=qwen3.7-text-embedding
MILVUS_DIMENSION=1024
ENABLE_RERANK=True
RERANK_MODEL=qwen3.7-text-rerank
```

默认使用北京地域的 DashScope 网关。若业务空间要求专属地址，按控制台调用示例设置 `DASHSCOPE_HTTP_BASE_URL` 和 `DASHSCOPE_WORKSPACE_ID`。前者使用以 `/api/v1` 结尾的 DashScope 地址。模型调用需要联网，并按服务商规则计费。

### 启动与使用

双击 `start.bat`，或在项目根目录执行：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/start-local.ps1
```

打开 [应用页面](http://127.0.0.1:5173)，后端接口说明位于 [API 文档](http://127.0.0.1:8001/docs)。

1. 在“知识库”中新建知识库，上传 PDF、TXT、Markdown 或 DOCX，等待处理完成。
2. 在“智能问答”中选择知识库并提问；展开“执行过程”查看各步骤状态、文档片段和重排结果。
3. 在“助手”中配置知识库、提示词和检索参数，再开始对话。
4. 在“评测”中生成或上传问答数据集，运行评测并查看报告。

检索采用向量召回，可选多跳问题拆解和重排序，执行过程展示应用步骤及模型输入输出，不展示模型内部思维过程。

双击 `stop.bat` 停止服务。修改模型配置后需重启；更换嵌入模型或维度后，需重新处理已有文档。运行数据保存在 `data/` 和 `rag_system.db`，日志保存在 `logs/`。本应用无登录鉴权，适用于本机使用。

## 技术架构

```text
Vue 3 + Element Plus + Vite
           │ HTTP / SSE 执行状态
           ▼
FastAPI ─── SQLAlchemy ─── SQLite（业务数据与会话记录）
   │
   ├── 文档上传 → Celery Worker → 解析 → 分块 → 嵌入 → 向量存储
   │
   └── 问答 → 历史消息 → 问题拆解 → 向量召回 → 去重 → 重排序
                                                        │
                                 保存执行记录 ← 回答生成 ← 上下文组装
```

| 层级 | 实现 |
| --- | --- |
| 前端 | Vue 3、Vue Router、Element Plus、Vite，SSE 实时接收执行状态 |
| 后端 | FastAPI、Pydantic、SQLAlchemy |
| 文档处理 | PyMuPDF、pdfplumber、python-docx、LangChain 文本分块 |
| 本地服务 | SQLite 保存业务数据、向量、短期记忆、任务队列与结果；本地文件保存上传内容 |
| 模型调用 | DashScope SDK：`qwen3.7-plus` 回答、`qwen3.7-text-embedding` 嵌入、`qwen3.7-text-rerank` 重排 |
| 可选外部服务 | `LOCAL_MODE=False` 时使用 Milvus、MinIO、Redis、RabbitMQ，相关配置位于 `docker/` |
