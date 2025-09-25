<template>
  <div class="sdn-chat-container">
    <!-- 顶部导航 -->
    <div class="top-bar">
      <div class="left-section">
        <h1 class="title">SDN智能控制台</h1>
        <span class="subtitle">基于RYU控制器</span>
      </div>
      <div class="right-section">
        <div class="controller-status" :class="{ online: controllerOnline, offline: !controllerOnline }">
          <i :class="controllerOnline ? 'fas fa-circle' : 'fas fa-exclamation-triangle'"></i>
          <span>{{ controllerOnline ? '控制器在线' : '控制器离线' }}</span>
        </div>
        <button class="new-chat-btn" @click="clearChat">
          <i class="fas fa-plus"></i>
          新建会话
        </button>
      </div>
    </div>

    <div class="main-layout">
      <!-- 左侧功能面板 -->
      <div class="sidebar">
        <div class="sidebar-header">
          <h3>网络管理</h3>
        </div>
        
        <!-- 网络状态 -->
        <div class="network-status">
          <h4>网络状态</h4>
          <div class="status-item">
            <span class="label">交换机数量:</span>
            <span class="value">{{ networkStats.switches }}</span>
          </div>
          <div class="status-item">
            <span class="label">活跃交换机:</span>
            <span class="value">{{ networkStats.active_switches }}</span>
          </div>
          <div class="status-item">
            <span class="label">主机数量:</span>
            <span class="value">{{ networkStats.hosts }}</span>
          </div>
          <div class="status-item">
            <span class="label">链路数量:</span>
            <span class="value">{{ networkStats.links }}</span>
          </div>
          <div class="status-item">
            <span class="label">流表数量:</span>
            <span class="value">{{ networkStats.flows }}</span>
          </div>
          <div class="status-item">
            <span class="label">控制器状态:</span>
            <span class="value" :class="networkStats.controller_status === 'connected' ? 'status-online' : 'status-offline'">
              {{ networkStats.controller_status === 'connected' ? '已连接' : '未连接' }}
            </span>
          </div>
        </div>

        <!-- 快捷命令 -->
        <div class="quick-commands">
          <h4>快捷命令</h4>
          <button @click="insertCommand('加黑 ')" class="cmd-btn">
            <i class="fas fa-ban"></i>
            加黑IP
          </button>
          <button @click="insertCommand('解除 ')" class="cmd-btn">
            <i class="fas fa-unlock"></i>
            解除封锁
          </button>
          <button @click="insertCommand('查询 ')" class="cmd-btn">
            <i class="fas fa-search"></i>
            查询状态
          </button>
          <button @click="insertCommand('拓扑')" class="cmd-btn">
            <i class="fas fa-project-diagram"></i>
            查看拓扑
          </button>
        </div>

        <!-- 最近操作 -->
        <div class="recent-operations">
          <h4>最近操作</h4>
          <div class="operation-list">
            <div v-for="op in recentOperations" :key="op.id" class="operation-item">
              <div class="op-time">{{ formatTime(op.timestamp) }}</div>
              <div class="op-command">{{ op.command }}</div>
              <div class="op-status" :class="op.status">{{ op.status }}</div>
            </div>
          </div>
        </div>
      </div>

      <!-- 主聊天区域 -->
      <div class="chat-area">
        <!-- 未登录提示 -->
        <div v-if="!userStore.token" class="auth-error">
          <div class="error-content">
            <i class="fas fa-exclamation-triangle"></i>
            <h3>请先登录</h3>
            <p>您需要登录才能使用SDN控制台功能</p>
            <button @click="$router.push('/login')" class="login-btn">
              前往登录
            </button>
          </div>
        </div>
        
        <!-- 聊天消息区域 -->
        <div class="messages-container" ref="messagesContainer">
          <div class="messages">
            <!-- 欢迎消息 -->
            <div v-if="messages.length === 0" class="welcome-message">
              <div class="welcome-content">
                <i class="fas fa-robot"></i>
                <h3>欢迎使用SDN智能控制台</h3>
                <p>您可以使用以下命令格式：</p>
                <ul>
                  <li><code>加黑 192.168.1.100</code> - 封锁指定IP地址</li>
                  <li><code>解除 192.168.1.100</code> - 解除IP地址封锁</li>
                  <li><code>查询 192.168.1.100</code> - 查询IP地址状态</li>
                  <li><code>拓扑</code> - 查看网络拓扑</li>
                </ul>
              </div>
            </div>
            
            <div 
              v-for="message in messages" 
              :key="message.id"
              class="message"
              :class="message.role"
            >
              <div class="message-content">
                <div class="message-header">
                  <div class="avatar">
                    <i :class="message.role === 'user' ? 'fas fa-user' : 'fas fa-robot'"></i>
                  </div>
                  <span class="role-name">{{ message.role === 'user' ? '我' : 'SDN控制器' }}</span>
                  <span class="message-time">{{ formatTime(message.timestamp) }}</span>
                </div>
                
                <div class="message-text" :class="{ thinking: message.isThinking }">
                  <div v-if="message.isThinking" class="thinking-animation">
                    <span>控制器正在处理</span>
                    <div class="thinking-dots">
                      <span></span>
                      <span></span>
                      <span></span>
                    </div>
                  </div>
                  <div v-else v-html="renderMessage(message.content)"></div>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- 输入区域 -->
        <div class="input-area">
          <div class="input-container">
            <textarea 
              v-model="inputMessage"
              @keydown.enter.exact.prevent="sendMessage"
              @keydown.ctrl.enter="insertNewline"
              placeholder="输入命令，例如：加黑 192.168.1.100"
              class="message-input"
              rows="2"
            ></textarea>
            
            <div class="input-actions">
              <button class="send-btn" @click="sendMessage" :disabled="!inputMessage.trim() || isProcessing">
                <i class="fas fa-paper-plane"></i>
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, nextTick, onMounted } from 'vue'
import { useUserStore } from '@/stores/user.ts'
import { useRouter } from 'vue-router'

interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  timestamp: Date
  isThinking?: boolean
}

interface Operation {
  id: string
  command: string
  timestamp: Date
  status: 'success' | 'error' | 'pending'
}

interface NetworkStats {
  switches: number
  hosts: number
  links: number
  flows: number
  active_switches: number
  controller_status: string
}

const userStore = useUserStore()
const router = useRouter()
const inputMessage = ref('')
const messages = ref<Message[]>([])
const isProcessing = ref(false)
const controllerOnline = ref(false)
const messagesContainer = ref<HTMLElement>()

// 网络统计数据
const networkStats = ref<NetworkStats>({
  switches: 0,
  hosts: 0,
  links: 0,
  flows: 0,
  controller_status: 'unknown',
  active_switches: 0
})

// const detailedStats = ref({
//   switches: [],
//   topology: null,
//   controller: null
// }) // 暂时注释未使用的变量

// 最近操作记录
const recentOperations = ref<Operation[]>([])

// 检查控制器状态
const checkControllerStatus = async () => {
  try {
    const response = await fetch('/api/sdn/status', {
      headers: {
        'Authorization': `Bearer ${userStore.token}`
      }
    })
    
    if (response.ok) {
      const data = await response.json()
      networkStats.value.controller_status = data.status === 'connected' ? 'connected' : 'disconnected'
    } else {
      networkStats.value.controller_status = 'disconnected'
    }
  } catch (error) {
    console.error('检查控制器状态失败:', error)
    networkStats.value.controller_status = 'error'
  }
  
  // 同时刷新网络统计数据
  await loadNetworkStats()
}

