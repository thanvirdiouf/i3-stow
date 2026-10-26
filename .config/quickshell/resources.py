#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Stream Linux resource snapshots as JSON lines; no external Python packages."""
import csv
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
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


def read_number(path):
    try:
        value = float(path.read_text().strip())
        return value if math.isfinite(value) and value >= 0 else None
    except (OSError, ValueError):
        return None


def temperatures(hwmon_root=Path("/sys/class/hwmon")):
    readings = {"cpu": [], "gpu": [], "storage": [], "chipset": []}
    for device in hwmon_root.glob("hwmon*"):
        try:
            name = (device / "name").read_text().strip()
        except OSError:
            continue
        if name in {"coretemp", "k10temp", "zenpower", "cpu_thermal"}:
            category = "cpu"
        elif name in {"amdgpu", "nouveau", "i915", "xe"}:
            category = "gpu"
        elif name in {"nvme", "drivetemp"}:
            category = "storage"
        elif name.startswith("pch_"):
            category = "chipset"
        else:
            continue
        sensors = list(device.glob("temp*_input"))
        # NVMe's Composite temperature represents the drive; avoid substituting
        # unrelated vendor-specific sensor temperatures when it is available.
        if name == "nvme":
            composite = []
            for sensor in sensors:
                try:
                    if sensor.with_name(sensor.name.replace("_input", "_label")).read_text().strip() == "Composite":
                        composite.append(sensor)
                except OSError:
                    pass
            if composite:
                sensors = composite
        for sensor in sensors:
            value = read_number(sensor)
            if value is not None and 0 < value < 150000:
                readings[category].append(value / 1000)
    return {name: max(values) if values else None for name, values in readings.items()}


def temperature():
    return temperatures()["cpu"]


def gpu_number(value, maximum=None):
    try:
        number = float(value.strip())
        if not math.isfinite(number) or number < 0 or (maximum is not None and number > maximum):
            return None
        return number
    except (ValueError, AttributeError):
        return None


def parse_nvidia_gpus(output):
    gpus = []
    for row in csv.reader(output.splitlines(), skipinitialspace=True):
        if len(row) != 6:
            continue
        bus, name, usage, used, total, temp = [field.strip() for field in row]
        if not bus or not name:
            continue
        used, total = gpu_number(used), gpu_number(total)
        gpus.append({"id": bus, "name": name, "utilization": gpu_number(usage, 100),
                     "memoryUsed": used * 1024**2 if used is not None else None,
                     "memoryTotal": total * 1024**2 if total is not None else None,
                     "temperature": gpu_number(temp, 150)})
    return gpus


def gpu_stats(drm_root=Path("/sys/class/drm")):
    gpus = []
    if shutil.which("nvidia-smi"):
        try:
            result = subprocess.run(
                ["nvidia-smi", "--query-gpu=pci.bus_id,name,utilization.gpu,memory.used,memory.total,temperature.gpu",
                 "--format=csv,noheader,nounits"], capture_output=True, text=True, timeout=1, check=True)
            gpus.extend(parse_nvidia_gpus(result.stdout))
        except (OSError, subprocess.SubprocessError):
            # A sleeping GPU, absent driver, or unsupported field must not stop
            # the rest of the monitor or manufacture a zero-utilization sample.
            pass
    for card in sorted(drm_root.glob("card[0-9]*")):
        if not card.name[4:].isdigit():
            continue
        device = card / "device"
        try:
            if (device / "vendor").read_text().strip() != "0x1002":
                continue
        except OSError:
            continue
        usage = read_number(device / "gpu_busy_percent")
        used = read_number(device / "mem_info_vram_used")
        total = read_number(device / "mem_info_vram_total")
        name = "AMD GPU"
        try:
            name = (device / "product_name").read_text().strip() or name
        except OSError:
            pass
        sensors = [read_number(path) for path in device.glob("hwmon/hwmon*/temp1_input")]
        sensors = [v / 1000 for v in sensors if v is not None and 0 < v < 150000]
        gpus.append({"id": str(device.resolve()), "name": name,
                     "utilization": usage if usage is not None and usage <= 100 else None,
                     "memoryUsed": used, "memoryTotal": total,
                     "temperature": max(sensors) if sensors else None})
    return gpus


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
        thermal = temperatures()
        gpus = gpu_stats()
        gpu_temps = [gpu["temperature"] for gpu in gpus if gpu["temperature"] is not None]
        if thermal["gpu"] is not None:
            gpu_temps.append(thermal["gpu"])
        thermal["gpu"] = max(gpu_temps) if gpu_temps else None
        snapshot = {"cpu": round(usage, 1), "cores": os.cpu_count(), "memory": memory(),
                    "disk": {"used": disk.used, "total": disk.total, "percent": 100 * disk.used / disk.total},
                    "rx": rx, "tx": tx, "interfaces": sorted(net), "temperature": thermal["cpu"],
                    "temperatures": thermal, "gpus": gpus,
                    "uptime": float(Path("/proc/uptime").read_text().split()[0]),
                    "load": os.getloadavg()[0], "processes": rows}
        print(json.dumps(snapshot), flush=True)
        previous_cpu, previous_net, previous_time = cpu, net, now
        time.sleep(max(0.1, interval - (time.monotonic() - now)))


if __name__ == "__main__":
    try:
        stream()
    except (BrokenPipeError, KeyboardInterrupt):
        pass
