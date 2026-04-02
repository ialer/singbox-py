#!/usr/bin/env python3
"""
links.py — 分享链接生成模块

为 sing-box 支持的 5 种协议生成标准分享链接：
VLess-Reality, VMess-WS, Hysteria2, TUIC5, AnyTLS
兼容 Python 3.6+，纯标准库实现。
"""

import json
import base64
try:
    from urllib.parse import quote, urlencode
except ImportError:
    from urllib import quote, urlencode

from config import extract_config, load_config, get_public_ip, DEFAULT_SNI


def _url_encode(s):
    """
    URL 编码字符串。

    参数:
        s (str): 待编码字符串

    返回:
        str: 编码后的字符串
    """
    return quote(str(s), safe='')


def gen_vless_link(uuid, ip, port, sni, public_key, short_id,
                   flow="xtls-rprx-vision", name="VLess-Reality"):
    """
    生成 VLess-Reality 分享链接。

    参数:
        uuid (str): 用户 UUID
        ip (str): 服务器 IP
        port (int): 服务器端口
        sni (str): TLS SNI
        public_key (str): Reality 公钥
        short_id (str): Reality 短 ID
        flow (str): 流控模式，默认 xtls-rprx-vision
        name (str): 节点名称

    返回:
        str: vless:// 开头的分享链接
    """
    params = {
        'encryption': 'none',
        'flow': flow,
        'security': 'reality',
        'sni': sni,
        'fp': 'chrome',
        'pbk': public_key,
        'sid': short_id,
        'type': 'tcp',
        'headerType': 'none',
    }
    query = urlencode(params)
    link = "vless://{}@{}:{}?{}#{}".format(
        uuid, ip, port, query, _url_encode(name))
    return link


def gen_vmess_link(uuid, ip, port, sni, path, name="VMess-WS"):
    """
    生成 VMess-WS-TLS 分享链接（Base64 编码 JSON）。

    参数:
        uuid (str): 用户 UUID
        ip (str): 服务器 IP
        port (int): 服务器端口
        sni (str): TLS SNI
        path (str): WebSocket 路径
        name (str): 节点名称

    返回:
        str: vmess:// 开头的分享链接
    """
    vmess_obj = {
        "v": "2",
        "ps": name,
        "add": ip,
        "port": str(port),
        "id": uuid,
        "aid": "0",
        "scy": "auto",
        "net": "ws",
        "type": "none",
        "host": "",
        "path": path,
        "tls": "tls",
        "sni": sni,
        "alpn": "",
        "fp": "",
    }
    json_str = json.dumps(vmess_obj, separators=(',', ':'))
    # Python 3.6 base64 输出 bytes，需要 decode
    encoded = base64.b64encode(json_str.encode('utf-8')).decode('utf-8')
    return "vmess://" + encoded


def gen_hy2_link(password, ip, port, sni, name="Hysteria2"):
    """
    生成 Hysteria2 分享链接。

    参数:
        password (str): 认证密码
        ip (str): 服务器 IP
        port (int): 服务器端口
        sni (str): TLS SNI
        name (str): 节点名称

    返回:
        str: hysteria2:// 开头的分享链接
    """
    params = {
        'sni': sni,
        'insecure': '1',
    }
    query = urlencode(params)
    link = "hysteria2://{}@{}:{}?{}#{}".format(
        _url_encode(password), ip, port, query, _url_encode(name))
    return link


def gen_tuic_link(uuid, password, ip, port, sni, name="Tuic5"):
    """
    生成 TUIC5 分享链接。

    参数:
        uuid (str): 用户 UUID
        password (str): 用户密码
        ip (str): 服务器 IP
        port (int): 服务器端口
        sni (str): TLS SNI
        name (str): 节点名称

    返回:
        str: tuic:// 开头的分享链接
    """
    params = {
        'congestion_control': 'bbr',
        'sni': sni,
        'insecure': '1',
        'udp_relay_mode': 'native',
    }
    query = urlencode(params)
    link = "tuic://{}:{}@{}:{}?{}#{}".format(
        uuid, _url_encode(password), ip, port, query, _url_encode(name))
    return link


def gen_anytls_link(password, ip, port, sni, name="AnyTLS"):
    """
    生成 AnyTLS 分享链接。

    参数:
        password (str): 认证密码
        ip (str): 服务器 IP
        port (int): 服务器端口
        sni (str): TLS SNI
        name (str): 节点名称

    返回:
        str: anytls:// 开头的分享链接
    """
    params = {
        'sni': sni,
        'allowInsecure': '1',
    }
    query = urlencode(params)
    link = "anytls://{}@{}:{}?{}#{}".format(
        _url_encode(password), ip, port, query, _url_encode(name))
    return link


def gen_all_links(config, ip=None):
    """
    根据配置生成所有协议的分享链接。

    参数:
        config (dict): load_config() 返回的完整配置
        ip (str, optional): 公网 IP，为 None 时自动获取

    返回:
        dict: {protocol_name: share_link} 格式
    """
    if ip is None:
        ip = get_public_ip()

    extracted = extract_config(config)
    links = {}

    # ─── VLess-Reality ───
    v = extracted.get('vless', {})
    if v:
        links['VLess-Reality'] = gen_vless_link(
            uuid=v['uuid'],
            ip=ip,
            port=v['port'],
            sni=v['sni'],
            public_key=v['public_key'],
            short_id=v['short_id'],
            flow=v['flow'],
            name="VLess-Reality-{}".format(ip),
        )

    # ─── VMess-WS ───
    vm = extracted.get('vmess', {})
    if vm:
        links['VMess-WS'] = gen_vmess_link(
            uuid=vm['uuid'],
            ip=ip,
            port=vm['port'],
            sni=vm['sni'],
            path=vm['path'],
            name="VMess-WS-{}".format(ip),
        )

    # ─── Hysteria2 ───
    hy = extracted.get('hysteria2', {})
    if hy:
        links['Hysteria2'] = gen_hy2_link(
            password=hy['password'],
            ip=ip,
            port=hy['port'],
            sni=hy['sni'],
            name="Hysteria2-{}".format(ip),
        )

    # ─── TUIC5 ───
    tu = extracted.get('tuic', {})
    if tu:
        links['Tuic5'] = gen_tuic_link(
            uuid=tu['uuid'],
            password=tu['password'],
            ip=ip,
            port=tu['port'],
            sni=tu['sni'],
            name="Tuic5-{}".format(ip),
        )

    # ─── AnyTLS ───
    at = extracted.get('anytls', {})
    if at:
        links['AnyTLS'] = gen_anytls_link(
            password=at['password'],
            ip=ip,
            port=at['port'],
            sni=at['sni'],
            name="AnyTLS-{}".format(ip),
        )

    return links


# ──────────────────── 命令行测试 ────────────────────
if __name__ == '__main__':
    import sys
    config_path = sys.argv[1] if len(sys.argv) > 1 else None
    try:
        cfg = load_config(config_path) if config_path else load_config()
        ip = get_public_ip()
        links = gen_all_links(cfg, ip)
        print("=== 分享链接 (VPS: {}) ===".format(ip))
        for name, link in links.items():
            print("\n[{}]".format(name))
            print(link)
    except Exception as e:
        print("错误: {}".format(e), file=sys.stderr)
        sys.exit(1)
