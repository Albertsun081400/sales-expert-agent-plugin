# Sales-Expert Plugin — 实施计划 & 进度追踪

> 文档版本：v0.1（起草）  
> 创建日期：2025-03-29  
> 负责人：Albert Sun  
> 状态：🔴 未启动

---

## 一、项目背景 & 目标

### 1.1 为什么做这个

Sales-Expert-Agent 是已有 FastAPI 后端（8000端口），管理 ChromaDB 向量库。当前 Agent 代码里的 `/api/chat` 端点直接调用本地 `memory_store.search()`。

DeerFlow 是独立运行的多 Agent RAG 系统（LangGraph + 2024端口），需要访问 Sales-Expert-Agent 的向量检索能力，但**不能直接 import 对方代码**（跨进程）。

### 1.2 解决方案

```
DeerFlow Agent
    │
    │  curl /api/v1/retrieve
    ▼
Sales-Expert Plugin (8080)          ← 新建项目
    │
    │  HTTP GET/POST
    ▼
Sales-Expert-Agent (8000)           现有服务
    │
    ▼
ChromaDB (向量库)
```

- **Plugin 项目**：thin HTTP wrapper，不持有 ChromaDB，只转发请求
- **DeerFlow Skill**：`skills/custom/sales-expert/SKILL.md`，指导 agent 用 curl 调用

### 1.3 交付目标

| 里程碑 | 内容 | 状态 |
|--------|------|------|
| M1 | Plugin 服务完成 `/api/v1/retrieve` + `/api/v1/sync` | ✅ 完成 |
| M2 | Plugin 服务 Docker 化，可独立部署 | 🔄 待办 |
| M3 | DeerFlow skill 完成，agent 可调用 | ✅ 完成 |
| M4 | 联调测试：DeerFlow → Plugin → Agent → ChromaDB | 🔄 待办 |
| M5 | 云端部署验证 | 🔄 待办 |

---

## 二、系统架构

### 2.1 整体拓扑

```
                         ┌─────────────────────────────────────┐
                         │           DeerFlow 服务               │
                         │  LangGraph (2024)  +  Gateway (8001)  │
                         │                                       │
  团队成员浏览器 ────────▶│  Lead Agent                            │
                         │    │                                   │
                         │    └── skills/custom/sales-expert/    │
                         │           SKILL.md (curl 调用方式)    │
                         └──────────────┬────────────────────────┘
                                        │ HTTP POST /api/v1/*
                                        │ curl
                                        ▼
                         ┌─────────────────────────────────────┐
                         │   Sales-Expert Plugin (8080)         │
                         │   FastAPI — thin HTTP wrapper        │
                         │   独立 Docker 容器                    │
                         └──────────────┬────────────────────────┘
                                        │ HTTP GET/POST
                                        │ X-Tenant-ID header
                                        ▼
                         ┌─────────────────────────────────────┐
                         │   Sales-Expert-Agent (8000)         │
                         │   现有服务，含 memory_store.search() │
                         │   ChromaDB 连接                       │
                         └─────────────────────────────────────┘
```

### 2.2 API 规格

#### POST /api/v1/retrieve
**用途**：混合检索（vector + BM25 + rerank）

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `query` | string | ✅ | — | 检索query |
| `top_k` | int | ❌ | 4 | 返回条数 |
| `customer_filter` | string | ❌ | null | 按客户名过滤 |
| `collection_type` | string | ❌ | "private" | private 或 global |

**响应**：
```json
{
  "results": "**file.md** [客户名]\n片段内容\n\n---\n\n...",
  "query": "...",
  "count": 2
}
```

#### POST /api/v1/sync
**用途**：写入对话 + 客户档案到 ChromaDB

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `conversations` | array | ❌ | 消息轮次列表 |
| `profiles` | array | ❌ | 客户档案列表 |
| `session_id` | string | ❌ | 会话ID |
| `customer_name` | string | ❌ | 客户姓名（应用于所有轮次） |

