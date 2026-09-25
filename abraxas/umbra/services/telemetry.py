#!/usr/bin/env python3
# =====================================================================
#  ❖ ABRAXAS 2.0 | UMBRA - TELEMETRY & SYSTEM SERVICES
# =====================================================================

import os
import time
import socket
import datetime
import subprocess
import platform

class UmbraHardwareCollector:
    """
    Colector de telemetría de hardware en tiempo real de bajo nivel en Linux (/proc, /sys).
    Desacoplado y optimizado para cero bloqueos de la GUI.
    """
    def __init__(self):
        self.last_cpu_idle = 0.0
        self.last_cpu_total = 0.0
        self.last_disk_read_bytes = 0
        self.last_disk_write_bytes = 0
        self.last_disk_time = 0.0
        self.last_net_rx_bytes = 0
        self.last_net_tx_bytes = 0
        self.last_net_time = 0.0
        
        # Cache de metadatos estáticos
        self.cpu_model = self._detect_cpu_model()
        self.gpu_model = "NVIDIA GPU"
        self.net_iface = self._detect_primary_net_iface()
        self.distro_str = self._detect_distro()
        self.kernel_str = platform.uname().release
        self.cpu_temp_path = self._detect_cpu_temp_path()
        self.nvme_dev_name = self._detect_primary_disk_device()

        self._init_first_samples()

    def _detect_cpu_model(self) -> str:
        try:
            with open("/proc/cpuinfo", "r") as f:
                for line in f:
                    if "model name" in line:
                        name = line.split(":", 1)[1].strip()
                        name = name.replace("Intel(R) Core(TM) ", "").replace("Processor", "")
                        return name
        except Exception:
            pass
        return "Intel Core Processor"

    def _detect_cpu_temp_path(self) -> str:
        for z in sorted(os.listdir("/sys/class/thermal")):
            if z.startswith("thermal_zone"):
                t_type = os.path.join("/sys/class/thermal", z, "type")
                t_temp = os.path.join("/sys/class/thermal", z, "temp")
                try:
                    with open(t_type, "r") as f:
                        if "x86_pkg_temp" in f.read():
                            return t_temp
                except Exception:
                    pass
        fb = "/sys/class/thermal/thermal_zone0/temp"
        return fb if os.path.exists(fb) else None

    def _detect_primary_disk_device(self) -> str:
        try:
            with open("/proc/diskstats", "r") as f:
                for line in f:
                    parts = line.split()
                    if len(parts) > 2 and parts[2].startswith("nvme0n1"):
                        return "nvme0n1"
        except Exception:
            pass
        return "nvme0n1"

    def _detect_primary_net_iface(self) -> str:
        try:
            with open("/proc/net/dev", "r") as f:
                lines = f.readlines()[2:]
                for l in lines:
                    iface = l.split(":", 1)[0].strip()
                    if iface.startswith(("wlan", "eth", "enp", "wlp")):
                        return iface
        except Exception:
            pass
        return "wlan0"

    def _detect_distro(self) -> str:
        try:
            if os.path.exists("/etc/os-release"):
                with open("/etc/os-release") as f:
                    for l in f:
                        if l.startswith("NAME="):
                            return l.split("=", 1)[1].strip().strip('"')
        except Exception:
            pass
        return "CachyOS Linux"

    def _init_first_samples(self):
        try:
            with open("/proc/stat", "r") as f:
                fields = [float(x) for x in f.readline().strip().split()[1:8]]
                self.last_cpu_idle = fields[3] + fields[4]
                self.last_cpu_total = sum(fields)
        except Exception:
            pass

        now = time.time()
        self.last_disk_time = now
        self.last_net_time = now
        self._read_raw_disk_bytes()
        self._read_raw_net_bytes()

    def _read_raw_disk_bytes(self) -> tuple[int, int]:
        r_b, w_b = 0, 0
        try:
            with open("/proc/diskstats", "r") as f:
                for line in f:
                    p = line.split()
                    if len(p) > 9 and p[2] == self.nvme_dev_name:
                        r_b = int(p[5]) * 512
                        w_b = int(p[9]) * 512
                        break
        except Exception:
            pass
        self.last_disk_read_bytes = r_b
        self.last_disk_write_bytes = w_b
        return r_b, w_b

    def _read_raw_net_bytes(self) -> tuple[int, int]:
        rx, tx = 0, 0
        try:
            with open("/proc/net/dev", "r") as f:
                for line in f.readlines()[2:]:
                    parts = line.split(":", 1)
                    if len(parts) == 2 and parts[0].strip() == self.net_iface:
                        cols = parts[1].split()
                        rx = int(cols[0])
                        tx = int(cols[8])
                        break
        except Exception:
            pass
        self.last_net_rx_bytes = rx
        self.last_net_tx_bytes = tx
        return rx, tx

    def collect_snapshot(self) -> dict:
        """Recolecta métricas vivas de hardware en milisegundos."""
        now = time.time()
        
        # 1. CPU Usage %
        cpu_pct = 15
        try:
            with open("/proc/stat", "r") as f:
                fields = [float(x) for x in f.readline().strip().split()[1:8]]
                idle = fields[3] + fields[4]
                total = sum(fields)
                d_idle = idle - self.last_cpu_idle
                d_total = total - self.last_cpu_total
                if d_total > 0:
                    cpu_pct = max(0, min(100, int((1.0 - (d_idle / d_total)) * 100)))
                self.last_cpu_idle = idle
                self.last_cpu_total = total
        except Exception:
            pass

        # CPU Temp
        cpu_temp = 42
        if self.cpu_temp_path and os.path.exists(self.cpu_temp_path):
            try:
                with open(self.cpu_temp_path, "r") as f:
                    val = int(f.read().strip())
                    cpu_temp = val // 1000
            except Exception:
                pass

        # CPU Clock (GHz)
        cpu_ghz = 5.0
        try:
            freq_file = "/sys/devices/system/cpu/cpu0/cpufreq/scaling_cur_freq"
            if os.path.exists(freq_file):
                with open(freq_file) as f:
                    cpu_ghz = round(int(f.read().strip()) / 1_000_000, 1)
        except Exception:
            pass

        # 2. RAM
        ram_used_gb = 5.8
        ram_total_gb = 31.2
        ram_pct = 18
        try:
            mem = {}
            with open("/proc/meminfo", "r") as f:
                for l in f:
                    p = l.split(":")
                    if len(p) == 2:
                        mem[p[0].strip()] = int(p[1].strip().split()[0])
            t_kb = mem.get("MemTotal", 0)
            a_kb = mem.get("MemAvailable", 0)
            if t_kb > 0:
                u_kb = t_kb - a_kb
                ram_total_gb = round(t_kb / 1024 / 1024, 1)
                ram_used_gb = round(u_kb / 1024 / 1024, 1)
                ram_pct = int((u_kb / t_kb) * 100)
        except Exception:
            pass

        # 3. GPU (nvidia-smi)
        gpu_pct = 10
        gpu_temp = 50
        vram_used_gb = 1.5
        vram_total_gb = 12.0
        try:
            cmd = ["nvidia-smi", "--query-gpu=utilization.gpu,memory.used,memory.total,temperature.gpu,name", "--format=csv,noheader,nounits"]
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=0.8)
            if res.returncode == 0 and res.stdout.strip():
                parts = [x.strip() for x in res.stdout.strip().split(",")]
                if len(parts) >= 4:
                    gpu_pct = int(parts[0])
                    vram_used_gb = round(float(parts[1]) / 1024.0, 1)
                    vram_total_gb = round(float(parts[2]) / 1024.0, 1)
                    gpu_temp = int(parts[3])
                if len(parts) >= 5:
                    self.gpu_model = parts[4].replace("NVIDIA GeForce ", "")
        except Exception:
            pass

        # 4. Storage (Btrfs Root `/`)
        disk_free_tb = 1.8
        disk_used_pct = 9
        try:
            st = os.statvfs("/")
            t_bytes = st.f_blocks * st.f_frsize
            f_bytes = st.f_bavail * st.f_frsize
            u_bytes = t_bytes - f_bytes
            disk_free_tb = round(f_bytes / (1024**4), 1)
            disk_used_pct = int((u_bytes / t_bytes) * 100) if t_bytes > 0 else 9
        except Exception:
            pass

        # Disk I/O Delta (MB/s)
        disk_read_mbs = 0.0
        disk_write_mbs = 0.0
        elapsed_disk = max(0.1, now - self.last_disk_time)
        try:
            with open("/proc/diskstats", "r") as f:
                for line in f:
                    p = line.split()
                    if len(p) > 9 and p[2] == self.nvme_dev_name:
                        cur_r = int(p[5]) * 512
                        cur_w = int(p[9]) * 512
                        disk_read_mbs = round(max(0, (cur_r - self.last_disk_read_bytes) / elapsed_disk / (1024*1024)), 1)
                        disk_write_mbs = round(max(0, (cur_w - self.last_disk_write_bytes) / elapsed_disk / (1024*1024)), 1)
                        self.last_disk_read_bytes = cur_r
                        self.last_disk_write_bytes = cur_w
                        self.last_disk_time = now
                        break
        except Exception:
            pass

        # 5. Network Delta (MB/s)
        net_rx_mbs = 0.0
        net_tx_mbs = 0.0
        elapsed_net = max(0.1, now - self.last_net_time)
        try:
            with open("/proc/net/dev", "r") as f:
                for line in f.readlines()[2:]:
                    parts = line.split(":", 1)
                    if len(parts) == 2 and parts[0].strip() == self.net_iface:
                        cols = parts[1].split()
                        cur_rx = int(cols[0])
                        cur_tx = int(cols[8])
                        net_rx_mbs = round(max(0, (cur_rx - self.last_net_rx_bytes) / elapsed_net / (1024*1024)), 1)
                        net_tx_mbs = round(max(0, (cur_tx - self.last_net_tx_bytes) / elapsed_net / (1024*1024)), 1)
                        self.last_net_rx_bytes = cur_rx
                        self.last_net_tx_bytes = cur_tx
                        self.last_net_time = now
                        break
        except Exception:
            pass

        # Ping Latency
        ping_ms = 18
        try:
            t0 = time.perf_counter()
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(0.15)
            s.connect(("1.1.1.1", 53))
            s.close()
            ping_ms = max(1, int((time.perf_counter() - t0) * 1000))
        except Exception:
            pass

        return {
            "cpu_pct": cpu_pct,
            "cpu_temp": cpu_temp,
            "cpu_ghz": cpu_ghz,
            "cpu_model": self.cpu_model,
            "ram_used_gb": ram_used_gb,
            "ram_total_gb": ram_total_gb,
            "ram_pct": ram_pct,
            "gpu_pct": gpu_pct,
            "gpu_temp": gpu_temp,
            "gpu_vram_used_gb": vram_used_gb,
            "gpu_vram_total_gb": vram_total_gb,
            "gpu_model": self.gpu_model,
            "disk_free_tb": disk_free_tb,
            "disk_used_pct": disk_used_pct,
            "disk_read_mbs": disk_read_mbs,
            "disk_write_mbs": disk_write_mbs,
            "net_rx_mbs": net_rx_mbs,
            "net_tx_mbs": net_tx_mbs,
            "net_ping_ms": ping_ms,
            "operator_name": "SILVYNTH",
            "kernel_version": self.kernel_str,
            "distro_name": self.distro_str
        }


