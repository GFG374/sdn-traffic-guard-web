<template>
  <div>
    <!-- 页面标题 -->
    <div class="mb-6">
      <h2 class="text-[clamp(1.5rem,3vw,2rem)] font-bold text-dark">限速中心</h2>
      <p class="text-dark-2 mt-1">管理当前被限速的IP地址</p>
    </div>
    
    <!-- 限速IP卡片墙 -->
    <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
      <div 
        v-for="(item, index) in limitedIps" 
        :key="index" 
        class="rate-limit-card bg-white rounded-xl p-6 shadow-md hover:shadow-lg transition-all duration-300"
        :class="{ 'high-traffic': item.current_speed > 800 }"
      >
        <div class="flex items-start justify-between mb-4">
          <div>
            <h3 class="text-xl font-bold text-gray-800">{{ item.ip }}</h3>
            <p class="text-gray-600 text-sm mt-1">限速时间: {{ formatTime(item.start_time) }}</p>
            <div class="flex items-center mt-2">
              <span class="text-xs px-2 py-1 rounded-full" :class="getSpeedBadgeClass(item.current_speed)">
                {{ item.current_speed }} KB/s
              </span>
            </div>
          </div>
          <div class="w-12 h-12 rounded-lg bg-yellow-500/10 flex items-center justify-center text-yellow-500">
            <i class="fas fa-tachometer-alt text-xl"></i>
          </div>
        </div>
        
        <!-- SVG波浪进度条 -->
        <div class="mb-4">
          <div class="wave-container">
            <svg class="wave-svg" viewBox="0 0 200 60" xmlns="http://www.w3.org/2000/svg">
              <defs>
                <linearGradient :id="`waveGradient${index}`" x1="0%" y1="0%" x2="0%" y2="100%">
                  <stop offset="0%" :style="`stop-color:${getWaveColor(item.current_speed)};stop-opacity:0.8`" />
                  <stop offset="100%" :style="`stop-color:${getWaveColor(item.current_speed)};stop-opacity:0.3`" />
                </linearGradient>
                <clipPath :id="`waveClip${index}`">
                  <rect x="0" y="0" width="200" height="60" rx="8" />
                </clipPath>
              </defs>
              
              <!-- 背景 -->
              <rect x="0" y="0" width="200" height="60" rx="8" fill="#f3f4f6" />
              
              <!-- 波浪 -->
              <g :clip-path="`url(#waveClip${index})`">
                <path 
                  :d="getWavePath(getProgressPercentage(item.start_time, item.duration), index)"
                  :fill="`url(#waveGradient${index})`"
                  class="wave-path"
                >
                  <animateTransform
                    attributeName="transform"
                    type="translate"
                    values="-200,0;0,0;-200,0"
                    dur="3s"
                    repeatCount="indefinite"
                  />
                </path>
              </g>
              
              <!-- 进度文字 -->
              <text x="100" y="35" text-anchor="middle" class="wave-text" fill="#374151" font-size="12" font-weight="bold">
                {{ Math.round(getProgressPercentage(item.start_time, item.duration)) }}%
              </text>
            </svg>
          </div>
          
          <div class="flex justify-between mt-2 text-sm text-gray-600">
            <span>已限速: {{ getElapsedTime(item.start_time) }}</span>
            <span>剩余: {{ getRemainingTime(item.start_time, item.duration) }}</span>
          </div>
        </div>
        
        <!-- 速度仪表盘 -->
         <div class="mb-4">
           <div class="speed-gauge-container">
             <div :data-gauge="index" class="speed-gauge"></div>
           </div>
         </div>
        
        <!-- 热力波纹效果 -->
        <div class="ripple-container" v-if="item.current_speed > 500">
          <div class="ripple" :style="{ animationDuration: getRippleDuration(item.current_speed) }"></div>
          <div class="ripple" :style="{ animationDuration: getRippleDuration(item.current_speed), animationDelay: '0.5s' }"></div>
        </div>
        
        <button @click="handleRelease(item.ip)" class="w-full py-2 bg-blue-500 hover:bg-blue-600 text-white rounded-lg transition-colors">
          解除限速
        </button>
      </div>
      
      <div v-if="limitedIps.length === 0" class="col-span-full text-center py-12 bg-white rounded-xl shadow-md">
        <i class="fas fa-check-circle text-green-500 text-4xl mb-4"></i>
        <h3 class="text-xl font-semibold text-gray-700">当前没有被限速的IP</h3>
        <p class="text-gray-500 mt-2">所有网络流量正常运行</p>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, nextTick } from 'vue';
import axios from 'axios';

// 定义数据结构
interface LimitedIP {
  ip: string;
  start_time: number;
  duration: number; // 秒
  current_speed: number; // KB/s
  limit_speed: number; // KB/s
}