**响应**：
```json
{
  "status": "ok",
  "messages_stored": 5,
  "profiles_stored": 2
}
```

#### GET /health
**用途**：健康检查

**响应**：`{"status": "ok"}`

### 2.3 Header 规范

| Header | 值 | 说明 |
|--------|----|------|
| `X-Tenant-ID` | string | 租户层级凭证 (Scoped ID)，格式：`{tenant_id}/{user_id}`。默认 `default` |
| `Content-Type` | application/json | POST 请求必须 |

### 2.4 多租户隔离

- Plugin 在 HTTP 层转发 `X-Tenant-ID` 到 Agent
- Agent 内部用 `{tenant_id}` 作为 ChromaDB collection 前缀
- Plugin 本身不维护任何持久状态（无状态设计）

---

## 三、项目结构

```
Workers/
├── sales-expert-plugin/                    ← ★ 新建独立项目
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py          # FastAPI 入口，端点定义
│   │   ├── schemas.py        # Pydantic 模型
│   │   ├── memory_store.py   # RemoteMemoryStore，HTTP 转发
│   │   └── config.py          # 环境变量读取
│   ├── Dockerfile             # Python 3.11-slim 镜像
│   ├── docker-compose.yml     # 端口 8080，连接 host.docker.internal:8000
│   ├── requirements.txt       # fastapi, uvicorn, httpx, pydantic, python-dotenv
│   ├── .env.example           # SALES_EXPERT_BASE_URL, PLUGIN_TIMEOUT_SECONDS
│   └── README.md              # 部署说明
│
└── deer-flow-fresh/
    └── skills/
        └── custom/
            └── sales-expert/              ← ★ 新建 DeerFlow Skill
                ├── SKILL.md               # 完整调用文档 + curl 示例
                └── references/            # 预留，后续可放 API schema 文件
```

---

## 四、任务分解 & 进度

### 4.1 任务看板

| # | 任务 | 负责人 | 状态 | 备注 |
|---|------|--------|------|------|
| T1 | 确认父服务 Agent API 规格 | 待定 | 🔄 待确认 | `/api/v1/retrieve` 和 `/api/v1/sync` 是否已在 Agent 实现？ |
| T2 | Plugin 服务本地联调 | 待定 | 🔄 待办 | 启动 Plugin → 手动 curl 测试两个端点 |
| T3 | Plugin Docker 化验证 | 待定 | 🔄 待办 | `docker compose up --build` 是否正常 |
| T4 | DeerFlow skill 安装验证 | 待定 | 🔄 待办 | DeerFlow 重启后 skill 是否出现在 `/api/skills` |
| T5 | 端到端联调（DeerFlow → Plugin → Agent → ChromaDB） | 待定 | 🔄 待办 | 真实用户 query 跑一遍完整链路 |
| T6 | 云端部署方案设计 | 待定 | 🔄 待办 | docker-compose 云端配置、域名、CORS |
| T7 | 监控 & 日志规范 | 待定 | 🔄 待办 | Plugin 日志、错误告警 |

### 4.2 关键技术验证点

```
T1 ──▶ 确认 Agent 侧 /api/v1/retrieve 是否已实现
        └── [未实现] 需要先在 Agent 项目补充这两个端点
        └── [已实现] Plugin 可直接对接

T2 ──▶ Plugin 启动 + curl 测试
        curl -X POST http://localhost:8080/api/v1/retrieve \
          -H "Content-Type: application/json" \
          -d '{"query": "如何应对客户压价", "top_k": 3}'
        └── 期望：返回向量检索结果

T3 ──▶ Docker 网络验证
        docker compose up -d
        docker logs sales-expert-plugin
        └── 期望：启动成功，8080 端口监听

T4 ──▶ DeerFlow Skill 注册
        重启 DeerFlow langgraph 服务
        GET /api/skills 确认 sales-expert 出现
        └── 期望：skill 列表包含 sales-expert

T5 ──▶ 完整链路测试
        在 DeerFlow web UI 输入销售相关问题
        观察 DeerFlow 是否正确调用 skill 并使用检索结果
```

