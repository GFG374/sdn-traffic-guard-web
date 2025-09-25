<template>
  <div>
    <!-- 页面标题 -->
    <div class="mb-6">
      <h2 class="text-[clamp(1.5rem,3vw,2rem)] font-bold text-dark">链路管理</h2>
      <p class="text-dark-2 mt-1">管理和配置网络中的所有链路连接</p>
    </div>
    
    <!-- 链路列表 -->
    <div class="bg-white rounded-xl p-6 card-shadow mb-8">
      <div class="flex flex-wrap items-center justify-between gap-4 mb-6">
        <h3 class="font-semibold text-lg">链路列表</h3>
        <div class="flex flex-wrap gap-3">
          <div class="relative">
            <span class="absolute inset-y-0 left-0 flex items-center pl-3">
              <i class="fa fa-search text-dark-2"></i>
            </span>
            <input 
              type="text" 
              placeholder="搜索链路ID..." 
              v-model="searchQuery"
              class="pl-10 pr-4 py-2 rounded-lg border border-light-2 focus:outline-none focus:ring-2 focus:ring-primary/30 focus:border-primary transition-all-300 w-full md:w-64"
            >
          </div>
          <button 
            class="px-4 py-2 bg-primary text-white rounded-lg hover:bg-primary/90 transition-all-300 flex items-center"
            @click="showAddLinkModal = true"
          >
            <i class="fa fa-plus mr-2"></i> 新增链路
          </button>
        </div>
      </div>
      
      <div class="overflow-x-auto">
        <table class="w-full">
          <thead>
            <tr class="border-b border-light-2">
              <th class="text-left py-4 px-4 font-semibold text-dark-2">链路ID</th>
              <th class="text-left py-4 px-4 font-semibold text-dark-2">源节点</th>
              <th class="text-left py-4 px-4 font-semibold text-dark-2">目标节点</th>
              <th class="text-left py-4 px-4 font-semibold text-dark-2">带宽</th>
              <th class="text-left py-4 px-4 font-semibold text-dark-2">当前负载</th>
              <th class="text-left py-4 px-4 font-semibold text-dark-2">状态</th>
              <th class="text-left py-4 px-4 font-semibold text-dark-2">操作</th>
            </tr>
          </thead>
          <tbody>
            <tr 
              v-for="link in filteredLinks" 
              :key="link.id"
              class="border-b border-light-2 hover:bg-gray-50 transition-all-300"
            >
              <td class="py-4 px-4">{{ link.id }}</td>
              <td class="py-4 px-4">{{ link.source }}</td>
              <td class="py-4 px-4">{{ link.target }}</td>
              <td class="py-4 px-4">{{ link.bandwidth }}</td>
              <td class="py-4 px-4">
                <div class="flex items-center">
                  <div class="w-32 bg-light-1 rounded-full h-2 mr-3">
                    <div 
                      :class="getLoadClass(link.load)" 
                      class="h-2 rounded-full" 
                      :style="{ width: `${link.load}%` }"
                    ></div>
                  </div>
                  <span class="text-sm font-medium">{{ link.load }}%</span>
                </div>
              </td>
              <td class="py-4 px-4">
                <span 
                  :class="getStatusClass(link.status)" 
                  class="px-2 py-1 text-xs rounded-full"
                >
                  {{ link.statusText }}
                </span>
              </td>
              <td class="py-4 px-4">
                <button 
                  class="text-primary hover:text-primary/80 mr-3 transition-all-300"
                  @click="viewLinkDetails(link)"
                >
                  <i class="fa fa-eye"></i>
                </button>
                <button 
                  class="text-warning hover:text-warning/80 mr-3 transition-all-300"
                  @click="editLink(link)"
                >
                  <i class="fa fa-pencil"></i>
                </button>
                <button 
                  class="text-danger hover:text-danger/80 transition-all-300"
                  @click="deleteLink(link.id)"
                >
                  <i class="fa fa-trash"></i>
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
      
      <div class="flex items-center justify-between mt-6">
        <p class="text-sm text-dark-2">显示 1 至 {{ filteredLinks.length }} 条，共 {{ links.length }} 条</p>
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
    
    <!-- 链路拓扑和负载配置 -->
    <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
      <div class="bg-white rounded-xl p-6 card-shadow">
        <h3 class="font-semibold text-lg mb-6">链路拓扑图</h3>
        <div class="h-80 bg-gray-50 rounded-lg flex items-center justify-center">
          <img 
            src="https://picsum.photos/id/0/800/400" 
            alt="网络拓扑图" 
            class="max-w-full max-h-full object-contain rounded" 
          />
        </div>
      </div>
      
      <div class="bg-white rounded-xl p-6 card-shadow">
        <h3 class="font-semibold text-lg mb-6">负载均衡配置</h3>
        <form @submit.prevent="saveLoadBalanceConfig">
          <div class="mb-4">
            <label class="block text-sm font-medium text-dark-2 mb-1">负载均衡阈值</label>
            <input 
              type="number" 
              v-model="loadBalanceConfig.threshold"
              min="1" 
              max="100" 
              class="w-full px-4 py-2 rounded-lg border border-light-2 focus:outline-none focus:ring-2 focus:ring-primary/30 focus:border-primary transition-all-300"
            >
            <p class="text-xs text-dark-2 mt-1">当链路负载超过此百分比时，自动触发负载均衡</p>
          </div>
          
          <div class="mb-4">
            <label class="block text-sm font-medium text-dark-2 mb-1">检测间隔时间 (秒)</label>
            <input 
              type="number" 
              v-model="loadBalanceConfig.checkInterval"
              min="5" 
              max="300" 
              class="w-full px-4 py-2 rounded-lg border border-light-2 focus:outline-none focus:ring-2 focus:ring-primary/30 focus:border-primary transition-all-300"
            >
          </div>
          
          <div class="mb-4">
            <label class="block text-sm font-medium text-dark-2 mb-1">负载均衡策略</label>
            <select 
              v-model="loadBalanceConfig.strategy"
              class="w-full px-4 py-2 rounded-lg border border-light-2 focus:outline-none focus:ring-2 focus:ring-primary/30 focus:border-primary transition-all-300"
            >
              <option>最小负载优先</option>
              <option>轮询算法</option>
              <option>加权轮询</option>
              <option>AI智能调度</option>
            </select>
          </div>
          
          <button 
            type="submit" 
            class="w-full py-2.5 bg-primary text-white rounded-lg hover:bg-primary/90 transition-all-300"
          >
            保存配置
          </button>
        </form>
      </div>
    </div>
    
    <!-- 新增/编辑链路模态框 -->
    <div 
      v-if="showAddLinkModal" 
      class="fixed inset-0 bg-black/50 z-50 flex items-center justify-center"
      @click="closeModal"
    >
      <div 
        class="bg-white rounded-xl p-6 w-full max-w-md mx-4 transform transition-all-300 scale-100 opacity-100"
        @click.stop
      >
        <div class="flex items-center justify-between mb-4">
          <h3 class="font-semibold text-lg">{{ isEditing ? '编辑链路' : '新增链路' }}</h3>
          <button 
            class="text-dark-2 hover:text-dark transition-all-300"
            @click="closeModal"
          >
            <i class="fa fa-times"></i>
          </button>
        </div>
        
        <form @submit.prevent="saveLink">
          <div class="mb-4">
            <label class="block text-sm font-medium text-dark-2 mb-1">链路ID</label>
            <input 
              type="text" 
              v-model="currentLink.id"
              :readonly="isEditing"
              class="w-full px-4 py-2 rounded-lg border border-light-2 focus:outline-none focus:ring-2 focus:ring-primary/30 focus:border-primary transition-all-300"
            >
          </div>
          
          <div class="mb-4">
            <label class="block text-sm font-medium text-dark-2 mb-1">源节点</label>
            <input 
              type="text" 
              v-model="currentLink.source"
              class="w-full px-4 py-2 rounded-lg border border-light-2 focus:outline-none focus:ring-2 focus:ring-primary/30 focus:border-primary transition-all-300"
            >
          </div>
          
          <div class="mb-4">
            <label class="block text-sm font-medium text-dark-2 mb-1">目标节点</label>
            <input 
              type="text" 
              v-model="currentLink.target"
              class="w-full px-4 py-2 rounded-lg border border-light-2 focus:outline-none focus:ring-2 focus:ring-primary/30 focus:border-primary transition-all-300"
            >
          </div>
          
          <div class="mb-4">
            <label class="block text-sm font-medium text-dark-2 mb-1">带宽</label>
            <select 
              v-model="currentLink.bandwidth"
              class="w-full px-4 py-2 rounded-lg border border-light-2 focus:outline-none focus:ring-2 focus:ring-primary/30 focus:border-primary transition-all-300"
            >
              <option>100Mbps</option>
              <option>1Gbps</option>
              <option>10Gbps</option>
              <option>100Gbps</option>
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
              class="flex-1 py-2.5 bg-primary text-white rounded-lg hover:bg-primary/90 transition-all-300"
            >
              {{ isEditing ? '更新链路' : '添加链路' }}
            </button>
          </div>
        </form>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue';

