# AI Agent 使用指南

## 概述

本项目基于LangChain构建了一个强大的AI Agent系统，提供CSV分析、数据可视化、网络诊断、文档分析等多功能AI服务。所有AI调用都在后端完成，前端只需调用相应的API接口。

## 功能特性

### 1. 智能对话
- 自然语言交互
- 上下文记忆
- 专业建议

### 2. CSV文件分析
- 数据统计分析
- 趋势识别
- 异常检测
- 相关性分析

### 3. 数据可视化
- 支持多种图表类型：柱状图、折线图、饼图、散点图、直方图
- 自动生成图表
- 可自定义样式

### 4. 网络诊断
- 配置分析
- 安全评估
- 性能优化建议
- 问题排查

### 5. 文档分析
- 文本摘要
- 关键信息提取
- 情感分析
- 主题识别

## API接口

### 基础信息
- 基础URL: `http://localhost:8001/api`
- AI服务路径: `/ai`

### 可用端点

#### 1. 智能对话
```
POST /ai/chat
Content-Type: application/json

{
  "message": "你的问题",
  "context": {
    "user_info": "可选的用户信息",
    "history": "可选的历史记录"
  }
}
```

#### 2. CSV文件分析
```
POST /ai/analyze-csv
Content-Type: multipart/form-data

file: CSV文件
query: 分析查询字符串
context: JSON格式的上下文信息（可选）
```

#### 3. 文本文档分析
```
POST /ai/analyze-text
Content-Type: multipart/form-data

file: 文本文件（.txt, .md, .json, .log）
query: 分析查询字符串
context: JSON格式的上下文信息（可选）
```

#### 4. 网络诊断
```
POST /ai/network-diagnosis
Content-Type: application/json

{
  "ip_config": {
    "gateway": "192.168.1.1",
    "dns_servers": ["8.8.8.8", "8.8.4.4"]
  },
  "firewall_rules": [
    {"port": 80, "action": "allow"}
  ],
  "bandwidth_usage": 75
}
```

#### 5. 创建可视化图表
```
POST /ai/create-visualization
Content-Type: application/json

{
  "data": {
    "x": ["一月", "二月", "三月"],
    "y": [100, 200, 150]
  },
  "chart_type": "bar",
  "title": "月度销售数据",
  "x_label": "月份",
  "y_label": "销售额"
}
```

#### 6. 获取功能列表
```
GET /ai/capabilities
```

#### 7. 健康检查
```
GET /ai/health
```

## 配置要求

### 环境变量配置
在 `backend/.env` 文件中配置以下API密钥：

```bash
# Kimi AI配置
KIMI_API_KEY=your-kimi-api-key-here
KIMI_API_URL=https://api.moonshot.cn/v1/chat/completions

# Dashscope配置
DASHSCOPE_API_KEY=your-dashscope-api-key-here
DASHSCOPE_EMBEDDING_MODEL=text-embedding-v2
DASHSCOPE_CHAT_MODEL=qwen-turbo
```

### 获取API密钥

#### Kimi API密钥
1. 访问 [Moonshot AI](https://platform.moonshot.cn/)
2. 注册账号并登录
3. 在控制台创建API密钥
4. 将密钥填入 `KIMI_API_KEY`

#### Dashscope API密钥
1. 访问 [阿里云Dashscope](https://dashscope.console.aliyun.com/)
2. 注册阿里云账号
3. 开通Dashscope服务
4. 创建API密钥并填入 `DASHSCOPE_API_KEY`

## 使用示例

### 1. Python调用示例

```python
import requests
import json

# 基础URL
base_url = "http://localhost:8001/api"

# 智能对话
response = requests.post(
    f"{base_url}/ai/chat",
    json={
        "message": "请帮我分析网络配置的安全性",
        "context": {"network_type": "企业网络"}
    }
)
print(response.json())

# CSV分析
with open('data.csv', 'rb') as f:
    response = requests.post(
        f"{base_url}/ai/analyze-csv",
        files={'file': f},
        data={'query': '分析这份数据的趋势和异常值'}
    )
    print(response.json())

# 网络诊断
network_config = {
    "ip_config": {
        "gateway": "192.168.1.1",
        "dns_servers": ["8.8.8.8"]
    },
    "firewall_rules": [
        {"port": 22, "action": "allow"},
        {"port": 80, "action": "allow"}
    ]
}

response = requests.post(
    f"{base_url}/ai/network-diagnosis",
    json=network_config
)
print(response.json())
```

### 2. JavaScript调用示例

```javascript
// 智能对话
const chatResponse = await fetch('http://localhost:8001/api/ai/chat', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
  },
  body: JSON.stringify({
    message: '如何优化网络性能？',
    context: { network_size: 'medium' }
  })
});

const data = await chatResponse.json();
console.log(data);

// 文件上传分析
const formData = new FormData();
formData.append('file', csvFile);
formData.append('query', '分析这份数据的统计特征');

const fileResponse = await fetch('http://localhost:8001/api/ai/analyze-csv', {
  method: 'POST',
  body: formData
});

const result = await fileResponse.json();
console.log(result);
```

## 部署说明

### 1. 安装依赖
```bash
cd backend
pip install -r requirements.txt
```

### 2. 配置环境变量
```bash
cp .env.example .env
# 编辑.env文件，填入API密钥
```

### 3. 启动服务
```bash
# 开发模式
python -m uvicorn app:app --host 0.0.0.0 --port 8001 --reload

# 生产模式
python -m uvicorn app:app --host 0.0.0.0 --port 8001
```

## 故障排除

### 常见问题

1. **API密钥无效**
   - 检查密钥是否正确
   - 确认服务是否已开通
   - 检查网络连接

2. **文件上传失败**
   - 确认文件格式支持
   - 检查文件大小限制
   - 验证网络连接

3. **分析结果不准确**
   - 检查数据格式是否正确
   - 确认查询描述清晰
   - 尝试提供更多上下文信息

### 调试方法

1. 查看后端日志
2. 检查API响应状态码
3. 验证环境变量配置
4. 使用健康检查端点

## 扩展开发

### 添加新工具

1. 在 `ai_agent_service.py` 中添加新的工具函数
2. 在 `_initialize_tools` 方法中注册新工具
3. 在 `ai_routes.py` 中添加对应的路由
4. 更新功能列表

### 自定义提示词

修改 `ai_agent_service.py` 中的提示词模板，以适应特定场景需求。

## 支持

如有问题，请检查：
1. API密钥配置
2. 网络连接状态
3. 服务日志信息
4. 文档中的示例代码

---

*最后更新：2024年1月*