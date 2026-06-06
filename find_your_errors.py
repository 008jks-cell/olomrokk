#!/usr/bin/env python3
"""
=============================================================
  FIND YOUR ERRORS - Computer Diagnostic Tool
  Detects: System/OS errors, Disk issues, Network errors,
           and Running process issues
=============================================================
"""

import os
import sys
import platform
import shutil
import socket
import subprocess
import psutil
import datetime

# ─────────────────────────────────────────────
#  COLORS for terminal output
# ─────────────────────────────────────────────
class Color:
    RED     = "\033[91m"
    GREEN   = "\033[92m"
    YELLOW  = "\033[93m"
    CYAN    = "\033[96m"
    BOLD    = "\033[1m"
    RESET   = "\033[0m"

def header(title):
    print(f"\n{Color.BOLD}{Color.CYAN}{'='*55}{Color.RESET}")
    print(f"{Color.BOLD}{Color.CYAN}  {title}{Color.RESET}")
    print(f"{Color.BOLD}{Color.CYAN}{'='*55}{Color.RESET}")

def ok(msg):
    print(f"  {Color.GREEN}[OK]{Color.RESET}  {msg}")

def warn(msg):
    print(f"  {Color.YELLOW}[WARN]{Color.RESET} {msg}")

def error(msg):
    print(f"  {Color.RED}[ERROR]{Color.RESET} {msg}")

def info(msg):
    print(f"  {Color.CYAN}[INFO]{Color.RESET} {msg}")

