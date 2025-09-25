<template>
  <div>
    <!-- 页面标题 -->
    <div class="mb-6">
      <h2 class="text-[clamp(1.5rem,3vw,2rem)] font-bold text-dark">黑白名单管理</h2>
      <p class="text-dark-2 mt-1">管理和配置网络中的IP黑白名单规则</p>
    </div>
    
    <!-- 黑名单统计和操作 -->
    <div class="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
      <div class="bg-white rounded-xl p-6 card-shadow">
        <div class="flex items-start justify-between">
          <div>
            <p class="text-dark-2 mb-1">已拦截IP总数</p>
            <h3 class="text-3xl font-bold text-dark">{{ blacklist.length }}</h3>
            <p class="text-success text-sm mt-2 flex items-center">
              <i class="fa fa-arrow-up mr-1"></i> 3 个 (今日)
            </p>
          </div>
          <div class="w-12 h-12 rounded-lg bg-danger/10 flex items-center justify-center text-danger">
            <i class="fa fa-ban text-xl"></i>
          </div>
        </div>
      </div>
      
      <div class="bg-white rounded-xl p-6 card-shadow">
        <div class="flex items-start justify-between">
          <div>
            <p class="text-dark-2 mb-1">今日拦截次数</p>
            <h3 class="text-3xl font-bold text-dark">156</h3>
            <p class="text-danger text-sm mt-2 flex items-center">
              <i class="fa fa-arrow-up mr-1"></i> 24 次 (较昨日)
            </p>
          </div>
          <div class="w-12 h-12 rounded-lg bg-warning/10 flex items-center justify-center text-warning">
            <i class="fa fa-shield-alt text-xl"></i>
          </div>
        </div>
      </div>
      
      <div class="bg-white rounded-xl p-6 card-shadow">
        <div class="flex items-start justify-between">
          <div>
            <p class="text-dark-2 mb-1">拦截模式</p>
            <h3 class="text-3xl font-bold text-dark">自动+手动</h3>
            <p class="text-dark-2 text-sm mt-2 flex items-center">
              <i class="fa fa-cog mr-1"></i> 可在设置中调整
            </p>
          </div>
          <div class="w-12 h-12 rounded-lg bg-primary/10 flex items-center justify-center text-primary">
            <i class="fa fa-sliders-h text-xl"></i>
          </div>
        </div>
      </div>
    </div>
    
    <!-- 黑名单列表 -->
    <div class="bg-white rounded-xl p-6 card-shadow mb-8">
      <div class="flex flex-wrap items-center justify-between gap-4 mb-6">
        <h3 class="font-semibold text-lg">黑名单列表</h3>
        <div class="flex flex-wrap gap-3">
          <div class="relative">
            <span class="absolute inset-y-0 left-0 flex items-center pl-3">
              <i class="fa fa-search text-dark-2"></i>
            </span>
            <input 
              type="text" 
              placeholder="搜索IP地址..." 
              v-model="searchQuery"
              class="pl-10 pr-4 py-2 rounded-lg border border-light-2 focus:outline-none focus:ring-2 focus:ring-primary/30 focus:border-primary transition-all-300 w-full md:w-64"
            >
          </div>
          <button 
            class="px-4 py-2 bg-primary text-white rounded-lg hover:bg-primary/90 transition-all-300 flex items-center"
            @click="showAddBlacklistModal = true"
          >
            <i class="fa fa-plus mr-2"></i> 添加IP
          </button>
        </div>
      </div>
      
      <div class="overflow-x-auto">
        <table class="w-full">
          <thead>
            <tr class="border-b border-light-2">
              <th class="text-left py-4 px-4 font-semibold text-dark-2">IP地址</th>
              <th class="text-left py-4 px-4 font-semibold text-dark-2">拦截原因</th>
              <th class="text-left py-4 px-4 font-semibold text-dark-2">拦截类型</th>
              <th class="text-left py-4 px-4 font-semibold text-dark-2">添加时间</th>
              <th class="text-left py-4 px-4 font-semibold text-dark-2">拦截次数</th>
              <th class="text-left py-4 px-4 font-semibold text-dark-2">操作</th>
            </tr>
          </thead>
          <tbody>
            <tr 
              v-for="item in filteredBlacklist" 
              :key="item.id"
              class="border-b border-light-2 hover:bg-gray-50 transition-all-300"
            >
              <td class="py-4 px-4 font-medium">{{ item.ip_address }}</td>
              <td class="py-4 px-4">{{ item.description }}</td>
              <td class="py-4 px-4">
                <span 
                  :class="item.rule_type === 'auto' ? 'bg-warning/10 text-warning' : 'bg-primary/10 text-primary'" 
                  class="px-2 py-1 text-xs rounded-full"
                >
                  {{ item.rule_type === 'auto' ? '自动拦截' : '手动添加' }}
                </span>
              </td>
              <td class="py-4 px-4 text-dark-2">{{ new Date(item.created_at).toLocaleString() }}</td>
              <td class="py-4 px-4">
                <span class="text-danger font-medium">0</span>
              </td>
              <td class="py-4 px-4">
                <button 
                  class="text-primary hover:text-primary/80 mr-3 transition-all-300"
                  @click="viewDetails(item)"
                >
                  <i class="fa fa-eye"></i>
                </button>
                <button 
                  class="text-success hover:text-success/80 mr-3 transition-all-300"
                  @click="removeFromBlacklist(item.id, item.ip_address)"
                >
                  <i class="fa fa-check-circle"></i>
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
      
      <div class="flex items-center justify-between mt-6">
        <p class="text-sm text-dark-2">显示 1 至 {{ filteredBlacklist.length }} 条，共 {{ blacklist.length }} 条</p>
        <div class="flex space-x-1">
          <button 
            class="w-8 h-8 flex items-center justify-center rounded border border-light-2 text-dark-2 hover:border-primary hover:text-primary transition-all-300 disabled:opacity-50" 
            :disabled="currentPage === 1"
            @click="currentPage--"
          >
            <i class="fa fa-chevron-left text-xs"></i>
          </button>
          <button class="w-8 h-8 flex items-center justify-center rounded bg-primary text-white">{{ currentPage }}</button>
          <button 
            class="w-8 h-8 flex items-center justify-center rounded border border-light-2 hover:border-primary hover:text-primary transition-all-300"
            :disabled="currentPage >= totalPages"
            @click="currentPage++"
          >
            <i class="fa fa-chevron-right text-xs"></i>
          </button>
        </div>
      </div>
    </div>
    
    <!-- 拦截规则配置 -->
    <div class="bg-white rounded-xl p-6 card-shadow">
      <h3 class="font-semibold text-lg mb-6">拦截规则配置</h3>
      
      <form @submit.prevent="saveRules">
        <div class="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
          <div>
            <label class="block text-sm font-medium text-dark-2 mb-1">自动拦截阈值</label>
            <input 
              type="number" 
              v-model="rules.autoBlockThreshold"
              min="1" 
              max="100" 
              class="w-full px-4 py-2 rounded-lg border border-light-2 focus:outline-none focus:ring-2 focus:ring-primary/30 focus:border-primary transition-all-300"
            >
            <p class="text-xs text-dark-2 mt-1">单位：次/分钟，超过此阈值将自动拦截</p>
          </div>
          
          <div>
            <label class="block text-sm font-medium text-dark-2 mb-1">拦截持续时间</label>
            <select 
              v-model="rules.blockDuration"
              class="w-full px-4 py-2 rounded-lg border border-light-2 focus:outline-none focus:ring-2 focus:ring-primary/30 focus:border-primary transition-all-300"
            >
              <option>1小时</option>
              <option>24小时</option>
              <option>7天</option>
              <option>永久</option>
            </select>
          </div>
        </div>
        
        <div class="mb-6">
          <label class="block text-sm font-medium text-dark-2 mb-3">自动拦截类型</label>
          
          <div class="space-y-3">
            <div class="flex items-center">
              <input 
                type="checkbox" 
                id="portScan" 
                v-model="rules.autoBlockTypes" 
                value="端口扫描"
                class="w-4 h-4 text-primary focus:ring-primary border-light-2 rounded"
              >
              <label for="portScan" class="ml-2 text-dark-2">端口扫描攻击</label>
            </div>
            
            <div class="flex items-center">
              <input 
                type="checkbox" 
                id="bruteForce" 
                v-model="rules.autoBlockTypes" 
                value="暴力破解"
                class="w-4 h-4 text-primary focus:ring-primary border-light-2 rounded"
              >
              <label for="bruteForce" class="ml-2 text-dark-2">暴力破解尝试</label>
            </div>
            
            <div class="flex items-center">
              <input 
                type="checkbox" 
                id="ddos" 
                v-model="rules.autoBlockTypes" 
                value="DDoS攻击"
                class="w-4 h-4 text-primary focus:ring-primary border-light-2 rounded"
              >
              <label for="ddos" class="ml-2 text-dark-2">DDoS攻击行为</label>
            </div>
            
            <div class="flex items-center">
              <input 
                type="checkbox" 
                id="malicious" 
                v-model="rules.autoBlockTypes" 
                value="恶意请求"
                class="w-4 h-4 text-primary focus:ring-primary border-light-2 rounded"
              >
              <label for="malicious" class="ml-2 text-dark-2">恶意请求模式</label>
            </div>
          </div>
        </div>
        
        <div class="mb-6">
          <label class="block text-sm font-medium text-dark-2 mb-1">白名单IP（不拦截）</label>
          <textarea 
            v-model="rules.whitelist"
            placeholder="每行输入一个IP地址"
            rows="4"
            class="w-full px-4 py-2 rounded-lg border border-light-2 focus:outline-none focus:ring-2 focus:ring-primary/30 focus:border-primary transition-all-300"
          ></textarea>
        </div>
        
        <button 
          type="submit" 
          class="px-6 py-2.5 bg-primary text-white rounded-lg hover:bg-primary/90 transition-all-300"
        >
          保存规则配置
        </button>
      </form>
    </div>
    
    <!-- 添加IP到黑名单模态框 -->
    <div 
      v-if="showAddBlacklistModal" 
      class="fixed inset-0 bg-black/50 z-50 flex items-center justify-center"
      @click="closeModal"
    >
      <div 
        class="bg-white rounded-xl p-6 w-full max-w-md mx-4 transform transition-all-300 scale-100 opacity-100"
        @click.stop
      >
        <div class="flex items-center justify-between mb-4">
          <h3 class="font-semibold text-lg">添加IP到黑名单</h3>
          <button 
            class="text-dark-2 hover:text-dark transition-all-300"
            @click="closeModal"
          >
            <i class="fa fa-times"></i>
          </button>
        </div>
        
        <form @submit.prevent="addIPToBlacklist">
          <div class="mb-4">
            <label class="block text-sm font-medium text-dark-2 mb-1">IP地址</label>
            <input 
              type="text" 
              v-model="newBlacklistItem.ip_address"
              placeholder="例如：192.168.1.100"
              class="w-full px-4 py-2 rounded-lg border border-light-2 focus:outline-none focus:ring-2 focus:ring-primary/30 focus:border-primary transition-all-300"
            >
          </div>
          
          <div class="mb-4">
            <label class="block text-sm font-medium text-dark-2 mb-1">拦截原因</label>
            <select 
              v-model="newBlacklistItem.description"
              class="w-full px-4 py-2 rounded-lg border border-light-2 focus:outline-none focus:ring-2 focus:ring-primary/30 focus:border-primary transition-all-300"
            >
              <option>端口扫描攻击</option>
              <option>暴力破解尝试</option>
              <option>异常流量行为</option>
              <option>恶意软件传播</option>
              <option>其他安全威胁</option>
            </select>
          </div>
          
          <div class="mb-4">
            <label class="block text-sm font-medium text-dark-2 mb-1">规则类型</label>
            <select 
              v-model="newBlacklistItem.rule_type"
              class="w-full px-4 py-2 rounded-lg border border-light-2 focus:outline-none focus:ring-2 focus:ring-primary/30 focus:border-primary transition-all-300"
            >
              <option value="ip">IP地址</option>
              <option value="mac">MAC地址</option>
              <option value="range">IP范围</option>
            </select>
          </div>
          
          <div class="flex space-x-3 mt-6">
            <button 
              type="button" 
              class="flex-1 py-2.5 border border-light-2 text-dark-2 rounded-lg hover:bg-gray-50 transition-all-300"
              @click="closeModal"
            >
              取消
            </button>
            <button 
              type="submit" 
              class="flex-1 py-2.5 bg-danger text-white rounded-lg hover:bg-danger/90 transition-all-300"
            >
              确认拦截
            </button>
          </div>
        </form>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue';
