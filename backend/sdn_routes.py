#!/usr/bin/env python

"""SDN网络管理路由模块

此模块提供与SDN控制器交互的API端点，包括获取网络拓扑、流表信息、交换机统计数据等功能。"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel
from typing import Dict, Any
import requests
import json
import re
from datetime import datetime

from database import get_db
from models import User
from auth import get_current_user
from sdn_manager import SDNManager

# 请求模型
class SDNChatRequest(BaseModel):
    user: str

# 创建SDN路由路由器
sdn_router = APIRouter(prefix="/api/sdn", tags=["SDN网络管理"])

# 创建SDN管理器实例
sdn_manager = SDNManager()


@sdn_router.get("/controller/status")
async def get_controller_status(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取SDN控制器状态
    
    Returns:
        Dict: 控制器状态信息
    """
    try:
        status = sdn_manager.is_controller_alive()
        return {
            "success": True,
            "status": "online" if status else "offline",
            "message": "控制器在线" if status else "控制器离线"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取控制器状态失败: {str(e)}")


@sdn_router.get("/topology")
async def get_network_topology(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取SDN网络拓扑信息
    
    Returns:
        Dict: 网络拓扑信息
    """
    try:
        topology = sdn_manager.get_network_topology()
        if topology is None:
            raise HTTPException(status_code=500, detail="获取网络拓扑信息失败")
        
        return {
            "success": True,
            "topology": topology
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取网络拓扑信息失败: {str(e)}")


@sdn_router.get("/switches")
async def get_switches(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取所有SDN交换机列表
    
    Returns:
        List: 交换机DPID列表
    """
    try:
        switches = sdn_manager.get_switch_stats()
        if switches is None:
            raise HTTPException(status_code=500, detail="获取交换机列表失败")
        
        return {
            "success": True,
            "switches": switches,
            "count": len(switches)
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取交换机列表失败: {str(e)}")


@sdn_router.post("/chat")
async def sdn_chat(
    request: SDNChatRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """SDN智能聊天接口
    
    处理用户命令并与RYU控制器交互
    支持的命令格式：
    - 加黑 IP地址
    - 解除 IP地址  
    - 查询 IP地址
    - 拓扑
    
    Args:
        request: 包含用户命令的请求
        current_user: 当前用户
        db: 数据库会话
        
    Returns:
        Dict: 处理结果
    """
    try:
        user_command = request.user.strip()
        
        # 解析命令
        command_result = parse_sdn_command(user_command)
        
        if command_result["error"]:
            return {
                "success": False,
                "response": command_result["error"],
                "command_type": "error"
            }
        
        command_type = command_result["type"]
        ip_address = command_result.get("ip")
        
        # 根据命令类型执行相应操作
        if command_type == "block":
            result = await block_ip_address(ip_address)
        elif command_type == "unblock":
            result = await unblock_ip_address(ip_address)
        elif command_type == "query":
            result = await query_ip_status(ip_address)
        elif command_type == "topology":
            result = await get_topology_info()
        else:
            result = {
                "success": False,
                "response": "不支持的命令类型"
            }
        
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"处理SDN命令失败: {str(e)}")


def parse_sdn_command(command: str) -> Dict[str, Any]:
    """解析SDN命令
    
    Args:
        command: 用户输入的命令
        
    Returns:
        Dict: 解析结果
    """
    command = command.strip()
    
    # IP地址正则表达式
    ip_pattern = r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b'
    
    # 加黑命令
    if command.startswith('加黑'):
        ip_match = re.search(ip_pattern, command)
        if ip_match:
            return {
                "type": "block",
                "ip": ip_match.group(),
                "error": None
            }
        else:
            return {
                "type": None,
                "error": "请提供有效的IP地址，格式：加黑 192.168.1.100"
            }
    
    # 解除命令
    elif command.startswith('解除'):
        ip_match = re.search(ip_pattern, command)
        if ip_match:
            return {
                "type": "unblock",
                "ip": ip_match.group(),
                "error": None
            }
        else:
            return {
                "type": None,
                "error": "请提供有效的IP地址，格式：解除 192.168.1.100"
            }
    
    # 查询命令
    elif command.startswith('查询'):
        ip_match = re.search(ip_pattern, command)
        if ip_match:
            return {
                "type": "query",
                "ip": ip_match.group(),
                "error": None
            }
        else:
            return {
                "type": None,
                "error": "请提供有效的IP地址，格式：查询 192.168.1.100"
            }
    
    # 拓扑命令
    elif command == '拓扑' or command.lower() == 'topology':
        return {
            "type": "topology",
            "error": None
        }
    
    else:
        return {
            "type": None,
            "error": "不支持的命令格式。支持的命令：\n- 加黑 IP地址\n- 解除 IP地址\n- 查询 IP地址\n- 拓扑"
        }


async def block_ip_address(ip: str) -> Dict[str, Any]:
    """封锁IP地址"""
    try:
        # 调用RYU控制器API
        ryu_url = "http://192.168.44.129:8080/v1/chat"
        payload = {
            "user_id": f"user-{int(datetime.now().timestamp())}",
            "user": f"ai: 加黑 {ip}"
        }
        
        response = requests.post(ryu_url, json=payload, timeout=10)
        
        if response.status_code == 200:
            return {
                "success": True,
                "response": f"已成功封锁IP地址 {ip}，该IP的所有流量将被阻止。",
                "command_type": "block",
                "ip": ip
            }
        else:
            return {
                "success": False,
                "response": f"封锁IP地址 {ip} 失败，控制器响应错误（状态码：{response.status_code}）",
                "command_type": "block",
                "ip": ip
            }
            
    except requests.exceptions.Timeout:
        return {
            "success": False,
            "response": f"封锁IP地址 {ip} 超时，请检查RYU控制器是否正常运行",
            "command_type": "block",
            "ip": ip
        }
    except Exception as e:
        return {
            "success": False,
            "response": f"封锁IP地址 {ip} 失败：{str(e)}",
            "command_type": "block",
            "ip": ip
        }


async def unblock_ip_address(ip: str) -> Dict[str, Any]:
    """解除IP地址封锁"""
    try:
        # 调用RYU控制器API
        ryu_url = "http://192.168.44.129:8080/v1/chat"
        payload = {
            "user_id": f"user-{int(datetime.now().timestamp())}",
            "user": f"ai: 解除 {ip}"
        }
        
        response = requests.post(ryu_url, json=payload, timeout=10)
        
        if response.status_code == 200:
            return {
                "success": True,
                "response": f"已成功解除IP地址 {ip} 的封锁，该IP现在可以正常通信。",
                "command_type": "unblock",
                "ip": ip
            }
        else:
            return {
                "success": False,
                "response": f"解除IP地址 {ip} 封锁失败，控制器响应错误（状态码：{response.status_code}）",
                "command_type": "unblock",
                "ip": ip
            }
            
    except requests.exceptions.Timeout:
        return {
            "success": False,
            "response": f"解除IP地址 {ip} 封锁超时，请检查RYU控制器是否正常运行",
            "command_type": "unblock",
            "ip": ip
        }
    except Exception as e:
        return {
            "success": False,
            "response": f"解除IP地址 {ip} 封锁失败：{str(e)}",
            "command_type": "unblock",
            "ip": ip
        }


async def query_ip_status(ip: str) -> Dict[str, Any]:
    """查询IP地址状态"""
    try:
        # 调用RYU控制器API
        ryu_url = "http://192.168.44.129:8080/v1/chat"
        payload = {
            "user_id": f"user-{int(datetime.now().timestamp())}",
            "user": f"ai: 查询 {ip}"
        }
        
        response = requests.post(ryu_url, json=payload, timeout=10)
        
        if response.status_code == 200:
            return {
                "success": True,
                "response": f"IP地址 {ip} 的当前状态查询完成。请查看控制器日志获取详细信息。",
                "command_type": "query",
                "ip": ip
            }
        else:
            return {
                "success": False,
                "response": f"查询IP地址 {ip} 状态失败，控制器响应错误（状态码：{response.status_code}）",
                "command_type": "query",
                "ip": ip
            }
            
    except requests.exceptions.Timeout:
        return {
            "success": False,
            "response": f"查询IP地址 {ip} 状态超时，请检查RYU控制器是否正常运行",
            "command_type": "query",
            "ip": ip
        }
    except Exception as e:
        return {
            "success": False,
            "response": f"查询IP地址 {ip} 状态失败：{str(e)}",
            "command_type": "query",
            "ip": ip
        }


async def get_topology_info() -> Dict[str, Any]:
    """获取网络拓扑信息"""
    try:
        # 使用现有的SDN管理器获取拓扑信息
        topology = sdn_manager.get_network_topology()
        
        if topology:
            switches_count = len(topology.get('switches', []))
            hosts_count = len(topology.get('hosts', []))
            links_count = len(topology.get('links', []))
            
            response_text = f"""当前网络拓扑信息：
📊 交换机数量：{switches_count}
🖥️ 主机数量：{hosts_count}
🔗 链路数量：{links_count}

交换机列表：
"""
            
            for switch in topology.get('switches', []):
                response_text += f"- 交换机 {switch.get('dpid', 'Unknown')}\n"
            
            if topology.get('hosts'):
                response_text += "\n主机列表：\n"
                for host in topology.get('hosts', []):
                    response_text += f"- 主机 {host.get('mac', 'Unknown')} (IP: {host.get('ipv4', ['Unknown'])[0] if host.get('ipv4') else 'Unknown'})\n"
            
            return {
                "success": True,
                "response": response_text,
                "command_type": "topology",
                "topology_data": topology
            }
        else:
            return {
                "success": False,
                "response": "无法获取网络拓扑信息，请检查控制器连接状态",
                "command_type": "topology"
            }
            
    except Exception as e:
        return {
            "success": False,
            "response": f"获取网络拓扑信息失败：{str(e)}",
            "command_type": "topology"
        }


@sdn_router.get("/switches/{dpid}/flows")
async def get_switch_flows(
    dpid: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取指定交换机的流表信息
    
    Args:
        dpid: 交换机的DPID
    
    Returns:
        Dict: 流表信息
    """
    try:
        flows = sdn_manager.get_switch_flows(dpid)
        if flows is None:
            raise HTTPException(status_code=500, detail=f"获取交换机{dpid}的流表信息失败")
        
        return {
            "success": True,
            "dpid": dpid,
            "flows": flows.get(dpid, []),
            "flow_count": len(flows.get(dpid, []))
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取交换机流表信息失败: {str(e)}")


@sdn_router.get("/flows")
async def get_all_flows(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取所有交换机的流表信息
    
    Returns:
        Dict: 所有交换机的流表信息
    """
    try:
        all_flows = sdn_manager.get_all_flows()
        if all_flows is None:
            raise HTTPException(status_code=500, detail="获取所有交换机的流表信息失败")
        
        # 统计总流表数
        total_flows = 0
        for dpid, flows in all_flows.items():
            total_flows += len(flows)
        
        return {
            "success": True,
            "flows": all_flows,
            "switch_count": len(all_flows),
            "total_flow_count": total_flows
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取所有流表信息失败: {str(e)}")


@sdn_router.post("/switches/{dpid}/flows")
async def add_switch_flow(
    dpid: str,
    flow_entry: Dict[str, Any],
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """向交换机添加流表项
    
    Args:
        dpid: 交换机的DPID
        flow_entry: 流表项配置
    
    Returns:
        Dict: 操作结果
    """
    try:
        # 调试：打印用户信息
        print(f"[DEBUG] 添加流表请求")
        print(f"[DEBUG] 用户名: {current_user.username}")
        print(f"[DEBUG] 用户ID: {current_user.id}")
        print(f"[DEBUG] 角色原始值: {repr(current_user.role)}")
        print(f"[DEBUG] 角色字节: {current_user.role.encode() if current_user.role else None}")
        print(f"[DEBUG] 角色长度: {len(current_user.role) if current_user.role else 0}")
        
        # 清理role字段（去除空格和换行符）
        user_role = current_user.role.strip().lower() if current_user.role else ""
        print(f"[DEBUG] 清理后的角色: '{user_role}'")
        
        # 验证用户权限（管理员才能添加流表）
        if user_role != "admin":
            raise HTTPException(
                status_code=403, 
                detail=f"需要管理员权限才能添加流表（当前角色: {current_user.role}）"
            )
        
        success = sdn_manager.add_flow_entry(dpid, flow_entry)
        if not success:
            raise HTTPException(status_code=500, detail=f"向交换机{dpid}添加流表项失败")
        
        return {
            "success": True,
            "message": f"成功向交换机{dpid}添加流表项"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"添加流表项失败: {str(e)}")


@sdn_router.delete("/switches/{dpid}/flows")
async def delete_switch_flow(
    dpid: str,
    flow_entry: Dict[str, Any],
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """删除交换机的流表项
    
    Args:
        dpid: 交换机的DPID
        flow_entry: 要删除的流表项配置
    
    Returns:
        Dict: 操作结果
    """
    try:
        # 验证用户权限（管理员才能删除流表）
        if current_user.role != "admin":
            raise HTTPException(status_code=403, detail="您没有权限执行此操作")
        
        success = sdn_manager.delete_flow_entry(dpid, flow_entry)
        if not success:
            raise HTTPException(status_code=500, detail=f"删除交换机{dpid}的流表项失败")
        
        return {
            "success": True,
            "message": f"成功删除交换机{dpid}的流表项"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"删除流表项失败: {str(e)}")


@sdn_router.delete("/switches/{dpid}/flows/all")
async def delete_all_switch_flows(
    dpid: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """删除交换机的所有流表项
    
    Args:
        dpid: 交换机的DPID
    
    Returns:
        Dict: 操作结果
    """
    try:
        # 验证用户权限（管理员才能删除所有流表）
        if current_user.role != "admin":
            raise HTTPException(status_code=403, detail="您没有权限执行此操作")
        
        success = sdn_manager.delete_all_flows(dpid)
        if not success:
            raise HTTPException(status_code=500, detail=f"删除交换机{dpid}的所有流表项失败")
        
        return {
            "success": True,
            "message": f"成功删除交换机{dpid}的所有流表项"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"删除所有流表项失败: {str(e)}")


@sdn_router.get("/switches/{dpid}/ports")
async def get_switch_ports(
    dpid: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取交换机的端口信息
    
    Args:
        dpid: 交换机的DPID
    
    Returns:
        Dict: 端口信息
    """
    try:
        port_desc = sdn_manager.get_port_desc(dpid)
        if port_desc is None:
            raise HTTPException(status_code=500, detail=f"获取交换机{dpid}的端口描述信息失败")
        
        port_stats = sdn_manager.get_port_stats(dpid)
        
        return {
            "success": True,
            "dpid": dpid,
            "port_desc": port_desc.get(dpid, []),
            "port_stats": port_stats.get(dpid, {}) if port_stats else {},
            "port_count": len(port_desc.get(dpid, []))
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取端口信息失败: {str(e)}")


@sdn_router.get("/network-summary")
async def get_network_summary(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取SDN网络摘要信息
    
    Returns:
        Dict: 网络摘要信息
    """
    try:
        summary = sdn_manager.get_network_summary()
        
        return {
            "success": True,
            "summary": summary,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取网络摘要信息失败: {str(e)}")

@sdn_router.get("/dashboard-data")
async def get_dashboard_data(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取Dashboard所需的所有实时数据
    
    Returns:
        Dict: Dashboard所需的所有数据
    """
    try:
        # 获取网络摘要信息
        summary = sdn_manager.get_network_summary()
        
        # 获取交换机信息
        switches = sdn_manager.get_switch_stats() or []
        
        # 获取所有流表信息
        all_flows = sdn_manager.get_all_flows() or {}
        
        # 统计总流表数
        total_flows = 0
        for dpid, flows in all_flows.items():
            total_flows += len(flows)
        
        # 获取限速主机列表
        limited_hosts = []
        if hasattr(sdn_manager, 'get_limit_list'):
            try:
                # 尝试从SDN控制器获取限速列表
                limited_hosts = sdn_manager.get_limit_list()
            except:
                # 如果失败，尝试从RYU控制器实例获取
                try:
                    from SDN.sdn_smart import SDNSecurityController
                    controller_instances = [app for app in ry_app_mgr.SERVICE_BRICKS.values() 
                                          if isinstance(app, SDNSecurityController)]
                    if controller_instances:
                        limited_hosts = controller_instances[0].get_limit_list()
                except Exception as e:
                    logger.error(f"获取限速主机列表失败: {e}")
        
        # 获取ACL列表
        acl_lists = {}
        if hasattr(sdn_manager, 'get_acl_lists'):
            try:
                acl_lists = sdn_manager.get_acl_lists()
            except:
                # 如果失败，尝试从RYU控制器实例获取
                try:
                    from SDN.sdn_smart import SDNSecurityController
                    controller_instances = [app for app in ry_app_mgr.SERVICE_BRICKS.values() 
                                          if isinstance(app, SDNSecurityController)]
                    if controller_instances:
                        acl_lists = controller_instances[0].get_acl_lists()
                except Exception as e:
                    logger.error(f"获取ACL列表失败: {e}")
        
        # 获取最近的异常事件
        recent_anomalies = []
        try:
            # 从数据库获取最近的异常事件
            conn = db
            with conn.cursor() as cursor:
                sql = """
                SELECT id, src_ip, dst_ip, anomaly_type, confidence, details, 
                       detected_at, status, action_taken
                FROM anomaly_events
                ORDER BY detected_at DESC
                LIMIT 10
                """
                cursor.execute(sql)
                columns = [col[0] for col in cursor.description]
                recent_anomalies = [dict(zip(columns, row)) for row in cursor.fetchall()]
                
                # 格式化时间戳
                for anomaly in recent_anomalies:
                    if isinstance(anomaly['detected_at'], datetime):
                        anomaly['timestamp'] = int(anomaly['detected_at'].timestamp())
                    else:
                        anomaly['timestamp'] = int(time.time())
        except Exception as e:
            logger.error(f"获取最近异常事件失败: {e}")
            # 如果数据库查询失败，尝试从RYU控制器获取
            try:
                from SDN.sdn_smart import SDNSecurityController, ANOMALY_QUEUE
                if ANOMALY_QUEUE:
                    # 转换队列数据为列表
                    recent_anomalies = list(ANOMALY_QUEUE)[-10:]
                    for i, anomaly in enumerate(recent_anomalies):
                        anomaly['id'] = i
                        if 'timestamp' not in anomaly:
                            anomaly['timestamp'] = int(time.time())
            except Exception as e:
                logger.error(f"从RYU控制器获取异常事件失败: {e}")
        
        # 获取流量统计数据
        flow_stats = []
        try:
            # 尝试从v1_routes中获取流量统计数据
            from v1_routes import generate_real_flowstats
            flow_stats = generate_real_flowstats()
        except Exception as e:
            logger.error(f"获取流量统计数据失败: {e}")
            # 返回空数据而不是模拟数据
            flow_stats = []
        
        # 计算协议分布
        protocol_distribution = {}
        for stat in flow_stats:
            protocol = stat.get("protocol", "OTHER")
            if protocol not in protocol_distribution:
                protocol_distribution[protocol] = 0
            protocol_distribution[protocol] += stat.get("packet_count", 0)
        
        # 计算活跃主机数
        active_hosts = set()
        for stat in flow_stats:
            if "src_ip" in stat:
                active_hosts.add(stat["src_ip"])
            if "dst_ip" in stat:
                active_hosts.add(stat["dst_ip"])
        
        # 构建返回数据
        dashboard_data = {
            "success": True,
            "timestamp": datetime.now().isoformat(),
            "summary": {
                "switch_count": len(switches),
                "active_hosts": len(active_hosts),
                "anomaly_count": len(recent_anomalies),
                "limited_hosts": len(limited_hosts),
                "total_flows": total_flows,
                "controller_status": summary.get("controller_status", "unknown")
            },
            "traffic_stats": {
                "flow_stats": flow_stats[-144:],  # 最近24小时的数据(每10分钟一个点)
                "protocol_distribution": protocol_distribution
            },
            "anomalies": recent_anomalies,
            "acl": {
                "whitelist": acl_lists.get("white_list", []),
                "blacklist": acl_lists.get("black_list", [])
            },
            "limited_hosts": limited_hosts
        }
        
        return dashboard_data
    except Exception as e:
        logger.error(f"获取Dashboard数据失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取Dashboard数据失败: {str(e)}")


@sdn_router.get("/dashboard-data")
async def get_dashboard_data():
    """获取仪表盘数据
    
    Returns:
        Dict: 仪表盘数据，包括交换机数量、主机数量、异常数量、限速主机数量等
    """
    try:
        # 检查控制器状态
        controller_status = sdn_manager.is_controller_alive()
        if not controller_status:
            raise HTTPException(status_code=500, detail="RYU控制器离线")
        
        # 获取交换机信息
        switches = sdn_manager.get_switch_stats() or []
        
        # 获取主机信息
        hosts = sdn_manager.get_hosts() or []
        
        # 获取异常信息
        anomalies = sdn_manager.get_anomalies() or []
        
        # 获取限速主机信息
        limited_hosts = sdn_manager.get_limit_list() or []
        
        # 获取流量数据
        traffic_data = sdn_manager.get_traffic_stats() or {}
        
        # 获取协议分布
        protocol_data = sdn_manager.get_protocol_distribution() or {}
        
        # 获取访问控制列表
        acl_data = {
            "whitelist": sdn_manager.get_whitelist() or [],
            "blacklist": sdn_manager.get_blacklist() or []
        }
        
        return {
            "summary": {
                "switch_count": len(switches),
                "host_count": len(hosts),
                "anomaly_count": len(anomalies),
                "limited_count": len(limited_hosts)
            },
            "traffic": traffic_data,
            "protocols": protocol_data,
            "anomalies": anomalies[:5],  # 只返回最近5条异常
            "acl": acl_data
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取仪表盘数据失败: {str(e)}")


@sdn_router.get("/monitoring/start")
async def start_network_monitoring(
    interval: int = Query(default=5, ge=1, le=60, description="监控间隔（秒）"),
    duration: int = Query(default=30, ge=5, le=300, description="监控持续时间（秒）"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """启动网络监控
    
    Args:
        interval: 监控间隔（秒）
        duration: 监控持续时间（秒）
    
    Returns:
        Dict: 监控数据
    """
    try:
        # 验证用户权限（管理员或操作员才能监控网络）
        if current_user.role not in ["admin", "operator"]:
            raise HTTPException(status_code=403, detail="您没有权限执行此操作")
        
        print(f"开始网络监控: 间隔={interval}秒, 持续时间={duration}秒")
        monitor_data = sdn_manager.monitor_network(interval=interval, duration=duration)
        
        return {
            "success": True,
            "monitoring_data": monitor_data,
            "interval": interval,
            "duration": duration,
            "data_points": len(monitor_data)
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"网络监控失败: {str(e)}")


@sdn_router.post("/switches/{dpid}/simple-flow")
async def create_simple_flow(
    dpid: str,
    in_port: int,
    eth_dst: str,
    out_port: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """创建一个简单的转发流表项（便于快速配置）
    
    Args:
        dpid: 交换机的DPID
        in_port: 入端口
        eth_dst: 目标MAC地址
        out_port: 出端口
    
    Returns:
        Dict: 操作结果
    """
    try:
        # 验证用户权限
        if current_user.role != "admin":
            raise HTTPException(status_code=403, detail="您没有权限执行此操作")
        
        success = sdn_manager.create_simple_flow(dpid, in_port, eth_dst, out_port)
        if not success:
            raise HTTPException(status_code=500, detail=f"创建简单流表项失败")
        
        return {
            "success": True,
            "message": f"成功创建简单流表项: 从端口{in_port}到端口{out_port}的MAC地址{eth_dst}转发规则"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"创建简单流表项失败: {str(e)}")


# 如果作为独立模块运行（用于测试）
if __name__ == "__main__":
    import uvicorn
    from fastapi import FastAPI
    
    app = FastAPI(title="SDN管理API测试")
    app.include_router(sdn_router)
    
    # 添加CORS中间件
    from fastapi.middleware.cors import CORSMiddleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # 启动测试服务器
    uvicorn.run(app, host="0.0.0.0", port=8001)