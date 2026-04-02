#!/usr/bin/env python3
"""
config.py — sing-box 配置读取模块

从 /etc/s-box-sn/sb.json 动态读取所有配置信息，
提取各协议的端口、UUID、密钥、SNI 等参数。
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

# 从私钥推导的公钥（sing-box generate reality-keypair 生成）
REALITY_PUBLIC_KEY = "mayeSAHMUyw96197nxS9QzuGj5R0B3WGcAmKhpR7e0Y"


def strip_json_comments(text):
    """
    去除 JSON 中的 // 注释行（不影响字符串内的 // ）。

    参数:
        text (str): 原始 JSON 文本

    返回:
        str: 去除注释后的 JSON 文本
    """
    lines = []
    for line in text.split('\n'):
        # 跳过整行 // 注释
        stripped = line.lstrip()
        if stripped.startswith('//'):
            continue
        # 去除行内 // 注释（简单处理：不在引号内的 // 视为注释）
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
                break  # 行内注释，截断
            result.append(ch)
            i += 1
        lines.append(''.join(result))
    return '\n'.join(lines)


def load_config(config_path=DEFAULT_CONFIG_PATH):
    """
    读取并解析 sb.json 配置文件。

    参数:
        config_path (str): 配置文件路径，默认 /etc/s-box-sn/sb.json

    返回:
        dict: 解析后的配置字典

    异常:
        FileNotFoundError: 配置文件不存在
        json.JSONDecodeError: JSON 解析失败
    """
    if not os.path.isfile(config_path):
        raise FileNotFoundError("配置文件不存在: {}".format(config_path))

    with open(config_path, 'r', encoding='utf-8') as f:
        raw = f.read()

    # 去除 JSON 注释
    cleaned = strip_json_comments(raw)
    return json.loads(cleaned)


def get_public_ip():
    """
    获取当前 VPS 的公网 IP 地址。

    依次尝试多个外部服务获取公网 IP。

    返回:
        str: 公网 IP 地址
    """
    services = [
        ['curl', '-s', '--max-time', '5', 'https://api.ipify.org'],
        ['curl', '-s', '--max-time', '5', 'https://ifconfig.me'],
        ['curl', '-s', '--max-time', '5', 'https://icanhazip.com'],
    ]
    for cmd in services:
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            ip = result.stdout.strip()
            # 简单校验 IP 格式
            if re.match(r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$', ip):
                return ip
        except Exception:
            continue
    # 兜底：从配置中推断或使用已知 IP
    try:
        result = subprocess.run(['hostname', '-I'], capture_output=True, text=True, timeout=5)
        ips = result.stdout.strip().split()
        for ip in ips:
            if re.match(r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$', ip) and ip != '127.0.0.1':
                return ip
    except Exception:
        pass
    # 最终兜底
    return "96.44.141.123"


def _safe_get(d, *keys, default=None):
    """
    安全地从嵌套字典/列表中取值。

    参数:
        d: 源数据（dict 或 list）
        *keys: 逐层键名或索引
        default: 取不到时的默认值
    """
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
    """
    从 inbounds 列表中查找指定协议的入口。

    参数:
        inbounds (list): 入口配置列表
        protocol (str): 协议类型（如 "vless"、"vmess" 等）

    返回:
        dict or None: 找到的入口配置
    """
    for inbound in inbounds:
        if inbound.get('type') == protocol:
            return inbound
    return None


def extract_config(config):
    """
    从完整配置中提取各协议的关键参数。

    参数:
        config (dict): load_config() 返回的完整配置

    返回:
        dict: 包含各协议参数的字典，结构如下：
        {
            "vless": {"port": int, "uuid": str, "sni": str, "public_key": str, "short_id": str, "flow": str},
            "vmess": {"port": int, "uuid": str, "sni": str, "path": str},
            "hysteria2": {"port": int, "password": str, "sni": str},
            "tuic": {"port": int, "uuid": str, "password": str, "sni": str},
            "anytls": {"port": int, "password": str, "sni": str},
        }
    """
    inbounds = config.get('inbounds', [])
    result = {}

    # ─── VLess-Reality ───
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

    # ─── VMess-WS ───
    vmess = _find_inbound(inbounds, 'vmess')
    if vmess:
        result['vmess'] = {
            'port': vmess.get('listen_port', 0),
            'uuid': _safe_get(vmess, 'users', 0, 'uuid', default=''),
            'sni': _safe_get(vmess, 'tls', 'server_name', default=DEFAULT_SNI) or DEFAULT_SNI,
            'path': _safe_get(vmess, 'transport', 'path', default='/'),
        }

    # ─── Hysteria2 ───
    hy2 = _find_inbound(inbounds, 'hysteria2')
    if hy2:
        result['hysteria2'] = {
            'port': hy2.get('listen_port', 0),
            'password': _safe_get(hy2, 'users', 0, 'password', default=''),
            'sni': DEFAULT_SNI,  # Hy2 使用自签证书，SNI 固定为 hostname
        }

    # ─── TUIC ───
    tuic = _find_inbound(inbounds, 'tuic')
    if tuic:
        result['tuic'] = {
            'port': tuic.get('listen_port', 0),
            'uuid': _safe_get(tuic, 'users', 0, 'uuid', default=''),
            'password': _safe_get(tuic, 'users', 0, 'password', default=''),
            'sni': DEFAULT_SNI,
        }

    # ─── AnyTLS ───
    anytls = _find_inbound(inbounds, 'anytls')
    if anytls:
        result['anytls'] = {
            'port': anytls.get('listen_port', 0),
            'password': _safe_get(anytls, 'users', 0, 'password', default=''),
            'sni': DEFAULT_SNI,
        }

    return result


# ──────────────────── 命令行测试 ────────────────────
if __name__ == '__main__':
    config_path = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_CONFIG_PATH
    try:
        cfg = load_config(config_path)
        extracted = extract_config(cfg)
        ip = get_public_ip()
        print("=== VPS IP: {} ===".format(ip))
        for proto, params in extracted.items():
            print("\n[{}]".format(proto.upper()))
            for k, v in params.items():
                print("  {}: {}".format(k, v))
    except Exception as e:
        print("错误: {}".format(e), file=sys.stderr)
        sys.exit(1)
