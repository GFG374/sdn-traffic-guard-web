<template>
  <div>
    <!-- 页面标题 -->
    <div class="mb-6">
      <h2 class="text-[clamp(1.5rem,3vw,2rem)] font-bold text-dark">AI 助手</h2>
      <p class="text-dark-2 mt-1">使用自然语言与网络管理系统交互</p>
    </div>
    
    <!-- 聊天界面 -->
    <div class="bg-white rounded-xl shadow-md h-[calc(100vh-200px)] flex flex-col">
      <!-- 聊天历史记录 -->
      <div ref="chatHistoryRef" class="flex-1 p-6 overflow-y-auto">
        <div v-for="(message, index) in chatHistory" :key="index" class="mb-4">
          <!-- 用户消息 -->
          <div v-if="message.sender === 'user'" class="flex justify-end">
            <div class="bg-blue-100 text-blue-800 rounded-lg py-2 px-4 max-w-[80%]">
              <p>{{ message.content }}</p>
              <span class="text-xs text-blue-600 block text-right mt-1">{{ formatTime(message.timestamp) }}</span>
            </div>
          </div>
          
          <!-- AI消息 -->
          <div v-else class="flex justify-start">
            <div class="bg-gray-100 text-gray-800 rounded-lg py-2 px-4 max-w-[80%]">
              <p>{{ message.content }}</p>
              <span class="text-xs text-gray-500 block mt-1">{{ formatTime(message.timestamp) }}</span>
            </div>
          </div>
        </div>
        
        <!-- 加载中指示器 -->
        <div v-if="isLoading" class="flex justify-start mb-4">
          <div class="bg-gray-100 text-gray-800 rounded-lg py-2 px-4">
            <div class="flex space-x-2">
              <div class="w-2 h-2 rounded-full bg-gray-400 animate-bounce"></div>
              <div class="w-2 h-2 rounded-full bg-gray-400 animate-bounce" style="animation-delay: 0.2s"></div>
              <div class="w-2 h-2 rounded-full bg-gray-400 animate-bounce" style="animation-delay: 0.4s"></div>
            </div>
          </div>
        </div>
      </div>
      
      <!-- 输入区域 -->
      <div class="border-t p-4">
        <div class="flex">
          <input 
            v-model="userInput" 
            type="text" 
            placeholder="输入指令或问题..." 
            class="flex-1 border rounded-l-lg px-4 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
            @keyup.enter="sendMessage"
          />
          <button 
            @click="sendMessage" 
            class="bg-blue-600 text-white px-4 py-2 rounded-r-lg hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500"
            :disabled="isLoading || !userInput.trim()"
          >
            发送
          </button>
        </div>
        <div class="mt-2 text-sm text-gray-500">
          <p>示例: "查看当前网络状态"、"限制IP 192.168.1.100的速率"、"将192.168.1.200加入黑名单"</p>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, nextTick, watch } from 'vue';
import axios from 'axios';

// 定义消息结构
interface ChatMessage {
  sender: 'user' | 'ai';
  content: string;
  timestamp: number;
}

// 响应式数据
const chatHistory = ref<ChatMessage[]>([]);
const userInput = ref('');
const isLoading = ref(false);
const chatHistoryRef = ref<HTMLElement | null>(null);

// 轮询间隔(毫秒)
const POLLING_INTERVAL = 1000;
let pollingTimer: number | null = null;

// 格式化时间
const formatTime = (timestamp: number): string => {
  const date = new Date(timestamp * 1000);
  return date.toLocaleTimeString('zh-CN', {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit'
  });
};

// 发送消息
const sendMessage = async () => {
  const message = userInput.value.trim();
  if (!message || isLoading.value) return;
  
  // 添加用户消息到历史记录
  chatHistory.value.push({
    sender: 'user',
    content: message,
    timestamp: Math.floor(Date.now() / 1000)
  });
  
  // 清空输入框
  userInput.value = '';
  
  // 设置加载状态
  isLoading.value = true;
  
  try {
    // 发送消息到后端
    const response = await axios.post('/v1/chat', {
      user_id: 'web',
      message: message
    });
    
    // 添加AI回复到历史记录
    chatHistory.value.push({
      sender: 'ai',
      content: response.data.response || '我理解了您的指令，正在处理中...',
      timestamp: Math.floor(Date.now() / 1000)
    });
  } catch (error) {
    console.error('发送消息失败:', error);
    
    // 添加错误消息
    chatHistory.value.push({
      sender: 'ai',
      content: '抱歉，发送消息时出现错误，请稍后再试。',
      timestamp: Math.floor(Date.now() / 1000)
    });
  } finally {
    // 取消加载状态
    isLoading.value = false;
    
    // 滚动到底部
    scrollToBottom();
  }
};

// 滚动到底部
const scrollToBottom = async () => {
  await nextTick();
  if (chatHistoryRef.value) {
    chatHistoryRef.value.scrollTop = chatHistoryRef.value.scrollHeight;
  }
};

// 加载历史消息
const loadChatHistory = async () => {
  try {
    const response = await axios.get('/v1/chat/history?user_id=web');
    if (response.data && Array.isArray(response.data)) {
      // 转换格式
      chatHistory.value = response.data.map((item: any) => ({
        sender: item.is_user ? 'user' : 'ai',
        content: item.message,
        timestamp: item.timestamp
      }));
      
      // 滚动到底部
      scrollToBottom();
    }
  } catch (error) {
    console.error('加载聊天历史失败:', error);
    
    // 添加欢迎消息
    chatHistory.value = [{
      sender: 'ai',
      content: '欢迎使用SDN Guardian AI助手，我可以帮助您管理网络。请输入您的指令或问题。',
      timestamp: Math.floor(Date.now() / 1000)
    }];
  }
};

// 监听聊天历史变化，自动滚动到底部
watch(chatHistory, () => {
  scrollToBottom();
});

onMounted(() => {
  // 加载历史消息
  loadChatHistory();
  
  // 设置轮询
  pollingTimer = window.setInterval(() => {
    // 如果正在加载，跳过本次轮询
    if (isLoading.value) return;
    
    // 获取最新消息
    loadChatHistory();
  }, POLLING_INTERVAL);
  
  // 初始滚动到底部
  scrollToBottom();
});

onUnmounted(() => {
  // 清除轮询定时器
  if (pollingTimer) window.clearInterval(pollingTimer);
});
</script>

<style scoped>
/* 样式通过Tailwind工具类实现 */
</style>