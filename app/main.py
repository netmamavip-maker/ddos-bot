#!/usr/bin/env python3
"""
🔍 Facebook Activity Monitor v2.0
Real-time status tracking, last seen scraper, session persistence
"""

import os
import json
import logging
import threading
import time
import requests
from pathlib import Path
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from dotenv import load_dotenv
from flask import Flask, jsonify
from bs4 import BeautifulSoup
import sqlite3

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
FB_EMAIL = os.getenv("FB_EMAIL")
FB_PASSWORD = os.getenv("FB_PASSWORD")
PORT = int(os.getenv("PORT", 10000))

if not all([TELEGRAM_BOT_TOKEN, FB_EMAIL, FB_PASSWORD]):
    raise ValueError("❌ Missing: TELEGRAM_BOT_TOKEN, FB_EMAIL, FB_PASSWORD")

DB_FILE = "facebook_tracker.db"
app = Flask(__name__)

# ============================================================================
# DATABASE
# ============================================================================

class TrackerDB:
    @staticmethod
    def init():
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS targets (
            id INTEGER PRIMARY KEY,
            fb_id TEXT UNIQUE,
            name TEXT,
            url TEXT,
            user_id INTEGER,
            created_at TIMESTAMP
        )''')
        c.execute('''CREATE TABLE IF NOT EXISTS activity (
            id INTEGER PRIMARY KEY,
            fb_id TEXT,
            status TEXT,
            last_seen TEXT,
            timestamp TIMESTAMP,
            FOREIGN KEY(fb_id) REFERENCES targets(fb_id)
        )''')
        c.execute('''CREATE TABLE IF NOT EXISTS sessions (
            id INTEGER PRIMARY KEY,
            user_id INTEGER UNIQUE,
            cookie_jar TEXT,
            last_login TIMESTAMP
        )''')
        conn.commit()
        conn.close()
    
    @staticmethod
    def add_target(fb_id, name, url, user_id):
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        try:
            c.execute('INSERT INTO targets (fb_id, name, url, user_id, created_at) VALUES (?, ?, ?, ?, ?)',
                      (fb_id, name, url, user_id, datetime.now()))
            conn.commit()
            return True
        except:
            return False
        finally:
            conn.close()
    
    @staticmethod
    def log_activity(fb_id, status, last_seen):
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute('INSERT INTO activity (fb_id, status, last_seen, timestamp) VALUES (?, ?, ?, ?)',
                  (fb_id, status, last_seen, datetime.now()))
        conn.commit()
        conn.close()
    
    @staticmethod
    def get_activity(fb_id, limit=10):
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute('SELECT status, last_seen, timestamp FROM activity WHERE fb_id=? ORDER BY timestamp DESC LIMIT ?',
                  (fb_id, limit))
        rows = c.fetchall()
        conn.close()
        return rows
    
    @staticmethod
    def get_targets(user_id):
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute('SELECT fb_id, name, url FROM targets WHERE user_id=?', (user_id,))
        rows = c.fetchall()
        conn.close()
        return rows
    
    @staticmethod
    def save_session(user_id, cookies):
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute('INSERT OR REPLACE INTO sessions (user_id, cookie_jar, last_login) VALUES (?, ?, ?)',
                  (user_id, json.dumps(cookies), datetime.now()))
        conn.commit()
        conn.close()
    
    @staticmethod
    def load_session(user_id):
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute('SELECT cookie_jar FROM sessions WHERE user_id=?', (user_id,))
        row = c.fetchone()
        conn.close()
        return json.loads(row[0]) if row else None

TrackerDB.init()

# ============================================================================
# FACEBOOK SESSION MANAGER
# ============================================================================

class FacebookSession:
    def __init__(self, email, password):
        self.email = email
        self.password = password
        self.session = requests.Session()
        self.driver = None
        self.is_logged_in = False
    
    def login_selenium(self):
        """Login using Selenium (handles 2FA, JavaScript)"""
        try:
            options = Options()
            options.add_argument('--headless')
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
            
            self.driver = webdriver.Chrome(options=options)
            self.driver.get('https://www.facebook.com/login')
            
            # Email
            email_field = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.ID, 'email'))
            )
            email_field.send_keys(self.email)
            
            # Password
            pass_field = self.driver.find_element(By.ID, 'pass')
            pass_field.send_keys(self.password)
            
            # Click login
            login_btn = self.driver.find_element(By.NAME, 'login')
            login_btn.click()
            
            # Wait for redirect (adjust time if 2FA required)
            time.sleep(5)
            WebDriverWait(self.driver, 15).until(
                EC.presence_of_element_located((By.ID, 'mount_0_0'))
            )
            
            # Extract cookies
            cookies = {c['name']: c['value'] for c in self.driver.get_cookies()}
            self.session.cookies.update(cookies)
            self.is_logged_in = True
            
            logger.info("✅ Facebook session authenticated")
            return True
        
        except Exception as e:
            logger.error(f"❌ Login failed: {e}")
            return False
        
        finally:
            if self.driver:
                self.driver.quit()
    
    def get_profile_info(self, profile_url):
        """Scrape profile status, last seen, online status"""
        try:
            resp = self.session.get(profile_url, timeout=10)
            soup = BeautifulSoup(resp.content, 'html.parser')
            
            # Parse active now / last seen
            status = "offline"
            last_seen = "unknown"
            
            # Look for "Active now" indicator
            if "Active now" in resp.text:
                status = "online"
                last_seen = "now"
            
            # Look for "Active Xm ago" or "Active Xh ago"
            time_patterns = soup.find_all(string=lambda x: x and ("Active" in x and "ago" in x))
            if time_patterns:
                last_seen = time_patterns[0].strip()
                status = "seen_recently"
            
            # Get name
            name_elem = soup.find('h1')
            name = name_elem.text.strip() if name_elem else "Unknown"
            
            return {
                'name': name,
                'status': status,
                'last_seen': last_seen,
                'timestamp': datetime.now().isoformat()
            }
        
        except Exception as e:
            logger.error(f"❌ Scrape error: {e}")
            return None
    
    def get_fb_id_from_url(self, url):
        """Extract Facebook ID from profile URL"""
        try:
            if 'facebook.com/' in url:
                # https://facebook.com/username or /profile.php?id=123456
                if 'profile.php?id=' in url:
                    return url.split('id=')[1].split('&')[0]
                else:
                    username = url.split('facebook.com/')[1].split('/')[0]
                    return username
            return None
        except:
            return None

fb_session = FacebookSession(FB_EMAIL, FB_PASSWORD)

# ============================================================================
# TRACKER ENGINE
# ============================================================================

class ActivityTracker:
    def __init__(self):
        self.tracking = {}
        self.lock = threading.Lock()
    
    def add_target(self, user_id, profile_url, interval=60):
        """Start tracking a profile"""
        fb_id = fb_session.get_fb_id_from_url(profile_url)
        
        if not fb_id:
            return False, "❌ Invalid Facebook URL"
        
        # Get initial info
        info = fb_session.get_profile_info(profile_url)
        if not info:
            return False, "❌ Cannot access profile (private or login issue)"
        
        # Save to DB
        TrackerDB.add_target(fb_id, info['name'], profile_url, user_id)
        
        # Start tracking
        with self.lock:
            self.tracking[fb_id] = {
                'user_id': user_id,
                'url': profile_url,
                'interval': interval,
                'active': True,
                'last_status': info['status'],
                'last_seen': info['last_seen'],
                'last_check': datetime.now()
            }
        
        # Start monitor thread
        threading.Thread(target=self._monitor_profile, args=(fb_id,), daemon=True).start()
        
        logger.info(f"🔍 Tracking started: {info['name']} ({fb_id})")
        return True, f"✅ Tracking *{info['name']}*\nInterval: {interval}s"
    
    def _monitor_profile(self, fb_id):
        """Background monitor for a profile"""
        with self.lock:
            if fb_id not in self.tracking:
                return
            track = self.tracking[fb_id]
        
        while track.get('active', False):
            try:
                info = fb_session.get_profile_info(track['url'])
                if info:
                    # Check for changes
                    old_status = track['last_status']
                    old_last_seen = track['last_seen']
                    
                    # Log to DB
                    TrackerDB.log_activity(fb_id, info['status'], info['last_seen'])
                    
                    # Update tracking
                    with self.lock:
                        if fb_id in self.tracking:
                            self.tracking[fb_id]['last_status'] = info['status']
                            self.tracking[fb_id]['last_seen'] = info['last_seen']
                            self.tracking[fb_id]['last_check'] = datetime.now()
                    
                    # Change detection
                    if info['status'] != old_status or info['last_seen'] != old_last_seen:
                        logger.info(f"⚠️ {fb_id}: {old_status} → {info['status']} | {old_last_seen} → {info['last_seen']}")
                
                time.sleep(track['interval'])
            
            except Exception as e:
                logger.error(f"Monitor error ({fb_id}): {e}")
                time.sleep(60)
    
    def stop_tracking(self, fb_id):
        """Stop tracking a profile"""
        with self.lock:
            if fb_id in self.tracking:
                self.tracking[fb_id]['active'] = False
                del self.tracking[fb_id]
                logger.info(f"🛑 Tracking stopped: {fb_id}")
                return True
        return False
    
    def get_status(self, fb_id):
        """Get current status of a tracked profile"""
        with self.lock:
            if fb_id in self.tracking:
                track = self.tracking[fb_id]
                return {
                    'active': True,
                    'status': track['last_status'],
                    'last_seen': track['last_seen'],
                    'last_check': track['last_check'].isoformat(),
                    'interval': track['interval']
                }
        return {'active': False}
    
    def get_history(self, fb_id, limit=20):
        """Get activity history"""
        rows = TrackerDB.get_activity(fb_id, limit)
        return [{'status': r[0], 'last_seen': r[1], 'timestamp': r[2]} for r in rows]

tracker = ActivityTracker()

# ============================================================================
# FLASK ENDPOINTS
# ============================================================================

@app.route('/', methods=['GET'])
def health():
    return jsonify({
        'status': 'running',
        'service': 'Facebook Activity Tracker v2.0',
        'timestamp': datetime.now().isoformat(),
        'logged_in': fb_session.is_logged_in
    }), 200

@app.route('/targets/<int:user_id>', methods=['GET'])
def get_targets(user_id):
    targets = TrackerDB.get_targets(user_id)
    return jsonify({
        'targets': [{'fb_id': t[0], 'name': t[1], 'url': t[2]} for t in targets]
    }), 200

@app.route('/status/<fb_id>', methods=['GET'])
def get_status_endpoint(fb_id):
    return jsonify(tracker.get_status(fb_id)), 200

@app.route('/history/<fb_id>', methods=['GET'])
def get_history_endpoint(fb_id):
    return jsonify({
        'history': tracker.get_history(fb_id)
    }), 200

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
            resp = requests.post(f"{self.base_url}/getUpdates",
                                json={"offset": self.offset, "timeout": 30}, timeout=35)
            data = resp.json()
            return data.get('result', []) if data.get('ok') else []
        except Exception as e:
            logger.error(f"Get updates error: {e}")
            return []
    
    def send_message(self, chat_id, text, parse_mode="Markdown"):
        try:
            requests.post(f"{self.base_url}/sendMessage",
                         json={"chat_id": chat_id, "text": text, "parse_mode": parse_mode},
                         timeout=10)
        except Exception as e:
            logger.error(f"Send message error: {e}")
    
    def send_menu(self, chat_id):
        requests.post(f"{self.base_url}/sendMessage",
                     json={
                         "chat_id": chat_id,
                         "text": "🔍 *Facebook Activity Tracker*\n\nTrack profiles in real-time",
                         "parse_mode": "Markdown",
                         "reply_markup": {
                             "inline_keyboard": [
                                 [{"text": "➕ Add Target", "callback_data": "add_target"},
                                  {"text": "📊 My Targets", "callback_data": "list_targets"}],
                                 [{"text": "🔴 Active Now", "callback_data": "active"},
                                  {"text": "📋 History", "callback_data": "history"}]
                             ]
                         }
                     }, timeout=10)
    
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
        
        elif text.startswith('https://facebook.com') or text.startswith('https://www.facebook.com'):
            success, msg = tracker.add_target(user_id, text, interval=60)
            self.send_message(chat_id, msg)
        
        elif text.startswith('/status '):
            fb_id = text[8:].strip()
            status = tracker.get_status(fb_id)
            if status['active']:
                msg = (f"🔴 *{fb_id}*\n"
                       f"Status: `{status['status']}`\n"
                       f"Last Seen: `{status['last_seen']}`\n"
                       f"Last Check: `{status['last_check']}`")
            else:
                msg = "❌ Not tracking"
            self.send_message(chat_id, msg)
        
        elif text.startswith('/history '):
            fb_id = text[9:].strip()
            history = tracker.get_history(fb_id, 10)
            msg = f"📋 *History for {fb_id}*\n\n"
            for h in history:
                msg += f"`{h['timestamp']}` → `{h['status']}` ({h['last_seen']})\n"
            self.send_message(chat_id, msg)
    
    def handle_callback(self, callback):
        chat_id = callback['message']['chat']['id']
        data = callback['data']
        user_id = callback['from']['id']
        
        if data == "add_target":
            self.send_message(chat_id, "📎 Send Facebook profile URL:\n`https://facebook.com/username`")
        elif data == "list_targets":
            targets = TrackerDB.get_targets(user_id)
            msg = "*Your Targets:*\n\n"
            for t in targets:
                msg += f"👤 {t[1]} (`{t[0]}`)\n"
            self.send_message(chat_id, msg if targets else "❌ No targets")
        elif data == "active":
            targets = TrackerDB.get_targets(user_id)
            msg = "*Active Now:*\n\n"
            for t in targets:
                status = tracker.get_status(t[0])
                if status.get('active'):
                    msg += f"🔴 {t[1]}: `{status['status']}`\n"
            self.send_message(chat_id, msg if msg != "*Active Now:*\n\n" else "✅ All offline")
        elif data == "history":
            self.send_message(chat_id, "📋 Use: `/history fb_id`")
    
    def run(self):
        logger.info("🚀 Telegram bot started")
        while True:
            try:
                updates = self.get_updates()
                for update in updates:
                    self.handle_update(update)
                time.sleep(0.05)
            except Exception as e:
                logger.error(f"Bot error: {e}")
                time.sleep(5)

def start_bot():
    bot = TelegramBot(TELEGRAM_BOT_TOKEN)
    thread = threading.Thread(target=bot.run, daemon=True)
    thread.start()

# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    # Login to Facebook
    logger.info("🔑 Authenticating Facebook...")
    if not fb_session.login_selenium():
        logger.warning("⚠️ Facebook login failed - tracking may be limited")
    
    # Start telegram bot
    start_bot()
    
    logger.info(f"🚀 Flask server on 0.0.0.0:{PORT}")
    logger.info("🔍 Facebook Activity Tracker v2.0 - ONLINE")
    
    app.run(host='0.0.0.0', port=PORT, debug=False, use_reloader=False)
