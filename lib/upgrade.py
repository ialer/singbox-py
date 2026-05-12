#!/usr/bin/env python3
"""upgrade.py - sing-box upgrade"""
import os
from .system import run
def get_current_version():
    out,rc=run("/etc/s-box-sn/sing-box version")
    if rc==0 and out:
        for l in out.split("\n"):
            if l.startswith("sing-box version"): return l.split()[-1]
    return None
def get_latest_version():
    out,rc=run("curl -s https://api.github.com/repos/SagerNet/sing-box/releases/latest | python3 -c \"import sys,json; print(json.load(sys.stdin).get(\\\'tag_name\\\',\\\'\\\')\\\\.lstrip(\\\'v\\\'))\"",timeout=15)
    if rc==0 and out: return out.strip()
    return None
def upgrade(ver=None):
    if not ver: ver=get_latest_version()
    if not ver: raise RuntimeError("Cannot get latest version")
    url="https://github.com/SagerNet/sing-box/releases/download/v{}/sing-box-{}-linux-amd64.tar.gz".format(ver,ver)
    out,rc=run("cd /tmp && curl -L -o sb-upgrade.tar.gz "+url,timeout=120)
    if rc!=0: raise RuntimeError("Download failed")
    out,rc=run("cd /tmp && tar xzf sb-upgrade.tar.gz",timeout=30)
    if rc!=0: raise RuntimeError("Extract failed")
    binary="/tmp/sing-box-{}-linux-amd64/sing-box".format(ver)
    if not os.path.isfile(binary): raise RuntimeError("Binary not found")
    run("systemctl stop sing-box.service"); run("cp /etc/s-box-sn/sing-box /etc/s-box-sn/sing-box.bak")
    run("cp {} /etc/s-box-sn/sing-box".format(binary)); run("chmod +x /etc/s-box-sn/sing-box")
    run("systemctl start sing-box.service"); run("rm -rf /tmp/sb-upgrade.tar.gz /tmp/sing-box-*")
    return get_current_version()
def check_python_version():
    out,_=run("python3 --version"); return out.strip() if out else None
