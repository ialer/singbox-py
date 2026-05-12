#!/usr/bin/env python3
"""config.py - Config management"""
import json,os
from .system import (CONFIG_FILE,SB_CONFIG_FILE,USERS_FILE,CERT_FILE,KEY_FILE,INFO_FILE,run)
def _strip_comments(text):
    r=[]; i=0; ins=False; esc=False
    while i<len(text):
        c=text[i]
        if esc: r.append(c); esc=False; i+=1; continue
        if c=="\\" and ins: r.append(c); esc=True; i+=1; continue
        if c=="\"" and not esc: ins=not ins; r.append(c); i+=1; continue
        if ins: r.append(c); i+=1; continue
        if c=="/" and i+1<len(text):
            nc=text[i+1]
            if nc=="/":
                while i<len(text) and text[i]!="\n": i+=1
                continue
            elif nc=="*":
                i+=2
                while i+1<len(text) and not (text[i]=="*" and text[i+1]=="/"): i+=1
                i+=2; continue
        r.append(c); i+=1
    return "".join(r)
def load_json(fp):
    if not os.path.isfile(fp): return None
    with open(fp) as f: return json.loads(_strip_comments(f.read()))
def save_json(fp,d,m=0o600):
    with open(fp,"w") as f: json.dump(d,f,indent=2,ensure_ascii=False)
    os.chmod(fp,m)
def load_config():
    d=load_json(CONFIG_FILE)
    if not d: d=_default(); save_config(d)
    return d
def save_config(d): save_json(CONFIG_FILE,d,0o600)
def load_sb_config(): return load_json(SB_CONFIG_FILE)
def save_sb_config(d): save_json(SB_CONFIG_FILE,d,0o644)
def load_users_data():
    d=load_json(USERS_FILE)
    if not d: d={"users":[]}
    return d
def save_users_data(d): save_json(USERS_FILE,d,0o600)
def load_info():
    info={}
    if not os.path.isfile(INFO_FILE): return info
    with open(INFO_FILE) as f:
        for l in f:
            l=l.strip()
            if "=" in l: k,v=l.split("=",1); info[k]=v
    return info
def save_info(info):
    with open(INFO_FILE,"w") as f:
        for k,v in info.items(): f.write(f"{k}={v}\n")
def _default():
    return {"version":"2.0.0","server_ip":"","server_ipv6":"","hostname":"","domain":"rack.snbar.top",
        "uuid":"","private_key":"","public_key":"","short_id":"",
        "protocols":{"vless_reality":{"enabled":True,"port":60379,"sni":"apple.com"},"anytls":{"enabled":True,"port":42119}},
        "certificates":{"type":"self-signed","cert_path":"/etc/s-box-sn/cert.crt","key_path":"/etc/s-box-sn/private.key"},
        "warp":{"enabled":False},"argo":{"enabled":False},"subscription":{"enabled":False,"port":0}}
def generate_reality_keypair():
    out,rc=run("/etc/s-box-sn/sing-box x25519")
    if rc!=0: raise RuntimeError("Failed: "+out)
    pk=sk=""
    for l in out.split("\n"):
        if "Private" in l: sk=l.split(":",1)[1].strip()
        elif "Public" in l: pk=l.split(":",1)[1].strip()
    return sk,pk
def generate_short_id():
    import secrets; return secrets.token_hex(4)
def generate_uuid():
    out,rc=run("/etc/s-box-sn/sing-box generate uuid")
    if rc==0 and out: return out.strip()
    import uuid; return str(uuid.uuid4())
