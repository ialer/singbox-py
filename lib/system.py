#!/usr/bin/env python3
"""system.py - System utilities"""
import os
import platform
import random
import secrets
import shlex
import socket
import subprocess
import time

BASE_DIR = "/etc/s-box-sn"
CONFIG_FILE = os.path.join(BASE_DIR, "config.json")
SB_CONFIG_FILE = os.path.join(BASE_DIR, "sb.json")
USERS_FILE = os.path.join(BASE_DIR, "users.json")
CERT_FILE = os.path.join(BASE_DIR, "cert.crt")
KEY_FILE = os.path.join(BASE_DIR, "private.key")
INFO_FILE = os.path.join(BASE_DIR, "info.txt")
OUTPUT_DIR = os.path.join(BASE_DIR, "output")

def run(cmd, check=False, timeout=30, cwd=None):
    """Run a shell command. Returns (stdout, returncode).
    Uses shlex.split to avoid shell injection. Pass string commands."""
    try:
        if isinstance(cmd, str):
            args = shlex.split(cmd)
        else:
            args = cmd
        r = subprocess.run(
            args, capture_output=True, text=True,
            timeout=timeout, cwd=cwd
        )
        if check and r.returncode != 0:
            err = r.stderr.strip() if r.stderr else ""
            raise RuntimeError(f"Command failed ({r.returncode}): {err or r.stdout.strip()}")
        return r.stdout.strip(), r.returncode
    except subprocess.TimeoutExpired:
        return f"Timeout after {timeout}s", -1
    except FileNotFoundError as e:
        return f"Command not found: {e}", -1
    except Exception as e:
        return str(e), -1

def run_raw(cmd, timeout=30, cwd=None):
    """Run a command that needs shell features (pipes, &&).
    Use sparingly — prefer run() with list args."""
    try:
        r = subprocess.run(
            cmd, shell=True, capture_output=True, text=True,
            timeout=timeout, cwd=cwd
        )
        return r.stdout.strip(), r.returncode
    except subprocess.TimeoutExpired:
        return f"Timeout after {timeout}s", -1
    except Exception as e:
        return str(e), -1

def get_ipv4():
    for u in ["https://api.ipify.org", "https://ifconfig.me/ip"]:
        out, rc = run(f"curl -s --max-time 5 {u}", timeout=10)
        if rc == 0 and out and all(p.isdigit() for p in out.strip().split(".")):
            return out.strip()
    try:
        return socket.gethostbyname(socket.gethostname())
    except Exception:
        return ""

def get_ipv6():
    out, rc = run("curl -s --max-time 5 -6 https://api6.ipify.org", timeout=10)
    if rc == 0 and out and ":" in out:
        return out.strip()
    return ""

def get_hostname():
    out, _ = run("hostname")
    return out

def get_bbr_status():
    out, _ = run("sysctl -n net.ipv4.tcp_congestion_control")
    return out

def get_arch():
    """Detect system architecture for binary downloads."""
    m = platform.machine()
    if m in ("x86_64", "amd64"):
        return "amd64"
    elif m in ("aarch64", "arm64"):
        return "arm64"
    elif m.startswith("armv7"):
        return "armv7"
    return m

def random_available_port(ex=None):
    excluded = ex or set()
    candidates = list(set(range(10000, 65000)) - excluded)
    random.shuffle(candidates)
    for p in candidates[:20]:
        out, rc = run(f"ss -tlnH sport = :{p}")
        if rc == 0 and not out:
            return p
    return random.choice(candidates)

def ensure_dirs():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

def backup_config(tag="auto"):
    ts = int(time.time())
    for f in [CONFIG_FILE, USERS_FILE, SB_CONFIG_FILE]:
        if os.path.isfile(f):
            run(f"cp {f} {f}.{ts}")
    return ts
