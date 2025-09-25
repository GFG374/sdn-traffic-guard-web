<template>
  <div class="ai-nav-item">
    <router-link 
      to="/ai-assistant" 
      class="nav-link"
      :class="{ active: $route.path === '/ai-assistant' }"
    >
      <div class="nav-icon">
        <i class="fas fa-robot"></i>
      </div>
      <span class="nav-text">AI助手</span>
      <div class="nav-badge" v-if="hasNewMessages">
        <span class="badge-dot"></span>
      </div>
    </router-link>
    
    <!-- AI功能快捷菜单 -->
    <div class="ai-quick-actions" v-if="showQuickActions">
      <button class="quick-action-btn" @click="startQuickChat('文档分析')">
        <i class="fas fa-file-alt"></i>
        文档分析
      </button>
      <button class="quick-action-btn" @click="startQuickChat('数据可视化')">
        <i class="fas fa-chart-bar"></i>
        数据可视化
      </button>
      <button class="quick-action-btn" @click="startQuickChat('网络诊断')">
        <i class="fas fa-network-wired"></i>
        网络诊断
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'

const router = useRouter()


const showQuickActions = ref(false)
const hasNewMessages = ref(false)

const startQuickChat = (type: string) => {
  const query = type ? { quickStart: type } : {}
  router.push({ path: '/ai-assistant', query })
}

// 检查是否有新消息（可以从API获取）
const checkNewMessages = async () => {
  // 这里可以添加实际的API调用来检查新消息
  hasNewMessages.value = false
}

// 定期检查新消息
setInterval(checkNewMessages, 30000)
</script>

<style scoped>
.ai-nav-item {
  position: relative;
}

.nav-link {
  display: flex;
  align-items: center;
  padding: 0.75rem 1rem;
  color: #64748b;
  text-decoration: none;
  transition: all 0.3s ease;
  border-radius: 0.375rem;
  margin: 0.125rem 0;
  position: relative;
}

.nav-link:hover {
  background-color: #f1f5f9;
  color: #1e293b;
}

.nav-link.active {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  box-shadow: 0 2px 8px rgba(102, 126, 234, 0.3);
}

.nav-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 1.5rem;
  margin-right: 0.75rem;
}

.nav-text {
  font-weight: 500;
  font-size: 0.875rem;
}

.nav-badge {
  margin-left: auto;
}

.badge-dot {
  display: inline-block;
  width: 8px;
  height: 8px;
  background-color: #ef4444;
  border-radius: 50%;
  animation: pulse 2s infinite;
}

@keyframes pulse {
  0% {
    opacity: 1;
    transform: scale(1);
  }
  50% {
    opacity: 0.5;
    transform: scale(1.2);
  }
  100% {
    opacity: 1;
    transform: scale(1);
  }
}

.ai-quick-actions {
  position: absolute;
  top: 100%;
  left: 0;
  right: 0;
  background: white;
  border: 1px solid #e2e8f0;
  border-radius: 0.375rem;
  box-shadow: 0 10px 25px rgba(0, 0, 0, 0.1);
  padding: 0.5rem;
  margin-top: 0.25rem;
  z-index: 1000;
}

.quick-action-btn {
  display: flex;
  align-items: center;
  width: 100%;
  padding: 0.5rem 0.75rem;
  margin: 0.125rem 0;
  background: none;
  border: none;
  border-radius: 0.25rem;
  color: #475569;
  font-size: 0.875rem;
  cursor: pointer;
  transition: all 0.2s ease;
}

.quick-action-btn:hover {
  background-color: #f8fafc;
  color: #1e293b;
}

.quick-action-btn i {
  margin-right: 0.5rem;
  font-size: 0.875rem;
}

/* 深色主题支持 */
:deep(.dark .nav-link) {
  color: #94a3b8;
}

:deep(.dark .nav-link:hover) {
  background-color: #334155;
  color: #e2e8f0;
}

:deep(.dark .nav-link.active) {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
}

:deep(.dark .ai-quick-actions) {
  background: #1e293b;
  border-color: #334155;
}

:deep(.dark .quick-action-btn) {
  color: #cbd5e1;
}

:deep(.dark .quick-action-btn:hover) {
  background-color: #334155;
  color: #e2e8f0;
}
</style>