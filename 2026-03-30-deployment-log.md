# Sales-Expert Plugin 云服务器部署日志

**日期**: 2026-03-30  
**版本**: v45  
**目标**: 修复插件服务认证问题，实现免认证内部 API 调用

---

## 📋 问题背景

### 初始问题
插件服务在调用主服务 `/api/v1/retrieve` 端点时返回 `500 Internal Server Error`，原因是：
- 主服务的 `/api/v1/retrieve` 需要用户认证（`user: User = Depends(current_active_user)`）
- 插件服务作为内部服务，无法提供认证 token

### 错误日志
```
httpx.HTTPStatusError: Server error '500 Internal Server Error' for url 'http://sales-expert:8080/api/v1/retrieve'
```

---

## 🔧 解决方案

### 1. 主服务代码修改

**文件**: `Sales-Expert-Agent/app/main.py`

**新增端点**:
- `/api/v1/internal/retrieve` - 免认证检索端点
- `/api/v1/internal/sync` - 免认证同步端点

**代码片段**:
```python
# ── V1 API: Internal Retrieval (No Auth, for Plugin) ─────────────────────────────
@app.post("/api/v1/internal/retrieve", response_model=RetrieveResponse)
async def internal_retrieve(req: RetrieveRequest):
    """
    Internal retrieval endpoint for plugin service (no auth required).
    Uses default tenant_id for multi-tenant isolation.
    """
    from agent.memory_store import memory_store

    tenant_id = req.customer_filter.get("tenant_id", "default") if req.customer_filter else "default"

    results = memory_store.search(
        query=req.query,
        top_k=req.top_k,
        customer_filter=req.customer_filter,
        tenant_id=tenant_id,
        collection_type=req.collection_type,
    )
    count = results.count("\n\n---\n\n") + 1 if "---" in results else (1 if results and "[未找到]" not in results else 0)
    return RetrieveResponse(results=results, query=req.query, count=count)


# ── V1 API: Internal Sync (No Auth, for Plugin) ──────────────────────────────────
@app.post("/api/v1/internal/sync", response_model=SyncResponse)
async def internal_sync(req: SyncRequest):
    """
    Internal sync endpoint for plugin service (no auth required).
    Uses tenant_id from request for multi-tenant isolation.
    """
    from agent.memory_store import memory_store
    import datetime

    tenant_id = getattr(req, "tenant_id", "default") or "default"
    customer_name = req.customer_name or "unknown"

    messages_stored = 0
    for turn in req.conversations:
        doc_content = f"[{turn.role.upper()}] {turn.content}"
        ts = turn.timestamp or datetime.datetime.now().isoformat()
        memory_store.add_documents(
            documents=[doc_content],
            metadatas=[{
                "source_dir": "conversations",
                "file_name": f"session_{req.session_id or 'unknown'}",
                "customer_name": customer_name,
                "role": turn.role,
                "timestamp": ts,
            }],
            tenant_id=tenant_id,
        )
        messages_stored += 1

    profiles_stored = 0
    for profile in req.profiles:
        profile_doc = (
            f"客户：{profile.customer_name}\n"
            f"公司：{profile.company or '未知'}\n"
            f"行业：{profile.industry or '未知'}\n"
            f"跟进轮次：{profile.turn_count}\n"
            f"最后接触：{profile.last_contact or '未知'}\n"
            f"标签：{', '.join(profile.tags)}"
        )
        memory_store.add_documents(
            documents=[profile_doc],
            metadatas=[{
                "source_dir": "profiles",
                "file_name": profile.customer_name,
                "customer_name": profile.customer_name,
                "company": profile.company,
                "industry": profile.industry,
                "turn_count": str(profile.turn_count),
                "last_contact": profile.last_contact,
                "tags": ",".join(profile.tags),
            }],
            tenant_id=tenant_id,
        )
        profiles_stored += 1

    return SyncResponse(
        status="ok",
        messages_stored=messages_stored,
        profiles_stored=profiles_stored,
    )
```

---

### 2. 插件服务代码修改

