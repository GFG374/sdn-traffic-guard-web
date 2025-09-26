<template>
  <n-config-provider :theme="null">
    <div class="dashboard-container">
      <!-- 4个KPI卡片 -->
      <div class="kpi-grid">
        <n-card class="kpi-card" hoverable>
          <div class="kpi-content">
            <div class="kpi-info">
              <p class="kpi-label">总流量</p>
              <p class="kpi-value" ref="totalTrafficRef">{{ formatBytes(summary.total_traffic || 0) }}</p>
            </div>
            <div class="kpi-icon traffic-icon">
              <i class="fas fa-chart-line"></i>
            </div>
          </div>
        </n-card>
        
        <n-card class="kpi-card" hoverable>
          <div class="kpi-content">
            <div class="kpi-info">
              <p class="kpi-label">包速率</p>
              <p class="kpi-value" ref="packetRateRef">{{ formatNumber(summary.packet_rate || 0) }}/s</p>
            </div>
            <div class="kpi-icon packet-icon">
              <i class="fas fa-tachometer-alt"></i>
            </div>
          </div>
        </n-card>
        
        <n-card class="kpi-card" hoverable>
          <div class="kpi-content">
            <div class="kpi-info">
              <p class="kpi-label">今日异常</p>
              <p class="kpi-value" ref="anomaliesRef">{{ summary.anomalies_today || 0 }}</p>
            </div>
            <div class="kpi-icon anomaly-icon">
              <i class="fas fa-exclamation-triangle"></i>
            </div>
          </div>
        </n-card>
        
        <n-card class="kpi-card" hoverable>
          <div class="kpi-content">
            <div class="kpi-info">
              <p class="kpi-label">TOP攻击者</p>
              <p class="kpi-value ip-value">{{ summary.top_attack_ip || '192.168.1.101' }}</p>
            </div>
            <div class="kpi-icon attacker-icon">
              <i class="fas fa-user-shield"></i>
            </div>
          </div>
        </n-card>
      </div>
      
      <!-- 24h流量折线图 -->
      <n-card class="chart-card" title="24小时流量趋势" hoverable>
        <template #header-extra>
          <n-button text @click="refreshFlowStats">
            <i class="fas fa-sync-alt"></i>
            刷新
          </n-button>
        </template>
        <div id="flowChart" class="chart-container"></div>
      </n-card>
      
      <!-- 最近5条异常 -->
      <n-card class="anomaly-card" title="实时异常监控" hoverable>
        <template #header-extra>
          <div class="anomaly-controls">
            <span class="auto-refresh-status">自动刷新: {{ autoRefresh ? '开启' : '关闭' }}</span>
            <n-button text @click="toggleAutoRefresh">
              <i :class="autoRefresh ? 'fas fa-pause' : 'fas fa-play'"></i>
              {{ autoRefresh ? '暂停' : '开始' }}
            </n-button>
          </div>
        </template>
        
        <n-data-table
          :columns="anomalyColumns"
          :data="anomalies"
          :pagination="false"
          :max-height="400"
          :row-class-name="getRowClassName"
        />
        
        <n-empty v-if="anomalies.length === 0" description="暂无异常检测到">
          <template #icon>
            <i class="fas fa-shield-check" style="color: var(--success); font-size: 48px;"></i>
          </template>
        </n-empty>
      </n-card>
    </div>
  </n-config-provider>
</template>

<script setup lang="ts">
import { onMounted, ref, onUnmounted, nextTick, h, getCurrentInstance } from 'vue';
import { NButton, NTag } from 'naive-ui';
import axios from 'axios';
import * as echarts from 'echarts';

// 响应式数据
const summary = ref<Summary>({
  total_traffic: 0,
  packet_rate: 0,
  anomalies_today: 0,
  top_attack_ip: '192.168.1.101'
});

const flowStats = ref<FlowStat[]>([]);
const anomalies = ref<Anomaly[]>([]);
const autoRefresh = ref(true);

// 获取全局消息实例
const { proxy } = getCurrentInstance()!;
const message = (proxy as any)?.$message;

// 定义数据结构
interface Summary {
  total_traffic: number;
  packet_rate: number;
  anomalies_today: number;
  top_attack_ip: string;
}

interface FlowStat {
  timestamp: number;
  bytes_per_sec: number;
  packets_per_sec: number;
  protocol: string;
}

interface Anomaly {
  id?: number;
  timestamp: number;
  src_ip: string;
  type: string;
  details: string;
  severity: 'low' | 'medium' | 'high' | 'critical';
}



// ECharts 实例
let flowChart: any = null;
let refreshTimer: NodeJS.Timeout | null = null;

