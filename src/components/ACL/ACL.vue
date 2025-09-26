<template>
  <div>
    <!-- 页面标题 -->
    <div class="mb-6">
      <h2 class="text-[clamp(1.5rem,3vw,2rem)] font-bold text-dark">ACL管理</h2>
      <p class="text-dark-2 mt-1">管理黑白名单IP地址</p>
    </div>
    
    <!-- 黑白名单Tab -->
    <div class="bg-white rounded-xl shadow-md overflow-hidden">
      <div class="border-b border-gray-200">
        <nav class="flex -mb-px">
          <button 
            @click="activeTab = 'whitelist'" 
            :class="[
              'py-4 px-6 text-center border-b-2 font-medium text-sm',
              activeTab === 'whitelist' 
                ? 'border-blue-500 text-blue-600' 
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
            ]"
          >
            白名单
          </button>
          <button 
            @click="activeTab = 'blacklist'" 
            :class="[
              'py-4 px-6 text-center border-b-2 font-medium text-sm',
              activeTab === 'blacklist' 
                ? 'border-blue-500 text-blue-600' 
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
            ]"
          >
            黑名单
          </button>
        </nav>
      </div>
      
      <!-- 白名单表格 -->
      <div v-if="activeTab === 'whitelist'" class="p-6">
        <div class="flex justify-between mb-6">
          <h3 class="text-lg font-semibold">白名单IP列表</h3>
          <button @click="showAddModal('whitelist')" class="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 transition-colors">
            添加白名单
          </button>
        </div>
        
        <div class="overflow-x-auto">
          <table class="min-w-full divide-y divide-gray-200">
            <thead>
              <tr>
                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">IP地址</th>
                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">添加时间</th>
                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">过期时间</th>
                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">操作</th>
              </tr>
            </thead>
            <tbody class="bg-white divide-y divide-gray-200">
              <tr v-for="(item, index) in whitelist" :key="index" class="hover:bg-gray-50">
                <td class="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">{{ item.ip }}</td>
                <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{{ formatTime(item.add_time) }}</td>
                <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                  {{ item.expire_time ? formatTime(item.expire_time) : '永不过期' }}
                </td>
                <td class="px-6 py-4 whitespace-nowrap text-sm font-medium">
                  <button @click="handleDelete(item.ip, 'whitelist')" class="text-red-600 hover:text-red-900">删除</button>
                </td>
              </tr>
              <tr v-if="whitelist.length === 0">
                <td colspan="4" class="px-6 py-4 text-center text-sm text-gray-500">暂无白名单IP</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
      
      <!-- 黑名单表格 -->
      <div v-if="activeTab === 'blacklist'" class="p-6">
        <div class="flex justify-between mb-6">
          <h3 class="text-lg font-semibold">黑名单IP列表</h3>
          <button @click="showAddModal('blacklist')" class="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 transition-colors">
            添加黑名单
          </button>
        </div>
        
        <div class="overflow-x-auto">
          <table class="min-w-full divide-y divide-gray-200">
            <thead>
              <tr>
                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">IP地址</th>
                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">添加时间</th>
                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">过期时间</th>
                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">操作</th>
              </tr>
            </thead>
            <tbody class="bg-white divide-y divide-gray-200">
              <tr v-for="(item, index) in blacklist" :key="index" class="hover:bg-gray-50">
                <td class="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">{{ item.ip }}</td>
                <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{{ formatTime(item.add_time) }}</td>
                <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                  {{ item.expire_time ? formatTime(item.expire_time) : '永不过期' }}
                </td>
                <td class="px-6 py-4 whitespace-nowrap text-sm font-medium">
                  <button @click="handleDelete(item.ip, 'blacklist')" class="text-red-600 hover:text-red-900">删除</button>
                </td>
              </tr>
              <tr v-if="blacklist.length === 0">
                <td colspan="4" class="px-6 py-4 text-center text-sm text-gray-500">暂无黑名单IP</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
    
    <!-- 添加IP模态框 -->
    <div v-if="showModal" class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div class="bg-white rounded-lg shadow-xl p-6 w-full max-w-md">
        <h3 class="text-lg font-semibold mb-4">添加{{ modalType === 'whitelist' ? '白' : '黑' }}名单IP</h3>
        
        <div class="mb-4">
          <label class="block text-sm font-medium text-gray-700 mb-1">IP地址</label>
          <input 
            v-model="newIp" 
            type="text" 
            class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            placeholder="请输入IP地址"
          />
        </div>
        
        <div class="mb-6">
          <label class="block text-sm font-medium text-gray-700 mb-1">过期时间（可选）</label>
          <input 
            v-model="expireTime" 
            type="datetime-local" 
            class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>
        
        <div class="flex justify-end space-x-3">
          <button 
            @click="closeModal" 
            class="px-4 py-2 border border-gray-300 rounded-md text-gray-700 hover:bg-gray-50"
          >
            取消
          </button>
          <button 
            @click="handleAdd" 
            class="px-4 py-2 bg-blue-500 text-white rounded-md hover:bg-blue-600"
          >
            确认添加
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue';
import axios from 'axios';

