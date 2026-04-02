#!/usr/bin/env python3
"""
clash.py - Clash/Mihomo 配置生成模块

从 sb.json 读取配置，生成完整的 Clash YAML 配置文件。
支持指定用户和协议选择。
纯 Python 标准库实现，字符串格式化生成 YAML。
"""

import os
import sys
import datetime

from config import (load_config, extract_config, extract_config_for_user,
                    get_public_ip, DEFAULT_SNI, PROTOCOL_NAMES)


def _build_proxies_yaml(extracted, ip):
    """
    根据提取的配置构建代理 YAML 块。

    参数:
        extracted (dict): extract_config() 返回的配置
        ip (str): 公网 IP

    返回:
        str: YAML 代理列表文本
    """
    proxies_yaml = ""

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

    return proxies_yaml


def _build_proxy_names(extracted):
    """构建代理名称列表"""
    names = []
    for key in ('vless', 'vmess', 'hysteria2', 'tuic', 'anytls'):
        if extracted.get(key):
            names.append('"{}"'.format(PROTOCOL_NAMES.get(key, key)))
    return names


def generate_clash_yaml(config, ip=None):
    """
    生成完整的 Clash/Mihomo YAML 配置（默认用户，向后兼容）。

    参数:
        config (dict): load_config() 返回的完整配置
        ip (str, optional): 公网 IP

    返回:
        str: 完整的 YAML 配置文本
    """
    if ip is None:
        ip = get_public_ip()
    extracted = extract_config(config)
    return _generate_yaml(extracted, ip)


def generate_clash_yaml_for_user(config, user, ip=None):
    """
    为指定用户生成 Clash 配置。

    参数:
        config (dict): load_config() 返回的完整配置
        user (dict): 用户信息
        ip (str, optional): 公网 IP

    返回:
        str: 完整的 YAML 配置文本
    """
    if ip is None:
        ip = get_public_ip()
    extracted = extract_config_for_user(config, user)
    return _generate_yaml(extracted, ip)


def generate_clash_yaml_for_protocols(config, user, protocols, ip=None):
    """
    为指定用户、指定协议生成 Clash 配置。

    参数:
        config (dict): load_config() 返回的完整配置
        user (dict): 用户信息
        protocols (list): 选中的协议列表
        ip (str, optional): 公网 IP

    返回:
        str: 完整的 YAML 配置文本
    """
    if ip is None:
        ip = get_public_ip()
    extracted = extract_config_for_user(config, user)
    filtered = {k: v for k, v in extracted.items() if k in protocols}
    return _generate_yaml(filtered, ip, user_suffix=user['name'])


def _generate_yaml(extracted, ip, user_suffix=""):
    """
    内部函数：根据提取的配置生成完整 YAML。

    参数:
        extracted (dict): 提取的配置
        ip (str): 公网 IP
        user_suffix (str): 用户名后缀

    返回:
        str: YAML 配置文本
    """
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    user_tag = " - {}".format(user_suffix) if user_suffix else ""

    proxies_yaml = _build_proxies_yaml(extracted, ip)
    proxy_names = _build_proxy_names(extracted)

    if not proxy_names:
        return "# 没有可用的协议配置\n"

    proxy_names_block = "\n      ".join(proxy_names)
    auto_proxies_block = "\n      ".join(proxy_names)

    yaml = """# ============================================================
# Clash/Mihomo 配置文件 - sing-box 管理工具自动生成
# 生成时间: {time}
# VPS: {ip}{user_tag}
# ============================================================

mixed-port: 7890
allow-lan: true
mode: rule
log-level: info

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

proxies:
{proxies}
proxy-groups:
  - name: "proxy"
    type: select
    proxies:
      {proxy_names}
      - "auto"

  - name: "auto"
    type: url-test
    url: "https://www.gstatic.com/generate_204"
    interval: 300
    tolerance: 50
    lazy: true
    proxies:
      {auto_proxies}

  - name: "节点选择"
    type: select
    proxies:
      - "proxy"
      - "direct"

  - name: "自动选择"
    type: url-test
    url: "https://www.gstatic.com/generate_204"
    interval: 300
    tolerance: 50
    lazy: true
    proxies:
      {auto_proxies}

rules:
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
  - GEOIP,CN,direct
  - GEOSITE,CN,direct
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
  - MATCH,proxy
""".format(time=now, ip=ip, user_tag=user_tag, proxies=proxies_yaml,
           proxy_names=proxy_names_block, auto_proxies=auto_proxies_block)

    return yaml


def save_clash_yaml(config, ip=None, output_dir="/etc/s-box-sn/output"):
    """
    生成并保存 Clash YAML 配置文件（默认用户，向后兼容）。

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


def save_clash_yaml_for_user(config, user, ip=None, output_dir="/etc/s-box-sn/output"):
    """
    为指定用户保存 Clash YAML 配置文件。

    参数:
        config (dict): load_config() 返回的完整配置
        user (dict): 用户信息
        ip (str, optional): 公网 IP
        output_dir (str): 输出目录

    返回:
        str: 输出文件的完整路径
    """
    os.makedirs(output_dir, exist_ok=True)
    yaml_content = generate_clash_yaml_for_user(config, user, ip)
    filename = "clash-{}.yaml".format(user['name'])
    output_path = os.path.join(output_dir, filename)
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(yaml_content)
    return output_path


def save_clash_yaml_for_protocols(config, user, protocols, ip=None, output_dir="/etc/s-box-sn/output"):
    """
    为指定用户、指定协议保存 Clash YAML 配置文件。

    参数:
        config (dict): load_config() 返回的完整配置
        user (dict): 用户信息
        protocols (list): 选中的协议列表
        ip (str, optional): 公网 IP
        output_dir (str): 输出目录

    返回:
        str: 输出文件的完整路径
    """
    os.makedirs(output_dir, exist_ok=True)
    yaml_content = generate_clash_yaml_for_protocols(config, user, protocols, ip)
    filename = "clash-{}.yaml".format(user['name'])
    output_path = os.path.join(output_dir, filename)
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(yaml_content)
    return output_path


if __name__ == '__main__':
    config_path = sys.argv[1] if len(sys.argv) > 1 else None
    try:
        cfg = load_config(config_path) if config_path else load_config()
        ip = get_public_ip()
        path = save_clash_yaml(cfg, ip)
        print("Clash 配置已生成: {}".format(path))
    except Exception as e:
        print("错误: {}".format(e), file=sys.stderr)
        sys.exit(1)
