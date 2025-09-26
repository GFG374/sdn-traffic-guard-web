<template>
  <div>
    <!-- 页面标题 -->
    <div class="mb-6">
      <h2 class="text-[clamp(1.5rem,3vw,2rem)] font-bold text-dark">AI分析结果</h2>
      <p class="text-dark-2 mt-1">网络异常检测与智能优化建议</p>
      <!-- 声音开关 -->
      <div class="mt-4 flex items-center gap-4">
        <button 
          @click="toggleSound" 
          class="px-4 py-2 rounded-lg border transition-all-300 flex items-center gap-2"
          :class="soundEnabled ? 'bg-primary text-white border-primary' : 'bg-white text-dark border-light-2 hover:bg-light-1'"
        >
          <i :class="soundEnabled ? 'fa fa-volume-up' : 'fa fa-volume-mute'"></i>
          {{ soundEnabled ? '声音已开启' : '声音已关闭' }}
        </button>
      </div>
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
            <h3 class="text-3xl font-bold text-dark">{{ anomalies.length }}</h3>
            <p class="text-warning text-sm mt-2 flex items-center">
              <i class="fa fa-exclamation-circle mr-1"></i> {{ criticalCount }}个需要立即处理
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
          
          <button 
            @click="refreshData"
            class="px-4 py-2 border border-light-2 text-dark-2 rounded-lg hover:bg-light-1 transition-all-300 flex items-center"
          >
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
          <transition-group name="slide-in" tag="div">
            <div 
              v-for="anomaly in filteredAnomalies" 
              :key="anomaly.id"
              class="anomaly-card-3d p-4 border border-light-2 rounded-lg hover:border-primary/30 transition-all-300 cursor-pointer"
              :class="[getAttackTypeClass(anomaly.type), getDangerLevelClass(anomaly.type, anomaly.pps)]"
              @mouseenter="playAttackSound(anomaly)"
              @click="showAnomalyDetails(anomaly)"
              @mouseleave="resetCardTransform"
            >
              <div class="flex items-start justify-between mb-2">
                <h4 class="font-medium text-dark flex items-center">
                  <span 
                    :class="getSeverityClass(anomaly.severity)" 
                    class="severity-indicator w-3 h-3 rounded-full mr-3 animate-pulse"
                  ></span>
                  <span class="attack-type-badge-enhanced" :class="getAttackTypeBadgeClass(anomaly.type)">
                    {{ anomaly.type }}
                  </span>
                  {{ anomaly.title }}
                </h4>
                <div class="flex flex-col items-end">
                  <span class="text-xs text-dark-2">{{ anomaly.time }}</span>
                  <span class="text-xs font-mono text-primary mt-1">{{ anomaly.pps }} PPS</span>
                </div>
              </div>
              <p class="text-sm text-dark-2 mb-3">{{ anomaly.description }}</p>
              <div class="flex items-center justify-between">
                <span class="text-xs bg-light-1 px-2 py-1 rounded-full">{{ anomaly.affected }}</span>
                <button class="text-primary text-sm hover:text-primary/80">处理</button>
              </div>
            </div>
          </transition-group>
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
  type: 'SYN' | 'UDP' | 'ICMP' | 'ARP' | 'DDoS' | 'Port Scan' | 'Brute Force';
  time: string;
  affected: string;
  pps?: number; // 每秒包数
}

// 状态数据
const anomalies = ref<Anomaly[]>([]);
const severityFilter = ref('all');
const soundEnabled = ref(true);

// 计算属性
const criticalCount = computed(() => 
  anomalies.value.filter(a => a.severity === 'critical').length
);

