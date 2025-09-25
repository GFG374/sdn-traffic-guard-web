# AI助手集成指南

本指南将帮助您完成Kimi AI助手的配置和部署。

## 功能特性

- 🤖 **Kimi大模型集成** - 基于Moonshot AI的Kimi大语言模型
- 📁 **多文件支持** - 支持PDF、Word、Excel、CSV、TXT等格式
- 💬 **对话历史** - 完整的对话记录和管理
- 🎨 **Kimi官网风格** - 现代化的深色主题界面
- 🔍 **智能文件分析** - 自动解析和总结文件内容
- 📊 **数据可视化** - 支持图表生成和数据分析

## 环境配置

### 1. 获取Kimi API密钥

1. 访问 [Moonshot AI官网](https://platform.moonshot.cn/)
2. 注册账号并创建API密钥
3. 将密钥添加到环境变量：
   ```bash
   # 在 .env 文件中添加
   VITE_KIMI_API_KEY=your-actual-api-key-here
   ```

### 2. 安装依赖

```bash
# 安装Python依赖
pip install -r requirements.txt

# 安装前端依赖
cd src
npm install

# 安装额外的前端依赖
npm install marked @types/marked
```

### 3. 数据库初始化

系统会自动创建所需的数据库表，包括：
- `ai_conversations` - 存储对话记录
- `ai_messages` - 存储消息内容
- `ai_files` - 存储上传的文件信息

## 文件结构

```
src/components/AIAssistant/
├── AIAssistant.vue          # 主AI助手组件
├── components/
│   ├── FileUpload.vue       # 文件上传组件
│   ├── ChatMessage.vue      # 消息显示组件
│   └── ConversationList.vue # 对话列表组件

backend/
├── ai_routes.py             # AI相关API路由
├── models.py               # 数据库模型
└── requirements.txt        # Python依赖
```

## 使用方法

### 启动服务

1. **启动后端服务**:
   ```bash
   cd backend
   python -m uvicorn app:app --reload --host 0.0.0.0 --port 8001
   ```

2. **启动前端服务**:
   ```bash
   cd src
   npm run dev
   ```

### 功能使用

#### 1. 新建对话
- 点击"新建对话"按钮开始新的AI对话
- 系统会自动创建对话标题

#### 2. 文件上传
- 支持拖拽上传或点击选择文件
- 支持的文件类型：
  - PDF文档 (.pdf)
  - Word文档 (.doc, .docx)
  - Excel表格 (.xls, .xlsx)
  - CSV文件 (.csv)
  - 文本文件 (.txt)

#### 3. 对话管理
- 左侧边栏显示历史对话
- 点击对话记录可继续之前的对话
- 支持对话搜索和删除

#### 4. 文件分析示例

**PDF分析**:
```
用户：请分析这份财务报告
AI：基于您提供的PDF文件，我分析了以下内容：
1. 收入趋势：本季度收入增长了15%
2. 成本结构：人工成本占比45%
3. 建议：建议优化供应链成本...
```

**Excel数据分析**:
```
用户：请根据销售数据生成图表
AI：根据您的Excel数据，我为您生成了以下分析：
- 月度销售趋势图
- 产品类别分布饼图
- 地区销售对比柱状图
```

## API接口

### 主要接口

1. **发送消息**:
   ```http
   POST /api/ai/analyze
   {
     "message": "用户消息",
     "file": {文件信息},
     "conversationId": "对话ID",
     "history": [历史消息]
   }
   ```

2. **获取对话列表**:
   ```http
   GET /api/ai/conversations
   ```

3. **获取对话详情**:
   ```http
   GET /api/ai/conversations/{conversation_id}
   ```

4. **文件上传**:
   ```http
   POST /api/ai/upload
   Content-Type: multipart/form-data
   ```

## 配置选项

### 环境变量

在 `.env` 文件中配置以下参数：

```bash
# Kimi API配置
VITE_KIMI_API_KEY=your-kimi-api-key
VITE_KIMI_API_URL=https://api.moonshot.cn/v1/chat/completions

# 文件上传限制
MAX_FILE_SIZE=10485760  # 10MB
ALLOWED_FILE_TYPES=pdf,doc,docx,xls,xlsx,csv,txt

# 对话配置
MAX_HISTORY_MESSAGES=10
AI_MODEL=moonshot-v1-8k
```

### 自定义样式

可以通过修改CSS变量来自定义主题：

```css
:root {
  --ai-primary-color: #667eea;
  --ai-secondary-color: #764ba2;
  --ai-background-dark: #0f0f0f;
  --ai-background-light: #1a1a1a;
  --ai-text-primary: #ffffff;
  --ai-text-secondary: #888888;
}
```

## 故障排除

### 常见问题

1. **API调用失败**
   - 检查API密钥是否正确
   - 确认网络连接正常
   - 查看API额度是否充足

2. **文件上传失败**
   - 检查文件大小限制
   - 确认文件格式支持
   - 查看服务器磁盘空间

3. **数据库错误**
   - 确认数据库文件权限
   - 检查数据库表结构
   - 重启数据库连接

### 调试模式

启用调试模式查看详细日志：

```bash
# 后端调试
export DEBUG=true
python app.py

# 前端调试
npm run dev -- --debug
```

## 扩展功能

### 自定义分析模板

可以添加自定义的分析模板：

```javascript
const analysisTemplates = {
  '财务分析': '请分析以下财务数据，关注收入、成本、利润等关键指标...',
  '网络诊断': '请诊断以下网络配置，检查潜在的安全风险...',
  '数据报告': '请根据以下数据生成详细的分析报告...'
}
```

### 集成其他AI模型

支持集成其他AI模型：

```python
# 在 ai_routes.py 中添加新的模型配置
AI_MODELS = {
    'kimi': 'moonshot-v1-8k',
    'gpt': 'gpt-3.5-turbo',
    'claude': 'claude-3-haiku-20240307'
}
```

## 性能优化

### 缓存策略

- 对话历史本地缓存
- 文件内容预处理缓存
- API响应结果缓存

### 数据库优化

- 定期清理旧对话
- 文件存储优化
- 索引优化

## 安全建议

1. **API密钥保护**
   - 不要将API密钥提交到代码仓库
   - 使用环境变量存储敏感信息
   - 定期更换API密钥

2. **文件安全**
   - 限制上传文件类型
   - 扫描上传文件内容
   - 定期清理临时文件

3. **用户权限**
   - 实施用户会话管理
   - 限制API调用频率
   - 记录用户操作日志

## 技术支持

如有问题，请联系：
- 邮箱：support@example.com
- 文档：[项目Wiki](https://github.com/your-repo/wiki)
- 问题反馈：[GitHub Issues](https://github.com/your-repo/issues)

---

*最后更新：2024年12月*