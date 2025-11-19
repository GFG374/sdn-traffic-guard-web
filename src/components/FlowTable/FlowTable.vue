<template>
  <div class="min-h-screen bg-gray-50 font-inter">
    <main class="container mx-auto px-4 py-6">
      
      <!-- 🎨 顶部区域：网络拓扑 + 控制器状态 (两列布局) -->
      <div class="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-6">
        
        <!-- 左侧：网络拓扑 (占2列) -->
        <div class="lg:col-span-2 bg-white rounded-lg shadow-md border border-gray-200">
          <div class="px-6 py-4 border-b border-gray-200 flex items-center justify-between">
            <h3 class="text-lg font-bold text-gray-800 flex items-center gap-2">
              <span class="text-blue-600">📡</span>
              <span>网络拓扑</span>
            </h3>
            <span class="text-xs text-gray-500">实时同步 • RYU可视化</span>
          </div>
          <div class="topology-container">
            <svg viewBox="0 0 800 400" class="w-full h-auto">
              <!-- 定义渐变和样式 -->
              <defs>
                <!-- 交换机渐变 -->
                <linearGradient id="switchGradient" x1="0%" y1="0%" x2="0%" y2="100%">
                  <stop offset="0%" style="stop-color:#667eea;stop-opacity:1" />
                  <stop offset="100%" style="stop-color:#4c51bf;stop-opacity:1" />
                </linearGradient>
                <!-- 主机渐变 -->
                <linearGradient id="hostGradient" x1="0%" y1="0%" x2="0%" y2="100%">
                  <stop offset="0%" style="stop-color:#34d399;stop-opacity:1" />
                  <stop offset="100%" style="stop-color:#10b981;stop-opacity:1" />
                </linearGradient>
                <!-- 阴影效果 -->
                <filter id="shadow" x="-50%" y="-50%" width="200%" height="200%">
                  <feGaussianBlur in="SourceAlpha" stdDeviation="3"/>
                  <feOffset dx="0" dy="2" result="offsetblur"/>
                  <feComponentTransfer>
                    <feFuncA type="linear" slope="0.3"/>
                  </feComponentTransfer>
                  <feMerge>
                    <feMergeNode/>
                    <feMergeNode in="SourceGraphic"/>
                  </feMerge>
                </filter>
              </defs>
              
              <!-- 交换机 - 专业图标 -->
              <g id="switch" filter="url(#shadow)">
                <!-- 主体 -->
                <rect x="340" y="165" width="120" height="70" rx="8" fill="url(#switchGradient)" stroke="#4c51bf" stroke-width="2"/>
                <!-- 顶部装饰条 -->
                <rect x="340" y="165" width="120" height="12" rx="8" fill="#5a67d8" opacity="0.5"/>
                <!-- 端口指示灯 -->
                <circle cx="360" cy="195" r="3" fill="#48bb78"/>
                <circle cx="375" cy="195" r="3" fill="#48bb78"/>
                <circle cx="390" cy="195" r="3" fill="#48bb78"/>
                <circle cx="405" cy="195" r="3" fill="#48bb78"/>
                <circle cx="420" cy="195" r="3" fill="#48bb78"/>
                <circle cx="435" cy="195" r="3" fill="#48bb78"/>
                <!-- 文字 -->
                <text x="400" y="220" text-anchor="middle" fill="white" font-weight="bold" font-size="14">交换机 S1</text>
                <!-- 底部通风孔装饰 -->
                <line x1="350" y1="225" x2="450" y2="225" stroke="#5a67d8" stroke-width="1" opacity="0.3"/>
              </g>
              
              <!-- 8个主机 - 电脑图标样式 -->
              <!-- h1 (192.168.1.100) - 上 -->
              <g class="host" @click="selectHost('h1')" filter="url(#shadow)">
                <!-- 显示器 -->
                <rect x="375" y="30" width="50" height="35" rx="3" fill="url(#hostGradient)" stroke="#059669" stroke-width="2"/>
                <rect x="380" y="35" width="40" height="25" rx="2" fill="#1e293b"/>
                <!-- 支架 -->
                <rect x="395" y="65" width="10" height="8" fill="#059669"/>
                <rect x="385" y="73" width="30" height="3" rx="1" fill="#059669"/>
                <!-- 标签 -->
                <text x="400" y="95" text-anchor="middle" fill="#374151" font-weight="bold" font-size="12">H1</text>
                <text x="400" y="107" text-anchor="middle" fill="#6b7280" font-size="10">.100</text>
                <!-- 连接线 -->
                <line x1="400" y1="76" x2="400" y2="165" stroke="#9ca3af" stroke-width="2" stroke-dasharray="5,3"/>
              </g>
              
              <!-- h8 (192.168.1.108) - 右上 -->
              <g class="host" @click="selectHost('h8')" filter="url(#shadow)">
                <rect x="525" y="75" width="50" height="35" rx="3" fill="url(#hostGradient)" stroke="#059669" stroke-width="2"/>
                <rect x="530" y="80" width="40" height="25" rx="2" fill="#1e293b"/>
                <rect x="545" y="110" width="10" height="8" fill="#059669"/>
                <rect x="535" y="118" width="30" height="3" rx="1" fill="#059669"/>
                <text x="550" y="138" text-anchor="middle" fill="#374151" font-weight="bold" font-size="12">H8</text>
                <text x="550" y="150" text-anchor="middle" fill="#6b7280" font-size="10">.108</text>
                <line x1="540" y1="121" x2="440" y2="180" stroke="#9ca3af" stroke-width="2" stroke-dasharray="5,3"/>
              </g>
              
              <!-- h2 (192.168.1.101) - 右 -->
              <g class="host" @click="selectHost('h2')" filter="url(#shadow)">
                <rect x="575" y="182" width="50" height="35" rx="3" fill="url(#hostGradient)" stroke="#059669" stroke-width="2"/>
                <rect x="580" y="187" width="40" height="25" rx="2" fill="#1e293b"/>
                <rect x="595" y="217" width="10" height="8" fill="#059669"/>
                <rect x="585" y="225" width="30" height="3" rx="1" fill="#059669"/>
                <text x="630" y="205" text-anchor="start" fill="#374151" font-weight="bold" font-size="12">H2</text>
                <text x="630" y="217" text-anchor="start" fill="#6b7280" font-size="10">.101</text>
                <line x1="575" y1="200" x2="460" y2="200" stroke="#9ca3af" stroke-width="2" stroke-dasharray="5,3"/>
              </g>
              
              <!-- h3 (192.168.1.102) - 右下 -->
              <g class="host" @click="selectHost('h3')" filter="url(#shadow)">
                <rect x="525" y="270" width="50" height="35" rx="3" fill="url(#hostGradient)" stroke="#059669" stroke-width="2"/>
                <rect x="530" y="275" width="40" height="25" rx="2" fill="#1e293b"/>
                <rect x="545" y="305" width="10" height="8" fill="#059669"/>
                <rect x="535" y="313" width="30" height="3" rx="1" fill="#059669"/>
                <text x="550" y="335" text-anchor="middle" fill="#374151" font-weight="bold" font-size="12">H3</text>
                <text x="550" y="347" text-anchor="middle" fill="#6b7280" font-size="10">.102</text>
                <line x1="540" y1="270" x2="440" y2="220" stroke="#9ca3af" stroke-width="2" stroke-dasharray="5,3"/>
              </g>
              
              <!-- h4 (192.168.1.103) - 下 -->
              <g class="host" @click="selectHost('h4')" filter="url(#shadow)">
                <rect x="375" y="320" width="50" height="35" rx="3" fill="url(#hostGradient)" stroke="#059669" stroke-width="2"/>
                <rect x="380" y="325" width="40" height="25" rx="2" fill="#1e293b"/>
                <rect x="395" y="355" width="10" height="8" fill="#059669"/>
                <rect x="385" y="363" width="30" height="3" rx="1" fill="#059669"/>
                <text x="400" y="383" text-anchor="middle" fill="#374151" font-weight="bold" font-size="12">H4</text>
                <text x="400" y="395" text-anchor="middle" fill="#6b7280" font-size="10">.103</text>
                <line x1="400" y1="320" x2="400" y2="235" stroke="#9ca3af" stroke-width="2" stroke-dasharray="5,3"/>
              </g>
              
              <!-- h5 (192.168.1.104) - 左下 -->
              <g class="host" @click="selectHost('h5')" filter="url(#shadow)">
                <rect x="225" y="270" width="50" height="35" rx="3" fill="url(#hostGradient)" stroke="#059669" stroke-width="2"/>
                <rect x="230" y="275" width="40" height="25" rx="2" fill="#1e293b"/>
                <rect x="245" y="305" width="10" height="8" fill="#059669"/>
                <rect x="235" y="313" width="30" height="3" rx="1" fill="#059669"/>
                <text x="250" y="335" text-anchor="middle" fill="#374151" font-weight="bold" font-size="12">H5</text>
                <text x="250" y="347" text-anchor="middle" fill="#6b7280" font-size="10">.104</text>
                <line x1="260" y1="270" x2="360" y2="220" stroke="#9ca3af" stroke-width="2" stroke-dasharray="5,3"/>
              </g>
              
              <!-- h6 (192.168.1.105) - 左 -->
              <g class="host" @click="selectHost('h6')" filter="url(#shadow)">
                <rect x="175" y="182" width="50" height="35" rx="3" fill="url(#hostGradient)" stroke="#059669" stroke-width="2"/>
                <rect x="180" y="187" width="40" height="25" rx="2" fill="#1e293b"/>
                <rect x="195" y="217" width="10" height="8" fill="#059669"/>
                <rect x="185" y="225" width="30" height="3" rx="1" fill="#059669"/>
                <text x="170" y="205" text-anchor="end" fill="#374151" font-weight="bold" font-size="12">H6</text>
                <text x="170" y="217" text-anchor="end" fill="#6b7280" font-size="10">.105</text>
                <line x1="225" y1="200" x2="340" y2="200" stroke="#9ca3af" stroke-width="2" stroke-dasharray="5,3"/>
              </g>
              
              <!-- h7 (192.168.1.200) - 左上 -->
              <g class="host" @click="selectHost('h7')" filter="url(#shadow)">
                <rect x="225" y="75" width="50" height="35" rx="3" fill="url(#hostGradient)" stroke="#059669" stroke-width="2"/>
                <rect x="230" y="80" width="40" height="25" rx="2" fill="#1e293b"/>
                <rect x="245" y="110" width="10" height="8" fill="#059669"/>
                <rect x="235" y="118" width="30" height="3" rx="1" fill="#059669"/>
                <text x="250" y="138" text-anchor="middle" fill="#374151" font-weight="bold" font-size="12">H7</text>
                <text x="250" y="150" text-anchor="middle" fill="#6b7280" font-size="10">.200</text>
                <line x1="260" y1="121" x2="360" y2="180" stroke="#9ca3af" stroke-width="2" stroke-dasharray="5,3"/>
              </g>
              
              <!-- 流表发送动画箭头 -->
              <g v-if="showFlowAnimation" class="flow-animation">
                <defs>
                  <marker id="arrowhead" markerWidth="10" markerHeight="10" refX="9" refY="3" orient="auto">
                    <polygon points="0 0, 10 3, 0 6" fill="#ef4444" />
                  </marker>
                </defs>
                <line 
                  :x1="flowAnimSrc.x" 
                  :y1="flowAnimSrc.y" 
                  :x2="flowAnimDst.x" 
                  :y2="flowAnimDst.y" 
                  stroke="#ef4444" 
                  stroke-width="3" 
                  marker-end="url(#arrowhead)"
                  class="animated-arrow"
                />
                <text 
                  :x="(flowAnimSrc.x + flowAnimDst.x) / 2" 
                  :y="(flowAnimSrc.y + flowAnimDst.y) / 2 - 10" 
                  text-anchor="middle" 
                  fill="#ef4444" 
                  font-weight="bold" 
                  font-size="12"
                  class="animated-text"
                >
                  流表已下发
                </text>
              </g>
            </svg>
          </div>
          <div class="px-6 py-3 bg-gray-50 border-t border-gray-200 text-xs text-gray-600">
            💡 提示：8个主机在192.168.1.0/24网段 (.100, .101, .102, .103, .104, .105, .108, .200)
          </div>
        </div>
        
        <!-- 右侧：控制器状态 (占1列) -->
        <div class="bg-white rounded-lg shadow-md border border-gray-200">
          <div class="px-6 py-4 border-b border-gray-200">
            <h3 class="text-lg font-bold text-gray-800 flex items-center gap-2">
              <span class="text-blue-600">🎛️</span>
              <span>控制器状态</span>
            </h3>
          </div>
          <div class="p-6 space-y-4">
            <!-- 在线状态 -->
            <div class="flex items-center justify-between pb-3 border-b border-gray-100">
              <span class="text-sm text-gray-600">交换机</span>
              <span class="text-2xl font-bold text-gray-900">{{ switches.length }}</span>
            </div>
            <div class="flex items-center justify-between pb-3 border-b border-gray-100">
              <span class="text-sm text-gray-600">主机</span>
              <span class="text-2xl font-bold text-gray-900">8</span>
            </div>
            <div class="flex items-center justify-between pb-3 border-b border-gray-100">
              <span class="text-sm text-gray-600">主控制器</span>
              <span class="text-sm font-mono text-blue-600">192.168.44.129:8080</span>
            </div>
            
            <!-- 网段信息 -->
            <div class="pt-2">
              <div class="text-xs text-gray-500 mb-2">网段：</div>
              <div class="bg-gray-50 px-3 py-2 rounded text-xs font-mono text-gray-700">
                192.168.1.0/24
              </div>
              <div class="mt-2 text-xs text-gray-500">
                主控地址：用于连接RYU控制器
              </div>
            </div>
            
            <!-- IP列表 -->
            <div class="pt-2">
              <div class="text-xs text-gray-500 mb-2">IP：</div>
              <div class="flex flex-wrap gap-1">
                <span v-for="ip in ['101', '102', '103', '104', '105', '106', '108', '200']" :key="ip"
                      class="px-2 py-1 bg-blue-50 text-blue-700 rounded text-xs font-mono">
                  .{{ ip }}
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- 🚨 设备异常监控区域 -->
      <div class="mb-6 bg-white rounded-lg shadow-md border border-gray-200">
        <div class="px-6 py-4 border-b border-gray-200 flex items-center justify-between">
          <h3 class="text-lg font-bold text-gray-800 flex items-center gap-2">
            <span class="text-orange-500">⚠️</span>
            <span>设备异常监控</span>
          </h3>
          <div class="flex items-center gap-3">
            <select v-model="statusFilter" @change="loadDeviceAnomalies"
                    class="px-4 py-2 border border-gray-300 rounded-lg text-sm focus:border-blue-500 focus:ring-2 focus:ring-blue-100 bg-white">
              <option value="all">全部</option>
              <option value="pending">未处理</option>
              <option value="handled">已处理</option>
            </select>
            <button @click="loadDeviceAnomalies" 
                    class="px-4 py-2 bg-blue-500 text-white text-sm rounded-lg hover:bg-blue-600 transition-all flex items-center gap-2">
              <span>🔄</span>
              <span>刷新</span>
            </button>
          </div>
        </div>
        
        <!-- 无异常状态 -->
        <div v-if="deviceAnomalies.length === 0" 
             class="p-16 text-center bg-gradient-to-br from-green-50 to-emerald-50">
          <div class="inline-flex items-center justify-center w-20 h-20 bg-green-500 rounded-full mb-4">
            <svg class="w-12 h-12 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="3" d="M5 13l4 4L19 7"></path>
            </svg>
          </div>
          <p class="text-2xl font-bold text-green-700 mb-2">系统运行正常</p>
          <p class="text-sm text-gray-600">未检测到设备异常</p>
        </div>
        
        <!-- 有异常时显示列表 -->
        <div v-else class="p-6">
          <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            <div v-for="anomaly in deviceAnomalies" :key="anomaly.id" 
                 class="bg-white p-4 rounded-lg border-2 hover:shadow-lg transition-all"
                 :class="{
                   'border-red-300 bg-red-50': anomaly.severity === 'high',
                   'border-yellow-300 bg-yellow-50': anomaly.severity === 'medium',
                   'border-blue-300 bg-blue-50': anomaly.severity === 'low'
                 }">
              <div class="flex items-start justify-between mb-3">
                <span class="px-2 py-1 rounded text-xs font-bold"
                      :class="{
                        'bg-red-600 text-white': anomaly.severity === 'high',
                        'bg-yellow-600 text-white': anomaly.severity === 'medium',
                        'bg-blue-600 text-white': anomaly.severity === 'low'
                      }">
                  {{ anomaly.severity.toUpperCase() }}
                </span>
                <span class="px-2 py-1 rounded text-xs font-medium"
                      :class="{
                        'bg-orange-200 text-orange-800': anomaly.status === 'pending',
                        'bg-green-200 text-green-800': anomaly.status === 'handled'
                      }">
                  {{ anomaly.status === 'pending' ? '待处理' : '已处理' }}
                </span>
              </div>
              <h4 class="font-bold text-gray-800 text-sm mb-2">{{ anomaly.anomaly_type }}</h4>
              <p class="text-xs text-gray-600 mb-2 leading-relaxed">{{ anomaly.description }}</p>
              <div class="flex items-center justify-between text-xs text-gray-500 mb-3">
                <span class="font-mono">{{ anomaly.device_id }}</span>
                <span>{{ anomaly.detected_at }}</span>
              </div>
              <!-- ✅ 新增：已处理按钮 -->
              <div class="flex gap-2">
                <button 
                  @click="markAnomalyAsResolved(anomaly.id)"
                  class="flex-1 px-3 py-2 text-xs font-bold text-white bg-green-500 rounded-lg hover:bg-green-600 transition-colors duration-200 flex items-center justify-center gap-1.5"
                >
                  <i class="fa fa-check text-xs"></i>
                  <span>已处理</span>
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- 流表管理 -->
      <div class="bg-white rounded-lg shadow-md border border-gray-200 mb-6">
        <div class="px-6 py-4 border-b border-gray-200 flex items-center justify-between">
          <h3 class="text-lg font-bold text-gray-800 flex items-center gap-2">
            <span class="text-blue-600">📊</span>
            <span>流表管理</span>
          </h3>
          <div class="flex items-center gap-3">
            <select v-model="selectedSwitch" @change="loadFlows" 
                    class="px-4 py-2 border border-gray-300 rounded-lg text-sm focus:border-blue-500 focus:ring-2 focus:ring-blue-100 bg-white">
              <option value="">-- 请选择交换机 --</option>
              <option v-for="sw in switches" :key="sw" :value="sw">
                交换机 S{{ sw }}
              </option>
            </select>
            <button @click="refreshData" :disabled="loading"
                    class="px-4 py-2 bg-blue-500 text-white text-sm rounded-lg hover:bg-blue-600 transition-all disabled:opacity-50">
              🔄 刷新
            </button>
            <button @click="showAddModal = true" :disabled="!selectedSwitch"
                    class="px-4 py-2 bg-purple-500 text-white text-sm rounded-lg hover:bg-purple-600 transition-all disabled:opacity-50">
              ➕ 添加流表
            </button>
            <button @click="showTemplateModal = true" :disabled="!selectedSwitch"
                    class="px-4 py-2 bg-yellow-500 text-white text-sm rounded-lg hover:bg-yellow-600 transition-all disabled:opacity-50">
              🚀 快速场景
            </button>
          </div>
        </div>

        <!-- 加载/空状态 -->
        <div v-if="loading" class="p-12 text-center text-gray-500">
          <div class="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500 mb-2"></div>
          <p>加载中...</p>
        </div>
        
        <div v-else-if="!selectedSwitch" class="p-12 text-center text-gray-400">
          <p class="text-lg">👆 请选择一个交换机查看流表</p>
        </div>

        <!-- 流表列表 -->
        <div v-else-if="flows.length > 0" class="overflow-x-auto">
          <table class="w-full">
            <thead class="bg-gray-50 border-b border-gray-200">
              <tr>
                <th class="px-4 py-3 text-left text-xs font-semibold text-gray-600 uppercase">优先级</th>
                <th class="px-4 py-3 text-left text-xs font-semibold text-gray-600 uppercase">匹配字段</th>
                <th class="px-4 py-3 text-left text-xs font-semibold text-gray-600 uppercase">动作</th>
                <th class="px-4 py-3 text-left text-xs font-semibold text-gray-600 uppercase">包计数</th>
                <th class="px-4 py-3 text-left text-xs font-semibold text-gray-600 uppercase">字节数</th>
                <th class="px-4 py-3 text-left text-xs font-semibold text-gray-600 uppercase">操作</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-gray-200">
              <tr v-for="(flow, index) in flows" :key="index" class="hover:bg-gray-50">
                <td class="px-4 py-3">
                  <span class="px-2 py-1 bg-blue-100 text-blue-700 rounded text-xs font-semibold">
                    {{ flow.priority }}
                  </span>
                </td>
                <td class="px-4 py-3 text-sm text-gray-700">
                  <div v-if="Object.keys(flow.match).length > 0" class="space-y-1">
                    <div v-for="(value, key) in flow.match" :key="key" class="flex items-center gap-1">
                      <span class="font-medium text-gray-600">{{ formatMatchKey(key) }}:</span>
                      <span>{{ formatMatchValue(key, value) }}</span>
                    </div>
                  </div>
                  <span v-else class="text-gray-400 italic">匹配所有</span>
                </td>
                <td class="px-4 py-3 text-sm">
                  <div v-if="flow.actions && flow.actions.length > 0" class="space-y-1">
                    <div v-for="(action, idx) in flow.actions" :key="idx">
                      {{ formatAction(action) }}
                    </div>
                  </div>
                  <div v-else class="text-red-600 font-medium">
                    🚫 丢弃
                  </div>
                </td>
                <td class="px-4 py-3 text-sm font-mono text-gray-700">{{ flow.packet_count || 0 }}</td>
                <td class="px-4 py-3 text-sm font-mono text-gray-700">{{ formatBytes(flow.byte_count || 0) }}</td>
                <td class="px-4 py-3">
                  <div class="flex items-center gap-2">
                    <button @click="viewDetails(flow)" 
                            class="px-3 py-1 bg-blue-500 text-white text-xs rounded hover:bg-blue-600">
                      查看
                    </button>
                    <button @click="deleteFlow(flow)" 
                            class="px-3 py-1 bg-red-500 text-white text-xs rounded hover:bg-red-600">
                      删除
                    </button>
                  </div>
                </td>
              </tr>
            </tbody>
          </table>
        </div>

        <!-- 空状态 -->
        <div v-else class="p-12 text-center text-gray-400">
          <p class="text-lg">📋 该交换机暂无流表项</p>
          <p class="text-sm mt-2">点击"添加流表"或"快速场景"开始配置</p>
        </div>
      </div>

    <!-- 添加流表模态框 -->
    <div v-if="showAddModal" class="modal-overlay" @click.self="showAddModal = false">
      <div class="modal large">
        <div class="flex justify-between items-center mb-6">
          <h3 class="text-2xl font-bold text-gray-800">➕ 添加流表</h3>
          <button @click="showAddModal = false" class="text-gray-400 hover:text-gray-600 text-2xl">✕</button>
        </div>
        
        <!-- ✅ 第1步：选择场景类型 -->
        <div class="mb-6">
          <label class="block text-sm font-semibold text-gray-700 mb-3">🎯 选择场景类型</label>
          <div class="grid grid-cols-2 gap-3">
            <button @click="newFlow.scenarioType = 'forward'" 
                    :class="newFlow.scenarioType === 'forward' ? 'bg-blue-500 text-white' : 'bg-gray-100 text-gray-700'"
                    class="p-4 rounded-xl font-medium hover:shadow-md transition-all">
              📤 允许转发
            </button>
            <button @click="newFlow.scenarioType = 'block'" 
                    :class="newFlow.scenarioType === 'block' ? 'bg-red-500 text-white' : 'bg-gray-100 text-gray-700'"
                    class="p-4 rounded-xl font-medium hover:shadow-md transition-all">
              🚫 封禁阻止
            </button>
            <button @click="newFlow.scenarioType = 'ratelimit'" 
                    :class="newFlow.scenarioType === 'ratelimit' ? 'bg-yellow-500 text-white' : 'bg-gray-100 text-gray-700'"
                    class="p-4 rounded-xl font-medium hover:shadow-md transition-all">
              ⚡ 限速控制
            </button>
            <button @click="newFlow.scenarioType = 'custom'" 
                    :class="newFlow.scenarioType === 'custom' ? 'bg-purple-500 text-white' : 'bg-gray-100 text-gray-700'"
                    class="p-4 rounded-xl font-medium hover:shadow-md transition-all">
              ⚙️ 自定义
            </button>
          </div>
        </div>
        
        <!-- ✅ 第2步：根据场景类型显示字段 -->
        <div v-if="newFlow.scenarioType" class="space-y-6">
          
          <!-- 场景1：允许转发 -->
          <div v-if="newFlow.scenarioType === 'forward'" class="bg-blue-50 p-6 rounded-xl border-2 border-blue-200">
            <h4 class="font-semibold text-blue-900 mb-4 flex items-center gap-2">
              <span>📤</span>
              <span>允许转发配置</span>
            </h4>
            <div class="grid grid-cols-2 gap-4">
              <div>
                <label class="block text-sm font-medium text-gray-700 mb-2">源IP</label>
                <input type="text" v-model="newFlow.match.ipv4_src" placeholder="192.168.1.100" 
                       class="w-full px-4 py-2 border-2 border-gray-300 rounded-lg focus:border-blue-500" />
              </div>
              <div>
                <label class="block text-sm font-medium text-gray-700 mb-2">目标IP</label>
                <input type="text" v-model="newFlow.match.ipv4_dst" placeholder="192.168.1.200" 
                       class="w-full px-4 py-2 border-2 border-gray-300 rounded-lg focus:border-blue-500" />
              </div>
              <div>
                <label class="block text-sm font-medium text-gray-700 mb-2">输出端口</label>
                <select v-model.number="newFlow.actions.output" 
                        class="w-full px-4 py-2 border-2 border-gray-300 rounded-lg focus:border-blue-500">
                  <option :value="null">选择输出端口...</option>
                  <option :value="1">1 - H1 (.100)</option>
                  <option :value="2">2 - H2 (.101)</option>
                  <option :value="3">3 - H3 (.102)</option>
                  <option :value="4">4 - H4 (.103)</option>
                  <option :value="5">5 - H5 (.104)</option>
                  <option :value="6">6 - H6 (.105)</option>
                  <option :value="7">7 - H7 (.108)</option>
                  <option :value="8">8 - H8 (.200)</option>
                </select>
              </div>
              <div>
                <label class="block text-sm font-medium text-gray-700 mb-2">优先级</label>
                <input type="number" v-model.number="newFlow.priority" value="100" 
                       class="w-full px-4 py-2 border-2 border-gray-300 rounded-lg focus:border-blue-500" />
              </div>
            </div>
          </div>
          
          <!-- 场景2：封禁阻止 -->
          <div v-if="newFlow.scenarioType === 'block'" class="bg-red-50 p-6 rounded-xl border-2 border-red-200">
            <h4 class="font-semibold text-red-900 mb-4 flex items-center gap-2">
              <span></span>
              <span>封禁阻止配置</span>
            </h4>
            <div class="grid grid-cols-2 gap-4">
              <div>
                <label class="block text-sm font-medium text-gray-700 mb-2">源IP（要封禁的IP）</label>
                <input type="text" v-model="newFlow.match.ipv4_src" placeholder="192.168.1.101" 
                       class="w-full px-4 py-2 border-2 border-gray-300 rounded-lg focus:border-red-500" />
              </div>
              <div>
                <label class="block text-sm font-medium text-gray-700 mb-2">目标IP（留空=封禁所有）</label>
                <input type="text" v-model="newFlow.match.ipv4_dst" placeholder="留空或192.168.1.200" 
                       class="w-full px-4 py-2 border-2 border-gray-300 rounded-lg focus:border-red-500" />
              </div>
              <div>
                <label class="block text-sm font-medium text-gray-700 mb-2">优先级（建议200）</label>
                <input type="number" v-model.number="newFlow.priority" value="200" 
                       class="w-full px-4 py-2 border-2 border-gray-300 rounded-lg focus:border-red-500" />
              </div>
            </div>
            <div class="mt-4 p-4 bg-red-100 rounded-lg">
              <p class="text-sm text-red-800"> 注意：封禁规则不需要设置输出端口，系统会自动DROP数据包</p>
            </div>
          </div>
          
          <!-- 场景3：限速控制 -->
          <div v-if="newFlow.scenarioType === 'ratelimit'" class="bg-yellow-50 p-6 rounded-xl border-2 border-yellow-200">
            <h4 class="font-semibold text-yellow-900 mb-4 flex items-center gap-2">
              <span></span>
              <span>限速控制配置</span>
            </h4>
            <div class="grid grid-cols-2 gap-4">
              <div>
                <label class="block text-sm font-medium text-gray-700 mb-2">源IP（要限速的IP）</label>
                <input type="text" v-model="newFlow.match.ipv4_src" placeholder="192.168.1.102" 
                       class="w-full px-4 py-2 border-2 border-gray-300 rounded-lg focus:border-yellow-500" />
              </div>
              <div>
                <label class="block text-sm font-medium text-gray-700 mb-2">限速级别</label>
                <select v-model.number="newFlow.actions.queue_id" 
                        class="w-full px-4 py-2 border-2 border-gray-300 rounded-lg focus:border-yellow-500">
                  <option :value="null">不限速</option>
                  <option :value="1"> 低速 (256Kbps)</option>
                  <option :value="2"> 中速 (1024Kbps)</option>
                  <option :value="3"> 高速 (2048Kbps)</option>
                </select>
              </div>
              <div>
                <label class="block text-sm font-medium text-gray-700 mb-2">优先级</label>
                <input type="number" v-model.number="newFlow.priority" value="120" 
                       class="w-full px-4 py-2 border-2 border-gray-300 rounded-lg focus:border-yellow-500" />
              </div>
            </div>
            <div class="mt-4 p-4 bg-yellow-100 rounded-lg">
              <p class="text-sm text-yellow-800"> 提示：限速后数据包会使用NORMAL转发</p>
            </div>
          </div>
          
          <!-- 场景4：自定义 -->
          <div v-if="newFlow.scenarioType === 'custom'" class="bg-purple-50 p-6 rounded-xl border-2 border-purple-200">
            <h4 class="font-semibold text-purple-900 mb-4"> 自定义配置（高级）</h4>
            <p class="text-sm text-gray-600 mb-4">请使用快速场景模板或查看文档</p>
            <button @click="showTemplateModal = true; showAddModal = false" 
                    class="px-4 py-2 bg-purple-500 text-white rounded-lg hover:bg-purple-600">
              查看快速场景
            </button>
          </div>  
        </div>
        
        <!-- 底部按钮 -->
        <div v-if="newFlow.scenarioType" class="flex justify-end gap-3 mt-6 pt-6 border-t border-gray-200">
          <button @click="showAddModal = false" 
                  class="px-8 py-3 border-2 border-gray-300 rounded-xl hover:bg-gray-50 transition-all font-medium text-gray-700">
            取消
          </button>
          <button @click="handleAddFlowClick" 
                  class="px-8 py-3 bg-blue-500 text-white rounded-xl hover:shadow-lg transition-all font-medium">
            添加流表
          </button>
        </div>
      </div>
    </div>

    <!-- 详情模态框 -->
    <div v-if="showDetailsModal" class="modal-overlay" @click.self="showDetailsModal = false">
      <div class="modal">
        <h3>流表详情</h3>
        <pre>{{ JSON.stringify(selectedFlow, null, 2) }}</pre>
        <button @click="showDetailsModal = false">关闭</button>
      </div>
    </div>
    
    <!-- 快速场景模态框 -->
    <div v-if="showTemplateModal" class="modal-overlay" @click.self="showTemplateModal = false">
      <div class="modal large">
        <div class="flex justify-between items-center mb-4">
          <h3 class="text-xl font-bold">📋 快速场景模板</h3>
          <button @click="showTemplateModal = false" class="text-gray-400 hover:text-gray-600">✕</button>
        </div>
        
        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
          <!-- 场景1: 主机间定向转发 -->
          <div class="template-card" @click="applyTemplate(1)">
            <div class="template-header">
              <span class="template-icon">🎯</span>
              <h4 class="template-title">场景1: 主机间定向转发</h4>
            </div>
            <p class="template-desc">H1 (192.168.1.100) → H7 (192.168.1.200) 精准转发</p>
            <div class="template-details">
              <div class="text-xs text-gray-600">
                <div>• 匹配: 源IP=.100, 目标IP=.200</div>
                <div>• 动作: 输出到端口 8</div>
                <div>• 优先级: 100</div>
              </div>
            </div>
          </div>
          
          <!-- 场景2: 封禁特定IP访问 -->
          <div class="template-card" @click="applyTemplate(2)">
            <div class="template-header">
              <span class="template-icon">🚫</span>
              <h4 class="template-title">场景2: 封禁IP访问</h4>
            </div>
            <p class="template-desc">禁止 H2 (192.168.1.101) 访问 H7</p>
            <div class="template-details">
              <div class="text-xs text-gray-600">
                <div>• 匹配: 源IP=.101, 目标IP=.200</div>
                <div>• 动作: 无（丢弃）</div>
                <div>• 优先级: 200 (高于普通转发)</div>
              </div>
            </div>
          </div>
          
          <!-- 场景3: 只允许HTTP流量 -->
          <div class="template-card" @click="applyTemplate(3)">
            <div class="template-header">
              <span class="template-icon">🌍</span>
              <h4 class="template-title">场景3: 只允许HTTP流量</h4>
            </div>
            <p class="template-desc">只允许端口80的TCP流量到达H7</p>
            <div class="template-details">
              <div class="text-xs text-gray-600">
                <div>• 匹配: 目标IP=.200, TCP, 端口80</div>
                <div>• 动作: 输出到端口 8</div>
                <div>• 优先级: 150</div>
              </div>
            </div>
          </div>
          
          <!-- 场景4: ARP学习 -->
          <div class="template-card" @click="applyTemplate(4)">
            <div class="template-header">
              <span class="template-icon">📚</span>
              <h4 class="template-title">场景4: ARP学习</h4>
            </div>
            <p class="template-desc">所有ARP请求发送给控制器</p>
            <div class="template-details">
              <div class="text-xs text-gray-600">
                <div>• 匹配: 以太网类型=ARP (0x0806)</div>
                <div>• 动作: CONTROLLER</div>
                <div>• 优先级: 50</div>
              </div>
            </div>
          </div>
          
          <!-- 场景5: 限速低速IP -->
          <div class="template-card" @click="applyTemplate(5)">
            <div class="template-header">
              <span class="template-icon">🐌</span>
              <h4 class="template-title">场景5: 限速低速 (256K)</h4>
            </div>
            <p class="template-desc">对 H3 (192.168.1.102) 应用低速限制</p>
            <div class="template-details">
              <div class="text-xs text-gray-600">
                <div>• 匹配: 源IP=.102</div>
                <div>• 动作: FLOOD + 队列ID=1 (低速)</div>
                <div>• 优先级: 120</div>
              </div>
            </div>
          </div>
          
          <!-- 场景6: 限速中速 -->
          <div class="template-card" @click="applyTemplate(6)">
            <div class="template-header">
              <span class="template-icon">🐎</span>
              <h4 class="template-title">场景6: 限速中速 (1M)</h4>
            </div>
            <p class="template-desc">对 H4 (192.168.1.103) 应用中速限制</p>
            <div class="template-details">
              <div class="text-xs text-gray-600">
                <div>• 匹配: 源IP=.103</div>
                <div>• 动作: FLOOD + 队列ID=2 (中速)</div>
                <div>• 优先级: 120</div>
              </div>
            </div>
          </div>
        </div>
        
        <div class="mt-4 p-3 bg-yellow-50 border border-yellow-200 rounded-lg text-sm text-yellow-800">
          <strong>⚠️ 注意：</strong> 点击场景卡片将直接发送流表到交换机，并在拓扑图上显示动画。
        </div>
        
        <div class="modal-footer">
          <button @click="showTemplateModal = false" class="btn-secondary">关闭</button>
        </div>
      </div>
    </div>
    </main>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import ryuApi from '@/api/ryu'

