<template>
  <div>
    <!-- 页面标题 -->
    <div class="mb-6">
      <h2 class="text-[clamp(1.5rem,3vw,2rem)] font-bold text-dark">AI分析结果</h2>
      <p class="text-dark-2 mt-1">网络异常检测与智能优化建议</p>
    </div>
    
    <!-- 分析概览 -->
    <div class="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
      <div class="bg-white rounded-xl p-6 card-shadow">
        <div class="flex items-start justify-between">
          <div>
            <p class="text-dark-2 mb-1">分析完成率</p>
            <h3 class="text-3xl font-bold text-dark">98.7%</h3>
            <p class="text-success text-sm mt-2 flex items-center">
              <i class="fa fa-check-circle mr-1"></i> 分析已完成
            </p>
          </div>
          <div class="w-12 h-12 rounded-lg bg-primary/10 flex items-center justify-center text-primary">
            <i class="fa fa-chart-pie text-xl"></i>
          </div>
        </div>
      </div>
      
      <div class="bg-white rounded-xl p-6 card-shadow">
        <div class="flex items-start justify-between">
          <div>
            <p class="text-dark-2 mb-1">检测异常数</p>
            <h3 class="text-3xl font-bold text-dark">12</h3>
            <p class="text-warning text-sm mt-2 flex items-center">
              <i class="fa fa-exclamation-circle mr-1"></i> 3个需要立即处理
            </p>
          </div>
          <div class="w-12 h-12 rounded-lg bg-warning/10 flex items-center justify-center text-warning">
            <i class="fa fa-exclamation-triangle text-xl"></i>
          </div>
        </div>
      </div>
      
      <div class="bg-white rounded-xl p-6 card-shadow">
        <div class="flex items-start justify-between">
          <div>
            <p class="text-dark-2 mb-1">优化建议数</p>
            <h3 class="text-3xl font-bold text-dark">8</h3>
            <p class="text-success text-sm mt-2 flex items-center">
              <i class="fa fa-lightbulb mr-1"></i> 可提升性能30%
            </p>
          </div>
          <div class="w-12 h-12 rounded-lg bg-success/10 flex items-center justify-center text-success">
            <i class="fa fa-rocket text-xl"></i>
          </div>
        </div>
      </div>
    </div>
    
    <!-- 异常检测图表 -->
    <div class="bg-white rounded-xl p-6 card-shadow mb-8">
      <div class="flex flex-wrap items-center justify-between gap-4 mb-6">
        <h3 class="font-semibold text-lg">网络异常检测趋势</h3>
        <div class="flex flex-wrap items-center gap-4">
          <div class="flex space-x-2">
            <button class="px-3 py-1 text-sm rounded-md bg-primary/10 text-primary">今日</button>
            <button class="px-3 py-1 text-sm rounded-md text-dark-2 hover:bg-light-1">本周</button>
            <button class="px-3 py-1 text-sm rounded-md text-dark-2 hover:bg-light-1">本月</button>
          </div>
          
          <button class="px-4 py-2 border border-light-2 text-dark-2 rounded-lg hover:bg-light-1 transition-all-300 flex items-center">
            <i class="fa fa-sync-alt mr-2"></i> 重新分析
          </button>
        </div>
      </div>
      
      <div class="h-80">
        <canvas id="anomalyChart"></canvas>
      </div>
    </div>
    
    <!-- 异常列表和优化建议 -->
    <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
      <!-- 异常列表 -->
      <div class="bg-white rounded-xl p-6 card-shadow">
        <div class="flex items-center justify-between mb-6">
          <h3 class="font-semibold text-lg">检测到的异常</h3>
          <div class="relative">
            <select 
              v-model="severityFilter"
              class="appearance-none pl-3 pr-8 py-1.5 text-sm rounded-lg border border-light-2 focus:outline-none focus:ring-2 focus:ring-primary/30 focus:border-primary transition-all-300"
            >
              <option value="all">所有严重程度</option>
              <option value="critical">严重</option>
              <option value="warning">警告</option>
              <option value="info">信息</option>
            </select>
            <span class="absolute inset-y-0 right-0 flex items-center pr-2 pointer-events-none">
              <i class="fa fa-chevron-down text-xs text-dark-2"></i>
            </span>
          </div>
        </div>
        
        <div class="space-y-4 max-h-96 overflow-y-auto pr-2">
          <div 
            v-for="anomaly in filteredAnomalies" 
            :key="anomaly.id"
            class="p-4 border border-light-2 rounded-lg hover:border-primary/30 transition-all-300"
          >
            <div class="flex items-start justify-between mb-2">
              <h4 class="font-medium text-dark flex items-center">
                <span 
                  :class="getSeverityClass(anomaly.severity)" 
                  class="w-2 h-2 rounded-full mr-2"
                ></span>
                {{ anomaly.title }}
              </h4>
              <span class="text-xs text-dark-2">{{ anomaly.time }}</span>
            </div>
            <p class="text-sm text-dark-2 mb-3">{{ anomaly.description }}</p>
            <div class="flex items-center justify-between">
              <span class="text-xs bg-light-1 px-2 py-1 rounded-full">{{ anomaly.affected }}</span>
              <button class="text-primary text-sm hover:text-primary/80">处理</button>
            </div>
          </div>
        </div>
      </div>
      
      <!-- 优化建议 -->
      <div class="bg-white rounded-xl p-6 card-shadow">
        <div class="flex items-center justify-between mb-6">
          <h3 class="font-semibold text-lg">AI优化建议</h3>
          <button class="text-primary text-sm hover:text-primary/80">查看全部</button>
        </div>
        
        <div class="space-y-6">
          <div class="p-4 border-l-4 border-primary bg-primary/5 rounded-r-lg">
            <h4 class="font-medium text-dark mb-2">链路负载均衡优化</h4>
            <p class="text-sm text-dark-2 mb-3">检测到Switch-C至Switch-D链路负载过高，建议将20%流量分流至Switch-C至Switch-F链路，可降低负载35%。</p>
            <div class="flex justify-end">
              <button class="px-3 py-1 text-sm bg-primary text-white rounded-lg hover:bg-primary/90 transition-all-300">
                应用优化
              </button>
            </div>
          </div>
          
          <div class="p-4 border-l-4 border-primary bg-primary/5 rounded-r-lg">
            <h4 class="font-medium text-dark mb-2">节点资源分配调整</h4>
            <p class="text-sm text-dark-2 mb-3">Switch-B节点CPU利用率持续高于80%，建议迁移部分服务至Switch-E节点，可将CPU利用率降至60%以下。</p>
            <div class="flex justify-end">
              <button class="px-3 py-1 text-sm bg-primary text-white rounded-lg hover:bg-primary/90 transition-all-300">
                应用优化
              </button>
            </div>
          </div>
          
          <div class="p-4 border-l-4 border-primary bg-primary/5 rounded-r-lg">
            <h4 class="font-medium text-dark mb-2">带宽扩容建议</h4>
            <p class="text-sm text-dark-2 mb-3">检测到工作日9:00-11:00期间，主干链路带宽经常达到90%以上，建议将带宽从1Gbps升级至10Gbps。</p>
            <div class="flex justify-end">
              <button class="px-3 py-1 text-sm bg-gray-200 text-dark-2 rounded-lg cursor-not-allowed">
                计划中
              </button>
            </div>
          </div>
          
          <div class="p-4 border-l-4 border-primary bg-primary/5 rounded-r-lg">
            <h4 class="font-medium text-dark mb-2">安全策略增强</h4>
            <p class="text-sm text-dark-2 mb-3">近期来自198.51.100.0/24网段的异常连接尝试增加，建议增强该网段的访问控制策略。</p>
            <div class="flex justify-end">
              <button class="px-3 py-1 text-sm bg-primary text-white rounded-lg hover:bg-primary/90 transition-all-300">
                应用优化
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue';
import { Chart, registerables } from 'chart.js';

