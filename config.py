#!/usr/bin/env python3
"""
config.py - sing-box 配置读取模块

从 /etc/s-box-sn/sb.json 动态读取所有配置信息，
提取各协议的端口、UUID、密钥、SNI 等参数。
支持多用户配置读取。
兼容 Python 3.6+，纯标准库实现。
"""

import json
import os
import re
import sys
import subprocess


# 默认 SNI，当配置中 SNI 为 null 或缺失时使用
DEFAULT_SNI = "racknerd-9edcd3"

# 默认配置文件路径
DEFAULT_CONFIG_PATH = "/etc/s-box-sn/sb.json"

# 从私钥推导的公钥
REALITY_PUBLIC_KEY = "mayeSAHMUyw96197nxS9QzuGj5R0B3WGcAmKhpR7e0Y"


def strip_json_comments(text):
    """去除 JSON 中的 // 注释行"""
    lines = []
    for line in text.split('\n'):
        stripped = line.lstrip()
        if stripped.startswith('//'):
            continue
        in_string = False
        escape = False
        result = []
        i = 0
        while i < len(line):
            ch = line[i]
            if escape:
                result.append(ch)
                escape = False
                i += 1
                continue
            if ch == '\\':
                result.append(ch)
                escape = True
                i += 1
                continue
            if ch == '"':
                in_string = not in_string
                result.append(ch)
                i += 1
                continue
            if not in_string and ch == '/' and i + 1 < len(line) and line[i + 1] == '/':
                break
            result.append(ch)
            i += 1
        lines.append(''.join(result))
    return '\n'.join(lines)


def load_config(config_path=DEFAULT_CONFIG_PATH):
    """读取并解析 sb.json 配置文件"""
    if not os.path.isfile(config_path):
        raise FileNotFoundError("配置文件不存在: {}".format(config_path))
    with open(config_path, 'r', encoding='utf-8') as f:
        raw = f.read()
    cleaned = strip_json_comments(raw)
    return json.loads(cleaned)


