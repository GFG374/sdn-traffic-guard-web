<template>
  <div>
    <!-- 页面标题 -->
    <div class="mb-6">
      <h2 class="text-[clamp(1.5rem,3vw,2rem)] font-bold text-dark">网络状态总览</h2>
      <p class="text-dark-2 mt-1">实时监控网络运行情况和关键指标</p>
    </div>
    
    <!-- 状态卡片 -->
    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
      <div class="bg-white rounded-xl p-6 shadow-md hover:shadow-lg transition-all duration-300">
        <div class="flex items-start justify-between">
          <div>
            <p class="text-gray-600 mb-1">总节点数</p>
            <h3 class="text-3xl font-bold text-gray-800">24</h3>
            <p class="text-green-600 text-sm mt-2 flex items-center">
              <i class="fa fa-arrow-up mr-1"></i> 2 个 (本周)
            </p>
          </div>
          <div class="w-12 h-12 rounded-lg bg-blue-500/10 flex items-center justify-center text-blue-500">
            <i class="fas fa-server text-xl"></i>
          </div>
        </div>
      </div>
      
      <div class="bg-white rounded-xl p-6 card-shadow hover:shadow-lg transition-all-300">
        <div class="flex items-start justify-between">
          <div>
            <p class="text-gray-600 mb-1">活跃链路</p>
            <h3 class="text-3xl font-bold text-gray-800">42</h3>
            <p class="text-green-600 text-sm mt-2 flex items-center">
              <i class="fa fa-arrow-up mr-1"></i> 5 条 (本周)
            </p>
          </div>
          <div class="w-12 h-12 rounded-lg bg-green-500/10 flex items-center justify-center text-green-500">
            <i class="fas fa-project-diagram text-xl"></i>
          </div>
        </div>
      </div>
      
      <div class="bg-white rounded-xl p-6 card-shadow hover:shadow-lg transition-all-300">
        <div class="flex items-start justify-between">
          <div>
            <p class="text-gray-600 mb-1">网络负载</p>
            <h3 class="text-3xl font-bold text-gray-800">68%</h3>
            <p class="text-red-600 text-sm mt-2 flex items-center">
              <i class="fa fa-arrow-up mr-1"></i> 5% (今日)
            </p>
          </div>
          <div class="w-12 h-12 rounded-lg bg-yellow-500/10 flex items-center justify-center text-yellow-500">
            <i class="fas fa-tachometer-alt text-xl"></i>
          </div>
        </div>
      </div>
      
      <div class="bg-white rounded-xl p-6 card-shadow hover:shadow-lg transition-all-300">
        <div class="flex items-start justify-between">
          <div>
            <p class="text-gray-600 mb-1">异常事件</p>
            <h3 class="text-3xl font-bold text-gray-800">3</h3>
            <p class="text-green-600 text-sm mt-2 flex items-center">
              <i class="fa fa-arrow-down mr-1"></i> 2 起 (今日)
            </p>
          </div>
          <div class="w-12 h-12 rounded-lg bg-red-500/10 flex items-center justify-center text-red-500">
            <i class="fas fa-exclamation-triangle text-xl"></i>
          </div>
        </div>
      </div>
    </div>
    
    <!-- 图表和数据 -->
    <div class="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-8">
      <div class="bg-white rounded-xl p-6 shadow-md lg:col-span-2">
        <div class="flex items-center justify-between mb-6">
          <h3 class="font-semibold text-lg">网络流量趋势</h3>
          <div class="flex space-x-2">
            <button class="px-3 py-1 text-sm rounded-md bg-blue-500/10 text-blue-500">今日</button>
            <button class="px-3 py-1 text-sm rounded-md text-gray-600 hover:bg-gray-100">本周</button>
            <button class="px-3 py-1 text-sm rounded-md text-gray-600 hover:bg-gray-100">本月</button>
          </div>
        </div>
        <div class="h-80">
          <canvas id="trafficChart"></canvas>
        </div>
      </div>
      
      <div class="bg-white rounded-xl p-6 shadow-md">
        <div class="flex items-center justify-between mb-6">
          <h3 class="font-semibold text-lg">节点状态分布</h3>
          <button class="text-blue-500 hover:text-blue-400">
            <i class="fas fa-ellipsis-v"></i>
          </button>
        </div>
        <div class="h-80 flex items-center justify-center">
          <canvas id="nodeStatusChart"></canvas>
        </div>
      </div>
    </div>
    
    <!-- 最近异常和节点列表 -->
    <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
      <div class="bg-white rounded-xl p-6 card-shadow lg:col-span-2">
        <div class="flex items-center justify-between mb-6">
          <h3 class="font-semibold text-lg">最近异常事件</h3>
          <button class="text-blue-500 hover:text-blue-400 text-sm">查看全部</button>
        </div>
        
        <div class="overflow-x-auto">
          <table class="w-full">
            <thead>
              <tr class="border-b border-gray-300">
                <th class="text-left py-3 px-4 font-semibold text-gray-600">事件类型</th>
                <th class="text-left py-3 px-4 font-semibold text-gray-600">影响节点</th>
                <th class="text-left py-3 px-4 font-semibold text-gray-600">发生时间</th>
                <th class="text-left py-3 px-4 font-semibold text-gray-600">状态</th>
                <th class="text-left py-3 px-4 font-semibold text-gray-600">操作</th>
              </tr>
            </thead>
            <tbody>
              <tr class="border-b border-gray-300 hover:bg-gray-100 transition-all duration-300">
                <td class="py-3 px-4">
                  <div class="flex items-center">
                    <div class="w-8 h-8 rounded-full bg-red-500/10 flex items-center justify-center text-red-500 mr-3">
                      <i class="fas fa-exclamation-circle"></i>
                    </div>
                    <span>链路过载</span>
                  </div>
                </td>
                <td class="py-3 px-4">Switch-C - Switch-D</td>
                <td class="py-3 px-4 text-dark-2">10:23:45</td>
                <td class="py-3 px-4">
                  <span class="px-2 py-1 bg-yellow-500/10 text-yellow-600 text-xs rounded-full">处理中</span>
                </td>
                <td class="py-3 px-4">
                  <button class="text-blue-500 hover:text-blue-400">处理</button>
                </td>
              </tr>
              <tr class="border-b border-gray-300 hover:bg-gray-100 transition-all duration-300">
                <td class="py-3 px-4">
                  <div class="flex items-center">
                    <div class="w-8 h-8 rounded-full bg-yellow-500/10 flex items-center justify-center text-yellow-600 mr-3">
                      <i class="fas fa-exclamation-triangle"></i>
                    </div>
                    <span>负载过高</span>
                  </div>
                </td>
                <td class="py-3 px-4">Switch-B - Switch-C</td>
                <td class="py-3 px-4 text-dark-2">09:15:32</td>
                <td class="py-3 px-4">
                  <span class="px-2 py-1 bg-green-500/10 text-green-600 text-xs rounded-full">已解决</span>
                </td>
                <td class="py-3 px-4">
                  <button class="text-gray-600 hover:text-blue-500">详情</button>
                </td>
              </tr>
              <tr class="border-b border-gray-300 hover:bg-gray-100 transition-all duration-300">
                <td class="py-3 px-4">
                  <div class="flex items-center">
                    <div class="w-8 h-8 rounded-full bg-red-500/10 flex items-center justify-center text-red-500 mr-3">
                      <i class="fas fa-times-circle"></i>
                    </div>
                    <span>节点离线</span>
                  </div>
                </td>
                <td class="py-3 px-4">Switch-F</td>
                <td class="py-3 px-4 text-dark-2">08:42:19</td>
                <td class="py-3 px-4">
                  <span class="px-2 py-1 bg-yellow-500/10 text-yellow-600 text-xs rounded-full">处理中</span>
                </td>
                <td class="py-3 px-4">
                  <button class="text-blue-500 hover:text-blue-400">处理</button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
      
      <div class="bg-white rounded-xl p-6 shadow-md">
        <div class="flex items-center justify-between mb-6">
          <h3 class="font-semibold text-lg">节点状态</h3>
          <button class="text-blue-500 hover:text-blue-400 text-sm">刷新</button>
        </div>
        
        <div class="space-y-4">
          <div class="flex items-center justify-between p-3 rounded-lg hover:bg-gray-100 transition-all duration-300">
            <div class="flex items-center">
              <div class="w-3 h-3 bg-success rounded-full mr-3"></div>
              <span>Switch-A</span>
            </div>
            <span class="text-sm text-gray-600">在线 · 正常</span>
          </div>
          
          <div class="flex items-center justify-between p-3 rounded-lg hover:bg-gray-100 transition-all duration-300">
            <div class="flex items-center">
              <div class="w-3 h-3 bg-success rounded-full mr-3"></div>
              <span>Switch-B</span>
            </div>
            <span class="text-sm text-gray-600">在线 · 负载高</span>
          </div>
          
          <div class="flex items-center justify-between p-3 rounded-lg hover:bg-light-1 transition-all-300">
            <div class="flex items-center">
              <div class="w-3 h-3 bg-warning rounded-full mr-3"></div>
              <span>Switch-C</span>
            </div>
            <span class="text-sm text-dark-2">在线 · 需注意</span>
          </div>
          
          <div class="flex items-center justify-between p-3 rounded-lg hover:bg-light-1 transition-all-300">
            <div class="flex items-center">
              <div class="w-3 h-3 bg-danger rounded-full mr-3"></div>
              <span>Switch-D</span>
            </div>
            <span class="text-sm text-dark-2">离线 · 需处理</span>
          </div>
          
          <div class="flex items-center justify-between p-3 rounded-lg hover:bg-light-1 transition-all-300">
            <div class="flex items-center">
              <div class="w-3 h-3 bg-success rounded-full mr-3"></div>
              <span>Switch-E</span>
            </div>
            <span class="text-sm text-dark-2">在线 · 正常</span>
          </div>
          
          <div class="flex items-center justify-between p-3 rounded-lg hover:bg-light-1 transition-all-300">
            <div class="flex items-center">
              <div class="w-3 h-3 bg-success rounded-full mr-3"></div>
              <span>Switch-F</span>
            </div>
            <span class="text-sm text-dark-2">在线 · 正常</span>
          </div>
        </div>
        
        <button class="w-full mt-6 py-2 border border-light-2 rounded-lg text-dark-2 hover:bg-light-1 transition-all-300">
          查看所有节点
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted } from 'vue';
import { Chart, registerables } from 'chart.js';

