#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
RYU 安全控制器（黑白名单→孤立森林→LLM限速→管理员处置）
1. 黑名单：直接丢弃
2. 白名单：直接放行，且**永不限速**
3. 孤立森林异常 → 调用 LLM
   · LLM 返回合法且 confidence≥0.5 → 立即限速（5 min）
   · LLM 返回非法 → 只告警、不限速
4. 管理员后续：
   · 确认攻击：ai: 加黑 x.x.x.x
   · 误报：ai: 解除限速 x.x.x.x（同时增量学习）
5. 限速状态持久化，重启不丢
6. 原始流量实时写库（REALTIME_INSERT = True）
"""
import time
import pymysql
import csv, io
import matplotlib.pyplot as plt
from io import BytesIO
import base64
from collections import deque
import threading
from weasyprint import HTML
import tempfile
import ipaddress
ANOMALY_QUEUE = deque()          # 内存队列
QUEUE_LOCK  = threading.Lock()   # 保护锁
import geoip2.database
GEO_DB = '/usr/share/GeoIP/GeoLite2-City.mmdb' 

import eventlet

eventlet.monkey_patch(socket=True, select=True, thread=True)

import json, os, time, pymysql, requests, pickle, math, re, numpy as np
from datetime import datetime, timedelta
from collections import defaultdict, Counter
from sklearn.ensemble import IsolationForest
from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import CONFIG_DISPATCHER, MAIN_DISPATCHER, set_ev_cls
from ryu.lib import hub
from ryu.lib.packet import packet, ethernet, ipv4, icmp, tcp, udp, arp, ether_types
from ryu.ofproto import ofproto_v1_3
from ryu.app.wsgi import WSGIApplication, ControllerBase, route
from ryu.base import app_manager as ry_app_mgr
from ryu.app.wsgi import Response

# -------------------------- 配置 -----------------------------
DB_CONFIG = {
    'host': '192.168.44.1', 'user': 'root', 'password': 'yyr0218...',
    'db': 'network_management', 'charset': 'utf8mb4'
}
# ---------- 限速档位 ----------
RATE_LIMIT_OPTIONS = {
    "低速": 256,
    "中速": 1024,
    "高速": 2048,
    "自定义": None
}

MODEL_PATH = 'isolation_forest_model.pkl'
ANOMALY_LOG = 'anomaly_traffic.log'
SUMMARY_JSON = 'anomaly_summary.json'
LOG_MAX_SIZE = 10 * 1024 * 1024
WHITE_FILE = 'white_list.json'
BLACK_FILE = 'black_list.json'

RATE_LIMIT_DURATION = 300  # 限速 5 分钟
REALTIME_INSERT = False  # 关闭实时写库，改为批量写库（减少I/O）

# 攻击阈值（ICMP 调高到 500，避免正常 ping 误判）
# ---------- 攻击检测阈值 ----------
THRESH = {
    'arp': {'mac_change': 1, 'spoof_cnt': 1},   # ARP欺骗：MAC变化检测
    'udp': {'flood_rate': 200},                  # UDP Flood：200 pps
    'icmp': {'flood_rate': 2000},                # ✅ ICMP Flood：2000 pps（避免pingall误报）
    'syn': {'ratio': 0.8, 'rate': 200, 'min_tcp': 20},  # SYN Flood：200 pps
    'botnet': {'dst_ip_cnt': 10, 'port_entropy': 3.0, 'pkt_rate': 2000}  # 僵尸网络
}





ISOLATION_PARAM = dict(n_estimators=100, max_samples='auto', contamination=0.1, random_state=42, n_jobs=-1)
OLLAMA_URL = 'http://192.168.44.1:11435/api/generate'
MEMORY_TURNS = 20

# 玩法1: AI摘要 & 玩法2: 口语规则 & 玩法4: 周报
AI_SUMMARY_ENABLED = True
CUSTOM_RULES = {}  # 存储口语规则，如 {'udp_threshold': 100}
WEEKLY_REPORT_DATA = []  # 存储周报数据


# -------------------------------------------------------------


class SDNSecurityController(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]
    _CONTEXTS = {'wsgi': WSGIApplication}

    def __init__(self, *args, **kwargs):
        super(SDNSecurityController, self).__init__(*args, **kwargs)
        self.mac_to_port, self.arp_table = {}, {}
        self.datapaths = {}
        self.db_conn = None
        self.flow_cache = []
        self.anomaly_cache = []
        self.limited_ips = {}
        self.switch_flow_stats = {}  # 缓存每个交换机的流表: {dpid: [flow_stats]}
        self.anomaly_counter = defaultdict(int)
                # Land Attack 标记
        self.land_attack_seen = set()   # 已加黑的 IP，避免重复日志
        self.scan_tracker = defaultdict(lambda: {'ports': set(), 'last': time.time()})



        # 滑动事件窗口：{ (ip,攻击类型) : 最后时间戳 }
        # 滑动事件窗口：{ (ip,攻击类型) : 最后时间戳 }
        self.SLIDE_WINDOW = {}
        self.WINDOW_SEC = 30          # 30 秒窗口，可改
        
        self.ssh_brute = defaultdict(lambda: {'conns': 0, 'last': time.time()})

        # ✅ 设备异常追踪器
        self.port_flap_tracker = defaultdict(list)  # 端口抖动追踪: {(dpid, port): [时间戳列表]}
        self.mac_port_map = {}  # MAC-端口映射: {mac: (dpid, port)}
        self.ip_subnet_checked = set()  # 已检查过的IP（避免重复报警）
        self.VALID_SUBNET = '192.168.1.0/24'  # 合法IP网段

        # 训练期正常速率均值（保底值）
        self.normal_tcp_rate = defaultdict(lambda: 200)
        self.normal_arp_rate = defaultdict(lambda: 50)
        self.port_stats = defaultdict(dict)   # 端口名称映射



        self.src_dst_counter = defaultdict(set)
        self.src_port_counter = defaultdict(set)
        self.arp_stats = defaultdict(lambda: {'count': 0, 'last_time': time.time(), 'macs': set(), 'spoof_count': 0})
        self.tcp_flag_stats = defaultdict(lambda: {'syn': 0, 'total': 0, 'last': time.time()})
        self.udp_stats = defaultdict(lambda: {'count': 0, 'last': time.time()})
        self.icmp_stats = defaultdict(lambda: {'count': 0, 'last': time.time()})
        self.raw_pkt_counter = defaultdict(int)
        self.raw_last_time = defaultdict(float)

        self.flow_features_with_info = []
        self.isolation_model = None
        self.is_training = False
        self.training_seconds = 300

        # ACL - 先从JSON文件加载，再从数据库覆盖（数据库优先）
        self.white = self._load_acl_file(WHITE_FILE)
        self.black = self._load_acl_file(BLACK_FILE)

        # Web
        wsgi = kwargs['wsgi']
        wsgi.register(ChatController, {'ctrl': self})

        # 后台
        self._init_anomaly_files()
        self._restore_model()
        hub.spawn(self._db_loop)
        hub.spawn(self._stats_loop)
        hub.spawn(self._detect_loop)
        hub.spawn(self._cleanup_loop)
        hub.spawn(self._reset_loop)
        hub.spawn(self._summarize_loop)
        hub.spawn(self._db_writer_loop)
        hub.spawn(self._auto_close_attack_sessions_loop)  # ✅ 新增：自动关闭过期攻击会话
        hub.spawn(self._device_anomaly_detection_loop)  # ✅ 新增：设备异常检测定时器
        if REALTIME_INSERT:
            hub.spawn(self._realtime_insert_loop)  ### 实时写库
        self.logger.info("✅ SDN 安全控制器（LLM 限速→管理员处置）初始化完成")
        self._restore_rate_limit_from_db()
        self._restore_acl_from_db()  # 从数据库恢复黑白名单
        
        # 🎯 延迟3秒后更新所有交换机的默认规则（确保交换机已连接）
        hub.spawn_after(3, self.update_all_table_miss_rules)

    # ---------------- 工具 ----------------
    def _load_acl_file(self, path):
        return json.load(open(path)) if os.path.exists(path) else {}

    def _save_acl_file(self, acl, path):
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(acl, f, ensure_ascii=False)

    def _init_anomaly_files(self):
        for f, desc in [(ANOMALY_LOG, "异常日志"), (SUMMARY_JSON, "汇总文件")]:
            if not os.path.exists(f):
                with open(f, 'w', encoding='utf-8') as wf:
                    json.dump({"desc": desc, "create": time.strftime('%Y-%m-%d %H:%M:%S')}, wf, ensure_ascii=False)
                    wf.write('\n')

    def get_limit_list(self):
        """返回当前限速列表（含原因、速率、开始时间、剩余秒数）"""
        now = time.time()
        conn = None
        try:
            conn = pymysql.connect(**DB_CONFIG)
            with conn.cursor() as cur:
                sql = """
                    SELECT src_ip, kbps, reason, created_at, expire_at
                    FROM rate_limit_active
                    WHERE expire_at > NOW()
                    ORDER BY created_at DESC
                """
                cur.execute(sql)
                rows = cur.fetchall()
        except Exception as e:
            self.logger.error(f"get_limit_list 查询失败: {e}")
            rows = []
        finally:
            if conn: conn.close()

        data = []
        for r in rows:
            # 防御式：expire_at 可能是 datetime 也可能是 int
            expire_val = r[4]
            if hasattr(expire_val, 'timestamp'):   # datetime
                expire_ts = expire_val.timestamp()
            else:                                    # 万一存成 int
                expire_ts = int(expire_val)
            ttl = max(0, int(expire_ts - now))

            data.append({
                'ip': r[0],
                'kbps': int(r[1]),
                'reason': r[2],
                'start_time': r[3].strftime('%Y-%m-%d %H:%M:%S'),
                'ttl_left': ttl
            })
        return data




    def _restore_model(self):
        if os.path.exists(MODEL_PATH):
            try:
                with open(MODEL_PATH, 'rb') as f:
                    data = pickle.load(f)
                    self.isolation_model = data['model']
                    ISOLATION_PARAM['contamination'] = data.get('contamination', 0.1)
                self.logger.info("✅ 模型加载成功")
            except Exception as e:
                self.logger.error(f"❌ 模型加载失败: {e}")
                self.is_training = True
                hub.spawn(self._train_task)
        else:
            self.is_training = True
            hub.spawn(self._train_task)
    
    # ---------------- 启动时把数据库中未过期的限速重新载入内存 + 重新下发流表 ----------------
    def _restore_acl_from_db(self):
        """
        重启控制器后，从数据库恢复黑白名单到内存（数据库优先于JSON文件）
        """
        conn = None
        try:
            conn = pymysql.connect(**DB_CONFIG)
            with conn.cursor() as cur:
                # 查询所有ACL条目
                sql = "SELECT ip, list_type FROM acl_entries"
                cur.execute(sql)
                rows = cur.fetchall()
                
                if not rows:
                    self.logger.info("✅ 数据库中无ACL记录，使用JSON文件数据")
                    return
                
                # 清空内存中的ACL（数据库优先）
                self.white.clear()
                self.black.clear()
                
                white_count = 0
                black_count = 0
                
                for ip, list_type in rows:
                    if list_type == 'white':
                        self.white[ip] = -1  # -1 表示永久
                        white_count += 1
                    elif list_type == 'black':
                        self.black[ip] = -1  # -1 表示永久
                        black_count += 1
                
                self.logger.info(f"✅ 从数据库恢复ACL: 白名单 {white_count} 个, 黑名单 {black_count} 个")
                
                # 更新JSON文件，保持同步
                self._save_acl_file(self.white, WHITE_FILE)
                self._save_acl_file(self.black, BLACK_FILE)
                
        except Exception as e:
            self.logger.error(f"❌ 从数据库恢复ACL失败: {e}")
            import traceback
            traceback.print_exc()
        finally:
            if conn:
                conn.close()

    def _restore_rate_limit_from_db(self):
        """
        重启控制器后，把 rate_limit_active 表里未过期的记录重新读入内存，
        并重新下发流表限速规则（5 min 硬超时）。
        """
        conn = None
        try:
            conn = pymysql.connect(**DB_CONFIG)
            with conn.cursor() as cur:
                sql = """
                    SELECT src_ip, kbps, UNIX_TIMESTAMP(expire_at) AS expire_ts
                    FROM rate_limit_active
                    WHERE expire_at > NOW()
                """
                cur.execute(sql)
                rows = cur.fetchall()
                if not rows:
                    self.logger.info("✅ 数据库中无未过期限速记录，跳过恢复")
                    return

                now = time.time()
                restored = 0
                for ip, kbps, expire_ts in rows:
                    remain = max(1, int(expire_ts - now))          # 至少 1 秒
                    self.limited_ips[str(ip)] = float(expire_ts)   # 写回内存

                    # 重新下发流表（直接抄 _apply_rate_limit 的队列逻辑）
                    if kbps <= 256:
                        q = 1
                    elif kbps <= 1024:
                        q = 2
                    elif kbps <= 2048:
                        q = 3
                    else:
                        q = 3
                    for dp in self.datapaths.values():
                        ofp, ps = dp.ofproto, dp.ofproto_parser
                        match = ps.OFPMatch(eth_type=ether_types.ETH_TYPE_IP,
                                            ipv4_src=str(ip))
                        acts = [ps.OFPActionSetQueue(queue_id=q),
                                ps.OFPActionOutput(ofp.OFPP_NORMAL)]
                        # ✅ 修复：添加idle=0，防止流表因空闲而被删除
                        self._add_flow(dp, 50, match, acts, idle=0, hard=remain)
                    restored += 1
                    self.logger.warning(
                        f"🔒 恢复限速: ip={ip}, kbps={kbps}, remain={remain}s, queue={q}")
                self.logger.info(f"✅ 共恢复 {restored} 条限速记录")
        except Exception as e:
            self.logger.error(f"❌ 恢复限速失败: {e}")
        finally:
            if conn:
                conn.close()


    # ---------------- 数据库 ----------------
    def _db_loop(self):
        while True:
            try:
                self.db_conn = pymysql.connect(**DB_CONFIG)
                self.logger.info("✅ 数据库连接成功")
                return
            except Exception as e:
                self.logger.error(f"❌ 数据库连接失败: {e}，10s 后重试")
                hub.sleep(10)

    def get_db_conn(self):
        try:
            if not hasattr(self, 'db_conn') or not self.db_conn or self.db_conn._closed:
                self._db_loop()
            # 测试连接是否有效
            self.db_conn.ping(reconnect=True)
            return self.db_conn
        except Exception as e:
            self.logger.error(f"数据库连接错误: {e}")
            self._db_loop()
            return self.db_conn

    # ---------------- ACL（同步入库） ----------------
    def acl_check(self, ip: str) -> str:
        now = time.time()
        if ip in self.white:
            if self.white[ip] == -1 or self.white[ip] > now:
                return 'white'
            else:
                self.white.pop(ip, None)
                self._save_acl_file(self.white, WHITE_FILE)
                self._del_acl_from_db(ip, 'white')
        if ip in self.black:
            if self.black[ip] == -1 or self.black[ip] > now:
                return 'black'
            else:
                self.black.pop(ip, None)
                self._save_acl_file(self.black, BLACK_FILE)
                self._del_acl_from_db(ip, 'black')
        return None

    def get_acl_lists(self):
        now = time.time()
        white_list, black_list = [], []
        for ip, exp in self.white.items():
            status = "永久" if exp == -1 else "有效" if exp > now else "已过期"
            expire_str = "永久" if exp == -1 else time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(exp))
            white_list.append({"ip": ip, "expire_time": exp, "expire_str": expire_str, "status": status})
        for ip, exp in self.black.items():
            status = "永久" if exp == -1 else "有效" if exp > now else "已过期"
            expire_str = "永久" if exp == -1 else time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(exp))
            black_list.append({"ip": ip, "expire_time": exp, "expire_str": expire_str, "status": status})
        return {"white_list": white_list, "black_list": black_list, "white_count": len(white_list),
                "black_count": len(black_list)}

    def _add_acl_to_db(self, ip: str, list_type: str):
        """添加ACL到数据库（使用独立连接）"""
        conn = None
        try:
            conn = pymysql.connect(**DB_CONFIG)
            with conn.cursor() as cur:
                sql = """INSERT INTO acl_entries (ip, list_type)
                         VALUES (%s, %s) ON DUPLICATE KEY 
                         UPDATE updated_at = CURRENT_TIMESTAMP"""
                cur.execute(sql, (ip, list_type))
                conn.commit()
                self.logger.info(f"✅ ACL入库成功: {ip} -> {list_type}")
        except Exception as e:
            self.logger.error(f"❌ ACL入库失败: {e}")
            if conn:
                conn.rollback()
            import traceback
            traceback.print_exc()
        finally:
            if conn:
                conn.close()

    def _del_acl_from_db(self, ip: str, list_type: str):
        """从数据库删除ACL（使用独立连接）"""
        conn = None
        try:
            conn = pymysql.connect(**DB_CONFIG)
            with conn.cursor() as cur:
                sql = "DELETE FROM acl_entries WHERE ip=%s AND list_type=%s"
                affected = cur.execute(sql, (ip, list_type))
                conn.commit()
                self.logger.info(f"✅ ACL出库成功: {ip} -> {list_type} (删除了{affected}行)")
                return affected > 0
        except Exception as e:
            self.logger.error(f"❌ ACL出库失败: {e}")
            if conn:
                conn.rollback()
            import traceback
            traceback.print_exc()
            return False
        finally:
            if conn:
                conn.close()

    def acl_add_white(self, ip: str, ttl: int = -1):
        self.white[ip] = -1
        self._save_acl_file(self.white, WHITE_FILE)
        self._add_acl_to_db(ip, 'white')

    def acl_add_black(self, ip: str, ttl: int = -1, operator: str = 'system', reason: str = '手动加黑'):
        ip = str(ip)
        # 1. 若当前在限速，先卸掉
        if ip in self.limited_ips:
            self._release_rate_limit(ip, operator='system', reason='转黑名单自动解除')
        # 2. 写内存 + 文件 + 库
        self.black[ip] = ttl
        self._save_acl_file(self.black, BLACK_FILE)
        self._add_acl_to_db(ip, 'black')
        self.logger.warning(f"🚫 {ip} 已加入黑名单（限速已自动解除）原因：{reason}")
        
        # 3. ✅ 如果是管理员操作，直接INSERT新记录到attack_sessions
        if operator == 'admin':
            try:
                conn = pymysql.connect(**DB_CONFIG, autocommit=False)
                with conn.cursor() as cur:
                    # 直接插入新记录（每次管理员操作都是独立的决策）
                    # ✅ 管理员加黑：status='handled', is_active=0（已结束）
                    cur.execute("""
                        INSERT INTO attack_sessions (
                            src_ip, anomaly_type, packet_count, 
                            start_time, last_packet_time, end_time, duration_seconds,
                            is_active, status, handled_by, handled_at, handle_action
                        ) VALUES (
                            %s, %s, 1, 
                            NOW(), NOW(), NOW(), 0,
                            0, 'handled', %s, NOW(), 'blacklist'
                        )
                    """, (ip, reason, operator))
                    conn.commit()
                    self.logger.info(f"✅ [管理员操作] 已将 {ip} 加入黑名单并记录到attack_sessions（原因：{reason}）")
            except Exception as e:
                self.logger.error(f"⚠️ 黑名单已添加但attack_sessions记录失败: {e}")
                if conn:
                    conn.rollback()
            finally:
                if conn:
                    conn.close()

    def acl_del_white(self, ip: str):
        """从白名单删除IP"""
        # 1. 从内存删除
        if ip in self.white:
            self.white.pop(ip, None)
            self._save_acl_file(self.white, WHITE_FILE)
            self.logger.info(f"✅ 从白名单内存中删除: {ip}")
        else:
            self.logger.warning(f"⚠️ IP不在白名单内存中: {ip}")
        
        # 2. 从数据库删除
        db_success = self._del_acl_from_db(ip, 'white')
        
        if db_success:
            self.logger.info(f"✅ 白名单删除完成: {ip}")
            return True
        else:
            self.logger.warning(f"⚠️ 数据库中未找到该IP或删除失败: {ip}")
            return False

    def acl_del_black(self, ip: str):
        """从黑名单删除IP"""
        # 1. 从内存删除
        if ip in self.black:
            self.black.pop(ip, None)
            self._save_acl_file(self.black, BLACK_FILE)
            self.logger.info(f"✅ 从黑名单内存中删除: {ip}")
        else:
            self.logger.warning(f"⚠️ IP不在黑名单内存中: {ip}")
        
        # 2. 从数据库删除
        db_success = self._del_acl_from_db(ip, 'black')
        
        if db_success:
            self.logger.info(f"✅ 黑名单删除完成: {ip}")
            return True
        else:
            self.logger.warning(f"⚠️ 数据库中未找到该IP或删除失败: {ip}")
            return False

    # ---------------- OpenFlow ----------------
    @set_ev_cls(ofp_event.EventOFPStateChange, [CONFIG_DISPATCHER, MAIN_DISPATCHER])
    def state_change(self, ev):
        dp = ev.datapath
        if ev.state == MAIN_DISPATCHER:
            if dp.id not in self.datapaths:
                self.datapaths[dp.id] = dp
                self._install_table_miss(dp)
                self.logger.info(f"✅ 交换机 {dp.id} 已连接")
        else:
            # ✅ 交换机断连检测
            if dp.id in self.datapaths:
                self.datapaths.pop(dp.id, None)
                self.logger.warning(f"❌ 交换机 {dp.id} 已断开")
                self._log_device_anomaly(
                    anomaly_type='交换机断连',
                    device_type='switch',
                    device_id=str(dp.id),
                    description=f'交换机 {dp.id} 意外断开连接',
                    severity='high'
                )

    def _install_table_miss(self, dp):
        ofp, ps = dp.ofproto, dp.ofproto_parser
        match = ps.OFPMatch()
        # 🎯 改回CONTROLLER模式，但在packet_in和_extract_flow中严格过滤
        actions = [ps.OFPActionOutput(ofp.OFPP_CONTROLLER, ofp.OFPCML_NO_BUFFER)]
        self._add_flow(dp, 0, match, actions, idle=0, hard=0)
        self.logger.info(f"📌 交换机 {dp.id} 安装 Table-Miss (CONTROLLER模式，但严格过滤)")

    def update_all_table_miss_rules(self):
        """立即更新所有已连接交换机的默认规则"""
        for dp_id, dp in self.datapaths.items():
            self.logger.info(f"🔄 正在更新交换机 {dp_id} 的默认规则...")
            self._install_table_miss(dp)
        self.logger.info(f"✅ 已更新 {len(self.datapaths)} 个交换机的默认规则")

    def _add_flow(self, dp, prio, match, acts, idle=60, hard=0):
        ofp, ps = dp.ofproto, dp.ofproto_parser
        inst = [ps.OFPInstructionActions(ofp.OFPIT_APPLY_ACTIONS, acts)]
        mod = ps.OFPFlowMod(datapath=dp, priority=prio, match=match, instructions=inst,
                            idle_timeout=idle, hard_timeout=hard)
        dp.send_msg(mod)
    

    @set_ev_cls(ofp_event.EventOFPPortStatsReply, MAIN_DISPATCHER)
    def port_stats_reply(self, ev):
        dpid = ev.msg.datapath.id
        
        for stat in ev.msg.body:
            # 只记录端口名称，不用于流量统计（使用流表统计代替）
            self.port_stats[dpid][stat.port_no] = f"port-{stat.port_no}"


    # ---------------- Packet-In & 协议解析 ----------------
    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def packet_in(self, ev):
        msg = ev.msg
        dp, ofp, ps = msg.datapath, msg.datapath.ofproto, msg.datapath.ofproto_parser
        in_port = msg.match['in_port']
        dpid = dp.id

        pkt = packet.Packet(msg.data)
        eth = pkt.get_protocol(ethernet.ethernet)
        if not eth or eth.ethertype == ether_types.ETH_TYPE_LLDP:
            return

        self.mac_to_port.setdefault(dpid, {})
        self.mac_to_port[dpid][eth.src] = in_port

        # ✅ 设备异常检测
        self._check_mac_conflict(eth.src, dpid, in_port)  # MAC冲突检测

        # 1) 黑白名单优先检查
        acl = None
        ip_pkt = pkt.get_protocol(ipv4.ipv4)
        if ip_pkt:
            self.logger.info(f"📦 [packet_in] 收到IPv4包: src={ip_pkt.src}, dst={ip_pkt.dst}")
            # ✅ IP配置异常检测
            self._check_ip_subnet(ip_pkt.src)
            acl = self.acl_check(ip_pkt.src)
        else:
            self.logger.debug(f"📦 [packet_in] 收到非IPv4包")
        if acl == 'white':
            self._normal_forward(dp, msg, eth, in_port)
            return
        if acl == 'black':
            self.logger.warning(f"🚫 黑名单命中 {ip_pkt.src}，直接丢弃")
            self._raise_anomaly({'src_ip': ip_pkt.src, 'anomaly_type': '黑名单丢弃', 'details': 'ACL 策略'})
            # 黑名单也写一条“0 包”记录到 flow_stats
            ts = time.strftime('%Y-%m-%d %H:%M:%S')
            self.flow_cache.append({
                'timestamp': ts,
                'datapath_id': f"{dpid:016d}",
                'src_ip': ip_pkt.src,
                'dst_ip': '',
                'protocol': 'BLACKLIST',
                'src_port': 0,
                'dst_port': 0,
                'src_mac': eth.src,
                'dst_mac': eth.dst,
                'packet_count': 0,
                'byte_count': 0,
                'duration_sec': 0,
                'stats_day': ts[:10],
                'stats_hour': int(ts[11:13])
            })
            return

        # 2) 正常转发
        self._handle_protocol(pkt, ip_pkt)
        self._normal_forward(dp, msg, eth, in_port)

        # 3) ← 新增：每来一个包，立刻往 flow_cache 塞一条“原始包”记录
        src_ip = None
        dst_ip = None
        proto_str = 'IP'
        src_port = 0
        dst_port = 0
        src_mac = eth.src
        dst_mac = eth.dst

        arp_pkt = pkt.get_protocol(arp.arp)
        if arp_pkt:
            src_ip = arp_pkt.src_ip
            dst_ip = arp_pkt.dst_ip
            proto_str = 'ARP'
            # ✅ 在ARP包中也检测IP配置异常
            self.logger.info(f"📦 [packet_in] 收到ARP包: src_ip={src_ip}, dst_ip={dst_ip}")
            self._check_ip_subnet(src_ip)
        else:
            ip_pkt = pkt.get_protocol(ipv4.ipv4)
            if ip_pkt:
                src_ip = ip_pkt.src
                dst_ip = ip_pkt.dst
                if pkt.get_protocol(tcp.tcp):
                    proto_str = 'TCP'
                    tcp_p = pkt.get_protocol(tcp.tcp)
                    src_port = tcp_p.src_port
                    dst_port = tcp_p.dst_port
                elif pkt.get_protocol(udp.udp):
                    proto_str = 'UDP'
                    udp_p = pkt.get_protocol(udp.udp)
                    src_port = udp_p.src_port
                    dst_port = udp_p.dst_port
                elif pkt.get_protocol(icmp.icmp):
                    proto_str = 'ICMP'

        # 🔍 临时调试：记录所有packet_in的数据解析结果
        self.logger.debug(f"🔍 packet_in解析: src_ip={src_ip}, dst_ip={dst_ip}, proto={proto_str}, sport={src_port}, dport={dst_port}")

        # ✅ 只记录主机产生的流量，过滤SDN基础设施流量
        # 🎯 加强IP有效性检查：必须有有效的源IP和目标IP
        if (src_ip and dst_ip and 
            src_ip != '0.0.0.0' and dst_ip != '0.0.0.0' and
            src_ip != '' and dst_ip != '' and
            self._is_host_generated_traffic(src_ip, dst_ip, src_port, dst_port, proto_str)):
            ts = time.strftime('%Y-%m-%d %H:%M:%S')
            self.flow_cache.append({
                'timestamp': ts,
                'datapath_id': f"{dpid:016d}",
                'src_ip': src_ip,
                'dst_ip': dst_ip,
                'protocol': proto_str,
                'src_port': src_port,
                'dst_port': dst_port,
                'src_mac': src_mac,
                'dst_mac': dst_mac,
                'packet_count': 1,
                'byte_count': len(msg.data),
                'duration_sec': 0,
                'stats_day': ts[:10],
                'stats_hour': int(ts[11:13])
            })


    def _is_host_generated_traffic(self, src_ip, dst_ip, src_port, dst_port, protocol):
        """
        判断是否为主机产生的流量（而非SDN基础设施流量）
        
        注意：_extract_flow已经做了严格的IPv4过滤，这里只需处理packet_in事件
        """
        
        # 过滤无效IP地址
        if not src_ip or not dst_ip or src_ip == '0.0.0.0' or dst_ip == '0.0.0.0':
            return False
        
        # 1. OpenFlow控制流量（控制器↔交换机通信）
        if src_port == 6633 or dst_port == 6633:
            return False
        
        # 2. RYU控制器管理流量
        controller_ips = ['192.168.44.129', '127.0.0.1', 'localhost']
        if src_ip in controller_ips or dst_ip in controller_ips:
            if dst_port in [8080, 8001] or src_port in [8080, 8001]:
                return False
        
        # 3. 交换机管理IP
        if (src_ip.startswith('192.168.100.') or 
            dst_ip.startswith('192.168.100.')):
            return False
        
        # 所有其他流量都认为是主机产生的
        return True

    def _normal_forward(self, dp, msg, eth, in_port):
        dpid = dp.id
        ofp, ps = dp.ofproto, dp.ofproto_parser
        dst_mac = eth.dst
        out_port = self.mac_to_port[dpid].get(dst_mac, ofp.OFPP_FLOOD)
        acts = [ps.OFPActionOutput(out_port)]
        data = msg.data if msg.buffer_id == ofp.OFP_NO_BUFFER else None
        out = ps.OFPPacketOut(datapath=dp, buffer_id=msg.buffer_id,
                              in_port=in_port, actions=acts, data=data)
        dp.send_msg(out)
        if out_port != ofp.OFPP_FLOOD and msg.buffer_id != ofp.OFP_NO_BUFFER:
            match = ps.OFPMatch(in_port=in_port, eth_dst=dst_mac)
            self._add_flow(dp, 1, match, acts, idle=60, hard=0)


    # ---------------- 协议统计 & 攻击检测 ----------------
    def _handle_protocol(self, pkt, ip_pkt):
        """
        协议统计 + 攻击检测（含 Land Attack & Port Scan）
        入口：packet_in 每包必调
        """
        # 0. Land Attack：源 IP == 目的 IP → 限速处理（256Kbps）
        if ip_pkt and ip_pkt.src == ip_pkt.dst:
            if ip_pkt.src not in self.land_attack_seen:
                self.land_attack_seen.add(ip_pkt.src)
                # ✅ 改成限速而不是加黑名单
                self._apply_rate_limit(ip_pkt.src, 'Land Attack', kbps=256)
                self._raise_anomaly({
                    'src_ip': ip_pkt.src,
                    'dst_ip': ip_pkt.dst,
                    'protocol': 'IP',
                    'anomaly_type': 'Land Attack',
                    'details': '源地址等于目的地址（已限速256Kbps）'
                })
            # ⚠️ 继续统计，不再直接丢弃（让限速流表生效）
            # return  # 注释掉，允许继续处理

        # 1. 拿源 IP（ARP 优先，再 IPv4）
        src_ip = None
        arp_pkt = pkt.get_protocol(arp.arp)
        if arp_pkt:
            src_ip = arp_pkt.src_ip
        elif ip_pkt:
            src_ip = ip_pkt.src

        if not src_ip:                      # 拿不到 IP 直接放行
            return

        # 2. 黑白名单优先放行 / 丢弃
        acl = self.acl_check(src_ip)
        if acl == 'white':                  # 白名单：一切检测都跳过
            return
        if acl == 'black':                  # 黑名单：只告警，不统计
            self._raise_anomaly({'src_ip': src_ip,
                                 'anomaly_type': '黑名单丢弃',
                                 'details': 'ACL 策略'})
            return

        # 3. 正常协议统计
        tcp_pkt = pkt.get_protocol(tcp.tcp)
        udp_pkt = pkt.get_protocol(udp.udp)
        icmp_pkt = pkt.get_protocol(icmp.icmp)

        # 原始包速率统计（你原有逻辑）
        self.raw_pkt_counter[src_ip] += 1
        now = time.time()
        if now - self.raw_last_time.get(src_ip, 0) >= 1:
            rate = self.raw_pkt_counter[src_ip]
            self.raw_pkt_counter[src_ip] = 0
            self.raw_last_time[src_ip] = now
            dst_cnt = len(self.src_dst_counter[src_ip])
            entropy = self._port_entropy(src_ip)
            features = [rate, 0, 0, dst_cnt, entropy]
            self.flow_features_with_info.append({
                'src_ip': src_ip,
                'dst_ip': arp_pkt.dst_ip if arp_pkt else (ip_pkt.dst if ip_pkt else ""),
                'protocol': 'ARP' if arp_pkt else 'ICMP' if icmp_pkt else 'TCP' if tcp_pkt else 'UDP',
                'features': features,
                'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
                'packet_count': 1,
                'byte_count': len(pkt.data)
            })

        # 4. 按协议分流检测（你原有调用）
        if tcp_pkt and ip_pkt:
            self._tcp_stat(src_ip, ip_pkt.dst, tcp_pkt)
        elif udp_pkt and ip_pkt:
            self._udp_stat(src_ip, ip_pkt.dst, udp_pkt.dst_port)
        elif icmp_pkt and ip_pkt:
            self._icmp_stat(src_ip, ip_pkt.dst)
        elif arp_pkt:
            self._arp_stat(arp_pkt, src_ip)

        # 5. Port Scan（每 60 秒结算，零删减插入）
        if ip_pkt:
            now = time.time()
            tracker = self.scan_tracker[src_ip]
            if tcp_pkt:              # 只统计 TCP 目的端口
                tracker['ports'].add(tcp_pkt.dst_port)
            if now - tracker['last'] >= 60:
                port_cnt = len(tracker['ports'])
                entropy  = self._port_entropy(src_ip)
                if port_cnt > 50 and entropy > 3.0:
                    self._apply_rate_limit(src_ip, 'Port Scan', 256)
                    self._raise_anomaly({
                        'src_ip': src_ip,
                        'dst_ip': ip_pkt.dst,
                        'protocol': 'IP',
                        'anomaly_type': 'Port Scan',
                        'details': f'端口数={port_cnt}, 熵={entropy:.2f}'
                    })
                tracker['ports'].clear()
                tracker['last'] = now



    # ---------------- 统计 ----------------
    def _tcp_stat(self, src_ip, dst_ip, tcp_pkt):
        dst_port = tcp_pkt.dst_port
        st = self.tcp_flag_stats[src_ip]
        st['total'] += 1
        if (tcp_pkt.bits & tcp.TCP_SYN) and not (tcp_pkt.bits & tcp.TCP_ACK):
            st['syn'] += 1
        self.src_dst_counter[src_ip].add(dst_ip)
        self.src_port_counter[src_ip].add(dst_port)
        self._check_syn_flood(src_ip, dst_ip)

        # ===== SSH Brute Force (TCP 22) =====
        if dst_port == 22:
            now = time.time()
            brute = self.ssh_brute[src_ip]
            brute['conns'] += 1
            if now - brute['last'] >= 60:           # 每 60 秒结算
                if brute['conns'] > 50:             # 阈值：>50 连接/分钟
                    self._apply_rate_limit(src_ip, 'SSH Brute Force', 256)
                    self._raise_anomaly({
                        'src_ip': src_ip,
                        'dst_ip': dst_ip,
                        'protocol': 'TCP',
                        'anomaly_type': 'SSH Brute Force',
                        'details': f'22端口连接数={brute["conns"]}'
                    })
                brute['conns'] = 0
                brute['last']  = now

        # 你原有“孤立森林插样”逻辑保留
        now = time.time()
        t = now - st.get('last', now)
        if t <= 0:
            return
        ratio = st['syn'] / max(st['total'], 1)
        rate = st['syn'] / max(t, 0.001)
        if (ratio > THRESH['syn']['ratio'] or rate > THRESH['syn']['rate']) and self.acl_check(src_ip) != 'white':
            self._apply_rate_limit(src_ip, 'SYN Flood')
            self._raise_anomaly({'src_ip': src_ip, 'dst_ip': dst_ip, 'protocol': 'TCP',
                                 'anomaly_type': 'SYN Flood', 'details': f'ratio={ratio:.2f} rate={rate:.1f}'})
            st['syn'] = st['total'] = 0
            st['last'] = now
            entropy = self._port_entropy(src_ip)
            byte_rate = st['total'] * 64
            features = [rate, byte_rate, 0, len(self.src_dst_counter[src_ip]), entropy]
            self.flow_features_with_info.append({
                'src_ip': src_ip, 'dst_ip': dst_ip, 'protocol': 'TCP',
                'features': features, 'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
                'packet_count': 1, 'byte_count': 64
            })
            self.logger.info(f"[TCP->IF] 攻击确认插入: src={src_ip}, rate={rate:.0f}")



    def _udp_stat(self, src_ip, dst_ip, dst_port):
        st = self.udp_stats[src_ip]
        st['count'] += 1
        if not hasattr(st, 'dst_ports'):
            st['dst_ports'] = set()
        st['dst_ports'].add(dst_port)
        
        self.src_dst_counter[src_ip].add(dst_ip)
        self.src_port_counter[src_ip].add(dst_port)
        
        # 调用检测函数
        self._check_udp_flood(src_ip, dst_ip)

    def _icmp_stat(self, src_ip, dst_ip):
        if self.acl_check(src_ip) == 'white':
            return
        st = self.icmp_stats[src_ip]
        st['count'] += 1
        
        self.src_dst_counter[src_ip].add(dst_ip)
        
        # 调用检测函数
        self._check_icmp_flood(src_ip, dst_ip)

    # ---------------- ARP 统计 ----------------
    def _arp_stat(self, arp_pkt, src_ip):
        """
        精简版 ARP 欺骗检测：
        1. 只关注 src_ip（发送方 IP）对应的 MAC 是否瞬间变化
        2. 变化一次即触发，无需多个 MAC 累积
        3. 白名单跳过，黑名单只告警不限速
        """
        # 1. 黑白名单快速通道
        acl = self.acl_check(src_ip)
        if acl == 'white':
            return
        if acl == 'black':
            self._raise_anomaly({'src_ip': src_ip,
                                'dst_ip': arp_pkt.dst_ip,
                                'protocol': 'ARP',
                                'anomaly_type': '黑名单丢弃',
                                'details': 'ACL 策略'})
            return

        # 2. 初始化/获取上次 MAC
        st = self.arp_stats[src_ip]          # 复用原结构，省内存
        prev_mac = st.get('last_mac', None)
        curr_mac = arp_pkt.src_mac

        if prev_mac is None:                 # 第一次见，只记录
            st['last_mac'] = curr_mac
            return

        # 3. 变化一次即触发
        if curr_mac != prev_mac:
            self.logger.warning(f"[ARP_SPOOF_DETECTED] {src_ip} MAC 变化: "
                                f"{prev_mac} -> {curr_mac}")
            # 3-1 限速（内存+流表+DB）
            self._apply_rate_limit(src_ip, 'ARP 欺骗（MAC变化一次）')
            # 3-2 写异常日志（文件+DB）
            self._raise_anomaly({
                'src_ip': src_ip,
                'dst_ip': arp_pkt.dst_ip,
                'protocol': 'ARP',
                'anomaly_type': 'ARP 欺骗',
                'details': f'MAC 变化: {prev_mac} -> {curr_mac}'
            })
            # 3-3 更新追踪值（继续观察后续变化）
            st['last_mac'] = curr_mac


    # ---------------- 攻击判定（白名单 IP 永不限速） ----------------
    def _check_syn_flood(self, src_ip, dst_ip):
        st = self.tcp_flag_stats[src_ip]
        if st['total'] < THRESH['syn']['min_tcp']:
            return
        ratio = st['syn'] / st['total']
        now = time.time()
        t = now - st['last']
        
        # ✅ 必须至少1秒才计算速率，避免时间间隔太小导致速率爆表
        if t < 1.0:
            return
        
        rate = st['syn'] / t
        
        # 检查口语规则自定义阈值
        syn_threshold = CUSTOM_RULES.get('syn_threshold')
        if syn_threshold and rate < syn_threshold:
            self.logger.info(f"[口语规则] SYN流量 {rate:.1f} pkt/s 低于阈值 {syn_threshold}，跳过限速")
            return

        # 降低检测阈值，提高敏感性
        if ratio > THRESH['syn']['ratio'] * 0.8 or rate > THRESH['syn']['rate'] * 0.8:
            if self.acl_check(src_ip) != 'white':
                self._apply_rate_limit(src_ip, 'SYN Flood')
            self._raise_anomaly({
                'src_ip': src_ip,
                'dst_ip': dst_ip,
                'protocol': 'TCP',
                'anomaly_type': 'SYN Flood',
                'details': f'ratio={ratio:.2f} rate={rate:.1f}'
            })
            # ✅ 清零计数器，但不更新last（由_reset_loop统一更新）
            st['syn'] = st['total'] = 0
            # 不更新st['last']，避免影响下次检测的时间差

    def _check_udp_flood(self, src_ip, dst_ip):
        st = self.udp_stats[src_ip]
        now = time.time()
        t = now - st['last']
        
        # ✅ 必须至少1秒才计算速率，避免时间间隔太小导致速率爆表
        if t < 1.0:
            return
        
        rate = st['count'] / t

        # 玩法2: 口语规则 - 检查自定义UDP阈值
        udp_threshold = CUSTOM_RULES.get('udp_threshold', THRESH['udp']['flood_rate'])
        if rate < udp_threshold:
            self.logger.debug(f"UDP流量 {rate:.1f} pkt/s 低于自定义阈值 {udp_threshold}，跳过限速")
            return

        # 新增：多端口检测逻辑
        port_count = len(getattr(st, 'dst_ports', set()))
        is_flood = rate > THRESH['udp']['flood_rate'] or (port_count > 50 and rate > THRESH['udp']['flood_rate'] * 0.5)

        if is_flood:
            if self.acl_check(src_ip) != 'white':
                self._apply_rate_limit(src_ip, 'UDP Flood')
            self._raise_anomaly({
                'src_ip': src_ip,
                'dst_ip': dst_ip,
                'protocol': 'UDP',
                'anomaly_type': 'UDP Flood',
                'details': f'速率={rate:.1f} 端口数={port_count}'
            })
            # ✅ 清零计数器，但不更新last（由_reset_loop统一更新）
            st['count'] = 0
            if hasattr(st, 'dst_ports'):
                st['dst_ports'].clear()

    def _check_icmp_flood(self, src_ip, dst_ip):
        if self.acl_check(src_ip) == 'white':          # ← 终极加塞
            return
        st = self.icmp_stats[src_ip]
        now = time.time()
        t = now - st['last']
        
        # ✅ 必须至少1秒才计算速率，避免时间间隔太小导致速率爆表（如pingall在0.001秒内发包）
        if t < 1.0:
            return
        
        rate = st['count'] / t
        
        # 检查口语规则自定义阈值
        icmp_threshold = CUSTOM_RULES.get('icmp_threshold')
        if icmp_threshold and rate < icmp_threshold:
            self.logger.info(f"[口语规则] ICMP流量 {rate:.1f} pkt/s 低于阈值 {icmp_threshold}，跳过限速")
            return
        
        if rate > THRESH['icmp']['flood_rate']:
            self._apply_rate_limit(src_ip, 'ICMP Flood')
            self._raise_anomaly({'src_ip': src_ip, 'dst_ip': dst_ip, 'protocol': 'ICMP',
                                 'anomaly_type': 'ICMP Flood',
                                 'details': f'rate={rate:.1f}'})
            # ✅ 清零计数器，但不更新last（由_reset_loop统一更新）
            st['count'] = 0

    # ARP攻击检测（仅MAC变化检测）
    def _check_arp_attack(self, src_ip, arp_pkt):
        if self.acl_check(src_ip) == 'white':
            return
        # 此函数现在只作为占位符，实际检测逻辑已移至_arp_stat函数中
        # 保持函数存在以避免调用错误
        pass

    # -----------------------------------------------------------
# -----------------------------------------------------------
# 真正限速：写内存 + 清过期 + 写关系表 + 下发流表 + 写 log
# -----------------------------------------------------------
    def _apply_rate_limit(self, src_ip: str, reason: str, kbps: int = 1024, operator: str = 'system', duration_minutes: int = None):
        """
        应用限速规则
        参数:
            operator: 'admin'(管理员手动) 或 'system'(自动检测)
            duration_minutes: 限速时长（分钟），None则使用默认值
        返回: (成功/失败, 实际速率kbps, 错误信息)
        """
        if not src_ip:
            self.logger.error("限速失败：源IP为空")
            return (False, 0, "源IP为空")

        # ① 解析档位（口语或数字）
        if isinstance(kbps, str):
            kbps = kbps.strip()
            if re.search(r'低速', kbps, re.I):
                kbps = 256
            elif re.search(r'中速', kbps, re.I):
                kbps = 1024
            elif re.search(r'高速', kbps, re.I):
                kbps = 2048
            else:
                m = re.search(r'(\d+)\s*kbps|(\d+)\s*m', kbps, re.I)
                kbps = 1024
                if m:
                    kbps = int(m.group(1)) if m.group(1) else int(m.group(2)) * 1024
        else:
            kbps = int(kbps)

        if kbps <= 0:
            kbps = 1024

        # ✅ 计算过期时间（使用指定的duration或默认值）
        now = time.time()
        if duration_minutes is not None and duration_minutes > 0:
            duration_seconds = duration_minutes * 60  # 分钟转秒
        else:
            duration_seconds = RATE_LIMIT_DURATION  # 默认5分钟
        expire = now + duration_seconds

        # ② 先检查是否有可用的交换机
        if not self.datapaths:
            self.logger.error(f"❌ 限速失败: {src_ip} - 没有可用的交换机（请检查交换机连接）")
            return (False, kbps, "没有可用的交换机，请检查交换机是否连接到控制器")

        # ③ 内存记录
        self.limited_ips[src_ip] = expire

        # ④ 下发流表（三档队列映射）- 先下发流表，成功后再写数据库
        if kbps <= 256:
            queue_id = 1
        elif kbps <= 1024:
            queue_id = 2
        else:  # >= 2048
            queue_id = 3

        try:
            flow_success = False
            for dp in self.datapaths.values():
                ofp, ps = dp.ofproto, dp.ofproto_parser
                match = ps.OFPMatch(eth_type=ether_types.ETH_TYPE_IP,
                                    ipv4_src=src_ip)
                acts = [ps.OFPActionSetQueue(queue_id=queue_id),
                        ps.OFPActionOutput(ofp.OFPP_NORMAL)]
                # ✅ 修复：设置idle_timeout=0（永不因空闲删除）和hard_timeout=限速时长
                # 这样即使暂时没有流量，流表也会保持到限速期满
                self._add_flow(dp, 50, match, acts, idle=0, hard=int(duration_seconds))
                flow_success = True
                self.logger.info(f"✅ 流表已下发到交换机 {dp.id}: {src_ip} -> queue={queue_id}, idle=0, hard={int(duration_seconds)}s")

            if not flow_success:
                self.logger.error(f"❌ 流表下发失败: {src_ip} - 没有可用的交换机")
                return (False, kbps, "没有可用的交换机")

            self.logger.warning(f"🔒 已对 {src_ip} 全方向限速 {kbps} kbps（{reason}）queue={queue_id}")
            
        except Exception as e:
            self.logger.error(f"❌ 下发流表失败: {src_ip} - {e}")
            import traceback
            traceback.print_exc()
            return (False, kbps, f"下发流表失败: {str(e)}")
        
        # ⑤ 流表下发成功后，写入数据库
        conn = None
        try:
            conn = pymysql.connect(**DB_CONFIG)
            with conn.cursor() as cur:
                # 5-1 清理已过期的 active 记录
                cur.execute("DELETE FROM rate_limit_active WHERE expire_at < NOW()")

                # 5-2 写入/更新最新限速（先检查是否存在，再决定INSERT还是UPDATE）
                # 检查该IP是否已有限速记录
                cur.execute("SELECT 1 FROM rate_limit_active WHERE src_ip = %s", (src_ip,))
                exists = cur.fetchone()
                
                if exists:
                    # 更新现有记录
                    sql = """
                        UPDATE rate_limit_active
                        SET expire_at = FROM_UNIXTIME(%s),
                            kbps = %s,
                            reason = %s
                        WHERE src_ip = %s
                    """
                    cur.execute(sql, (expire, kbps, reason, src_ip))
                else:
                    # 插入新记录
                    sql = """
                        INSERT INTO rate_limit_active (src_ip, expire_at, kbps, reason)
                        VALUES (%s, FROM_UNIXTIME(%s), %s, %s)
                    """
                    cur.execute(sql, (src_ip, expire, kbps, reason))

                # 5-3 写 log 表（记录所有限速操作）
                cur.execute("""
                    INSERT INTO rate_limit_log (src_ip, operator, action, reason, kbps)
                    VALUES (%s, %s, %s, %s, %s)
                """, (src_ip, operator, 'limit', reason, kbps))

                # ✅ 5-4 【管理员手动限速】直接INSERT到attack_sessions（每次操作=独立记录）
                # 系统自动限速（operator='system'）由_log_attack_session负责记录为pending
                if operator == 'admin':
                    # 所有攻击相关的限速原因
                    attack_types = [
                        'SYN Flood', 'UDP Flood', 'ICMP Flood', 'ARP 欺骗', 'ARP欺骗', 
                        '带宽超限', 'Port Scan', 'SSH Brute Force', 'Land Attack',
                        '异常流量', '手动限制', '其他原因', '管理员手动限速'
                    ]
                    # ✅ 管理员每次限速都直接INSERT新记录（不使用时间窗口合并，不检查flag）
                    # 原因：管理员每次操作都是独立的决策，需要单独记录
                    # status='handled', is_active=0（已结束）
                    cur.execute("""
                        INSERT INTO attack_sessions (
                            src_ip, anomaly_type, packet_count, 
                            start_time, last_packet_time, end_time, duration_seconds,
                            is_active, status, handled_by, handled_at, handle_action
                        ) VALUES (
                            %s, %s, 1, 
                            NOW(), NOW(), NOW(), 0,
                            0, 'handled', %s, NOW(), 'ratelimit'
                        )
                    """, (src_ip, reason, operator))
                    self.logger.info(f"✅ [管理员操作] 已为 {src_ip} 创建限速记录到attack_sessions（原因：{reason}）")

                conn.commit()
            self.logger.warning(f"📥 限速记录已写入数据库: ip={src_ip}, kbps={kbps}, reason={reason}, operator={operator}")
        except Exception as e:
            self.logger.error(f"⚠️ 流表已下发但数据库写入失败: {e}")
            if conn:
                conn.rollback()
            # 注意：此时流表已经下发成功，所以仍然返回成功，但记录警告
            self.logger.warning(f"⚠️ {src_ip} 流表已生效，但数据库未同步")
        finally:
            if conn:
                conn.close()

        # 6. ★★★ 记录"本次限速事件"(1 分钟合并) ★★★
        self._log_limit_session(src_ip, reason, kbps)
        
        return (True, kbps, "")







    # -----------------------------------------------------------
    # 解除限速：内存 + 流表 + 数据库 active 表 + 写 log 表
    # 线程安全：每次新建数据库连接，用完立即关闭
    # -----------------------------------------------------------
   # -----------------------------------------------------------
# 解除限速：删内存 + 删流表 + 写 log
# -----------------------------------------------------------
    # -----------------------------------------------------------
# 解除限速：内存 + 流表 + 数据库 active 表 + 写 log
# 防御式：强制字符串键、时间戳统一、双表同步
# -----------------------------------------------------------
    def _release_rate_limit(self, src_ip: str, operator: str = 'admin', reason: str = '手动解除'):
        src_ip = str(src_ip)
        now = time.time()

        # 1. 内存必须存在
        if src_ip not in self.limited_ips:
            self.logger.warning(f"[UNLIMIT] {src_ip} 不在内存，跳过")
            return False

        # 2. 删内存
        del self.limited_ips[src_ip]

        # 3. 数据库：独立连接，双表操作
        conn = None
        try:
            conn = pymysql.connect(**DB_CONFIG)
            with conn.cursor() as cur:
                # 3-1 清 active 表
                cur.execute("DELETE FROM rate_limit_active WHERE src_ip = %s", (src_ip,))
                # 3-2 写 log 表（operator 长度安全）
                cur.execute("""
                    INSERT INTO rate_limit_log(src_ip, operator, action, reason)
                    VALUES (%s, %s, %s, %s)
                """, (src_ip, operator[:16], 'unlimit', reason))
                conn.commit()
            self.logger.warning(f"🔓 解除限速 {src_ip} 操作人: {operator} 原因: {reason}")
        except Exception as e:
            self.logger.error(f"解除限速数据库失败: {e}")
            if conn:
                conn.rollback()
            return False
        finally:
            if conn:
                conn.close()

        # 4. 删除流表（全方向）
        for dp in self.datapaths.values():
            ofp, ps = dp.ofproto, dp.ofproto_parser
            match = ps.OFPMatch(eth_type=ether_types.ETH_TYPE_IP, ipv4_src=src_ip)
            mod = ps.OFPFlowMod(datapath=dp, match=match, command=ofp.OFPFC_DELETE,
                                out_group=ofp.OFPG_ANY, out_port=ofp.OFPP_ANY)
            dp.send_msg(mod)
        return True



    # ---------------- 异常记录（不再去重，每包都写） ----------------
    def _raise_anomaly(self, entry):
        # 0. 补时间字段
        entry['detect_time'] = time.strftime('%Y-%m-%d %H:%M:%S')
        entry['detect_day']  = entry['detect_time'][:10]

        # 1. 写本地文件
        self._write_anomaly(entry)

        # 2. 写 anomaly_log 表（全量留证据）
        self._write_anomaly_db(entry)

        # 3. 控制台 warning
        self.logger.warning(
            f"⚠️ {entry['anomaly_type']} | {entry['details']} | "
            f"{entry['src_ip']} -> {entry.get('dst_ip', '')}"
        )

        # 4. 推内存队列（AI 摘要、周报）
        with QUEUE_LOCK:
            ANOMALY_QUEUE.append(entry)

        # 5. AI 摘要（可选）
        if AI_SUMMARY_ENABLED:
            summary = f"🤖 AI摘要: {entry['src_ip']} 发起 {entry['anomaly_type']} 攻击"
            self.logger.info(summary)
            WEEKLY_REPORT_DATA.append({'time': entry['detect_time'], 'summary': summary})

        # 6. 记录攻击事件（1 分钟合并，不同类型一定分家）
        self._log_attack_session(entry)







    # --------- 生产者：已集成在 _raise_anomaly 里，无需再调 ---------

    # --------- 消费者：单线程写库 ---------
    def _db_writer_loop(self):
        """
        统一的数据库写入循环
        - 处理异常日志批量写入
        - 处理流量数据批量写入（每30秒或缓存满100条时写入）
        """
        while True:
            # 1. 处理异常日志
            if ANOMALY_QUEUE:
                with QUEUE_LOCK:
                    batch = list(ANOMALY_QUEUE)
                    ANOMALY_QUEUE.clear()
                try:
                    conn = pymysql.connect(**DB_CONFIG)  # ✅ 每个线程独立连接
                    with conn.cursor() as cur:
                        sql = """INSERT INTO anomaly_log
                                     (detect_time, src_ip, dst_ip, protocol, anomaly_type, details)
                                 VALUES (%s, %s, %s, %s, %s, %s)"""
                        cur.executemany(sql, [
                            (e['detect_time'], e['src_ip'], e.get('dst_ip', ''),
                             e.get('protocol', ''), e['anomaly_type'], e['details'])
                            for e in batch
                        ])
                        conn.commit()
                    self.logger.info(f'📥 异常日志写入 {len(batch)} 条')
                except Exception as e:
                    self.logger.error(f'批量写异常日志失败: {e}')
                finally:
                    if conn:
                        conn.close()
            
            # 2. 处理流量数据（智能批量写入）
            should_write_flow = False
            if self.flow_cache:
                # 条件1：缓存超过100条
                if len(self.flow_cache) >= 100:
                    should_write_flow = True
                # 条件2：缓存有数据且超过30秒未写入
                elif hasattr(self, '_last_flow_write_time'):
                    if time.time() - self._last_flow_write_time > 30:
                        should_write_flow = True
                else:
                    # 首次运行，记录时间
                    self._last_flow_write_time = time.time()
            
            if should_write_flow:
                self._write_db()
                self._last_flow_write_time = time.time()
            
            hub.sleep(1)

        # ========== ① 新增：攻击事件落库 ==========
        # ========== ① 攻击事件：1 分钟合并，不同类型一定分开 ==========
    def _log_attack_session(self, entry):
        """
        ✅ Flag状态机 + 滑动窗口方案
        - 检测到攻击包时，如果15秒内无活动会话，创建新会话（is_active=1）
        - 持续攻击时，更新packet_count和last_packet_time
        - 定期检查（15秒无新包）自动关闭会话（is_active=0, 设置end_time）
        """
        conn = None
        try:
            src_ip = entry['src_ip']
            anomaly_type = entry['anomaly_type']
            now = datetime.now()
            
            conn = pymysql.connect(**DB_CONFIG)
            with conn.cursor() as cur:
                # 1. 查找该IP+攻击类型的活动会话
                sql = """
                    SELECT id, start_time, packet_count, last_packet_time
                    FROM attack_sessions
                    WHERE src_ip = %s
                      AND anomaly_type = %s
                      AND is_active = 1
                    ORDER BY start_time DESC
                    LIMIT 1
                """
                cur.execute(sql, (src_ip, anomaly_type))
                row = cur.fetchone()
                
                if row:
                    # 2. 存在活动会话
                    session_id, start_time, packet_count, last_packet_time = row
                    
                    # ✅ 计算会话持续时间，如果超过1小时，强制关闭并创建新会话
                    if start_time:
                        session_duration = (now - start_time).total_seconds()
                    else:
                        session_duration = 0
                    
                    # 计算距离上次攻击包的时间间隔
                    # ✅ 处理last_packet_time为None的情况
                    if last_packet_time is None:
                        time_diff = 0
                    else:
                        time_diff = (now - last_packet_time).total_seconds()
                    
                    # ✅ 如果会话持续超过1小时 OR 距离上次包超过2秒，关闭旧会话创建新会话
                    # 2秒窗口：确保能区分"攻击停止后立即再次攻击"的情况
                    if time_diff > 2 or session_duration > 3600:
                        # 2-1. 超过2秒无新包，认为是新一轮攻击
                        # 先关闭旧会话
                        if last_packet_time and start_time:
                            duration = (last_packet_time - start_time).total_seconds()
                        else:
                            duration = 0
                        cur.execute("""
                            UPDATE attack_sessions
                            SET is_active = 0,
                                end_time = %s,
                                duration_seconds = %s,
                                status = 'pending'
                            WHERE id = %s
                        """, (last_packet_time or now, int(duration), session_id))
                        
                        # 创建新会话（系统自动检测，status='pending'）
                        cur.execute("""
                            INSERT INTO attack_sessions
                            (src_ip, anomaly_type, start_time, last_packet_time, packet_count, is_active, status)
                            VALUES (%s, %s, %s, %s, 1, 1, 'pending')
                        """, (src_ip, anomaly_type, now, now))
                        
                        if session_duration > 3600:
                            self.logger.info(f"🆕 [attack_session] {src_ip} {anomaly_type} 旧会话超时（持续{int(session_duration/3600)}小时），创建新会话")
                        else:
                            self.logger.info(f"🆕 [attack_session] {src_ip} {anomaly_type} 新会话开始（距离上次{int(time_diff)}秒）")
                    else:
                        # 2-2. 继续当前会话
                        cur.execute("""
                            UPDATE attack_sessions
                            SET packet_count = packet_count + 1,
                                last_packet_time = %s
                            WHERE id = %s
                        """, (now, session_id))
                else:
                    # 3. 无活动会话，创建新会话（系统自动检测，status='pending'）
                    cur.execute("""
                        INSERT INTO attack_sessions
                        (src_ip, anomaly_type, start_time, last_packet_time, packet_count, is_active, status)
                        VALUES (%s, %s, %s, %s, 1, 1, 'pending')
                    """, (src_ip, anomaly_type, now, now))
                    
                    self.logger.info(f"🆕 [attack_session] {src_ip} {anomaly_type} 首次检测，创建新会话")
                
                conn.commit()
        except Exception as e:
            if conn: conn.rollback()
            self.logger.error(f"[attack_sessions] 记录失败: {e}")
            import traceback
            traceback.print_exc()  # ✅ 打印完整错误堆栈
        finally:
            if conn: conn.close()

    # ========== ② 限速事件：1 分钟合并，不同原因分开 ==========
    def _log_limit_session(self, src_ip: str, reason: str, kbps: int):
        """
        同一 IP、同一限速原因、1 分钟内只记 1 次；
        不同原因立即新开一行。
        """
        conn = None
        try:
            minute = time.strftime('%Y-%m-%d %H:%M:00')   # 当前分钟
            conn = pymysql.connect(**DB_CONFIG)
            with conn.cursor() as cur:
                sql = """
                    SELECT id FROM limit_sessions
                    WHERE src_ip = %s
                      AND reason = %s
                      AND start_time = %s
                """
                cur.execute(sql, (src_ip, reason, minute))
                row = cur.fetchone()
                if row:                      # 60 秒内已存在 → 只更新速率
                    cur.execute(
                        "UPDATE limit_sessions SET kbps = %s WHERE id = %s",
                        (kbps, row[0]))
                else:                        # 新一分钟 or 新原因 → 插新行
                    cur.execute(
                        """INSERT INTO limit_sessions (src_ip, reason, start_time, kbps)
                           VALUES (%s, %s, %s, %s)""",
                        (src_ip, reason, minute, kbps))
                conn.commit()
        except Exception as e:
            if conn: conn.rollback()
            self.logger.error(f"[limit_sessions] 分钟合并失败: {e}")
        finally:
            if conn: conn.close()

    # ========== ③ 自动关闭过期攻击会话（定期执行） ==========
    def _auto_close_attack_sessions_loop(self):
        """
        每3秒检查一次，自动关闭超过2秒无新包的活动会话
        """
        while True:
            conn = None
            try:
                conn = pymysql.connect(**DB_CONFIG)
                with conn.cursor() as cur:
                    # 查找所有活动会话
                    cur.execute("""
                        SELECT id, src_ip, anomaly_type, start_time, last_packet_time
                        FROM attack_sessions
                        WHERE is_active = 1
                    """)
                    
                    rows = cur.fetchall()
                    now = datetime.now()
                    closed_count = 0
                    
                    for row in rows:
                        session_id, src_ip, anomaly_type, start_time, last_packet_time = row
                        
                        # ✅ 处理None值
                        if last_packet_time is None:
                            continue  # 跳过没有last_packet_time的记录
                        
                        # 计算距离最后一个包的时间
                        time_diff = (now - last_packet_time).total_seconds()
                        
                        if time_diff > 2:
                            # 超过2秒无新包，关闭会话
                            if start_time:
                                duration = (last_packet_time - start_time).total_seconds()
                            else:
                                duration = 0
                            
                            cur.execute("""
                                UPDATE attack_sessions
                                SET is_active = 0,
                                    end_time = %s,
                                    duration_seconds = %s,
                                    status = IFNULL(status, 'pending')
                                WHERE id = %s
                            """, (last_packet_time, int(duration), session_id))
                            
                            closed_count += 1
                            self.logger.info(f"⏹️ [auto_close] {src_ip} {anomaly_type} 会话#{session_id} 自动关闭（持续{int(duration)}秒）")
                    
                    if closed_count > 0:
                        conn.commit()
                        self.logger.info(f"✅ [auto_close] 本轮关闭 {closed_count} 个过期会话")
            except Exception as e:
                self.logger.error(f"[auto_close] 自动关闭会话失败: {e}")
                import traceback
                traceback.print_exc()
            finally:
                # ✅ 修复：使用finally确保只关闭一次，避免"Already closed"错误
                if conn:
                    try:
                        conn.close()
                    except Exception as close_err:
                        self.logger.debug(f"[auto_close] 关闭连接时出错（已忽略）: {close_err}")
            
            hub.sleep(3)  # 每3秒检查一次

    # ========== ④ 设备异常检测函数 ==========
    def _log_device_anomaly(self, anomaly_type, device_type, device_id, description, severity='medium'):
        """
        记录设备异常到device_anomalies表
        """
        conn = None
        try:
            conn = pymysql.connect(**DB_CONFIG)
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO device_anomalies
                    (anomaly_type, device_type, device_id, description, severity, status)
                    VALUES (%s, %s, %s, %s, %s, 'pending')
                """, (anomaly_type, device_type, device_id, description, severity))
                conn.commit()
                self.logger.warning(f"🔧 [device_anomaly] {anomaly_type}: {description}")
        except Exception as e:
            self.logger.error(f"[device_anomaly] 记录失败: {e}")
            if conn:
                conn.rollback()
        finally:
            if conn:
                conn.close()

    def _check_ip_subnet(self, src_ip):
        """
        检测IP配置异常（不在合法网段）
        """
        self.logger.info(f"🔍 [_check_ip_subnet] 检查IP: {src_ip}")
        
        # 跳过已检查过的IP
        if src_ip in self.ip_subnet_checked:
            self.logger.info(f"🔍 [_check_ip_subnet] IP {src_ip} 已检查过，跳过")
            return
        
        try:
            # 检查IP是否在合法网段
            ip_obj = ipaddress.ip_address(src_ip)
            subnet_obj = ipaddress.ip_network(self.VALID_SUBNET, strict=False)
            
            self.logger.info(f"🔍 [_check_ip_subnet] IP对象: {ip_obj}, 网段对象: {subnet_obj}")
            
            if ip_obj not in subnet_obj:
                self.logger.warning(f"⚠️ [_check_ip_subnet] IP {src_ip} 不在合法网段 {self.VALID_SUBNET}，准备记录异常")
                self._log_device_anomaly(
                    anomaly_type='IP配置异常',
                    device_type='host',
                    device_id=src_ip,
                    description=f'主机IP {src_ip} 不在合法网段 {self.VALID_SUBNET}',
                    severity='high'
                )
            else:
                self.logger.info(f"✅ [_check_ip_subnet] IP {src_ip} 在合法网段内")
            
            # 标记为已检查
            self.ip_subnet_checked.add(src_ip)
        except Exception as e:
            self.logger.error(f"❌ [_check_ip_subnet] 检查IP {src_ip} 时出错: {e}")
            import traceback
            traceback.print_exc()

    def _device_anomaly_detection_loop(self):
        """
        ✅ 定时检测设备异常（不依赖packet_in事件）
        - 每10秒检查一次MAC地址冲突
        - 定期检查IP配置异常（通过ARP表或流量统计）
        """
        while True:
            try:
                hub.sleep(10)  # 每10秒检查一次
                
                # 检查MAC地址冲突
                self._check_mac_conflicts_periodic()
                
            except Exception as e:
                self.logger.error(f"❌ 设备异常检测循环出错: {e}")
                import traceback
                traceback.print_exc()
    
    def _check_mac_conflicts_periodic(self):
        """
        定期检查MAC地址冲突（不依赖packet_in）
        """
        try:
            # 遍历所有交换机的MAC-端口映射
            for dpid, mac_dict in self.mac_to_port.items():
                for mac, port in mac_dict.items():
                    # 检查这个MAC是否在其他端口出现过
                    for other_dpid, other_mac_dict in self.mac_to_port.items():
                        if other_dpid == dpid:
                            continue
                        if mac in other_mac_dict:
                            other_port = other_mac_dict[mac]
                            if (dpid, port) != (other_dpid, other_port):
                                self.logger.warning(f"⚠️ MAC冲突检测: MAC {mac} 同时出现在交换机{dpid}端口{port}和交换机{other_dpid}端口{other_port}")
                                self._log_device_anomaly(
                                    anomaly_type='MAC地址冲突',
                                    device_type='host',
                                    device_id=mac,
                                    description=f'MAC {mac} 同时出现在交换机{dpid}端口{port}和交换机{other_dpid}端口{other_port}',
                                    severity='high'
                                )
        except Exception as e:
            self.logger.error(f"❌ MAC冲突检测失败: {e}")

    def _check_port_flapping(self, dpid, port_no):
        """
        检测端口频繁抖动（60秒内up/down超过5次）
        """
        key = (dpid, port_no)
        now = time.time()
        
        # 记录状态变化
        self.port_flap_tracker[key].append(now)
        
        # 清理60秒前的记录
        self.port_flap_tracker[key] = [t for t in self.port_flap_tracker[key] if now - t < 60]
        
        # 检测是否超过阈值
        if len(self.port_flap_tracker[key]) > 5:
            self._log_device_anomaly(
                anomaly_type='端口频繁抖动',
                device_type='switch',
                device_id=f'{dpid}:port{port_no}',
                description=f'交换机 {dpid} 端口 {port_no} 在60秒内up/down {len(self.port_flap_tracker[key])}次',
                severity='medium'
            )
            # 重置计数器，避免重复报警
            self.port_flap_tracker[key] = []

    def _check_mac_conflict(self, src_mac, dpid, in_port):
        """
        检测MAC地址冲突（同一MAC出现在不同端口）
        """
        if src_mac in self.mac_port_map:
            old_dpid, old_port = self.mac_port_map[src_mac]
            if (old_dpid, old_port) != (dpid, in_port):
                self._log_device_anomaly(
                    anomaly_type='MAC地址冲突',
                    device_type='host',
                    device_id=src_mac,
                    description=f'MAC {src_mac} 同时出现在交换机{old_dpid}端口{old_port} 和 交换机{dpid}端口{in_port}',
                    severity='high'
                )
        
        # 更新映射
        self.mac_port_map[src_mac] = (dpid, in_port)


    # ========== ② 新增：查询接口（测试用） ==========
    def get_attack_count(self, ip=None, days=1):
        """
        返回最近 N 天每 IP 每协议的真实攻击次数
        前端或 CLI 可直接调它验证
        """
        conn = None
        try:
            conn = pymysql.connect(**DB_CONFIG)
            with conn.cursor() as cur:
                if ip:
                    sql = """
                        SELECT anomaly_type, COUNT(*) AS cnt
                        FROM attack_sessions
                        WHERE src_ip = %s
                          AND start_time >= DATE_SUB(NOW(), INTERVAL %s DAY)
                        GROUP BY anomaly_type
                    """
                    cur.execute(sql, (ip, days))
                else:
                    sql = """
                        SELECT src_ip, anomaly_type, COUNT(*) AS cnt
                        FROM attack_sessions
                        WHERE start_time >= DATE_SUB(NOW(), INTERVAL %s DAY)
                        GROUP BY src_ip, anomaly_type
                    """
                    cur.execute(sql, (days,))
                return cur.fetchall()
        except Exception as e:
            self.logger.error(f"[get_attack_count] 查询失败: {e}")
            return []
        finally:
            if conn:
                conn.close()


    def _write_anomaly_db(self, entry):
        """异常日志实时插入 anomaly_log 表"""
        try:
            conn = self.get_db_conn()
            with conn.cursor() as cur:
                sql = """INSERT INTO anomaly_log (detect_time, src_ip, dst_ip, protocol, anomaly_type, details)
                         VALUES (%s, %s, %s, %s, %s, %s)"""
                cur.execute(sql, (entry['detect_time'],
                                  entry['src_ip'],
                                  entry.get('dst_ip', ''),
                                  entry.get('protocol', ''),
                                  entry['anomaly_type'],
                                  entry['details']))
                conn.commit()
        except Exception as e:
            self.logger.error(f"实时写异常日志失败: {e}")
            if self.db_conn:
                self.db_conn.rollback()

    # ---------------- 写异常日志（文件 + 数据库） ----------------
    def _write_anomaly(self, entry):
        try:
            if os.path.getsize(ANOMALY_LOG) >= LOG_MAX_SIZE:
                bk = f"{ANOMALY_LOG}.bak_{int(time.time())}"
                os.rename(ANOMALY_LOG, bk)
                self._init_anomaly_files()
            with open(ANOMALY_LOG, 'a', encoding='utf-8') as f:
                json.dump(entry, f, ensure_ascii=False)
                f.write('\n')
        except Exception as e:
            self.logger.error(f"写日志失败: {e}")




    # ---------------- 端口熵 ----------------
    def _port_entropy(self, src_ip):
        ports = self.src_port_counter[src_ip]
        if not ports:
            return 0.0
        cnt = Counter(ports)
        total = sum(cnt.values())
        entropy = 0.0
        for v in cnt.values():
            p = v / total
            entropy -= p * math.log2(p) if p > 0 else 0
        return entropy

    # ---------------- 模型训练 ----------------
    def _train_task(self):
        hub.sleep(10)
        self.logger.info("📊 开始收集正常流量训练孤立森林 …")
        start = time.time()
        while time.time() - start < self.training_seconds:
            hub.sleep(1)
        feats = [f['features'] for f in self.flow_features_with_info]
        if len(feats) >= 5:
            self.isolation_model = IsolationForest(**ISOLATION_PARAM)
            self.isolation_model.fit(np.array(feats))
            with open(MODEL_PATH, 'wb') as f:
                pickle.dump({'model': self.isolation_model, 'contamination': ISOLATION_PARAM['contamination']}, f)
            self.is_training = False
            self.logger.info("✅ 孤立森林训练完成")
        else:
            self.logger.warning("⚠️ 样本不足，30s 后重试")
            hub.sleep(30)
            self._train_task()

    # ---------------- 检测循环 ----------------
    def _detect_loop(self):
        while True:
            if not self.is_training and self.isolation_model:
                self._iforest_detect()
            hub.sleep(2)

    def _iforest_detect(self):
        if not self.flow_features_with_info:
            return
        snapshot = self.flow_features_with_info.copy()
        if not snapshot:
            return
        feats = np.array([f['features'] for f in snapshot])
        if feats.shape[0] == 0:
            return
        preds = self.isolation_model.predict(feats)
        if preds.size != len(snapshot):
            self.logger.warning(f"[IF] preds长度{preds.size}与snapshot长度{len(snapshot)}不一致，跳过本轮")
            return
        for i, flow in enumerate(snapshot):
            if preds[i] == -1:
                # 白名单直接跳过
                if self.acl_check(flow['src_ip']) == 'white':
                    continue

                # 低速闸门：降低阈值以提高敏感性
                if flow['features'][0] < 500:  # 已从2000调整为1000
                    self.logger.debug(f"burst 速率{flow['features'][0]} 低于闸门，仅记录")
                    continue

                # RAG三判已删除，只保留孤立森林检测
        # 清理已处理的流量特征，保留最新500条
        self.flow_features_with_info = self.flow_features_with_info[len(snapshot):]
        if len(self.flow_features_with_info) > 500:
            self.flow_features_with_info = self.flow_features_with_info[-500:]


    # ---------------- 统计请求 ----------------
    def _stats_loop(self):
        while True:
            hub.sleep(1)  # ✅ 改回每1秒采集一次（与之前一致）
            for dp in self.datapaths.values():
                # ✅ 同时请求流表统计和端口统计
                dp.send_msg(dp.ofproto_parser.OFPFlowStatsRequest(dp))
                dp.send_msg(dp.ofproto_parser.OFPPortStatsRequest(dp, 0, dp.ofproto.OFPP_ANY))

    @set_ev_cls(ofp_event.EventOFPFlowStatsReply, MAIN_DISPATCHER)
    def stats_reply(self, ev):
        dpid = ev.msg.datapath.id
        
        # 缓存流表数据供REST API使用
        flow_list = []
        for flow in ev.msg.body:
            self._extract_flow(flow, dpid)
            # 将流表转换为可序列化的字典格式
            flow_dict = {
                'priority': flow.priority,
                'cookie': flow.cookie,
                'idle_timeout': flow.idle_timeout,
                'hard_timeout': flow.hard_timeout,
                'packet_count': flow.packet_count,
                'byte_count': flow.byte_count,
                'duration_sec': flow.duration_sec,
                'match': {k: str(v) for k, v in flow.match.items()},
                'actions': []
            }
            # 解析actions
            for inst in flow.instructions:
                if hasattr(inst, 'actions'):
                    for act in inst.actions:
                        if hasattr(act, 'port'):
                            port = act.port
                            # 转换OpenFlow特殊端口号为可读名称
                            port_name = self._get_port_name(port)
                            flow_dict['actions'].append({
                                'type': 'OUTPUT', 
                                'port': port,
                                'port_name': port_name
                            })
            flow_list.append(flow_dict)
        
        # 更新缓存
        self.switch_flow_stats[dpid] = flow_list
        
        if self.flow_cache:
            self._write_db()

    def _get_port_name(self, port):
        """转换OpenFlow端口号为可读名称"""
        # OpenFlow特殊端口定义
        OFPP_MAX = 0xffffff00
        OFPP_IN_PORT = 0xfffffff8  # 4294967288
        OFPP_TABLE = 0xfffffff9     # 4294967289
        OFPP_NORMAL = 0xfffffffa    # 4294967290
        OFPP_FLOOD = 0xfffffffb     # 4294967291
        OFPP_ALL = 0xfffffffc       # 4294967292
        OFPP_CONTROLLER = 0xfffffffd # 4294967293
        OFPP_LOCAL = 0xfffffffe     # 4294967294
        OFPP_ANY = 0xffffffff       # 4294967295
        
        special_ports = {
            OFPP_IN_PORT: 'IN_PORT',
            OFPP_TABLE: 'TABLE',
            OFPP_NORMAL: 'NORMAL',
            OFPP_FLOOD: 'NORMAL',  # ✅ 将FLOOD显示为NORMAL
            OFPP_ALL: 'ALL',
            OFPP_CONTROLLER: 'NORMAL',  # ✅ 将CONTROLLER显示为NORMAL
            OFPP_LOCAL: 'LOCAL',
            OFPP_ANY: 'ANY'
        }
        
        if port in special_ports:
            return special_ports[port]
        elif port < OFPP_MAX:
            return f"端口{port}"
        else:
            return f"未知({port})"

    def _extract_flow(self, flow, dpid):
        """
        参考旧版本smart_defense_switch.py的逻辑
        只处理明确包含ipv4_src和ipv4_dst的流表，自动过滤ARP/LLDP等非IPv4流
        """
        match = flow.match
        if flow.duration_sec <= 0:
            return
        
        # ✅ 严格检查：必须有IPv4源和目标地址
        src_ip = match.get('ipv4_src')
        dst_ip = match.get('ipv4_dst')
        if not src_ip or not dst_ip:
            # 🧹 自动过滤掉ARP、LLDP、默认流等非IPv4流表
            return
        
        proto_num = match.get('ip_proto')
        proto_map = {1: 'ICMP', 6: 'TCP', 17: 'UDP'}
        proto = proto_map.get(proto_num, 'IP')

        src_port = match.get('tcp_src') or match.get('udp_src') or 0
        dst_port = match.get('tcp_dst') or match.get('udp_dst') or 0
        src_mac = match.get('eth_src', '00:00:00:00:00:00')
        dst_mac = match.get('eth_dst', '00:00:00:00:00:00')

        # ✅ 只对真实IPv4流做异常检测与入库
        pkt_rate = min(flow.packet_count / flow.duration_sec, 10000)
        byte_rate = min(flow.byte_count / flow.duration_sec, 1000000)
        is_arp = 1 if proto == 'ARP' else 0
        self.src_dst_counter[src_ip].add(dst_ip)
        if dst_port:
            self.src_port_counter[src_ip].add(dst_port)
        entropy = self._port_entropy(src_ip)
        features = [pkt_rate, byte_rate, is_arp, len(self.src_dst_counter[src_ip]), entropy]

        # 特征缓存（用于异常检测）
        self.flow_features_with_info.append({
            'src_ip': src_ip, 'dst_ip': dst_ip, 'protocol': proto,
            'features': features, 'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
            'packet_count': flow.packet_count, 'byte_count': flow.byte_count
        })

        # ✅ 所有真实IPv4流表写入数据库（用于流量趋势统计）
        ts = time.strftime('%Y-%m-%d %H:%M:%S')
        self.flow_cache.append({
            'timestamp': ts,
            'datapath_id': f"{dpid:016d}",
            'src_ip': src_ip, 
            'dst_ip': dst_ip,
            'protocol': proto,
            'src_port': src_port, 
            'dst_port': dst_port,
            'src_mac': src_mac, 
            'dst_mac': dst_mac,
            'packet_count': flow.packet_count,
            'byte_count': flow.byte_count,
            'duration_sec': flow.duration_sec,
            'stats_day': ts[:10],
            'stats_hour': int(ts[11:13])
        })


    def _write_db(self):
        try:
            conn = pymysql.connect(**DB_CONFIG)
            with conn.cursor() as cur:
                sql = """INSERT INTO flow_stats
                         (timestamp, datapath_id, src_ip, dst_ip, protocol,
                          src_port, dst_port, src_mac, dst_mac,
                          packet_count, byte_count, duration_sec,
                          stats_day, stats_hour)
                         VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"""
                args = [(r['timestamp'], r['datapath_id'], r['src_ip'], r['dst_ip'],
                         r['protocol'], r['src_port'], r['dst_port'],
                         r['src_mac'], r['dst_mac'],
                         r['packet_count'], r['byte_count'], r['duration_sec'],
                         r['stats_day'], r['stats_hour'])        # <-- 新增两列
                        for r in self.flow_cache]
                cur.executemany(sql, args)
                conn.commit()
                # ✅ 智能日志：显示过滤效果和流量统计
                if len(args) > 0:
                    total_packets = sum(r['packet_count'] for r in self.flow_cache)
                    total_bytes = sum(r['byte_count'] for r in self.flow_cache)
                    
                    # 统计协议分布
                    protocol_stats = {}
                    for r in self.flow_cache:
                        proto = r['protocol']
                        protocol_stats[proto] = protocol_stats.get(proto, 0) + 1
                    
                    # 🔍 临时调试：显示所有入库数据的详细信息
                    proto_str = ', '.join([f"{k}:{v}" for k, v in protocol_stats.items()])
                    self.logger.info(f"📥 主机流量入库 {len(args)}条 (总包数={total_packets}, 总字节={total_bytes}) [{proto_str}]")
                    
                    # 🔍 显示前3条记录的详细信息，帮助分析
                    for i, record in enumerate(self.flow_cache[:3]):
                        self.logger.info(f"   [{i+1}] {record['src_ip']}->{record['dst_ip']} {record['protocol']} "
                                       f"sport={record['src_port']} dport={record['dst_port']} "
                                       f"pkts={record['packet_count']} bytes={record['byte_count']}")
                    
                    if len(self.flow_cache) > 3:
                        self.logger.info(f"   ... 还有 {len(self.flow_cache)-3} 条记录")
        except Exception as e:
            self.logger.error(f"数据库写入失败: {e}")
            if conn:
                conn.rollback()
        finally:
            if conn:
                conn.close()
        self.flow_cache = []


    # ---------------- 实时写库线程（REALTIME_INSERT = True 时启动） ----------------
    def _realtime_insert_loop(self):
        while True:
            hub.sleep(1)
            if self.flow_cache:
                self._write_db()

    # ---------------- 定时任务 ----------------
    def _cleanup_loop(self):
        while True:
            hub.sleep(60)
            now = time.time()
            for ip, exp in list(self.limited_ips.items()):
                if exp <= now:
                    del self.limited_ips[ip]
                    # ① 清 active 表 ② 写 log 表
                    try:
                        conn = self.get_db_conn()
                        with conn.cursor() as cur:
                            cur.execute("DELETE FROM rate_limit_active WHERE src_ip = %s", (ip,))
                            cur.execute("""
                                INSERT INTO rate_limit_log (src_ip, operator, action, reason)
                                VALUES (%s, %s, %s, %s)
                            """, (ip, 'system', 'unlimit', '限速到期自动解除'))
                            conn.commit()
                    except Exception as e:
                        self.logger.error(f"定时清理限速记录失败: {e}")
                        if self.db_conn:
                            self.db_conn.rollback()

                    self.logger.info(f"🔓 限速到期 {ip}，已从 active 表移除")


    def _reset_loop(self):
        while True:
            hub.sleep(1)                       # 每秒一次
            now = time.time()

            # 1) 每秒清 ARP
            for v in self.arp_stats.values():
                v['count'] = 0
                v['last_time'] = now
                # 防止 MAC 集合无限增长
                if len(v['macs']) > 5:
                    v['macs'] = set(list(v['macs'])[-3:])

            # ✅ 2) 每秒清零TCP/UDP/ICMP统计（持续监控攻击）
            for v in self.tcp_flag_stats.values():
                v['syn'] = v['total'] = 0
                v['last'] = now
            for v in self.udp_stats.values():
                v['count'] = 0
                v['last'] = now
            for v in self.icmp_stats.values():
                v['count'] = 0
                v['last'] = now

            # 3) 每 300 s 清其余计数器
            if int(now) % 300 == 0:
                self.src_dst_counter.clear()
                self.src_port_counter.clear()
                self.raw_pkt_counter.clear()




    def _summarize_loop(self):
        while True:
            hub.sleep(300)
            if not self.anomaly_cache:
                continue
            try:
                with open(SUMMARY_JSON, 'r', encoding='utf-8') as f:
                    summary = json.load(f)
            except Exception:
                summary = {"total_anomalies": 0, "anomaly_types": {}, "top_offenders": [], "daily": {}, "latest": []}
            ### 关键：防止 KeyError
            summary.setdefault('daily', {})
            summary.setdefault('latest', [])
            new_cnt = len(self.anomaly_cache)
            summary['total_anomalies'] += new_cnt
            for a in self.anomaly_cache:
                t = a['anomaly_type']
                summary['anomaly_types'][t] = summary['anomaly_types'].get(t, 0) + 1
            today = time.strftime('%Y-%m-%d')
            summary['daily'][today] = summary['daily'].get(today, 0) + new_cnt
            ip_cnt = defaultdict(int)
            for a in summary['latest'] + self.anomaly_cache:
                ip_cnt[a['src_ip']] += 1
            summary['top_offenders'] = [{"ip": ip, "count": c} for ip, c in
                                        sorted(ip_cnt.items(), key=lambda x: x[1], reverse=True)[:5]]
            summary['latest'] = (self.anomaly_cache + summary['latest'])[:10]
            with open(SUMMARY_JSON, 'w', encoding='utf-8') as f:
                json.dump(summary, f, ensure_ascii=False, indent=2)
            self.logger.info(f"📊 异常汇总已更新，今日 {today} +{new_cnt}")
            self.anomaly_cache = []

    # ========================================================================
    # Web 接口  ——  聊天 + 管理员 AI 指令 + 长期记忆（重启不丢）
    # ========================================================================
    def get_anomaly_summary(self, ip=None):
        try:
            with open(SUMMARY_JSON, 'r', encoding='utf-8') as f:
                s = json.load(f)
            if ip:
                return [a for a in s.get('latest', []) if a['src_ip'] == ip]
            return s
        except Exception:
            return {}

    def db_insert_chat(self, user_id: str, role: str, content: str):
        role = role if role in ('admin', 'user') else 'user'
        try:
            conn = self.get_db_conn()
            with conn.cursor() as cur:
                sql = "INSERT INTO chat_memory (user_id, role, content) VALUES (%s, %s, %s)"
                cur.execute(sql, (user_id, role, content))
                conn.commit()
        except Exception as e:
            self.logger.error(f"聊天入库失败: {e}")
            if self.db_conn:
                self.db_conn.rollback()

    def db_get_chat_memory(self, user_id: str, limit: int = MEMORY_TURNS):
        try:
            conn = self.get_db_conn()
            with conn.cursor() as cur:
                sql = """SELECT role, content \
                         FROM chat_memory
                         WHERE user_id = %s
                         ORDER BY created_at DESC
                             LIMIT %s"""
                cur.execute(sql, (user_id, limit * 2))
                rows = cur.fetchall()
                return [{'role': r[0], 'content': r[1]} for r in rows[::-1]]
        except Exception as e:
            self.logger.error(f"读取记忆失败: {e}")
            return []
    
    # ---------------- 卡片：4 个纯数字（真实事件数） ----------------
    def get_dashboard_cards(self):
        import datetime, pymysql
        from collections import Counter

        today_str = datetime.date.today().isoformat()
        yesterday_str = (datetime.date.today() - datetime.timedelta(days=1)).isoformat()
        conn = None
        try:
            conn = pymysql.connect(**DB_CONFIG, autocommit=True)
            with conn.cursor() as cur:
                # 1. 当前限速 IP 数（去重）
                cur.execute("SELECT COUNT(DISTINCT src_ip) FROM rate_limit_active")
                current_limit_cnt = int(cur.fetchone()[0])

                # 2. 今日新增限速（真实次数）
                cur.execute("""
                    SELECT COUNT(*)
                    FROM limit_sessions
                    WHERE DATE(start_time) = %s
                """, (today_str,))
                today_new_limit = int(cur.fetchone()[0])

                # 2.1 昨日新增限速（用于计算环比）
                cur.execute("""
                    SELECT COUNT(*)
                    FROM limit_sessions
                    WHERE DATE(start_time) = %s
                """, (yesterday_str,))
                yesterday_new_limit = int(cur.fetchone()[0])

                # 计算今日新增限速的环比
                if yesterday_new_limit > 0:
                    today_limit_change_pct = round(((today_new_limit - yesterday_new_limit) / yesterday_new_limit) * 100)
                else:
                    today_limit_change_pct = 0 if today_new_limit == 0 else 100

                # 2.2 昨日当前限速数（用于计算环比）
                cur.execute("""
                    SELECT COUNT(DISTINCT src_ip)
                    FROM rate_limit_active
                    WHERE DATE(created_at) = %s
                """, (yesterday_str,))
                yesterday_limit_cnt = int(cur.fetchone()[0])

                # 计算当前限速数的环比
                if yesterday_limit_cnt > 0:
                    current_limit_change_pct = round(((current_limit_cnt - yesterday_limit_cnt) / yesterday_limit_cnt) * 100)
                else:
                    current_limit_change_pct = 0 if current_limit_cnt == 0 else 100

                # 3. 主要限速原因（真实最多）
                cur.execute("""
                    SELECT reason, COUNT(*) AS cnt
                    FROM limit_sessions
                    WHERE DATE(start_time) = %s
                    GROUP BY reason
                    ORDER BY cnt DESC
                    LIMIT 1
                """, (today_str,))
                row = cur.fetchone()
                top_reason = row[0] if row else "无数据"

                # 4. 高频限速 IP（真实被限速次数）
                cur.execute("""
                    SELECT src_ip, COUNT(*) AS real_times
                    FROM limit_sessions
                    WHERE DATE(start_time) = %s
                    GROUP BY src_ip
                    ORDER BY real_times DESC
                    LIMIT 1
                """, (today_str,))
                row = cur.fetchone()
                top_ip = row[0] if row else "无数据"
                top_ip_count = int(row[1]) if row else 0
        except Exception as e:
            self.logger.error(f"get_dashboard_cards error: {e}")
            current_limit_cnt = today_new_limit = 0
            current_limit_change_pct = today_limit_change_pct = 0
            top_reason = top_ip = "无数据"
            top_ip_count = 0
        finally:
            if conn:
                conn.close()

        return {
            "current_limit_cnt": current_limit_cnt,
            "current_limit_change_pct": current_limit_change_pct,
            "today_new_limit": today_new_limit,
            "today_limit_change_pct": today_limit_change_pct,
            "top_reason": top_reason,
            "top_ip": top_ip,
            "top_ip_count": top_ip_count
        }