**文件**: `Workers/sales-expert-plugin/app/memory_store.py`

**修改内容**:
- 将 `search()` 方法调用端点从 `/api/v1/retrieve` 改为 `/api/v1/internal/retrieve`
- 将 `add_documents()` 方法调用端点从 `/api/v1/sync` 改为 `/api/v1/internal/sync`
- 移除 `X-Tenant-ID` header，改为在 payload 中传递 `tenant_id`

**代码片段**:
```python
def search(
    self,
    query: str,
    top_k: int = 4,
    customer_filter: Optional[dict] = None,
    tenant_id: str = "default",
    collection_type: str = "private",
) -> str:
    """Hybrid retrieval via parent service internal endpoint (no auth)."""
    # Add tenant_id to filter for multi-tenant isolation
    if customer_filter is None:
        customer_filter = {"tenant_id": tenant_id}
    else:
        customer_filter["tenant_id"] = tenant_id
    
    payload = {
        "query": query,
        "top_k": top_k,
        "customer_filter": customer_filter,
        "collection_type": collection_type,
    }
    with httpx.Client(timeout=TIMEOUT_SECONDS) as client:
        resp = client.post(
            f"{self.base_url}/api/v1/internal/retrieve",
            json=payload,
        )
        resp.raise_for_status()
        data = resp.json()
        return data["results"]
```

---

### 3. Dockerfile 优化

**文件**: `Sales-Expert-Agent/app/Dockerfile`

**修改**: 使用清华镜像源加速 pip 安装

```dockerfile
# 安装 Python 依赖（使用清华镜像源加速）
COPY requirements.txt .
RUN pip install --no-cache-dir -i https://pypi.tuna.tsinghua.edu.cn/simple -r requirements.txt
```

---

## 📦 镜像构建与推送

### 镜像信息
| 镜像 | 标签 | 仓库 |
|------|------|------|
| 主服务 | `v45` | `ccr.ccs.tencentyun.com/sale-expert/sales-expert:v45` |
| 插件服务 | `v45` | `ccr.ccs.tencentyun.com/sale-expert/sales-expert-plugin:v45` |

### 构建命令（本地）
```bash
# 构建主服务
cd "/Users/sunxiangyu/Documents/Obsidian Vault/05 AI Dojo/Sales-Expert-Agent/app"
docker build --platform linux/amd64 -t ccr.ccs.tencentyun.com/sale-expert/sales-expert:v45 .

# 构建插件
cd "/Users/sunxiangyu/Documents/Obsidian Vault/05 AI Dojo/Workers/sales-expert-plugin"
docker build --platform linux/amd64 -t ccr.ccs.tencentyun.com/sale-expert/sales-expert-plugin:v45 .

# 推送镜像
docker push ccr.ccs.tencentyun.com/sale-expert/sales-expert:v45
docker push ccr.ccs.tencentyun.com/sale-expert/sales-expert-plugin:v45
```

---

## ☁️ 云服务器部署命令

### 升级步骤
```bash
# 1. 停止旧容器
sudo docker stop sales-expert sales-expert-plugin

# 2. 删除旧容器
sudo docker rm sales-expert sales-expert-plugin

# 3. 拉取 v45 镜像
sudo docker pull ccr.ccs.tencentyun.com/sale-expert/sales-expert:v45
sudo docker pull ccr.ccs.tencentyun.com/sale-expert/sales-expert-plugin:v45

# 4. 启动主服务
sudo docker run -d --name sales-expert --network sales-expert-net -p 8000:8080 -v /home/ubuntu/sales-expert-data:/app/data --restart unless-stopped ccr.ccs.tencentyun.com/sale-expert/sales-expert:v45

# 5. 启动插件服务
sudo docker run -d --name sales-expert-plugin --network sales-expert-net -p 8080:8080 -e SALES_EXPERT_BASE_URL=http://sales-expert:8080 -e PLUGIN_TIMEOUT_SECONDS=30 --restart unless-stopped ccr.ccs.tencentyun.com/sale-expert/sales-expert-plugin:v45

# 6. 验证部署
sleep 10
sudo docker ps | grep sales-expert
```