// 注册Chart.js组件
Chart.register(...registerables);

// 异常数据类型定义
interface Anomaly {
  id: string;
  title: string;
  description: string;
  severity: 'critical' | 'warning' | 'info';
  time: string;
  affected: string;
}

// 状态数据
const anomalies = ref<Anomaly[]>([]);
const severityFilter = ref('all');

// 初始化数据
onMounted(() => {
  // 模拟从API获取数据
  anomalies.value = [
    {
      id: 'A-001',
      title: '链路负载过高',
      description: 'Switch-C至Switch-D链路负载持续15分钟超过90%，可能导致网络延迟增加',
      severity: 'critical',
      time: '10:23:45',
      affected: 'Switch-C, Switch-D'
    },
    {
      id: 'A-002',
      title: '节点CPU利用率高',
      description: 'Switch-B节点CPU利用率超过80%，持续时间超过30分钟',
      severity: 'warning',
      time: '09:15:32',
      affected: 'Switch-B'
    },
    {
      id: 'A-003',
      title: '异常流量模式',
      description: '检测到来自198.51.100.12的异常流量模式，可能存在攻击行为',
      severity: 'critical',
      time: '08:42:19',
      affected: '全网'
    },
    {
      id: 'A-004',
      title: '链路抖动',
      description: 'Switch-E至Switch-F链路出现间歇性抖动，丢包率0.5%',
      severity: 'warning',
      time: '07:56:08',
      affected: 'Switch-E, Switch-F'
    },
    {
      id: 'A-005',
      title: '内存使用率上升',
      description: 'Switch-A内存使用率在过去2小时内上升了15%',
      severity: 'info',
      time: '06:32:47',
      affected: 'Switch-A'
    },
    {
      id: 'A-006',
      title: '端口连接数异常',
      description: 'Switch-C的端口8080连接数异常增加，较平均值高300%',
      severity: 'warning',
      time: '05:18:23',
      affected: 'Switch-C'
    }
  ];
  
  // 初始化异常检测图表
  initAnomalyChart();
});