const controllerOnline = ref(false)
const switches = ref<number[]>([])
const selectedSwitch = ref('')
const flows = ref<any[]>([])
const loading = ref(false)
const showAddModal = ref(false)
const showDetailsModal = ref(false)
const showTemplateModal = ref(false)
const selectedFlow = ref<any>(null)
const showFlowAnimation = ref(false)
const flowAnimSrc = ref({ x: 400, y: 200 })
const flowAnimDst = ref({ x: 400, y: 200 })
// ✅ 用于跟踪当前显示箭头的流表信息
// @ts-ignore - 这个变量在setInterval中使用，TypeScript误报
const currentAnimatedFlow = ref<{srcIp: string, dstIp: string, priority: number} | null>(null)
const flowCheckInterval = ref<number | null>(null)

// ✅ 设备异常数据
const deviceAnomalies = ref<any[]>([])
const statusFilter = ref<'all' | 'pending' | 'handled'>('all')

const newFlow = ref({
  scenarioType: '',  // ✅ 场景类型：forward, block, ratelimit, custom
  priority: 100,
  idle_timeout: 0,
  match: { 
    in_port: null, 
    eth_src: null, 
    eth_dst: null,
    eth_type: null,
    ipv4_src: null,
    ipv4_dst: null,
    ip_proto: null,
    tcp_src: null,
    tcp_dst: null
  },
  actions: { output: null, queue_id: null }
})