### 测试命令
```bash
# 健康检查
curl http://127.0.0.1:8080/health

# 测试检索 API
curl -X POST http://127.0.0.1:8080/api/v1/retrieve -H "Content-Type: application/json" -d '{"query": "客户说价格太贵怎么回应", "top_k": 3}'

# 测试同步 API
curl -X POST http://127.0.0.1:8080/api/v1/sync -H "Content-Type: application/json" -d '{"session_id": "test_001", "customer_name": "测试客户", "conversations": [], "profiles": []}'
```

---

## 📊 架构说明

```
┌─────────────────────────────────────────────────────────┐
│                    云服务器 (Ubuntu)                     │
│                                                          │
│  ┌────────────────────────────────────────────────────┐ │
│  │         Docker Network: sales-expert-net           │ │
│  │                                                     │ │
│  │  ┌──────────────────┐    ┌──────────────────────┐ │ │
│  │  │  sales-expert    │◄───│ sales-expert-plugin  │ │ │
│  │  │  (主服务)         │    │  (插件服务)           │ │ │
│  │  │  Port: 8080      │    │  Port: 8080          │ │ │
│  │  │                  │    │                      │ │ │
│  │  │  - 向量数据库     │    │  - 内存存储          │ │ │
│  │  │  - 客户档案       │    │  - 会话记录          │ │ │
│  │  │  - AI 推理引擎    │    │  - 请求转发          │ │ │
│  │  │                  │    │                      │ │ │
│  │  │  /api/v1/internal│    │  /api/v1/retrieve    │ │ │
│  │  │  (免认证)         │    │  (调用内部端点)       │ │ │
│  │  └──────────────────┘    └──────────────────────┘ │ │
│  │         │                        │                 │
│  └─────────┼────────────────────────┼─────────────────┘
│            │                        │
│      外部访问：8000           外部访问：8080
│      (主服务 API)            (插件 API)
│
└─────────────────────────────────────────────────────────┘
```

---

## ✅ 完成清单

- [x] 主服务添加 `/api/v1/internal/retrieve` 端点
- [x] 主服务添加 `/api/v1/internal/sync` 端点
- [x] 插件服务修改为调用内部端点
- [x] 插件服务移除认证 header
- [x] Dockerfile 优化（清华镜像源）
- [x] 创建部署文档 `DEPLOYMENT_GUIDE.md`
- [ ] 镜像构建完成（进行中）
- [ ] 镜像推送完成（待执行）
- [ ] 云服务器升级完成（待执行）
- [ ] API 测试通过（待验证）

---

## 📝 关键决策记录

### 决策 1：为什么不使用原有认证端点？
**原因**: 插件作为内部服务，与主服务在同一 Docker 网络内，不需要外部认证机制。添加免认证内部端点简化了架构。

### 决策 2：为什么选择 `/api/v1/internal/*` 路径？
**原因**: 
- 清晰区分内部 API 和外部 API
- 便于未来审计和监控
- 不影响现有认证端点

### 决策 3：多租户隔离如何实现？
**方案**: 通过 `tenant_id` 参数在请求 payload 中传递，主服务根据 `tenant_id` 过滤数据。

---

## 🔗 相关仓库

- **主服务**: `https://github.com/Albertsun081400/obsidian-AI-Dojo` (Sales-Expert-Agent 目录)
- **插件服务**: `https://github.com/Albertsun081400/sales-expert-agent-plugin`
- **腾讯云镜像仓库**: `ccr.ccs.tencentyun.com/sale-expert/`

---

## 📅 下一步计划

1. ✅ 等待本地 Docker 镜像构建完成
2. ⏳ 推送 v45 镜像到腾讯云
3. ⏳ 在云服务器执行升级命令
4. ⏳ 测试检索和同步 API
5. ⏳ 验证多租户隔离功能

---

**记录人**: DeepAgents  
**创建时间**: 2026-03-30 21:00  
**最后更新**: 2026-03-30 21:30
