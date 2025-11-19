#!/bin/bash
# setup_qos.sh
# 开机自动给 Mininet 所有主机端口绑定三档 QoS（256K/1M/2M）

# 必须等 OVS 起来
until systemctl is-active --quiet openvswitch-switch; do
  echo "⏳ 等待 OVS 启动..."
  sleep 2
done

# 严格映射：hX-eth0 ↔ s1-ethY
declare -A HOST_PORT_MAP=(
  [h1]="s1-eth1"
  [h2]="s1-eth3"
  [h3]="s1-eth4"
  [h4]="s1-eth5"
  [h5]="s1-eth6"
  [h6]="s1-eth7"
  [h7]="s1-eth8"
  [h8]="s1-eth2"
)

# 三档速率（bit/s）
Q1_RATE=262144      # 256 K
Q2_RATE=1048576     # 1 M
Q3_RATE=2097152     # 2 M
TOTAL_RATE=100000000 # 100 M 保底

for host in "${!HOST_PORT_MAP[@]}"; do
  port=${HOST_PORT_MAP[$host]}
  echo "🔗 绑定 $host → $port"

  # 先清旧 QoS
  ovs-vsctl clear port "$port" qos 2>/dev/null

  # 创建新 QoS + 三队列
  ovs-vsctl set port "$port" qos=@newqos -- \
    --id=@newqos create qos type=linux-htb other-config:max-rate=$TOTAL_RATE \
    queues:1=@q1 queues:2=@q2 queues:3=@q3 -- \
    --id=@q1 create queue other-config:max-rate=$Q1_RATE -- \
    --id=@q2 create queue other-config:max-rate=$Q2_RATE -- \
    --id=@q3 create queue other-config:max-rate=$Q3_RATE

  qos_id=$(ovs-vsctl get port "$port" qos 2>/dev/null | tr -d '"[]')
  [ -n "$qos_id" ] && echo "✅ $host → $port 成功" || echo "❌ $host → $port 失败"
done

echo "=== 最终验证 ==="
for host in "${!HOST_PORT_MAP[@]}"; do
  port=${HOST_PORT_MAP[$host]}
  qos=$(ovs-vsctl get port "$port" qos 2>/dev/null | tr -d '"[]')
  echo "$host → $port : QoS=$qos"
done