// 异常表格列定义
const anomalyColumns = [
  {
    title: '时间',
    key: 'timestamp',
    render: (row: Anomaly) => formatTime(row.timestamp),
    width: 120
  },
  {
    title: '源IP',
    key: 'src_ip',
    render: (row: Anomaly) => h('code', { style: 'font-family: monospace;' }, row.src_ip),
    width: 140
  },
  {
    title: '攻击类型',
    key: 'type',
    render: (row: Anomaly) => h(NTag, { 
      type: getTagType(row.type),
      size: 'small'
    }, () => row.type),
    width: 120
  },
  {
    title: '详情',
    key: 'details',
    ellipsis: true
  },
  {
    title: '危险等级',
    key: 'severity',
    render: (row: Anomaly) => h('div', { 
      style: 'display: flex; align-items: center;' 
    }, [
      h('div', { 
        style: `width: 8px; height: 8px; border-radius: 50%; background: ${getSeverityColor(row.severity)}; margin-right: 8px;` 
      }),
      getSeverityText(row.severity)
    ]),
    width: 100
  },
  {
    title: '操作',
    key: 'actions',
    render: (row: Anomaly) => h(NButton, {
      text: true,
      type: 'primary',
      onClick: () => handleAnomaly(row)
    }, () => '处理'),
    width: 80
  }
];

