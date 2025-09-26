<template>
  <div class="flow-stats-page">
    <!-- KPI 条 -->
    <div class="kpi-row">
      <div class="kpi-card"><div class="num">{{ kpi.totalBytes }}</div><div class="txt">总流量</div></div>
      <div class="kpi-card"><div class="num">{{ kpi.packetRate }}</div><div class="txt">包速率</div></div>
      <div class="kpi-card"><div class="num">{{ kpi.anomalyCount }}</div><div class="txt">异常数</div></div>
      <div class="kpi-card"><div class="num">{{ kpi.topAttacker }}</div><div class="txt">TOP 攻击者</div></div>
    </div>

    <!-- 图表区 -->
    <div class="chart-row">
      <div class="left-chart">
        <h3>24h 协议流量趋势</h3>
        <div ref="lineEl" class="chart-box"></div>
      </div>
      <div class="right-chart">
        <h3>协议分布</h3>
        <div ref="pieEl" class="chart-box"></div>
      </div>
    </div>

    <!-- 实时异常表格（滑入动画） -->
    <div class="table-card">
      <h3>实时异常 TOP 20</h3>
      <transition-group name="list" tag="table" class="anomaly-table">
        <thead key="head"><tr><th>时间</th><th>源 IP</th><th>类型</th><th>详情</th><th>操作</th></tr></thead>
        <tbody key="body">
          <tr v-for="(r, i) in anomalies" :key="r.detect_time + i" :class="rowClass(r)">
            <td>{{ fmtTime(r.detect_time) }}</td>
            <td>{{ r.src_ip }}</td>
            <td><span class="tag" :class="r.anomaly_type">{{ r.anomaly_type }}</span></td>
            <td>{{ r.details }}</td>
            <td>
              <button class="btn danger" @click="addBlack(r.src_ip)">加黑</button>
              <button class="btn" @click="limit(r.src_ip)">限速</button>
            </td>
          </tr>
        </tbody>
      </transition-group>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import axios from 'axios'
import * as echarts from 'echarts'

// ---- 数据 ----
const kpi = ref({ totalBytes: '0 B', packetRate: '0 pps', anomalyCount: 0, topAttacker: '-' })
const lineEl = ref(null), pieEl = ref(null)
let lineIns, pieIns, timer

