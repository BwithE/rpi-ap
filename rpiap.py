#!/usr/bin/python3
# rpiap.py – FINAL CLEAN VERSION (no dnsmasq edits, original login method)
from flask import Flask, render_template_string, request, redirect, url_for, session, flash
import subprocess
import re
import os
import json
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'rpiap_super_secure_key_2025_change_me'

# === CONFIG ===
CONFIG_DIR = "/etc/rpiap"
os.makedirs(CONFIG_DIR, exist_ok=True)
CREDS_FILE = f"{CONFIG_DIR}/creds.json"
BLOCKLIST_FILE = f"{CONFIG_DIR}/blocked_macs.txt"
DNSMASQ_LOG = "/var/log/dnsmasq.log"
WIFICARD = "wlan0"

DEFAULT_CREDS = {"username": "admin", "password": "admin"}

def load_creds():
    if os.path.exists(CREDS_FILE):
        try:
            with open(CREDS_FILE) as f:
                return json.load(f)
        except:
            return DEFAULT_CREDS
    return DEFAULT_CREDS

def save_creds(username, password):
    with open(CREDS_FILE, "w") as f:
        json.dump({"username": username, "password": password}, f)

def load_blocked():
    if os.path.exists(BLOCKLIST_FILE):
        with open(BLOCKLIST_FILE) as f:
            return [line.strip().upper() for line in f if line.strip()]
    return []

def save_blocked(mac_list):
    with open(BLOCKLIST_FILE, "w") as f:
        for mac in mac_list:
            f.write(mac + "\n")

def get_clients():
    try:
        result = subprocess.check_output(["arp", "-a"]).decode()
    except:
        return []
    clients = []
    blocked = load_blocked()
    for line in result.splitlines():
        ip_match = re.search(r'\(([\d.]+)\)', line)
        mac_match = re.search(r'([0-9a-f]{2}:[0-9a-f]{2}:[0-9a-f]{2}:[0-9a-f]{2}:[0-9a-f]{2}:[0-9a-f]{2})', line, re.I)
        hostname = line.split()[0] if line.split() else "unknown"
        if ip_match and mac_match:
            ip = ip_match.group(1)
            mac = mac_match.group(1).upper()
            status = "Blocked" if mac in blocked else "Allowed"
            clients.append({"ip": ip, "mac": mac, "hostname": hostname, "status": status})
    return clients

def get_traffic_mb():
    try:
        rx = int(open(f"/sys/class/net/{WIFICARD}/statistics/rx_bytes").read())
        tx = int(open(f"/sys/class/net/{WIFICARD}/statistics/tx_bytes").read())
        return round(rx / (1024*1024), 1), round(tx / (1024*1024), 1)
    except:
        return 0, 0

def get_uptime_compact():
    try:
        secs = int(float(open('/proc/uptime').read().split()[0]))
        d = secs // 86400
        h = (secs % 86400) // 3600
        m = (secs % 3600) // 60
        s = secs % 60
        parts = []
        if d: parts.append(f"{d}d")
        if h: parts.append(f"{h}h")
        if m: parts.append(f"{m}m")
        if s or not parts: parts.append(f"{s}s")
        return "".join(parts)
    except:
        return "0m"

def get_stats():
    down_mb, up_mb = get_traffic_mb()
    return {
        "clients": len(get_clients()),
        "uptime": get_uptime_compact(),
        "data_down": down_mb,
        "data_up": up_mb
    }

def restart_ap():
    subprocess.run(["systemctl", "restart", "hostapd"], timeout=15)
    subprocess.run(["systemctl", "restart", "dnsmasq"], timeout=15)