// 链路数据类型定义
interface Link {
  id: string;
  source: string;
  target: string;
  bandwidth: string;
  load: number;
  status: 'normal' | 'high' | 'overload';
  statusText: string;
}

// 负载均衡配置类型
interface LoadBalanceConfig {
  threshold: number;
  checkInterval: number;
  strategy: string;
}

// 状态数据
const links = ref<Link[]>([]);
const searchQuery = ref('');
const currentPage = ref(1);
const itemsPerPage = 5;
const showAddLinkModal = ref(false);
const isEditing = ref(false);
const currentLink = ref<Link>({
  id: '',
  source: '',
  target: '',
  bandwidth: '1Gbps',
  load: 0,
  status: 'normal',
  statusText: '正常'
});
const loadBalanceConfig = ref<LoadBalanceConfig>({
  threshold: 80,
  checkInterval: 30,
  strategy: '最小负载优先'
});

// 初始化数据
onMounted(() => {
  // 模拟从API获取数据
  links.value = [
    { id: 'LNK-001', source: 'Switch-A', target: 'Switch-B', bandwidth: '1Gbps', load: 35, status: 'normal', statusText: '正常' },
    { id: 'LNK-002', source: 'Switch-B', target: 'Switch-C', bandwidth: '1Gbps', load: 78, status: 'high', statusText: '负载较高' },
    { id: 'LNK-003', source: 'Switch-C', target: 'Switch-D', bandwidth: '1Gbps', load: 92, status: 'overload', statusText: '过载' },
    { id: 'LNK-004', source: 'Switch-A', target: 'Switch-D', bandwidth: '1Gbps', load: 22, status: 'normal', statusText: '正常' },
    { id: 'LNK-005', source: 'Switch-B', target: 'Switch-E', bandwidth: '1Gbps', load: 65, status: 'high', statusText: '负载较高' },
    { id: 'LNK-006', source: 'Switch-E', target: 'Switch-F', bandwidth: '1Gbps', load: 45, status: 'normal', statusText: '正常' },
    { id: 'LNK-007', source: 'Switch-C', target: 'Switch-F', bandwidth: '1Gbps', load: 58, status: 'normal', statusText: '正常' },
    { id: 'LNK-008', source: 'Switch-D', target: 'Switch-E', bandwidth: '1Gbps', load: 32, status: 'normal', statusText: '正常' }
  ];
  
  // 启动模拟负载更新
  startLoadSimulation();
});

