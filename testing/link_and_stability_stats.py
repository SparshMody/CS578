#!/usr/bin/env python3
"""
Wireless-link and reading-stability stats from server/logs/readings.csv.

    python3 link_and_stability_stats.py                       # whole log
    python3 link_and_stability_stats.py --since "2026-12-01 14:00:00" --until "2026-12-01 14:10:00"

Per bin it reports:
  * updates received, missed packets (sequence gaps) -> packet delivery ratio
  * mean / min / max RSSI
  * largest gap between updates (how long the dashboard would have been blind)
  * number of level changes and fill-% std-dev (stability test: bin left untouched
    should give 0 level changes)
Use --since/--until to isolate one test run (e.g. one distance in the Wi-Fi range test).
"""
import argparse
import csv
import os
import statistics
import time
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT = os.path.join(HERE, "..", "server", "logs", "readings.csv")


def ts(s):
    return time.mktime(time.strptime(s, "%Y-%m-%d %H:%M:%S"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("csv", nargs="?", default=DEFAULT)
    ap.add_argument("--since")
    ap.add_argument("--until")
    a = ap.parse_args()
    lo = ts(a.since) if a.since else 0
    hi = ts(a.until) if a.until else float("inf")

    bins = defaultdict(list)
    with open(a.csv, newline="") as f:
        for r in csv.DictReader(f):
            t = float(r["server_time"])
            if lo <= t <= hi:
                bins[r["bin_id"]].append(r)
    if not bins:
        raise SystemExit("No readings in that window.")

    for bid, rows in sorted(bins.items()):
        rows.sort(key=lambda r: float(r["server_time"]))
        seqs = [int(float(r["seq"])) for r in rows]
        missed = sum(max(0, b - a - 1) for a, b in zip(seqs, seqs[1:]) if b > a)
        rssi = [int(float(r["rssi"])) for r in rows if r["rssi"] not in ("", None)]
        times = [float(r["server_time"]) for r in rows]
        gaps = [b - a for a, b in zip(times, times[1:])]
        fills = [float(r["fill_pct"]) for r in rows]
        changes = sum(a["level"] != b["level"] for a, b in zip(rows, rows[1:]))
        sent = len(rows) + missed
        print(f"== {bid} ({rows[0]['location']}) ==")
        print(f"  window          : {time.strftime('%H:%M:%S', time.localtime(times[0]))} - "
              f"{time.strftime('%H:%M:%S', time.localtime(times[-1]))} ({times[-1]-times[0]:.0f} s)")
        print(f"  updates received: {len(rows)}   missed: {missed}   delivery ratio: {100*len(rows)/sent:.1f}%")
        if rssi:
            print(f"  RSSI dBm        : mean {statistics.mean(rssi):.1f}  min {min(rssi)}  max {max(rssi)}")
        if gaps:
            print(f"  update gap (s)  : mean {statistics.mean(gaps):.1f}  max {max(gaps):.1f}")
        print(f"  level changes   : {changes}   fill % std-dev: {statistics.pstdev(fills):.2f}")
        print()


if __name__ == "__main__":
    main()
