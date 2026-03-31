# Sales-Expert Plugin (多租户 Agent 检索插件)

> **Role**: 为外部 Agent (如 DeerFlow, Dify, AutoGPT) 提供基于多租户隔离的销售知识 RAG 检索能力。
> **Asset Level**: L4 Application (AI Dojo)

## 1. Agent 接入协议 (Protocol)

任何外部 Agent 在调用此插件时，必须遵循以下 **Scoped Identity** 规则：

### 1.1 凭证获取 (Authentication)
所有的请求必须携带 `X-Tenant-ID` 请求头。
- **获取方式**: 用户登录 `Sales-Expert-Agent` 主端 -> 个人设置 -> 架构配置 -> 复制 **Agent 插件接入凭证 (Scoped ID)**。
- **格式示例**: `diling/0b021b9e-8b9f-4dd7-91ee-1524e7bc5124` (格式为：`租户/用户ID`)。

### 1.2 核心端点 (Endpoints)

| 端点 | 描述 | 调用逻辑 |
|------|------|--------|
| `POST /api/v1/retrieve` | **知识检索** | 传入 `query`，返回经过向量+重排处理的销售知识片段。 |
| `POST /api/v1/sync` | **记忆归档** | 将当前的对话轮次或生成的客户画像同步进 ChromaDB，实现 Agent 的长期记忆。 |

---

## 2. 调用示例 (Examples)

### CURL (推荐给 DeerFlow Skill)
```bash
curl -X POST "http://81.69.61.141:8080/api/v1/retrieve" \
     -H "Content-Type: application/json" \
     -H "X-Tenant-ID: diling/your-scoped-id" \
     -d '{"query": "客户报价太低怎么回复?", "top_k": 3}'
```

### Python (推荐给自定义 Worker)
```python
import httpx

headers = {"X-Tenant-ID": "diling/your-scoped-id"}
payload = {"query": "如何应对压价", "top_k": 2}

with httpx.Client() as client:
    response = client.post("http://your-plugin-ip:8080/api/v1/retrieve", headers=headers, json=payload)
    print(response.json())
```

---

## 3. 给 Agent 的指令 (Prompt Engineering)

如果你是正在配置 DeerFlow 或 Dify 的 Agent，请将以下逻辑加入它的 **System Prompt**:

> 当你需要获悉关于特定客户的历史信息、应对策略或相似成功案例时，请调用 `sales-expert` 插件。
> 1. **Header 注入**: 必须包含 `X-Tenant-ID` (值见用户配置)。
> 2. **意图识别**: 如果用户问的是“我该怎么说”，请先调用 `/retrieve` 检索相似语料；如果对话结束，请调用 `/sync` 存入画像。
> 3. **数据隔离**: 严禁在未授权的情况下尝试猜测其他租户的 ID。

---

## 4. 部署与维护 (Operations)

### 环境依赖
- **SALES_EXPERT_BASE_URL**: 指向主服务的 API 地址（如 `http://81.69.61.141:8015`）。
- **PLUGIN_TIMEOUT_SECONDS**: 检索超时限制（建议 30s，用于复杂重排）。

### 部署
```bash
docker compose up -d
```

---
**Maintainer**: Albert Sun (Digital Twin)  
**Status**: Stable Multi-Tenant Scoped