// 注册Chart.js组件
Chart.register(...registerables);

onMounted(() => {
  // 网络流量趋势图
  const trafficCtx = document.getElementById('trafficChart') as HTMLCanvasElement;
  new Chart(trafficCtx, {
    type: 'line',
    data: {
      labels: ['00:00', '03:00', '06:00', '09:00', '12:00', '15:00', '18:00', '21:00'],
      datasets: [
        {
          label: '流入流量 (GB)',
          data: [12, 19, 13, 24, 22, 30, 25, 28],
          borderColor: '#165DFF',
          backgroundColor: 'rgba(22, 93, 255, 0.1)',
          tension: 0.4,
          fill: true
        },
        {
          label: '流出流量 (GB)',
          data: [8, 15, 10, 18, 25, 20, 30, 22],
          borderColor: '#52C41A',
          backgroundColor: 'rgba(82, 196, 26, 0.1)',
          tension: 0.4,
          fill: true
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
        y: {
          beginAtZero: true
        }
      }
    }
  });
  
  // 节点状态分布图
  const nodeStatusCtx = document.getElementById('nodeStatusChart') as HTMLCanvasElement;
  new Chart(nodeStatusCtx, {
    type: 'doughnut',
    data: {
      labels: ['正常', '负载高', '需注意', '离线'],
      datasets: [{
        data: [15, 4, 3, 2],
        backgroundColor: [
          '#52C41A',
          '#FAAD14',
          '#FA8C16',
          '#FF4D4F'
        ],
        borderWidth: 0
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          position: 'bottom',
        }
      },
      cutout: '70%'
    }
  });
});
</script>

<style scoped>
/* 仪表盘样式已通过Tailwind工具类实现 */
</style>