// 初始化数据
onMounted(() => {
  // 模拟从API获取数据
  anomalies.value = [
    {
      id: 'A-001',
      title: '链路负载过高',
      description: 'Switch-C至Switch-D链路负载持续15分钟超过90%，可能导致网络延迟增加',
      severity: 'critical',
      type: 'SYN',
      time: '10:23:45',
      affected: 'Switch-C, Switch-D',
      pps: 1500
    },
    {
      id: 'A-002',
      title: '节点CPU利用率高',
      description: 'Switch-B节点CPU利用率超过80%，持续时间超过30分钟',
      severity: 'warning',
      type: 'UDP',
      time: '09:15:32',
      affected: 'Switch-B',
      pps: 800
    },
    {
      id: 'A-003',
      title: '异常流量模式',
      description: '检测到来自198.51.100.12的异常流量模式，可能存在攻击行为',
      severity: 'critical',
      type: 'DDoS',
      time: '08:42:19',
      affected: '全网',
      pps: 2000
    },
    {
      id: 'A-004',
      title: '链路抖动',
      description: 'Switch-E至Switch-F链路出现间歇性抖动，丢包率0.5%',
      severity: 'warning',
      type: 'ICMP',
      time: '07:56:08',
      affected: 'Switch-E, Switch-F',
      pps: 300
    },
    {
      id: 'A-005',
      title: '内存使用率上升',
      description: 'Switch-A内存使用率在过去2小时内上升了15%',
      severity: 'info',
      type: 'ARP',
      time: '06:32:47',
      affected: 'Switch-A',
      pps: 100
    },
    {
      id: 'A-006',
      title: '端口连接数异常',
      description: 'Switch-C的端口8080连接数异常增加，较平均值高300%',
      severity: 'warning',
      type: 'Port Scan',
      time: '05:18:23',
      affected: 'Switch-C',
      pps: 600
    }
  ];
  
  // 初始化异常检测图表
  initAnomalyChart();
  
  // 模拟新异常的实时添加
  startAnomalySimulation();
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

// 获取攻击类型样式类
const getAttackTypeClass = (type: string) => {
  switch (type) {
    case 'SYN': return 'attack-syn';
    case 'UDP': return 'attack-udp';
    case 'ICMP': return 'attack-icmp';
    case 'ARP': return 'attack-arp';
    case 'DDoS': return 'attack-ddos';
    case 'Port Scan': return 'attack-port-scan';
    case 'Brute Force': return 'attack-brute-force';
    default: return '';
  }
};

// 获取危险等级样式类（基于攻击类型和PPS）
const getDangerLevelClass = (type: string, pps?: number) => {
  // 根据攻击类型和PPS计算危险等级
  let dangerLevel = 'low';
  
  // 如果pps未定义，默认为0
  const ppsValue = pps || 0;
  
  if (type === 'DDoS' && ppsValue > 1500) {
    dangerLevel = 'critical';
  } else if (type === 'SYN' && ppsValue > 1000) {
    dangerLevel = 'high';
  } else if (type === 'UDP' && ppsValue > 800) {
    dangerLevel = 'high';
  } else if (ppsValue > 500) {
    dangerLevel = 'medium';
  }
  
  return `danger-${dangerLevel}`;
};

// 重置卡片变换
const resetCardTransform = (event: MouseEvent) => {
  const card = event.currentTarget as HTMLElement;
  card.style.transform = '';
};

// 获取攻击类型徽章样式
const getAttackTypeBadgeClass = (type: string) => {
  switch (type) {
    case 'SYN': return 'badge-syn';
    case 'UDP': return 'badge-udp';
    case 'ICMP': return 'badge-icmp';
    case 'ARP': return 'badge-arp';
    case 'DDoS': return 'badge-ddos';
    case 'Port Scan': return 'badge-port-scan';
    case 'Brute Force': return 'badge-brute-force';
    default: return 'badge-default';
  }
};

// 播放攻击声音
const playAttackSound = (anomaly: Anomaly) => {
  if (!soundEnabled.value) return;
  
  // 高危攻击（SYN/UDP > 1000 pps）触发声音
  if ((anomaly.type === 'SYN' || anomaly.type === 'UDP' || anomaly.type === 'DDoS') && 
      anomaly.pps && anomaly.pps > 1000) {
    // 使用Web Audio API播放提示音
    const audioContext = new (window.AudioContext || (window as any).webkitAudioContext)();
    const oscillator = audioContext.createOscillator();
    const gainNode = audioContext.createGain();
    
    oscillator.connect(gainNode);
    gainNode.connect(audioContext.destination);
    
    oscillator.frequency.setValueAtTime(800, audioContext.currentTime);
    gainNode.gain.setValueAtTime(0.3, audioContext.currentTime);
    gainNode.gain.exponentialRampToValueAtTime(0.01, audioContext.currentTime + 0.3);
    
    oscillator.start(audioContext.currentTime);
    oscillator.stop(audioContext.currentTime + 0.3);
  }
};

// 切换声音开关
const toggleSound = () => {
  soundEnabled.value = !soundEnabled.value;
};

// 显示异常详情
const showAnomalyDetails = (anomaly: Anomaly) => {
  console.log('显示异常详情:', anomaly);
  // 这里可以实现弹窗或跳转到详情页面
};

// 刷新数据
const refreshData = () => {
  console.log('刷新分析数据');
  // 重新获取数据的逻辑
};

// 模拟新异常的实时添加
const startAnomalySimulation = () => {
  setInterval(() => {
    // 随机添加新异常
    if (Math.random() < 0.3) { // 30%概率添加新异常
      const newAnomaly: Anomaly = {
        id: `A-${Date.now()}`,
        title: '新检测异常',
        description: '实时检测到的网络异常',
        severity: Math.random() > 0.7 ? 'critical' : Math.random() > 0.4 ? 'warning' : 'info',
        type: ['SYN', 'UDP', 'ICMP', 'ARP', 'DDoS'][Math.floor(Math.random() * 5)] as any,
        time: new Date().toLocaleTimeString(),
        affected: 'Switch-X',
        pps: Math.floor(Math.random() * 2000) + 100
      };
      
      anomalies.value.unshift(newAnomaly);
      
      // 限制列表长度
      if (anomalies.value.length > 20) {
        anomalies.value.pop();
      }
    }
  }, 5000); // 每5秒检查一次
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
/* 滑入动画 */
.slide-in-enter-active {
  transition: all 0.5s ease-out;
}

.slide-in-enter-from {
  transform: translateY(-30px);
  opacity: 0;
}

.slide-in-enter-to {
  transform: translateY(0);
  opacity: 1;
}

/* 异常卡片样式 */
.anomaly-card {
  position: relative;
  overflow: hidden;
}

.anomaly-card::before {
  content: '';
  position: absolute;
  top: 0;
  left: -100%;
  width: 100%;
  height: 100%;
  background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.2), transparent);
  transition: left 0.5s;
}

.anomaly-card:hover::before {
  left: 100%;
}

/* 攻击类型危险色阶 */
.attack-syn {
  border-left: 4px solid #dc2626 !important; /* 深红 - SYN攻击 */
  background: linear-gradient(135deg, rgba(220, 38, 38, 0.05), rgba(220, 38, 38, 0.02));
}

.attack-udp {
  border-left: 4px solid #ea580c !important; /* 橙色 - UDP攻击 */
  background: linear-gradient(135deg, rgba(234, 88, 12, 0.05), rgba(234, 88, 12, 0.02));
}

.attack-icmp {
  border-left: 4px solid #eab308 !important; /* 黄色 - ICMP攻击 */
  background: linear-gradient(135deg, rgba(234, 179, 8, 0.05), rgba(234, 179, 8, 0.02));
}

.attack-arp {
  border-left: 4px solid #9333ea !important; /* 紫色 - ARP攻击 */
  background: linear-gradient(135deg, rgba(147, 51, 234, 0.05), rgba(147, 51, 234, 0.02));
}

.attack-ddos {
  border-left: 4px solid #b91c1c !important; /* 深红 - DDoS攻击 */
  background: linear-gradient(135deg, rgba(185, 28, 28, 0.08), rgba(185, 28, 28, 0.03));
  animation: pulse-red 2s infinite;
}

.attack-port-scan {
  border-left: 4px solid #f59e0b !important; /* 琥珀色 - 端口扫描 */
  background: linear-gradient(135deg, rgba(245, 158, 11, 0.05), rgba(245, 158, 11, 0.02));
}

.attack-brute-force {
  border-left: 4px solid #dc2626 !important; /* 深红 - 暴力破解 */
  background: linear-gradient(135deg, rgba(220, 38, 38, 0.06), rgba(220, 38, 38, 0.02));
}

/* 攻击类型徽章样式增强 */
.attack-type-badge-enhanced {
  display: inline-block;
  padding: 4px 12px;
  border-radius: 16px;
  font-size: 10px;
  font-weight: 700;
  margin-right: 12px;
  text-transform: uppercase;
  letter-spacing: 1px;
  position: relative;
  overflow: hidden;
  transition: all 0.3s ease;
}

.attack-type-badge-enhanced::before {
  content: '';
  position: absolute;
  top: 0;
  left: -100%;
  width: 100%;
  height: 100%;
  background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.3), transparent);
  transition: left 0.5s ease;
}