# ─────────────────────────────────────────────
#  1. SYSTEM / OS ERRORS
# ─────────────────────────────────────────────
def check_system():
    header("1. SYSTEM / OS CHECKS")

    # Basic OS info
    info(f"OS        : {platform.system()} {platform.release()} ({platform.version()})")
    info(f"Machine   : {platform.machine()}")
    info(f"Hostname  : {socket.gethostname()}")
    info(f"Python    : {sys.version.split()[0]}")
    info(f"Date/Time : {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # Uptime
    boot_time = psutil.boot_time()
    uptime_seconds = (datetime.datetime.now() - datetime.datetime.fromtimestamp(boot_time)).total_seconds()
    uptime_hours = uptime_seconds / 3600
    if uptime_hours > 720:  # > 30 days
        warn(f"System uptime is very long ({uptime_hours:.0f} hours). Consider a restart.")
    else:
        ok(f"Uptime: {uptime_hours:.1f} hours")

    # CPU usage
    cpu_percent = psutil.cpu_percent(interval=1)
    if cpu_percent > 90:
        error(f"CPU usage critically high: {cpu_percent}%")
    elif cpu_percent > 70:
        warn(f"CPU usage is high: {cpu_percent}%")
    else:
        ok(f"CPU usage: {cpu_percent}%")

    # CPU temperature (if available)
    try:
        temps = psutil.sensors_temperatures()
        if temps:
            for name, entries in temps.items():
                for entry in entries:
                    if entry.current > 90:
                        error(f"High temperature on {name}: {entry.current}°C")
                    elif entry.current > 75:
                        warn(f"Elevated temperature on {name}: {entry.current}°C")
                    else:
                        ok(f"Temperature ({name}): {entry.current}°C")
    except AttributeError:
        info("Temperature sensors not available on this OS.")

    # RAM usage
    ram = psutil.virtual_memory()
    ram_used_pct = ram.percent
    if ram_used_pct > 90:
        error(f"RAM usage critically high: {ram_used_pct}% ({ram.used // (1024**2)} MB used / {ram.total // (1024**2)} MB total)")
    elif ram_used_pct > 75:
        warn(f"RAM usage is high: {ram_used_pct}%")
    else:
        ok(f"RAM usage: {ram_used_pct}% ({ram.used // (1024**2)} MB / {ram.total // (1024**2)} MB)")

    # Swap usage
    swap = psutil.swap_memory()
    if swap.total > 0:
        if swap.percent > 80:
            error(f"Swap usage very high: {swap.percent}%")
        elif swap.percent > 50:
            warn(f"Swap usage elevated: {swap.percent}%")
        else:
            ok(f"Swap usage: {swap.percent}%")
    else:
        info("No swap memory configured.")

# ─────────────────────────────────────────────
#  2. DISK & STORAGE ISSUES
# ─────────────────────────────────────────────
def check_disk():
    header("2. DISK & STORAGE CHECKS")

    partitions = psutil.disk_partitions()
    if not partitions:
        error("No disk partitions found!")
        return

    for part in partitions:
        try:
            usage = psutil.disk_usage(part.mountpoint)
            used_pct = usage.percent
            total_gb = usage.total / (1024**3)
            used_gb  = usage.used  / (1024**3)
            free_gb  = usage.free  / (1024**3)

            label = f"{part.device} ({part.mountpoint})"

            if used_pct > 95:
                error(f"DISK FULL: {label} — {used_pct}% used ({free_gb:.1f} GB free / {total_gb:.1f} GB total)")
            elif used_pct > 80:
                warn(f"Disk space low: {label} — {used_pct}% used ({free_gb:.1f} GB free)")
            else:
                ok(f"Disk: {label} — {used_pct}% used ({free_gb:.1f} GB free / {total_gb:.1f} GB total)")
        except PermissionError:
            warn(f"Cannot access partition: {part.mountpoint} (permission denied)")
        except Exception as e:
            warn(f"Skipping {part.mountpoint}: {e}")

    # Disk I/O errors (read/write counts)
    try:
        io = psutil.disk_io_counters()
        if io:
            info(f"Disk reads: {io.read_count:,} | Disk writes: {io.write_count:,}")
    except Exception:
        info("Disk I/O counters not available.")

# ─────────────────────────────────────────────
#  3. NETWORK ERRORS
# ─────────────────────────────────────────────
def check_network():
    header("3. NETWORK CHECKS")

    # Check internet connectivity
    test_hosts = [("8.8.8.8", 53, "Google DNS"), ("1.1.1.1", 53, "Cloudflare DNS")]
    internet_ok = False
    for host, port, name in test_hosts:
        try:
            socket.setdefaulttimeout(3)
            socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect((host, port))
            ok(f"Internet reachable via {name} ({host}:{port})")
            internet_ok = True
            break
        except Exception:
            warn(f"Cannot reach {name} ({host}:{port})")

    if not internet_ok:
        error("No internet connectivity detected!")

    # Network interfaces
    interfaces = psutil.net_if_stats()
    for iface, stats in interfaces.items():
        if stats.isup:
            ok(f"Interface UP: {iface} (speed: {stats.speed} Mbps)")
        else:
            warn(f"Interface DOWN: {iface}")

    # Network I/O counters
    net_io = psutil.net_io_counters()
    info(f"Bytes sent: {net_io.bytes_sent / (1024**2):.2f} MB | Bytes received: {net_io.bytes_recv / (1024**2):.2f} MB")
    if net_io.errin > 0:
        error(f"Network receive errors: {net_io.errin}")
    else:
        ok("No network receive errors.")
    if net_io.errout > 0:
        error(f"Network send errors: {net_io.errout}")
    else:
        ok("No network send errors.")
    if net_io.dropin > 0:
        warn(f"Packets dropped (in): {net_io.dropin}")
    if net_io.dropout > 0:
        warn(f"Packets dropped (out): {net_io.dropout}")

    # DNS resolution test
    try:
        socket.gethostbyname("www.google.com")
        ok("DNS resolution working (www.google.com resolved)")
    except socket.gaierror:
        error("DNS resolution failed! Cannot resolve hostnames.")

# ─────────────────────────────────────────────
#  4. RUNNING PROCESS ISSUES
# ─────────────────────────────────────────────
def check_processes():
    header("4. RUNNING PROCESS CHECKS")

    procs = list(psutil.process_iter(['pid', 'name', 'status', 'cpu_percent', 'memory_percent']))
    total = len(procs)
    info(f"Total running processes: {total}")

    if total > 300:
        warn(f"Large number of processes running ({total}). This might slow your system.")

    # Top CPU hogs
    print(f"\n  {Color.BOLD}Top 5 CPU-consuming processes:{Color.RESET}")
    try:
        # Sample CPU for 1 second for accurate readings
        for p in procs:
            try:
                p.cpu_percent(interval=None)
            except Exception:
                pass

        import time
        time.sleep(1)

        cpu_list = []
        for p in procs:
            try:
                cpu = p.cpu_percent(interval=None)
                cpu_list.append((cpu, p.info['pid'], p.info['name']))
            except Exception:
                pass

        cpu_list.sort(reverse=True)
        for cpu, pid, name in cpu_list[:5]:
            tag = error if cpu > 80 else (warn if cpu > 50 else ok)
            tag(f"  PID {pid:>6} | CPU: {cpu:>6.1f}% | {name}")
    except Exception as e:
        warn(f"Could not retrieve CPU process list: {e}")

    # Top Memory hogs
    print(f"\n  {Color.BOLD}Top 5 Memory-consuming processes:{Color.RESET}")
    try:
        mem_list = []
        for p in procs:
            try:
                mem = p.info['memory_percent']
                if mem is not None:
                    mem_list.append((mem, p.info['pid'], p.info['name']))
            except Exception:
                pass

        mem_list.sort(reverse=True)
        for mem, pid, name in mem_list[:5]:
            tag = error if mem > 20 else (warn if mem > 10 else ok)
            tag(f"  PID {pid:>6} | MEM: {mem:>6.1f}% | {name}")
    except Exception as e:
        warn(f"Could not retrieve memory process list: {e}")

    # Zombie / sleeping processes
    zombies = [p for p in procs if p.info.get('status') == psutil.STATUS_ZOMBIE]
    if zombies:
        for z in zombies:
            error(f"Zombie process found: PID {z.info['pid']} ({z.info['name']})")
    else:
        ok("No zombie processes found.")

# ─────────────────────────────────────────────
#  SUMMARY REPORT
# ─────────────────────────────────────────────
def summary(results):
    header("SUMMARY REPORT")
    total_errors   = results.count("ERROR")
    total_warnings = results.count("WARN")

    if total_errors > 0:
        print(f"  {Color.RED}{Color.BOLD}❌ {total_errors} ERROR(S) found — immediate attention needed!{Color.RESET}")
    if total_warnings > 0:
        print(f"  {Color.YELLOW}{Color.BOLD}⚠  {total_warnings} WARNING(S) found — review suggested.{Color.RESET}")
    if total_errors == 0 and total_warnings == 0:
        print(f"  {Color.GREEN}{Color.BOLD}✅ No errors or warnings! Your system looks healthy.{Color.RESET}")

    print(f"\n  Scan completed at: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{Color.CYAN}{'='*55}{Color.RESET}\n")

# ─────────────────────────────────────────────
#  MAIN
# ─────────────────────────────────────────────
def main():
    print(f"\n{Color.BOLD}{Color.CYAN}")
    print("  ███████╗██╗███╗   ██╗██████╗     ██╗   ██╗ ██████╗ ██╗   ██╗██████╗ ")
    print("  ██╔════╝██║████╗  ██║██╔══██╗    ╚██╗ ██╔╝██╔═══██╗██║   ██║██╔══██╗")
    print("  █████╗  ██║██╔██╗ ██║██║  ██║     ╚████╔╝ ██║   ██║██║   ██║██████╔╝")
    print("  ██╔══╝  ██║██║╚██╗██║██║  ██║      ╚██╔╝  ██║   ██║██║   ██║██╔══██╗")
    print("  ██║     ██║██║ ╚████║██████╔╝       ██║   ╚██████╔╝╚██████╔╝██║  ██║")
    print("  ╚═╝     ╚═╝╚═╝  ╚═══╝╚═════╝        ╚═╝    ╚═════╝  ╚═════╝ ╚═╝  ╚═╝")
    print(f"                                                         E R R O R S{Color.RESET}")
    print(f"\n  {Color.BOLD}Computer Diagnostic Tool{Color.RESET} — Scanning your system...\n")

    # Check psutil is installed
    try:
        import psutil
    except ImportError:
        print(f"{Color.RED}[ERROR] 'psutil' is not installed.{Color.RESET}")
        print("  Install it by running:  pip install psutil")
        sys.exit(1)

    import io
    import contextlib

    # Capture output to count errors/warnings in summary
    captured = io.StringIO()
    with contextlib.redirect_stdout(captured):
        check_system()
        check_disk()
        check_network()
        check_processes()

    output = captured.getvalue()
    print(output)

    summary(output)


if __name__ == "__main__":
    main()