import axios from 'axios';

// 黑名单数据类型定义
interface BlacklistItem {
  id: number;
  ip_address: string;
  mac_address?: string;
  description?: string;
  rule_type: string;
  is_active: boolean;
  created_by: number;
  created_at: string;
  updated_at: string;
}

// 白名单数据类型定义
interface WhitelistItem {
  id: number;
  ip_address: string;
  mac_address?: string;
  description?: string;
  rule_type: string;
  is_active: boolean;
  created_by: number;
  created_at: string;
  updated_at: string;
}

// 拦截规则类型定义
interface BlockRules {
  autoBlockThreshold: number;
  blockDuration: string;
  autoBlockTypes: string[];
  whitelist: string;
}

// 状态数据
const blacklist = ref<BlacklistItem[]>([]);
const whitelist = ref<WhitelistItem[]>([]);
const searchQuery = ref('');
const currentPage = ref(1);
const itemsPerPage = 5;
const showAddBlacklistModal = ref(false);
const loading = ref(false);
const newBlacklistItem = ref({
  ip_address: '',
  description: '异常流量行为',
  rule_type: 'ip',
  is_active: true
});
const rules = ref<BlockRules>({
  autoBlockThreshold: 20,
  blockDuration: '24小时',
  autoBlockTypes: ['端口扫描', '暴力破解'],
  whitelist: '192.168.1.1\n192.168.1.2\n10.0.0.1'
});