.attack-type-badge-enhanced:hover::before {
  left: 100%;
}

.severity-indicator {
  position: relative;
  box-shadow: 0 0 8px currentColor;
}

.severity-indicator::after {
  content: '';
  position: absolute;
  top: -2px;
  left: -2px;
  right: -2px;
  bottom: -2px;
  border-radius: 50%;
  border: 1px solid currentColor;
  opacity: 0.3;
  animation: ping 2s cubic-bezier(0, 0, 0.2, 1) infinite;
}

@keyframes ping {
  75%, 100% {
    transform: scale(2);
    opacity: 0;
  }
}

.badge-syn {
  background: #dc2626;
  color: white;
  box-shadow: 0 0 8px rgba(220, 38, 38, 0.3);
}

.badge-udp {
  background: #ea580c;
  color: white;
  box-shadow: 0 0 8px rgba(234, 88, 12, 0.3);
}

.badge-icmp {
  background: #eab308;
  color: white;
  box-shadow: 0 0 8px rgba(234, 179, 8, 0.3);
}

.badge-arp {
  background: #9333ea;
  color: white;
  box-shadow: 0 0 8px rgba(147, 51, 234, 0.3);
}

.badge-ddos {
  background: #b91c1c;
  color: white;
  box-shadow: 0 0 12px rgba(185, 28, 28, 0.4);
  animation: glow-red 1.5s ease-in-out infinite alternate;
}