// IP地址与拓扑图坐标的映射
const ipToCoords: Record<string, {x: number, y: number}> = {
  '192.168.1.100': { x: 400, y: 50 },   // H1
  '192.168.1.108': { x: 550, y: 100 },  // H8
  '192.168.1.101': { x: 600, y: 200 },  // H2
  '192.168.1.102': { x: 550, y: 300 },  // H3
  '192.168.1.103': { x: 400, y: 350 },  // H4
  '192.168.1.104': { x: 250, y: 300 },  // H5
  '192.168.1.105': { x: 200, y: 200 },  // H6
  '192.168.1.200': { x: 250, y: 100 },  // H7
  'switch': { x: 400, y: 200 }          // S1
}

const selectHost = (hostName: string) => {
  console.log(`选中主机: ${hostName}`)
  // 可以扩展：点击主机后自动填充IP地址到表单
}

const checkControllerStatus = async () => {
  try {
    const res = await ryuApi.getSDNControllerStatus()
    controllerOnline.value = res.status === 'online'
  } catch (e) {
    controllerOnline.value = false
  }
}

const loadSwitches = async () => {
  try {
    const res = await ryuApi.getSDNSwitches()
    if (res.success) {
      switches.value = res.switches
      // ✅ 自动选中第一个交换机（如果当前没有选中）
      if (switches.value.length > 0 && !selectedSwitch.value) {
        selectedSwitch.value = String(switches.value[0])  // ✅ 修复：number转string
        await loadFlows()
      }
    }
  } catch (e) {
    console.error(e)
  }
}

