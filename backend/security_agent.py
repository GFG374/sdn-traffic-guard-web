"""
Security Agent - 网络安全智能代理
集成RAG知识库检索和MCP工具调用，实现自主决策
"""

import json
import requests
import os
import pymysql
from typing import Dict, List, Any, Optional
from datetime import datetime
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

try:
    from .rag_service import rag_service
    RAG_SERVICE = rag_service
except ImportError:
    try:
        from rag_service import rag_service
        RAG_SERVICE = rag_service
    except ImportError:
        # 降级方案：使用本地RAG
        try:
            from .rag_system import get_rag_instance
            RAG_SERVICE = None
        except ImportError:
            from rag_system import get_rag_instance
            RAG_SERVICE = None

# 数据库配置
DB_CONFIG = {
    'host': '192.168.44.1',
    'user': 'root',
    'password': 'yyr0218...',
    'db': 'network_management',
    'charset': 'utf8mb4'
}


class SecurityAgent:
    """网络安全智能代理"""
    
    def __init__(self, 
                 kimi_api_key: str = None,
                 model: str = "kimi-k2-turbo-preview"):
        """
        初始化Security Agent
        
        Args:
            kimi_api_key: Kimi API密钥
            model: 使用的模型名称（kimi-k2-turbo-preview）
        """
        self.kimi_api_key = kimi_api_key or os.getenv("KIMI_API_KEY", "")
        self.kimi_api_url = "https://api.moonshot.cn/v1/chat/completions"
        self.model = model  # 使用Kimi k2模型
        
        # 混合方案：优先使用阿里云Embedding + Kimi LLM
        if RAG_SERVICE is not None:
            self.rag = RAG_SERVICE
            self.use_dashscope_embedding = True
            print("✅ 使用阿里云DashScope Embedding（RAG检索）")
            # 初始化知识库
            self._initialize_knowledge_base()
        else:
            self.rag = get_rag_instance()
            self.use_dashscope_embedding = False
            print("✅ 使用本地RAG系统（Embedding）")
            # 构建本地知识库
            self._build_local_knowledge_base()
        
        # LLM使用Kimi API
        print("✅ 使用Kimi k2 LLM（模型分析）")
        
        # MCP工具注册表
        self.tools = {
            # 查询工具（从数据库获取实时数据）
            "search_knowledge": self._tool_search_knowledge,
            "query_acl_status": self._tool_query_acl_status,
            "query_acl_blacklist": self._tool_query_acl_blacklist,
            "query_acl_whitelist": self._tool_query_acl_whitelist,
            "query_rate_limit_history": self._tool_query_rate_limit_history,
            "query_attack_history": self._tool_query_attack_history,
            "query_flow_stats": self._tool_query_flow_stats,
            "get_defense_rules": self._tool_get_defense_rules,
            "query_network_topology": self._tool_query_network_topology,
            "get_current_status": self._tool_get_current_status,
            "query_device_anomalies": self._tool_query_device_anomalies,
            
            # 执行工具（修改数据库和防御规则）
            "apply_rate_limit": self._tool_apply_rate_limit,
            "add_to_blacklist": self._tool_add_to_blacklist,
            "add_to_whitelist": self._tool_add_to_whitelist,
            "remove_from_blacklist": self._tool_remove_from_blacklist,
            "remove_from_whitelist": self._tool_remove_from_whitelist,
            "release_rate_limit": self._tool_release_rate_limit,
            "modify_rate_limit_duration": self._tool_modify_rate_limit_duration,
            "modify_rate_limit_kbps": self._tool_modify_rate_limit_kbps,
            
            # 兼容旧版本
            "check_ip_history": self._tool_check_ip_history,
            "get_network_status": self._tool_get_network_status,
        }
        
        print("✅ Security Agent初始化成功（混合方案：阿里云Embedding + 本地Ollama LLM）")
    
    def _initialize_knowledge_base(self):
        """初始化阿里云RAG知识库"""
        try:
            import asyncio
            import os
            from pathlib import Path
            
            # 知识库文档路径（相对于项目根目录）
            current_dir = Path(__file__).parent
            docs_dir = current_dir.parent / "docs" / "knowledge_base"
            
            print(f"🔍 查找知识库目录: {docs_dir}")
            if not docs_dir.exists():
                print(f"⚠️ 知识库目录不存在: {docs_dir}")
                return
            
            # 读取所有文档文件（包括TXT、PDF等）
            all_files = list(docs_dir.glob("*"))
            doc_files = [f for f in all_files if f.is_file() and f.suffix in ['.txt', '.pdf', '.csv', '.docx']]
            
            if not doc_files:
                print(f"⚠️ 知识库目录中没有文档文件: {docs_dir}")
                return
            
            print(f"📚 开始加载知识库文档，共{len(doc_files)}个文件...")
            
            # 异步加载文档
            async def load_documents():
                for doc_file in doc_files:
                    try:
                        content = None
                        
                        # 根据文件类型提取内容
                        if doc_file.suffix == '.txt':
                            with open(doc_file, 'r', encoding='utf-8') as f:
                                content = f.read()
                        elif doc_file.suffix == '.pdf':
                            # 提取PDF内容
                            try:
                                import PyPDF2
                                with open(doc_file, 'rb') as f:
                                    pdf_reader = PyPDF2.PdfReader(f)
                                    content = ""
                                    for page in pdf_reader.pages:
                                        content += page.extract_text()
                            except Exception as e:
                                print(f"⚠️ PDF提取失败 {doc_file.name}: {e}")
                                continue
                        elif doc_file.suffix == '.csv':
                            with open(doc_file, 'r', encoding='utf-8') as f:
                                content = f.read()
                        elif doc_file.suffix == '.docx':
                            # 提取DOCX内容
                            try:
                                from docx import Document
                                doc = Document(doc_file)
                                content = "\n".join([para.text for para in doc.paragraphs])
                            except Exception as e:
                                print(f"⚠️ DOCX提取失败 {doc_file.name}: {e}")
                                continue
                        
                        if content and content.strip():
                            await self.rag.create_embeddings_from_file(content, doc_file.name)
                            print(f"✅ 已加载: {doc_file.name}")
                        else:
                            print(f"⚠️ 文件为空: {doc_file.name}")
                    except Exception as e:
                        print(f"❌ 加载文件失败 {doc_file.name}: {e}")
            
            # 运行异步任务
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    import concurrent.futures
                    with concurrent.futures.ThreadPoolExecutor() as executor:
                        future = executor.submit(asyncio.run, load_documents())
                        future.result(timeout=30)
                else:
                    loop.run_until_complete(load_documents())
            except RuntimeError:
                asyncio.run(load_documents())
            
            print("✅ 知识库初始化完成")
            
        except Exception as e:
            print(f"❌ 知识库初始化失败: {e}")
            import traceback
            traceback.print_exc()
    
    def _build_local_knowledge_base(self):
        """构建本地RAG知识库"""
        try:
            from pathlib import Path
            current_dir = Path(__file__).parent
            docs_dir = str(current_dir.parent / "docs" / "knowledge_base")
            
            print(f"🔍 构建本地知识库: {docs_dir}")
            if os.path.exists(docs_dir):
                count = self.rag.build_knowledge_base(docs_dir)
                print(f"✅ 本地知识库构建完成，共{count}个文档块")
            else:
                print(f"⚠️ 知识库目录不存在: {docs_dir}")
        except Exception as e:
            print(f"❌ 本地知识库构建失败: {e}")
    
    def _call_llm(self, prompt: str, temperature: float = 0.3) -> str:
        """调用LLM - 使用Kimi API"""
        return self._call_kimi_llm(prompt, temperature)
    
    def _call_kimi_llm(self, prompt: str, temperature: float = 0.6) -> str:
        """调用Kimi API (kimi-k2-turbo-preview)"""
        try:
            if not self.kimi_api_key:
                print("❌ 未配置KIMI_API_KEY")
                return "错误：未配置Kimi API密钥"
            
            headers = {
                "Authorization": f"Bearer {self.kimi_api_key}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "model": self.model,  # kimi-k2-turbo-preview
                "messages": [
                    {
                        "role": "system",
                        "content": "你是一个专业的网络管理AI助手，具备网络设备配置分析、网络安全诊断、性能优化建议、故障排查指导等能力。请用中文回答用户的问题，提供准确、专业的建议。"
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "temperature": temperature
            }
            
            response = requests.post(
                self.kimi_api_url,
                headers=headers,
                json=payload,
                timeout=30
            )
            response.raise_for_status()
            
            result = response.json()
            if result.get("choices") and len(result["choices"]) > 0:
                return result["choices"][0]["message"]["content"]
            else:
                print(f"⚠️ Kimi API响应异常: {result}")
                return "Kimi API返回异常响应"
                
        except Exception as e:
            print(f"❌ Kimi API调用失败: {e}")
            return f"Kimi API调用失败: {str(e)}"
    
    # ========== MCP工具 ==========
    
    def _tool_search_knowledge(self, query: str) -> Dict[str, Any]:
        """搜索知识库（MCP工具）"""
        try:
            if self.use_dashscope_embedding:
                # 使用阿里云Embedding进行RAG检索
                import asyncio
                try:
                    # 尝试获取当前事件循环
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        # 如果事件循环已在运行，使用run_coroutine_threadsafe
                        import concurrent.futures
                        with concurrent.futures.ThreadPoolExecutor() as executor:
                            future = executor.submit(
                                asyncio.run,
                                self.rag.search_similar_documents(query, k=3)
                            )
                            results = future.result(timeout=10)
                    else:
                        # 事件循环存在但未运行，直接运行
                        results = loop.run_until_complete(
                            self.rag.search_similar_documents(query, k=3)
                        )
                except RuntimeError:
                    # 没有事件循环，创建新的
                    results = asyncio.run(
                        self.rag.search_similar_documents(query, k=3)
                    )
                
                knowledge = [r.get("content", "") for r in results]
            else:
                # 使用本地RAG
                knowledge = self.rag.retrieve_knowledge(query, top_k=3)
            
            return {
                "tool": "search_knowledge",
                "success": True,
                "data": knowledge,
                "count": len(knowledge)
            }
        except Exception as e:
            print(f"⚠️ 知识库搜索失败: {e}")
            import traceback
            traceback.print_exc()
            return {
                "tool": "search_knowledge",
                "success": False,
                "error": str(e),
                "data": [],
                "count": 0
            }
    
    # ========== MCP工具1: 查询ACL状态 ==========
    def _tool_query_acl_status(self, ip: str) -> Dict[str, Any]:
        """查询IP的黑白名单状态"""
        try:
            conn = pymysql.connect(**DB_CONFIG)
            with conn.cursor() as cur:
                sql = "SELECT list_type, created_at FROM acl_entries WHERE ip=%s"
                cur.execute(sql, (ip,))
                result = cur.fetchone()
                
                if result:
                    return {
                        "tool": "query_acl_status",
                        "success": True,
                        "data": {
                            "ip": ip,
                            "status": result[0],  # 'white' or 'black'
                            "added_at": result[1].strftime('%Y-%m-%d %H:%M:%S') if result[1] else None
                        }
                    }
                else:
                    return {
                        "tool": "query_acl_status",
                        "success": True,
                        "data": {
                            "ip": ip,
                            "status": "normal",
                            "added_at": None
                        }
                    }
        except Exception as e:
            return {
                "tool": "query_acl_status",
                "success": False,
                "error": str(e),
                "data": {}
            }
        finally:
            if conn:
                conn.close()

    # ========== MCP工具1.5: 查询所有黑名单IP ==========
    def _tool_query_acl_blacklist(self) -> Dict[str, Any]:
        """查询所有黑名单IP（完整列表）"""
        try:
            conn = pymysql.connect(**DB_CONFIG)
            with conn.cursor() as cur:
                sql = "SELECT ip, created_at FROM acl_entries WHERE list_type='black' ORDER BY created_at DESC"
                cur.execute(sql)
                results = cur.fetchall()
                
                blacklist = []
                for row in results:
                    blacklist.append({
                        "ip": row[0],
                        "added_at": row[1].strftime('%Y-%m-%d %H:%M:%S') if row[1] else None
                    })
                
                return {
                    "tool": "query_acl_blacklist",
                    "success": True,
                    "data": {
                        "total": len(blacklist),
                        "blacklist": blacklist
                    }
                }
        except Exception as e:
            return {
                "tool": "query_acl_blacklist",
                "success": False,
                "error": str(e),
                "data": {"total": 0, "blacklist": []}
            }
        finally:
            if conn:
                conn.close()

    # ========== MCP工具1.6: 查询所有白名单IP ==========
    def _tool_query_acl_whitelist(self) -> Dict[str, Any]:
        """查询所有白名单IP（完整列表）"""
        try:
            conn = pymysql.connect(**DB_CONFIG)
            with conn.cursor() as cur:
                sql = "SELECT ip, created_at FROM acl_entries WHERE list_type='white' ORDER BY created_at DESC"
                cur.execute(sql)
                results = cur.fetchall()
                
                whitelist = []
                for row in results:
                    whitelist.append({
                        "ip": row[0],
                        "added_at": row[1].strftime('%Y-%m-%d %H:%M:%S') if row[1] else None
                    })
                
                return {
                    "tool": "query_acl_whitelist",
                    "success": True,
                    "data": {
                        "total": len(whitelist),
                        "whitelist": whitelist
                    }
                }
        except Exception as e:
            return {
                "tool": "query_acl_whitelist",
                "success": False,
                "error": str(e),
                "data": {"total": 0, "whitelist": []}
            }
        finally:
            if conn:
                conn.close()

    # ========== MCP工具2: 查询限速历史 ==========
    def _tool_query_rate_limit_history(self, ip: str = None, reason: str = None, days: int = 7) -> Dict[str, Any]:
        """
        查询限速历史
        可按IP查询，也可按限速原因查询，或两者结合
        【新增】days=-1表示不限制时间范围，查询所有历史记录
        """
        try:
            conn = pymysql.connect(**DB_CONFIG)
            with conn.cursor() as cur:
                # 【修复】支持按IP或按限速原因查询
                
                # 1. 查询当前限速（如果指定了IP）
                current_limits = []
                if ip and ip != "*":
                    sql = """SELECT src_ip, kbps, reason, expire_at, created_at 
                             FROM rate_limit_active 
                             WHERE src_ip=%s AND expire_at > NOW()"""
                    cur.execute(sql, (ip,))
                    current_limits = cur.fetchall()
                elif reason:
                    # 如果按原因查询，获取所有因为这个原因被限速的IP
                    sql = """SELECT src_ip, kbps, reason, expire_at, created_at 
                             FROM rate_limit_active 
                             WHERE reason LIKE %s AND expire_at > NOW()"""
                    cur.execute(sql, (f"%{reason}%",))
                    current_limits = cur.fetchall()
                else:
                    # 获取所有当前限速的IP
                    sql = """SELECT src_ip, kbps, reason, expire_at, created_at 
                             FROM rate_limit_active 
                             WHERE expire_at > NOW()"""
                    cur.execute(sql)
                    current_limits = cur.fetchall()
                
                # 2. 查询历史限速（limit_sessions表字段：id, src_ip, reason, start_time, kbps）
                # 【新增】如果days=-1，则不限制时间范围，查询所有历史记录
                if days == -1:
                    sql = """SELECT src_ip, reason, start_time, kbps 
                             FROM limit_sessions"""
                    params = []
                else:
                    sql = """SELECT src_ip, reason, start_time, kbps 
                             FROM limit_sessions 
                             WHERE start_time >= DATE_SUB(NOW(), INTERVAL %s DAY)"""
                    params = [days]
                
                # 如果指定了IP，添加IP过滤条件
                if ip and ip != "*":
                    sql += " AND src_ip=%s"
                    params.append(ip)
                
                # 如果指定了限速原因，添加原因过滤条件
                if reason:
                    sql += " AND reason LIKE %s"
                    params.append(f"%{reason}%")
                
                sql += " ORDER BY start_time DESC"
                
                cur.execute(sql, params)
                history = cur.fetchall()
                
                return {
                    "tool": "query_rate_limit_history",
                    "success": True,
                    "data": {
                        "ip": ip if ip and ip != "*" else "all",
                        "reason": reason if reason else "all",
                        "current_limits": {
                            "count": len(current_limits),
                            "limits": [
                                {
                                    "src_ip": c[0],
                                    "kbps": c[1],
                                    "reason": c[2],
                                    "expire_at": c[3].strftime('%Y-%m-%d %H:%M:%S') if hasattr(c[3], 'strftime') else str(c[3]),
                                    "created_at": c[4].strftime('%Y-%m-%d %H:%M:%S') if hasattr(c[4], 'strftime') else str(c[4])
                                } for c in current_limits
                            ]
                        },
                        "history": {
                            "count": len(history),
                            "records": [
                                {
                                    "src_ip": h[0],
                                    "reason": h[1],
                                    "start_time": h[2].strftime('%Y-%m-%d %H:%M:%S') if hasattr(h[2], 'strftime') else str(h[2]),
                                    "kbps": h[3]
                                } for h in history
                            ]
                        }
                    }
                }
        except Exception as e:
            return {
                "tool": "query_rate_limit_history",
                "success": False,
                "error": str(e),
                "data": {}
            }
        finally:
            if conn:
                conn.close()

    # ========== MCP工具3: 查询攻击历史 ==========
    def _tool_query_attack_history(self, ip: str = None, attack_type: str = None, days: int = 7) -> Dict[str, Any]:
        """
        查询攻击历史
        可按IP查询，也可按攻击类型查询，或两者结合
        【新增】days=-1表示不限制时间范围，查询所有历史记录
        """
        try:
            conn = pymysql.connect(**DB_CONFIG)
            with conn.cursor() as cur:
                # 【修复】支持按IP或按攻击类型查询
                # 【新增】如果days=-1，则不限制时间范围
                if days == -1:
                    sql = """SELECT src_ip, anomaly_type, packet_count, start_time, end_time, 
                                    status, handle_action
                             FROM attack_sessions"""
                    params = []
                else:
                    sql = """SELECT src_ip, anomaly_type, packet_count, start_time, end_time, 
                                    status, handle_action
                             FROM attack_sessions 
                             WHERE start_time >= DATE_SUB(NOW(), INTERVAL %s DAY)"""
                    params = [days]
                
                # 如果指定了IP，添加IP过滤条件
                if ip and ip != "*":
                    sql += " AND src_ip=%s"
                    params.append(ip)
                
                # 如果指定了攻击类型，添加攻击类型过滤条件
                if attack_type:
                    sql += " AND anomaly_type=%s"
                    params.append(attack_type)
                
                sql += " ORDER BY start_time DESC"
                
                cur.execute(sql, params)
                results = cur.fetchall()
                
                return {
                    "tool": "query_attack_history",
                    "success": True,
                    "data": {
                        "ip": ip if ip and ip != "*" else "all",
                        "attack_type": attack_type if attack_type else "all",
                        "total_attacks": len(results),
                        "attacks": [
                            {
                                "src_ip": r[0],
                                "type": r[1],
                                "packets": r[2],
                                "start_time": r[3].strftime('%Y-%m-%d %H:%M:%S') if hasattr(r[3], 'strftime') else str(r[3]),
                                "end_time": r[4].strftime('%Y-%m-%d %H:%M:%S') if r[4] and hasattr(r[4], 'strftime') else str(r[4]) if r[4] else None,
                                "status": r[5],
                                "action": r[6]
                            } for r in results
                        ]
                    }
                }
        except Exception as e:
            return {
                "tool": "query_attack_history",
                "success": False,
                "error": str(e),
                "data": {}
            }
        finally:
            if conn:
                conn.close()

    # ========== MCP工具4: 查询流量统计 ==========
    def _tool_query_flow_stats(self, ip: str, time_range_minutes: int = 60) -> Dict[str, Any]:
        """查询IP的流量统计"""
        try:
            conn = pymysql.connect(**DB_CONFIG)
            with conn.cursor() as cur:
                # 查询该IP的总数据包数
                sql = """SELECT SUM(packet_count) as total_packets
                         FROM flow_stats 
                         WHERE src_ip=%s"""
                cur.execute(sql, (ip,))
                result = cur.fetchone()
                total_packets = result[0] if result and result[0] else 0
                
                # 查询该IP的异常数据包数
                sql = """SELECT COUNT(*) as anomaly_count
                         FROM anomaly_log 
                         WHERE src_ip=%s"""
                cur.execute(sql, (ip,))
                result = cur.fetchone()
                anomaly_packets = result[0] if result and result[0] else 0
                
                return {
                    "tool": "query_flow_stats",
                    "success": True,
                    "data": {
                        "ip": ip,
                        "total_packets": total_packets,
                        "anomaly_packets": anomaly_packets,
                        "normal_packets": total_packets - anomaly_packets,
                        "anomaly_rate": round(anomaly_packets / total_packets * 100, 2) if total_packets > 0 else 0
                    }
                }
        except Exception as e:
            return {
                "tool": "query_flow_stats",
                "success": False,
                "error": str(e),
                "data": {}
            }
        finally:
            if conn:
                conn.close()

    # ========== MCP工具5: 查询设备异常 ==========
    def _tool_query_device_anomalies(self, device_type: str = None, anomaly_type: str = None, severity: str = None, days: int = 7) -> Dict[str, Any]:
        """
        查询设备异常
        可按设备类型、异常类型、严重程度查询，或多条件组合
        【新增】days=-1表示不限制时间范围，查询所有历史记录
        """
        try:
            conn = pymysql.connect(**DB_CONFIG)
            with conn.cursor() as cur:
                # 【新增】支持多条件查询设备异常
                # 【新增】如果days=-1，则不限制时间范围
                if days == -1:
                    sql = """SELECT id, anomaly_type, device_type, device_id, description, severity, 
                                    detected_at, resolved_at, status, handled_by, handled_at, handle_action
                             FROM device_anomalies"""
                    params = []
                else:
                    sql = """SELECT id, anomaly_type, device_type, device_id, description, severity, 
                                    detected_at, resolved_at, status, handled_by, handled_at, handle_action
                             FROM device_anomalies 
                             WHERE detected_at >= DATE_SUB(NOW(), INTERVAL %s DAY)"""
                    params = [days]
                
                # 如果指定了设备类型，添加过滤条件
                if device_type:
                    sql += " AND device_type=%s"
                    params.append(device_type)
                
                # 如果指定了异常类型，添加过滤条件
                if anomaly_type:
                    sql += " AND anomaly_type LIKE %s"
                    params.append(f"%{anomaly_type}%")
                
                # 如果指定了严重程度，添加过滤条件
                if severity:
                    sql += " AND severity=%s"
                    params.append(severity)
                
                sql += " ORDER BY detected_at DESC"
                
                cur.execute(sql, params)
                results = cur.fetchall()
                
                return {
                    "tool": "query_device_anomalies",
                    "success": True,
                    "data": {
                        "device_type": device_type if device_type else "all",
                        "anomaly_type": anomaly_type if anomaly_type else "all",
                        "severity": severity if severity else "all",
                        "total_anomalies": len(results),
                        "anomalies": [
                            {
                                "id": r[0],
                                "anomaly_type": r[1],
                                "device_type": r[2],
                                "device_id": r[3],
                                "description": r[4],
                                "severity": r[5],
                                "detected_at": r[6].strftime('%Y-%m-%d %H:%M:%S') if hasattr(r[6], 'strftime') else str(r[6]),
                                "resolved_at": r[7].strftime('%Y-%m-%d %H:%M:%S') if r[7] and hasattr(r[7], 'strftime') else str(r[7]) if r[7] else None,
                                "status": r[8],
                                "handled_by": r[9],
                                "handled_at": r[10].strftime('%Y-%m-%d %H:%M:%S') if r[10] and hasattr(r[10], 'strftime') else str(r[10]) if r[10] else None,
                                "handle_action": r[11]
                            } for r in results
                        ]
                    }
                }
        except Exception as e:
            return {
                "tool": "query_device_anomalies",
                "success": False,
                "error": str(e),
                "data": {}
            }
        finally:
            if conn:
                conn.close()

    # ========== MCP工具6: 获取防御规则 ==========
    def _tool_get_defense_rules(self, attack_type: Optional[str] = None) -> Dict[str, Any]:
        """获取防御规则"""
        try:
            # 首先尝试从RAG知识库获取防御规则
            if attack_type:
                query = f"{attack_type}攻击的检测阈值和防御措施"
            else:
                query = "网络安全防御规则和攻击检测阈值"
            
            knowledge_result = self._tool_search_knowledge(query)
            
            # 如果RAG检索成功，返回结果
            if knowledge_result['success'] and knowledge_result['data']:
                return {
                    "tool": "get_defense_rules",
                    "success": True,
                    "data": {
                        "attack_type": attack_type,
                        "rules": knowledge_result['data'],
                        "count": knowledge_result['count'],
                        "source": "rag"
                    }
                }
            
            # 如果RAG检索失败或为空，返回硬编码的防御规则（降级方案）
            default_rules = {
                "DDoS": {
                    "detection_threshold": "流量突增超过200pps",
                    "defense_measures": ["限速", "黑名单", "流量清洗"],
                    "priority": "高"
                },
                "SYN Flood": {
                    "detection_threshold": "SYN包占比>80%，速率>200pps",
                    "defense_measures": ["限速", "黑名单", "SYN代理"],
                    "priority": "高"
                },
                "UDP Flood": {
                    "detection_threshold": "UDP包数>200pps",
                    "defense_measures": ["限速", "黑名单", "UDP过滤"],
                    "priority": "高"
                },
                "ARP Spoofing": {
                    "detection_threshold": "MAC地址变化",
                    "defense_measures": ["ARP防护", "黑名单"],
                    "priority": "中"
                },
                "Port Scan": {
                    "detection_threshold": "单IP扫描端口数>10",
                    "defense_measures": ["限速", "黑名单"],
                    "priority": "中"
                }
            }
            
            if attack_type and attack_type in default_rules:
                rules = [default_rules[attack_type]]
            else:
                rules = list(default_rules.values())
            
            return {
                "tool": "get_defense_rules",
                "success": True,
                "data": {
                    "attack_type": attack_type,
                    "rules": rules,
                    "count": len(rules),
                    "source": "default"
                }
            }
            
        except Exception as e:
            print(f"⚠️ 获取防御规则失败: {e}")
            return {
                "tool": "get_defense_rules",
                "success": False,
                "error": str(e),
                "data": {}
            }

    # ========== MCP工具6: 查询网络拓扑 ==========
    def _tool_query_network_topology(self) -> Dict[str, Any]:
        """查询网络拓扑"""
        try:
            # 从RAG知识库获取拓扑信息
            query = "网络拓扑结构交换机主机配置IP地址h1 h2 h3 h4 h5 h6 h7 h8"
            knowledge_result = self._tool_search_knowledge(query)
            
            print(f"[DEBUG] RAG拓扑查询结果: {knowledge_result}")
            
            # 确保知识库数据被正确返回
            topology_info = knowledge_result.get('data', [])
            if not topology_info:
                print(f"⚠️ RAG知识库返回为空，使用默认值")
                topology_info = []
            
            # 硬编码的主机配置（从知识库文件中提取）
            host_config = """## 主机配置
所有主机均在 192.168.1.0/24 子网：
1. h1: IP=192.168.1.100/24, MAC=00:00:00:00:00:01
2. h2: IP=192.168.1.101/24, MAC=00:00:00:00:00:02
3. h3: IP=192.168.1.102/24, MAC=00:00:00:00:00:03
4. h4: IP=192.168.1.103/24, MAC=00:00:00:00:00:04
5. h5: IP=192.168.1.104/24, MAC=00:00:00:00:00:05
6. h6: IP=192.168.1.105/24, MAC=00:00:00:00:00:06
7. h7: IP=192.168.1.200/24, MAC=00:00:00:00:00:07
8. h8: IP=192.168.1.108/24, MAC=00:00:00:00:00:08"""
            
            # 合并RAG结果和硬编码配置
            combined_info = host_config
            if topology_info:
                combined_info += "\n\n【RAG知识库补充信息】\n" + "\n".join(topology_info)
            
            return {
                "tool": "query_network_topology",
                "success": True,
                "data": {
                    "topology_type": "star",
                    "switches": ["s1"],
                    "hosts": ["h1", "h2", "h3", "h4", "h5", "h6", "h7", "h8"],
                    "ip_subnet": "192.168.1.0/24",
                    "total_hosts": 8,
                    "qos_levels": [256, 1024, 2048],
                    "host_mapping": {
                        "h1": "192.168.1.100",
                        "h2": "192.168.1.101",
                        "h3": "192.168.1.102",
                        "h4": "192.168.1.103",
                        "h5": "192.168.1.104",
                        "h6": "192.168.1.105",
                        "h7": "192.168.1.200",
                        "h8": "192.168.1.108"
                    },
                    "topology_info": combined_info,
                    "knowledge_success": knowledge_result.get('success', False)
                }
            }
        except Exception as e:
            print(f"[ERROR] 拓扑查询失败: {e}")
            import traceback
            traceback.print_exc()
            return {
                "tool": "query_network_topology",
                "success": False,
                "error": str(e),
                "data": {}
            }

    # ========== MCP工具7: 获取系统当前状态 ==========
    def _tool_get_current_status(self) -> Dict[str, Any]:
        """获取系统当前状态"""
        try:
            conn = pymysql.connect(**DB_CONFIG)
            with conn.cursor() as cur:
                # 查询限速IP数量
                sql = "SELECT COUNT(*) FROM rate_limit_active WHERE expire_at > NOW()"
                cur.execute(sql)
                limited_count = cur.fetchone()[0]
                
                # 查询黑名单IP数量
                sql = "SELECT COUNT(*) FROM acl_entries WHERE list_type='black'"
                cur.execute(sql)
                blacklist_count = cur.fetchone()[0]
                
                # 查询白名单IP数量
                sql = "SELECT COUNT(*) FROM acl_entries WHERE list_type='white'"
                cur.execute(sql)
                whitelist_count = cur.fetchone()[0]
                
                # 查询最近的攻击事件
                sql = """SELECT src_ip, anomaly_type, start_time, status
                         FROM attack_sessions 
                         ORDER BY start_time DESC LIMIT 5"""
                cur.execute(sql)
                recent_attacks = cur.fetchall()
                
                # 查询设备异常数量
                sql = "SELECT COUNT(*) FROM device_anomalies WHERE status='pending'"
                cur.execute(sql)
                device_anomalies_count = cur.fetchone()[0]
                
                return {
                    "tool": "get_current_status",
                    "success": True,
                    "data": {
                        "total_hosts": 8,
                        "limited_ips_count": limited_count,
                        "blacklist_count": blacklist_count,
                        "whitelist_count": whitelist_count,
                        "device_anomalies_count": device_anomalies_count,
                        "recent_attacks": [
                            {
                                "ip": r[0],
                                "type": r[1],
                                "time": r[2].strftime('%Y-%m-%d %H:%M:%S') if hasattr(r[2], 'strftime') else str(r[2]),
                                "status": r[3]
                            } for r in recent_attacks
                        ],
                        "system_status": "normal" if limited_count < 3 else "warning" if limited_count < 6 else "critical"
                    }
                }
        except Exception as e:
            return {
                "tool": "get_current_status",
                "success": False,
                "error": str(e),
                "data": {}
            }
        finally:
            if conn:
                conn.close()

    # ========== MCP工具8: 应用限速（执行工具）==========
    def _tool_apply_rate_limit(self, ip: str, level: str, duration_seconds: int, reason: str) -> Dict[str, Any]:
        """应用限速规则
        
        【关键设计】：MCP工具只负责调用RYU API，不直接操作数据库
        所有操作（流表下发、内存更新、数据库写入）都由RYU控制器统一处理
        这样保证数据一致性和流表有效性
        
        【重要】：MCP工具是管理员调用的，所以operator='admin'
        这样RYU会：
        1. 写入rate_limit_log（operator='admin'）
        2. 写入attack_sessions（status='handled'）
        3. 写入limit_sessions（分钟合并）
        """
        try:
            import requests
            
            # 如果没有提供reason，默认为"前端手动限速"
            if not reason or reason.strip() == "":
                reason = "前端手动限速"
            
            # 映射限速档位
            level_map = {"low": 256, "medium": 1024, "high": 2048}
            kbps = level_map.get(level, 1024)
            
            # 【唯一操作】：调用RYU控制器的/v1/rate/apply接口
            # RYU会负责：
            # 1. 下发流表到OVS
            # 2. 更新内存字典 self.limited_ips
            # 3. 写入数据库 rate_limit_active
            # 4. 写入rate_limit_log（operator='admin'）
            # 5. 写入attack_sessions（status='handled'）
            # 6. 写入limit_sessions（分钟合并）
            RYU_BASE = "http://192.168.44.129:8080/v1"
            ryu_data = {
                "ip": ip,
                "kbps": kbps,
                "duration": duration_seconds,
                "reason": reason,
                "operator": "admin"  # ✅ 改为admin，表示这是管理员操作
            }
            print(f"[DEBUG] MCP工具调用RYU API: POST {RYU_BASE}/rate/apply")
            print(f"[DEBUG] 请求数据: {ryu_data}")
            
            try:
                ryu_response = requests.post(f"{RYU_BASE}/rate/apply", json=ryu_data, timeout=10)
                ryu_response.raise_for_status()
                ryu_result = ryu_response.json()
                print(f"[DEBUG] RYU API响应: {ryu_result}")
                
                # 检查RYU是否成功
                if ryu_result.get('success'):
                    print(f"[SUCCESS] RYU成功处理限速请求")
                    return {
                        "tool": "apply_rate_limit",
                        "success": True,
                        "data": {
                            "ip": ip,
                            "level": level,
                            "kbps": kbps,
                            "duration_seconds": duration_seconds,
                            "reason": reason,
                            "message": f"✅ 已对{ip}应用{level}限速（{kbps}Kbps），持续{duration_seconds}秒"
                        }
                    }
                else:
                    # RYU返回失败
                    error_msg = ryu_result.get('message', '未知错误')
                    print(f"[ERROR] RYU返回失败: {error_msg}")
                    return {
                        "tool": "apply_rate_limit",
                        "success": False,
                        "error": f"RYU控制器返回失败: {error_msg}",
                        "data": {}
                    }
            except requests.exceptions.RequestException as req_error:
                print(f"[ERROR] 请求RYU API失败: {req_error}")
                return {
                    "tool": "apply_rate_limit",
                    "success": False,
                    "error": f"无法连接RYU控制器: {str(req_error)}",
                    "data": {}
                }
        except Exception as e:
            print(f"[ERROR] MCP工具异常: {e}")
            import traceback
            traceback.print_exc()
            return {
                "tool": "apply_rate_limit",
                "success": False,
                "error": str(e),
                "data": {}
            }

    # ========== MCP工具9: 加入黑名单（执行工具）==========
    def _tool_add_to_blacklist(self, ip: str, reason: str) -> Dict[str, Any]:
        """将IP加入黑名单"""
        try:
            import requests
            
            # 【关键】第1步：先调用RYU控制器下发ACL规则
            RYU_BASE = "http://192.168.44.129:8080/v1"
            ryu_data = {"ip": ip, "ttl": -1}
            print(f"[DEBUG] 调用RYU控制器加入黑名单: {ryu_data}")
            ryu_success = False
            try:
                ryu_response = requests.post(f"{RYU_BASE}/acl/black", json=ryu_data, timeout=10)
                ryu_response.raise_for_status()
                ryu_result = ryu_response.json()
                print(f"[DEBUG] RYU控制器加入黑名单响应: {ryu_result}")
                ryu_success = ryu_result.get('success', False)
            except Exception as ryu_error:
                print(f"[ERROR] RYU控制器加入黑名单失败: {ryu_error}")
                return {
                    "tool": "add_to_blacklist",
                    "success": False,
                    "error": f"RYU控制器加入黑名单失败: {ryu_error}",
                    "data": {}
                }
            
            # 【关键修复】只有RYU成功才继续写入数据库
            if ryu_success:
                # 第2步：写入MySQL数据库
                conn = pymysql.connect(**DB_CONFIG)
                with conn.cursor() as cur:
                    sql = """INSERT INTO acl_entries (ip, list_type, created_at)
                             VALUES (%s, 'black', NOW())
                             ON DUPLICATE KEY UPDATE updated_at = NOW()"""
                    cur.execute(sql, (ip,))
                    conn.commit()
                    
                    return {
                        "tool": "add_to_blacklist",
                        "success": True,
                        "data": {
                            "ip": ip,
                            "reason": reason,
                            "message": f"已将{ip}加入黑名单，原因：{reason}，ACL规则已下发"
                        }
                    }
            else:
                return {
                    "tool": "add_to_blacklist",
                    "success": False,
                    "error": f"RYU控制器返回失败",
                    "data": {}
                }
        except Exception as e:
            print(f"[ERROR] 加入黑名单失败: {e}")
            return {
                "tool": "add_to_blacklist",
                "success": False,
                "error": str(e),
                "data": {}
            }
        finally:
            if conn:
                conn.close()

    # ========== MCP工具10: 加入白名单（执行工具）==========
    def _tool_add_to_whitelist(self, ip: str, reason: str) -> Dict[str, Any]:
        """将IP加入白名单"""
        try:
            import requests
            
            # 【关键】第1步：先调用RYU控制器下发ACL规则
            RYU_BASE = "http://192.168.44.129:8080/v1"
            ryu_data = {"ip": ip, "ttl": -1}
            print(f"[DEBUG] 调用RYU控制器加入白名单: {ryu_data}")
            ryu_success = False
            try:
                ryu_response = requests.post(f"{RYU_BASE}/acl/white", json=ryu_data, timeout=10)
                ryu_response.raise_for_status()
                ryu_result = ryu_response.json()
                print(f"[DEBUG] RYU控制器加入白名单响应: {ryu_result}")
                ryu_success = ryu_result.get('success', False)
            except Exception as ryu_error:
                print(f"[ERROR] RYU控制器加入白名单失败: {ryu_error}")
                return {
                    "tool": "add_to_whitelist",
                    "success": False,
                    "error": f"RYU控制器加入白名单失败: {ryu_error}",
                    "data": {}
                }
            
            # 【关键修复】只有RYU成功才继续写入数据库
            if ryu_success:
                # 第2步：写入MySQL数据库
                conn = pymysql.connect(**DB_CONFIG)
                with conn.cursor() as cur:
                    sql = """INSERT INTO acl_entries (ip, list_type, created_at)
                             VALUES (%s, 'white', NOW())
                             ON DUPLICATE KEY UPDATE updated_at = NOW()"""
                    cur.execute(sql, (ip,))
                    conn.commit()
                    
                    return {
                        "tool": "add_to_whitelist",
                        "success": True,
                        "data": {
                            "ip": ip,
                            "reason": reason,
                            "message": f"已将{ip}加入白名单，原因：{reason}，ACL规则已下发"
                        }
                    }
            else:
                return {
                    "tool": "add_to_whitelist",
                    "success": False,
                    "error": f"RYU控制器返回失败",
                    "data": {}
                }
        except Exception as e:
            print(f"[ERROR] 加入白名单失败: {e}")
            return {
                "tool": "add_to_whitelist",
                "success": False,
                "error": str(e),
                "data": {}
            }
        finally:
            if conn:
                conn.close()

    # ========== MCP工具11: 从黑名单删除IP（执行工具）==========
    def _tool_remove_from_blacklist(self, ip: str, reason: str = "管理员解除") -> Dict[str, Any]:
        """从黑名单删除IP"""
        try:
            import requests
            
            # 【关键】第1步：先调用RYU控制器删除ACL规则
            RYU_BASE = "http://192.168.44.129:8080/v1"
            print(f"[DEBUG] 调用RYU控制器从黑名单删除: {ip}")
            ryu_success = False
            try:
                ryu_response = requests.delete(f"{RYU_BASE}/acl/black/{ip}", timeout=10)
                ryu_response.raise_for_status()
                ryu_result = ryu_response.json()
                print(f"[DEBUG] RYU控制器删除黑名单响应: {ryu_result}")
                ryu_success = ryu_result.get('success', False)
            except Exception as ryu_error:
                print(f"[ERROR] RYU控制器删除黑名单失败: {ryu_error}")
                return {
                    "tool": "remove_from_blacklist",
                    "success": False,
                    "error": f"RYU控制器删除黑名单失败: {ryu_error}",
                    "data": {}
                }
            
            # 【关键修复】如果RYU成功，就返回成功，不管数据库是否有记录
            if ryu_success:
                # 第2步：尝试从数据库中删除（但不影响最终结果）
                conn = pymysql.connect(**DB_CONFIG)
                with conn.cursor() as cur:
                    sql = "DELETE FROM acl_entries WHERE ip=%s AND list_type='black'"
                    affected = cur.execute(sql, (ip,))
                    conn.commit()
                    print(f"[DEBUG] 数据库DELETE影响行数: {affected}")
                
                # 【关键】：RYU成功了，就返回成功，即使数据库没有记录
                return {
                    "tool": "remove_from_blacklist",
                    "success": True,
                    "data": {
                        "ip": ip,
                        "reason": reason,
                        "message": f"已将{ip}从黑名单中删除，原因：{reason}，ACL规则已删除"
                    }
                }
            else:
                return {
                    "tool": "remove_from_blacklist",
                    "success": False,
                    "error": f"RYU控制器返回失败",
                    "data": {}
                }
        except Exception as e:
            print(f"[ERROR] 从黑名单删除失败: {e}")
            return {
                "tool": "remove_from_blacklist",
                "success": False,
                "error": str(e),
                "data": {}
            }
        finally:
            if conn:
                conn.close()

    # ========== MCP工具12: 从白名单删除IP（执行工具）==========
    def _tool_remove_from_whitelist(self, ip: str, reason: str = "管理员解除") -> Dict[str, Any]:
        """从白名单删除IP"""
        try:
            import requests
            
            # 【关键】第1步：先调用RYU控制器删除ACL规则
            RYU_BASE = "http://192.168.44.129:8080/v1"
            print(f"[DEBUG] 调用RYU控制器从白名单删除: {ip}")
            ryu_success = False
            try:
                ryu_response = requests.delete(f"{RYU_BASE}/acl/white/{ip}", timeout=10)
                ryu_response.raise_for_status()
                ryu_result = ryu_response.json()
                print(f"[DEBUG] RYU控制器删除白名单响应: {ryu_result}")
                ryu_success = ryu_result.get('success', False)
            except Exception as ryu_error:
                print(f"[ERROR] RYU控制器删除白名单失败: {ryu_error}")
                return {
                    "tool": "remove_from_whitelist",
                    "success": False,
                    "error": f"RYU控制器删除白名单失败: {ryu_error}",
                    "data": {}
                }
            
            # 【关键修复】如果RYU成功，就返回成功，不管数据库是否有记录
            if ryu_success:
                # 第2步：尝试从数据库中删除（但不影响最终结果）
                conn = pymysql.connect(**DB_CONFIG)
                with conn.cursor() as cur:
                    sql = "DELETE FROM acl_entries WHERE ip=%s AND list_type='white'"
                    affected = cur.execute(sql, (ip,))
                    conn.commit()
                    print(f"[DEBUG] 数据库DELETE影响行数: {affected}")
                
                # 【关键】：RYU成功了，就返回成功，即使数据库没有记录
                return {
                    "tool": "remove_from_whitelist",
                    "success": True,
                    "data": {
                        "ip": ip,
                        "reason": reason,
                        "message": f"已将{ip}从白名单中删除，原因：{reason}，ACL规则已删除"
                    }
                }
            else:
                return {
                    "tool": "remove_from_whitelist",
                    "success": False,
                    "error": f"RYU控制器返回失败",
                    "data": {}
                }
        except Exception as e:
            print(f"[ERROR] 从白名单删除失败: {e}")
            return {
                "tool": "remove_from_whitelist",
                "success": False,
                "error": str(e),
                "data": {}
            }
        finally:
            if conn:
                conn.close()

    # ========== MCP工具13: 解除限速（执行工具）==========
    def _tool_release_rate_limit(self, ip: str, reason: str = "管理员解除") -> Dict[str, Any]:
        """解除对IP的限速"""
        try:
            import requests
            
            # 【关键】第1步：先调用RYU控制器删除流表
            RYU_BASE = "http://192.168.44.129:8080/v1"
            print(f"[DEBUG] 调用RYU控制器解除限速: {ip}")
            ryu_success = False
            try:
                ryu_response = requests.delete(f"{RYU_BASE}/rate/{ip}", timeout=10)
                ryu_response.raise_for_status()
                ryu_result = ryu_response.json()
                print(f"[DEBUG] RYU控制器解除限速响应: {ryu_result}")
                ryu_success = ryu_result.get('success', False)
            except Exception as ryu_error:
                print(f"[ERROR] RYU控制器解除限速失败: {ryu_error}")
                return {
                    "tool": "release_rate_limit",
                    "success": False,
                    "error": f"RYU控制器解除限速失败: {ryu_error}",
                    "data": {}
                }
            
            # 【关键修复】如果RYU成功，就返回成功，不管数据库是否有记录
            if ryu_success:
                # 第2步：尝试从数据库中删除（但不影响最终结果）
                conn = pymysql.connect(**DB_CONFIG)
                with conn.cursor() as cur:
                    sql = "DELETE FROM rate_limit_active WHERE src_ip=%s"
                    affected = cur.execute(sql, (ip,))
                    conn.commit()
                    print(f"[DEBUG] 数据库DELETE影响行数: {affected}")
                
                # 【关键】：RYU成功了，就返回成功，即使数据库没有记录
                return {
                    "tool": "release_rate_limit",
                    "success": True,
                    "data": {
                        "ip": ip,
                        "reason": reason,
                        "message": f"已解除对{ip}的限速，原因：{reason}，流表已删除"
                    }
                }
            else:
                return {
                    "tool": "release_rate_limit",
                    "success": False,
                    "error": f"RYU控制器返回失败",
                    "data": {}
                }
        except Exception as e:
            print(f"[ERROR] 解除限速失败: {e}")
            return {
                "tool": "release_rate_limit",
                "success": False,
                "error": str(e),
                "data": {}
            }
        finally:
            if conn:
                conn.close()

    # ========== MCP工具14: 修改限速时长（执行工具）==========
    def _tool_modify_rate_limit_duration(self, ip: str, duration_seconds: int, reason: str = "修改限速时长") -> Dict[str, Any]:
        """修改对IP的限速时长"""
        try:
            import requests
            
            # 【关键】第1步：先调用RYU控制器更新流表过期时间
            RYU_BASE = "http://192.168.44.129:8080/v1"
            ryu_data = {
                "extra_seconds": duration_seconds  # 【修复】RYU期望的参数名是extra_seconds，不是duration
            }
            print(f"[DEBUG] 调用RYU控制器修改限速时长: {ryu_data}")
            try:
                ryu_response = requests.put(f"{RYU_BASE}/rate/duration/{ip}", json=ryu_data, timeout=10)
                ryu_response.raise_for_status()
                ryu_result = ryu_response.json()
                print(f"[DEBUG] RYU控制器修改限速时长响应: {ryu_result}")
            except Exception as ryu_error:
                print(f"[WARNING] RYU控制器修改限速时长失败，但继续更新数据库: {ryu_error}")
                # 继续执行，不中断流程
            
            # 【关键】第2步：更新数据库
            conn = pymysql.connect(**DB_CONFIG)
            with conn.cursor() as cur:
                # 先检查IP是否存在
                sql_check = "SELECT 1 FROM rate_limit_active WHERE src_ip=%s"
                cur.execute(sql_check, (ip,))
                existing = cur.fetchone()
                
                if existing:
                    # IP存在，执行UPDATE
                    sql = """UPDATE rate_limit_active 
                             SET expire_at = DATE_ADD(NOW(), INTERVAL %s SECOND)
                             WHERE src_ip=%s"""
                    affected = cur.execute(sql, (duration_seconds, ip))
                    conn.commit()
                    
                    print(f"[DEBUG] 数据库UPDATE影响行数: {affected}")
                    
                    # 【关键修复】：即使affected=0，也应该返回成功
                    # 因为RYU已经成功更新了流表和内存
                    return {
                        "tool": "modify_rate_limit_duration",
                        "success": True,
                        "data": {
                            "ip": ip,
                            "duration_seconds": duration_seconds,
                            "reason": reason,
                            "message": f"✅ 已修改{ip}的限速时长为{duration_seconds}秒，原因：{reason}，流表已更新"
                        }
                    }
                else:
                    # IP不存在，但RYU已经成功了
                    print(f"[WARNING] 数据库中未找到{ip}的限速记录，但RYU已成功处理")
                    return {
                        "tool": "modify_rate_limit_duration",
                        "success": True,
                        "data": {
                            "ip": ip,
                            "duration_seconds": duration_seconds,
                            "reason": reason,
                            "message": f"✅ 已修改{ip}的限速时长为{duration_seconds}秒，原因：{reason}，流表已更新（数据库记录可能已过期）"
                        }
                    }
        except Exception as e:
            print(f"[ERROR] 修改限速时长失败: {e}")
            return {
                "tool": "modify_rate_limit_duration",
                "success": False,
                "error": str(e),
                "data": {}
            }
        finally:
            if conn:
                conn.close()

    # ========== MCP工具15: 修改限速数值（执行工具）==========
    def _tool_modify_rate_limit_kbps(self, ip: str, kbps: int, reason: str = "修改限速数值") -> Dict[str, Any]:
        """修改对IP的限速数值（kbps）"""
        try:
            import requests
            
            # 验证kbps值
            if kbps not in [256, 512, 1024, 2048]:
                return {
                    "tool": "modify_rate_limit_kbps",
                    "success": False,
                    "error": f"限速数值必须为256、512、1024或2048 kbps，不支持 {kbps}",
                    "data": {}
                }
            
            # 【关键】第1步：先调用RYU控制器更新流表限速速率
            RYU_BASE = "http://192.168.44.129:8080/v1"
            ryu_data = {
                "ip": ip,
                "kbps": kbps
            }
            print(f"[DEBUG] 调用RYU控制器修改限速速率: {ryu_data}")
            try:
                ryu_response = requests.put(f"{RYU_BASE}/rate/speed/{ip}", json=ryu_data, timeout=10)
                ryu_response.raise_for_status()
                ryu_result = ryu_response.json()
                print(f"[DEBUG] RYU控制器修改限速速率响应: {ryu_result}")
            except Exception as ryu_error:
                print(f"[WARNING] RYU控制器修改限速速率失败，但继续更新数据库: {ryu_error}")
                # 继续执行，不中断流程
            
            # 【关键】第2步：更新数据库
            conn = pymysql.connect(**DB_CONFIG)
            with conn.cursor() as cur:
                # 先检查IP是否存在
                sql_check = "SELECT expire_at FROM rate_limit_active WHERE src_ip=%s"
                cur.execute(sql_check, (ip,))
                existing = cur.fetchone()
                
                if existing:
                    # IP存在，执行UPDATE
                    sql = """UPDATE rate_limit_active 
                             SET kbps = %s
                             WHERE src_ip=%s"""
                    affected = cur.execute(sql, (kbps, ip))
                    conn.commit()
                    
                    print(f"[DEBUG] 数据库UPDATE影响行数: {affected}")
                    
                    # 【关键修复】：即使affected=0，也应该返回成功
                    # 因为RYU已经成功更新了流表和内存
                    # 数据库可能因为值相同而affected=0，但这不是失败
                    expire_at = existing[0].strftime('%Y-%m-%d %H:%M:%S') if existing[0] else "未知"
                    
                    return {
                        "tool": "modify_rate_limit_kbps",
                        "success": True,
                        "data": {
                            "ip": ip,
                            "kbps": kbps,
                            "expire_at": expire_at,
                            "reason": reason,
                            "message": f"✅ 已修改{ip}的限速数值为{kbps} kbps，原因：{reason}，流表已更新"
                        }
                    }
                else:
                    # IP不存在，但RYU已经成功了
                    # 这种情况下应该返回成功（因为RYU已经处理了）
                    print(f"[WARNING] 数据库中未找到{ip}的限速记录，但RYU已成功处理")
                    return {
                        "tool": "modify_rate_limit_kbps",
                        "success": True,
                        "data": {
                            "ip": ip,
                            "kbps": kbps,
                            "reason": reason,
                            "message": f"✅ 已修改{ip}的限速数值为{kbps} kbps，原因：{reason}，流表已更新（数据库记录可能已过期）"
                        }
                    }
        except Exception as e:
            print(f"[ERROR] 修改限速速率失败: {e}")
            return {
                "tool": "modify_rate_limit_kbps",
                "success": False,
                "error": str(e),
                "data": {}
            }
        finally:
            if conn:
                conn.close()

    # ========== 旧工具（保留兼容性）==========
    def _tool_check_ip_history(self, ip: str) -> Dict[str, Any]:
        """检查IP历史记录（兼容旧版本）"""
        # 调用新的查询工具
        acl_status = self._tool_query_acl_status(ip)
        attack_history = self._tool_query_attack_history(ip)
        rate_limit = self._tool_query_rate_limit_history(ip)
        
        return {
            "tool": "check_ip_history",
            "success": True,
            "data": {
                "ip": ip,
                "acl_status": acl_status['data'],
                "attack_history": attack_history['data'],
                "rate_limit": rate_limit['data']
            }
        }
    
    def _tool_get_network_status(self) -> Dict[str, Any]:
        """获取网络状态（兼容旧版本）"""
        # 调用新的查询工具
        return self._tool_get_current_status()
    
    # ========== Agent核心功能 ==========
    
    def analyze_anomaly(self, anomaly_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        分析网络异常（Agent主要功能）
        
        Args:
            anomaly_info: 异常信息
                - type: 攻击类型
                - src_ip: 源IP
                - features: 特征描述
                
        Returns:
            分析结果
        """
        src_ip = anomaly_info.get('src_ip', '未知')
        anomaly_type = anomaly_info.get('type', '未知')
        features = anomaly_info.get('features', '无')
        
        print(f"\n{'='*60}")
        print(f"🤖 Security Agent 开始分析异常...")
        print(f"   异常类型: {anomaly_type}")
        print(f"   源IP: {src_ip}")
        print(f"{'='*60}")
        
        # ========== 阶段1: 知识检索（RAG） ==========
        print("\n📚 [阶段1] 检索知识库...")
        query = f"{anomaly_type}攻击的特征和防御策略"
        knowledge_result = self._tool_search_knowledge(query)
        
        if knowledge_result['success'] and knowledge_result['data']:
            print(f"✅ 检索到 {knowledge_result['count']} 条相关知识")
            knowledge_context = "\n".join([f"- {k[:100]}..." for k in knowledge_result['data']])
        else:
            print("⚠️ 未检索到相关知识")
            knowledge_context = "（暂无相关知识库信息）"
        
        # ========== 阶段2: 信息收集（MCP工具调用） ==========
        print("\n🔍 [阶段2] 调用MCP工具收集信息...")
        
        # 调用工具1：查询ACL状态
        acl_status = self._tool_query_acl_status(src_ip)
        print(f"   ✓ 已查询ACL状态")
        
        # 调用工具2：查询限速历史
        rate_limit_history = self._tool_query_rate_limit_history(src_ip)
        print(f"   ✓ 已查询限速历史")
        
        # 调用工具3：查询攻击历史
        attack_history = self._tool_query_attack_history(src_ip)
        print(f"   ✓ 已查询攻击历史")
        
        # 调用工具4：查询流量统计
        flow_stats = self._tool_query_flow_stats(src_ip)
        print(f"   ✓ 已查询流量统计")
        
        # 调用工具5：获取防御规则
        defense_rules = self._tool_get_defense_rules(anomaly_type)
        print(f"   ✓ 已获取防御规则")
        
        # 调用工具6：查询网络拓扑
        network_topology = self._tool_query_network_topology()
        print(f"   ✓ 已查询网络拓扑")
        
        # 调用工具7：获取系统状态
        system_status = self._tool_get_current_status()
        print(f"   ✓ 已获取系统状态")
        
        # ========== 阶段3: LLM分析（Agent思考） ==========
        print("\n🧠 [阶段3] AI分析中...")
        
        # 构建增强提示词
        prompt = f"""你是一个网络安全专家，正在分析一个网络异常事件。

【检测到的异常信息】
- 攻击类型：{anomaly_type}
- 源IP：{src_ip}
- 异常特征：{features}

【知识库相关信息】
{knowledge_context}

【IP黑白名单状态】
{json.dumps(acl_status['data'], ensure_ascii=False, indent=2)}

【IP限速历史】
{json.dumps(rate_limit_history['data'], ensure_ascii=False, indent=2)}

【IP攻击历史】
{json.dumps(attack_history['data'], ensure_ascii=False, indent=2)}

【IP流量统计（最近1小时）】
{json.dumps(flow_stats['data'], ensure_ascii=False, indent=2)}

【防御规则】
{json.dumps(defense_rules['data'], ensure_ascii=False, indent=2)}

【网络拓扑】
{json.dumps(network_topology['data'], ensure_ascii=False, indent=2)}

【系统当前状态】
{json.dumps(system_status['data'], ensure_ascii=False, indent=2)}

请基于以上信息，用JSON格式给出分析结果：
{{
    "risk_level": "低/中/高/严重",
    "confidence": 0-100的整数,
    "recommended_action": "rate_limit/blacklist/alert_only/no_action",
    "kbps": 建议的限速速率（如果action是rate_limit）,
    "reason": "详细的分析原因，200字以内",
    "evidence": ["证据1", "证据2", "证据3"]
}}

只返回JSON，不要其他内容。"""
        
        llm_response = self._call_llm(prompt, temperature=0.2)
        
        # 解析LLM响应
        try:
            # 提取JSON部分
            json_start = llm_response.find('{')
            json_end = llm_response.rfind('}') + 1
            if json_start >= 0 and json_end > json_start:
                analysis = json.loads(llm_response[json_start:json_end])
            else:
                raise ValueError("未找到JSON格式的响应")
        except Exception as e:
            print(f"⚠️ LLM响应解析失败，使用默认分析: {e}")
            analysis = {
                "risk_level": "中",
                "confidence": 50,
                "recommended_action": "alert_only",
                "reason": f"检测到{anomaly_type}异常，建议人工审核",
                "evidence": ["自动检测到异常流量"]
            }
        
        print(f"✅ 分析完成")
        print(f"   风险等级: {analysis.get('risk_level', '未知')}")
        print(f"   置信度: {analysis.get('confidence', 0)}%")
        print(f"   建议措施: {analysis.get('recommended_action', '未知')}")
        
        # ========== 阶段4: 生成完整报告 ==========
        result = {
            "anomaly_type": anomaly_type,
            "src_ip": src_ip,
            "timestamp": datetime.now().isoformat(),
            
            # RAG检索结果
            "knowledge_sources": knowledge_result['data'] if knowledge_result['success'] else [],
            "knowledge_count": knowledge_result.get('count', 0),
            
            # MCP工具调用结果
            "tools_used": [
                "search_knowledge",
                "query_acl_status",
                "query_rate_limit_history",
                "query_attack_history",
                "query_flow_stats",
                "get_defense_rules",
                "query_network_topology",
                "get_current_status"
            ],
            "mcp_results": {
                "acl_status": acl_status['data'],
                "rate_limit_history": rate_limit_history['data'],
                "attack_history": attack_history['data'],
                "flow_stats": flow_stats['data'],
                "defense_rules": defense_rules['data'],
                "network_topology": network_topology['data'],
                "system_status": system_status['data']
            },
            
            # Agent分析结果
            "analysis": analysis,
            
            # 元数据
            "agent_version": "2.0",
            "model_used": self.model,
            "rag_enabled": True,
            "mcp_enabled": True
        }
        
        print(f"\n{'='*60}")
        print("✅ Agent分析完成！")
        print(f"{'='*60}\n")
        
        return result
    
    def quick_query(self, query: str) -> Dict[str, Any]:
        """
        快速查询（简单的RAG问答）
        
        Args:
            query: 用户查询
            
        Returns:
            查询结果
        """
        print(f"\n🤖 Agent快速查询: {query}")
        
        # 使用RAG生成回答
        rag_result = self.rag.generate_with_rag(query, top_k=3)
        
        return {
            "query": query,
            "answer": rag_result['answer'],
            "knowledge_sources": rag_result['knowledge_sources'],
            "timestamp": datetime.now().isoformat(),
            "agent_version": "1.0"
        }


# 全局Agent实例
_agent_instance = None

def get_agent_instance() -> SecurityAgent:
    """获取Agent实例（单例）"""
    global _agent_instance
    if _agent_instance is None:
        _agent_instance = SecurityAgent()
    return _agent_instance


# 测试代码
if __name__ == "__main__":
    print("="*60)
    print("Security Agent 测试")
    print("="*60)
    
    # 初始化Agent
    agent = get_agent_instance()
    
    # 测试1: 分析异常
    print("\n\n【测试1：分析DDoS攻击】")
    result = agent.analyze_anomaly({
        "type": "DDoS",
        "src_ip": "192.168.1.100",
        "features": "流量突增，包大小512字节，目标端口80"
    })
    
    print("\n【分析结果】")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    
    # 测试2: 快速查询
    print("\n\n【测试2：快速查询】")
    query_result = agent.quick_query("什么是端口扫描？如何防御？")
    
    print("\n【查询结果】")
    print(f"回答: {query_result['answer']}")
    print(f"\n知识源数量: {len(query_result['knowledge_sources'])}")
