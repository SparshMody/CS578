#!/usr/bin/env python3
"""
Smart Trash Bin dashboard server (runs on the laptop).

Pure Python standard library - no pip installs needed.  Python 3.8+.

    python3 server.py              # listens on 0.0.0.0:8000
    python3 server.py --port 8080 --stale 20

Then open http://localhost:8000 in a browser.  The ESP32 must POST to
http://<this-laptop's-LAN-IP>:8000/api/update  (laptop and ESP32 on the same Wi-Fi).

Endpoints
  GET  /                 dashboard page
  GET  /api/bins         latest status of every bin (+ age / stale flag)
  GET  /api/history?bin_id=bin-1&n=120   recent readings for a chart
  POST /api/update       ESP32 sends a JSON status here
  POST /api/test_sample  record a test sample (ground truth vs. reported level)

Files written
  logs/readings.csv      every update received (for analysis / debugging)
  ../testing/results.csv every test sample recorded from the dashboard
"""
import argparse
import csv
import json
import os
import threading
import time
from collections import defaultdict, deque
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

HERE = os.path.dirname(os.path.abspath(__file__))
LOG_DIR = os.path.join(HERE, "logs")
READINGS_CSV = os.path.join(LOG_DIR, "readings.csv")
RESULTS_CSV = os.path.join(HERE, "..", "testing", "results.csv")
DASHBOARD = os.path.join(HERE, "dashboard.html")

READING_FIELDS = ["server_time", "bin_id", "location", "seq", "uptime_ms", "distance_cm",
                  "raw_median_cm", "fill_pct", "level", "empty_cm", "full_cm",
                  "valid_ratio", "rssi", "client_ip"]
RESULT_FIELDS = ["server_time", "bin_id", "trial", "arrangement", "true_level", "true_fill_pct",
                 "reported_level", "reported_fill_pct", "distance_cm", "valid_ratio",
                 "rssi", "notes"]

lock = threading.Lock()
latest = {}                                   # bin_id -> dict
history = defaultdict(lambda: deque(maxlen=600))
gaps = defaultdict(int)                       # bin_id -> missed sequence numbers
STALE_SECONDS = 20


def append_csv(path, fields, row):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    new = not os.path.exists(path)
    with open(path, "a", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        if new:
            w.writeheader()
        w.writerow(row)


def bin_view(b, now):
    age = now - b["server_time"]
    out = dict(b)
    out["age_s"] = round(age, 1)
    out["stale"] = age > STALE_SECONDS
    out["missed_packets"] = gaps[b["bin_id"]]
    out["last_update_iso"] = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(b["server_time"]))
    return out


class Handler(BaseHTTPRequestHandler):
    server_version = "SmartBin/1.0"

    def log_message(self, fmt, *args):  # quieter console
        pass

    def _send(self, code, body, ctype="application/json"):
        data = body if isinstance(body, bytes) else json.dumps(body).encode()
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def _json_body(self):
        n = int(self.headers.get("Content-Length", 0))
        return json.loads(self.rfile.read(n) or b"{}")

    # ---------- GET ----------
    def do_GET(self):
        url = urlparse(self.path)
        now = time.time()
        if url.path in ("/", "/index.html"):
            with open(DASHBOARD, "rb") as f:
                return self._send(200, f.read(), "text/html; charset=utf-8")
        if url.path == "/api/bins":
            with lock:
                bins = [bin_view(b, now) for b in latest.values()]
            bins.sort(key=lambda b: b["bin_id"])
            return self._send(200, {"server_time": now, "stale_after_s": STALE_SECONDS, "bins": bins})
        if url.path == "/api/history":
            q = parse_qs(url.query)
            bid = q.get("bin_id", [""])[0]
            n = int(q.get("n", ["120"])[0])
            with lock:
                h = list(history[bid])[-n:]
            return self._send(200, {"bin_id": bid, "points": h})
        self._send(404, {"error": "not found"})

    # ---------- POST ----------
    def do_POST(self):
        url = urlparse(self.path)
        try:
            body = self._json_body()
        except (ValueError, json.JSONDecodeError):
            return self._send(400, {"error": "bad json"})

        if url.path == "/api/update":
            bid = str(body.get("bin_id", "")).strip()
            if not bid:
                return self._send(400, {"error": "bin_id required"})
            body["server_time"] = time.time()
            body["client_ip"] = self.client_address[0]
            with lock:
                prev = latest.get(bid)
                if prev is not None and isinstance(body.get("seq"), int) and isinstance(prev.get("seq"), int):
                    if body["seq"] > prev["seq"] + 1:
                        gaps[bid] += body["seq"] - prev["seq"] - 1
                    elif body["seq"] < prev["seq"]:
                        gaps[bid] = 0  # device rebooted
                latest[bid] = body
                history[bid].append({"t": body["server_time"], "fill_pct": body.get("fill_pct"),
                                     "distance_cm": body.get("distance_cm"), "level": body.get("level")})
            append_csv(READINGS_CSV, READING_FIELDS, body)
            print(f"[{time.strftime('%H:%M:%S')}] {bid:10s} {body.get('level','?'):>5s} "
                  f"fill={body.get('fill_pct', 0):5.1f}%  d={body.get('distance_cm', 0):5.1f}cm  "
                  f"rssi={body.get('rssi', '?')}")
            return self._send(200, {"ok": True})

        if url.path == "/api/test_sample":
            bid = body.get("bin_id")
            with lock:
                b = latest.get(bid)
                if b is None:
                    return self._send(404, {"error": f"no data from {bid} yet"})
                age = time.time() - b["server_time"]
                b = dict(b)
            if age > STALE_SECONDS:
                return self._send(409, {"error": f"latest reading is stale ({age:.0f}s old) - not recorded"})
            row = {
                "server_time": time.strftime("%Y-%m-%d %H:%M:%S"),
                "bin_id": bid,
                "trial": body.get("trial", ""),
                "arrangement": body.get("arrangement", ""),
                "true_level": body.get("true_level", ""),
                "true_fill_pct": body.get("true_fill_pct", ""),
                "reported_level": b.get("level"),
                "reported_fill_pct": b.get("fill_pct"),
                "distance_cm": b.get("distance_cm"),
                "valid_ratio": b.get("valid_ratio"),
                "rssi": b.get("rssi"),
                "notes": body.get("notes", ""),
            }
            append_csv(RESULTS_CSV, RESULT_FIELDS, row)
            return self._send(200, {"ok": True, "recorded": row})

        self._send(404, {"error": "not found"})


def main():
    global STALE_SECONDS
    ap = argparse.ArgumentParser(description="Smart Trash Bin dashboard server")
    ap.add_argument("--host", default="0.0.0.0")
    ap.add_argument("--port", type=int, default=8000)
    ap.add_argument("--stale", type=int, default=20, help="seconds without data before a bin is flagged stale")
    a = ap.parse_args()
    STALE_SECONDS = a.stale
    srv = ThreadingHTTPServer((a.host, a.port), Handler)
    print(f"Dashboard:  http://localhost:{a.port}")
    print(f"ESP32 URL:  http://<this laptop's IP>:{a.port}/api/update   (stale after {STALE_SECONDS}s)")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\nbye")


if __name__ == "__main__":
    main()