// 获取网络统计数据
const loadNetworkStats = async () => {
  try {
    // 获取控制器状态
    const statusResponse = await fetch('/api/sdn/status', {
      headers: {
        'Authorization': `Bearer ${userStore.token}`
      }
    })
    
    // 获取网络拓扑
    const topologyResponse = await fetch('/api/sdn/topology', {
      headers: {
        'Authorization': `Bearer ${userStore.token}`
      }
    })
    
    // 获取交换机列表
    const switchesResponse = await fetch('/api/sdn/switches', {
      headers: {
        'Authorization': `Bearer ${userStore.token}`
      }
    })
    
    if (statusResponse.ok && topologyResponse.ok && switchesResponse.ok) {
      const statusData = await statusResponse.json()
      const topologyData = await topologyResponse.json()
      const switchesData = await switchesResponse.json()
      
      networkStats.value = {
        switches: switchesData.length || 0,
        hosts: topologyData.hosts?.length || 0,
        links: topologyData.links?.length || 0,
        flows: statusData.total_flows || 0,
        controller_status: statusData.status || 'unknown',
        active_switches: switchesData.filter((s: any) => s.status === 'connected').length || 0
      }
    }
  } catch (error) {
    console.error('获取网络统计数据失败:', error)
    networkStats.value = {
      switches: 0,
      hosts: 0,
      links: 0,
      flows: 0,
      controller_status: 'error',
      active_switches: 0
    }
  }
}

