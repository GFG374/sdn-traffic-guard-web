<template>
  <div>
    <!-- 页面标题 -->
    <div class="mb-6">
      <h2 class="text-[clamp(1.5rem,3vw,2rem)] font-bold text-dark">异常检测</h2>
      <p class="text-dark-2 mt-1">实时监控网络异常行为</p>
    </div>
    
    <!-- 异常检测表格 -->
    <div class="bg-white rounded-xl p-6 shadow-md mb-8">
      <div class="overflow-x-auto">
        <table class="min-w-full divide-y divide-gray-200">
          <thead>
            <tr>
              <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">时间</th>
              <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">源IP</th>
              <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">类型</th>
              <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">详情</th>
              <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">操作</th>
            </tr>
          </thead>
          <tbody class="bg-white divide-y divide-gray-200">
            <tr v-for="(anomaly, index) in anomalies" :key="index" class="hover:bg-gray-50">
              <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{{ formatTime(anomaly.timestamp) }}</td>
              <td class="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">{{ anomaly.src_ip }}</td>
              <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{{ anomaly.type }}</td>
              <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{{ anomaly.details }}</td>
              <td class="px-6 py-4 whitespace-nowrap text-sm font-medium">
                <button @click="handleAction(anomaly.src_ip, 'blacklist')" class="text-red-600 hover:text-red-900 mr-3">加黑</button>
                <button @click="handleAction(anomaly.src_ip, 'ratelimit')" class="text-yellow-600 hover:text-yellow-900">限速</button>
              </td>
            </tr>
            <tr v-if="anomalies.length === 0">
              <td colspan="5" class="px-6 py-4 text-center text-sm text-gray-500">暂无异常数据</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue';
import axios from 'axios';

// 定义数据结构
interface Anomaly {
  timestamp: number;
  src_ip: string;
  type: string;
  details: string;
}

// 响应式数据
const anomalies = ref<Anomaly[]>([]);

// 定时器
let anomaliesTimer: number | null = null;

// 格式化时间
const formatTime = (timestamp: number): string => {
  const date = new Date(timestamp * 1000);
  return date.toLocaleString('zh-CN', {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit'
  });
};

// 获取异常数据
const fetchAnomalies = async () => {
  try {
    const response = await axios.get('/v1/anomalies');
    anomalies.value = response.data;
  } catch (error) {
    console.error('获取异常数据失败:', error);
  }
};

// 处理操作按钮
const handleAction = async (ip: string, action: 'blacklist' | 'ratelimit') => {
  try {
    const command = action === 'blacklist' ? `block ${ip}` : `limit ${ip}`;
    const response = await axios.post('/v1/chat', {
      user_id: 'web',
      message: command
    });
    
    // 显示操作结果
    alert(response.data.reply || '操作成功');
    
    // 刷新数据
    fetchAnomalies();
  } catch (error) {
    console.error('操作失败:', error);
    alert('操作失败，请重试');
  }
};

onMounted(() => {
  // 初始加载数据
  fetchAnomalies();
  
  // 设置定时器
  anomaliesTimer = window.setInterval(fetchAnomalies, 3000); // 每3秒更新异常
});

onUnmounted(() => {
  // 清除定时器
  if (anomaliesTimer) window.clearInterval(anomaliesTimer);
});
</script>

<style scoped>
/* 样式通过Tailwind工具类实现 */
</style>