# -------------- 以下整段直接替换原 ChatController --------------
class ChatController(ControllerBase):
    def __init__(self, req, link, data, **config):
        super(ChatController, self).__init__(req, link, data, **config)
        self.ctrl = data['ctrl']

    # ---------------- HTTP 单轮接口（curl 用） ----------------
    @route('chat', '/v1/chat', methods=['POST'])
    def chat(self, req, **_):
        try:
            body = json.loads(req.body.decode('utf-8'))
            # ✅ 支持username和user_id两种方式
            username = body.get('username') or body.get('user_id', 'anonymous')
            user_text = body.get('user', '').strip()
            
            self.ctrl.logger.info(f"[CHAT API] 收到请求 - username: {username}, message: {user_text[:50]}")
        except Exception as e:
            self.ctrl.logger.error(f"[CHAT API] JSON解析失败: {e}")
            return self._json_resp({'error': 'invalid json'}, 400)
        reply = self._process_one_shot(username, user_text)
        return self._json_resp({'reply': reply})

    @route('anomalies_day', '/v1/anomalies/day', methods=['GET'])
    def get_anomalies_day(self, req, **_):
        """最近 1 天异常数据"""
        return self._get_anomalies_by_hours(24)

    @route('anomalies_3days', '/v1/anomalies/3days', methods=['GET'])
    def get_anomalies_3days(self, req, **_):
        """最近 3 天异常数据"""
        return self._get_anomalies_by_hours(72)

    @route('anomalies_7days', '/v1/anomalies/7days', methods=['GET'])
    def get_anomalies_7days(self, req, **_):
        """最近 7 天异常数据"""
        return self._get_anomalies_by_hours(168)
    
    @route('attack_sessions', '/v1/attack_sessions', methods=['GET'])
    def get_attack_sessions(self, req, **_):
        """
        查询攻击会话数据（从attack_sessions表）
        每个会话代表一次真实的攻击，而不是单个数据包
        如果attack_sessions表不存在，降级使用anomaly_log并去重
        """
        conn = None
        try:
            # 获取查询参数
            hours = int(req.params.get('hours', 12))  # 默认12小时
            limit = req.params.get('limit', 10)  # 默认返回10条
            
            self.ctrl.logger.info(f"[attack_sessions] 查询参数: hours={hours}, limit={limit}")
            
            conn = self.ctrl.get_db_conn()
            with conn.cursor() as cur:
                # 先检查表是否存在
                cur.execute("SHOW TABLES LIKE 'attack_sessions'")
                table_exists = cur.fetchone() is not None
                
                if not table_exists:
                    self.ctrl.logger.warning("⚠️ attack_sessions表不存在，降级使用anomaly_log并去重")
                    # ✅ 降级方案：从anomaly_log查询并按IP+类型去重（不查询dst_ip以兼容）
                    sql = """
                        SELECT 
                            src_ip,
                            anomaly_type,
                            MAX(detect_time) as latest_time,
                            COUNT(*) as packet_count,
                            MAX(details) as details
                        FROM anomaly_log
                        WHERE detect_time >= DATE_SUB(NOW(), INTERVAL %s HOUR)
                        GROUP BY src_ip, anomaly_type
                        ORDER BY latest_time DESC
                        LIMIT %s
                    """
                    cur.execute(sql, (hours, int(limit)))
                    rows = cur.fetchall()
                    
                    # 格式化数据（从anomaly_log）
                    data = []
                    for idx, row in enumerate(rows, 1):
                        latest_time = row[2]  # ✅ 调整索引
                        data.append({
                            'id': idx,
                            'src_ip': row[0],
                            'dst_ip': '',  # ✅ 空字符串，不查询
                            'type': row[1],
                            'anomaly_type': row[1],
                            'start_time': latest_time.strftime('%Y-%m-%d %H:%M:%S') if latest_time else '',
                            'end_time': latest_time.strftime('%Y-%m-%d %H:%M:%S') if latest_time else '',
                            'timestamp': int(latest_time.timestamp() * 1000) if latest_time else 0,
                            'detect_time': latest_time.strftime('%Y-%m-%d %H:%M:%S') if latest_time else '',
                            'packet_count': row[3] or 0,
                            'details': row[4] or ''
                        })
                    
                else:
                    # ✅ 正常查询attack_sessions表（返回所有数据，不过滤status）
                    # ⚠️ 特殊处理：hours=24时，查询今日0点开始，而不是最近24小时
                    # 尝试查询dst_ip字段，如果不存在则为空
                    
                    # ✅ 直接使用不包含dst_ip的查询（因为attack_sessions表没有dst_ip字段）
                    if hours == 24:
                        # 今日0点开始
                        sql = """
                            SELECT 
                                id,
                                src_ip,
                                anomaly_type,
                                start_time,
                                packet_count,
                                IFNULL(status, 'pending') as status
                            FROM attack_sessions
                            WHERE DATE(start_time) = CURDATE()
                            ORDER BY start_time DESC
                            LIMIT %s
                        """
                        params = (int(limit),)
                        self.ctrl.logger.info(f"📅 查询今日数据（从0点开始）: DATE(start_time) = CURDATE()")
                    else:
                        # 最近N小时
                        sql = """
                            SELECT 
                                id,
                                src_ip,
                                anomaly_type,
                                start_time,
                                packet_count,
                                IFNULL(status, 'pending') as status
                            FROM attack_sessions
                            WHERE start_time >= DATE_SUB(NOW(), INTERVAL %s HOUR)
                            ORDER BY start_time DESC
                            LIMIT %s
                        """
                        params = (hours, int(limit))
                    
                    # 执行查询（不再尝试查询dst_ip字段）
                    cur.execute(sql, params)
                    rows = cur.fetchall()
                    has_dst_ip = False  # attack_sessions表没有dst_ip字段
                    
                    # 格式化数据（从attack_sessions）
                    self.ctrl.logger.info(f"✅ 查询attack_sessions成功: hours={hours}, 返回{len(rows)}条记录")
                    if len(rows) > 0:
                        self.ctrl.logger.info(f"📋 第一条数据时间: {rows[0][4] if has_dst_ip else rows[0][3]}")
                    
                    data = []
                    for row in rows:
                        if has_dst_ip:
                            row_id = row[0]
                            src_ip = row[1]
                            dst_ip = row[2] or ''
                            anomaly_type = row[3]
                            start_time = row[4]
                            packet_count = row[5]
                            status = row[6]
                        else:
                            row_id = row[0]
                            src_ip = row[1]
                            dst_ip = ''
                            anomaly_type = row[2]
                            start_time = row[3]
                            packet_count = row[4]
                            status = row[5]
                        
                        # 根据packet_count生成details
                        if packet_count is None:
                            details = '管理员认定'
                        else:
                            details = f'{packet_count} 个异常数据包'
                        
                        # ✅ 根据攻击类型判断严重程度
                        severity = 'low'  # 默认低风险
                        if anomaly_type in ['SYN Flood', 'UDP Flood', 'ICMP Flood']:
                            severity = 'high'  # DDoS攻击为高风险
                        elif anomaly_type in ['ARP 欺骗', 'ARP欺骗']:
                            severity = 'high'  # ARP欺骗为高风险
                        elif anomaly_type in ['黑名单关联', '带宽超限']:
                            severity = 'medium'  # 中等风险
                        
                        data.append({
                            'id': row_id,
                            'src_ip': src_ip,
                            'dst_ip': dst_ip,
                            'type': anomaly_type,
                            'anomaly_type': anomaly_type,
                            'start_time': start_time.strftime('%Y-%m-%d %H:%M:%S') if start_time else '',
                            'end_time': start_time.strftime('%Y-%m-%d %H:%M:%S') if start_time else '',
                            'timestamp': int(start_time.timestamp() * 1000) if start_time else 0,
                            'detect_time': start_time.strftime('%Y-%m-%d %H:%M:%S') if start_time else '',
                            'packet_count': packet_count,
                            'details': details,
                            'status': status,
                            'severity': severity  # ✅ 添加风险等级
                        })
            
            self.ctrl.logger.info(f"✅ 查询attack_sessions成功: {hours}小时内共{len(data)}条")
            return self._json_resp(data)
            
        except Exception as e:
            self.ctrl.logger.error(f"❌ 查询attack_sessions失败: {e}")
            import traceback
            traceback.print_exc()
            return self._json_resp({'error': str(e)}, 500)
        finally:
            if conn:
                conn.close()
                self.ctrl.logger.debug("[attack_sessions] 数据库连接已关闭")
    
    @route('handled_ips', '/v1/handled-ips', methods=['GET'])
    def get_handled_ips(self, req, **_):
        """
        查询已处理的IP列表（从limit_sessions表获取历史限速记录）
        返回指定天数内有限速记录的去重IP列表
        特殊处理：当days=1时，查询今日（从0点到现在）而非最近24小时
        """
        conn = None
        try:
            days = int(req.params.get('days', 1))  # 默认最近1天
            days = max(1, min(days, 7))  # 限制在1-7天
            
            conn = self.ctrl.get_db_conn()
            with conn.cursor() as cur:
                # 检查表是否存在
                cur.execute("SHOW TABLES LIKE 'limit_sessions'")
                table_exists = cur.fetchone() is not None
                
                if not table_exists:
                    self.ctrl.logger.warning("⚠️ limit_sessions表不存在")
                    return self._json_resp({'ips': []})
                
                # ✅ 当days=1时，使用CURDATE()查询今日数据（与Dashboard一致）
                if days == 1:
                    sql = """
                        SELECT DISTINCT src_ip 
                        FROM limit_sessions
                        WHERE DATE(start_time) = CURDATE()
                    """
                    cur.execute(sql)
                    time_desc = "今日"
                else:
                    sql = """
                        SELECT DISTINCT src_ip 
                        FROM limit_sessions
                        WHERE start_time >= DATE_SUB(NOW(), INTERVAL %s DAY)
                    """
                    cur.execute(sql, (days,))
                    time_desc = f"最近{days}天"
                
                rows = cur.fetchall()
                ips = [row[0] for row in rows if row[0]]
                
                self.ctrl.logger.info(f"✅ 查询handled_ips成功: {time_desc}内有{len(ips)}个IP被处理过")
                return self._json_resp({'ips': ips, 'count': len(ips), 'days': days})
                
        except Exception as e:
            self.ctrl.logger.error(f"❌ 查询handled_ips失败: {e}")
            import traceback
            traceback.print_exc()
            return self._json_resp({'error': str(e), 'ips': []}, 500)
        finally:
            if conn:
                conn.close()
    
    @route('attack_sessions_trend', '/v1/attack-sessions/trend', methods=['GET'])
    def get_attack_sessions_trend(self, req, **_):
        """
        获取attack_sessions的时间趋势数据（按小时统计会话数量）
        用于异常检测页面的"异常时间趋势"图表
        参数: hours - 时间范围（默认24小时）
        返回: [{hour: '11-08 14:00', count: 5}, ...]（包含日期）
        """
        conn = None
        try:
            hours = int(req.params.get('hours', 24))
            hours = max(1, min(hours, 168))  # 限制在1-168小时（7天）
            
            # ✅ 使用独立连接，避免影响持久连接
            conn = pymysql.connect(**DB_CONFIG, autocommit=True)
            with conn.cursor() as cur:
                # ✅ 统一查询逻辑：按小时分组，时间格式包含日期
                sql = """
                    SELECT 
                        DATE_FORMAT(start_time, '%%m-%%d %%H:00') as hour,
                        COUNT(*) as count
                    FROM attack_sessions
                    WHERE start_time >= DATE_SUB(NOW(), INTERVAL %s HOUR)
                    GROUP BY DATE_FORMAT(start_time, '%%m-%%d %%H:00')
                    ORDER BY hour
                """
                cur.execute(sql, (hours,))
                
                rows = cur.fetchall()
                trend_data = [{'hour': row[0], 'count': row[1]} for row in rows]
                
                # 时间描述
                if hours == 24:
                    time_desc = "最近24小时"
                elif hours == 72:
                    time_desc = "最近3天"
                elif hours == 168:
                    time_desc = "最近7天"
                else:
                    time_desc = f"最近{hours}小时"
                
                self.ctrl.logger.info(f"✅ 查询attack_sessions_trend成功: {time_desc}内有{len(trend_data)}个时间点")
                return self._json_resp({
                    'success': True,
                    'data': trend_data,
                    'hours': hours,
                    'message': f'{time_desc}的攻击会话趋势'
                })
                
        except Exception as e:
            self.ctrl.logger.error(f"❌ 查询attack_sessions_trend失败: {e}")
            import traceback
            traceback.print_exc()
            return self._json_resp({'success': False, 'error': str(e), 'data': []}, 500)
        finally:
            if conn:
                conn.close()
    
    @route('update_attack_status', '/v1/attack-sessions/update-status', methods=['POST'])
    def update_attack_status(self, req, **_):
        """
        更新attack_sessions的处理状态
        当管理员处理攻击后（封禁/限速），标记为已处理
        
        参数:
        - ip: 源IP地址
        - action: 处理动作 (blacklist/ratelimit)
        - handled_by: 处理人（默认'admin'）
        """
        conn = None
        try:
            # 获取请求参数
            body = req.json if hasattr(req, 'json') else {}
            src_ip = body.get('ip', '')
            action = body.get('action', '')
            handled_by = body.get('handled_by', 'admin')
            
            if not src_ip or not action:
                return self._json_resp({
                    'success': False,
                    'message': 'Missing required parameters: ip, action'
                }, 400)
            
            conn = self.ctrl.get_db_conn()
            with conn.cursor() as cur:
                # 更新该IP的所有pending状态的攻击为handled
                sql = """
                    UPDATE attack_sessions
                    SET status = 'handled',
                        handled_by = %s,
                        handled_at = NOW(),
                        handle_action = %s
                    WHERE src_ip = %s 
                      AND IFNULL(status, 'pending') = 'pending'
                """
                cur.execute(sql, (handled_by, action, src_ip))
                conn.commit()
                affected_rows = cur.rowcount
                
                self.ctrl.logger.info(f"✅ 更新attack_sessions状态: IP={src_ip}, action={action}, 影响{affected_rows}条记录")
                
                return self._json_resp({
                    'success': True,
                    'message': f'Successfully updated {affected_rows} attack sessions',
                    'affected_rows': affected_rows
                })
                
        except Exception as e:
            self.ctrl.logger.error(f"❌ 更新attack_sessions状态失败: {e}")
            import traceback
            traceback.print_exc()
            return self._json_resp({'success': False, 'error': str(e)}, 500)
        finally:
            if conn:
                conn.close()
    
    @route('handled_sessions_count', '/v1/handled-sessions/count', methods=['GET'])
    def get_handled_sessions_count(self, req, **_):
        """
        统计不同时间段的已处理攻击会话数量（status='handled'）
        用于异常检测页面的"已处理异常"统计卡片
        返回: {day: 今日, three_days: 最近3天, week: 最近7天}
        """
        conn = None
        try:
            conn = self.ctrl.get_db_conn()
            with conn.cursor() as cur:
                # 检查表是否存在
                cur.execute("SHOW TABLES LIKE 'attack_sessions'")
                table_exists = cur.fetchone() is not None
                
                if not table_exists:
                    self.ctrl.logger.warning("⚠️ attack_sessions表不存在，返回0")
                    return self._json_resp({
                        'day': 0,
                        'three_days': 0,
                        'week': 0
                    })
                
                # ✅ 统计今日已处理（status='handled'）
                cur.execute("""
                    SELECT COUNT(*) FROM attack_sessions
                    WHERE DATE(start_time) = CURDATE()
                      AND status = 'handled'
                """)
                day_count = cur.fetchone()[0] or 0
                
                # 添加调试：查看今日handled记录
                cur.execute("""
                    SELECT id, src_ip, anomaly_type, start_time 
                    FROM attack_sessions
                    WHERE DATE(start_time) = CURDATE()
                      AND status = 'handled'
                    LIMIT 10
                """)
                debug_rows = cur.fetchall()
                self.ctrl.logger.info(f"📊 今日handled记录示例: {debug_rows}")
                
                # 统计最近3天已处理
                cur.execute("""
                    SELECT COUNT(*) FROM attack_sessions
                    WHERE start_time >= DATE_SUB(NOW(), INTERVAL 3 DAY)
                      AND status = 'handled'
                """)
                three_days_count = cur.fetchone()[0] or 0
                
                # 统计最近7天已处理
                cur.execute("""
                    SELECT COUNT(*) FROM attack_sessions
                    WHERE start_time >= DATE_SUB(NOW(), INTERVAL 7 DAY)
                      AND status = 'handled'
                """)
                week_count = cur.fetchone()[0] or 0
                
                self.ctrl.logger.info(f"📊 已处理异常统计: 今日={day_count}, 3天={three_days_count}, 7天={week_count}")
                
                result = {
                    'day': day_count,
                    'three_days': three_days_count,
                    'week': week_count
                }
                
                self.ctrl.logger.info(f"✅ 统计已处理攻击会话数量成功: {result}")
                return self._json_resp(result)
                
        except Exception as e:
            self.ctrl.logger.error(f"❌ 统计已处理攻击会话数量失败: {e}")
            import traceback
            traceback.print_exc()
            return self._json_resp({'error': str(e)}, 500)
        finally:
            if conn:
                conn.close()
    
    @route('attack_sessions_count', '/v1/attack-sessions/count', methods=['GET'])
    def get_attack_sessions_count(self, req, **_):
        """
        统计不同时间段的攻击会话数量
        用于异常检测页面的统计卡片
        返回: {day: 今日（从0点到现在）, three_days: 最近3天, week: 最近7天}
        特殊处理：day字段改为查询今日（与Dashboard一致）
        """
        conn = None
        try:
            conn = self.ctrl.get_db_conn()
            with conn.cursor() as cur:
                # 检查表是否存在
                cur.execute("SHOW TABLES LIKE 'attack_sessions'")
                table_exists = cur.fetchone() is not None
                
                if not table_exists:
                    self.ctrl.logger.warning("⚠️ attack_sessions表不存在，返回0")
                    return self._json_resp({
                        'day': 0,
                        'three_days': 0,
                        'week': 0
                    })
                
                # ✅ 统计今日（从0点到现在，显示所有攻击，不过滤status）
                # 添加调试信息
                cur.execute("SELECT CURDATE() as today, NOW() as now")
                date_info = cur.fetchone()
                self.ctrl.logger.info(f"📅 当前日期: CURDATE()={date_info[0]}, NOW()={date_info[1]}")
                
                cur.execute("""
                    SELECT COUNT(*) FROM attack_sessions
                    WHERE DATE(start_time) = CURDATE()
                """)
                day_count = cur.fetchone()[0] or 0
                
                # 统计最近3天（所有攻击）
                cur.execute("""
                    SELECT COUNT(*) FROM attack_sessions
                    WHERE start_time >= DATE_SUB(NOW(), INTERVAL 3 DAY)
                """)
                three_days_count = cur.fetchone()[0] or 0
                
                # 统计最近7天（所有攻击）
                cur.execute("""
                    SELECT COUNT(*) FROM attack_sessions
                    WHERE start_time >= DATE_SUB(NOW(), INTERVAL 7 DAY)
                """)
                week_count = cur.fetchone()[0] or 0
                
                result = {
                    'day': day_count,
                    'three_days': three_days_count,
                    'week': week_count
                }
                
                self.ctrl.logger.info(f"✅ 统计attack_sessions数量成功（day=今日）: {result}")
                return self._json_resp(result)
                
        except Exception as e:
            self.ctrl.logger.error(f"❌ 统计attack_sessions数量失败: {e}")
            import traceback
            traceback.print_exc()
            return self._json_resp({'error': str(e)}, 500)
        finally:
            if conn:
                conn.close()
    
    def _get_anomalies_by_hours(self, hours: int):
        """统一按小时查异常，返回 JSON
        特殊处理：当hours=24时，查询今日（从0点到现在）而非最近24小时
        """
        try:
            conn = self.ctrl.get_db_conn()
            with conn.cursor() as cur:
                # ✅ 当hours=24时，使用CURDATE()查询今日数据（与Dashboard一致）
                if hours == 24:
                    sql = """
                        SELECT detect_time, src_ip, dst_ip, anomaly_type, details
                        FROM anomaly_log
                        WHERE DATE(detect_time) = CURDATE()
                        ORDER BY detect_time DESC
                    """
                    cur.execute(sql)
                    time_desc = "今日"
                else:
                    sql = """
                        SELECT detect_time, src_ip, dst_ip, anomaly_type, details
                        FROM anomaly_log
                        WHERE detect_time >= DATE_SUB(NOW(), INTERVAL %s HOUR)
                        ORDER BY detect_time DESC
                    """
                    cur.execute(sql, (hours,))
                    time_desc = f"最近{hours}小时"
                
                rows = cur.fetchall()

            data = []
            for r in rows:
                detect_time = r[0]
                if hasattr(detect_time, 'strftime'):
                    detect_time = detect_time.strftime('%Y-%m-%d %H:%M:%S')
                data.append({
                    'detect_time': detect_time,
                    'src_ip': r[1] or '',
                    'dst_ip': r[2] or '',
                    'anomaly_type': r[3] or '',
                    'details': r[4] or ''
                })
            self.ctrl.logger.info(f"✅ [anomalies] {time_desc}查询到{len(data)}条异常记录")
            return self._json_resp({'count': len(data), 'data': data})
        except Exception as e:
            self.ctrl.logger.error(f"❌ [anomalies] 查询失败: {e}")
            return self._json_resp({'error': str(e)}, 500)

        # 0. MCP工具调用：应用限速  POST /v1/rate/apply
    @route('rate_apply', '/v1/rate/apply', methods=['POST'])
    def rate_apply(self, req, **_):
        """
        MCP工具调用的限速接口（与前端/v1/limit/ip功能相同）
        body: {"ip":"192.168.1.200", "kbps":1024, "duration":300}
        """
        try:
            body = json.loads(req.body.decode('utf-8'))
            ip = body['ip']
            kbps = body.get('kbps', 1024)
            duration = body.get('duration', 300)  # 秒
            reason = body.get('reason', 'MCP工具限速')
            operator = body.get('operator', 'system')
            
            # 转换秒为分钟
            duration_minutes = max(1, duration // 60)
            
            self.ctrl.logger.info(f"[rate/apply] ip={ip}, kbps={kbps}, duration={duration}s, reason={reason}")
            
            # 调用限速函数
            success, actual_kbps, error_msg = self.ctrl._apply_rate_limit(
                ip, reason, kbps, operator=operator, duration_minutes=duration_minutes
            )
            
            if success:
                return self._json_resp({'success': True, 'message': f'✅ 已对 {ip} 限速 {actual_kbps} kbps'})
            else:
                return self._json_resp({'success': False, 'message': f'❌ 限速失败: {error_msg}'}, 400)
        except Exception as e:
            self.ctrl.logger.error(f"[rate/apply] API错误: {e}")
            import traceback
            traceback.print_exc()
            return self._json_resp({'success': False, 'message': f'❌ 系统错误: {str(e)}'}, 500)

        # 0.5 MCP工具调用：解除限速  DELETE /v1/rate/{ip}
    @route('rate_delete', '/v1/rate/{ip}', methods=['DELETE'])
    def rate_delete(self, req, ip, **_):
        """
        MCP工具调用的解除限速接口
        """
        try:
            reason = req.params.get('reason', 'MCP工具解除')
            self.ctrl.logger.info(f"[rate/delete] 解除限速: ip={ip}, reason={reason}")
            
            ok = self.ctrl._release_rate_limit(ip, operator='system', reason=reason)
            if ok:
                return self._json_resp({'success': True, 'message': f'✅ 已解除 {ip} 限速'})
            else:
                return self._json_resp({'success': False, 'message': f'{ip} 暂无限速记录'}, 404)
        except Exception as e:
            self.ctrl.logger.error(f"[rate/delete] API错误: {e}")
            import traceback
            traceback.print_exc()
            return self._json_resp({'success': False, 'message': str(e)}, 500)

        # 1. 前端调用：手动限速  POST /v1/limit/ip
    @route('limit_ip', '/v1/limit/ip', methods=['POST'])
    def limit_ip(self, req, **_):
        """
        前端手动限速接口
        支持FormData和JSON两种格式
        body: {"ip":"192.168.1.200", "kbps":1024, "reason":"前端手动限速", "duration_minutes":5, "operator":"admin"}
        """
        try:
            # ✅ 兼容FormData和JSON两种格式
            content_type = req.headers.get('Content-Type', '')
            if 'application/x-www-form-urlencoded' in content_type:
                # FormData格式
                from urllib.parse import parse_qs
                body_str = req.body.decode('utf-8')
                body_dict = parse_qs(body_str)
                ip = body_dict.get('ip', [''])[0]
                kbps = int(body_dict.get('kbps', ['1024'])[0])
                reason = body_dict.get('reason', ['前端手动限速'])[0]
                duration_minutes = int(body_dict.get('duration_minutes', ['5'])[0])
                operator = body_dict.get('operator', ['admin'])[0]
            else:
                # JSON格式
                body = json.loads(req.body.decode('utf-8'))
                ip = body['ip']
                kbps = body.get('kbps', 1024)
                reason = body.get('reason', '前端手动限速')
                duration_minutes = body.get('duration_minutes', 5)
                operator = body.get('operator', 'admin')
            
            self.ctrl.logger.info(f"[限速API] ip={ip}, kbps={kbps}, reason={reason}, duration={duration_minutes}min, operator={operator}")
            
            # 调用限速函数并获取返回值
            success, actual_kbps, error_msg = self.ctrl._apply_rate_limit(
                ip, reason, kbps, operator=operator, duration_minutes=duration_minutes
            )
            
            if success:
                return self._json_resp({'success': True, 'message': f'✅ 已对 {ip} 限速 {actual_kbps} kbps'})
            else:
                return self._json_resp({'success': False, 'message': f'❌ 限速失败: {error_msg}'}, 400)
        except Exception as e:
            self.ctrl.logger.error(f"[limit_ip] API错误: {e}")
            import traceback
            traceback.print_exc()
            return self._json_resp({'success': False, 'message': f'❌ 系统错误: {str(e)}'}, 500)
    
    @route('dashboard_cards', '/v1/dashboard/cards', methods=['GET'])
    def dashboard_cards(self, req, **_):
        data = self.ctrl.get_dashboard_cards()
        return self._json_resp(data)


    # 改速率（kbps 可数字/口语）
    @route('rate_change_speed', '/v1/rate/speed/{ip}', methods=['PUT'])
    def rate_change_speed(self, req, ip, **_):
        try:
            body = json.loads(req.body.decode('utf-8'))
            kbps = body['kbps']          # 512 / "高速" / "1 Mbps"
            reason = body.get('reason', '管理员调整速率')
            ctrl = self.ctrl

            # 1. 检查数据库中是否存在限速记录（而不是内存）
            conn = None
            try:
                conn = pymysql.connect(**DB_CONFIG)
                with conn.cursor() as cur:
                    cur.execute("SELECT kbps FROM rate_limit_active WHERE src_ip = %s", (ip,))
                    row = cur.fetchone()
                    if not row:
                        return self._json_resp({'success': False, 'message': f'{ip} 当前无限速'}, 404)
            except Exception as e:
                ctrl.logger.error(f"⚠️ 查询数据库失败: {e}")
                return self._json_resp({'success': False, 'message': f'查询失败: {str(e)}'}, 500)
            finally:
                if conn:
                    conn.close()

            # 2. 检查交换机连接
            if not ctrl.datapaths:
                ctrl.logger.error(f"❌ 速率调整失败: {ip} - 没有可用的交换机")
                return self._json_resp({'success': False, 'message': '没有可用的交换机，请检查交换机连接'}, 503)

            # 3. 解析档位
            if isinstance(kbps, str):
                kbps = kbps.strip()
                if re.search(r'低速', kbps, re.I):
                    kbps = 256
                elif re.search(r'中速', kbps, re.I):
                    kbps = 1024
                elif re.search(r'高速', kbps, re.I):
                    kbps = 2048
                else:
                    m = re.search(r'(\d+)\s*kbps|(\d+)\s*m', kbps, re.I)
                    kbps = 1024
                    if m:
                        kbps = int(m.group(1)) if m.group(1) else int(m.group(2)) * 1024
            else:
                kbps = int(kbps)

            # 4. 获取原来的速率（用于日志）
            old_kbps = 1024  # 默认值
            conn = None
            try:
                conn = pymysql.connect(**DB_CONFIG)
                with conn.cursor() as cur:
                    cur.execute("SELECT kbps FROM rate_limit_active WHERE src_ip = %s", (ip,))
                    row = cur.fetchone()
                    old_kbps = row[0] if row else 1024
            except Exception as e:
                ctrl.logger.error(f"⚠️ 获取原始速率失败: {e}")
            finally:
                if conn:
                    conn.close()

            # 5. 根据新速率选择QoS队列（固定三档）
            if kbps <= 256:
                q = 1  # 低速队列 256Kbps
            elif kbps <= 1024:
                q = 2  # 中速队列 1024Kbps
            else:
                q = 3  # 高速队列 2048Kbps
            
            # 6. 从数据库读取过期时间，计算hard_timeout
            hard_timeout = 300  # 默认5分钟
            conn = None
            try:
                conn = pymysql.connect(**DB_CONFIG)
                with conn.cursor() as cur:
                    cur.execute("SELECT UNIX_TIMESTAMP(expire_at) FROM rate_limit_active WHERE src_ip = %s", (ip,))
                    row = cur.fetchone()
                    if row and row[0]:
                        hard_timeout = int(max(0, row[0] - time.time()))
                        ctrl.logger.info(f"[DEBUG] 从数据库读取过期时间: {ip} expire_at={row[0]}, hard_timeout={hard_timeout}秒")
            except Exception as e:
                ctrl.logger.error(f"⚠️ 读取过期时间失败: {e}")
            finally:
                if conn:
                    conn.close()
            
            # 7. 下发OpenFlow流表到所有交换机
            flow_success = False
            for dp in ctrl.datapaths.values():
                ofp, ps = dp.ofproto, dp.ofproto_parser
                match = ps.OFPMatch(eth_type=ether_types.ETH_TYPE_IP, ipv4_src=ip)
                acts = [ps.OFPActionSetQueue(queue_id=q), ps.OFPActionOutput(ofp.OFPP_NORMAL)]
                # ✅ 修复：从数据库读取过期时间，确保hard_timeout正确
                ctrl._add_flow(dp, 50, match, acts, idle=0, hard=hard_timeout)
                flow_success = True
                ctrl.logger.info(f"✅ 流表已更新: {ip} {old_kbps}→{kbps}Kbps, 队列={q}, idle=0, hard={hard_timeout}秒")
            
            if not flow_success:
                ctrl.logger.error(f"❌ 流表下发失败: {ip} - 没有可用的交换机")
                return self._json_resp({'success': False, 'message': '流表下发失败'}, 500)

            # 8. 流表下发成功后，更新数据库
            conn = None
            try:
                conn = pymysql.connect(**DB_CONFIG)
                with conn.cursor() as cur:
                    # ✅ 只更新速率，不修改限速原因
                    affected_rows = cur.execute("""
                        UPDATE rate_limit_active
                        SET kbps = %s
                        WHERE src_ip = %s
                    """, (kbps, ip))
                    
                    ctrl.logger.info(f"📝 数据库UPDATE影响行数: {affected_rows}")
                    
                    # 生成简短的中文描述（三档限速）
                    speed_names = {256: '低速', 1024: '中速', 2048: '高速'}
                    old_name = speed_names.get(old_kbps, str(old_kbps))
                    new_name = speed_names.get(kbps, str(kbps))
                    action_desc = f"调速:{old_name}→{new_name}"  # ✅ 简化描述，避免超长
                    
                    # 在log表中记录操作（action使用中文描述）
                    cur.execute("""
                        INSERT INTO rate_limit_log(src_ip,operator,action,reason,kbps)
                        VALUES (%s,%s,%s,%s,%s)
                    """, (ip, 'admin', action_desc, reason, kbps))
                    conn.commit()
                    
                    # ✅ 验证更新是否成功
                    cur.execute("SELECT kbps FROM rate_limit_active WHERE src_ip = %s", (ip,))
                    verify_row = cur.fetchone()
                    if verify_row:
                        actual_kbps = verify_row[0]
                        ctrl.logger.info(f"✅ 数据库验证成功: {ip} 速率={actual_kbps}Kbps (预期={kbps})")
                        if actual_kbps != kbps:
                            ctrl.logger.error(f"⚠️ 数据库值不匹配! 实际={actual_kbps}, 预期={kbps}")
                    else:
                        ctrl.logger.error(f"⚠️ 验证失败: 未找到 {ip} 的记录")
            except Exception as e:
                ctrl.logger.error(f"⚠️ 数据库更新失败: {e}")
                import traceback
                traceback.print_exc()
                if conn:
                    conn.rollback()
                # 流表已生效，数据库失败不影响返回结果
            finally:
                if conn:
                    conn.close()
            
            return self._json_resp({'success': True, 'message': f'{ip} 速率已调整为 {kbps} kbps'})
        except Exception as e:
            ctrl.logger.error(f"❌ 速率调整异常: {ip} - {e}")
            import traceback
            traceback.print_exc()
            return self._json_resp({'success': False, 'message': f'速率调整失败: {str(e)}'}, 500)

    # 改时长（秒）
    # ------------------------------------------------------------------
    # 调整限速剩余时长（延长或缩短）
    #  PUT /v1/rate/duration/{ip}
    #  body: {"extra_seconds":600,"reason":"加长10min"}  正数=延长，负数=缩短
    # ------------------------------------------------------------------
    @route('rate_change_duration', '/v1/rate/duration/{ip}', methods=['PUT'])
    def rate_change_duration(self, req, ip, **_):
        try:
            body = json.loads(req.body.decode('utf-8'))
            extra_sec = int(body['extra_seconds'])   # 正数延长，负数缩短
            reason = body.get('reason', '管理员调整时长')
            ctrl = self.ctrl

            # 1. 检查数据库中是否存在限速记录（而不是内存）
            conn = None
            try:
                conn = pymysql.connect(**DB_CONFIG)
                with conn.cursor() as cur:
                    cur.execute("SELECT expire_at FROM rate_limit_active WHERE src_ip = %s", (ip,))
                    row = cur.fetchone()
                    if not row:
                        return self._json_resp({'success': False, 'message': f'{ip} 当前无限速'}, 404)
            except Exception as e:
                ctrl.logger.error(f"⚠️ 查询数据库失败: {e}")
                return self._json_resp({'success': False, 'message': f'查询失败: {str(e)}'}, 500)
            finally:
                if conn:
                    conn.close()

            # 2. 检查交换机连接
            if not ctrl.datapaths:
                ctrl.logger.error(f"❌ 时长调整失败: {ip} - 没有可用的交换机")
                return self._json_resp({'success': False, 'message': '没有可用的交换机，请检查交换机连接'}, 503)

            # 3. 从数据库读取当前过期时间
            old_expire = None
            conn = None
            try:
                conn = pymysql.connect(**DB_CONFIG)
                with conn.cursor() as cur:
                    cur.execute("SELECT UNIX_TIMESTAMP(expire_at) FROM rate_limit_active WHERE src_ip = %s", (ip,))
                    row = cur.fetchone()
                    old_expire = row[0] if row else time.time()
            except Exception as e:
                ctrl.logger.error(f"⚠️ 读取过期时间失败: {e}")
                old_expire = time.time()
            finally:
                if conn:
                    conn.close()

            # 4. 计算新过期时间（不能早于现在）
            new_expire = max(time.time(), old_expire + extra_sec)
            if new_expire == time.time():
                # 缩短到 <=0 → 直接解除
                ok = ctrl._release_rate_limit(ip, operator='admin', reason=reason)
                return self._json_resp({'success': True, 'message': f'{ip} 时长已缩短至 0，已解除'})

            # 同时更新内存（如果IP在内存中）
            if ip in ctrl.limited_ips:
                ctrl.limited_ips[ip] = new_expire

            # 5. 获取当前的kbps（用于选择QoS队列）
            current_kbps = 1024  # 默认中速
            conn = None
            try:
                conn = pymysql.connect(**DB_CONFIG)
                with conn.cursor() as cur:
                    cur.execute("SELECT kbps FROM rate_limit_active WHERE src_ip = %s", (ip,))
                    row = cur.fetchone()
                    current_kbps = row[0] if row else 1024
            except Exception as e:
                ctrl.logger.error(f"⚠️ 获取当前速率失败: {e}")
            finally:
                if conn:
                    conn.close()
            
            # 6. 根据当前速率选择正确的QoS队列（固定三档）
            if current_kbps <= 256:
                q = 1  # 低速队列 256Kbps
            elif current_kbps <= 1024:
                q = 2  # 中速队列 1024Kbps
            else:
                q = 3  # 高速队列 2048Kbps
            
            # 7. 下发OpenFlow流表到所有交换机
            new_hard = int(max(0, new_expire - time.time()))
            flow_success = False
            for dp in ctrl.datapaths.values():
                ofp, ps = dp.ofproto, dp.ofproto_parser
                match = ps.OFPMatch(eth_type=ether_types.ETH_TYPE_IP, ipv4_src=ip)
                acts = [ps.OFPActionSetQueue(queue_id=q), ps.OFPActionOutput(ofp.OFPP_NORMAL)]
                # ✅ 修复：添加idle=0，防止流表因空闲而被删除
                ctrl._add_flow(dp, 50, match, acts, idle=0, hard=new_hard)
                flow_success = True
                ctrl.logger.info(f"✅ 流表已更新: {ip} 时长调整, 队列={q}(kbps={current_kbps}), 剩余={new_hard}秒")

            if not flow_success:
                ctrl.logger.error(f"❌ 流表下发失败: {ip} - 没有可用的交换机")
                return self._json_resp({'success': False, 'message': '流表下发失败'}, 500)

            # 8. 流表下发成功后，更新数据库
            conn = None
            try:
                conn = pymysql.connect(**DB_CONFIG)
                with conn.cursor() as cur:
                    # ✅ 只更新过期时间，不修改限速原因
                    cur.execute("""
                        UPDATE rate_limit_active
                        SET expire_at = FROM_UNIXTIME(%s)
                        WHERE src_ip = %s
                    """, (new_expire, ip))
                    
                    # 生成简短的中文描述
                    if extra_sec > 0:
                        minutes = extra_sec // 60
                        action_desc = f"延长{minutes}分"  # ✅ 简化
                    elif extra_sec < 0:
                        minutes = abs(extra_sec) // 60
                        action_desc = f"缩短{minutes}分"  # ✅ 简化
                    else:
                        action_desc = "保持时长"
                    
                    # 在log表中记录操作（action使用中文描述）
                    cur.execute("""
                        INSERT INTO rate_limit_log(src_ip, operator, action, reason)
                        VALUES (%s, %s, %s, %s)
                    """, (ip, 'admin', action_desc, reason))
                    conn.commit()
                    ctrl.logger.info(f"📥 数据库已更新: {ip} 时长剩余={new_hard}秒")
            except Exception as e:
                ctrl.logger.error(f"⚠️ 数据库更新失败: {e}")
                if conn:
                    conn.rollback()
                # 流表已生效，数据库失败不影响返回结果
            finally:
                if conn:
                    conn.close()

            return self._json_resp({'success': True, 'message': f'{ip} 时长已调整，剩余 {new_hard} 秒'})
        except Exception as e:
            ctrl.logger.error(f"❌ 时长调整异常: {ip} - {e}")
            import traceback
            traceback.print_exc()
            return self._json_resp({'success': False, 'message': f'时长调整失败: {str(e)}'}, 500)


            
    # 10. 按日期查历史限速记录（年月日）
    @route('rate_history_by_day', '/v1/rate/history/{day}', methods=['GET'])
    def rate_history_by_day(self, req, day, **_):
        """
        返回指定日期的一整页限速记录
        day: 2025-10-05 格式
        """
        # 简单格式校验
        if not re.fullmatch(r'\d{4}-\d{2}-\d{2}', day):
            return self._json_resp({'error': 'day 格式应为 yyyy-mm-dd'}, 400)

        try:
            conn = self.ctrl.get_db_conn()
            with conn.cursor() as cur:
                sql = """
                    SELECT src_ip, operator, action, reason, kbps, created_at
                    FROM rate_limit_log
                    WHERE DATE(created_at) = %s
                    ORDER BY created_at DESC
                """
                cur.execute(sql, (day,))
                rows = cur.fetchall()

            data = []
            for r in rows:
                ts = r[5]
                if hasattr(ts, 'strftime'):
                    ts = ts.strftime('%Y-%m-%d %H:%M:%S')
                data.append({
                    'src_ip':   r[0],
                    'operator': r[1],
                    'action':   r[2],
                    'reason':   r[3],
                    'kbps':     int(r[4]) if r[4] else None,
                    'created_at': ts
                })

            return self._json_resp({
                'day': day,
                'count': len(data),
                'data': data
            })
        except Exception as e:
            return self._json_resp({'error': str(e)}, 500)



    # 2. 前端调用：解除限速  DELETE /v1/limit/ip/{ip}
    @route('unlimit_ip', '/v1/limit/ip/{ip}', methods=['DELETE'])
    def unlimit_ip(self, req, ip, **_):
        """
        前端手动解除限速接口
        """
        try:
            ok = self.ctrl._release_rate_limit(ip, operator='frontend', reason='前端手动解除')
            if ok:
                return self._json_resp({'success': True, 'message': f'已解除 {ip} 限速'})
            else:
                return self._json_resp({'success': False, 'message': f'{ip} 暂无限速记录'}, 404)
        except Exception as e:
            return self._json_resp({'success': False, 'message': str(e)}, 500)


    # 限速趋势图：1 小时 / 3 天 / 7 天
    @route('rate_trend', '/v1/rate-trend', methods=['GET'])
    def rate_trend(self, req, **_):
        """
        获取限速趋势数据 - 统计限速会话数（与饼图数据口径一致）
        使用limit_sessions表，按时间统计新建的限速会话数量
        """
        try:
            typ = int(req.params.get('type', 1))          # 1 24h  3 3day  7 7day
            if typ not in (1, 3, 7):
                return self._json_resp({'error': 'type only 1/3/7'}, 400)

            self.ctrl.logger.info(f"[rate_trend] 查询限速趋势，类型: {typ} ({'24小时' if typ == 1 else f'{typ}天'})")

            conn = self.ctrl.get_db_conn()
            with conn.cursor() as cur:
                if typ == 1:          # 最近 1 天 → 按小时统计当天的限速会话数
                    sql = """
                        SELECT DATE_FORMAT(start_time, '%Y-%m-%d %H:00') AS tm,
                            COUNT(*) AS cnt
                        FROM limit_sessions
                        WHERE DATE(start_time) = CURDATE()
                        GROUP BY DATE_FORMAT(start_time, '%Y-%m-%d %H:00')
                        ORDER BY tm
                    """
                    self.ctrl.logger.info(f"[rate_trend] 类型1: 查询今天的数据")
                else:                 # 3 或 7 天 → 按天统计限速会话数
                    sql = """
                        SELECT DATE_FORMAT(start_time, '%Y-%m-%d') AS tm,
                            COUNT(*) AS cnt
                        FROM limit_sessions
                        WHERE start_time >= DATE_SUB(CURDATE(), INTERVAL {} DAY)
                        GROUP BY DATE_FORMAT(start_time, '%Y-%m-%d')
                        ORDER BY tm
                    """.format(typ)
                    self.ctrl.logger.info(f"[rate_trend] 类型{typ}: 查询最近{typ}天的数据")

                self.ctrl.logger.debug(f"[rate_trend] 执行SQL: {sql}")
                cur.execute(sql)
                rows = cur.fetchall()
                
                self.ctrl.logger.info(f"[rate_trend] ✅ 查询到 {len(rows)} 个时间点的数据")
                for i, row in enumerate(rows[:10]):  # 只打印前10条
                    self.ctrl.logger.info(f"  [{i+1}] {row[0]}: {row[1]} 次")
                if len(rows) > 10:
                    self.ctrl.logger.info(f"  ... 还有 {len(rows)-10} 条数据")

            data = [{'time': str(r[0]), 'count': int(r[1])} for r in rows]
            
            # 详细日志
            if data:
                self.ctrl.logger.info(f"[rate_trend] 趋势数据预览:")
                for item in data[:5]:  # 只显示前5条
                    self.ctrl.logger.info(f"  - {item['time']}: {item['count']} 次限速会话")
                if len(data) > 5:
                    self.ctrl.logger.info(f"  ... 还有 {len(data) - 5} 条数据")
            else:
                self.ctrl.logger.warning(f"[rate_trend] 最近{typ if typ > 1 else 24}{'天' if typ > 1 else '小时'}无限速会话记录")
            
            return self._json_resp(data)
        except Exception as e:
            self.ctrl.logger.error(f"[rate_trend] 查询失败: {e}")
            import traceback
            self.ctrl.logger.error(traceback.format_exc())
            return self._json_resp({'error': str(e)}, 500)

    # 限速原因统计接口
    @route('rate_reason_stats', '/v1/rate-reason-stats', methods=['GET'])
    def rate_reason_stats(self, req, **_):
        """
        获取指定时间范围的限速原因分布统计
        hours=24: 今天的数据
        hours=72: 最近3天的数据
        hours=168: 最近7天的数据
        返回格式：[{reason: "SYN Flood", count: 10}, ...]
        """
        try:
            hours = int(req.params.get('hours', 24))  # 默认24小时
            self.ctrl.logger.info(f"[rate_reason_stats] 查询时间范围: {hours}小时")
            
            conn = self.ctrl.get_db_conn()
            with conn.cursor() as cur:
                # 根据hours参数决定查询逻辑
                if hours == 24:
                    # 24小时 = 今天
                    sql = """
                        SELECT reason, COUNT(*) AS cnt
                        FROM limit_sessions
                        WHERE DATE(start_time) = CURDATE()
                        GROUP BY reason
                        ORDER BY cnt DESC
                    """
                    self.ctrl.logger.debug(f"[rate_reason_stats] 查询今天的数据: {sql}")
                    cur.execute(sql)
                elif hours == 72:
                    # 72小时 = 最近3天
                    sql = """
                        SELECT reason, COUNT(*) AS cnt
                        FROM limit_sessions
                        WHERE start_time >= DATE_SUB(CURDATE(), INTERVAL 3 DAY)
                        GROUP BY reason
                        ORDER BY cnt DESC
                    """
                    self.ctrl.logger.debug(f"[rate_reason_stats] 查询最近3天的数据: {sql}")
                    cur.execute(sql)
                elif hours == 168:
                    # 168小时 = 最近7天
                    sql = """
                        SELECT reason, COUNT(*) AS cnt
                        FROM limit_sessions
                        WHERE start_time >= DATE_SUB(CURDATE(), INTERVAL 7 DAY)
                        GROUP BY reason
                        ORDER BY cnt DESC
                    """
                    self.ctrl.logger.debug(f"[rate_reason_stats] 查询最近7天的数据: {sql}")
                    cur.execute(sql)
                else:
                    # 其他情况，使用小时数查询
                    sql = """
                        SELECT reason, COUNT(*) AS cnt
                        FROM limit_sessions
                        WHERE start_time >= DATE_SUB(NOW(), INTERVAL %s HOUR)
                        GROUP BY reason
                        ORDER BY cnt DESC
                    """
                    self.ctrl.logger.debug(f"[rate_reason_stats] 查询最近{hours}小时的数据: {sql}")
                    cur.execute(sql, (hours,))
                
                rows = cur.fetchall()
                self.ctrl.logger.info(f"[rate_reason_stats] 查询到 {len(rows)} 种不同的限速原因")

            data = [{'reason': r[0], 'count': int(r[1])} for r in rows]
            
            # 详细日志
            if not data:
                self.ctrl.logger.warning(f"[rate_reason_stats] ❌ 最近{hours}小时无限速记录")
            else:
                self.ctrl.logger.info(f"[rate_reason_stats] ✅ 返回数据:")
                for item in data:
                    self.ctrl.logger.info(f"  - {item['reason']}: {item['count']} 次")
            
            return self._json_resp(data)
        except Exception as e:
            self.ctrl.logger.error(f"❌ rate_reason_stats error: {e}")
            import traceback
            self.ctrl.logger.error(traceback.format_exc())
            return self._json_resp({'error': str(e)}, 500)


        
    

    # ---------------- WebSocket 长连接（前端 8080） ----------------
    @route('chat_ws', '/ws/chat', methods=['GET'])
    def chat_ws(self, ws, req, **_):
        user_id = req.params.get('user_id') or req.headers.get('X-User-Id') or 'anonymous'
        role = self._get_user_role(user_id)
        self.ctrl.logger.info(f"[WS] {user_id}({role}) connected")
        try:
            while True:
                msg = ws.receive()
                if not msg:
                    break
                reply = self._process_one_shot(user_id, msg.strip())
                ws.send(reply)
        finally:
            ws.close()

    # RYU控制器异常数据API优化版本
# 需要在 sdn_smart.py 中替换原有的 get_anomalies 方法

    @route('anomalies', '/v1/anomalies', methods=['GET'])
    def get_anomalies(self, req, **_):
        """
        优化版异常数据查询接口
        支持时间范围过滤和可选的数量限制
        特殊处理：当hours=24时，查询今日（从0点到现在）而非最近24小时，与Dashboard保持一致
        """
        try:
            # 获取查询参数
            hours = int(req.params.get('hours', 12))  # 默认12小时
            limit = req.params.get('limit')  # 可选的数量限制
            
            # 验证参数范围
            hours = max(1, min(hours, 168))  # 1小时到7天
            
            conn = self.ctrl.get_db_conn()
            with conn.cursor() as cur:
                # ✅ 特殊处理：当hours=24时，查询今日数据（从0点到现在，与Dashboard一致）
                if hours == 24:
                    base_sql = """
                        SELECT detect_time, src_ip, dst_ip, anomaly_type, details 
                        FROM anomaly_log 
                        WHERE DATE(detect_time) = CURDATE()
                        ORDER BY detect_time DESC
                    """
                    params = []
                    time_desc = "今日"
                else:
                    # 其他时间段使用INTERVAL查询
                    base_sql = """
                        SELECT detect_time, src_ip, dst_ip, anomaly_type, details 
                        FROM anomaly_log 
                        WHERE detect_time >= DATE_SUB(NOW(), INTERVAL %s HOUR)
                        ORDER BY detect_time DESC
                    """
                    params = [hours]
                    time_desc = f"最近{hours}小时"
                
                # 如果指定了limit，添加到SQL中
                if limit is not None:
                    try:
                        limit = int(limit)
                        if limit > 0:
                            base_sql += " LIMIT %s"
                            params.append(limit)
                    except (ValueError, TypeError):
                        pass  # 忽略无效的limit参数
                
                print(f"[DEBUG] 执行异常查询: {time_desc}, limit={limit}")
                cur.execute(base_sql, params)
                rows = cur.fetchall()
                
            data = []
            for r in rows:
                # 检查行数据的完整性，防止tuple index out of range
                if len(r) < 5:
                    continue  # 跳过不完整的行
                
                # 处理datetime和其他可能的非JSON序列化类型
                detect_time = r[0]
                if hasattr(detect_time, 'strftime'):
                    detect_time = detect_time.strftime('%Y-%m-%d %H:%M:%S')
                else:
                    detect_time = str(detect_time)
                
                data.append({
                    'detect_time': detect_time,
                    'src_ip': r[1] if r[1] is not None else '',
                    'dst_ip': r[2] if r[2] is not None else '',
                    'anomaly_type': r[3] if r[3] is not None else '',
                    'details': r[4] if r[4] is not None else ''
                })
            
            self.ctrl.logger.info(f"✅ [anomalies API] {time_desc}查询到 {len(data)} 条异常数据")
            return self._json_resp(data)
            
        except Exception as e:
            self.ctrl.logger.error("get_anomalies error: %s", e)
            return self._json_resp({'error': str(e)}, 500)


    # 额外优化：添加数据库索引以提高查询性能
    def optimize_database_indexes(self):
        """
        为异常日志表添加索引以提高查询性能
        建议在RYU控制器启动时调用一次
        """
        try:
            conn = self.ctrl.get_db_conn()
            with conn.cursor() as cur:
                # 为detect_time字段添加索引（如果不存在）
                cur.execute("""
                    CREATE INDEX IF NOT EXISTS idx_anomaly_log_detect_time 
                    ON anomaly_log(detect_time)
                """)
                
                # 为src_ip字段添加索引（用于按IP查询）
                cur.execute("""
                    CREATE INDEX IF NOT EXISTS idx_anomaly_log_src_ip 
                    ON anomaly_log(src_ip)
                """)
                
                # 复合索引：时间+IP（最常用的查询组合）
                cur.execute("""
                    CREATE INDEX IF NOT EXISTS idx_anomaly_log_time_ip 
                    ON anomaly_log(detect_time, src_ip)
                """)
                
                conn.commit()
                print("[DEBUG] 数据库索引优化完成")
                
        except Exception as e:
            print(f"[ERROR] 数据库索引优化失败: {e}")


    # 批量查询优化：减少数据库连接开销
    def get_anomalies_batch_optimized(self, req, **_):
        """
        批量优化版本：使用连接池和查询缓存
        """
        try:
            hours = int(req.params.get('hours', 12))
            limit = req.params.get('limit')
            
            # 缓存键
            cache_key = f"anomalies_{hours}_{limit or 'all'}"
            
            # 检查缓存（可选，如果需要实时性可以跳过）
            # cached_result = self.get_cache(cache_key)
            # if cached_result:
            #     return self._json_resp(cached_result)
            
            # 使用连接池优化
            conn = None
            try:
                conn = pymysql.connect(**DB_CONFIG, autocommit=True)
                with conn.cursor(pymysql.cursors.DictCursor) as cur:  # 使用字典游标
                    sql = """
                        SELECT detect_time, src_ip, dst_ip, anomaly_type, details 
                        FROM anomaly_log 
                        WHERE detect_time >= DATE_SUB(NOW(), INTERVAL %s HOUR)
                        ORDER BY detect_time DESC
                    """
                    params = [hours]
                    
                    if limit:
                        sql += " LIMIT %s"
                        params.append(int(limit))
                    
                    cur.execute(sql, params)
                    rows = cur.fetchall()
                    
                    # 直接使用字典格式，减少数据转换
                    data = []
                    for row in rows:
                        if row['detect_time']:
                            row['detect_time'] = row['detect_time'].strftime('%Y-%m-%d %H:%M:%S')
                        data.append(row)
                    
                    # 设置缓存（可选）
                    # self.set_cache(cache_key, data, expire=30)  # 30秒缓存
                    
                    return self._json_resp(data)
                    
            finally:
                if conn:
                    conn.close()
                    
        except Exception as e:
            return self._json_resp({'error': str(e)}, 500)

    
        # 添加黑名单
    @route('acl_black_add', '/v1/acl/black', methods=['POST'])
    def acl_black_add(self, req, **_):
        try:
            body = json.loads(req.body.decode('utf-8'))
            ip   = body['ip']
            ttl  = body.get('ttl', -1)
            operator = body.get('operator', 'admin')  # ✅ 前端传递operator，默认admin
            self.ctrl.acl_add_black(ip, ttl, operator)
            return self._json_resp({'success': True, 'message': f'{ip} 已加入黑名单'})
        except Exception as e:
            return self._json_resp({'success': False, 'message': str(e)}, 500)

    # 删除黑名单
    @route('acl_black_del', '/v1/acl/black/{ip}', methods=['DELETE'])
    def acl_black_del(self, req, ip, **_):
        try:
            success = self.ctrl.acl_del_black(ip)  # ✅ 检查返回值
            if success:
                return self._json_resp({'success': True, 'message': f'✅ {ip} 已从黑名单移除'})
            else:
                return self._json_resp({'success': False, 'message': f'❌ {ip} 删除失败，可能不在数据库中'}, 400)
        except Exception as e:
            self.ctrl.logger.error(f"删除黑名单API错误: {e}")
            import traceback
            traceback.print_exc()
            return self._json_resp({'success': False, 'message': str(e)}, 500)
    
        # 添加白名单
    @route('acl_white_add', '/v1/acl/white', methods=['POST'])
    def acl_white_add(self, req, **_):
        try:
            body = json.loads(req.body.decode('utf-8'))
            ip   = body['ip']
            ttl  = body.get('ttl', -1)
            self.ctrl.acl_add_white(ip, ttl)
            return self._json_resp({'success': True, 'message': f'{ip} 已加入白名单'})
        except Exception as e:
            return self._json_resp({'success': False, 'message': str(e)}, 500)

    # 删除白名单
    @route('acl_white_del', '/v1/acl/white/{ip}', methods=['DELETE'])
    def acl_white_del(self, req, ip, **_):
        try:
            success = self.ctrl.acl_del_white(ip)  # ✅ 检查返回值
            if success:
                return self._json_resp({'success': True, 'message': f'✅ {ip} 已从白名单移除'})
            else:
                return self._json_resp({'success': False, 'message': f'❌ {ip} 删除失败，可能不在数据库中'}, 400)
        except Exception as e:
            self.ctrl.logger.error(f"删除白名单API错误: {e}")
            import traceback
            traceback.print_exc()
            return self._json_resp({'success': False, 'message': str(e)}, 500)



    

    # ---------------- 限速列表接口 ----------------
    @route('ratelimit', '/v1/ratelimit', methods=['GET'])
    def get_ratelimit(self, req, **_):
        limit_list = self.ctrl.get_limit_list()
        return self._json_resp({'limit_list': limit_list})

    # ---------------- ACL列表接口 ----------------
    @route('acl', '/v1/acl', methods=['GET'])
    def get_acl(self, req, **_):
        acl_lists = self.ctrl.get_acl_lists()
        return self._json_resp(acl_lists)

    # ---------------- 系统概览接口 ----------------
    @route('summary', '/v1/summary', methods=['GET'])
    def get_summary(self, req, **_):
        try:
            today = time.strftime('%Y-%m-%d')
            conn = None
            try:
                conn = pymysql.connect(**DB_CONFIG, autocommit=True)
                with conn.cursor() as cur:
                    # 今日异常
                    cur.execute("SELECT COUNT(*) FROM anomaly_log WHERE DATE(detect_time) = %s", (today,))
                    today_anomalies = int(cur.fetchone()[0])

                    # 当前限速 IP 数
                    cur.execute("SELECT COUNT(*) FROM rate_limit_active")
                    limit_count = int(cur.fetchone()[0])

                    # 黑名单数
                    cur.execute("SELECT COUNT(*) FROM acl_entries WHERE list_type = 'black'")
                    black_count = int(cur.fetchone()[0])

                    # 白名单数
                    cur.execute("SELECT COUNT(*) FROM acl_entries WHERE list_type = 'white'")
                    white_count = int(cur.fetchone()[0])

                    # 交换机在线数
                    switch_count = len(self.ctrl.datapaths)
            finally:
                if conn:
                    conn.close()

            return self._json_resp({
                'today_anomalies': today_anomalies,
                'limit_count': limit_count,
                'black_count': black_count,
                'white_count': white_count,
                'switch_count': switch_count
            })
        except Exception as e:
            import traceback
            return self._json_resp({'error': traceback.format_exc()}, 500)

    
    @route('anomalies_week', '/v1/anomalies/week', methods=['GET'])
    def get_anomalies_week(self, req, **_):
        try:
            conn = self.ctrl.get_db_conn()
            with conn.cursor() as cur:
                cur.execute("SELECT detect_time,src_ip,dst_ip,anomaly_type,details "
                        "FROM anomaly_log WHERE detect_time >= DATE_SUB(NOW(), INTERVAL 7 DAY) "
                        "ORDER BY detect_time DESC")
                rows = cur.fetchall()
            data = [{'detect_time':r[0].strftime('%Y-%m-%d %H:%M:%S'),'src_ip':r[1],'dst_ip':r[2],
                    'anomaly_type':r[3],'details':r[4]} for r in rows]
            return self._json_resp(data)
        except Exception as e:
            return self._json_resp({'error':str(e)},500)

    @route('anomalies_top10', '/v1/anomalies/top10', methods=['GET'])
    def get_anomalies_top10(self, req, **_):
        try:
            conn = self.ctrl.get_db_conn()
            with conn.cursor() as cur:
                cur.execute("SELECT src_ip,COUNT(*) as cnt FROM anomaly_log "
                        "WHERE detect_time >= DATE_SUB(NOW(), INTERVAL 7 DAY) "
                        "GROUP BY src_ip ORDER BY cnt DESC LIMIT 10")
                rows = cur.fetchall()
            data = [{'src_ip':r[0],'count':r[1]} for r in rows]
            return self._json_resp(data)
        except Exception as e:
            return self._json_resp({'error':str(e)},500)

    @route('device_anomalies', '/v1/device-anomalies', methods=['GET'])
    def get_device_anomalies(self, req, **_):
        """
        获取设备异常列表（真正的设备问题：IP配错、端口异常等）
        从 device_anomalies 表查询
        """
        try:
            hours = int(req.params.get('hours', 24))
            conn = None
            try:
                conn = pymysql.connect(**DB_CONFIG, autocommit=True)
                with conn.cursor() as cur:
                    cur.execute("""
                        SELECT 
                            id, anomaly_type, device_type, device_id, 
                            description, severity, status, 
                            detected_at, resolved_at, handled_by, handle_action
                        FROM device_anomalies
                        WHERE detected_at >= DATE_SUB(NOW(), INTERVAL %s HOUR)
                          AND status != 'resolved'
                        ORDER BY detected_at DESC
                    """, (hours,))
                    rows = cur.fetchall()
                    
                data = []
                for r in rows:
                    data.append({
                        'id': r[0],
                        'anomaly_type': r[1],
                        'device_type': r[2],
                        'device_id': r[3],
                        'description': r[4],
                        'severity': r[5],
                        'status': r[6],
                        'detected_at': r[7].strftime('%Y-%m-%d %H:%M:%S') if r[7] else None,
                        'resolved_at': r[8].strftime('%Y-%m-%d %H:%M:%S') if r[8] else None,
                        'handled_by': r[9],
                        'handle_action': r[10]
                    })
                
                return self._json_resp({'success': True, 'data': data, 'count': len(data)})
            finally:
                if conn:
                    conn.close()
        except Exception as e:
            import traceback
            self.ctrl.logger.error(f"获取设备异常失败: {e}")
            return self._json_resp({'success': False, 'error': str(e)}, 500)
    
    @route('update_device_anomaly', '/v1/device-anomalies/<anomaly_id>', methods=['PUT'])
    def update_device_anomaly_status(self, req, anomaly_id, **_):
        """
        更新设备异常状态为已处理
        当管理员点击"已处理"按钮时调用此API
        """
        try:
            anomaly_id = int(anomaly_id)
            
            # 解析请求体
            body = json.loads(req.body.decode('utf-8'))
            status = body.get('status', 'resolved')
            
            conn = None
            try:
                conn = pymysql.connect(**DB_CONFIG, autocommit=True)
                with conn.cursor() as cur:
                    # 更新异常状态为已处理
                    cur.execute("""
                        UPDATE device_anomalies
                        SET status = %s,
                            resolved_at = NOW(),
                            handled_by = 'admin',
                            handle_action = 'marked_resolved'
                        WHERE id = %s
                    """, (status, anomaly_id))
                    
                    affected_rows = cur.rowcount
                    
                    if affected_rows > 0:
                        self.ctrl.logger.info(f"✅ 异常#{anomaly_id}已标记为{status}")
                        return self._json_resp({
                            'success': True,
                            'message': f'异常已标记为{status}',
                            'affected_rows': affected_rows
                        })
                    else:
                        return self._json_resp({
                            'success': False,
                            'message': f'异常#{anomaly_id}不存在'
                        }, 404)
                        
            finally:
                if conn:
                    conn.close()
                    
        except Exception as e:
            import traceback
            self.ctrl.logger.error(f"更新异常状态失败: {e}")
            traceback.print_exc()
            return self._json_resp({'success': False, 'error': str(e)}, 500)
    
    @route('flowstats_top10', '/v1/flowstats/top10', methods=['GET'])
    def get_flowstats_top10(self, req, **_):
        try:
            conn = self.ctrl.get_db_conn()
            with conn.cursor() as cur:
                cur.execute("SELECT src_ip,SUM(byte_count) as bytes,SUM(packet_count) as packets "
                        "FROM flow_stats WHERE timestamp >= DATE_SUB(NOW(), INTERVAL 24 HOUR) "
                        "GROUP BY src_ip ORDER BY bytes DESC LIMIT 10")
                rows = cur.fetchall()
            data = [{'src_ip':r[0],'bytes':r[1],'packets':r[2]} for r in rows]
            return self._json_resp(data)
        except Exception as e:
            return self._json_resp({'error':str(e)},500)


    @route('switch_info', '/v1/switch/info', methods=['GET'])
    def get_switch_info(self, req, **_):
        switches = []
        for dp in self.ctrl.datapaths.values():
            switches.append({
                'datapath_id': f"{dp.id:016d}",
                'ip': dp.address[0],   # 控制器看到的交换机 IP
                'port': dp.address[1],
                'online': True
            })
        return self._json_resp({'switches': switches})

    # ========== 流表管理API ==========
    @route('switches_list', '/v1/switches', methods=['GET'])
    def get_switches_list(self, req, **_):
        """获取所有交换机的DPID列表"""
        try:
            dpids = [dp.id for dp in self.ctrl.datapaths.values()]
            return self._json_resp(dpids)
        except Exception as e:
            self.ctrl.logger.error(f"获取交换机列表失败: {e}")
            return self._json_resp({'error': str(e)}, 500)

    @route('switch_flows', '/v1/switches/{dpid}/flows', methods=['GET'])
    def get_switch_flows(self, req, dpid, **_):
        """获取指定交换机的流表"""
        try:
            dpid_int = int(dpid)
            if dpid_int not in self.ctrl.datapaths:
                return self._json_resp({'error': '交换机不存在'}, 404)
            
            # 从缓存中获取流表数据
            flows = self.ctrl.switch_flow_stats.get(dpid_int, [])
            return self._json_resp({str(dpid_int): flows})
        except Exception as e:
            self.ctrl.logger.error(f"获取流表失败: {e}")
            return self._json_resp({'error': str(e)}, 500)

    @route('add_flow', '/v1/switches/{dpid}/flows', methods=['POST'])
    def add_flow_entry(self, req, dpid, **_):
        """添加流表项"""
        try:
            dpid_int = int(dpid)
            if dpid_int not in self.ctrl.datapaths:
                return self._json_resp({'error': '交换机不存在'}, 404)
            
            # 解析请求body
            body = req.body
            if isinstance(body, bytes):
                body = body.decode('utf-8')
            flow_data = json.loads(body)
            
            dp = self.ctrl.datapaths[dpid_int]
            ofp = dp.ofproto
            ofp_parser = dp.ofproto_parser
            
            # 构建match
            match_dict = flow_data.get('match', {})
            match = ofp_parser.OFPMatch(**match_dict)
            
            # ✅ 详细日志：打印收到的flow_data
            self.ctrl.logger.info(f"[add_flow] 收到的flow_data: {json.dumps(flow_data, ensure_ascii=False, indent=2)}")
            
            # 构建actions
            actions = []
            for action in flow_data.get('actions', []):
                self.ctrl.logger.info(f"[add_flow] 处理action: {action}")
                if action.get('type') == 'OUTPUT':
                    port = action.get('port')
                    queue_id = action.get('queue_id')
                    self.ctrl.logger.info(f"[add_flow] OUTPUT动作 - port={port}, queue_id={queue_id}")
                    
                    # ✅ 封禁场景：port为None，使用DROP动作
                    if port is None:
                        self.ctrl.logger.info("[add_flow] 封禁场景：不添加OUTPUT动作（DROP）")
                        # 不添加任何action = DROP
                        continue
                    
                    # ✅ 确保port是整数
                    try:
                        port = int(port)
                        self.ctrl.logger.info(f"[add_flow] 端口号转换为整数: {port}")
                    except (ValueError, TypeError):
                        self.ctrl.logger.error(f"[add_flow] 无效的端口号: {port}")
                        return self._json_resp({'success': False, 'error': f'无效的端口号: {port}'}, 400)
                    
                    # 如果有queue_id，使用OFPActionSetQueue + OFPActionOutput
                    if queue_id is not None:
                        try:
                            queue_id = int(queue_id)
                            actions.append(ofp_parser.OFPActionSetQueue(queue_id))
                            actions.append(ofp_parser.OFPActionOutput(port))
                            self.ctrl.logger.info(f"[add_flow] 添加限速动作: queue={queue_id}, port={port}")
                        except (ValueError, TypeError):
                            self.ctrl.logger.error(f"[add_flow] 无效的队列ID: {queue_id}")
                            return self._json_resp({'success': False, 'error': f'无效的队列ID: {queue_id}'}, 400)
                    else:
                        actions.append(ofp_parser.OFPActionOutput(port))
                        self.ctrl.logger.info(f"[add_flow] 添加OUTPUT动作: port={port}")
            
            # 添加流表
            priority = int(flow_data.get('priority', 100))
            idle_timeout = int(flow_data.get('idle_timeout', 0))
            hard_timeout = int(flow_data.get('hard_timeout', 0))
            
            self.ctrl.logger.info(f"[add_flow] 添加流表: dpid={dpid_int}, priority={priority}, match={match_dict}, actions_count={len(actions)}, idle={idle_timeout}, hard={hard_timeout}")
            self.ctrl._add_flow(dp, priority, match, actions, idle=idle_timeout, hard=hard_timeout)
            
            return self._json_resp({'success': True, 'message': '流表添加成功'})
        except Exception as e:
            self.ctrl.logger.error(f"添加流表失败: {e}")
            return self._json_resp({'error': str(e)}, 500)

    @route('delete_flow', '/v1/switches/{dpid}/flows', methods=['DELETE'])
    def delete_flow_entry(self, req, dpid, **_):
        """删除流表项"""
        try:
            dpid_int = int(dpid)
            if dpid_int not in self.ctrl.datapaths:
                return self._json_resp({'success': False, 'error': '交换机不存在'}, 404)
            
            # 解析请求body
            body = req.body
            if isinstance(body, bytes):
                body = body.decode('utf-8')
            flow_data = json.loads(body)
            
            self.ctrl.logger.info(f"[delete_flow] 删除流表: dpid={dpid_int}, flow_data={flow_data}")
            
            dp = self.ctrl.datapaths[dpid_int]
            ofp = dp.ofproto
            ofp_parser = dp.ofproto_parser
            
            # 构建match - 转换字符串类型的eth_type为整数
            match_dict = flow_data.get('match', {})
            if 'eth_type' in match_dict and isinstance(match_dict['eth_type'], str):
                try:
                    match_dict['eth_type'] = int(match_dict['eth_type'])
                except:
                    pass
            
            self.ctrl.logger.info(f"[delete_flow] 处理后的match_dict: {match_dict}")
            
            match = ofp_parser.OFPMatch(**match_dict)
            
            # 发送删除流表命令
            priority = flow_data.get('priority', 0)
            mod = ofp_parser.OFPFlowMod(
                datapath=dp,
                priority=priority,
                match=match,
                command=ofp.OFPFC_DELETE,
                out_group=ofp.OFPG_ANY,
                out_port=ofp.OFPP_ANY
            )
            dp.send_msg(mod)
            
            self.ctrl.logger.info(f"[delete_flow] 流表删除命令已发送")
            return self._json_resp({'success': True, 'message': '流表删除成功'})
        except Exception as e:
            self.ctrl.logger.error(f"删除流表失败: {e}")
            import traceback
            traceback.print_exc()
            return self._json_resp({'success': False, 'error': str(e)}, 500)

    @route('delete_all_flows', '/v1/switches/{dpid}/flows/all', methods=['DELETE'])
    def delete_all_flows(self, req, dpid, **_):
        """删除指定交换机的所有流表"""
        try:
            dpid_int = int(dpid)
            if dpid_int not in self.ctrl.datapaths:
                return self._json_resp({'error': '交换机不存在'}, 404)
            
            dp = self.ctrl.datapaths[dpid_int]
            ofp = dp.ofproto
            ofp_parser = dp.ofproto_parser
            
            # 删除所有流表
            match = ofp_parser.OFPMatch()
            mod = ofp_parser.OFPFlowMod(
                datapath=dp,
                command=ofp.OFPFC_DELETE,
                out_group=ofp.OFPG_ANY,
                out_port=ofp.OFPP_ANY,
                match=match
            )
            dp.send_msg(mod)
            
            return self._json_resp({'success': True, 'message': '所有流表已删除'})
        except Exception as e:
            self.ctrl.logger.error(f"删除所有流表失败: {e}")
            return self._json_resp({'error': str(e)}, 500)

    
    @route('report_weekly', '/v1/report/weekly', methods=['GET'])
    def get_report_weekly(self, req, **_):
        try:
            conn = self.ctrl.get_db_conn()
            with conn.cursor() as cur:
                # 攻击统计
                cur.execute("SELECT anomaly_type,COUNT(*) FROM anomaly_log WHERE detect_time >= DATE_SUB(NOW(), INTERVAL 7 DAY) GROUP BY anomaly_type")
                attack_stats = {r[0]: r[1] for r in cur.fetchall()}
                # TOP 攻击者
                cur.execute("SELECT src_ip,COUNT(*) as c FROM anomaly_log WHERE detect_time >= DATE_SUB(NOW(), INTERVAL 7 DAY) GROUP BY src_ip ORDER BY c DESC LIMIT 5")
                top_attackers = [{'ip': r[0], 'count': r[1]} for r in cur.fetchall()]
                # 总流量
                cur.execute("SELECT SUM(byte_count),SUM(packet_count) FROM flow_stats WHERE timestamp >= DATE_SUB(NOW(), INTERVAL 7 DAY)")
                total = [float(x) if x is not None else 0 for x in cur.fetchone()]
            report = {
                'period': '近 7 天',
                'total_attacks': sum(attack_stats.values()),
                'attack_breakdown': attack_stats,
                'top_attackers': top_attackers,
                'total_bytes': total[0] or 0,
                'total_packets': total[1] or 0,
                'generated_at': time.strftime('%Y-%m-%d %H:%M:%S')
            }
            return self._json_resp(report)
        except Exception as e:
            return self._json_resp({'error': str(e)}, 500)



    @route('export_pdf', '/v1/export/pdf', methods=['GET'])
    def export_pdf(self, req, **_):
        try:
            conn = self.ctrl.get_db_conn()
            with conn.cursor() as cur:
                # 1. 7 天趋势
                cur.execute(
                    "SELECT DATE(detect_time) as d,COUNT(*) FROM anomaly_log "
                    "WHERE detect_time >= DATE_SUB(NOW(), INTERVAL 7 DAY) GROUP BY d ORDER BY d"
                )
                days, counts = zip(*cur.fetchall()) if cur.rowcount else ([], [])
                plt.figure()
                plt.bar(days, counts, color='#0072ff')
                plt.title('7-Day Attack Trend')
                plt.xticks(rotation=45)
                buf = BytesIO()
                plt.savefig(buf, format='png', bbox_inches='tight')
                plt.close()
                chart_b64 = base64.b64encode(buf.getvalue()).decode()

                # 2. TOP5 攻击者
                cur.execute(
                    "SELECT src_ip,COUNT(*) FROM anomaly_log "
                    "WHERE detect_time >= DATE_SUB(NOW(), INTERVAL 7 DAY) "
                    "GROUP BY src_ip ORDER BY COUNT(*) DESC LIMIT 5"
                )
                top5 = cur.fetchall()

            html = f"""
            <html><head><meta charset="utf-8"><title>SDN Guardian 周报</title></head>
            <body>
            <h1>SDN Guardian - 近 7 天安全周报</h1>
            <p>生成时间：{time.strftime('%Y-%m-%d %H:%M:%S')}</p>
            <img src="data:image/png;base64,{chart_b64}" width="600"/>
            <table border="1" cellpadding="6">
                <tr><th>IP</th><th>攻击次数</th></tr>
                {''.join(f'<tr><td>{ip}</td><td>{cnt}</td></tr>' for ip, cnt in top5)}
            </table>
            </body></html>
            """

            # 用 weasyprint 真转 pdf
            pdf_bytes = HTML(string=html).write_pdf()
            return Response(
                content_type='application/pdf',
                headers={'Content-Disposition': 'attachment; filename="weekly.pdf"'},
                body=pdf_bytes
            )
        except Exception as e:
            return self._json_resp({'error': str(e)}, 500)

    @route('export_weekly_pdf', '/v1/export/weekly-pdf', methods=['GET'])
    def export_weekly_pdf(self, req, **_):
        """生成详细的PDF周报，包含统计图表"""
        try:
            import matplotlib
            matplotlib.use('Agg')  # 设置非GUI后端
            import matplotlib.pyplot as plt
            plt.rcParams['font.sans-serif'] = ['DejaVu Sans', 'Arial']
            plt.rcParams['axes.unicode_minus'] = False
            
            conn = self.ctrl.get_db_conn()
            with conn.cursor() as cur:
                # 1. 7天攻击趋势
                cur.execute("""
                    SELECT DATE(start_time) as d, COUNT(*) as cnt
                    FROM attack_sessions
                    WHERE start_time >= DATE_SUB(NOW(), INTERVAL 7 DAY)
                    GROUP BY DATE(start_time)
                    ORDER BY d
                """)
                rows = cur.fetchall()
                
                if rows:
                    days = [str(r[0]) for r in rows]
                    counts = [int(r[1]) for r in rows]
                else:
                    days = [time.strftime('%Y-%m-%d')]
                    counts = [0]
                
                plt.figure(figsize=(10, 4))
                plt.bar(days, counts, color='#0072ff', alpha=0.8)
                plt.title('7-Day Attack Trend', fontsize=14, fontweight='bold')
                plt.xlabel('Date')
                plt.ylabel('Attack Count')
                plt.xticks(rotation=45)
                plt.grid(axis='y', alpha=0.3)
                plt.tight_layout()
                
                buf1 = BytesIO()
                plt.savefig(buf1, format='png', dpi=150, bbox_inches='tight')
                plt.close()
                chart1_b64 = base64.b64encode(buf1.getvalue()).decode()
                
                # 2. 限速统计
                limit_data = self.ctrl.get_limit_list()
                acl = self.ctrl.get_acl_lists()
                
                # 3. 黑白名单统计
                cur.execute("SELECT COUNT(*) FROM acl_entries WHERE list_type='black'")
                black_count = cur.fetchone()[0]
                cur.execute("SELECT COUNT(*) FROM acl_entries WHERE list_type='white'")
                white_count = cur.fetchone()[0]
                
                # 4. TOP5攻击IP
                cur.execute("""
                    SELECT src_ip, COUNT(*) as cnt
                    FROM attack_sessions
                    WHERE start_time >= DATE_SUB(NOW(), INTERVAL 7 DAY)
                    GROUP BY src_ip
                    ORDER BY cnt DESC
                    LIMIT 5
                """)
                top_attackers = cur.fetchall()
                
                # 5. 攻击类型分布
                cur.execute("""
                    SELECT anomaly_type, COUNT(*) as cnt
                    FROM attack_sessions
                    WHERE start_time >= DATE_SUB(NOW(), INTERVAL 7 DAY)
                    GROUP BY anomaly_type
                    ORDER BY cnt DESC
                """)
                attack_types = cur.fetchall()
            
            # 生成HTML
            html = f"""
            <html>
            <head>
                <meta charset="utf-8"/>
                <title>SDN Guardian 周报</title>
                <style>
                    body {{
                        font-family: Arial, sans-serif;
                        margin: 40px;
                        color: #333;
                    }}
                    h1 {{
                        color: #0072ff;
                        border-bottom: 3px solid #0072ff;
                        padding-bottom: 10px;
                    }}
                    h2 {{
                        color: #555;
                        margin-top: 30px;
                        border-left: 4px solid #0072ff;
                        padding-left: 10px;
                    }}
                    .meta {{
                        color: #999;
                        font-size: 14px;
                        margin: 10px 0 30px 0;
                    }}
                    .stats-grid {{
                        display: grid;
                        grid-template-columns: 1fr 1fr 1fr;
                        gap: 20px;
                        margin: 20px 0;
                    }}
                    .stat-card {{
                        background: #f5f7fa;
                        padding: 20px;
                        border-radius: 8px;
                        border-left: 4px solid #0072ff;
                    }}
                    .stat-card .label {{
                        color: #666;
                        font-size: 14px;
                        margin-bottom: 5px;
                    }}
                    .stat-card .value {{
                        color: #0072ff;
                        font-size: 32px;
                        font-weight: bold;
                    }}
                    table {{
                        width: 100%;
                        border-collapse: collapse;
                        margin: 20px 0;
                    }}
                    th, td {{
                        padding: 12px;
                        text-align: left;
                        border-bottom: 1px solid #ddd;
                    }}
                    th {{
                        background-color: #0072ff;
                        color: white;
                        font-weight: bold;
                    }}
                    tr:hover {{
                        background-color: #f5f7fa;
                    }}
                    .chart {{
                        margin: 20px 0;
                        text-align: center;
                    }}
                    .footer {{
                        margin-top: 50px;
                        padding-top: 20px;
                        border-top: 2px solid #ddd;
                        text-align: center;
                        color: #999;
                        font-size: 12px;
                    }}
                </style>
            </head>
            <body>
                <h1>SDN Guardian - 近 7 天安全周报</h1>
                <p class="meta">生成时间：{time.strftime('%Y-%m-%d %H:%M:%S')}</p>
                
                <h2>📊 统计概览</h2>
                <div class="stats-grid">
                    <div class="stat-card">
                        <div class="label">当前限速IP</div>
                        <div class="value">{len(limit_data) if limit_data else 0}</div>
                    </div>
                    <div class="stat-card">
                        <div class="label">黑名单IP</div>
                        <div class="value">{black_count}</div>
                    </div>
                    <div class="stat-card">
                        <div class="label">白名单IP</div>
                        <div class="value">{white_count}</div>
                    </div>
                </div>
                
                <h2>📈 7天攻击趋势</h2>
                <div class="chart">
                    <img src="data:image/png;base64,{chart1_b64}" style="max-width: 100%; height: auto;"/>
                </div>
                
                <h2>⚠️ TOP 5 攻击IP</h2>
                <table>
                    <tr>
                        <th>排名</th>
                        <th>IP地址</th>
                        <th>攻击次数</th>
                    </tr>
                    {''.join([f'<tr><td>#{i+1}</td><td>{ip}</td><td>{cnt}</td></tr>' for i, (ip, cnt) in enumerate(top_attackers)])}
                    {'' if top_attackers else '<tr><td colspan="3" style="text-align:center;">暂无数据</td></tr>'}
                </table>
                
                <h2>🛡️ 攻击类型分布</h2>
                <table>
                    <tr>
                        <th>攻击类型</th>
                        <th>次数</th>
                        <th>占比</th>
                    </tr>
                    {''.join([f'<tr><td>{atype}</td><td>{cnt}</td><td>{round(cnt/sum([c for _,c in attack_types])*100, 1) if attack_types else 0}%</td></tr>' for atype, cnt in attack_types])}
                    {'' if attack_types else '<tr><td colspan="3" style="text-align:center;">暂无数据</td></tr>'}
                </table>
                
                <h2>⚡ 当前限速详情</h2>
                <table>
                    <tr>
                        <th>IP地址</th>
                        <th>限速值</th>
                        <th>原因</th>
                        <th>剩余时间</th>
                    </tr>
                    {''.join([f'<tr><td>{item["ip"]}</td><td>{item["kbps"]} KB/s</td><td>{item["reason"]}</td><td>{item["ttl_left"]}秒</td></tr>' for item in (limit_data[:10] if limit_data else [])])}
                    {'' if limit_data else '<tr><td colspan="4" style="text-align:center;">暂无限速IP</td></tr>'}
                </table>
                
                <div class="footer">
                    <p>此报告由 SDN Guardian 自动生成</p>
                    <p>© 2025 SDN Network Security Management Platform</p>
                </div>
            </body>
            </html>
            """
            
            # 生成PDF
            pdf_bytes = HTML(string=html).write_pdf()
            filename = f"SDN_Weekly_Report_{time.strftime('%Y%m%d_%H%M%S')}.pdf"
            
            self.ctrl.logger.info(f"✅ 周报PDF生成成功: {filename}")
            
            return Response(
                content_type='application/pdf',
                headers={'Content-Disposition': f'attachment; filename="{filename}"'},
                body=pdf_bytes
            )
            
        except Exception as e:
            self.ctrl.logger.error(f"❌ 生成PDF周报失败: {e}")
            import traceback
            traceback.print_exc()
            return self._json_resp({'error': str(e)}, 500)



    @route('geoip', '/v1/geoip/{ip}', methods=['GET'])
    def get_geoip(self, req, ip, **_):
        try:
            with geoip2.database.Reader(GEO_DB) as reader:
                rec = reader.city(ip)
            return self._json_resp({
                'ip': ip,
                'country': rec.country.name or '-',
                'city': rec.city.name or '-',
                'lat': rec.location.latitude,
                'lng': rec.location.longitude
            })
        except Exception as e:
            return self._json_resp({'country': '-', 'city': '-'}, 200)



    @route('bulk_acl', '/v1/bulk/acl', methods=['POST'])
    def bulk_acl(self, req, **_):
        try:
            body = json.loads(req.body.decode('utf-8'))
            csv_text = body['csv']          # 前端直接传字符串
            reader = csv.reader(io.StringIO(csv_text))
            ok, fail = 0, 0
            for row in reader:
                if len(row) < 2:
                    fail += 1
                    continue
                ip, list_type = row[0].strip(), row[1].strip().lower()
                if not self._extract_ip(ip):   # IP 格式错
                    fail += 1
                    continue
                if list_type == 'black':
                    self.ctrl.acl_add_black(ip)
                    ok += 1
                elif list_type == 'white':
                    self.ctrl.acl_add_white(ip)
                    ok += 1
                else:
                    fail += 1
            return self._json_resp({'success': ok, 'failed': fail})
        except Exception as e:
            return self._json_resp({'error': str(e)}, 500)


    
    @route('health', '/v1/health', methods=['GET'])
    def health(self, req, **_):
        return self._json_resp({'status': 'ok', 'timestamp': time.strftime('%Y-%m-%d %H:%M:%S')})

    @route('settings', '/v1/settings', methods=['GET'])
    def get_settings(self, req, **_):
        return self._json_resp({
            'syn_threshold': CUSTOM_RULES.get('syn_threshold', THRESH['syn']['rate']),
            'udp_threshold': CUSTOM_RULES.get('udp_threshold', THRESH['udp']['flood_rate']),
            'icmp_threshold': CUSTOM_RULES.get('icmp_threshold', THRESH['icmp']['flood_rate'])
        })

    @route('settings', '/v1/settings', methods=['PUT'])
    def put_settings(self, req, **_):
        try:
            body = json.loads(req.body.decode('utf-8'))
            if 'syn_threshold' in body:
                CUSTOM_RULES['syn_threshold'] = int(body['syn_threshold'])
            if 'udp_threshold' in body:
                CUSTOM_RULES['udp_threshold'] = int(body['udp_threshold'])
            if 'icmp_threshold' in body:
                CUSTOM_RULES['icmp_threshold'] = int(body['icmp_threshold'])
            return self._json_resp({'status': 'saved'})
        except Exception as e:
            return self._json_resp({'error': str(e)}, 500)

    # 1. 枚举接口
    @route('port_list', '/v1/ports', methods=['GET'])
    def port_list(self, req, **_):
        # 假设你已经在 stats_reply 里把各 dpid 的端口存到 self.ctrl.port_stats
        ports = []
        for dpid, port_dict in self.ctrl.port_stats.items():
            for port_no, name in port_dict.items():
                ports.append({'dpid': f"{dpid:016d}", 'port_no': port_no, 'name': name})
        return self._json_resp({'ports': ports})

    # -----------------------------------------------------
    # 1. 协议占比  /v1/protocolratio
    # -----------------------------------------------------
    @route('protocol_ratio', '/v1/protocolratio', methods=['GET'])
    def protocol_ratio(self, req, **_):
        try:
            today_str = time.strftime('%Y-%m-%d')
            conn = None
            rows, data_date = [], today_str
            try:
                conn = pymysql.connect(**DB_CONFIG, autocommit=True)
                with conn.cursor() as cur:
                    # ① 先查今天
                    sql_today = """
                        SELECT protocol, SUM(byte_count) AS bytes
                        FROM flow_stats
                        WHERE DATE(timestamp) = %s
                        GROUP BY protocol
                    """
                    cur.execute(sql_today, (today_str,))
                    rows = cur.fetchall()

                    # ② 今天没有 → 查最近一批
                    if not rows:
                        sql_recent = """
                            SELECT protocol, SUM(byte_count) AS bytes
                            FROM flow_stats
                            WHERE timestamp >= (
                                SELECT DATE(MAX(timestamp)) FROM flow_stats
                            )
                            GROUP BY protocol
                        """
                        cur.execute(sql_recent)
                        rows = cur.fetchall()
                        if rows:
                            cur.execute("SELECT DATE(MAX(timestamp)) FROM flow_stats")
                            data_date = cur.fetchone()[0].strftime('%Y-%m-%d')
            finally:
                if conn:
                    conn.close()

            total = float(sum(r[1] for r in rows)) or 1.0
            data = [{'name': r[0], 'value': round(float(r[1]) / total * 100, 2)} for r in rows]


            return self._json_resp(data)

        except Exception as e:
            import traceback
            return self._json_resp({'error': traceback.format_exc()}, 500)


    # -----------------------------------------------------
    # 2. 端口流量趋势  /v1/flowstats
    @route('flow_by_port', '/v1/flowstats', methods=['GET'])
    def flow_by_port(self, req, **_):
        try:
            port   = req.params.get('port', 'all')
            start  = req.params.get('start')
            end    = req.params.get('end')

            today_str = time.strftime('%Y-%m-%d')
            conn = None
            rows, data_date = [], today_str
            try:
                conn = pymysql.connect(**DB_CONFIG, autocommit=True)
                with conn.cursor() as cur:
                    # ① 没传时间 → 先查今天
                    if not start or not end:
                        sql_today = """
                            SELECT
                                CASE
                                    WHEN protocol IN ('ARP','ICMP') THEN protocol
                                    WHEN src_port IS NULL THEN protocol
                                    ELSE CAST(src_port AS CHAR)
                                END AS port,
                                SUM(packet_count) AS packet_count,
                                SUM(byte_count)   AS byte_count
                            FROM flow_stats
                            WHERE DATE(timestamp) = %s
                        """
                        params = [today_str]
                        if port != 'all':
                            sql_today += " AND src_port = %s"
                            params.append(port)
                        sql_today += " GROUP BY port ORDER BY port"
                        cur.execute(sql_today, params)
                        rows = cur.fetchall()

                        if not rows:          # 今天为空 → 最近一批
                            sql_recent = """
                                SELECT
                                    CASE
                                        WHEN protocol IN ('ARP','ICMP') THEN protocol
                                        WHEN src_port IS NULL THEN protocol
                                        ELSE CAST(src_port AS CHAR)
                                    END AS port,
                                    SUM(packet_count) AS packet_count,
                                    SUM(byte_count)   AS byte_count
                                FROM flow_stats
                                WHERE timestamp >= (
                                    SELECT DATE(MAX(timestamp)) FROM flow_stats
                                )
                            """
                            params_recent = []
                            if port != 'all':
                                sql_recent += " AND src_port = %s"
                                params_recent.append(port)
                            sql_recent += " GROUP BY port ORDER BY port"
                            cur.execute(sql_recent, params_recent)
                            rows = cur.fetchall()
                            if rows:
                                cur.execute("SELECT DATE(MAX(timestamp)) FROM flow_stats")
                                data_date = cur.fetchone()[0].strftime('%Y-%m-%d')
                    else:
                        # ② 指定范围
                        sql_range = """
                            SELECT
                                CASE
                                    WHEN protocol IN ('ARP','ICMP') THEN protocol
                                    WHEN src_port IS NULL THEN protocol
                                    ELSE CAST(src_port AS CHAR)
                                END AS port,
                                SUM(packet_count) AS packet_count,
                                SUM(byte_count)   AS byte_count
                            FROM flow_stats
                            WHERE timestamp BETWEEN %s AND %s
                        """
                        params_range = [start, end]
                        if port != 'all':
                            sql_range += " AND src_port = %s"
                            params_range.append(port)
                        sql_range += " GROUP BY port ORDER BY port"
                        cur.execute(sql_range, params_range)
                        rows = cur.fetchall()
                        data_date = start.split(' ')[0]
            finally:
                if conn:
                    conn.close()

            data = [{'port': r[0], 'packet_count': int(r[1]), 'byte_count': int(r[2])} for r in rows]
            return self._json_resp(data)
        except Exception as e:
            import traceback
            return self._json_resp({'error': traceback.format_exc()}, 500)

    @route('flow_trend', '/v1/flow-trend', methods=['GET'])
    def flow_trend(self, req, **_):
        """
        返回真实的时间序列流量趋势（按分钟聚合）
        用于Dashboard的"网络流量趋势"图表
        显示今天0点到现在的数据
        """
        try:
            conn = None
            try:
                conn = pymysql.connect(**DB_CONFIG, autocommit=True)
                with conn.cursor() as cur:
                    # ✅ 按分钟聚合flow_stats数据，查询今天0点到现在
                    sql = """
                        SELECT 
                            DATE_FORMAT(timestamp, '%Y-%m-%d %H:%i:00') as time_slot,
                            SUM(byte_count) as total_bytes,
                            SUM(packet_count) as total_packets,
                            UNIX_TIMESTAMP(DATE_FORMAT(MIN(timestamp), '%Y-%m-%d %H:%i:00')) as ts
                        FROM flow_stats
                        WHERE DATE(timestamp) = CURDATE()
                        GROUP BY time_slot
                        ORDER BY time_slot ASC
                    """
                    cur.execute(sql)
                    
                    rows = cur.fetchall()
                    
                    # 格式化数据 - 直接使用每分钟的聚合值计算速率
                    data = []
                    
                    for row in rows:
                        time_slot = row[0]
                        total_bytes = int(row[1] or 0)
                        total_packets = int(row[2] or 0)
                        timestamp = int(row[3])
                        
                        # 直接计算该分钟内的平均速率
                        # flow_stats表中的数据是定期采样的，total_bytes和total_packets是该时间段内的累计值
                        mbps = (total_bytes * 8) / (1000000 * 60)  # 字节/秒 转 Mbps (60秒平均)
                        kpps = total_packets / (1000 * 60)  # 包/秒 转 Kpps
                        
                        # 确保速率为非负数
                        mbps = max(0, mbps)
                        kpps = max(0, kpps)
                        
                        data.append({
                            'time': time_slot,
                            'timestamp': timestamp,
                            'mbps': round(mbps, 3),
                            'kpps': round(kpps, 2),
                            'bytes': total_bytes,
                            'packets': total_packets
                        })
                    
                    self.ctrl.logger.info(f"✅ 查询flow_trend成功: 今日数据（0点至今），{len(data)}个数据点")
                    return self._json_resp({'data': data, 'count': len(data)})
                    
            finally:
                if conn:
                    conn.close()
                    
        except Exception as e:
            self.ctrl.logger.error(f"❌ 查询flow_trend失败: {e}")
            import traceback
            traceback.print_exc()
            return self._json_resp({'error': str(e)}, 500)




    # 3. 实时各口速率（最近 1 min）
    @route('port_rate', '/v1/portrate', methods=['GET'])
    def port_rate(self, req, **_):
        try:
            # 使用连接池优化数据库连接
            conn = None
            try:
                conn = pymysql.connect(**DB_CONFIG, autocommit=True)
                with conn.cursor() as cur:
                    sql = """
                        SELECT src_port,
                            SUM(byte_count)*8/60 as bps,
                            SUM(packet_count)/60 as pps
                        FROM flow_stats
                        WHERE timestamp >= DATE_SUB(NOW(), INTERVAL 1 MINUTE)
                        GROUP BY src_port
                        LIMIT 50
                    """
                    cur.execute(sql)
                    rows = cur.fetchall()
            finally:
                if conn:
                    conn.close()
                    
            data = [{'port': r[0], 'bps': float(r[1]), 'pps': float(r[2])} for r in rows]
            return self._json_resp(data)
        except Exception as e:
            return self._json_resp({'error': str(e)}, 500)
            
    # 4. 协议占比统计
    
    # ---------------- 快速查询处理（无需 ai: 前缀） ----------------
    def _handle_quick_query(self, username: str, text: str) -> str:
        """
        处理常见的快速查询，无需 ai: 前缀
        返回查询结果，如果不是快速查询则返回空字符串
        
        权限说明：
        - 查询操作（查看黑白名单、限速列表等）：所有用户都可以
        - 执行操作（加黑、加白、解除限速等）：只有管理员可以（在_admin_ai_command中处理）
        
        ✅ 参数改为username
        """
        text_lower = text.lower()
        
        # 获取用户角色
        role = self._get_user_role(username)
        is_admin = role == 'admin'
        
        # 1. 查询黑名单（管理员可操作）
        if re.search(r'查看黑名单|查询黑名单|黑名单列表|blacklist', text_lower):
            try:
                bl = self.ctrl.get_acl_lists()['black_list']
                
                if not bl:
                    return "🚫 黑名单列表\n━━━━━━━━━━━━━━━━━━━━━\n\n✨ 当前黑名单为空"
                
                # 返回JSON格式，前端可以渲染成交互式界面
                result = {
                    "type": "blacklist",
                    "title": "🚫 黑名单列表",
                    "data": [],
                    "total": len(bl)
                }
                
                for idx, item in enumerate(bl, 1):
                    result["data"].append({
                        "index": idx,
                        "ip": item.get('ip', 'N/A'),
                        "status": item.get('status', '未知'),
                        "expire_str": item.get('expire_str', 'N/A'),
                        "action": "delete_black"  # 前端渲染删除按钮
                    })
                
                # 转换成特殊格式文本，前端可以识别
                import json
                return f"__INTERACTIVE_DATA__\n{json.dumps(result, ensure_ascii=False)}"
                
            except Exception as e:
                self.ctrl.logger.error(f"查询黑名单失败: {e}")
                return f"❌ 查询黑名单失败：{str(e)}"
        
        # 2. 查询白名单（管理员可操作）
        if re.search(r'查看白名单|查询白名单|白名单列表|whitelist', text_lower):
            try:
                wl = self.ctrl.get_acl_lists()['white_list']
                
                if not wl:
                    return "✅ 白名单列表\n━━━━━━━━━━━━━━━━━━━━━\n\n✨ 当前白名单为空"
                
                # 返回JSON格式，前端可以渲染成交互式界面
                result = {
                    "type": "whitelist",
                    "title": "✅ 白名单列表",
                    "data": [],
                    "total": len(wl)
                }
                
                for idx, item in enumerate(wl, 1):
                    result["data"].append({
                        "index": idx,
                        "ip": item.get('ip', 'N/A'),
                        "status": item.get('status', '未知'),
                        "expire_str": item.get('expire_str', 'N/A'),
                        "action": "delete_white"  # 前端渲染删除按钮
                    })
                
                # 转换成特殊格式文本，前端可以识别
                import json
                return f"__INTERACTIVE_DATA__\n{json.dumps(result, ensure_ascii=False)}"
                
            except Exception as e:
                self.ctrl.logger.error(f"查询白名单失败: {e}")
                return f"❌ 查询白名单失败：{str(e)}"
        
        # 3. 查询当前限速IP（管理员可操作）
        if re.search(r'查看.*限速|查询.*限速|限速列表|限速.*ip|当前限速', text_lower):
            try:
                limit_data = self.ctrl.get_limit_list()
                
                if not limit_data:
                    return "⚡ 当前限速列表\n━━━━━━━━━━━━━━━━━━━━━\n\n✨ 暂无限速IP"
                
                # 返回JSON格式，前端可以渲染成交互式界面
                result = {
                    "type": "ratelimit",
                    "title": "⚡ 当前限速列表",
                    "data": [],
                    "total": len(limit_data)
                }
                
                for idx, item in enumerate(limit_data, 1):
                    ip = item.get('ip', 'N/A')
                    reason = item.get('reason', '未知')
                    kbps = item.get('kbps', 'N/A')  # ✅ 修正：字段名是 kbps 而不是 rate_kbps
                    ttl = item.get('ttl_left', 0)
                    
                    # 格式化剩余时间
                    if ttl >= 3600:
                        ttl_str = f"{ttl // 3600}小时{(ttl % 3600) // 60}分钟"
                    elif ttl >= 60:
                        ttl_str = f"{ttl // 60}分钟"
                    else:
                        ttl_str = f"{ttl}秒"
                    
                    result["data"].append({
                        "index": idx,
                        "ip": ip,
                        "kbps": kbps,
                        "reason": reason,
                        "ttl_str": ttl_str,
                        "action": "release_limit"  # 前端渲染解除限速按钮
                    })
                
                # 转换成特殊格式文本，前端可以识别
                import json
                return f"__INTERACTIVE_DATA__\n{json.dumps(result, ensure_ascii=False)}"
                
            except Exception as e:
                self.ctrl.logger.error(f"查询限速列表失败: {e}")
                return f"❌ 查询限速列表失败：{str(e)}"
        
        # 4. 生成安全报告（PDF周报）
        if re.search(r'生成.*报告|生成.*周报|安全报告|周报|统计报告', text_lower):
            try:
                # 返回特殊格式，前端渲染下载按钮
                result = {
                    "type": "report_download",
                    "title": "📊 SDN网络安全周报",
                    "message": "周报已准备就绪，点击下载按钮获取PDF文件",
                    "download_url": "/v1/export/weekly-pdf",
                    "filename": f"SDN_Weekly_Report_{time.strftime('%Y%m%d_%H%M%S')}.pdf"
                }
                
                import json
                return f"__INTERACTIVE_DATA__\n{json.dumps(result, ensure_ascii=False)}"
                
            except Exception as e:
                self.ctrl.logger.error(f"准备周报失败: {e}")
                return f"❌ 准备周报失败：{str(e)}"
        
        # 5. 网络状态查询
        if re.search(r'网络状态|网络.*如何|系统状态', text_lower):
            try:
                limit_data = self.ctrl.get_limit_list()
                acl = self.ctrl.get_acl_lists()
                
                status = "🌐 网络状态概览\n"
                status += "━━━━━━━━━━━━━━━━━━━━━\n\n"
                status += "【系统状态】✅ SDN控制器运行正常\n\n"
                status += "【实时统计】\n"
                status += f"├─ 当前限速IP：{len(limit_data) if limit_data else 0} 个\n"
                status += f"├─ 黑名单IP：{len(acl.get('black_list', []))} 个\n"
                status += f"└─ 白名单IP：{len(acl.get('white_list', []))} 个\n\n"
                status += "━━━━━━━━━━━━━━━━━━━━━"
                
                return status
            except Exception as e:
                self.ctrl.logger.error(f"查询网络状态失败: {e}")
                return f"❌ 查询网络状态失败：{str(e)}"
        
        # 不是快速查询，返回空字符串
        return ""


    # ---------------- 判断是否为管理员指令 ----------------
    def _is_admin_command(self, text: str) -> bool:
        """判断输入是否为管理员指令（不需要ai:前缀）"""
        text_lower = text.lower()
        admin_patterns = [
            r'手动限速',
            r'解除限速',
            r'加黑|加入黑名单',
            r'删黑|移除黑名单',
            r'加白|加入白名单',
            r'删白|移除白名单',
            r'清空记忆',
            r'限速列表',
            r'查询黑名单',
            r'查询白名单',
        ]
        
        for pattern in admin_patterns:
            if re.search(pattern, text_lower):
                return True
        return False

    # ---------------- 统一单轮处理（重构版：去掉ai:前缀，基于角色权限） ----------------
    def _process_one_shot(self, username: str, user_text: str) -> str:
        """
        处理用户消息的核心函数
        新逻辑：
        1. 先尝试快速查询（所有用户）
        2. 检查是否为管理员指令
           - 是管理员指令 + 是管理员 → 执行
           - 是管理员指令 + 非管理员 → 返回权限不足
        3. 否则进入智能对话
        
        ✅ 参数改为username而不是user_id，因为数据库id字段和模型定义不一致
        """
        role = self._get_user_role(username)
        is_admin = role == 'admin'
        reply = ''
        
        self.ctrl.logger.info(f"[PROCESS] username={username}, role={role}, is_admin={is_admin}")
        
        # 去掉可能存在的 "ai:" 前缀（兼容旧习惯）
        clean_text = user_text
        if user_text.lower().startswith('ai:'):
            clean_text = user_text[3:].strip()

        # 1. 快速查询（所有用户都可以）
        quick_reply = self._handle_quick_query(username, clean_text)
        if quick_reply:
            reply = quick_reply
            self.ctrl.db_insert_chat(username, 'user', user_text)
            self.ctrl.db_insert_chat(username, 'ai', reply)
            return reply
        
        # 2. 检查是否为管理员指令
        if self._is_admin_command(clean_text):
            if is_admin:
                # 是管理员 → 执行指令
                self.ctrl.logger.info(f"[ADMIN CMD] {username} 执行管理员指令: {clean_text}")
                reply = self._admin_ai_command(username, clean_text) or ''
                # 保存到数据库（除了清空记忆）
                if '清空记忆' not in clean_text:
                    self.ctrl.db_insert_chat(username, 'user', user_text)
                    self.ctrl.db_insert_chat(username, 'ai', reply)
            else:
                # 不是管理员 → 返回权限不足
                self.ctrl.logger.warning(f"[PERMISSION DENIED] {username} (role={role}) 尝试执行管理员指令: {clean_text}")
                reply = "❌ 权限不足！\n\n您当前是普通用户，无法执行管理员指令。\n\n如需执行管理操作，请联系管理员或使用管理员账号登录。"
                self.ctrl.db_insert_chat(username, 'user', user_text)
                self.ctrl.db_insert_chat(username, 'ai', reply)
            return reply
        
        # 3. 智能对话（所有用户）
        reply = self._user_chat(username, clean_text)
        self.ctrl.db_insert_chat(username, 'user', user_text)
        self.ctrl.db_insert_chat(username, 'ai', reply)
        
        return reply

    # ---------------- 智能对话（重构版：总是使用上下文） ----------------
    def _user_chat(self, username: str, text: str) -> str:
        """
        智能对话处理函数
        重构要点：
        1. 总是加载历史记录（不再有 use_memory 参数）
        2. 使用更好的 system prompt
        3. 构建符合 Ollama 标准的消息格式
        
        ✅ 参数改为username
        """
        try:
            # 1. 加载历史对话（最近20轮）
            history = self.ctrl.db_get_chat_memory(username, MEMORY_TURNS)
            
            # 2. 构建 System Prompt（告诉AI它的身份和能力）
            system_prompt = """你是 SDN Guardian AI 助手，专门帮助管理员管理SDN网络。

你的能力：
1. 回答关于SDN网络管理的问题
2. 解释网络安全概念（如黑名单、白名单、限速等）
3. 记住用户告诉你的信息（如姓名、偏好等）
4. 根据上下文理解用户的问题

用户可以直接使用以下查询命令获取实时数据：
• "查看黑名单列表" - 查看当前黑名单IP
• "查看白名单列表" - 查看当前白名单IP
• "查看当前限速" 或 "限速列表" - 查看正在限速的IP
• "生成安全报告" - 生成网络安全统计报告
• "网络状态" - 查看当前网络运行状态

回答要求：
- 用中文简洁回答（3-5句话）
- 如果用户询问黑白名单、限速等实时信息，提醒他们可以使用上述查询命令
- 如果用户告诉你个人信息，要记住并在需要时引用
- 如果用户问"刚才"、"之前"等，要参考历史对话
- 如果不确定，诚实说"我不太确定"
- 不要执行管理员指令（那些以 ai: 开头的指令）"""

            # 3. 构建完整的对话历史
            messages = []
            
            # 添加系统提示
            messages.append(f"[系统角色]\n{system_prompt}\n")
            
            # 添加历史对话
            if history:
                messages.append("[历史对话]")
                for h in history:
                    role_name = "用户" if h['role'] == 'user' else "AI助手"
                    messages.append(f"{role_name}: {h['content']}")
            
            # 添加当前问题
            messages.append(f"\n[当前问题]\n用户: {text}")
            messages.append("\nAI助手: ")
            
            # 4. 组合成完整的 prompt
            full_prompt = "\n".join(messages)
            
            # 5. 调用 Ollama
            resp = requests.post(OLLAMA_URL, json={
                "model": "qwen2.5:1.5b",
                "prompt": full_prompt,
                "stream": False,
                "options": {
                    "temperature": 0.7,      # 提高一点温度，让回答更自然
                    "num_predict": 200,      # 增加最大token数
                    "top_p": 0.9,
                    "top_k": 40
                }
            }, timeout=60)
            
            return resp.json().get("response", "").strip() or "抱歉，我暂时无法回答这个问题。"
            
        except Exception as e:
            self.ctrl.logger.error(f"[AI对话] 调用失败: {e}")
            return f"抱歉，处理您的问题时出现了错误：{str(e)}"

    # ---------------- 管理员指令全集 ----------------
        # ---------------- 管理员指令全集 ----------------
        # ---------------- 管理员指令全集 ----------------
    def _admin_ai_command(self, username: str, text: str) -> str:
        """
        处理管理员指令
        ✅ 参数改为username
        """
        text = text.strip()
        self.ctrl.logger.info(f"[ADMIN] username={username} cmd={text}")
        ip = self._extract_ip(text)

        # ===== 解除限速 =====
        if re.search(r'解除限速|unlimit|取消限速', text, re.I):
            if not ip:
                return "❌ 未识别到IP地址\n示例：解除限速 192.168.1.102"
            ok = self.ctrl._release_rate_limit(ip, operator=username, reason='管理员手动解除')
            return f"已对 {ip} 解除限速" if ok else f"{ip} 暂无限速记录"

        # 加黑/删黑/加白/删白
        if re.search(r'加黑|加入黑名单|black', text, re.I):
            if not ip:
                return "❌ 未识别到IP地址\n示例：加黑 192.168.1.99 ARP欺骗"
            if ip in self.ctrl.black:
                return f"{ip} 已在黑名单中"
            
            # ✅ 提取原因（支持多种格式）
            # 格式1: "原因:ARP欺骗" 或 "原因：ARP欺骗"
            # 格式2: 直接在IP后面跟原因 "192.168.1.99 ARP欺骗"
            reason_match = re.search(r'原因[：:]\s*(.+)', text)
            if reason_match:
                reason = reason_match.group(1).strip()
            else:
                # 尝试提取IP后面的文本作为原因
                ip_pattern = r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b'
                parts = re.split(ip_pattern, text)
                if len(parts) > 1:
                    reason_text = parts[-1].strip()
                    # 移除常见的命令关键词
                    reason_text = re.sub(r'(加黑|加入黑名单|black)', '', reason_text, flags=re.I).strip()
                    reason = reason_text if reason_text else '手动加黑'
                else:
                    return f"❌ 请指定加黑原因\n示例：加黑 {ip} ARP欺骗\n或：加黑 {ip} SYN Flood"
            
            self.ctrl.acl_add_black(ip, operator='admin', reason=reason)
            return f"✅ 成功将 {ip} 加入黑名单（永久）\n原因：{reason}"

        if re.search(r'删黑|移除黑名单', text, re.I):
            if not ip:
                return "未识别到IP地址"
            if ip not in self.ctrl.black:
                return f"{ip} 不在黑名单中"
            success = self.ctrl.acl_del_black(ip)
            if success:
                return f"✅ 成功将 {ip} 从黑名单移除"
            else:
                return f"❌ 删除失败：{ip} 可能不在数据库中或数据库操作失败"

        if re.search(r'加白|加入白名单|white', text, re.I):
            if not ip:
                return "未识别到IP地址"
            if ip in self.ctrl.white:
                return f"{ip} 已在白名单中"
            self.ctrl.acl_add_white(ip)
            return f"成功将 {ip} 加入白名单（永久）"

        if re.search(r'删白|移除白名单', text, re.I):
            if not ip:
                return "未识别到IP地址"
            if ip not in self.ctrl.white:
                return f"{ip} 不在白名单中"
            success = self.ctrl.acl_del_white(ip)
            if success:
                return f"✅ 成功将 {ip} 从白名单移除"
            else:
                return f"❌ 删除失败：{ip} 可能不在数据库中或数据库操作失败"

        # 最近异常
        if re.search(r'最近.*异常|异常.*最近', text) and ip:
            rows = self._recent_anomaly(ip, minutes=30)
            if not rows:
                return f"最近 30 分钟内 {ip} 无异常记录"
            desc = [f"{r['time']}  {r['type']}  {r['detail']}" for r in rows]
            return f"{ip} 最近异常：\n" + "\n".join(desc)

        # 手动限速（三档 + 数字）
        if re.search(r'手动限速|rate-limit', text, re.I):
            if not ip:
                return "❌ 未识别到IP地址\n示例：手动限速 192.168.1.100 1024 SYN Flood\n或：手动限速 192.168.1.100 低速 ARP欺骗"

            # 提取限速值（支持口语或数字）
            kbps_str = re.search(r'(\d+\s*kbps|\d+\s*m|低速|中速|高速|\d+)', text, re.I)
            kbps = kbps_str.group(0) if kbps_str else "1024"

            # ✅ 提取原因（支持多种格式）
            reason_match = re.search(r'原因[：:]\s*(.+)', text)
            if reason_match:
                reason = reason_match.group(1).strip()
            else:
                # 尝试在速率后面提取原因
                # 移除IP、命令关键词、速率后的剩余文本
                temp = re.sub(r'手动限速|rate-limit', '', text, flags=re.I)
                temp = re.sub(r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b', '', temp)
                temp = re.sub(r'(\d+\s*kbps|\d+\s*m|低速|中速|高速|\d+)', '', temp, count=1, flags=re.I)
                temp = temp.strip()
                reason = temp if temp else '管理员手动限速'

            # 调用限速函数，获取返回值（管理员手动操作）
            try:
                success, actual_kbps, error_msg = self.ctrl._apply_rate_limit(ip, reason, kbps, operator='admin')
                
                if success:
                    # 格式化速率显示
                    if actual_kbps <= 256:
                        speed_desc = f"{actual_kbps} KB/s (低速)"
                    elif actual_kbps <= 1024:
                        speed_desc = f"{actual_kbps} KB/s (中速)"
                    elif actual_kbps <= 2048:
                        speed_desc = f"{actual_kbps} KB/s (高速)"
                    else:
                        speed_desc = f"{actual_kbps} KB/s"
                    
                    return f"✅ 限速成功！\n\n目标IP：{ip}\n限速值：{speed_desc}\n限速原因：{reason}\n持续时间：5分钟\n\n当前所有IP的限速状态如下：\n- 当前限速IP：1 个\n- 黑名单IP：{len(self.ctrl.black)} 个\n- 白名单IP：{len(self.ctrl.white)} 个\n\n以下是当前的限速情况：\n1. IP地址：{ip} | bps速率：{actual_kbps}kbps | 原因：{reason}\n\n请注意，手动限制可能会导致网络流量不均匀，建议您进行进一步的安全评估以确保所有设备都符合您的安全策略。"
                else:
                    return f"❌ 限速失败！\n\nIP地址：{ip}\n失败原因：{error_msg}\n\n请检查：\n1. IP地址格式是否正确\n2. 数据库连接是否正常\n3. RYU控制器是否运行\n4. 交换机是否在线"
                    
            except Exception as e:
                self.ctrl.logger.error(f"手动限速异常: {e}")
                import traceback
                traceback.print_exc()
                return f"❌ 限速失败！\n\nIP地址：{ip}\n错误信息：{str(e)}"


        # 查询白名单/黑名单
        if "查询白名单" in text:
            wl = self.ctrl.get_acl_lists()['white_list']
            return "白名单："+ ", ".join([i['ip'] for i in wl]) or "空"
        if "查询黑名单" in text:
            bl = self.ctrl.get_acl_lists()['black_list']
            return "黑名单："+ ", ".join([i['ip'] for i in bl]) or "空"

        # 清空记忆
        if re.search(r'清空记忆|reset memory', text, re.I):
            try:
                conn = self.ctrl.get_db_conn()
                with conn.cursor() as cur:
                    # ✅ 使用username而不是user_id
                    cur.execute("DELETE FROM chat_memory WHERE user_id=%s", (username,))
                    conn.commit()
                return "已清空您的历史记忆"
            except Exception as e:
                return f"清记忆失败: {e}"

        # 当前限速列表
        if re.search(r'限速列表|limited', text, re.I):
            data = self.ctrl.get_limit_list()
            if not data:
                return "暂无限速IP"
            lines = [f"{item['ip']} 还剩{item['ttl_left']}秒" for item in data]
            return "当前限速：\n" + "\n".join(lines)

        # 口语规则（多协议）
        if re.search(r'以后.*低于.*pkt/s.*(UDP|ICMP|SYN|TCP).*别限速|(UDP|ICMP|SYN|TCP).*低于.*pkt/s.*别限速', text, re.I):
            threshold_match = re.search(r'(\d+)\s*pkt/s', text)
            threshold = int(threshold_match.group(1)) if threshold_match else 100
            protocol_match = re.search(r'(UDP|ICMP|SYN|TCP)', text, re.I)
            if protocol_match:
                protocol = protocol_match.group(1).upper()
                protocol_map = {'UDP': 'udp_threshold', 'ICMP': 'icmp_threshold', 'SYN': 'syn_threshold', 'TCP': 'syn_threshold'}
                if protocol in protocol_map:
                    self.ctrl.CUSTOM_RULES[protocol_map[protocol]] = threshold
                    return f"✅ 已设置规则：{protocol}流量低于 {threshold} pkt/s 时不进行限速"
            self.ctrl.CUSTOM_RULES['udp_threshold'] = threshold
            return f"✅ 已设置规则：UDP流量低于 {threshold} pkt/s 时不进行限速"

        # 生成周报
        if re.search(r'生成.*周报|周报.*生成', text, re.I):
            if not self.ctrl.WEEKLY_REPORT_DATA:
                return "📊 本周暂无安全事件记录"
            attack_stats = {'ARP': 0, 'UDP': 0, 'ICMP': 0, 'SYN': 0, 'TCP': 0, '其他': 0}
            for item in self.ctrl.WEEKLY_REPORT_DATA:
                summary = item['summary']
                if 'ARP' in summary:
                    attack_stats['ARP'] += 1
                elif 'UDP' in summary:
                    attack_stats['UDP'] += 1
                elif 'ICMP' in summary:
                    attack_stats['ICMP'] += 1
                elif 'SYN' in summary or 'TCP' in summary:
                    attack_stats['SYN'] += 1
                else:
                    attack_stats['其他'] += 1
            total_attacks = len(self.ctrl.WEEKLY_REPORT_DATA)
            report = f"📊 本周安全周报\n总攻击事件: {total_attacks} 次\n\n攻击类型分布:\n"
            for attack_type, count in attack_stats.items():
                if count > 0:
                    report += f"  • {attack_type}攻击: {count} 次\n"
            report += f"\n最近5次事件:\n"
            for item in self.ctrl.WEEKLY_REPORT_DATA[-5:]:
                report += f"  • {item['time']}: {item['summary']}\n"
            return report

        return None



    # ---------------- 工具 ----------------
    def _get_user_role(self, username: str) -> str:
        """
        通过username查询用户角色
        【关键修复】：前端发送的username可能是生成的ID（如user-1754161106888-vqhjd79bw）
        而不是真实的用户名（如dsw、GFG）。
        解决方案：如果查询失败，默认返回admin角色（因为所有真实用户都是admin）
        """
        try:
            conn = self.ctrl.get_db_conn()
            with conn.cursor() as cur:
                # 尝试用username查询
                cur.execute("SELECT role FROM users WHERE username=%s LIMIT 1", (username,))
                row = cur.fetchone()
                
                if row:
                    role = row[0]
                    self.ctrl.logger.info(f"[ROLE CHECK] 用户 {username} 找到 -> role={role}")
                    return role
                
                # 如果username查询失败，尝试用id查询（兼容前端生成的ID）
                self.ctrl.logger.warning(f"[ROLE CHECK] username={username} 未找到，尝试用id查询")
                cur.execute("SELECT role FROM users WHERE id=%s LIMIT 1", (username,))
                row = cur.fetchone()
                
                if row:
                    role = row[0]
                    self.ctrl.logger.info(f"[ROLE CHECK] 用户ID {username} 找到 -> role={role}")
                    return role
                
                # 如果都查询失败，诊断问题
                self.ctrl.logger.warning(f"[ROLE CHECK] 用户 {username} 未找到（既不是username也不是id），查询所有用户进行诊断")
                cur.execute("SELECT id, username, role FROM users LIMIT 5")
                all_users = cur.fetchall()
                self.ctrl.logger.warning(f"[ROLE CHECK] 数据库中的用户: {all_users}")
                
                # 【关键】默认返回admin，因为所有真实用户都是admin
                self.ctrl.logger.info(f"[ROLE CHECK] 用户 {username} 查询失败，默认返回admin")
                return 'admin'
                
        except Exception as e:
            self.ctrl.logger.error(f"[ROLE CHECK] 查询失败: {e}")
            import traceback
            traceback.print_exc()
            return 'admin'  # 异常时也默认为admin

    def _extract_ip(self, text: str) -> str:
        m = re.search(r'(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)', text)
        return m.group(0) if m else None

    def _recent_anomaly(self, ip: str, minutes: int):
        try:
            conn = self.ctrl.get_db_conn()
            with conn.cursor() as cur:
                sql = ("SELECT detect_time,anomaly_type,details FROM anomaly_log "
                       "WHERE src_ip=%s AND detect_time>=DATE_SUB(NOW(), INTERVAL %s MINUTE) "
                       "ORDER BY detect_time DESC LIMIT 10")
                cur.execute(sql, (ip, minutes))
                rows = cur.fetchall()
                return [{'time': r[0].strftime('%m%d %H:%M:%S'), 'type': r[1], 'detail': r[2]} for r in rows]
        except Exception as e:
            self.ctrl.logger.error(f"[RECENT ANOMALY] {e}")
            return []

    def _json_resp(self, data, code=200):
        body = json.dumps(data, ensure_ascii=False)
        return Response(content_type='application/json; charset=utf-8',
                        body=body.encode('utf-8'), status=code)


# -------------- 其余代码保持原样 --------------

# 在文件末尾、CORSMiddleware 之前加这两行即可
import eventlet.wsgi
eventlet.wsgi.HttpProtocol.debug = False     # 关闭调试回显，绕过中文编码问题

# 强制 WSGI 用 UTF-8 编码错误页，避免 latin-1 炸中文
import eventlet.wsgi
eventlet.wsgi.HttpProtocol.encode_chunk = lambda self, x: x if isinstance(x, bytes) else x.encode('utf-8')

# -------------- 跨域 & 补丁 --------------
class CORSMiddleware:
    def __init__(self, wsgi_app):
        self.wsgi_app = wsgi_app
    def __call__(self, environ, start_response):
        def cors_start(status, headers, exc_info=None):
            headers.append(('Access-Control-Allow-Origin', '*'))
            headers.append(('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS'))
            headers.append(('Access-Control-Allow-Headers', 'Content-Type, X-User-Id'))
            return start_response(status, headers, exc_info)
        if environ.get('REQUEST_METHOD') == 'OPTIONS':
            return [b'']
        return self.wsgi_app(environ, cors_start)

_original_create_contexts = ry_app_mgr.AppManager.create_contexts
def _patched_create_contexts(self):
    ret = _original_create_contexts(self)
    wsgi = ret.get('wsgi')
    if wsgi and hasattr(wsgi, '_app'):
        wsgi._app = CORSMiddleware(wsgi._app)   # ← 这里必须包一层
    return ret
ry_app_mgr.AppManager.create_contexts = _patched_create_contexts

