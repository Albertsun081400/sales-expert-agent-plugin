# Sales-Expert Plugin - 简化版

## 架构说明

```
DeerFlow Skill (本地)
       ↓ import
sales_expert_plugin (本地 Python 包)
       ↓ HTTP POST →
主服务 (服务器：ccr.ccs.tencentyun.com/sale-expert/sales-expert:v45)
```

## 服务器端（只需主服务）

```bash
# 服务器上只运行主服务，开放 8000 端口
sudo docker run -d \
  --name sales-expert \
  -p 8000:8080 \
  -v /home/ubuntu/sales-expert-data:/app/data \
  -v /home/ubuntu/sales-expert-knowledge:/app/VECTOR_CORPUS \
  --restart unless-stopped \
  ccr.ccs.tencentyun.com/sale-expert/sales-expert:v45
```

## 本地端（DeerFlow Skill 直接调用）

```python
# 在 DeerFlow skill 中直接调用
import httpx

def search_sales_knowledge(query: str, top_k: int = 3):
    """检索销售知识库"""
    resp = httpx.post(
        "http://你的服务器 IP:8000/api/v1/internal/retrieve",
        json={
            "query": query,
            "top_k": top_k,
            "customer_filter": {"tenant_id": "default"},
            "collection_type": "private"
        },
        timeout=30
    )
    return resp.json()["results"]

def sync_customer_profile(customer_name: str, conversation: list):
    """同步客户档案"""
    resp = httpx.post(
        "http://你的服务器 IP:8000/api/v1/internal/sync",
        json={
            "customer_name": customer_name,
            "conversations": conversation,
            "profiles": [],
            "tenant_id": "default"
        },
        timeout=30
    )
    return resp.json()
```

## 服务器防火墙设置

```bash
# 开放 8000 端口
sudo ufw allow 8000/tcp
```

## 测试

```bash
# 本地直接 curl 测试
curl -X POST http://你的服务器 IP:8000/api/v1/internal/retrieve \
  -H "Content-Type: application/json" \
  -d '{"query":"销售话术","top_k":3,"customer_filter":{"tenant_id":"default"},"collection_type":"private"}'
```

## 核心原则

1. **主服务**：服务器上唯一的服务，开放 HTTP API
2. **Plugin**：不是 Docker，是本地 Python 代码，DeerFlow skill 直接 import
3. **通信**：简单的 HTTP POST，无认证，无容器间通信
4. **数据**：知识库和档案存在服务器，本地只负责调用