// ---- 工具 ----
const fmtTime = t => new Date(t).toLocaleString('zh-CN', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' })
const fmtBytes = b => {
  const u = ['B','KB','MB','GB'], v = Number(b)
  let i = 0, x = v
  while(x >= 1024 && i < 3){ x /= 1024; i++ }
  return x.toFixed(2) + ' ' + u[i]
}
const rowClass = r => ({ high: r.anomaly_type === 'SYN Flood', mid: r.anomaly_type === 'UDP Flood', low: true })

// ---- 图表初始化 ----
const initLine = () => {
  lineIns = echarts.init(lineEl.value)
  lineIns.setOption({
    backgroundColor: 'transparent',
    tooltip: { trigger: 'axis', axisPointer: { type: 'cross' } },
    legend: { textStyle: { color: '#b9b9b9' } },
    grid: { left: 40, right: 40, bottom: 40, top: 40 },
    xAxis: { type: 'category', boundaryGap: false, axisLine: { lineStyle: { color: '#6a7985' } }, data: [] },
    yAxis: [
      { type: 'value', name: '包速率(pps)', position: 'left', axisLine: { lineStyle: { color: '#5470c6' } } },
      { type: 'value', name: '字节速率(B/s)', position: 'right', axisLine: { lineStyle: { color: '#91cc75' } } }
    ],
    series: []
  })
}
const initPie = () => {
  pieIns = echarts.init(pieEl.value)
  pieIns.setOption({
    backgroundColor: 'transparent',
    tooltip: { trigger: 'item' },
    legend: { orient: 'vertical', left: 'left', textStyle: { color: '#b9b9b9' } },
    series: [{ type: 'pie', radius: ['40%', '70%'], itemStyle: { borderRadius: 10, borderColor: '#fff', borderWidth: 2 }, label: { show: false }, emphasis: { label: { show: true, fontSize: 20 } }, data: [] }]
  })
}

// ---- 数据加载 ----
const loadKPI = async () => {
  const s = await axios.get('/v1/summary').then(r => r.data).catch(() => ({}))
  kpi.value = { totalBytes: fmtBytes(s.today_bytes || 0), packetRate: (s.today_packets || 0).toLocaleString() + ' pps', anomalyCount: s.today_anomalies || 0, topAttacker: s.top_attacker || '-' }
}
const loadFlow = async () => {
  const raw = await axios.get('/v1/flowstats').then(r => r.data).catch(() => [])
  // 24h 桶聚合
  const bucket = {}
  raw.forEach(r => {
    const h = new Date(r.timestamp).getHours()
    if (!bucket[h]) bucket[h] = { tcp: { p: 0, b: 0 }, udp: { p: 0, b: 0 }, icmp: { p: 0, b: 0 }, arp: { p: 0, b: 0 } }
    const p = (r.protocol || 'IP').toLowerCase()
    if (bucket[h][p]) { bucket[h][p].p += r.packet_count; bucket[h][p].b += r.byte_count }
  })
  const hours = Object.keys(bucket).sort((a, b) => +a - +b).map(h => h + ':00')
  const proto = { tcp: { packets: [], bytes: [] }, udp: { packets: [], bytes: [] }, icmp: { packets: [], bytes: [] }, arp: { packets: [], bytes: [] } }
  hours.forEach(h => Object.keys(proto).forEach(p => { proto[p].packets.push(bucket[h][p].p); proto[p].bytes.push(bucket[h][p].b) }))
  // 折线
  const series = []
  Object.keys(proto).forEach((p, i) => {
    series.push({ name: `${p.toUpperCase()} 包`, type: 'line', smooth: true, yAxisIndex: 0, data: proto[p].packets, lineStyle: { width: 2, color: ['#5470c6', '#91cc75', '#fac858', '#ee6666'][i % 4] } })
    series.push({ name: `${p.toUpperCase()} 字节`, type: 'line', smooth: true, yAxisIndex: 1, data: proto[p].bytes, lineStyle: { width: 2, type: 'dashed', color: ['#5470c6', '#91cc75', '#fac858', '#ee6666'][i % 4] } })
  })
  lineIns.setOption({ xAxis: { data: hours }, series })
  // 饼图
  const pieData = Object.keys(proto).map(p => ({ name: p.toUpperCase(), value: proto[p].bytes.reduce((a, b) => a + b, 0) }))
  pieIns.setOption({ series: [{ data: pieData }] })
}
const loadAnomaly = async () => {
  const data = await axios.get('/v1/anomalies').then(r => r.data).catch(() => [])
  anomalies.value = data.slice(0, 20)
}

// ---- 按钮 ----
const addBlack = async ip => {
  const res = await axios.post('/v1/chat', { user_id: 'web', user: `ai: 加黑 ${ip}` }).catch(() => ({}))
  alert(res.data?.reply || '已加黑')
}
const limit = async ip => {
  const res = await axios.post('/v1/chat', { user_id: 'web', user: `ai: 手动限速 ${ip} 1024` }).catch(() => ({}))
  alert(res.data?.reply || '已限速')
}

// ---- 生命周期 ----
const anomalies = ref([])
onMounted(() => {
  initLine(); initPie()
  loadKPI(); loadFlow(); loadAnomaly()
  timer = setInterval(() => { loadKPI(); loadFlow(); loadAnomaly() }, 10000)
})
onUnmounted(() => {
  clearInterval(timer)
  lineIns?.dispose(); pieIns?.dispose()
})
</script>

<style scoped>
/* ---- 暗黑主题 ---- */
.flow-stats-page{
  background:#0f0f0f;
  color:#b9b9b9;
  min-height:100vh;
  padding:24px;
}
.kpi-row{
  display:grid;
  grid-template-columns:repeat(4,1fr);
  gap:16px;
  margin-bottom:24px;
}
.kpi-card{
  background:#1e1e1e;
  border-radius:12px;
  padding:20px;
  text-align:center;
  box-shadow:0 2px 8px rgba(0,0,0,.4);
}
.kpi-card .num{
  font-size:2rem;
  font-weight:700;
  color:#00ff92;
  font-family:ui-monospace,SFMono-Regular,Menlo,Monaco,Consolas,"Liberation Mono","Courier New",monospace;
}
.kpi-card .txt{
  margin-top:4px;
  font-size:.875rem;
  color:#6a7985;
}
.chart-row{
  display:grid;
  grid-template-columns:2fr 1fr;
  gap:16px;
  margin-bottom:24px;
}
.left-chart,.right-chart{
  background:#1e1e1e;
  border-radius:12px;
  padding:20px;
  box-shadow:0 2px 8px rgba(0,0,0,.4);
}
.left-chart h3,.right-chart h3{
  margin:0 0 12px;
  font-size:1.1rem;
  color:#b9b9b9;
}
.chart-box{
  height:320px;
}
.table-card{
  background:#1e1e1e;
  border-radius:12px;
  padding:20px;
  box-shadow:0 2px 8px rgba(0,0,0,.4);
}
.table-card h3{
  margin:0 0 12px;
  font-size:1.1rem;
  color:#b9b9b9;
}
.anomaly-table{
  width:100%;
  border-collapse:collapse;
}
.anomaly-table th{
  padding:12px;
  text-align:left;
  font-size:.875rem;
  color:#6a7985;
  border-bottom:1px solid #333;
}
.anomaly-table td{
  padding:12px;
  font-size:.875rem;
  border-bottom:1px solid #333;
}
.anomaly-table tr.high{
  background:#2e0b0b;
  border-left:4px solid #ff2e63;
}
.anomaly-table tr.mid{
  background:#2e1f0b;
  border-left:4px solid #ff9800;
}
.anomaly-table tr.low{
  border-left:4px solid #6a7985;
}
.tag{
  padding:2px 8px;
  border-radius:4px;
  font-size:.75rem;
  font-weight:600;
}
.tag.SYN\ Flood{ background:#ff2e63; color:#fff; }
.tag.UDP\ Flood{ background:#ff9800; color:#fff; }
.tag.ICMP\ Flood{ background:#ffeb3b; color:#000; }
.tag.ARP\ Flood{ background:#9c27b0; color:#fff; }
.btn{
  padding:4px 10px;
  margin-left:6px;
  border:none;
  border-radius:4px;
  font-size:.75rem;
  cursor:pointer;
  transition:opacity .2s;
}
.btn.danger{ background:#ff2e63; color:#fff; }
.btn:hover{ opacity:.8; }

/* 滑入动画 */
.list-enter-active,.list-leave-active{ transition:all .3s ease; }
.list-enter-from{ transform:translateY(-10px); opacity:0; }
.list-leave-to{ transform:translateY(10px); opacity:0; }
</style>