// 格式化函数
const formatBytes = (bytes: number): string => {
  if (bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
};

const formatNumber = (num: number): string => {
  if (num >= 1000000) return (num / 1000000).toFixed(1) + 'M';
  if (num >= 1000) return (num / 1000).toFixed(1) + 'K';
  return num.toString();
};

const formatTime = (timestamp: number): string => {
  return new Date(timestamp * 1000).toLocaleTimeString('zh-CN');
};

// 样式函数
const getTagType = (type: string): 'default' | 'error' | 'primary' | 'info' | 'success' | 'warning' => {
  switch (type) {
    case 'SYN洪水': return 'error';
    case 'UDP洪水': return 'warning';
    case 'ICMP洪水': return 'info';
    case 'ARP欺骗': return 'error';
    case 'Botnet': return 'error';
    default: return 'default';
  }
};

const getSeverityColor = (severity: string): string => {
  switch (severity) {
    case 'critical': return '#ff4d4f';
    case 'high': return '#ff7875';
    case 'medium': return '#ffa940';
    case 'low': return '#52c41a';
    default: return '#d9d9d9';
  }
};

const getSeverityText = (severity: string): string => {
  switch (severity) {
    case 'critical': return '严重';
    case 'high': return '高危';
    case 'medium': return '中危';
    case 'low': return '低危';
    default: return '未知';
  }
};

const getRowClassName = (row: Anomaly): string => {
  switch (row.severity) {
    case 'critical': return 'critical-row';
    case 'high': return 'high-row';
    case 'medium': return 'medium-row';
    default: return '';
  }
};

// API调用函数
const fetchSummary = async () => {
  try {
    const response = await axios.get('/api/v1/summary');
    if (response.data.success) {
      summary.value = response.data.data;
      // CountUp动画效果
      animateNumbers();
    }
  } catch (error) {
    console.error('获取概览数据失败:', error);
    // 使用真实SDN拓扑IP地址的模拟数据
    summary.value = {
      total_traffic: Math.floor(Math.random() * 1000000000) + 500000000,
      packet_rate: Math.floor(Math.random() * 10000) + 5000,
      anomalies_today: Math.floor(Math.random() * 50) + 10,
      top_attack_ip: ['192.168.1.101', '192.168.1.102', '192.168.1.103', '192.168.1.104', '192.168.1.105'][Math.floor(Math.random() * 5)]
    };
    animateNumbers();
  }
};

const fetchFlowStats = async () => {
  try {
    const response = await axios.get('/api/v1/flowstats');
    if (response.data.success) {
      flowStats.value = response.data.data;
      updateFlowChart();
    }
  } catch (error) {
    console.error('获取流量统计失败:', error);
    // 生成24小时的模拟数据
    const now = Date.now();
    const mockData = [];
    for (let i = 23; i >= 0; i--) {
      mockData.push({
        timestamp: Math.floor((now - i * 3600000) / 1000),
        bytes_per_sec: Math.floor(Math.random() * 10000000) + 1000000,
        packets_per_sec: Math.floor(Math.random() * 5000) + 1000,
        protocol: ['TCP', 'UDP', 'ICMP'][Math.floor(Math.random() * 3)]
      });
    }
    flowStats.value = mockData;
    updateFlowChart();
  }
};

const fetchAnomalies = async () => {
  try {
    const response = await axios.get('/api/v1/anomalies');
    if (response.data.success) {
      anomalies.value = response.data.data.slice(0, 5); // 只显示最近5条
    }
  } catch (error) {
    console.error('获取异常数据失败:', error);
    // 使用真实SDN拓扑IP地址的模拟异常数据
    const realIPs = ['192.168.1.101', '192.168.1.102', '192.168.1.103', '192.168.1.104', '192.168.1.105', '192.168.1.200'];
    const attackTypes = ['SYN洪水', 'UDP洪水', 'ICMP洪水', 'ARP欺骗', 'Botnet'];
    const severities = ['low', 'medium', 'high', 'critical'] as const;
    
    const mockAnomalies = Array.from({ length: 5 }, (_, i) => ({
      id: i + 1,
      timestamp: Math.floor(Date.now() / 1000) - i * 300,
      src_ip: realIPs[Math.floor(Math.random() * realIPs.length)],
      type: attackTypes[Math.floor(Math.random() * attackTypes.length)],
      details: `检测到异常流量，包速率: ${Math.floor(Math.random() * 5000) + 1000}/s`,
      severity: severities[Math.floor(Math.random() * severities.length)]
    }));
    
    anomalies.value = mockAnomalies;
  }
};

// CountUp数字动画
const animateNumbers = () => {
  // 简单的数字动画效果
  const elements = [
    { ref: 'totalTrafficRef', target: summary.value.total_traffic },
    { ref: 'packetRateRef', target: summary.value.packet_rate },
    { ref: 'anomaliesRef', target: summary.value.anomalies_today }
  ];
  
  elements.forEach(({ ref, target }) => {
    const element = document.querySelector(`[ref="${ref}"]`);
    if (element && target > 0) {
      let current = 0;
      const increment = target / 30;
      const timer = setInterval(() => {
        current += increment;
        if (current >= target) {
          current = target;
          clearInterval(timer);
        }
        if (ref === 'totalTrafficRef') {
          element.textContent = formatBytes(Math.floor(current));
        } else if (ref === 'packetRateRef') {
          element.textContent = formatNumber(Math.floor(current)) + '/s';
        } else {
          element.textContent = Math.floor(current).toString();
        }
      }, 50);
    }
  });
};

// 图表初始化
const initFlowChart = async () => {
  await nextTick();
  const chartDom = document.getElementById('flowChart');
  if (!chartDom) return;
  
  flowChart = echarts.init(chartDom);
  
  const option = {
    backgroundColor: 'transparent',
    tooltip: {
      trigger: 'axis',
      backgroundColor: 'rgba(255, 255, 255, 0.95)',
      borderColor: '#e6e9f0',
      textStyle: { color: '#262626' }
    },
    legend: {
      data: ['流量 (MB/s)', '包速率 (包/s)'],
      textStyle: { color: '#262626' },
      top: 10
    },
    grid: {
      left: '3%',
      right: '4%',
      bottom: '3%',
      containLabel: true
    },
    xAxis: {
      type: 'time',
      axisLine: { lineStyle: { color: '#e6e9f0' } },
      axisLabel: { color: '#8c8c8c' },
      splitLine: { show: false }
    },
    yAxis: [
      {
        type: 'value',
        name: '流量 (MB/s)',
        nameTextStyle: { color: '#00c6ff' },
        axisLine: { lineStyle: { color: '#e6e9f0' } },
        axisLabel: { color: '#8c8c8c' },
        splitLine: { lineStyle: { color: '#f0f0f0' } }
      },
      {
        type: 'value',
        name: '包速率 (包/s)',
        nameTextStyle: { color: '#0072ff' },
        axisLine: { lineStyle: { color: '#e6e9f0' } },
        axisLabel: { color: '#8c8c8c' },
        splitLine: { show: false }
      }
    ],
    series: [
      {
        name: '流量 (MB/s)',
        type: 'line',
        yAxisIndex: 0,
        data: [],
        smooth: true,
        lineStyle: { color: '#00c6ff', width: 2 },
        itemStyle: { color: '#00c6ff' },
        areaStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: 'rgba(0, 198, 255, 0.3)' },
            { offset: 1, color: 'rgba(0, 198, 255, 0.05)' }
          ])
        }
      },
      {
        name: '包速率 (包/s)',
        type: 'line',
        yAxisIndex: 1,
        data: [],
        smooth: true,
        lineStyle: { color: '#0072ff', width: 2 },
        itemStyle: { color: '#0072ff' }
      }
    ],
    animationDuration: 1200,
    animationEasing: 'cubicOut'
  };
  
  flowChart.setOption(option);
};

