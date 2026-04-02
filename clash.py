#!/usr/bin/env python3
"""
clash.py — Clash/Mihomo 配置生成模块

从 sb.json 读取配置，生成完整的 Clash YAML 配置文件。
包含: 5 个协议代理、DNS (fake-ip)、分流规则、代理组。
纯 Python 标准库实现，字符串格式化生成 YAML。
"""

import os
import sys
import datetime

from config import load_config, extract_config, get_public_ip, DEFAULT_SNI


def generate_clash_yaml(config, ip=None):
    """
    生成完整的 Clash/Mihomo YAML 配置。

    参数:
        config (dict): load_config() 返回的完整配置
        ip (str, optional): 公网 IP，为 None 时自动获取

    返回:
        str: 完整的 YAML 配置文本
    """
    if ip is None:
        ip = get_public_ip()

    extracted = extract_config(config)
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # ─── 构建代理列表 ───
    proxies_yaml = ""

    # VLess-Reality
    v = extracted.get('vless', {})
    if v:
        proxies_yaml += """
  - name: "VLess-Reality"
    type: vless
    server: {ip}
    port: {port}
    uuid: {uuid}
    udp: true
    tls: true
    flow: {flow}
    servername: {sni}
    reality-opts:
      public-key: {pbk}
      short-id: {sid}
    client-fingerprint: chrome
""".format(ip=ip, port=v['port'], uuid=v['uuid'],
           flow=v['flow'], sni=v['sni'], pbk=v['public_key'], sid=v['short_id'])

    # VMess-WS
    vm = extracted.get('vmess', {})
    if vm:
        proxies_yaml += """
  - name: "VMess-WS"
    type: vmess
    server: {ip}
    port: {port}
    uuid: {uuid}
    alterId: 0
    cipher: auto
    udp: true
    tls: true
    servername: {sni}
    network: ws
    ws-opts:
      path: {path}
""".format(ip=ip, port=vm['port'], uuid=vm['uuid'], sni=vm['sni'], path=vm['path'])

    # Hysteria2
    hy = extracted.get('hysteria2', {})
    if hy:
        proxies_yaml += """
  - name: "Hysteria2"
    type: hysteria2
    server: {ip}
    port: {port}
    password: {password}
    udp: true
    sni: {sni}
    skip-cert-verify: true
    alpn:
      - h3
""".format(ip=ip, port=hy['port'], password=hy['password'], sni=hy['sni'])

    # TUIC5
    tu = extracted.get('tuic', {})
    if tu:
        proxies_yaml += """
  - name: "Tuic5"
    type: tuic
    server: {ip}
    port: {port}
    uuid: {uuid}
    password: {password}
    udp: true
    congestion-controller: bbr
    alpn:
      - h3
    sni: {sni}
    skip-cert-verify: true
    udp-relay-mode: native
""".format(ip=ip, port=tu['port'], uuid=tu['uuid'],
           password=tu['password'], sni=tu['sni'])

    # AnyTLS
    at = extracted.get('anytls', {})
    if at:
        proxies_yaml += """
  - name: "AnyTLS"
    type: anytls
    server: {ip}
    port: {port}
    password: {password}
    sni: {sni}
    skip-cert-verify: true
""".format(ip=ip, port=at['port'], password=at['password'], sni=at['sni'])

    # 代理名称列表
    proxy_names = []
    if v:
        proxy_names.append('"VLess-Reality"')
    if vm:
        proxy_names.append('"VMess-WS"')
    if hy:
        proxy_names.append('"Hysteria2"')
    if tu:
        proxy_names.append('"Tuic5"')
    if at:
        proxy_names.append('"AnyTLS"')

    proxy_names_block = "\n      ".join(proxy_names)
    auto_proxies_block = "\n      ".join(proxy_names)

    yaml = """# ============================================================
# Clash/Mihomo 配置文件 — sing-box 管理工具自动生成
# 生成时间: {time}
# VPS: {ip}
# ============================================================

# ============================================================
# 端口与模式
# ============================================================
mixed-port: 7890
allow-lan: true
mode: rule
log-level: info

# ============================================================
# DNS 配置 (fake-ip 模式)
# ============================================================
dns:
  enable: true
  ipv6: false
  enhanced-mode: fake-ip
  fake-ip-range: 198.18.0.1/16
  fake-ip-filter:
    - "*.lan"
    - "*.local"
    - localhost.ptlogin2.qq.com
    - "+.srv.nintendo.net"
    - "+.stun.playstation.net"
    - "+.msftconnecttest.com"
    - "+.msftncsi.com"
  nameserver:
    - 223.5.5.5
    - 119.29.29.29
  fallback:
    - https://dns.google/dns-query
    - https://cloudflare-dns.com/dns-query
    - tls://1.1.1.1:853
  fallback-filter:
    geoip: true
    geoip-code: CN
    ipcidr:
      - 240.0.0.0/4

# ============================================================
# 代理节点
# ============================================================
proxies:
{proxies}
# ============================================================
# 代理组
# ============================================================
proxy-groups:

  # 手动选择
  - name: "proxy"
    type: select
    proxies:
      {proxy_names}
      - "auto"

  # 自动测速选择
  - name: "auto"
    type: url-test
    url: "https://www.gstatic.com/generate_204"
    interval: 300
    tolerance: 50
    lazy: true
    proxies:
      {auto_proxies}

  # 节点选择 (通用 fallback)
  - name: "节点选择"
    type: select
    proxies:
      - "proxy"
      - "direct"

  # 自动选择 (所有节点测速)
  - name: "自动选择"
    type: url-test
    url: "https://www.gstatic.com/generate_204"
    interval: 300
    tolerance: 50
    lazy: true
    proxies:
      {auto_proxies}

# ============================================================
# 规则
# ============================================================
rules:
  # --- 广告拦截 ---
  - DOMAIN-SUFFIX,ads.google.com,REJECT
  - DOMAIN-SUFFIX,pagead2.googlesyndication.com,REJECT
  - DOMAIN-SUFFIX,analytics.google.com,REJECT
  - DOMAIN-KEYWORD,admarvel,REJECT
  - DOMAIN-KEYWORD,admaster,REJECT
  - DOMAIN-KEYWORD,adsage,REJECT
  - DOMAIN-KEYWORD,adsensor,REJECT
  - DOMAIN-KEYWORD,adsmogo,REJECT
  - DOMAIN-KEYWORD,adsrvmedia,REJECT
  - DOMAIN-KEYWORD,adsserving,REJECT
  - DOMAIN-KEYWORD,adsystem,REJECT
  - DOMAIN-KEYWORD,adwords,REJECT

  # --- 国内直连 ---
  - GEOIP,CN,direct
  - GEOSITE,CN,direct

  # --- 私有网络直连 ---
  - IP-CIDR,10.0.0.0/8,direct,no-resolve
  - IP-CIDR,172.16.0.0/12,direct,no-resolve
  - IP-CIDR,192.168.0.0/16,direct,no-resolve
  - IP-CIDR,127.0.0.0/8,direct,no-resolve
  - IP-CIDR,224.0.0.0/4,direct,no-resolve
  - IP-CIDR,fc00::/7,direct,no-resolve
  - IP-CIDR,fe80::/10,direct,no-resolve
  - IP-CIDR,::1/128,direct,no-resolve
  - DOMAIN-SUFFIX,local,direct
  - DOMAIN-SUFFIX,localhost,direct
  - DOMAIN-SUFFIX,lan,direct

  # --- 兜底 ---
  - MATCH,proxy
""".format(
        time=now,
        ip=ip,
        proxies=proxies_yaml,
        proxy_names=proxy_names_block,
        auto_proxies=auto_proxies_block,
    )

    return yaml


def save_clash_yaml(config, ip=None, output_dir="/etc/s-box-sn/output"):
    """
    生成并保存 Clash YAML 配置文件。

    参数:
        config (dict): load_config() 返回的完整配置
        ip (str, optional): 公网 IP
        output_dir (str): 输出目录

    返回:
        str: 输出文件的完整路径
    """
    os.makedirs(output_dir, exist_ok=True)
    yaml_content = generate_clash_yaml(config, ip)
    output_path = os.path.join(output_dir, "clash.yaml")
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(yaml_content)
    return output_path


# ──────────────────── 命令行测试 ────────────────────
if __name__ == '__main__':
    config_path = sys.argv[1] if len(sys.argv) > 1 else None
    try:
        cfg = load_config(config_path) if config_path else load_config()
        ip = get_public_ip()
        path = save_clash_yaml(cfg, ip)
        print("✅ Clash 配置已生成: {}".format(path))
    except Exception as e:
        print("❌ 错误: {}".format(e), file=sys.stderr)
        sys.exit(1)