---

## 五、T1 详细说明（关键卡点）

**T1 是所有后续步骤的前置依赖。**

### 问题：Agent 侧 `/api/v1/retrieve` 是否已实现？

**现状分析：**
- Agent 项目的 `app/agent/memory_store.py` 中有 `search()` 方法（Hybrid Search）
- 但 `app/main.py` 中**没有**对应的 `POST /api/v1/retrieve` HTTP 端点
- 现有端点是 `@app.post("/api/chat")` → 内部调用 `agent.run()`

### 两种可能的实现路径

#### 路径 A（推荐）：父服务直接暴露 /api/v1/*
```
在 Sales-Expert-Agent 项目 app/main.py 中新增：
  POST /api/v1/retrieve    → 调用 memory_store.search()
  POST /api/v1/sync        → 调用 memory_store.add_documents()

Plugin 项目：http://localhost:8080 → http://host.docker.internal:8000
```

#### 路径 B：Plugin 作为 API 网关自行实现检索逻辑
```
Plugin 直接 import chromadb，
    自己实现 search() + add_documents()，
    绕过父服务（但这样 Plugin 就不"thin"了）
```

### 建议

> **路径 A**。父服务已有完整的 Hybrid Search 实现，只差两个 HTTP 包装端点。
> 建议在 Sales-Expert-Agent 项目中补充这两个端点，然后 Plugin 纯转发。

---

## 六、部署计划

### 6.1 本地开发环境

```bash
# 启动 Sales-Expert-Agent（父服务）
cd /path/to/Sales-Expert-Agent
uvicorn app.main:app --host 0.0.0.0 --port 8000 &

# 启动 Plugin
cd Workers/sales-expert-plugin
cp .env.example .env
# 编辑 .env：SALES_EXPERT_BASE_URL=http://localhost:8000
uvicorn app.main:app --host 0.0.0.0 --port 8080 --reload

# 验证
curl http://localhost:8080/health
```

### 6.2 Docker 部署

```bash
# 本地构建
cd Workers/sales-expert-plugin
docker compose up --build -d

# 云端构建（Git push 后 CI/CD 自动触发）
# docker-compose.yml 已配置 restart: unless-stopped
```

### 6.3 环境变量

| 变量名 | 默认值 | 说明 |
|--------|--------|------|
| `SALES_EXPERT_BASE_URL` | `http://localhost:8000` | 父服务地址 |
| `PLUGIN_TIMEOUT_SECONDS` | `30` | HTTP 请求超时 |

---

## 七、团队协作说明

### 7.1 代码管理

- **仓库**：使用 Sales-Expert-Agent 现有 Git 仓库
- **新项目路径**：`Workers/sales-expert-plugin/` 和 `Workers/deer-flow-fresh/skills/custom/sales-expert/`
- **分支策略**：在对应仓库创建 `feature/sales-expert-plugin` 分支开发

### 7.2 遇到问题时的分工

| 问题类型 | 谁来处理 |
|----------|----------|
| Plugin 服务报错 | 负责 Plugin 的同学 |
| ChromaDB 查询结果不对 | 负责 Agent 项目的同学 |
| DeerFlow skill 不触发 | 负责 DeerFlow 配置的同学 |
| 云端网络不通 | 负责 DevOps 的同学 |

### 7.3 下一步行动

> **在开始 T2 之前，必须先确认 T1（父服务 /api/v1/* 端点）是否已实现。**
>
> 请负责 Agent 项目的同学运行：
> ```bash
> curl -X POST http://localhost:8000/api/v1/retrieve \
>   -H "Content-Type: application/json" \
>   -d '{"query": "test", "top_k": 1}'
> ```
> 如果返回 404，说明端点不存在，需要先在 Agent 项目补充。

---

## 八、变更日志

| 日期 | 版本 | 变更内容 | 作者 |
|------|------|----------|------|
| 2025-03-29 | v0.1 | 起草文档，建立项目结构 | Albert Sun |