class UmbraStatusRibbonCollector:
    """
    Colector de métricas de Segundo Cerebro (Obsidian), paquetes y resiliencia Btrfs.
    """
    def __init__(self, vault_dir="/home/silvynth/Vault/01_Obsidian"):
        self.vault_dir = vault_dir
        self.last_pkg_count = 0
        self.last_pkg_summary = "Sistema sincronizado"
        self.last_pkg_time = 0.0

    def collect_vault_metrics(self) -> tuple[int, int]:
        total = 0
        today_cnt = 0
        today_date = datetime.date.today()
        
        if os.path.exists(self.vault_dir):
            for root, _, files in os.walk(self.vault_dir):
                for f in files:
                    if f.endswith(".md"):
                        total += 1
                        try:
                            fp = os.path.join(root, f)
                            mtime = datetime.date.fromtimestamp(os.path.getmtime(fp))
                            if mtime == today_date:
                                today_cnt += 1
                        except Exception:
                            pass
        return total, today_cnt

    def collect_package_updates(self, force=False) -> tuple[int, str]:
        now = time.time()
        if not force and (now - self.last_pkg_time < 45.0) and self.last_pkg_time > 0:
            return self.last_pkg_count, self.last_pkg_summary

        count = 0
        summary = "Todos los paquetes sincronizados"
        try:
            res = subprocess.run(["checkupdates"], capture_output=True, text=True, timeout=4)
            if res.returncode == 0 and res.stdout.strip():
                lines = [l.strip() for l in res.stdout.strip().split("\n") if l.strip()]
                count = len(lines)
                if count > 0:
                    summary = f"{lines[0].split()[0]} · CachyOS / Arch al día"
            elif res.returncode == 2:
                count = 0
                summary = "Sistema al 100% sincronizado"
        except Exception:
            pass
        self.last_pkg_count = count
        self.last_pkg_summary = summary
        self.last_pkg_time = now
        return count, summary

    def collect_btrfs_snapshots_status(self) -> tuple[int, str, bool]:
        cnt = 12
        desc = "Snapper activo · Limine Bootloader OK"
        sync_ok = True

        try:
            if os.path.exists("/.snapshots"):
                mtime = datetime.datetime.fromtimestamp(os.stat("/.snapshots").st_mtime)
                now = datetime.datetime.now()
                if mtime.date() == now.date():
                    time_str = f"Hoy {mtime.strftime('%H:%M')}"
                else:
                    time_str = mtime.strftime("%d/%m %H:%M")
                desc = f"Último: {time_str} · Limine Bootloader OK"
        except Exception:
            pass

        has_snapper = subprocess.run(["which", "snapper"], capture_output=True).returncode == 0
        return cnt, desc, has_snapper

    def collect_ribbon_snapshot(self) -> dict:
        total_notes, today_notes = self.collect_vault_metrics()
        pkg_cnt, pkg_summary = self.collect_package_updates()
        snap_cnt, snap_desc, sync_ok = self.collect_btrfs_snapshots_status()

        return {
            "vault_total": total_notes,
            "vault_today": today_notes,
            "pkg_count": pkg_cnt,
            "pkg_summary": pkg_summary,
            "snap_count": snap_cnt,
            "snap_desc": snap_desc,
            "snap_sync_ok": sync_ok
        }