// 响应式数据
const limitedIps = ref<LimitedIP[]>([]);

// 定时器
let updateTimer: number | null = null;
let gaugeCharts: any[] = [];

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

// 获取已经过去的时间（分钟:秒）
const getElapsedTime = (startTime: number): string => {
  const elapsed = Math.floor(Date.now() / 1000) - startTime;
  const minutes = Math.floor(elapsed / 60);
  const seconds = elapsed % 60;
  return `${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
};

// 获取剩余时间（分钟:秒）
const getRemainingTime = (startTime: number, duration: number): string => {
  const elapsed = Math.floor(Date.now() / 1000) - startTime;
  const remaining = Math.max(0, duration - elapsed);
  const minutes = Math.floor(remaining / 60);
  const seconds = remaining % 60;
  return `${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
};

// 获取进度百分比
const getProgressPercentage = (startTime: number, duration: number): number => {
  const elapsed = Math.floor(Date.now() / 1000) - startTime;
  const percentage = Math.min(100, (elapsed / duration) * 100);
  return 100 - percentage; // 倒计时，所以用100减
};

// 获取速度徽章样式
const getSpeedBadgeClass = (speed: number): string => {
  if (speed > 800) return 'bg-red-100 text-red-800';
  if (speed > 500) return 'bg-orange-100 text-orange-800';
  if (speed > 200) return 'bg-yellow-100 text-yellow-800';
  return 'bg-green-100 text-green-800';
};

// 获取波浪颜色
const getWaveColor = (speed: number): string => {
  if (speed > 800) return '#ef4444'; // 红色
  if (speed > 500) return '#f97316'; // 橙色
  if (speed > 200) return '#eab308'; // 黄色
  return '#22c55e'; // 绿色
};

// 生成波浪路径
const getWavePath = (percentage: number, index: number): string => {
  const height = 60;
  const waveHeight = height * (percentage / 100);
  const waveY = height - waveHeight;
  
  // 创建波浪形状
  const amplitude = 8; // 波浪幅度
  const frequency = 0.02; // 波浪频率
  const phase = index * 0.5; // 相位偏移
  
  let path = `M 0 ${waveY}`;
  
  for (let x = 0; x <= 400; x += 2) {
    const y = waveY + Math.sin((x * frequency) + phase) * amplitude;
    path += ` L ${x} ${y}`;
  }
  
  path += ` L 400 ${height} L 0 ${height} Z`;
  return path;
};

// 获取波纹动画持续时间
const getRippleDuration = (speed: number): string => {
  // 速度越高，波纹越快
  const duration = Math.max(0.5, 2 - (speed / 1000));
  return `${duration}s`;
};

// 初始化速度仪表盘
const initSpeedGauges = async () => {
  await nextTick();
  
  // 动态导入ECharts
  const echarts = await import('echarts');
  
  limitedIps.value.forEach((item, index) => {
    const container = document.querySelector(`[data-gauge="${index}"]`) as HTMLElement;
    if (container && !gaugeCharts[index]) {
      const chart = echarts.init(container);
      
      const option = {
        series: [{
          type: 'gauge',
          startAngle: 180,
          endAngle: 0,
          center: ['50%', '75%'],
          radius: '90%',
          min: 0,
          max: item.limit_speed || 1000,
          splitNumber: 8,
          axisLine: {
            lineStyle: {
              width: 6,
              color: [
                [0.3, '#67e0e3'],
                [0.7, '#37a2da'],
                [1, '#fd666d']
              ]
            }
          },
          pointer: {
            icon: 'path://M12.8,0.7l12,40.1H0.7L12.8,0.7z',
            length: '12%',
            width: 20,
            offsetCenter: [0, '-60%'],
            itemStyle: {
              color: 'auto'
            }
          },
          axisTick: {
            length: 12,
            lineStyle: {
              color: 'auto',
              width: 2
            }
          },
          splitLine: {
            length: 20,
            lineStyle: {
              color: 'auto',
              width: 5
            }
          },
          axisLabel: {
            color: '#464646',
            fontSize: 10,
            distance: -60,
            rotate: 'tangential',
            formatter: function (value: number) {
              if (value === item.limit_speed) {
                return value + ' KB/s';
              }
              return value + '';
            }
          },
          title: {
            offsetCenter: [0, '-10%'],
            fontSize: 12
          },
          detail: {
            fontSize: 14,
            offsetCenter: [0, '-35%'],
            valueAnimation: true,
            formatter: function (value: number) {
              return Math.round(value) + ' KB/s';
            },
            color: 'auto'
          },
          data: [{
            value: item.current_speed,
            name: 'SPEED'
          }]
        }]
      };
      
      chart.setOption(option);
      gaugeCharts[index] = chart;
    }
  });
};

// 更新仪表盘数据
const updateGauges = () => {
  limitedIps.value.forEach((item, index) => {
    if (gaugeCharts[index]) {
      gaugeCharts[index].setOption({
        series: [{
          data: [{
            value: item.current_speed,
            name: 'SPEED'
          }]
        }]
      });
    }
  });
};

// 获取限速IP列表
const fetchLimitedIps = async () => {
  try {
    const response = await axios.get('/v1/ratelimit');
    // 模拟添加当前速度和限制速度数据
    limitedIps.value = response.data.map((item: any) => ({
      ...item,
      current_speed: Math.floor(Math.random() * 1000) + 100, // 模拟当前速度
      limit_speed: 1000 // 模拟限制速度
    }));
    
    // 更新仪表盘
    updateGauges();
  } catch (error) {
    console.error('获取限速IP列表失败:', error);
    // 如果API失败，使用模拟数据
    limitedIps.value = [
      {
        ip: '192.168.1.100',
        start_time: Math.floor(Date.now() / 1000) - 300,
        duration: 3600,
        current_speed: 650,
        limit_speed: 1000
      },
      {
        ip: '10.0.0.50',
        start_time: Math.floor(Date.now() / 1000) - 150,
        duration: 1800,
        current_speed: 320,
        limit_speed: 500
      }
    ];
    
    // 初始化仪表盘
    setTimeout(() => {
      initSpeedGauges();
    }, 100);
  }
};

// 处理解除限速
const handleRelease = async (ip: string) => {
  try {
    const response = await axios.post('/v1/chat', {
      user_id: 'web',
      message: `unlimit ${ip}`
    });
    
    // 显示操作结果
    alert(response.data.reply || '解除限速成功');
    
    // 刷新数据
    fetchLimitedIps();
  } catch (error) {
    console.error('解除限速失败:', error);
    alert('解除限速失败，请重试');
  }
};

onMounted(() => {
  // 初始加载数据
  fetchLimitedIps();
  
  // 设置定时器
  updateTimer = window.setInterval(() => {
    fetchLimitedIps();
  }, 2000); // 每2秒更新一次
});

onUnmounted(() => {
  // 清除定时器
  if (updateTimer) window.clearInterval(updateTimer);
  
  // 销毁图表
  gaugeCharts.forEach(chart => {
    if (chart) chart.dispose();
  });
  gaugeCharts = [];
});
</script>

<style scoped>
/* 波浪容器样式 */
.wave-container {
  width: 100%;
  height: 60px;
  border-radius: 8px;
  overflow: hidden;
  position: relative;
}

.wave-svg {
  width: 100%;
  height: 100%;
}

.wave-path {
  filter: drop-shadow(0 2px 4px rgba(0, 0, 0, 0.1));
}

/* 速度仪表盘样式 */
.speed-gauge-container {
  width: 100%;
  height: 120px;
  position: relative;
}

.speed-gauge {
  width: 100%;
  height: 100%;
}

/* 限速卡片样式 */
.rate-limit-card {
  position: relative;
  overflow: hidden;
  transition: all 0.3s ease;
}

.rate-limit-card.high-traffic {
  border: 2px solid #ef4444;
  box-shadow: 0 0 20px rgba(239, 68, 68, 0.3);
}

/* 热力波纹效果 */
.ripple-container {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  pointer-events: none;
  z-index: 0;
}

.ripple {
  position: absolute;
  top: 50%;
  left: 50%;
  width: 20px;
  height: 20px;
  border: 2px solid rgba(239, 68, 68, 0.6);
  border-radius: 50%;
  transform: translate(-50%, -50%);
  animation: ripple-expand 2s infinite;
}

@keyframes ripple-expand {
  0% {
    width: 20px;
    height: 20px;
    opacity: 1;
  }
  100% {
    width: 200px;
    height: 200px;
    opacity: 0;
  }
}

/* 高流量闪烁效果 */
.high-traffic {
  animation: traffic-pulse 2s infinite;
}

@keyframes traffic-pulse {
  0%, 100% {
    box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
  }
  50% {
    box-shadow: 0 0 20px rgba(239, 68, 68, 0.5), 0 0 40px rgba(239, 68, 68, 0.3);
  }
}

/* 深色模式支持 */
@media (prefers-color-scheme: dark) {
  .rate-limit-card {
    background-color: #1f2937;
    color: #f9fafb;
  }
  
  .wave-svg rect[fill="#f3f4f6"] {
    fill: #374151;
  }
  
  .wave-text {
    fill: #f9fafb;
  }
}

/* 响应式设计 */
@media (max-width: 640px) {
  .speed-gauge-container {
    height: 100px;
  }
  
  .wave-container {
    height: 50px;
  }
}
</style>