// 更新图表数据
const updateFlowChart = () => {
  if (!flowChart || !flowStats.value.length) return;
  
  const bytesData = flowStats.value.map(stat => [
    new Date(stat.timestamp * 1000),
    (stat.bytes_per_sec / 1024 / 1024).toFixed(2)
  ]);
  
  const packetsData = flowStats.value.map(stat => [
    new Date(stat.timestamp * 1000),
    stat.packets_per_sec
  ]);
  
  flowChart.setOption({
    series: [
      { data: bytesData },
      { data: packetsData }
    ]
  });
};

// 事件处理函数
const refreshFlowStats = () => {
  fetchFlowStats();
  if (message) {
    message.success('流量数据已刷新');
  }
};

const toggleAutoRefresh = () => {
  autoRefresh.value = !autoRefresh.value;
  if (autoRefresh.value) {
    startAutoRefresh();
    if (message) {
      message.success('自动刷新已开启');
    }
  } else {
    stopAutoRefresh();
    if (message) {
      message.info('自动刷新已关闭');
    }
  }
};

const handleAnomaly = (anomaly: Anomaly) => {
  if (message) {
    message.info(`正在处理来自 ${anomaly.src_ip} 的 ${anomaly.type} 攻击`);
  }
  // 这里可以添加处理异常的逻辑
};

// 自动刷新控制
const startAutoRefresh = () => {
  if (refreshTimer) clearInterval(refreshTimer);
  refreshTimer = setInterval(() => {
    fetchSummary();
    fetchFlowStats();
    fetchAnomalies();
  }, 5000);
};

const stopAutoRefresh = () => {
  if (refreshTimer) {
    clearInterval(refreshTimer);
    refreshTimer = null;
  }
};

// 生命周期钩子
onMounted(async () => {
  await fetchSummary();
  await fetchFlowStats();
  await fetchAnomalies();
  
  await initFlowChart();
  
  if (autoRefresh.value) {
    startAutoRefresh();
  }
});

onUnmounted(() => {
  stopAutoRefresh();
  if (flowChart) flowChart.dispose();
});
</script>

<style scoped>
.dashboard-container {
  padding: 24px;
  background-color: var(--bg);
  min-height: 100vh;
}

.kpi-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 24px;
  margin-bottom: 24px;
}

.kpi-card {
  border-radius: var(--radius);
  box-shadow: var(--shadow);
  border: 1px solid var(--border);
}

.kpi-content {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px;
}

.kpi-info {
  flex: 1;
}

.kpi-label {
  font-size: 14px;
  color: var(--text2);
  margin: 0 0 8px 0;
}

.kpi-value {
  font-size: 24px;
  font-weight: bold;
  color: var(--text);
  margin: 0;
  font-family: 'Courier New', monospace;
}

.ip-value {
  font-size: 18px;
}

.kpi-icon {
  width: 48px;
  height: 48px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 20px;
}

.traffic-icon {
  background: linear-gradient(135deg, #00c6ff20, #0072ff20);
  color: #00c6ff;
}

.packet-icon {
  background: linear-gradient(135deg, #52c41a20, #389e0d20);
  color: #52c41a;
}

.anomaly-icon {
  background: linear-gradient(135deg, #ff4d4f20, #cf1322);
  color: #ff4d4f;
}

.attacker-icon {
  background: linear-gradient(135deg, #ffa94020, #d48806);
  color: #ffa940;
}

.chart-card, .anomaly-card {
  margin-bottom: 24px;
  border-radius: var(--radius);
  box-shadow: var(--shadow);
  border: 1px solid var(--border);
}

.chart-container {
  width: 100%;
  height: 400px;
}

.anomaly-controls {
  display: flex;
  align-items: center;
  gap: 16px;
}

.auto-refresh-status {
  font-size: 14px;
  color: var(--text2);
}

/* 异常行样式 */
:deep(.critical-row) {
  background-color: rgba(255, 77, 79, 0.1);
  border-left: 4px solid #ff4d4f;
}

:deep(.high-row) {
  background-color: rgba(255, 120, 117, 0.1);
  border-left: 4px solid #ff7875;
}

:deep(.medium-row) {
  background-color: rgba(255, 169, 64, 0.1);
  border-left: 4px solid #ffa940;
}

/* 响应式设计 */
@media (max-width: 1200px) {
  .kpi-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (max-width: 768px) {
  .kpi-grid {
    grid-template-columns: 1fr;
  }
  
  .dashboard-container {
    padding: 16px;
  }
}
</style>