const loadFlows = async () => {
  if (!selectedSwitch.value) return
  loading.value = true
  try {
    const res = await ryuApi.getSDNSwitchFlows(selectedSwitch.value)
    if (res.success) flows.value = res.flows
  } catch (e) {
    console.error(e)
  } finally {
    loading.value = false
  }
}

const refreshData = async () => {
  await checkControllerStatus()
  await loadSwitches()
  // loadSwitches 中已经处理了自动选中和加载流表
}

const handleAddFlowClick = () => {
  console.log('[提交按钮] newFlow.value:', JSON.parse(JSON.stringify(newFlow.value)))
  addFlow()
}

const addFlow = async (flowData?: any, skipAnimation = false) => {
  if (!selectedSwitch.value) return
  
  // ✅ 关键修复：先确保 newFlow.value.actions 存在
  if (!flowData && !newFlow.value.actions) {
    console.error('[addFlow] ❌ newFlow.value.actions 是 undefined，强制初始化！')
    newFlow.value.actions = { output: null, queue_id: null }
  }
  
  const flow = flowData || newFlow.value
  
  // ✅ 调试日志：打印当前flow对象
  console.log('[addFlow] 开始添加流表，flow对象:', JSON.parse(JSON.stringify(flow)))
  console.log('[addFlow] flow.actions:', flow.actions)
  console.log('[addFlow] flow.actions?.output:', flow.actions?.output)
  
  // ✅ 防御性检查：确保 match 和 actions 对象存在
  if (!flow.match) {
    flow.match = {
      in_port: null,
      eth_src: null,
      eth_dst: null,
      eth_type: null,
      ipv4_src: null,
      ipv4_dst: null,
      ip_proto: null,
      tcp_src: null,
      tcp_dst: null
    }
  }
  
  if (!flow.actions) {
    console.error('[addFlow] ❌ flow.actions 是 undefined，强制初始化！')
    flow.actions = {
      output: null,
      queue_id: null
    }
  }
  
  // ✅ 根据场景类型自动设置参数
  if (flow.scenarioType === 'block') {
    // 封禁场景：不需要输出端口
    flow.actions.output = null
    flow.match.eth_type = 0x0800  // IPv4
  } else if (flow.scenarioType === 'ratelimit') {
    // 限速场景：使用NORMAL转发（而非FLOOD）
    flow.actions.output = 4294967290  // OFPP_NORMAL = 0xfffffffa
    flow.match.eth_type = 0x0800  // IPv4
  } else if (flow.scenarioType === 'forward') {
    // 转发场景：需要输出端口
    if (!flow.actions.output) {
      alert('请选择输出端口')
      return
    }
    flow.match.eth_type = 0x0800  // IPv4
  }
  
  try {
    // ✅ 确保所有数值参数都是整数类型
    const flowEntry: any = { 
      priority: parseInt(flow.priority) || 100,
      idle_timeout: parseInt(flow.idle_timeout) || 0,
      hard_timeout: 0,
      match: {}, 
      actions: [] 
    }
    
    // 构建匹配字段（所有访问都加上 flow.match 存在性检查，并确保数值类型正确）
    if (flow.match) {
      // ✅ 强制添加eth_type（所有场景都需要）
      flowEntry.match.eth_type = parseInt(flow.match.eth_type) || 0x0800
      
      // 其他匹配字段
      if (flow.match.in_port) flowEntry.match.in_port = parseInt(flow.match.in_port)
      if (flow.match.eth_src) flowEntry.match.eth_src = flow.match.eth_src
      if (flow.match.eth_dst) flowEntry.match.eth_dst = flow.match.eth_dst
      if (flow.match.ipv4_src && flow.match.ipv4_src.trim()) {
        flowEntry.match.ipv4_src = flow.match.ipv4_src.trim()
      }
      if (flow.match.ipv4_dst && flow.match.ipv4_dst.trim()) {
        flowEntry.match.ipv4_dst = flow.match.ipv4_dst.trim()
      }
      if (flow.match.ip_proto) flowEntry.match.ip_proto = parseInt(flow.match.ip_proto)
      if (flow.match.tcp_src) flowEntry.match.tcp_src = parseInt(flow.match.tcp_src)
      if (flow.match.tcp_dst) flowEntry.match.tcp_dst = parseInt(flow.match.tcp_dst)
    }
    
    console.log('[addFlow] 构建的flowEntry:', JSON.stringify(flowEntry, null, 2))
    
    // ✅ 添加动作（确保 port 是整数或特殊值）
    let outputPort = flow.actions?.output
    
    // 封禁场景：不添加OUTPUT动作（port为null = DROP）
    if (outputPort === null || outputPort === undefined) {
      console.log('[addFlow] 封禁场景：不添加OUTPUT动作（actions为空数组=DROP）')
      // ✅ 不添加任何action，actions保持为空数组
    } else {
      // 转发/限速场景：添加OUTPUT动作
      outputPort = parseInt(outputPort)
      const action: any = { type: 'OUTPUT', port: outputPort }
      if (flow.actions?.queue_id) action.queue_id = parseInt(flow.actions.queue_id)
      flowEntry.actions.push(action)
      console.log('[addFlow] 添加OUTPUT动作:', action)
    }
    
    const res = await ryuApi.addSDNFlowEntry(selectedSwitch.value, flowEntry)
    if (res.success) {
      alert('✅ 流表添加成功！')
      showAddModal.value = false
      
      // 显示动画
      if (!skipAnimation && flow.match) {
        showFlowAnimationEffect(flow.match.ipv4_src, flow.match.ipv4_dst)
      }
      
      // 重置表单
      if (!flowData) {
        newFlow.value = { 
          scenarioType: '',
          priority: 100,
          idle_timeout: 0,
          match: { 
            in_port: null, eth_src: null, eth_dst: null,
            eth_type: null, ipv4_src: null, ipv4_dst: null,
            ip_proto: null, tcp_src: null, tcp_dst: null
          },
          actions: { output: null, queue_id: null }
        }
      }
      await loadFlows()
    }
  } catch (e: any) {
    alert('❌ 添加失败: ' + (e.response?.data?.detail || e.message))
  }
}