// 过滤异常数据
const filteredAnomalies = computed(() => {
  if (severityFilter.value === 'all') {
    return anomalies.value;
  }
  return anomalies.value.filter(anomaly => anomaly.severity === severityFilter.value);
});

// 获取严重程度样式
const getSeverityClass = (severity: string) => {
  switch (severity) {
    case 'critical': return 'bg-danger';
    case 'warning': return 'bg-warning';
    case 'info': return 'bg-primary';
    default: return 'bg-dark-2';
  }
};

// 初始化异常检测图表
const initAnomalyChart = () => {
  const ctx = document.getElementById('anomalyChart') as HTMLCanvasElement;
  new Chart(ctx, {
    type: 'bar',
    data: {
      labels: ['00:00', '03:00', '06:00', '09:00', '12:00', '15:00', '18:00', '21:00'],
      datasets: [
        {
          label: '严重异常',
          data: [0, 0, 1, 2, 0, 0, 0, 0],
          backgroundColor: '#FF4D4F',
        },
        {
          label: '警告异常',
          data: [1, 0, 0, 1, 2, 1, 0, 0],
          backgroundColor: '#FAAD14',
        },
        {
          label: '信息异常',
          data: [0, 2, 1, 0, 0, 1, 2, 1],
          backgroundColor: '#165DFF',
        }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          position: 'top',
        }
      },
      scales: {
        x: {
          stacked: true,
        },
        y: {
          stacked: true,
          beginAtZero: true,
          ticks: {
            precision: 0
          }
        }
      }
    }
  });
};
</script>

<style scoped>
/* AI分析结果样式已通过Tailwind工具类实现 */
</style>
