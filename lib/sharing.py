#!/usr/bin/env python3
"""sharing.py - Share link generation with Clash support"""
import base64

def gen_vless_link(config,user,pc):
    port=pc["port"]; sni=pc.get("sni","apple.com"); uuid=user["uuid"]
    domain=config.get("domain",config.get("server_ip",""))
    pbk=config["public_key"]; sid=config["short_id"]
    params="encryption=none&flow=xtls-rprx-vision&security=reality&sni={}&fp=chrome&pbk={}&sid={}&type=tcp&headerType=none".format(sni,pbk,sid)
    name="vl-reality-"+config.get("hostname","node")
    return "vless://{}@{}:{}?{}#{}".format(uuid,domain,port,params,name)

def gen_anytls_link(config,user,pc):
    port=pc["port"]; pw=user.get("password",user["uuid"])
    domain=config.get("domain",config.get("server_ip","node"))
    params="sni={}&allowInsecure=1".format(domain)
    label=domain.split(".")[0] if "." in domain else domain
    return "anytls://{}@{}:{}?{}#anytls-{}".format(pw,domain,port,params,label)

def gen_all_links(config,user):
    links=[]; protos=config.get("protocols",{})
    vr=protos.get("vless_reality",{})
    if vr.get("enabled") and vr.get("port"): links.append(("VLESS-Reality",gen_vless_link(config,user,vr)))
    at=protos.get("anytls",{})
    if at.get("enabled") and at.get("port"): links.append(("AnyTLS",gen_anytls_link(config,user,at)))
    return links

def generate_subscription(links):
    text="\n".join(lk for _,lk in links)
    return base64.b64encode(text.encode()).decode()

def generate_clash_config(config, user):
    """Generate full Clash/Mihomo YAML config"""
    domain = config.get("domain", "")
    protos = config.get("protocols", {})
    vr = protos.get("vless_reality", {})
    at = protos.get("anytls", {})
    
    proxies = []
    
    # VLESS-Reality proxy
    if vr.get("enabled") and vr.get("port"):
        proxies.append({
            "name": "vl-reality-" + config.get("hostname", "node"),
            "type": "vless",
            "server": domain,
            "port": vr["port"],
            "uuid": user["uuid"],
            "network": "tcp",
            "tls": True,
            "udp": True,
            "flow": "xtls-rprx-vision",
            "servername": vr.get("sni", "apple.com"),
            "client-fingerprint": "chrome",
            "reality-opts": {
                "public-key": config["public_key"],
                "short-id": config["short_id"]
            }
        })
    
    # AnyTLS proxy
    if at.get("enabled") and at.get("port"):
        proxies.append({
            "name": "anytls-" + domain.split(".")[0],
            "type": "anytls",
            "server": domain,
            "port": at["port"],
            "password": user.get("password", user["uuid"]),
            "tls": True,
            "udp": True,
            "sni": domain,
            "skip-cert-verify": True
        })
    
    if not proxies:
        return None
    
    proxy_names = [p["name"] for p in proxies]
    
    config_yaml = {
        "mixed-port": 7890,
        "allow-lan": False,
        "mode": "rule",
        "log-level": "info",
        "proxies": proxies,
        "proxy-groups": [
            {
                "name": "PROXY",
                "type": "select",
                "proxies": proxy_names + ["DIRECT"]
            }
        ],
        "rules": [
            "GEOIP,LAN,DIRECT,no-resolve",
            "DOMAIN-SUFFIX,snbar.top,DIRECT",
            "GEOIP,CN,DIRECT",
            "MATCH,PROXY"
        ]
    }
    
    # Convert to YAML manually (avoid pyyaml dependency)
    lines = []
    lines.append("port: 7890")
    lines.append("socks-port: 7891")
    lines.append("allow-lan: false")
    lines.append("mode: rule")
    lines.append("log-level: info")
    lines.append("")
    lines.append("proxies:")
    for p in proxies:
        lines.append("  - name: " + p["name"])
        lines.append("    type: " + p["type"])
        lines.append("    server: " + p["server"])
        lines.append("    port: " + str(p["port"]))
        if p["type"] == "vless":
            lines.append("    uuid: " + p["uuid"])
            lines.append("    network: tcp")
            lines.append("    tls: true")
            lines.append("    udp: true")
            lines.append("    flow: xtls-rprx-vision")
            lines.append("    servername: " + p["servername"])
            lines.append("    client-fingerprint: " + p["client-fingerprint"])
            lines.append("    reality-opts:")
            lines.append("      public-key: " + p["reality-opts"]["public-key"])
            lines.append("      short-id: " + p["reality-opts"]["short-id"])
        elif p["type"] == "anytls":
            lines.append("    password: " + p["password"])
            lines.append("    tls: true")
            lines.append("    udp: true")
            lines.append("    sni: " + p["sni"])
            lines.append("    skip-cert-verify: true")
        lines.append("")
    
    lines.append("proxy-groups:")
    lines.append("  - name: PROXY")
    lines.append("    type: select")
    lines.append("    proxies:")
    for name in proxy_names:
        lines.append("      - " + name)
    lines.append("      - DIRECT")
    lines.append("")
    lines.append("rules:")
    lines.append("  - GEOIP,LAN,DIRECT,no-resolve")
    lines.append("  - DOMAIN-SUFFIX,snbar.top,DIRECT")
    lines.append("  - GEOIP,CN,DIRECT")
    lines.append("  - MATCH,PROXY")
    
    return "\n".join(lines)