const showFlowAnimationEffect = (srcIp?: string, dstIp?: string) => {
  if (srcIp && ipToCoords[srcIp]) {
    flowAnimSrc.value = ipToCoords[srcIp]
  } else {
    flowAnimSrc.value = ipToCoords['switch']
  }
  
  if (dstIp && ipToCoords[dstIp]) {
    flowAnimDst.value = ipToCoords[dstIp]
  } else {
    flowAnimDst.value = ipToCoords['switch']
  }
  
  showFlowAnimation.value = true
  // ✅ 将动画时间延长到60秒，与流表的idle_timeout同步
  setTimeout(() => {
    showFlowAnimation.value = false
  }, 60000)
}

const applyTemplate = async (templateId: number) => {
  if (!selectedSwitch.value) return
  
  let templateFlow: any = null
  
  switch (templateId) {
    case 1: // 场景1: 主机间定向转发 H1 -> H7
      templateFlow = {
        priority: 100,
        idle_timeout: 0,
        match: {
          ipv4_src: '192.168.1.100',
          ipv4_dst: '192.168.1.200',
          eth_type: 0x0800
        },
        actions: { output: 8, queue_id: null }
      }
      break
      
    case 2: // 场景2: 封禁IP访问 H2 -X-> H7
      templateFlow = {
        priority: 200,
        idle_timeout: 0,
        match: {
          ipv4_src: '192.168.1.101',
          ipv4_dst: '192.168.1.200',
          eth_type: 0x0800
        },
        actions: { output: null, queue_id: null } // 无输出 = 丢弃
      }
      // 封禁场景特殊处理
      if (confirm('确定封禁 192.168.1.101 访问 192.168.1.200？（数据包将被丢弃）')) {
        try {
          const flowEntry = {
            priority: 200,
            idle_timeout: 0,
            hard_timeout: 0,
            match: {
              ipv4_src: '192.168.1.101',
              ipv4_dst: '192.168.1.200',
              eth_type: 0x0800
            },
            actions: [] // 空动作 = DROP
          }
          const res = await ryuApi.addSDNFlowEntry(selectedSwitch.value, flowEntry)
          if (res.success) {
            alert('✅ 封禁流表添加成功！')
            showFlowAnimationEffect('192.168.1.101', '192.168.1.200')
            showTemplateModal.value = false
            await loadFlows()
          }
        } catch (e: any) {
          alert('❌ 添加失败: ' + (e.response?.data?.detail || e.message))
        }
      }
      return
      
    case 3: // 场景3: 只允许HTTP流量
      // ✅ 特殊处理：需要添加两条流表
      if (confirm('场景3将添加两条流表：①允许HTTP(TCP 80)、②阻止其他流量到H7，确认继续？')) {
        try {
          // 第1条：允许HTTP流量
          const httpFlow = {
            priority: 150,
            idle_timeout: 0,
            hard_timeout: 0,
            match: {
              ipv4_dst: '192.168.1.200',
              eth_type: 0x0800,
              ip_proto: 6,  // TCP
              tcp_dst: 80
            },
            actions: [{ type: 'OUTPUT', port: 8 }]
          }
          await ryuApi.addSDNFlowEntry(selectedSwitch.value, httpFlow)
          
          // 第2条：阻止其他流量到H7（优先级更低）
          const blockFlow = {
            priority: 100,
            idle_timeout: 0,
            hard_timeout: 0,
            match: {
              ipv4_dst: '192.168.1.200',
              eth_type: 0x0800
            },
            actions: [] // 空动作 = DROP
          }
          const res = await ryuApi.addSDNFlowEntry(selectedSwitch.value, blockFlow)
          
          if (res.success) {
            alert('✅ 场景3流表添加成功！现在只允许HTTP流量到H7')
            showTemplateModal.value = false
            await loadFlows()
          }
        } catch (e: any) {
          alert('❌ 添加失败: ' + (e.response?.data?.detail || e.message))
        }
      }
      return
      
    case 4: // 场景4: ARP学习
      templateFlow = {
        priority: 50,
        idle_timeout: 0,
        match: {
          eth_type: 0x0806  // ARP
        },
        actions: { output: 4294967293, queue_id: null } // CONTROLLER
      }
      break
      
    case 5: // 场景5: 限速低速 H3
      templateFlow = {
        priority: 120,
        idle_timeout: 0,
        match: {
          ipv4_src: '192.168.1.102',
          eth_type: 0x0800
        },
        actions: { output: 4294967290, queue_id: 1 } // NORMAL + 低速队列
      }
      break
      
    case 6: // 场景6: 限速中速 H4
      templateFlow = {
        priority: 120,
        idle_timeout: 0,
        match: {
          ipv4_src: '192.168.1.103',
          eth_type: 0x0800
        },
        actions: { output: 4294967290, queue_id: 2 } // NORMAL + 中速队列
      }
      break
  }
  
  if (templateFlow) {
    showTemplateModal.value = false
    await addFlow(templateFlow)
  }
}

