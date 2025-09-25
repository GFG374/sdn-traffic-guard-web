# SDN功能设置指南

本文档将指导您如何在网络管理平台中设置和使用软件定义网络(SDN)功能。

## 环境要求

在使用SDN功能之前，请确保您的系统满足以下要求：

- Python 3.8+ 
- 足够的系统资源（建议8GB RAM以上，多核CPU）
- 管理员/root权限（用于网络配置）
- 支持虚拟化的环境（如KVM、VirtualBox或VMware）

## 安装所需依赖

### 1. 安装RYU控制器

RYU是一个基于Python的开源SDN控制器框架。

```bash
# 安装RYU控制器
pip install ryu

# 验证安装
ryu --version
```

### 2. 安装Mininet

Mininet是一个轻量级的网络仿真工具，用于创建SDN网络拓扑。

在Ubuntu/Debian系统上：

```bash
# 安装Mininet
apt-get install mininet

# 验证安装
mn --test pingall
```

在其他系统上，您可以从源码安装：

```bash
git clone https://github.com/mininet/mininet
cd mininet
util/install.sh -a
```

### 3. 安装项目依赖

```bash
# 安装后端依赖
cd e:\毕设\network-management-platform\backend
pip install -r requirements.txt

# 安装前端依赖
cd e:\毕设\network-management-platform
npm install
```

## 配置SDN环境

### 1. 配置RYU控制器

1. 默认情况下，RYU控制器会监听127.0.0.1:6633端口
2. 您可以在backend/.env文件中配置控制器连接信息：

```env
# RYU控制器配置
SDN_CONTROLLER_HOST=127.0.0.1
SDN_CONTROLLER_PORT=6633
```

### 2. 配置数据库

系统已自动在models.py中添加了必要的SDN相关数据模型，包括：
- SDNController：存储控制器信息
- SDNSwitch：存储交换机信息
- SDNPort：存储端口信息
- SDNLink：存储链路信息
- SDNHost：存储主机信息

确保数据库已初始化：

```bash
cd e:\毕设\network-management-platform\backend
python init_db.py
```

## 启动SDN功能

### 1. 启动RYU控制器

在一个终端窗口中运行：

```bash
# 使用我们提供的简单交换机应用启动控制器
cd e:\毕设\network-management-platform\backend
ryu-manager --verbose simple_switch_13.py
```

### 2. 启动后端服务器

在另一个终端窗口中运行：

```bash
cd e:\毕设\network-management-platform\backend
python start.py
```

### 3. 启动前端应用

在第三个终端窗口中运行：

```bash
cd e:\毕设\network-management-platform
npm run dev
```

### 4. 创建SDN网络拓扑

您可以使用我们提供的测试工具创建一个基本的SDN网络拓扑：

```bash
cd e:\毕设\network-management-platform\backend
python test_sdn_environment.py --test basic-topology
```

## 使用SDN功能

### 访问SDN拓扑页面

1. 打开浏览器，访问前端应用（默认地址：http://localhost:5173）
2. 登录系统
3. 在左侧边栏中，点击"SDN拓扑"菜单项

### SDN拓扑页面功能

1. **控制器状态监控**：显示连接的控制器状态和基本信息
2. **拓扑可视化**：以图形方式展示网络拓扑结构，包括交换机、主机和它们之间的连接
3. **拓扑操作**：
   - 刷新拓扑：从控制器获取最新拓扑信息
   - 创建测试拓扑：在Mininet中创建预定义的测试拓扑
4. **设备详情查看**：
   - 点击交换机图标查看交换机详细信息、端口状态和流表
   - 点击主机图标查看主机详细信息
5. **流量统计**：查看各端口的流量统计信息

### 使用API端点

系统提供了以下SDN相关的API端点：

1. **控制器管理**：
   - `GET /api/sdn/controller/status` - 获取控制器状态
   - `POST /api/sdn/controller/configure` - 配置控制器连接

2. **拓扑管理**：
   - `GET /api/sdn/topology` - 获取网络拓扑
   - `POST /api/sdn/topology/create` - 创建测试拓扑

3. **交换机管理**：
   - `GET /api/sdn/switches` - 获取所有交换机
   - `GET /api/sdn/switches/{dpid}` - 获取特定交换机详情

4. **流表管理**：
   - `GET /api/sdn/switches/{dpid}/flows` - 获取交换机流表
   - `POST /api/sdn/switches/{dpid}/flows` - 添加流表项
   - `DELETE /api/sdn/switches/{dpid}/flows/{flow_id}` - 删除流表项

5. **端口管理**：
   - `GET /api/sdn/switches/{dpid}/ports` - 获取交换机端口
   - `GET /api/sdn/switches/{dpid}/ports/{port_no}/stats` - 获取端口统计信息

## 测试SDN功能

我们提供了一个测试工具来验证SDN环境是否正常工作：

```bash
cd e:\毕设\network-management-platform\backend
python test_sdn_environment.py --test all
```

这将运行一系列测试来验证：
- RYU控制器是否正常运行
- Mininet是否正确安装
- SDN控制器与Mininet的连接是否正常
- 基本的SDN功能是否可用

## 故障排除

### 常见问题及解决方案

1. **控制器连接失败**
   - 确认RYU控制器正在运行
   - 检查控制器主机和端口配置是否正确
   - 检查防火墙设置，确保6633端口已开放

2. **无法获取拓扑信息**
   - 确认Mininet拓扑已创建
   - 检查交换机是否正确连接到控制器
   - 尝试重启RYU控制器和Mininet

3. **流表操作失败**
   - 确认交换机支持OpenFlow 1.3协议
   - 检查流表项参数是否正确
   - 查看RYU控制器日志以获取详细错误信息

## 开发注意事项

1. 所有SDN相关代码都位于backend目录下：
   - `sdn_manager.py`：SDN功能的核心实现
   - `sdn_routes.py`：SDN相关的API路由
   - `simple_switch_13.py`：基本的OpenFlow 1.3交换机应用

2. 前端SDN拓扑组件位于：
   - `src/components/SDN/SDNTopology.vue`

3. SDN相关数据模型位于：
   - `backend/models.py`

## 联系支持

如果您在使用SDN功能时遇到问题，请联系系统管理员或技术支持。