// 发送消息到RYU控制器
const sendMessage = async () => {
  if (!inputMessage.value.trim() || isProcessing.value) return

  const message = inputMessage.value.trim()
  inputMessage.value = ''
  isProcessing.value = true

  // 添加用户消息
  const userMessage: Message = {
    id: `msg_${Date.now()}`,
    role: 'user',
    content: message,
    timestamp: new Date()
  }
  
  messages.value.push(userMessage)
  await nextTick()
  scrollToBottom()

  // 添加思考消息
  const thinkingMessage: Message = {
    id: `msg_${Date.now() + 1}`,
    role: 'assistant',
    content: '控制器正在处理...',
    timestamp: new Date(),
    isThinking: true
  }
  
  messages.value.push(thinkingMessage)
  await nextTick()
  scrollToBottom()

  try {
    // 获取当前网络状态作为上下文
    const context = `交换机数量: ${networkStats.value.switches}, 活跃交换机: ${networkStats.value.active_switches}, 主机数量: ${networkStats.value.hosts}, 控制器状态: ${networkStats.value.controller_status}`
    
    // 调用Ollama SDN智能控制API
    const response = await fetch('/api/ollama/sdn-control', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${userStore.token}`
      },
      body: JSON.stringify({
        command: message,
        context: context
      })
    })

    if (response.ok) {
      const data = await response.json()
      
      // 更新思考消息为实际响应
      const thinkingIndex = messages.value.findIndex(msg => msg.id === thinkingMessage.id)
      if (thinkingIndex !== -1) {
        messages.value[thinkingIndex] = {
          ...thinkingMessage,
          content: data.response || '操作完成',
          isThinking: false
        }
      }
      
      // 记录操作
      const operation: Operation = {
        id: `op_${Date.now()}`,
        command: message,
        timestamp: new Date(),
        status: 'success' // Ollama API成功响应即为成功
      }
      
      recentOperations.value.unshift(operation)
      if (recentOperations.value.length > 10) {
        recentOperations.value = recentOperations.value.slice(0, 10)
      }
      
    } else {
      // 错误处理
      const thinkingIndex = messages.value.findIndex(msg => msg.id === thinkingMessage.id)
      if (thinkingIndex !== -1) {
        messages.value[thinkingIndex] = {
          ...thinkingMessage,
          content: '抱歉，控制器处理失败，请检查命令格式或网络连接',
          isThinking: false
        }
      }
    }
  } catch (error) {
    console.error('发送消息失败:', error)
    
    // 错误处理
    const thinkingIndex = messages.value.findIndex(msg => msg.id === thinkingMessage.id)
    if (thinkingIndex !== -1) {
      messages.value[thinkingIndex] = {
        ...thinkingMessage,
        content: `连接控制器失败: ${error instanceof Error ? error.message : '未知错误'}`,
        isThinking: false
      }
    }
  } finally {
    isProcessing.value = false
    await nextTick()
    scrollToBottom()
  }
}

// 插入命令到输入框
const insertCommand = (command: string) => {
  inputMessage.value = command
}

// 清空聊天
const clearChat = () => {
  messages.value = []
  inputMessage.value = ''
}

// 渲染消息内容
const renderMessage = (content: string) => {
  // 简单的文本渲染，支持换行
  return content.replace(/\n/g, '<br>')
}

// 格式化时间
const formatTime = (date: Date) => {
  return date.toLocaleTimeString('zh-CN', {
    hour: '2-digit',
    minute: '2-digit'
  })
}

// 滚动到底部
const scrollToBottom = () => {
  if (messagesContainer.value) {
    messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight
  }
}

// 插入换行
const insertNewline = () => {
  inputMessage.value += '\n'
}

// 初始化
onMounted(async () => {
  if (!userStore.isAuthenticated || !userStore.token) {
    router.push('/login')
    return
  }
  
  await checkControllerStatus()
  await loadNetworkStats()
  
  // 定期检查控制器状态
  setInterval(checkControllerStatus, 30000) // 每30秒检查一次
  setInterval(loadNetworkStats, 60000) // 每分钟更新一次网络统计
})
</script>

<style scoped>
.sdn-chat-container {
  height: 100vh;
  display: flex;
  flex-direction: column;
  background: #f8fafc;
}

.top-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1rem 2rem;
  background: white;
  border-bottom: 1px solid #e5e7eb;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

.left-section {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.title {
  font-size: 1.5rem;
  font-weight: 600;
  color: #1f2937;
  margin: 0;
}

.subtitle {
  color: #6b7280;
  font-size: 0.875rem;
}

.right-section {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.controller-status {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem 1rem;
  border-radius: 0.5rem;
  font-size: 0.875rem;
  font-weight: 500;
}

.controller-status.online {
  background: #dcfce7;
  color: #166534;
}

.controller-status.offline {
  background: #fef2f2;
  color: #dc2626;
}

.new-chat-btn {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem 1rem;
  background: #3b82f6;
  color: white;
  border: none;
  border-radius: 0.5rem;
  cursor: pointer;
  font-size: 0.875rem;
  font-weight: 500;
  transition: background-color 0.2s;
}

.new-chat-btn:hover {
  background: #2563eb;
}

.main-layout {
  display: flex;
  flex: 1;
  overflow: hidden;
}

.sidebar {
  width: 300px;
  background: white;
  border-right: 1px solid #e5e7eb;
  display: flex;
  flex-direction: column;
  overflow-y: auto;
}

.sidebar-header {
  padding: 1rem;
  border-bottom: 1px solid #e5e7eb;
}

.sidebar-header h3 {
  margin: 0;
  color: #1f2937;
  font-size: 1.125rem;
  font-weight: 600;
}

.network-status, .quick-commands, .recent-operations {
  padding: 1rem;
  border-bottom: 1px solid #e5e7eb;
}

.network-status h4, .quick-commands h4, .recent-operations h4 {
  margin: 0 0 0.75rem 0;
  color: #374151;
  font-size: 0.875rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.status-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 0.5rem;
  font-size: 0.875rem;
}

.status-item .label {
  color: #6b7280;
}

.status-item .value {
  color: #1f2937;
  font-weight: 500;
}

.cmd-btn {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  width: 100%;
  padding: 0.75rem;
  margin-bottom: 0.5rem;
  background: #f9fafb;
  border: 1px solid #e5e7eb;
  border-radius: 0.5rem;
  cursor: pointer;
  font-size: 0.875rem;
  color: #374151;
  transition: all 0.2s;
}

.cmd-btn:hover {
  background: #f3f4f6;
  border-color: #d1d5db;
}

.operation-list {
  max-height: 200px;
  overflow-y: auto;
}

.operation-item {
  padding: 0.5rem;
  margin-bottom: 0.5rem;
  background: #f9fafb;
  border-radius: 0.375rem;
  font-size: 0.75rem;
}

.op-time {
  color: #6b7280;
  margin-bottom: 0.25rem;
}

.op-command {
  color: #1f2937;
  font-weight: 500;
  margin-bottom: 0.25rem;
}

.op-status {
  font-weight: 500;
}

.op-status.success {
  color: #059669;
}

.op-status.error {
  color: #dc2626;
}

.op-status.pending {
  color: #d97706;
}

.chat-area {
  flex: 1;
  display: flex;
  flex-direction: column;
  background: white;
}

.auth-error {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
}

.error-content {
  text-align: center;
  color: #6b7280;
}

.error-content i {
  font-size: 3rem;
  color: #f59e0b;
  margin-bottom: 1rem;
}

.error-content h3 {
  margin: 0 0 0.5rem 0;
  color: #1f2937;
}

.login-btn {
  margin-top: 1rem;
  padding: 0.5rem 1rem;
  background: #3b82f6;
  color: white;
  border: none;
  border-radius: 0.5rem;
  cursor: pointer;
}

.messages-container {
  flex: 1;
  overflow-y: auto;
  padding: 1rem;
}

.welcome-message {
  text-align: center;
  padding: 2rem;
  color: #6b7280;
}

.welcome-content i {
  font-size: 3rem;
  color: #3b82f6;
  margin-bottom: 1rem;
}

.welcome-content h3 {
  margin: 0 0 1rem 0;
  color: #1f2937;
}

.welcome-content ul {
  text-align: left;
  display: inline-block;
  margin-top: 1rem;
}

.welcome-content code {
  background: #f3f4f6;
  padding: 0.25rem 0.5rem;
  border-radius: 0.25rem;
  font-family: 'Courier New', monospace;
}

.message {
  margin-bottom: 1.5rem;
}

.message.user .message-content {
  margin-left: 2rem;
}

.message.assistant .message-content {
  margin-right: 2rem;
}

.message-header {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-bottom: 0.5rem;
}

.avatar {
  width: 2rem;
  height: 2rem;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 0.875rem;
}

.message.user .avatar {
  background: #3b82f6;
  color: white;
}

.message.assistant .avatar {
  background: #10b981;
  color: white;
}

.role-name {
  font-weight: 500;
  color: #1f2937;
}

.message-time {
  color: #6b7280;
  font-size: 0.75rem;
}

.message-text {
  background: #f9fafb;
  padding: 0.75rem 1rem;
  border-radius: 0.75rem;
  color: #1f2937;
  line-height: 1.5;
}

.message.user .message-text {
  background: #eff6ff;
}

.thinking-animation {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  color: #6b7280;
}

.thinking-dots {
  display: flex;
  gap: 0.25rem;
}

.thinking-dots span {
  width: 0.375rem;
  height: 0.375rem;
  background: #6b7280;
  border-radius: 50%;
  animation: thinking 1.4s infinite ease-in-out;
}

.thinking-dots span:nth-child(1) {
  animation-delay: -0.32s;
}

.thinking-dots span:nth-child(2) {
  animation-delay: -0.16s;
}

@keyframes thinking {
  0%, 80%, 100% {
    transform: scale(0);
  }
  40% {
    transform: scale(1);
  }
}

.input-area {
  padding: 1rem;
  border-top: 1px solid #e5e7eb;
  background: #f9fafb;
}

.input-container {
  display: flex;
  gap: 0.75rem;
  align-items: flex-end;
}

.message-input {
  flex: 1;
  padding: 0.75rem;
  border: 1px solid #d1d5db;
  border-radius: 0.5rem;
  resize: none;
  font-family: inherit;
  font-size: 0.875rem;
  line-height: 1.5;
  background: white;
}

.message-input:focus {
  outline: none;
  border-color: #3b82f6;
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
}

.send-btn {
  padding: 0.75rem;
  background: #3b82f6;
  color: white;
  border: none;
  border-radius: 0.5rem;
  cursor: pointer;
  transition: background-color 0.2s;
}

.send-btn:hover:not(:disabled) {
  background: #2563eb;
}

.send-btn:disabled {
  background: #9ca3af;
  cursor: not-allowed;
}

.status-online {
  color: #10b981;
  font-weight: 600;
}

.status-offline {
  color: #ef4444;
  font-weight: 600;
}
</style>