const deleteFlow = async (flow: any) => {
  if (!confirm('确定删除?')) return
  try {
    const res = await ryuApi.deleteSDNFlowEntry(selectedSwitch.value, flow)
    if (res.success) {
      alert('删除成功')
      await loadFlows()
    }
  } catch (e: any) {
    alert('删除失败: ' + (e.response?.data?.detail || e.message))
  }
}

// ✅ 移除未使用的函数（已注释，如需要可取消注释）
// const deleteAllFlows = async () => {
//   if (!confirm('确定删除所有流表?')) return
//   try {
//     const res = await ryuApi.deleteSDNAllFlows(selectedSwitch.value)
//     if (res.success) {
//       alert('所有流表已删除')
//       await loadFlows()
//     }
//   } catch (e: any) {
//     alert('删除失败: ' + (e.response?.data?.detail || e.message))
//   }
// }

const viewDetails = (flow: any) => {
  selectedFlow.value = flow
  showDetailsModal.value = true
}

const formatBytes = (bytes: number) => {
  if (bytes === 0) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i]
}

const formatAction = (action: any) => {
  if (action.type === 'OUTPUT') {
    // 处理特殊的OpenFlow端口常量
    const portValue = action.port_name || action.port
    const portMap: Record<string | number, string> = {
      'FLOOD': 'NORMAL',  // 将FLOOD显示为NORMAL
      'CONTROLLER': 'NORMAL',  // 将CONTROLLER显示为NORMAL
      4294967291: 'NORMAL',  // FLOOD的数值
      4294967293: 'NORMAL'   // NORMAL的数值
    }
    
    // 如果是特殊端口，使用映射表
    if (portMap[portValue]) {
      return `📤 ${portMap[portValue]}转发`
    }
    
    // 优先使用可读的端口名称
    if (action.port_name) {
      return `📤 输出到 ${action.port_name}`
    }
    return `📤 输出到端口 ${action.port}`
  }
  if (action.type === 'SET_QUEUE') {
    return `⚡ 限速队列 ${action.queue_id}`
  }
  if (action.type === 'DROP') {
    return '🚫 丢弃 (DROP)'
  }
  return JSON.stringify(action)
}