def get_public_ip():
    """获取当前 VPS 的公网 IP 地址"""
    services = [
        ['curl', '-s', '--max-time', '5', 'https://api.ipify.org'],
        ['curl', '-s', '--max-time', '5', 'https://ifconfig.me'],
        ['curl', '-s', '--max-time', '5', 'https://icanhazip.com'],
    ]
    for cmd in services:
        try:
            result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True, timeout=10)
            ip = result.stdout.strip()
            if re.match(r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$', ip):
                return ip
        except Exception:
            continue
    try:
        result = subprocess.run(['hostname', '-I'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True, timeout=5)
        ips = result.stdout.strip().split()
        for ip in ips:
            if re.match(r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$', ip) and ip != '127.0.0.1':
                return ip
    except Exception:
        pass
    return "96.44.141.123"


def _safe_get(d, *keys, default=None):
    """安全地从嵌套字典/列表中取值"""
    for k in keys:
        if isinstance(d, dict):
            d = d.get(k, default)
        elif isinstance(d, list) and isinstance(k, int):
            d = d[k] if k < len(d) else default
        else:
            return default
        if d is None:
            return default
    return d


def _find_inbound(inbounds, protocol):
    """从 inbounds 列表中查找指定协议的入口"""
    for inbound in inbounds:
        if inbound.get('type') == protocol:
            return inbound
    return None


def extract_config(config):
    """
    从完整配置中提取各协议的关键参数（默认取第一个用户，保持向后兼容）。

    返回:
        dict: 包含各协议参数的字典
    """
    inbounds = config.get('inbounds', [])
    result = {}

    # VLess-Reality
    vless = _find_inbound(inbounds, 'vless')
    if vless:
        result['vless'] = {
            'port': vless.get('listen_port', 0),
            'uuid': _safe_get(vless, 'users', 0, 'uuid', default=''),
            'sni': _safe_get(vless, 'tls', 'server_name', default=DEFAULT_SNI) or DEFAULT_SNI,
            'private_key': _safe_get(vless, 'tls', 'reality', 'private_key', default=''),
            'public_key': REALITY_PUBLIC_KEY,
            'short_id': _safe_get(vless, 'tls', 'reality', 'short_id', 0, default=''),
            'flow': _safe_get(vless, 'users', 0, 'flow', default='xtls-rprx-vision'),
        }

    # VMess-WS
    vmess = _find_inbound(inbounds, 'vmess')
    if vmess:
        result['vmess'] = {
            'port': vmess.get('listen_port', 0),
            'uuid': _safe_get(vmess, 'users', 0, 'uuid', default=''),
            'sni': _safe_get(vmess, 'tls', 'server_name', default=DEFAULT_SNI) or DEFAULT_SNI,
            'path': _safe_get(vmess, 'transport', 'path', default='/'),
        }

    # Hysteria2
    hy2 = _find_inbound(inbounds, 'hysteria2')
    if hy2:
        result['hysteria2'] = {
            'port': hy2.get('listen_port', 0),
            'password': _safe_get(hy2, 'users', 0, 'password', default=''),
            'sni': DEFAULT_SNI,
        }

    # TUIC
    tuic = _find_inbound(inbounds, 'tuic')
    if tuic:
        result['tuic'] = {
            'port': tuic.get('listen_port', 0),
            'uuid': _safe_get(tuic, 'users', 0, 'uuid', default=''),
            'password': _safe_get(tuic, 'users', 0, 'password', default=''),
            'sni': DEFAULT_SNI,
        }

    # AnyTLS
    anytls = _find_inbound(inbounds, 'anytls')
    if anytls:
        result['anytls'] = {
            'port': anytls.get('listen_port', 0),
            'password': _safe_get(anytls, 'users', 0, 'password', default=''),
            'sni': DEFAULT_SNI,
        }

    return result


def extract_config_for_user(config, user):
    """
    为指定用户提取各协议参数（用该用户的 UUID/password 替换默认值）。

    参数:
        config (dict): load_config() 返回的完整配置
        user (dict): 用户信息 {"name": str, "uuid": str, "password": str}

    返回:
        dict: 包含各协议参数的字典
    """
    extracted = extract_config(config)

    for proto in extracted:
        if proto == 'vless':
            extracted[proto]['uuid'] = user['uuid']
        elif proto == 'vmess':
            extracted[proto]['uuid'] = user['uuid']
        elif proto in ('hysteria2', 'anytls'):
            extracted[proto]['password'] = user['password']
        elif proto == 'tuic':
            extracted[proto]['uuid'] = user['uuid']
            extracted[proto]['password'] = user['password']

    return extracted


def get_config_protocols(config):
    """
    获取配置中所有启用的协议列表。

    参数:
        config (dict): load_config() 返回的完整配置

    返回:
        list: 协议名称列表，如 ['vless', 'vmess', 'anytls']
    """
    protocols = []
    inbounds = config.get('inbounds', [])
    for inbound in inbounds:
        ptype = inbound.get('type', '')
        if ptype in ('vless', 'vmess', 'hysteria2', 'tuic', 'anytls'):
            protocols.append(ptype)
    return protocols


# 协议显示名称映射
PROTOCOL_NAMES = {
    'vless': 'VLess-Reality',
    'vmess': 'VMess-WS',
    'hysteria2': 'Hysteria2',
    'tuic': 'Tuic5',
    'anytls': 'AnyTLS',
}

# 协议序号映射
PROTOCOL_INDEX = {
    'vless': 1,
    'vmess': 2,
    'hysteria2': 3,
    'tuic': 4,
    'anytls': 5,
}

INDEX_PROTOCOL = {v: k for k, v in PROTOCOL_INDEX.items()}


def select_protocols(config):
    """
    交互式让用户选择协议。

    参数:
        config (dict): load_config() 返回的完整配置

    返回:
        list: 选中的协议名称列表，如 ['vless', 'anytls']
              空列表表示全选
    """
    protocols = get_config_protocols(config)
    if not protocols:
        return []

    print("\n可用协议:")
    for p in protocols:
        idx = PROTOCOL_INDEX.get(p, '?')
        name = PROTOCOL_NAMES.get(p, p)
        print("  [{}] {}".format(idx, name))
    print("  [0] 全部协议")

    choice = input("\n选择协议 (输入编号，逗号分隔，如 1,3 或 all): ").strip()

    if choice == '' or choice.lower() == 'all' or choice == '0':
        return protocols

    selected = []
    for part in choice.split(','):
        part = part.strip()
        try:
            idx = int(part)
            proto = INDEX_PROTOCOL.get(idx)
            if proto and proto in protocols and proto not in selected:
                selected.append(proto)
        except ValueError:
            # 尝试匹配协议名
            for p in protocols:
                if p.startswith(part.lower()) and p not in selected:
                    selected.append(p)
                    break

    if not selected:
        print("未选择任何协议，使用全部协议")
        return protocols

    return selected


if __name__ == '__main__':
    config_path = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_CONFIG_PATH
    try:
        cfg = load_config(config_path)
        extracted = extract_config(cfg)
        ip = get_public_ip()
        print("VPS IP: {}".format(ip))
        for proto, params in extracted.items():
            print("\n[{}]".format(proto.upper()))
            for k, v in params.items():
                print("  {}: {}".format(k, v))
    except Exception as e:
        print("错误: {}".format(e), file=sys.stderr)
        sys.exit(1)
