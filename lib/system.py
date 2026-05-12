#!/usr/bin/env python3
"""system.py - System utilities"""
import os,socket,subprocess,random
BASE_DIR="/etc/s-box-sn"
CONFIG_FILE=os.path.join(BASE_DIR,"config.json")
SB_CONFIG_FILE=os.path.join(BASE_DIR,"sb.json")
USERS_FILE=os.path.join(BASE_DIR,"users.json")
CERT_FILE=os.path.join(BASE_DIR,"cert.crt")
KEY_FILE=os.path.join(BASE_DIR,"private.key")
INFO_FILE=os.path.join(BASE_DIR,"info.txt")
OUTPUT_DIR=os.path.join(BASE_DIR,"output")
def run(cmd,check=False,timeout=30):
    try:
        r=subprocess.run(cmd,shell=True,capture_output=True,text=True,timeout=timeout)
        return r.stdout.strip(),r.returncode
    except: return "",-1
def get_ipv4():
    for u in ["https://api.ipify.org","https://ifconfig.me/ip"]:
        out,rc=run(f"curl -s --max-time 5 {u}",timeout=10)
        if rc==0 and out and all(p.isdigit() for p in out.strip().split(".")): return out.strip()
    try: return socket.gethostbyname(socket.gethostname())
    except: return ""
def get_ipv6():
    out,rc=run("curl -s --max-time 5 -6 https://api6.ipify.org",timeout=10)
    if rc==0 and out and ":" in out: return out.strip()
    return ""
def get_hostname(): out,_=run("hostname"); return out
def get_bbr_status(): out,_=run("sysctl -n net.ipv4.tcp_congestion_control"); return out
def random_available_port(ex=None):
    ex=ex or set(); c=list(set(range(10000,65000))-ex); random.shuffle(c)
    for p in c[:20]:
        out,rc=run(f"ss -tlnH sport = :{p}")
        if rc==0 and not out: return p
    return random.choice(c)
def ensure_dirs(): os.makedirs(OUTPUT_DIR,exist_ok=True)
def backup_config(tag="auto"):
    import time; ts=int(time.time())
    for f in [CONFIG_FILE,USERS_FILE,SB_CONFIG_FILE]:
        if os.path.isfile(f): run(f"cp {f} {f}.{ts}")
    return ts