// ✅ 格式化匹配字段的key（更易读）
const formatMatchKey = (key: string | number): string => {
  const keyStr = String(key)
  const keyMap: Record<string, string> = {
    'eth_type': '以太网类型',
    'ipv4_src': '源IP',
    'ipv4_dst': '目标IP',
    'in_port': '输入端口',
    'eth_src': '源MAC',
    'eth_dst': '目标MAC',
    'ip_proto': 'IP协议',
    'tcp_src': '源端口(TCP)',
    'tcp_dst': '目标端口(TCP)',
    'udp_src': '源端口(UDP)',
    'udp_dst': '目标端口(UDP)'
  }
  return keyMap[keyStr] || keyStr
}

// ✅ 格式化匹配字段的value
const formatMatchValue = (key: string | number, value: any): string => {
  const keyStr = String(key)
  if (keyStr === 'eth_type') {
    // 以太网类型的十六进制转换
    const numValue: number = typeof value === 'number' ? value : parseInt(String(value), 10)
    const typeMap: { [key: number]: string } = {
      2048: 'IPv4',     // 0x0800
      2054: 'ARP',      // 0x0806
      34525: 'IPv6'     // 0x86dd
    }
    return typeMap[numValue] || `0x${numValue.toString(16)}`
  }
  if (keyStr === 'ip_proto') {
    const numValue: number = typeof value === 'number' ? value : parseInt(String(value), 10)
    const protoMap: { [key: number]: string } = {
      1: 'ICMP',
      6: 'TCP',
      17: 'UDP'
    }
    return protoMap[numValue] || String(value)
  }
  return String(value)
}

// ✅ 加载设备异常列表（支持状态筛选，hours为空=全部）
const loadDeviceAnomalies = async () => {
  try {
    const statusParam = statusFilter.value === 'all' ? null : statusFilter.value
    const res = await ryuApi.getDeviceAnomalies(null, statusParam)
    if (res && res.success && res.data) {
      deviceAnomalies.value = res.data
      console.log(`✅ 设备异常加载成功（${statusFilter.value}）:`, deviceAnomalies.value.length)
    }
  } catch (e: any) {
    console.error('❌ 加载设备异常失败:', e)
  }
}

// ✅ 标记异常为已处理
const markAnomalyAsResolved = async (anomalyId: number) => {
  try {
    console.log(`[DEBUG] 开始标记异常 ${anomalyId} 为已处理`)
    const res = await ryuApi.updateDeviceAnomalyStatus(anomalyId, 'handled')
    console.log(`[DEBUG] 后端返回: ${JSON.stringify(res)}`)
    
    // 检查响应是否为成功
    if (res && (res.success === true || res.success === 'true')) {
      await loadDeviceAnomalies()
      console.log(`✅ 异常 ${anomalyId} 已标记为已处理`)
    } else if (res && res.message) {
      await loadDeviceAnomalies()
      console.log(`✅ 异常 ${anomalyId} 已处理: ${res.message}`)
    } else {
      console.error(`❌ 标记失败，响应: ${JSON.stringify(res)}`)
      alert('❌ 标记失败: ' + (res?.message || '未知错误'))
    }
  } catch (e: any) {
    console.error(`[ERROR] 标记异常 ${anomalyId} 时出错:`, e)
    
    const status = e.response?.status
    const detail = e.response?.data?.detail || e.message || '未知错误'
    
    if (status === 404) {
      await loadDeviceAnomalies()
      console.warn(`⚠️ 异常 ${anomalyId} 已不存在，视为已处理。`)
    } else if (status === 500) {
      alert(`❌ 服务器错误: ${detail}`)
    } else {
      alert(`❌ 标记失败: ${detail}`)
    }
  }
}

onMounted(() => {
  refreshData()
  // ✅ 加载设备异常
  loadDeviceAnomalies()
  
  // ✅ 每30秒自动刷新设备异常（实时监控）
  setInterval(() => {
    loadDeviceAnomalies()
  }, 30000)
})

// ✅ 组件卸载时清除定时器，防止内存泄漏
onUnmounted(() => {
  if (flowCheckInterval.value) {
    clearInterval(flowCheckInterval.value)
    flowCheckInterval.value = null
  }
})
</script>

