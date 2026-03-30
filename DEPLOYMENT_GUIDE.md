# Sales-Expert Plugin 部署与使用指南

> **版本**: v1.0.0  
> **最后更新**: 2026-03-30  
> **镜像仓库**: `ccr.ccs.tencentyun.com/sale-expert/sales-expert-plugin:latest`

---

## 📋 目录

1. [架构说明](#架构说明)
2. [快速部署](#快速部署)
3. [API 接口文档](#api-接口文档)
4. [使用示例](#使用示例)
5. [故障排查](#故障排查)

---

## 架构说明

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
│  │  └──────────────────┘    └──────────────────────┘ │ │
│  │         │                        │                 │
│  └─────────┼────────────────────────┼─────────────────┘
│            │                        │
│      外部访问：8000           外部访问：8080
│      (主服务 API)            (插件 API)
│
└─────────────────────────────────────────────────────────┘
```

### 核心依赖

| 组件 | 容器名称 | 端口 | 作用 |
|------|----------|------|------|
| **主服务** | `sales-expert` | 8000 (外部) / 8080 (内部) | 提供向量检索、客户档案管理、AI 推理 |
| **插件服务** | `sales-expert-plugin` | 8080 | 轻量级插件，提供简化的 API 接口 |

---

## 快速部署

### 前置条件

- Ubuntu 20.04+ 云服务器
- Docker 20.10+
- 至少 2GB 可用内存
- 开放端口：8000, 8080

### 一键部署脚本

```bash
#!/bin/bash
set -e

echo "════════════════════════════════════════════════════════"
echo "🚀 Sales-Expert 一键部署脚本"
echo "════════════════════════════════════════════════════════"

# 1. 拉取镜像
echo "📦 拉取 Docker 镜像..."
sudo docker pull ccr.ccs.tencentyun.com/sale-expert/sales-expert:latest
sudo docker pull ccr.ccs.tencentyun.com/sale-expert/sales-expert-plugin:latest

# 2. 创建数据目录
echo "📁 创建数据目录..."
sudo mkdir -p /home/ubuntu/sales-expert-data

# 3. 创建 Docker 网络
echo "🌐 创建 Docker 网络..."
sudo docker network create sales-expert-net 2>/dev/null || true

# 4. 启动主服务
echo "🏗️  启动主服务..."
sudo docker stop sales-expert 2>/dev/null || true
sudo docker rm sales-expert 2>/dev/null || true
sudo docker run -d \
  --name sales-expert \
  --network sales-expert-net \
  -p 8000:8080 \
  -v /home/ubuntu/sales-expert-data:/app/data \
  --restart unless-stopped \
  ccr.ccs.tencentyun.com/sale-expert/sales-expert:latest

# 5. 启动插件服务
echo "🔌 启动插件服务..."
sudo docker stop sales-expert-plugin 2>/dev/null || true
sudo docker rm sales-expert-plugin 2>/dev/null || true
sudo docker run -d \
  --name sales-expert-plugin \
  --network sales-expert-net \
  -p 8080:8080 \
  -e SALES_EXPERT_BASE_URL=http://sales-expert:8080 \
  -e PLUGIN_TIMEOUT_SECONDS=30 \
  --restart unless-stopped \
  ccr.ccs.tencentyun.com/sale-expert/sales-expert-plugin:latest

# 6. 等待服务启动
echo "⏳ 等待服务启动..."
sleep 10

# 7. 验证部署
echo "✅ 验证服务状态..."
sudo docker ps | grep -E "sales-expert|sales-expert-plugin"

echo ""
echo "════════════════════════════════════════════════════════"
echo "✅ 部署完成！"
echo "════════════════════════════════════════════════════════"
echo ""
echo "📋 服务访问地址:"
echo "   主服务 API: http://<服务器 IP>:8000"
echo "   插件 API:   http://<服务器 IP>:8080"
echo ""
echo "🔍 常用命令:"
echo "   # 查看日志"
echo "   sudo docker logs sales-expert"
echo "   sudo docker logs sales-expert-plugin"
echo ""
echo "   # 重启服务"
echo "   sudo docker restart sales-expert"
echo "   sudo docker restart sales-expert-plugin"
echo ""
echo "   # 停止服务"
echo "   sudo docker stop sales-expert sales-expert-plugin"
echo ""
```

**使用方法**：

```bash
# 创建部署脚本
cat > deploy.sh << 'EOF'
# (粘贴上面的脚本内容)
EOF

# 赋予执行权限并运行
chmod +x deploy.sh
./deploy.sh
```

---

## API 接口文档

### 插件服务 API (端口 8080)

#### 1. 健康检查

```http
GET /health
```

**响应示例**：
```json
{
  "status": "ok"
}
```

---

#### 2. 检索/搜索接口

```http
POST /api/v1/retrieve
Content-Type: application/json
X-Tenant-ID: your-tenant-id
```

**请求体**：
```json
{
  "query": "客户对价格敏感，如何说服？",
  "top_k": 5,
  "customer_filter": {
    "industry": "互联网",
    "tags": ["价格敏感", "决策者"]
  },
  "collection_type": "knowledge"
}
```

**参数说明**：

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `query` | string | ✅ | 搜索查询 |
| `top_k` | integer | ❌ | 返回结果数量，默认 5 |
| `customer_filter` | object | ❌ | 客户过滤条件 |
| `collection_type` | string | ❌ | 集合类型：`knowledge` / `conversation` / `profile` |

**响应示例**：
```json
{
  "results": "针对价格敏感客户，建议采用价值锚定法：先展示高端产品建立价格锚点，再推荐中等价位产品，让客户感觉'占了便宜'。同时强调产品的长期价值和 ROI，而非短期成本。",
  "query": "客户对价格敏感，如何说服？",
  "count": 3
}
```

---

#### 3. 同步接口

```http
POST /api/v1/sync
Content-Type: application/json
X-Tenant-ID: your-tenant-id
```

**请求体**：
```json
{
  "session_id": "session_20260330_001",
  "customer_name": "张三",
  "conversations": [
    {
      "role": "user",
      "content": "我想了解一下你们的产品",
      "timestamp": "2026-03-30T10:00:00Z"
    },
    {
      "role": "assistant",
      "content": "您好！我们提供...",
      "timestamp": "2026-03-30T10:00:05Z"
    }
  ],
  "profiles": [
    {
      "customer_name": "张三",
      "company": "XX 科技有限公司",
      "industry": "互联网",
      "turn_count": 3,
      "last_contact": "2026-03-30",
      "tags": ["价格敏感", "决策者", "北京"]
    }
  ]
}
```

**参数说明**：

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `session_id` | string | ❌ | 会话 ID |
| `customer_name` | string | ✅ | 客户姓名 |
| `conversations` | array | ❌ | 对话记录列表 |
| `profiles` | array | ❌ | 客户档案列表 |

**响应示例**：
```json
{
  "status": "ok",
  "messages_stored": 2,
  "profiles_stored": 1
}
```

---

### 主服务 API (端口 8000)

主服务提供更丰富的 API 接口，包括：

- `/api/profiles` - 客户档案管理
- `/api/sessions` - 会话历史查询
- `/api/analyze` - 销售话术分析
- `/api/recommend` - 销售策略推荐

详细文档请参考主服务 Swagger UI：`http://<服务器 IP>:8000/docs`

---

## 使用示例

### 示例 1：集成到 Agent 系统

```python
import requests

class SalesExpertClient:
    def __init__(self, base_url="http://localhost:8080", tenant_id="default"):
        self.base_url = base_url
        self.tenant_id = tenant_id
        self.headers = {
            "Content-Type": "application/json",
            "X-Tenant-ID": self.tenant_id
        }
    
    def retrieve(self, query, top_k=5, customer_filter=None):
        """检索销售知识"""
        payload = {
            "query": query,
            "top_k": top_k,
            "customer_filter": customer_filter or {}
        }
        response = requests.post(
            f"{self.base_url}/api/v1/retrieve",
            json=payload,
            headers=self.headers
        )
        response.raise_for_status()
        return response.json()
    
    def sync(self, session_id, customer_name, conversations=None, profiles=None):
        """同步对话和档案"""
        payload = {
            "session_id": session_id,
            "customer_name": customer_name,
            "conversations": conversations or [],
            "profiles": profiles or []
        }
        response = requests.post(
            f"{self.base_url}/api/v1/sync",
            json=payload,
            headers=self.headers
        )
        response.raise_for_status()
        return response.json()


# 使用示例
client = SalesExpertClient(
    base_url="http://your-server-ip:8080",
    tenant_id="my-company"
)

# 检索销售建议
result = client.retrieve(
    query="客户说'太贵了'，如何回应？",
    top_k=3,
    customer_filter={"tags": ["价格敏感"]}
)
print(result["results"])

# 同步对话记录
client.sync(
    session_id="session_001",
    customer_name="李四",
    conversations=[
        {"role": "user", "content": "这个价格还能再优惠吗？"},
        {"role": "assistant", "content": "我们提供的是整体解决方案..."}
    ],
    profiles=[{
        "customer_name": "李四",
        "company": "XX 公司",
        "industry": "制造业",
        "turn_count": 1,
        "tags": ["价格敏感"]
    }]
)
```

---

### 示例 2：在 DeepAgents 中使用

```python
# DeepAgents skill 配置
from langchain.tools import Tool

sales_expert_tool = Tool(
    name="sales_expert_retrieve",
    description="检索销售专家建议，适用于处理客户异议、销售话术优化等场景",
    func=lambda query: SalesExpertClient().retrieve(query)["results"]
)

# 添加到 Agent 工具列表
tools = [sales_expert_tool]
```

---

## 故障排查

### 问题 1：插件服务无法连接主服务

**症状**：
```
Error: Connection refused to http://sales-expert:8080
```

**解决方案**：

```bash
# 1. 确认主服务容器运行中
sudo docker ps | grep sales-expert

# 2. 检查两个容器在同一网络
sudo docker network inspect sales-expert-net | grep -E "sales-expert|sales-expert-plugin"

# 3. 测试容器间通信
sudo docker exec sales-expert-plugin curl -s http://sales-expert:8080/health

# 4. 如果失败，重启插件容器
sudo docker restart sales-expert-plugin
```

---

### 问题 2：端口冲突

**症状**：
```
Error: Port 8080 is already in use
```

**解决方案**：

```bash
# 查看占用端口的进程
sudo lsof -i :8080

# 停止占用进程或修改插件端口
sudo docker run -d \
  --name sales-expert-plugin \
  --network sales-expert-net \
  -p 8081:8080 \  # 修改为 8081
  ...
```

---

### 问题 3：镜像拉取失败

**症状**：
```
Error: manifest for ccr.ccs.tencentyun.com/sale-expert/sales-expert-plugin:latest not found
```

**解决方案**：

```bash
# 1. 确认镜像已推送
docker images | grep sales-expert

# 2. 重新拉取
sudo docker pull ccr.ccs.tencentyun.com/sale-expert/sales-expert-plugin:latest

# 3. 检查网络连接
ping ccr.ccs.tencentyun.com
```

---

### 问题 4：内存不足

**症状**：
```
Container killed due to OOMKilled
```

**解决方案**：

```bash
# 限制容器内存使用
sudo docker run -d \
  --name sales-expert-plugin \
  --memory="512m" \
  --memory-swap="1g" \
  ...
```

---

## 📞 技术支持

- **GitHub Issues**: https://github.com/Albertsun081400/sales-expert-agent-plugin/issues
- **文档更新**: 2026-03-30
