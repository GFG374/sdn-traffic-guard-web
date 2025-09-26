// src/api/service.js
import axios from 'axios'

const base = '/v1'

export const api = {
  // 异常列表
  getAnomalies: () => axios.get(`${base}/anomalies`).then(r => r.data),

  // 聊天指令（加黑 / 限速 / 解除 都用这一个）
  sendCmd: (cmd) => axios.post(`${base}/chat`, {
    user_id: 'web',
    user: `ai: ${cmd}`
  }).then(r => r.data.reply)
}
