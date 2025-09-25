# SDN Traffic Guard Web

智能SDN流量管控Web平台 - 基于软件定义网络的安全防护系统

## 🌟 项目特色

- **智能威胁检测**: 基于AI的DDoS攻击检测与防护
- **实时流量监控**: Web可视化界面展示网络状态
- **自动流量清洗**: 智能识别并过滤恶意流量
- **多层防护架构**: 支持ARP欺骗、SYN洪水、UDP洪水等多种攻击防护

## 🛠️ 技术栈

### 前端
- Vue 3 + TypeScript
- Tailwind CSS
- Vite构建工具

### 后端
- Python Flask
- SQLite数据库
- Ryu SDN控制器

### AI/ML
- LoRA微调技术
- 隔离森林算法
- RAG知识增强

## 📁 项目结构

```
├── SDN/                    # SDN控制器核心代码
├── backend/                # Flask后端API
├── src/                    # Vue前端源码
├── docs/                   # 项目文档
└── database/               # 数据库初始化脚本
```

## 🚀 快速开始

1. 安装依赖
```bash
# 后端依赖
cd backend
pip install -r requirements.txt

# 前端依赖
cd ..
npm install
```

2. 启动服务
```bash
# 启动后端
cd backend
python app.py

# 启动前端（新终端）
npm run dev
```

3. 访问 http://localhost:5173

## 🎯 核心功能

- ✅ DDoS攻击检测与防护
- ✅ 网络拓扑可视化
- ✅ 实时流量分析
- ✅ AI威胁识别
- ✅ 自动流量限速
- ✅ 黑名单管理

## 📊 支持的攻击类型

- ARP欺骗攻击
- SYN洪水攻击  
- UDP洪水攻击
- ICMP洪水攻击
- Botnet僵尸网络

## 🤖 AI模型

项目集成了多个AI模型：
- 基于LoRA的增量学习模型
- RAG知识增强分类器
- 隔离森林异常检测

## 📈 系统架构

采用三层检测架构：
1. 数据采集层 - Ryu控制器收集流表信息
2. AI分析层 - 多模型融合威胁识别
3. 防护执行层 - 自动下发流表规则

---

**作者**: gfg374  
**邮箱**: 484018742@qq.com  
**版本**: 1.0.0