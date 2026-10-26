#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Stream Linux resource snapshots as JSON lines; no external Python packages."""
import json
import os
from pathlib import Path
import shutil
import time


def cpu_times():
    values = [int(v) for v in Path("/proc/stat").read_text().splitlines()[0].split()[1:9]]
    return sum(values), values[3] + values[4]


def memory():
    values = {line.split(":")[0]: int(line.split()[1]) * 1024
              for line in Path("/proc/meminfo").read_text().splitlines()}
    total = values["MemTotal"]
    available = values.get("MemAvailable", values.get("MemFree", 0))
    return {"total": total, "used": total - available,
            "percent": 100 * (total - available) / total,
            "swapTotal": values["SwapTotal"],
            "swapUsed": values["SwapTotal"] - values["SwapFree"]}


def network():
    result = {}
    for line in Path("/proc/net/dev").read_text().splitlines()[2:]:
        name, raw = line.split(":", 1)
        if name.strip() == "lo":
            continue
        values = raw.split()
        result[name.strip()] = (int(values[0]), int(values[8]))
    return result


def temperature():
    readings = []
    for device in Path("/sys/class/hwmon").glob("hwmon*"):
        try:
            if (device / "name").read_text().strip() not in {"coretemp", "k10temp", "zenpower", "cpu_thermal"}:
                continue
            for sensor in device.glob("temp*_input"):
                value = float(sensor.read_text()) / 1000
                if 0 < value < 150:
                    readings.append(value)
        except (OSError, ValueError):
            continue
    return max(readings) if readings else None


def processes(previous, elapsed):
    current, rows = {}, []
    ticks = os.sysconf("SC_CLK_TCK")
    page_size = os.sysconf("SC_PAGE_SIZE")
    for path in Path("/proc").iterdir():
        if not path.name.isdecimal():
            continue
        try:
            raw = (path / "stat").read_text()
            fields = raw[raw.rfind(")") + 2:].split()
            # Include start time in the key, so reused PIDs never inherit CPU time.
            key = (path.name, fields[19])
            used = int(fields[11]) + int(fields[12])
            current[key] = used
            cpu = max(0, used - previous.get(key, used)) / ticks / elapsed * 100
            rows.append({"pid": int(path.name), "name": raw[raw.find("(") + 1:raw.rfind(")")],
                         "cpu": round(cpu, 1), "memory": int(fields[21]) * page_size})
        except (OSError, ValueError, IndexError):
            continue
    rows.sort(key=lambda row: (row["cpu"], row["memory"]), reverse=True)
    return current, rows[:7]


def stream(interval=2):
    previous_cpu, previous_net, previous_processes = cpu_times(), network(), {}
    previous_time = time.monotonic()
    while True:
        now = time.monotonic()
        elapsed = max(now - previous_time, 0.001)
        cpu, net = cpu_times(), network()
        total_delta = cpu[0] - previous_cpu[0]
        usage = max(0, min(100, 100 * (1 - (cpu[1] - previous_cpu[1]) / total_delta))) if total_delta > 0 else 0
        rx = tx = 0
        for name, values in net.items():
            before = previous_net.get(name, values)
            rx += max(0, values[0] - before[0]) / elapsed
            tx += max(0, values[1] - before[1]) / elapsed
        previous_processes, rows = processes(previous_processes, elapsed)
        disk = shutil.disk_usage("/")
        snapshot = {"cpu": round(usage, 1), "cores": os.cpu_count(), "memory": memory(),
                    "disk": {"used": disk.used, "total": disk.total, "percent": 100 * disk.used / disk.total},
                    "rx": rx, "tx": tx, "interfaces": sorted(net), "temperature": temperature(),
                    "uptime": float(Path("/proc/uptime").read_text().split()[0]),
                    "load": os.getloadavg()[0], "processes": rows}
        print(json.dumps(snapshot), flush=True)
        previous_cpu, previous_net, previous_time = cpu, net, now
        time.sleep(interval)


if __name__ == "__main__":
    try:
        stream()
    except (BrokenPipeError, KeyboardInterrupt):
        pass