def get_recent_dns_queries():
    if not os.path.exists(DNSMASQ_LOG):
        return []
    try:
        lines = subprocess.check_output(["tail", "-n", "200", DNSMASQ_LOG]).decode()
        queries = []
        for line in lines.splitlines():
            if "query[A]" in line or "query[AAAA]" in line:
                parts = line.split()
                if len(parts) >= 8:
                    # Extract time
                    time_str = parts[0] + " " + parts[1] + " " + parts[2]
                    try:
                        timestamp = datetime.strptime(f"{datetime.now().year} {time_str}", "%Y %b %d %H:%M:%S")
                    except:
                        timestamp = datetime.now()
                    domain = parts[-1]
                    ip = parts[5] if len(parts) > 5 and parts[5] not in ("query[A]", "query[AAAA]") else "unknown"
                    queries.append({"time": timestamp.strftime("%H:%M:%S"), "ip": ip, "domain": domain})
        return queries[-30:]  # last 30
    except:
        return []

def login_required(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('logged_in'):
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated

# =============================================================================
# TEMPLATES (clean & beautiful)
# =============================================================================

BASE_WITH_REFRESH = '''
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>RPiAP – {{ title }}</title>
    <meta http-equiv="refresh" content="10">
    <style>
        :root{--bg:#0d1117;--card:#161b22;--border:#30363d;--text:#c9d1d9;--accent:#58a6ff;--red:#f85149;--green:#238636}
        body{margin:0;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;background:var(--bg);color:var(--text);}
        .header{background:var(--card);border-bottom:1px solid var(--border);padding:15px;display:flex;align-items:center;justify-content:space-between;position:relative;z-index:10;}
        .menu-btn{background:none;border:none;font-size:1.8em;color:var(--accent);cursor:pointer;}
        .overlay{display:none;position:fixed;inset:0;background:rgba(0,0,0,0.7);z-index:98;}
        .sidebar{position:fixed;top:0;left:-280px;width:260px;height:100%;background:var(--card);border-right:1px solid var(--border);transition:left .3s;z-index:99;padding-top:70px;}
        .sidebar a{display:block;padding:18px 25px;color:var(--text);text-decoration:none;font-size:1.1em;border-bottom:1px solid var(--border);}
        .sidebar a:hover{background:#1f6feb15;}
        .sidebar a.active{background:#1f6feb30;color:var(--accent);font-weight:bold;}
        .sidebar a.logout{color:var(--red);}
        .content{padding:20px;}
        @media(min-width:768px){
            .menu-btn,.overlay{display:none;}
            .sidebar{left:0;position:relative;width:220px;float:left;height:100vh;padding-top:20px;}
            .content{margin-left:220px;padding:30px;}
            .header{justify-content:flex-start;}
        }
    </style>
</head>
<body>
    <div class="header">
        <button class="menu-btn" onclick="document.querySelector('.sidebar').style.left='0';document.querySelector('.overlay').style.display='block'">Menu</button>
        <div></div><div></div>
    </div>
    <div class="overlay" onclick="document.querySelector('.sidebar').style.left='-280px';this.style.display='none'"></div>
    <div class="sidebar">
        <a href="/dashboard" {% if title == "Dashboard" %}class="active"{% endif %}>Dashboard</a>
        <a href="/clients" {% if title == "Clients" %}class="active"{% endif %}>Clients</a>
        <a href="/traffic" {% if title == "Traffic" %}class="active"{% endif %}>Traffic</a>
        <a href="/settings" {% if title == "Settings" %}class="active"{% endif %}>Settings</a>
        <a href="/logout" class="logout">Logout</a>
    </div>
    <div class="content">
        {% block content %}{% endblock %}
    </div>
</body>
</html>
'''

BASE_NO_REFRESH = BASE_WITH_REFRESH.replace('<meta http-equiv="refresh" content="10">', '')

# PERFECT CENTERED LOGIN PAGE
LOGIN_HTML = '''
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>RPiAP Login</title>
    <style>
        body{margin:0;background:#0d1117;color:#c9d1d9;display:flex;justify-content:center;align-items:center;min-height:100vh;font-family:-apple-system,system-ui,sans-serif;}
        .login-box{background:#161b22;padding:50px 40px;border-radius:16px;box-shadow:0 15px 50px rgba(0,0,0,0.7);width:90%;max-width:380px;text-align:center;}
        h1{color:#58a6ff;margin:0 0 40px;font-size:2.2em;font-weight:300;}
        input{width:100%;padding:16px;margin:12px 0;border-radius:12px;border:1px solid #30363d;background:#0d1117;color:white;font-size:1.1em;box-sizing:border-box;}
        input:focus{outline:none;border-color:#58a6ff;}
        button{width:100%;padding:18px;margin-top:20px;background:#238636;color:white;border:none;border-radius:12px;font-size:1.2em;font-weight:bold;cursor:pointer;}
        button:hover{background:#2ea043;}
        .error{color:#f85149;margin:15px 0;font-size:0.95em;}
        .note{margin-top:30px;font-size:0.85em;opacity:0.7;}
    </style>
</head>
<body>
<div class="login-box">
    <h1>RPiAP Login</h1>
    {% with messages = get_flashed_messages() %}
      {% if messages %}<div class="error">{{ messages[0] }}</div>{% endif %}
    {% endwith %}
    <form method="post">
        <input type="text" name="username" placeholder="Username" required autofocus>
        <input type="password" name="password" placeholder="Password" required>
        <button type="submit">Login</button>
    </form>
</div>
</body>
</html>
'''

# All other HTML templates remain exactly the same as last working version
DASHBOARD_HTML = BASE_WITH_REFRESH.replace('{% block content %}{% endblock %}', '''
    <h1 style="text-align:center;color:#58a6ff;font-size:2.8em;margin-bottom:50px;">RPi Access Point</h1>
    <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:25px;">
        <div style="background:#161b22;padding:30px;border-radius:16px;text-align:center;box-shadow:0 10px 30px rgba(0,0,0,0.5);">
            <div style="font-size:3em;margin-bottom:10px;">Users</div>
            <div style="font-size:4.5em;font-weight:bold;color:#58a6ff;">{{ stats.clients }}</div>
            <div style="font-size:1.4em;opacity:0.9;">Connected Clients</div>
        </div>
        <div style="background:#161b22;padding:30px;border-radius:16px;text-align:center;box-shadow:0 10px 30px rgba(0,0,0,0.5);">
            <div style="font-size:3em;margin-bottom:10px;">Down Arrow</div>
            <div style="font-size:4.5em;font-weight:bold;color:#79c0ff;">{{ stats.data_down }}</div>
            <div style="font-size:1.4em;opacity:0.9;">Data Received (MB)</div>
        </div>
        <div style="background:#161b22;padding:30px;border-radius:16px;text-align:center;box-shadow:0 10px 30px rgba(0,0,0,0.5);">
            <div style="font-size:3em;margin-bottom:10px;">Up Arrow</div>
            <div style="font-size:4.5em;font-weight:bold;color:#79c0ff;">{{ stats.data_up }}</div>
            <div style="font-size:1.4em;opacity:0.9;">Data Sent (MB)</div>
        </div>
        <div style="background:#161b22;padding:30px;border-radius:16px;text-align:center;box-shadow:0 10px 30px rgba(0,0,0,0.5);">
            <div style="font-size:3em;margin-bottom:10px;">Clock</div>
            <div style="font-size:4em;font-weight:bold;color:#8b949e;">{{ stats.uptime }}</div>
            <div style="font-size:1.4em;opacity:0.9;">System Uptime</div>
        </div>
    </div>
    <p style="text-align:center;margin-top:60px;opacity:0.7;">
        Access Point IP: 10.10.10.1 • {{ now }}
    </p>
''').replace('{{ title }}', 'Dashboard')

CLIENTS_HTML = BASE_WITH_REFRESH.replace('{% block content %}{% endblock %}', '''
    <h1 style="text-align:center;color:#58a6ff;margin:30px 0;">Connected Clients ({{ clients|length }})</h1>
    <div style="overflow-x:auto;">
        <table style="width:100%;max-width:1000px;margin:0 auto;border-collapse:collapse;background:#161b22;">
            <tr style="background:#0d1117;">
                <th style="padding:14px;border:1px solid #30363d;">IP</th>
                <th style="padding:14px;border:1px solid #30363d;">MAC Address</th>
                <th style="padding:14px;border:1px solid #30363d;">Hostname</th>
                <th style="padding:14px;border:1px solid #30363d;">Status</th>
                <th style="padding:14px;border:1px solid #30363d;">Action</th>
            </tr>
            {% for c in clients %}
            <tr>
                <td style="padding:14px;border:1px solid #30363d;">{{ c.ip }}</td>
                <td style="padding:14px;border:1px solid #30363d;"><code>{{ c.mac }}</code></td>
                <td style="padding:14px;border:1px solid #30363d;">{{ c.hostname }}</td>
                <td style="padding:14px;border:1px solid #30363d;color:{% if c.status == 'Blocked' %}#f85149{% else %}#238636{% endif %};font-weight:bold;">{{ c.status }}</td>
                <td style="padding:14px;border:1px solid #30363d;">
                    <form method="post" action="/toggle/{{ c.mac }}" style="display:inline;">
                        <button style="padding:10px 16px;border:none;border-radius:8px;cursor:pointer;font-weight:bold;background:{% if c.status == 'Blocked' %}#238636{% else %}#f85149{% endif %};color:white;">
                            {{ 'Unblock' if c.status == 'Blocked' else 'Block' }}
                        </button>
                    </form>
                </td>
            </tr>
            {% endfor %}
        </table>
    </div>
''').replace('{{ title }}', 'Clients')

TRAFFIC_HTML = BASE_WITH_REFRESH.replace('{% block content %}{% endblock %}', '''
    <h1 style="text-align:center;color:#58a6ff;margin:30px 0;">Live Traffic</h1>
    <div style="background:#161b22;padding:20px;border-radius:12px;max-width:1000px;margin:0 auto;overflow-x:auto;">
        <table style="width:100%;border-collapse:collapse;">
            <tr style="background:#0d1117;">
                <th style="padding:14px;text-align:left;">Time</th>
                <th style="padding:14px;text-align:left;">IP</th>
                <th style="padding:14px;text-align:left;">Domain</th>
            </tr>
            {% for q in queries %}
            <tr style="border-bottom:1px solid #30363d;">
                <td style="padding:14px;font-family:monospace;">{{ q.time }}</td>
                <td style="padding:14px;">{{ q.ip }}</td>
                <td style="padding:14px;color:#79c0ff;">{{ q.domain }}</td>
            </tr>
            {% endfor %}
            {% if not queries %}
            <tr><td colspan="3" style="padding:40px;text-align:center;opacity:0.6;">No recent DNS queries detected</td></tr>
            {% endif %}
        </table>
    </div>
''').replace('{{ title }}', 'Traffic')

SETTINGS_HTML = BASE_NO_REFRESH.replace('{% block content %}{% endblock %}', '''
    <div style="max-width:500px;margin:40px auto;background:#161b22;padding:30px;border-radius:12px;">
        <h1 style="text-align:center;color:#58a6ff;">Settings</h1>
        {% with messages = get_flashed_messages() %}
          {% if messages %}<div style="background:#23863620;padding:15px;border-radius:10px;margin:20px 0;color:#8bf39f;text-align:center;font-weight:bold;">{{ messages[0] }}</div>{% endif %}
        {% endwith %}
        <form method="post">
            <h2 style="color:#58a6ff;margin-top:30px;">Admin Login</h2>
            <input type="text" name="username" value="{{ creds.username }}" required style="width:100%;padding:14px;margin:10px 0;border-radius:8px;background:#0d1117;border:1px solid #30363d;color:white;">
            <input type="password" name="password" placeholder="Leave blank to keep current" style="width:100%;padding:14px;margin:10px 0;border-radius:8px;background:#0d1117;border:1px solid #30363d;color:white;">

            <h2 style="color:#58a6ff;margin-top:30px;">WiFi Channel</h2>
            <select name="channel" style="width:100%;padding:14px;margin:10px 0;border-radius:8px;background:#0d1117;border:1px solid #30363d;color:white;">
                {% for ch in [1,6,11,36,40,44,48,149,153,157,161,165] %}
                <option value="{{ ch }}" {% if ch == current_channel %}selected{% endif %}>Channel {{ ch }} {% if ch <=11 %}(2.4 GHz){% else %}(5 GHz){% endif %}</option>
                {% endfor %}
            </select>

            <button type="submit" style="width:100%;padding:16px;margin-top:30px;background:#238636;color:white;border:none;border-radius:12px;font-weight:bold;cursor:pointer;">
                Save Settings
            </button>
        </form>
    </div>
''').replace('{{ title }}', 'Settings')

# =============================================================================
# ROUTES – BACK TO ORIGINAL WORKING LOGIN METHOD
# =============================================================================

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        creds = load_creds()
        if request.form['username'] == creds['username'] and request.form['password'] == creds['password']:
            session['logged_in'] = True
            return redirect(url_for('dashboard'))
        flash('Wrong username or password')
    return render_template_string(LOGIN_HTML)

@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    return redirect(url_for('login'))

@app.route('/toggle/<mac>', methods=['POST'])
@login_required
def toggle(mac):
    mac = mac.upper()
    blocked = load_blocked()
    if mac in blocked:
        blocked.remove(mac)
        subprocess.run(["iptables", "-D", "FORWARD", "-m", "mac", "--mac-source", mac, "-j", "DROP"], stderr=subprocess.DEVNULL)
    else:
        blocked.append(mac)
        subprocess.run(["iptables", "-I", "FORWARD", "1", "-m", "mac", "--mac-source", mac, "-j", "DROP"])
    save_blocked(blocked)
    subprocess.run("iptables-save > /etc/iptables/rules.v4", shell=True)
    return redirect(url_for('clients'))

@app.route('/dashboard')
@login_required
def dashboard():
    return render_template_string(DASHBOARD_HTML, stats=get_stats(), now=subprocess.check_output("date").decode().strip())

@app.route('/clients')
@login_required
def clients():
    return render_template_string(CLIENTS_HTML, clients=get_clients())

@app.route('/traffic')
@login_required
def traffic():
    return render_template_string(TRAFFIC_HTML, queries=get_recent_dns_queries())

@app.route('/settings', methods=['GET', 'POST'])
@login_required
def settings():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password'].strip()
        channel = request.form['channel']

        # Always save new username
        old_password = load_creds()['password']
        save_creds(username, password if password else old_password)

        # Only restart if channel changed
        current_channel_line = subprocess.check_output("grep '^channel=' /etc/hostapd/hostapd.conf | cut -d= -f2", shell=True).decode().strip()
        if current_channel_line != channel:
            mode = "g" if int(channel) <= 11 else "a"
            subprocess.run(f"sed -i 's/^channel=.*/channel={channel}/' /etc/hostapd/hostapd.conf", shell=True)
            subprocess.run(f"sed -i 's/^hw_mode=.*/hw_mode={mode}/' /etc/hostapd/hostapd.conf", shell=True)
            restart_ap()
            flash("Channel changed — Access Point restarted!")
        else:
            flash("Settings saved — no restart needed")

    current_channel_line = subprocess.check_output("grep '^channel=' /etc/hostapd/hostapd.conf | cut -d= -f2", shell=True).decode().strip()
    current_channel = int(current_channel_line) if current_channel_line.isdigit() else 6
    return render_template_string(SETTINGS_HTML, creds=load_creds(), current_channel=current_channel)

@app.route('/')
def index():
    return redirect(url_for('dashboard' if session.get('logged_in') else 'login'))

if __name__ == '__main__':
    # NO dnsmasq config changes — you already did it
    # Just restore blocked MACs on startup
    for mac in load_blocked():
        subprocess.run(["iptables", "-C", "FORWARD", "-m", "mac", "--mac-source", mac, "-j", "DROP"],
                       stderr=subprocess.DEVNULL, check=False) or \
        subprocess.run(["iptables", "-I", "FORWARD", "1", "-m", "mac", "--mac-source", mac, "-j", "DROP"])
    subprocess.run("iptables-save > /etc/iptables/rules.v4", shell=True)

    app.run(host='0.0.0.0', port=80)