// 获取黑名单数据
const loadBlacklist = async () => {
  try {
    loading.value = true;
    const response = await axios.get('/api/blacklist');
    blacklist.value = response.data;
  } catch (error) {
    console.error('获取黑名单失败:', error);
    alert('获取黑名单失败，请重试');
  } finally {
    loading.value = false;
  }
};

// 获取白名单数据
const loadWhitelist = async () => {
  try {
    const response = await axios.get('/api/whitelist');
    whitelist.value = response.data;
  } catch (error) {
    console.error('获取白名单失败:', error);
  }
};

// 初始化数据
onMounted(() => {
  loadBlacklist();
  loadWhitelist();
});

// 过滤黑名单数据
const filteredBlacklist = computed(() => {
  return blacklist.value
    .filter(item => item.ip_address.includes(searchQuery.value))
    .slice((currentPage.value - 1) * itemsPerPage, currentPage.value * itemsPerPage);
});

// 计算总页数
const totalPages = computed(() => {
  return Math.ceil(blacklist.value.filter(item => 
    item.ip_address.includes(searchQuery.value)
  ).length / itemsPerPage);
});

// 黑名单操作方法
const viewDetails = (item: BlacklistItem) => {
  console.log('查看黑名单详情:', item);
  // 可以打开详情模态框
};

