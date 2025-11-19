#!/usr/bin/env python

"""SDN网络管理路由模块

此模块提供与SDN控制器交互的API端点，包括获取网络拓扑、流表信息、交换机统计数据等功能。
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional, List, Dict, Any
from datetime import datetime

from database import get_db
from models import User
from auth import get_current_user
from sdn_manager import SDNManager

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
        # 验证用户权限（管理员才能添加流表）
        if current_user.role != "admin":
            raise HTTPException(status_code=403, detail="您没有权限执行此操作")
        
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
    uvicorn.run(app, host="0.0.0.0", port=8002)