// 定义数据结构
interface ACLEntry {
  ip: string;
  add_time: number;
  expire_time?: number;
}

// 响应式数据
const whitelist = ref<ACLEntry[]>([]);
const blacklist = ref<ACLEntry[]>([]);
const activeTab = ref<'whitelist' | 'blacklist'>('whitelist');
const showModal = ref(false);
const modalType = ref<'whitelist' | 'blacklist'>('whitelist');
const newIp = ref('');
const expireTime = ref('');

// 定时器
let updateTimer: number | null = null;

// 格式化时间
const formatTime = (timestamp?: number): string => {
  if (!timestamp) return '永不过期';
  const date = new Date(timestamp * 1000);
  return date.toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit'
  });
};

// 获取ACL数据
const fetchACL = async () => {
  try {
    const response = await axios.get('/v1/acl');
    whitelist.value = response.data.whitelist || [];
    blacklist.value = response.data.blacklist || [];
  } catch (error) {
    console.error('获取ACL数据失败:', error);
  }
};

// 显示添加模态框
const showAddModal = (type: 'whitelist' | 'blacklist') => {
  modalType.value = type;
  showModal.value = true;
  newIp.value = '';
  expireTime.value = '';
};

// 关闭模态框
const closeModal = () => {
  showModal.value = false;
};

// 处理添加IP
const handleAdd = async () => {
  if (!newIp.value) {
    alert('请输入IP地址');
    return;
  }
  
  try {
    const command = modalType.value === 'whitelist' 
      ? `whitelist add ${newIp.value}${expireTime.value ? ' ' + new Date(expireTime.value).getTime() / 1000 : ''}`
      : `block ${newIp.value}${expireTime.value ? ' ' + new Date(expireTime.value).getTime() / 1000 : ''}`;
    
    const response = await axios.post('/v1/chat', {
      user_id: 'web',
      message: command
    });
    
    // 显示操作结果
    alert(response.data.reply || '添加成功');
    
    // 关闭模态框并刷新数据
    closeModal();
    fetchACL();
  } catch (error) {
    console.error('添加失败:', error);
    alert('添加失败，请重试');
  }
};

// 处理删除IP
const handleDelete = async (ip: string, type: 'whitelist' | 'blacklist') => {
  try {
    const command = type === 'whitelist' ? `whitelist remove ${ip}` : `unblock ${ip}`;
    const response = await axios.post('/v1/chat', {
      user_id: 'web',
      message: command
    });
    
    // 显示操作结果
    alert(response.data.reply || '删除成功');
    
    // 刷新数据
    fetchACL();
  } catch (error) {
    console.error('删除失败:', error);
    alert('删除失败，请重试');
  }
};

onMounted(() => {
  // 初始加载数据
  fetchACL();
  
  // 设置定时器
  updateTimer = window.setInterval(fetchACL, 5000); // 每5秒更新一次
});

onUnmounted(() => {
  // 清除定时器
  if (updateTimer) window.clearInterval(updateTimer);
});
</script>

<style scoped>
/* 样式通过Tailwind工具类实现 */
</style>