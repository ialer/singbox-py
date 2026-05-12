#!/usr/bin/env python3
"""service.py - systemd service management"""
import time
from .system import run
SERVICE="sing-box.service"
def start(): run(f"systemctl start {SERVICE}"); time.sleep(1); return is_running()
def stop(): run(f"systemctl stop {SERVICE}"); time.sleep(1)
def restart(): run(f"systemctl restart {SERVICE}"); time.sleep(2); return is_running()
def is_running():
    out,_=run(f"systemctl is-active {SERVICE}"); return out=="active"
def status():
    a=is_running(); pid=""; mem=""; up=""
    if a:
        out,_=run(f"systemctl show {SERVICE} --property=MainPID")
        pid=out.split("=")[-1].strip() if "=" in out else ""
        out,_=run(f"systemctl show {SERVICE} --property=ActiveEnterTimestamp")
        up=out.split("=",1)[-1].strip() if "=" in out else ""
        if pid and pid!="0":
            out,_=run(f"ps -o rss= -p {pid}")
            if out:
                try: mem=f"{int(out.strip())/1024:.1f} MB"
                except: pass
    return {"active":a,"status_text":"Running" if a else "Stopped","pid":pid,"memory":mem,"uptime":up}
def logs(n=50):
    out,_=run(f"journalctl -u {SERVICE} -n {n} --no-pager"); return out
