#!/usr/bin/env python3
"""
端口抖动测试脚本
模拟端口在60秒内频繁up/down超过5次
"""
import time
import subprocess
import sys

def toggle_port(port_num=1, times=6, interval=8):
    """
    模拟端口抖动：关闭再启动端口
    
    Args:
        port_num: 端口号（1-8对应h1-h8）
        times: 抖动次数（必须>5才能触发检测）
        interval: 每次间隔秒数（必须<60秒）
    """
    print(f"🔄 开始模拟端口 {port_num} 抖动测试...")
    print(f"   - 抖动次数: {times}")
    print(f"   - 每次间隔: {interval}秒")
    print(f"   - 总耗时: {times * interval}秒")
    print(f"   - 窗口要求: 必须在60秒内完成{times}次抖动\n")
    
    if times * interval > 55:
        print("⚠️  警告：总耗时接近60秒，可能无法触发检测！")
        print("   建议: times * interval < 50秒\n")
    
    for i in range(times):
        print(f"[{i+1}/{times}] 关闭端口 {port_num}...")
        # 禁用端口
        result = subprocess.run(
            f"sudo ovs-ofctl mod-port s1 {port_num} down",
            shell=True,
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0:
            print(f"❌ 错误：{result.stderr}")
            print("   提示：请确保Mininet正在运行且交换机为s1")
            sys.exit(1)
        
        time.sleep(interval / 2)
        
        print(f"[{i+1}/{times}] 启动端口 {port_num}...")
        # 启用端口
        subprocess.run(
            f"sudo ovs-ofctl mod-port s1 {port_num} up",
            shell=True
        )
        time.sleep(interval / 2)
        
        print(f"   ✅ 第{i+1}次抖动完成（剩余{times-i-1}次）\n")
    
    print("=" * 50)
    print("🎉 测试完成！")
    print("=" * 50)
    print("\n📋 接下来请检查：")
    print("   1. RYU日志输出:")
    print("      grep 'device_anomaly' ryu.log")
    print("\n   2. 前端页面:")
    print("      http://localhost:5176 → 流表管理 → 设备异常监控")
    print("\n   3. 数据库记录:")
    print("      mysql> SELECT * FROM device_anomalies WHERE anomaly_type='端口频繁抖动';")

if __name__ == "__main__":
    # 默认测试端口1（h1），抖动6次，每次间隔8秒（总共48秒）
    print("\n" + "=" * 50)
    print("  端口频繁抖动测试脚本")
    print("=" * 50 + "\n")
    
    # 检查是否以root运行
    import os
    if os.geteuid() != 0:
        print("❌ 错误：此脚本需要root权限")
        print("   请使用: sudo python port_flapping.py")
        sys.exit(1)
    
    # 参数说明
    if len(sys.argv) > 1 and sys.argv[1] in ['-h', '--help']:
        print("使用方法:")
        print("  sudo python port_flapping.py [端口号] [次数] [间隔]")
        print("\n参数:")
        print("  端口号: 1-8 (对应h1-h8，默认1)")
        print("  次数:   抖动次数 (默认6，必须>5)")
        print("  间隔:   每次间隔秒数 (默认8)")
        print("\n示例:")
        print("  sudo python port_flapping.py 1 6 8")
        print("  sudo python port_flapping.py 2 7 6")
        sys.exit(0)
    
    # 解析参数
    port_num = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    times = int(sys.argv[2]) if len(sys.argv) > 2 else 6
    interval = int(sys.argv[3]) if len(sys.argv) > 3 else 8
    
    # 参数验证
    if port_num < 1 or port_num > 8:
        print("❌ 错误：端口号必须在1-8之间")
        sys.exit(1)
    
    if times <= 5:
        print("❌ 错误：抖动次数必须>5才能触发检测")
        sys.exit(1)
    
    # 开始测试
    toggle_port(port_num, times, interval)