<style scoped>
/* 拓扑图样式 */
.topology-container {
  background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
  border-radius: 12px;
  padding: 2rem;
  min-height: 400px;
}

.host {
  cursor: pointer;
  transition: all 0.3s ease;
}

.host:hover circle {
  filter: brightness(1.2);
  stroke-width: 3;
}

.host:hover {
  transform: scale(1.05);
}

/* 状态指示器 */
.status-indicator {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.status-dot {
  width: 12px;
  height: 12px;
  border-radius: 50%;
  animation: pulse 2s infinite;
}

.status-indicator.online .status-dot {
  background: #10b981;
  box-shadow: 0 0 10px rgba(16, 185, 129, 0.5);
}

.status-indicator.offline .status-dot {
  background: #ef4444;
  box-shadow: 0 0 10px rgba(239, 68, 68, 0.5);
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

/* 状态徽章样式 */
.status-badge {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem 1rem;
  border-radius: 9999px;
  font-size: 0.875rem;
  font-weight: 600;
  transition: all 0.2s;
}

.status-online {
  background: #d1fae5;
  color: #065f46;
  border: 2px solid #10b981;
}

.status-offline {
  background: #fee2e2;
  color: #991b1b;
  border: 2px solid #ef4444;
}

.status-badge .status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  animation: pulse 2s infinite;
}

.status-online .status-dot {
  background: #10b981;
}

.status-offline .status-dot {
  background: #ef4444;
}

/* 优化表格样式 */
.flows-table {
  border-collapse: separate;
  border-spacing: 0;
}

.flows-table thead th {
  background: linear-gradient(to bottom, #f9fafb, #f3f4f6);
  padding: 1rem;
  font-weight: 600;
  color: #374151;
  border-bottom: 2px solid #e5e7eb;
  font-size: 0.875rem;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.flows-table thead th:first-child {
  border-top-left-radius: 0.75rem;
}

.flows-table thead th:last-child {
  border-top-right-radius: 0.75rem;
}

.flows-table tbody tr {
  transition: all 0.2s;
}

.flows-table tbody tr:hover {
  background: #f9fafb;
  transform: scale(1.01);
  box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
}

.flows-table tbody td {
  padding: 1rem;
  border-bottom: 1px solid #f3f4f6;
}
.switch-selector { background: white; border-radius: 12px; padding: 1.5rem; margin-bottom: 1.5rem; display: flex; gap: 1rem; align-items: center; }
.switch-selector label { font-weight: 600; }
.switch-selector select { flex: 1; padding: 0.5rem; border: 2px solid #e5e7eb; border-radius: 8px; }
.switch-selector button { padding: 0.5rem 1rem; border: none; border-radius: 8px; font-weight: 600; cursor: pointer; }
.btn-template { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; }
.stats { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 1.5rem; margin-bottom: 1.5rem; }
.stat-card { background: white; border-radius: 12px; padding: 1.5rem; display: flex; flex-direction: column; gap: 0.5rem; }
.stat-card strong { font-size: 1.5rem; color: #667eea; }
.loading { background: white; border-radius: 12px; padding: 2rem; text-align: center; }
.flows-card { background: white; border-radius: 12px; padding: 1.5rem; }
.card-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem; }
.danger-btn { padding: 0.5rem 1rem; background: #ef4444; color: white; border: none; border-radius: 8px; cursor: pointer; }
.flows-table { width: 100%; border-collapse: collapse; }
.flows-table th { background: #f9fafb; padding: 0.75rem; text-align: left; font-weight: 600; border-bottom: 2px solid #e5e7eb; }
.flows-table td { padding: 1rem; border-bottom: 1px solid #e5e7eb; }
.btn-view, .btn-delete { padding: 0.25rem 0.75rem; border: none; border-radius: 6px; cursor: pointer; margin-right: 0.5rem; }
.btn-view { background: #3b82f6; color: white; }
.btn-delete { background: #ef4444; color: white; }
.empty { background: white; border-radius: 12px; padding: 3rem; text-align: center; color: #6b7280; }
.modal-overlay { 
  position: fixed; 
  top: 0; 
  left: 0; 
  right: 0; 
  bottom: 0; 
  background: rgba(0,0,0,0.6);
  backdrop-filter: blur(4px);
  display: flex; 
  align-items: center; 
  justify-content: center; 
  z-index: 1000;
  animation: fadeIn 0.2s ease;
}

@keyframes fadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}

.modal { 
  background: white; 
  border-radius: 16px; 
  padding: 2rem; 
  max-width: 500px; 
  width: 90%; 
  max-height: 80vh; 
  overflow-y: auto;
  box-shadow: 0 20px 60px rgba(0,0,0,0.3);
  animation: slideUp 0.3s ease;
}

.modal.large {
  max-width: 900px;
}

@keyframes slideUp {
  from { 
    transform: translateY(30px);
    opacity: 0;
  }
  to { 
    transform: translateY(0);
    opacity: 1;
  }
}

.modal h3 { 
  margin-bottom: 1rem;
  color: #1f2937;
}

/* 表单网格布局 */
.form-grid {
  display: grid;
  grid-template-columns: 1fr;
  gap: 2rem;
}

@media (min-width: 768px) {
  .form-grid {
    grid-template-columns: repeat(3, 1fr);
  }
}

.form-section {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.section-title {
  font-size: 1rem;
  font-weight: 600;
  color: #667eea;
  margin-bottom: 0.5rem;
  padding-bottom: 0.5rem;
  border-bottom: 2px solid #e5e7eb;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.form-group label {
  font-size: 0.875rem;
  font-weight: 500;
  color: #374151;
}

.form-input {
  padding: 0.625rem;
  border: 2px solid #e5e7eb;
  border-radius: 8px;
  font-size: 0.875rem;
  transition: all 0.2s;
}

.form-input:focus {
  outline: none;
  border-color: #667eea;
  box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
}

.hint {
  font-size: 0.75rem;
  color: #6b7280;
  margin-top: 0.25rem;
}

.modal-footer { 
  margin-top: 2rem;
  padding-top: 1.5rem;
  border-top: 1px solid #e5e7eb;
  display: flex; 
  gap: 1rem; 
  justify-content: flex-end;
}

.modal-footer button { 
  padding: 0.625rem 1.5rem;
  border: none; 
  border-radius: 8px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-primary { 
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
}

.btn-primary:hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 16px rgba(102, 126, 234, 0.5);
}

.btn-secondary {
  background: #f3f4f6;
  color: #374151;
}

.btn-secondary:hover {
  background: #e5e7eb;
}

pre { 
  background: #f9fafb; 
  padding: 1rem; 
  border-radius: 8px; 
  overflow-x: auto; 
  font-size: 0.875rem;
  border: 1px solid #e5e7eb;
}

/* 流表动画 */
.animated-arrow {
  animation: flowPulse 1.5s ease-in-out infinite;
  stroke-dasharray: 10 5;
  stroke-dashoffset: 0;
  animation: dash 1s linear infinite, flowPulse 1.5s ease-in-out infinite;
}

@keyframes dash {
  to {
    stroke-dashoffset: -15;
  }
}

@keyframes flowPulse {
  0%, 100% {
    opacity: 1;
    stroke-width: 3;
  }
  50% {
    opacity: 0.6;
    stroke-width: 4;
  }
}

.animated-text {
  animation: textFade 1.5s ease-in-out infinite;
}

@keyframes textFade {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.6; }
}

/* 场景模板卡片 */
.template-card {
  background: white;
  border: 2px solid #e5e7eb;
  border-radius: 12px;
  padding: 1.5rem;
  cursor: pointer;
  transition: all 0.3s ease;
}

.template-card:hover {
  border-color: #667eea;
  box-shadow: 0 8px 20px rgba(102, 126, 234, 0.2);
  transform: translateY(-4px);
}

.template-header {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  margin-bottom: 0.75rem;
}

.template-icon {
  font-size: 2rem;
}

.template-title {
  font-size: 1rem;
  font-weight: 600;
  color: #1f2937;
}

.template-desc {
  color: #6b7280;
  font-size: 0.875rem;
  margin-bottom: 1rem;
}

.template-details {
  background: #f9fafb;
  border-radius: 8px;
  padding: 0.75rem;
  border-left: 3px solid #667eea;
}
</style>
