import os
import sys
import json
import threading
import time
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from flask import Flask, render_template_string, jsonify, request
except ImportError:
    print("[!] Flask not installed. Run: pip install flask")
    Flask = None
    render_template_string = None
    jsonify = None
    request = None

from core.utils import colored

app = Flask(__name__) if Flask else None

# Shared state
state = {
    "status": "idle",
    "target": "",
    "logs": [],
    "commands": [],
    "start_time": None,
    "modules": {},
    "targets": {},  # multi-target: {target: {status, start_time, ports, services, findings, logs}}
    "stats": {"ports": 0, "services": 0, "attacks": 0, "uptime": "0s"}
}

# Shared dashboard data
dashboard_data = {
    "targets": {},
    "recent_activity": [],
    "system_info": {},
}

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AdhiHub CYBER-OMNI Dashboard</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: 'Courier New', monospace; background: #0a0a0a; color: #e0e0e0; padding: 20px; }
        .container { max-width: 1400px; margin: 0 auto; }
        .header { display: flex; justify-content: space-between; align-items: center; padding: 15px 20px; background: #1a1a1a; border: 1px solid #333; border-radius: 6px; margin-bottom: 20px; }
        .header h1 { color: #ff4444; font-size: 20px; }
        .status { padding: 8px 16px; border-radius: 4px; font-weight: bold; }
        .status.idle { background: #333; color: #888; }
        .status.running { background: #ff4400; color: #fff; animation: pulse 1s infinite; }
        .status.done { background: #00aa00; color: #fff; }
        .status.error { background: #cc0000; color: #fff; }
        @keyframes pulse { 0% { opacity: 1; } 50% { opacity: 0.6; } 100% { opacity: 1; } }

        .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-bottom: 20px; }
        .card { background: #1a1a1a; border: 1px solid #333; border-radius: 6px; padding: 20px; }
        .card h2 { color: #ff8844; font-size: 14px; margin-bottom: 15px; text-transform: uppercase; letter-spacing: 1px; border-bottom: 1px solid #333; padding-bottom: 8px; }
        .card.full { grid-column: 1 / -1; }
        .card.third { grid-column: span 1; }

        .log-area { height: 400px; overflow-y: auto; font-size: 12px; line-height: 1.5; background: #0a0a0a; padding: 10px; border-radius: 4px; border: 1px solid #252525; }
        .log-area::-webkit-scrollbar { width: 6px; }
        .log-area::-webkit-scrollbar-thumb { background: #444; border-radius: 3px; }
        .log-entry { padding: 2px 0; border-bottom: 1px solid #111; }
        .log-time { color: #666; }
        .log-info { color: #88ccff; }
        .log-ok { color: #44ff44; }
        .log-warn { color: #ffcc44; }
        .log-err { color: #ff4444; }

        .stat-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; }
        .stat { text-align: center; padding: 15px; background: #0a0a0a; border-radius: 4px; border: 1px solid #252525; }
        .stat .value { font-size: 28px; font-weight: bold; color: #ff8844; }
        .stat .label { font-size: 11px; color: #888; margin-top: 5px; text-transform: uppercase; }

        .cmd-input { display: flex; gap: 10px; margin-top: 15px; }
        .cmd-input input { flex: 1; padding: 10px 15px; background: #0a0a0a; border: 1px solid #333; color: #e0e0e0; font-family: 'Courier New', monospace; border-radius: 4px; }
        .cmd-input input:focus { outline: none; border-color: #ff8844; }
        .cmd-input button { padding: 10px 20px; background: #ff4444; color: #fff; border: none; border-radius: 4px; cursor: pointer; font-family: 'Courier New', monospace; }
        .cmd-input button:hover { background: #cc0000; }

        .attack-btn { display: inline-block; padding: 12px 24px; margin: 5px; background: #333; color: #e0e0e0; border: 1px solid #555; border-radius: 4px; cursor: pointer; font-family: 'Courier New', monospace; font-size: 12px; }
        .attack-btn:hover { background: #ff4444; border-color: #ff4444; }
        .attack-btn.active { background: #ff4400; border-color: #ff4400; }

        .module-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(150px, 1fr)); gap: 8px; }
        .module-item { padding: 10px; background: #0a0a0a; border: 1px solid #252525; border-radius: 4px; text-align: center; cursor: pointer; font-size: 12px; }
        .module-item:hover { border-color: #ff8844; }
        .module-item .icon { font-size: 24px; margin-bottom: 5px; }

        .target-table { width: 100%; border-collapse: collapse; font-size: 12px; }
        .target-table th { background: #252525; color: #ff8844; padding: 8px 10px; text-align: left; border-bottom: 2px solid #333; }
        .target-table td { padding: 8px 10px; border-bottom: 1px solid #222; }
        .target-table tr:hover td { background: #1f1f1f; }
        .target-status { display: inline-block; width: 8px; height: 8px; border-radius: 50%; margin-right: 6px; }
        .target-status.idle { background: #666; }
        .target-status.running { background: #ff4400; animation: pulse 1s infinite; }
        .target-status.done { background: #00aa00; }
        .target-status.error { background: #cc0000; }
        .findings-badge { display: inline-block; padding: 2px 6px; border-radius: 3px; font-size: 10px; font-weight: bold; }
        .findings-badge.critical { background: #cc0000; color: #fff; }
        .findings-badge.high { background: #ff4400; color: #fff; }
        .findings-badge.medium { background: #ffaa00; color: #000; }
        .findings-badge.low { background: #44aa00; color: #fff; }
        .findings-badge.info { background: #3366cc; color: #fff; }

        @media (max-width: 768px) { .grid { grid-template-columns: 1fr; } .stat-grid { grid-template-columns: repeat(2, 1fr); } }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>AdhiHub CYBER-OMNI v2 Dashboard</h1>
            <div>
                <span class="status {{ state.status }}">{{ state.status.upper() }}</span>
                <span style="color:#666;margin-left:15px;">{{ state.target|truncate(30) }}</span>
                <span style="color:#888;margin-left:15px;font-size:12px;">Targets: {{ state.targets|length }}</span>
            </div>
        </div>

        <div class="grid">
            <div class="card">
                <h2>Quick Attack</h2>
                <div class="cmd-input">
                    <input type="text" id="quickTarget" placeholder="Target IP or domain..." onkeypress="if(event.key==='Enter')sendAttack()">
                    <button onclick="sendAttack()">ATTACK</button>
                </div>
                <div style="margin-top:15px;">
                    <button class="attack-btn" onclick="sendModule('scan')">SCAN</button>
                    <button class="attack-btn" onclick="sendModule('recon')">RECON</button>
                    <button class="attack-btn" onclick="sendModule('osint')">OSINT</button>
                    <button class="attack-btn" onclick="sendModule('exploit')">EXPLOIT</button>
                </div>
            </div>

            <div class="card">
                <h2>Statistics</h2>
                <div class="stat-grid">
                    <div class="stat">
                        <div class="value" id="statTargets">0</div>
                        <div class="label">Targets</div>
                    </div>
                    <div class="stat">
                        <div class="value" id="statPorts">0</div>
                        <div class="label">Ports Found</div>
                    </div>
                    <div class="stat">
                        <div class="value" id="statAttacks">0</div>
                        <div class="label">Attacks Run</div>
                    </div>
                    <div class="stat">
                        <div class="value" id="statUptime">0s</div>
                        <div class="label">Uptime</div>
                    </div>
                </div>
            </div>

            <div class="card full">
                <h2>Targets ({{ state.targets|length }})</h2>
                <div style="overflow-x:auto;">
                    <table class="target-table">
                        <thead>
                            <tr><th>Status</th><th>Target</th><th>Ports</th><th>Findings</th><th>Duration</th></tr>
                        </thead>
                        <tbody id="targetTableBody">
                            <tr id="noTargetsRow"><td colspan="5" style="text-align:center;color:#666;padding:20px;">No targets yet. Launch an attack to begin.</td></tr>
                        </tbody>
                    </table>
                </div>
            </div>

            <div class="card full">
                <h2>Modules</h2>
                <div class="module-grid">
                    <div class="module-item" onclick="sendRaw('/scan ' + getTarget())"><div class="icon">🔍</div>Port Scanner</div>
                    <div class="module-item" onclick="sendRaw('/recon ' + getTarget())"><div class="icon">🕵️</div>Reconnaissance</div>
                    <div class="module-item" onclick="sendRaw('/osint ' + getTarget())"><div class="icon">🌐</div>OSINT</div>
                    <div class="module-item" onclick="sendRaw('/exploit ' + getTarget())"><div class="icon">💥</div>Exploit</div>
                    <div class="module-item" onclick="sendRaw('/attack ' + getTarget())"><div class="icon">⚔️</div>Guided Attack</div>
                    <div class="module-item" onclick="sendRaw('/autopwn ' + getTarget())"><div class="icon">🤖</div>AutoPwn</div>
                    <div class="module-item" onclick="sendRaw('/extract ' + getTarget())"><div class="icon">📥</div>Extract Data</div>
                    <div class="module-item" onclick="sendRaw('/search ' + getTarget())"><div class="icon">🌍</div>Web Search</div>
                    <div class="module-item" onclick="sendRaw('/tor')"><div class="icon">🛡️</div>TOR Status</div>
                    <div class="module-item" onclick="sendRaw('/tools')"><div class="icon">🔧</div>Tools</div>
                    <div class="module-item" onclick="sendRaw('/payload 10.0.0.1 4444')"><div class="icon">💣</div>Payloads</div>
                    <div class="module-item" onclick="sendRaw('/report')"><div class="icon">📄</div>Report</div>
                    <div class="module-item" onclick="sendRaw('/leak ' + getTarget())"><div class="icon">🕵️</div>Leak Check</div>
                    <div class="module-item" onclick="sendRaw('/nmap-parse')"><div class="icon">📋</div>Parse Nmap XML</div>
                </div>
            </div>

            <div class="card full">
                <h2>Live Log</h2>
                <div class="log-area" id="logArea">
                    <div class="log-entry"><span class="log-time">[--:--:--]</span> <span class="log-info">Dashboard ready</span></div>
                </div>
                <div class="cmd-input">
                    <input type="text" id="cmdInput" placeholder="Type any command..." onkeypress="if(event.key==='Enter')sendCommand()">
                    <button onclick="sendCommand()">RUN</button>
                    <button onclick="clearLog()" style="background:#333;">CLEAR</button>
                </div>
            </div>
        </div>
    </div>

    <script>
        var prevTargets = {};

        function getTarget() {
            return document.getElementById('quickTarget').value || 'example.com';
        }
        function sendAttack() {
            var t = document.getElementById('quickTarget').value;
            if (!t) return;
            sendRaw('/attack ' + t);
        }
        function sendModule(mod) {
            sendRaw('/' + mod + ' ' + getTarget());
        }
        function sendRaw(cmd) {
            fetch('/api/command', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({command: cmd, timestamp: new Date().toISOString()})
            });
        }
        function sendCommand() {
            var inp = document.getElementById('cmdInput');
            var cmd = inp.value.trim();
            if (!cmd) return;
            sendRaw(cmd);
            inp.value = '';
        }
        function clearLog() {
            fetch('/api/clear', {method: 'POST'});
        }

        function getSeverityClass(sev) {
            sev = (sev || 'info').toLowerCase();
            return sev === 'critical' ? 'critical' : sev === 'high' ? 'high' : sev === 'medium' ? 'medium' : sev === 'low' ? 'low' : 'info';
        }

        setInterval(function() {
            fetch('/api/state')
                .then(r => r.json())
                .then(data => {
                    var logArea = document.getElementById('logArea');
                    logArea.innerHTML = data.logs.map(function(l) {
                        var cls = l.type === 'info' ? 'log-info' : l.type === 'ok' ? 'log-ok' : l.type === 'warn' ? 'log-warn' : l.type === 'err' ? 'log-err' : '';
                        return '<div class="log-entry"><span class="log-time">[' + l.time + ']</span> <span class="' + cls + '">' + l.text + '</span></div>';
                    }).join('');
                    logArea.scrollTop = logArea.scrollHeight;

                    document.getElementById('statPorts').textContent = data.stats.ports || 0;
                    document.getElementById('statAttacks').textContent = data.stats.attacks || 0;
                    document.getElementById('statUptime').textContent = data.stats.uptime || '0s';

                    var targets = data.targets || {};
                    var targetKeys = Object.keys(targets);
                    document.getElementById('statTargets').textContent = targetKeys.length;

                    var tbody = document.getElementById('targetTableBody');
                    if (targetKeys.length === 0) {
                        tbody.innerHTML = '<tr id="noTargetsRow"><td colspan="5" style="text-align:center;color:#666;padding:20px;">No targets yet. Launch an attack to begin.</td></tr>';
                    } else {
                        var html = '';
                        targetKeys.forEach(function(t) {
                            var info = targets[t];
                            var status = info.status || 'idle';
                            var ports = info.ports || 0;
                            var findings = info.findings || [];
                            var duration = info.duration || '--';
                            var topFinding = findings.length > 0 ? findings[0] : null;
                            var badgeHtml = '';
                            if (topFinding) {
                                var cls = getSeverityClass(topFinding.severity);
                                badgeHtml = '<span class="findings-badge ' + cls + '">' + findings.length + '</span>';
                            }
                            html += '<tr><td><span class="target-status ' + status + '"></span>' + status + '</td><td>' + t + '</td><td>' + ports + '</td><td>' + badgeHtml + '</td><td>' + duration + '</td></tr>';
                        });
                        tbody.innerHTML = html;
                    }
                });
        }, 1000);
    </script>
</body>
</html>"""

state_lock = threading.RLock()


def add_log(text, type="info"):
    with state_lock:
        state["logs"].append({
            "time": datetime.now().strftime("%H:%M:%S"),
            "text": text,
            "type": type
        })
        if len(state["logs"]) > 500:
            state["logs"] = state["logs"][-500:]


def set_status(status, target=""):
    with state_lock:
        state["status"] = status
        if target:
            state["target"] = target
        if status == "running" and not state["start_time"]:
            state["start_time"] = time.time()


def register_target(target, module="scan"):
    with state_lock:
        if target not in state["targets"]:
            state["targets"][target] = {
                "status": "running",
                "module": module,
                "start_time": time.time(),
                "ports": 0,
                "services": [],
                "findings": [],
                "logs": [],
            }
            state["stats"]["attacks"] = state["stats"].get("attacks", 0) + 1
            add_log(f"Target registered: {target} ({module})", "ok")


def update_target(target, key, value):
    with state_lock:
        if target in state["targets"]:
            state["targets"][target][key] = value
            if key == "status" and value == "done":
                elapsed = int(time.time() - state["targets"][target].get("start_time", time.time()))
                state["targets"][target]["duration"] = f"{elapsed}s"


def add_target_finding(target, finding, severity="info"):
    with state_lock:
        if target in state["targets"]:
            state["targets"][target]["findings"].append({
                "finding": finding,
                "severity": severity,
                "time": datetime.now().strftime("%H:%M:%S")
            })


def remove_target(target):
    with state_lock:
        if target in state["targets"]:
            del state["targets"][target]
            add_log(f"Target removed: {target}", "warn")


if app:
    @app.route("/")
    def index():
        return render_template_string(HTML_TEMPLATE, state=state)


if app:
    @app.route("/api/state")
    def api_state():
        uptime = 0
        if state["start_time"]:
            uptime = int(time.time() - state["start_time"])
        uptime_str = f"{uptime}s"
        if uptime >= 3600:
            uptime_str = f"{uptime//3600}h{uptime%3600//60}m"
        elif uptime >= 60:
            uptime_str = f"{uptime//60}m{uptime%60}s"

        with state_lock:
            log_snapshot = list(state["logs"])
            stat_snapshot = dict(state.get("stats", {}))

        stat_snapshot["uptime"] = uptime_str
        return jsonify({
            "status": state["status"],
            "target": state["target"],
            "targets": state["targets"],
            "logs": log_snapshot[-100:],
            "stats": stat_snapshot
        })


if app:
    @app.route("/api/command", methods=["POST"])
    def api_command():
        data = request.get_json()
        cmd = data.get("command", "")
        add_log(f"Command queued: {cmd}", "info")
        with state_lock:
            state["commands"].append(cmd)
        return jsonify({"ok": True})


if app:
    @app.route("/api/targets")
    def api_targets():
        with state_lock:
            tlist = []
            for name, info in state["targets"].items():
                tlist.append({
                    "name": name,
                    "status": info.get("status", "idle"),
                    "module": info.get("module", ""),
                    "ports": info.get("ports", 0),
                    "findings": len(info.get("findings", [])),
                    "duration": info.get("duration", ""),
                })
        return jsonify({"targets": tlist})


if app:
    @app.route("/api/targets/<target>")
    def api_target_detail(target):
        with state_lock:
            info = state["targets"].get(target, {})
        return jsonify(info)


if app:
    @app.route("/api/clear", methods=["POST"])
    def api_clear():
        with state_lock:
            state["logs"] = []
        return jsonify({"ok": True})


def get_next_command():
    with state_lock:
        if state["commands"]:
            return state["commands"].pop(0)
    return None


def start_dashboard(host="127.0.0.1", port=1337):
    if app is None:
        print(colored("  [!] Flask not installed. Run: pip install flask", "31"))
        return
    add_log(f"Dashboard starting on http://{host}:{port}", "ok")
    print(colored(f"\n  [Dashboard] http://{host}:{port}", "32"))
    app.run(host=host, port=port, debug=False, use_reloader=False)


def run_dashboard_thread(host="127.0.0.1", port=1337):
    t = threading.Thread(target=start_dashboard, args=(host, port), daemon=True)
    t.start()
    return t