const removeFromBlacklist = async (id: number, ip: string) => {
  if (confirm(`确定要将 ${ip} 从黑名单中移除吗？`)) {
    try {
      await axios.delete(`/api/blacklist/${id}`);
      await loadBlacklist();
      alert(`IP ${ip} 已成功从黑名单中移除`);
    } catch (error) {
      console.error('移除黑名单失败:', error);
      alert('移除黑名单失败，请重试');
    }
  }
};

const addIPToBlacklist = async () => {
  if (!newBlacklistItem.value.ip_address) {
    alert('请输入IP地址');
    return;
  }
  
  // 简单的IP格式验证
  const ipRegex = /^(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})$/;
  if (!ipRegex.test(newBlacklistItem.value.ip_address)) {
    alert('请输入有效的IP地址');
    return;
  }
  
  if (blacklist.value.some(item => item.ip_address === newBlacklistItem.value.ip_address)) {
    alert('该IP已在黑名单中');
    return;
  }
  
  try {
    await axios.post('/api/blacklist', newBlacklistItem.value);
    await loadBlacklist();
    closeModal();
    alert(`IP ${newBlacklistItem.value.ip_address} 已成功添加到黑名单`);
  } catch (error) {
    console.error('添加黑名单失败:', error);
    alert('添加黑名单失败，请重试');
  }
};

// 关闭模态框
const closeModal = () => {
  showAddBlacklistModal.value = false;
  newBlacklistItem.value = {
    ip_address: '',
    description: '异常流量行为',
    rule_type: 'ip',
    is_active: true
  };
};

// 保存规则配置
const saveRules = () => {
  console.log('保存拦截规则配置:', rules.value);
  alert('拦截规则配置已保存');
};
</script>

<style scoped>
/* 黑名单管理样式已通过Tailwind工具类实现 */
</style>
