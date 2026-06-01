#!/usr/bin/env python3
"""landing.py - Landing proxy management with WARP failover (sing-box 1.14)"""
import json
import os
import shutil
import time

from . import system
from .config import load_config, save_config, load_sb_config, save_sb_config

SB_JSON = system.SB_CONFIG_FILE
WARP_BACKUP = SB_JSON + ".warp-on"


def check_socks5(server, port, username, password, timeout=5):
    """Test SOCKS5 proxy connectivity"""
    import socket
    import struct
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        sock.connect((server, int(port)))
        sock.send(b'\x05\x01\x02')
        resp = sock.recv(2)
        if len(resp) < 2 or resp[0] != 0x05:
            sock.close()
            return False
        if resp[1] == 0x02:
            un = username.encode()
            pw = password.encode()
            auth = b'\x01' + bytes([len(un)]) + un + bytes([len(pw)]) + pw
            sock.send(auth)
            auth_resp = sock.recv(2)
            if len(auth_resp) < 2 or auth_resp[1] != 0x00:
                sock.close()
                return False
        target_ip = socket.inet_aton(socket.gethostbyname('api.ipify.org'))
        connect = b'\x05\x01\x00\x01' + target_ip + struct.pack('>H', 443)
        sock.send(connect)
        connect_resp = sock.recv(10)
        sock.close()
        return len(connect_resp) >= 2 and connect_resp[1] == 0x00
    except Exception:
        return False


def check_warp(timeout=5):
    """Test WARP connectivity"""
    try:
        out, rc = system.run(
            "ping -c 1 -W {} engage.cloudflareclient.com".format(timeout))
        return rc == 0
    except Exception:
        return False


def get_landing_config():
    """Get landing proxy config from config.json"""
    config = load_config()
    return config.get("landing", {})


def save_landing_config(landing):
    """Save landing proxy config to config.json"""
    config = load_config()
    config["landing"] = landing
    save_config(config)


def build_sb_json():
    """Build complete sb.json with landing proxy + WARP failover"""
    config = load_config()
    landing = config.get("landing", {})

    sb = load_sb_config()
    if not sb:
        return False, "No sb.json found"

    # ── Outbounds ──
    outbounds = []
    tags = []

    # socks-out (landing proxy)
    if landing.get("enabled") and landing.get("server"):
        socks_out = {
            "type": "socks",
            "tag": "socks-out",
            "server": landing["server"],
            "server_port": int(landing.get("port", 443)),
            "username": landing.get("username", ""),
            "password": landing.get("password", ""),
            "version": "5"
        }
        outbounds.append(socks_out)
        tags.append("socks-out")

    # warp-out goes in endpoints (sing-box 1.14 WireGuard format)
    if os.path.isfile(WARP_BACKUP):
        with open(WARP_BACKUP) as f:
            warp_sb = json.load(f)
        for ep in warp_sb.get("endpoints", []):
            if ep.get("tag") == "warp-out":
                warp_ep = {k: v for k, v in ep.items()
                           if k not in ("system", "mtu", "domain_resolver")}
                sb["endpoints"] = [warp_ep]
                tags.append("warp-out")
                break
        if "dns" not in sb or not sb["dns"]:
            sb["dns"] = warp_sb.get("dns", {})

    # urltest group
    if len(tags) >= 2:
        group = {
            "type": "urltest",
            "tag": "proxy-group",
            "outbounds": tags,
            "url": "https://www.gstatic.com/generate_204",
            "interval": "3m",
            "tolerance": 200
        }
        outbounds.insert(0, group)

    outbounds.append({"type": "direct", "tag": "direct"})
    outbounds.append({"type": "block", "tag": "block"})
    sb["outbounds"] = outbounds

    # ── Route ──
    main_out = "proxy-group" if len(tags) >= 2 else (tags[0] if tags else "direct")

    google_suffixes = [
        "aistudio.google.com", "datacommons.org", "doubleclick.net",
        "gemini.google.com", "ggpht.com", "gmail.com",
        "google.ca", "google.co.jp", "google.co.kr", "google.co.uk",
        "google.com", "google.com.au", "google.com.br", "google.de",
        "google.fr", "googleadservices.com", "googleapis.com",
        "googletagmanager.com", "googleusercontent.com", "googlevideo.com",
        "gstatic.com", "makersuite.google.com", "withgoogle.com",
        "youtube.com", "ytimg.com"
    ]

    rules = [
        {"action": "sniff"},
        {"protocol": "dns", "action": "hijack-dns"},
    ]

    for rule in sb.get("route", {}).get("rules", []):
        if "action" in rule:
            continue
        doms = rule.get("domain_suffix", [])
        if doms:
            is_google = all(d in google_suffixes for d in doms)
            rule["outbound"] = "direct" if is_google else main_out
            rules.append(rule)
        elif rule.get("protocol"):
            rule["outbound"] = main_out
            rules.append(rule)
        elif rule.get("network"):
            rule["outbound"] = main_out
            rules.append(rule)

    sb["route"]["rules"] = rules
    sb["route"]["final"] = main_out

    if "dns" not in sb or not sb["dns"]:
        sb["dns"] = {
            "servers": [{"tag": "cloudflare", "type": "udp", "server": "1.1.1.1"}],
            "final": "cloudflare",
            "timeout": "3s",
            "optimistic": True
        }

    sb.setdefault("experimental", {})
    sb["experimental"].setdefault("clash_api", {"external_controller": "127.0.0.1:9090"})
    sb["experimental"].setdefault("cache_file", {
        "enabled": True, "store_dns": True,
        "path": "/etc/s-box-sn/cache.db"
    })

    save_sb_config(sb)
    return True, "Config built (primary={}, fallback={})".format(
        tags[0] if tags else "direct",
        tags[1] if len(tags) > 1 else "none"
    )


def get_status():
    """Get landing proxy + WARP status"""
    landing = get_landing_config()
    result = {
        "landing_enabled": landing.get("enabled", False),
        "landing_server": landing.get("server", ""),
        "landing_port": landing.get("port", 0),
        "landing_user": landing.get("username", ""),
        "landing_ok": False,
        "warp_ok": False,
        "active_outbound": "direct"
    }

    if landing.get("enabled") and landing.get("server"):
        result["landing_ok"] = check_socks5(
            landing["server"], landing.get("port", 443),
            landing.get("username", ""), landing.get("password", ""))

    result["warp_ok"] = check_warp()

    sb = load_sb_config()
    if sb:
        result["active_outbound"] = sb.get("route", {}).get("final", "direct")

    return result
