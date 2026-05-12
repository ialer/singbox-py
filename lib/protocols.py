#!/usr/bin/env python3
"""protocols.py - VLESS-Reality + AnyTLS config builder"""
from .config import load_config,load_users_data
def build_server_config(config,users):
    inbounds=[]; ul=users.get("users",[]); protos=config.get("protocols",{})
    vr=protos.get("vless_reality",{})
    if vr.get("enabled") and vr.get("port"):
        vu=[{"name":u["name"],"uuid":u["uuid"],"flow":"xtls-rprx-vision"} for u in ul]
        inbounds.append({"type":"vless","tag":"vless-in","listen":"::","listen_port":vr["port"],"users":vu,
            "tls":{"enabled":True,"server_name":vr.get("sni","apple.com"),
                "reality":{"enabled":True,"handshake":{"server":vr.get("sni","apple.com"),"server_port":443},
                    "private_key":config["private_key"],"short_id":[config["short_id"]]}}})
    at=protos.get("anytls",{})
    if at.get("enabled") and at.get("port"):
        au=[{"password":u.get("password",u["uuid"])} for u in ul]
        inbounds.append({"type":"anytls","tag":"anytls-in","listen":"::","listen_port":at["port"],"users":au,
            "tls":{"enabled":True,"certificate_path":config.get("certificates",{}).get("cert_path","/etc/s-box-sn/cert.crt"),
                "key_path":config.get("certificates",{}).get("key_path","/etc/s-box-sn/private.key")}})
    outbounds=[{"type":"direct","tag":"direct"},{"type":"block","tag":"block"}]
    warp=config.get("warp",{})
    rules=[{"action":"sniff"},{"protocol":["quic","stun"],"outbound":"block"}]
    if warp.get("enabled") and warp.get("rules",{}).get("domains"):
        rules.append({"outbound":"warp-out","domain_suffix":warp["rules"]["domains"]})
    rules.append({"outbound":"direct","network":"udp,tcp"})
    cfg={"log":{"disabled":False,"level":"warn","timestamp":True},"inbounds":inbounds,"outbounds":outbounds,"route":{"rules":rules}}
    if warp.get("enabled") and warp.get("private_key"):
        ipv6=warp.get("ipv6_address","") or "fd00::/128"
        if ":" in ipv6 and "/" not in ipv6: ipv6=ipv6+"/128"
        cfg["endpoints"]=[{"type":"wireguard","tag":"warp-out","system":False,"mtu":1280,
            "address":["172.16.0.2/32",ipv6],"private_key":warp["private_key"],
            "peers":[{"address":warp.get("endpoint","engage.cloudflareclient.com"),"port":2408,
                "public_key":"bmXOC+F1FxEMF9dyiK2H5/1SUtzH0JuVo51h2wPfgyo=",
                "allowed_ips":["0.0.0.0/0","::/0"],"reserved":warp.get("reserved",[0,0,0]),
                "persistent_keepalive_interval":25}]}]
    return cfg
def extract_from_sb_config(sb):
    e={}
    for ib in sb.get("inbounds",[]):
        if ib.get("type")=="vless" and ib.get("tag")=="vless-in":
            e["vless_port"]=ib.get("listen_port",0); us=ib.get("users",[])
            if us: e["uuid"]=us[0].get("uuid","")
            t=ib.get("tls",{}); r=t.get("reality",{})
            if r.get("private_key"): e["private_key"]=r["private_key"]
            if r.get("short_id"): s=r["short_id"]; e["short_id"]=s[0] if isinstance(s,list) else s
            e["sni"]=t.get("server_name","")
        elif ib.get("type")=="anytls" and ib.get("tag")=="anytls-in":
            e["anytls_port"]=ib.get("listen_port",0)
    for ep in sb.get("endpoints",[]):
        if ep.get("type")=="wireguard":
            e["warp_private_key"]=ep.get("private_key","")
            for a in ep.get("address",[]):
                if ":" in a and "/" in a: e["warp_ipv6"]=a.split("/")[0]
            ps=ep.get("peers",[])
            if ps: e["warp_reserved"]=ps[0].get("reserved",[0,0,0])
    return e
