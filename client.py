#!/usr/bin/env python3
"""
client.py — sing-box 客户端配置生成模块

从 sb.json 读取服务器配置，生成 sing-box 客户端 JSON 配置文件。
包含: TUN 入口 + mixed 代理入口、5 个协议 outbound、
selector/urltest 代理组、路由规则、DNS 配置。
纯 Python 标准库实现。
"""

import json
import os
import sys

from config import load_config, extract_config, get_public_ip, DEFAULT_SNI


def generate_client_config(config, ip=None):
    """
    生成完整的 sing-box 客户端配置 JSON。

    参数:
        config (dict): load_config() 返回的完整配置
        ip (str, optional): 公网 IP，为 None 时自动获取

    返回:
        dict: 客户端配置字典
    """
    if ip is None:
        ip = get_public_ip()

    extracted = extract_config(config)

    # ─── 构建 outbounds 列表 ───
    outbounds = []

    # VLess-Reality
    v = extracted.get('vless', {})
    if v:
        outbounds.append({
            "type": "vless",
            "tag": "VLess-Reality",
            "server": ip,
            "server_port": v['port'],
            "uuid": v['uuid'],
            "flow": v['flow'],
            "tls": {
                "enabled": True,
                "server_name": v['sni'],
                "utls": {
                    "enabled": True,
                    "fingerprint": "chrome",
                },
                "reality": {
                    "enabled": True,
                    "public_key": v['public_key'],
                    "short_id": v['short_id'],
                },
            },
        })

    # VMess-WS
    vm = extracted.get('vmess', {})
    if vm:
        outbounds.append({
            "type": "vmess",
            "tag": "VMess-WS",
            "server": ip,
            "server_port": vm['port'],
            "uuid": vm['uuid'],
            "security": "auto",
            "alter_id": 0,
            "tls": {
                "enabled": True,
                "server_name": vm['sni'],
                "insecure": True,
            },
            "transport": {
                "type": "ws",
                "path": vm['path'],
            },
        })

    # Hysteria2
    hy = extracted.get('hysteria2', {})
    if hy:
        outbounds.append({
            "type": "hysteria2",
            "tag": "Hysteria2",
            "server": ip,
            "server_port": hy['port'],
            "password": hy['password'],
            "tls": {
                "enabled": True,
                "server_name": hy['sni'],
                "insecure": True,
                "alpn": ["h3"],
            },
        })

    # TUIC5
    tu = extracted.get('tuic', {})
    if tu:
        outbounds.append({
            "type": "tuic",
            "tag": "Tuic5",
            "server": ip,
            "server_port": tu['port'],
            "uuid": tu['uuid'],
            "password": tu['password'],
            "congestion_control": "bbr",
            "udp_relay_mode": "native",
            "tls": {
                "enabled": True,
                "server_name": tu['sni'],
                "insecure": True,
                "alpn": ["h3"],
            },
        })

    # AnyTLS
    at = extracted.get('anytls', {})
    if at:
        outbounds.append({
            "type": "anytls",
            "tag": "AnyTLS",
            "server": ip,
            "server_port": at['port'],
            "password": at['password'],
            "tls": {
                "enabled": True,
                "server_name": at['sni'],
                "insecure": True,
            },
        })

    # 收集代理 tag 名称
    proxy_tags = [ob['tag'] for ob in outbounds]

    # direct / block outbound
    outbounds.append({"type": "direct", "tag": "direct"})
    outbounds.append({"type": "block", "tag": "block"})

    # selector 代理组
    outbounds.append({
        "type": "selector",
        "tag": "proxy",
        "outbounds": proxy_tags + ["auto"],
        "default": proxy_tags[0] if proxy_tags else "direct",
    })

    # urltest 自动选择
    outbounds.append({
        "type": "urltest",
        "tag": "auto",
        "outbounds": proxy_tags,
        "url": "https://www.gstatic.com/generate_204",
        "interval": "5m",
        "tolerance": 50,
    })

    # ─── 完整配置 ───
    client_config = {
        "log": {
            "level": "info",
            "timestamp": True,
        },
        "inbounds": [
            {
                "type": "tun",
                "tag": "tun-in",
                "interface_name": "tun0",
                "inet4_address": "172.19.0.1/30",
                "auto_route": True,
                "strict_route": True,
                "sniff": True,
            },
            {
                "type": "mixed",
                "tag": "mixed-in",
                "listen": "127.0.0.1",
                "listen_port": 7890,
                "sniff": True,
            },
        ],
        "outbounds": outbounds,
        "route": {
            "rules": [
                {
                    "action": "sniff",
                },
                {
                    "protocol": ["dns"],
                    "action": "hijack-dns",
                },
                {
                    "ip_is_private": True,
                    "outbound": "direct",
                },
                {
                    "geosite": ["cn"],
                    "outbound": "direct",
                },
                {
                    "geoip": ["cn"],
                    "outbound": "direct",
                },
                {
                    "geosite": ["private"],
                    "outbound": "direct",
                },
            ],
            "final": "proxy",
            "auto_detect_interface": True,
        },
        "dns": {
            "servers": [
                {
                    "tag": "local-dns",
                    "address": "223.5.5.5",
                    "detour": "direct",
                },
                {
                    "tag": "remote-dns",
                    "address": "https://dns.google/dns-query",
                    "detour": "proxy",
                },
            ],
            "rules": [
                {
                    "outbound": "any",
                    "server": "local-dns",
                },
                {
                    "geosite": ["cn"],
                    "server": "local-dns",
                },
                {
                    "geosite": ["private"],
                    "server": "local-dns",
                },
            ],
            "final": "remote-dns",
            "independent_cache": True,
        },
    }

    return client_config


def save_client_config(config, ip=None, output_dir="/etc/s-box-sn/output"):
    """
    生成并保存 sing-box 客户端配置 JSON 文件。

    参数:
        config (dict): load_config() 返回的完整配置
        ip (str, optional): 公网 IP
        output_dir (str): 输出目录

    返回:
        str: 输出文件的完整路径
    """
    os.makedirs(output_dir, exist_ok=True)
    client_cfg = generate_client_config(config, ip)
    output_path = os.path.join(output_dir, "sb-client.json")
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(client_cfg, f, indent=2, ensure_ascii=False)
    return output_path


# ──────────────────── 命令行测试 ────────────────────
if __name__ == '__main__':
    config_path = sys.argv[1] if len(sys.argv) > 1 else None
    try:
        cfg = load_config(config_path) if config_path else load_config()
        ip = get_public_ip()
        path = save_client_config(cfg, ip)
        print("✅ sing-box 客户端配置已生成: {}".format(path))
    except Exception as e:
        print("❌ 错误: {}".format(e), file=sys.stderr)
        sys.exit(1)