.badge-port-scan {
  background: #f59e0b;
  color: white;
  box-shadow: 0 0 8px rgba(245, 158, 11, 0.3);
}

.badge-brute-force {
  background: #dc2626;
  color: white;
  box-shadow: 0 0 8px rgba(220, 38, 38, 0.3);
}

.badge-default {
  background: #6b7280;
  color: white;
}

/* 心跳动画 - 新行闪红效果 */
@keyframes pulse-red {
  0% {
    box-shadow: 0 0 0 0 rgba(220, 38, 38, 0.4);
  }
  70% {
    box-shadow: 0 0 0 10px rgba(220, 38, 38, 0);
  }
  100% {
    box-shadow: 0 0 0 0 rgba(220, 38, 38, 0);
  }
}

/* 发光动画 */
@keyframes glow-red {
  from {
    box-shadow: 0 0 12px rgba(185, 28, 28, 0.4);
  }
  to {
    box-shadow: 0 0 20px rgba(185, 28, 28, 0.8);
  }
}

/* 高危攻击闪烁效果 */
.attack-syn.anomaly-card,
.attack-ddos.anomaly-card {
  animation: flash-red 0.3s ease-in-out;
}

@keyframes flash-red {
  0% { background-color: rgba(220, 38, 38, 0.1); }
  50% { background-color: rgba(220, 38, 38, 0.2); }
  100% { background-color: rgba(220, 38, 38, 0.05); }
}

/* 3D卡片翻转效果增强 */
.anomaly-card-3d {
  position: relative;
  overflow: hidden;
  transform-style: preserve-3d;
  transition: all 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275);
  perspective: 1000px;
  background: linear-gradient(145deg, #ffffff, #f8fafc);
  box-shadow: 0 4px 15px rgba(0, 0, 0, 0.08);
}

.anomaly-card-3d::before {
  content: '';
  position: absolute;
  top: 0;
  left: -100%;
  width: 100%;
  height: 100%;
  background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.4), transparent);
  transition: left 0.6s ease;
  z-index: 1;
}

.anomaly-card-3d:hover::before {
  left: 100%;
}

.anomaly-card-3d:hover {
  transform: rotateY(8deg) rotateX(4deg) translateY(-8px) scale(1.02);
  box-shadow: 0 20px 40px rgba(0, 0, 0, 0.15);
  z-index: 10;
}

.anomaly-card-3d:active {
  transform: rotateY(12deg) rotateX(6deg) translateY(-4px) scale(0.98);
  transition: all 0.1s ease;
}

/* 危险等级色阶增强 */
.danger-low {
  border-left-width: 3px;
  background: linear-gradient(135deg, rgba(34, 197, 94, 0.03), rgba(34, 197, 94, 0.01));
}

.danger-medium {
  border-left-width: 4px;
  background: linear-gradient(135deg, rgba(251, 191, 36, 0.05), rgba(251, 191, 36, 0.02));
  animation: pulse-yellow 3s infinite;
}

.danger-high {
  border-left-width: 5px;
  background: linear-gradient(135deg, rgba(239, 68, 68, 0.08), rgba(239, 68, 68, 0.03));
  animation: pulse-orange 2s infinite;
}

.danger-critical {
  border-left-width: 6px;
  background: linear-gradient(135deg, rgba(185, 28, 28, 0.12), rgba(185, 28, 28, 0.04));
  animation: pulse-critical 1.5s infinite;
  box-shadow: 0 0 20px rgba(185, 28, 28, 0.2);
}