// 过滤链路数据
const filteredLinks = computed(() => {
  return links.value
    .filter(link => link.id.toLowerCase().includes(searchQuery.value.toLowerCase()))
    .slice((currentPage.value - 1) * itemsPerPage, currentPage.value * itemsPerPage);
});

// 计算总页数
const totalPages = computed(() => {
  return Math.ceil(links.value.filter(link => 
    link.id.toLowerCase().includes(searchQuery.value.toLowerCase())
  ).length / itemsPerPage);
});

// 获取负载样式类
const getLoadClass = (load: number) => {
  if (load > 80) return 'bg-danger';
  if (load > 60) return 'bg-warning';
  return 'bg-success';
};

// 获取状态样式类
const getStatusClass = (status: string) => {
  switch (status) {
    case 'normal': return 'bg-success/10 text-success';
    case 'high': return 'bg-warning/10 text-warning';
    case 'overload': return 'bg-danger/10 text-danger';
    default: return 'bg-gray-100 text-gray-500';
  }
};

// 链路操作方法
const viewLinkDetails = (link: Link) => {
  console.log('查看链路详情:', link);
  // 可以打开详情模态框
};

const editLink = (link: Link) => {
  currentLink.value = { ...link };
  isEditing.value = true;
  showAddLinkModal.value = true;
};

const deleteLink = (id: string) => {
  if (confirm('确定要删除这条链路吗？')) {
    links.value = links.value.filter(link => link.id !== id);
  }
};

const saveLink = () => {
  if (isEditing.value) {
    // 更新现有链路
    const index = links.value.findIndex(link => link.id === currentLink.value.id);
    if (index !== -1) {
      links.value[index] = { ...currentLink.value };
    }
  } else {
    // 添加新链路
    if (!currentLink.value.id) {
      alert('请输入链路ID');
      return;
    }
    if (links.value.some(link => link.id === currentLink.value.id)) {
      alert('链路ID已存在');
      return;
    }
    links.value.push({ ...currentLink.value, load: Math.floor(Math.random() * 50), status: 'normal', statusText: '正常' });
  }
  
  closeModal();
};

// 关闭模态框
const closeModal = () => {
  showAddLinkModal.value = false;
  isEditing.value = false;
  currentLink.value = {
    id: '',
    source: '',
    target: '',
    bandwidth: '1Gbps',
    load: 0,
    status: 'normal',
    statusText: '正常'
  };
};

// 保存负载均衡配置
const saveLoadBalanceConfig = () => {
  console.log('保存负载均衡配置:', loadBalanceConfig.value);
  alert('负载均衡配置已保存');
};

// 模拟负载动态变化
const startLoadSimulation = () => {
  setInterval(() => {
    links.value = links.value.map(link => {
      // 随机微调负载值，保持在合理范围内
      let newLoad = link.load + (Math.random() * 10 - 5);
      newLoad = Math.max(5, Math.min(95, newLoad));
      
      // 更新状态文本
      let status: 'normal' | 'high' | 'overload' = 'normal';
      let statusText = '正常';
      
      if (newLoad > 80) {
        status = 'overload';
        statusText = '过载';
      } else if (newLoad > 60) {
        status = 'high';
        statusText = '负载较高';
      }
      
      return { ...link, load: Math.round(newLoad), status, statusText };
    });
  }, 5000);
};
</script>

<style scoped>
/* 链路管理样式已通过Tailwind工具类实现 */
</style>
