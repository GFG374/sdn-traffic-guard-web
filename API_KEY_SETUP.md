# AI文件上传和分析功能配置指南

## 功能概述

本项目已实现了完整的AI文件上传和分析功能，支持以下文件格式：
- **文本文件**: .txt, .md, .log
- **办公文档**: .pdf, .docx, .xlsx, .csv
- **数据文件**: .json

## 配置步骤

### 1. 获取DashScope API密钥

为了使用AI分析功能，您需要配置有效的DashScope API密钥：

1. **注册阿里云账号**: 访问 [阿里云官网](https://www.aliyun.com/)
2. **开通DashScope服务**: 访问 [DashScope控制台](https://dashscope.console.aliyun.com/)
3. **创建API密钥**: 在控制台中创建新的API密钥
4. **复制密钥**: 将生成的API密钥复制到剪贴板

### 2. 配置API密钥

将获取的API密钥添加到项目配置中：

#### 方法1: 修改.env文件
编辑 `backend/.env` 文件，更新以下配置：

```bash
# Dashscope AI配置（用于embedding和RAG）
DASHSCOPE_API_KEY=您的实际API密钥
DASHSCOPE_EMBEDDING_MODEL=text-embedding-v2
DASHSCOPE_CHAT_MODEL=qwen-turbo
```

#### 方法2: 环境变量设置
在启动服务前设置环境变量：

**Windows (PowerShell)**:
```powershell
$env:DASHSCOPE_API_KEY="您的实际API密钥"
```

**Linux/MacOS**:
```bash
export DASHSCOPE_API_KEY="您的实际API密钥"
```

### 3. 验证配置

重启后端服务后，可以通过以下方式验证：

1. **文件上传测试**: 上传任意支持的文件格式
2. **错误信息检查**: 如果API密钥无效，系统会显示友好的错误提示
3. **功能验证**: 上传文件后，AI会自动分析内容并添加到知识库

## 使用说明

### 前端操作
1. 登录系统
2. 导航到AI助手页面
3. 拖拽或选择文件上传
4. 查看分析结果

### 支持的文件类型
- **文本分析**: 支持.txt, .md, .log等文本文件
- **文档解析**: 支持.pdf, .docx等办公文档
- **数据分析**: 支持.csv, .xlsx, .json等数据文件

### 功能特点
- ✅ 多格式文件支持
- ✅ 智能内容分析
- ✅ 知识库构建
- ✅ 上下文问答
- ✅ 错误友好提示

## 故障排除

### 常见问题

**问题**: "Invalid API-key provided"
**解决**: 
1. 检查.env文件中的DASHSCOPE_API_KEY是否正确
2. 确保API密钥有访问DashScope服务的权限
3. 重启后端服务

**问题**: "RAG功能未启用"
**解决**: 确保在.env文件中正确配置了DASHSCOPE_API_KEY

**问题**: 文件上传失败
**解决**: 
1. 检查文件格式是否在支持列表中
2. 确保文件大小不超过限制
3. 检查网络连接

### 获取帮助

如需技术支持，请：
1. 检查控制台错误日志
2. 验证API密钥配置
3. 参考项目文档
4. 联系开发团队

## 免费额度

DashScope为新用户提供免费试用额度：
- 文本嵌入模型: 50万次调用
- 通义千问模型: 100万tokens

详细信息请参考 [DashScope定价](https://dashscope.console.aliyun.com/pricing)