/* 危险等级脉冲动画 */
@keyframes pulse-yellow {
  0%, 100% {
    box-shadow: 0 4px 15px rgba(0, 0, 0, 0.08);
  }
  50% {
    box-shadow: 0 4px 25px rgba(251, 191, 36, 0.3);
  }
}

@keyframes pulse-orange {
  0%, 100% {
    box-shadow: 0 4px 15px rgba(0, 0, 0, 0.08);
  }
  50% {
    box-shadow: 0 4px 30px rgba(239, 68, 68, 0.4);
  }
}

@keyframes pulse-critical {
  0%, 100% {
    box-shadow: 0 4px 15px rgba(0, 0, 0, 0.08), 0 0 20px rgba(185, 28, 28, 0.2);
  }
  50% {
    box-shadow: 0 4px 35px rgba(185, 28, 28, 0.5), 0 0 30px rgba(185, 28, 28, 0.4);
    transform: scale(1.01);
  }
}

/* 攻击类型危险色阶增强 */
.attack-syn {
  border-left: 4px solid #dc2626 !important;
  background: linear-gradient(135deg, rgba(220, 38, 38, 0.06), rgba(220, 38, 38, 0.02));
  position: relative;
}

.attack-syn::after {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: linear-gradient(45deg, transparent 30%, rgba(220, 38, 38, 0.05) 50%, transparent 70%);
  pointer-events: none;
}

.attack-udp {
  border-left: 4px solid #ea580c !important;
  background: linear-gradient(135deg, rgba(234, 88, 12, 0.06), rgba(234, 88, 12, 0.02));
  position: relative;
}

.attack-udp::after {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: linear-gradient(45deg, transparent 30%, rgba(234, 88, 12, 0.05) 50%, transparent 70%);
  pointer-events: none;
}

.attack-icmp {
  border-left: 4px solid #eab308 !important;
  background: linear-gradient(135deg, rgba(234, 179, 8, 0.06), rgba(234, 179, 8, 0.02));
  position: relative;
}

.attack-icmp::after {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: linear-gradient(45deg, transparent 30%, rgba(234, 179, 8, 0.05) 50%, transparent 70%);
  pointer-events: none;
}

.attack-arp {
  border-left: 4px solid #9333ea !important;
  background: linear-gradient(135deg, rgba(147, 51, 234, 0.06), rgba(147, 51, 234, 0.02));
  position: relative;
}

.attack-arp::after {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: linear-gradient(45deg, transparent 30%, rgba(147, 51, 234, 0.05) 50%, transparent 70%);
  pointer-events: none;
}

.attack-ddos {
  border-left: 6px solid #b91c1c !important;
  background: linear-gradient(135deg, rgba(185, 28, 28, 0.12), rgba(185, 28, 28, 0.04));
  animation: pulse-red 2s infinite, shake 0.5s ease-in-out;
  position: relative;
}

.attack-ddos::after {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: linear-gradient(45deg, transparent 20%, rgba(185, 28, 28, 0.08) 50%, transparent 80%);
  pointer-events: none;
  animation: slide-danger 2s infinite;
}

.attack-port-scan {
  border-left: 4px solid #f59e0b !important;
  background: linear-gradient(135deg, rgba(245, 158, 11, 0.06), rgba(245, 158, 11, 0.02));
  position: relative;
}

.attack-port-scan::after {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: linear-gradient(45deg, transparent 30%, rgba(245, 158, 11, 0.05) 50%, transparent 70%);
  pointer-events: none;
}

.attack-brute-force {
  border-left: 5px solid #dc2626 !important;
  background: linear-gradient(135deg, rgba(220, 38, 38, 0.08), rgba(220, 38, 38, 0.03));
  position: relative;
}

.attack-brute-force::after {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: linear-gradient(45deg, transparent 25%, rgba(220, 38, 38, 0.06) 50%, transparent 75%);
  pointer-events: none;
}

/* 新增动画效果 */
@keyframes shake {
  0%, 100% { transform: translateX(0); }
  25% { transform: translateX(-2px); }
  75% { transform: translateX(2px); }
}

@keyframes slide-danger {
  0% { transform: translateX(-100%); }
  100% { transform: translateX(100%); }
}

/* 声音按钮样式 */
.sound-btn {
  transition: all 0.3s ease;
}

.sound-btn:hover {
  transform: scale(1.05);
}

.sound-btn.active {
  animation: sound-pulse 2s infinite;
}

@keyframes sound-pulse {
  0% { transform: scale(1); }
  50% { transform: scale(1.05); }
  100% { transform: scale(1); }
}
</style>
