#!/usr/bin/env python3
"""
warp.py — WARP 分流配置模块

实现原理：
1. WARP 是 Cloudflare 提供的免费 WireGuard VPN
2. 在 sing-box 中配置 WireGuard endpoint 连接 WARP 服务器
3. 通过路由规则，指定某些域名走 WARP 出站
4. 解决 VPS IP 被某些服务封锁的问题（如 ChatGPT、Google）

流量路径：
  客户端 → sing-box → WireGuard 出站 → CF WARP → 目标网站

关键参数：
  - WARP 服务器: 162.159.192.1:2408 (IPv4) 或 [2606:4700:d0::a29f:c001]:2408 (IPv6)
  - WARP 公钥（固定）: bmXOC+F1FxEMF9dyiK2H5/1SUtzH0JuVo51h2wPfgyo=
  - 需要自己的 WireGuard 私钥 + WARP 分配的地址 + reserved 值

获取配置方式：
  warp-go 安装后会生成配置文件，从中提取：
  - PrivateKey
  - Address (IPv4 172.16.0.x + IPv6 fd00:xxxx)
  - Reserved（防指纹识别）
"""

import os
import sys
import json
import subprocess
import re
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

WARP_GO_DIR = "/etc/warp-go"
WARP_CONF = os.path.join(WARP_GO_DIR, "warp.conf")
WARP_STATE = os.path.join(WARP_GO_DIR, "state.json")
SB_JSON = "/etc/s-box-sn/sb.json"
WARP_ENDPOINT = "162.159.192.1"
WARP_ENDPOINT_V6 = "2606:4700:d0::a29f:c001"
WARP_PORT = 2408
WARP_PUBLIC_KEY = "bmXOC+F1FxEMF9dyiK2H5/1SUtzH0JuVo51h2wPfgyo="


def check_warp_installed():
    """检查 warp-go 是否安装"""
    return os.path.isfile('/usr/local/bin/warp-go') or os.path.isfile('/usr/bin/warp-go')


def get_warp_config():
    """
    从 warp-go 的状态文件获取 WireGuard 配置

    返回:
        dict: {
            'private_key': str,
            'address_v4': str,    (如 '172.16.0.2/32')
            'address_v6': str,    (如 'fd00::2/128')
            'reserved': list,     (如 [100, 200, 30])
        }
    """
    # 尝试从 state.json 读取
    if os.path.isfile(WARP_STATE):
        with open(WARP_STATE, 'r') as f:
            state = json.load(f)
        return {
            'private_key': state.get('private_key', ''),
            'address_v4': state.get('address', [''])[0] if state.get('address') else '',
            'address_v6': state.get('address', ['', ''])[1] if len(state.get('address', [])) > 1 else '',
            'reserved': state.get('reserved', [])
        }

    # 尝试从 warp.conf 读取（INI 格式）
    if os.path.isfile(WARP_CONF):
        return _parse_warp_conf(WARP_CONF)

    return None


def _parse_warp_conf(path):
    """
    解析 warp.conf (WireGuard INI 格式)

    [Interface]
    PrivateKey = xxx
    Address = 172.16.0.2/32
    Address = fd00::2/128

    [Peer]
    PublicKey = xxx
    Endpoint = 162.159.192.1:2408
    """
    config = {'private_key': '', 'address_v4': '', 'address_v6': '', 'reserved': []}
    addresses = []
    current_section = ''

    with open(path, 'r') as f:
        for line in f:
            line = line.strip()
            if line.startswith('['):
                current_section = line
            elif '=' in line and current_section == '[Interface]':
                key, val = line.split('=', 1)
                key = key.strip()
                val = val.strip()
                if key == 'PrivateKey':
                    config['private_key'] = val
                elif key == 'Address':
                    addresses.append(val)

    for addr in addresses:
        if ':' in addr:
            config['address_v6'] = addr
        else:
            config['address_v4'] = addr

    return config


def gen_warp_reserved():
    """
    生成随机 reserved 值（3个字节）

    WARP 的 reserved 字段用于防指纹识别，
    每个用户不同，需要从 WARP 注册信息中获取。

    返回:
        list: 3个 0-255 的整数
    """
    import random
    return [random.randint(0, 255) for _ in range(3)]


def add_warp_endpoint_to_config(wg_config):
    """
    将 WARP WireGuard endpoint 添加到 sb.json

    sing-box 1.13+ 使用 endpoints 数组格式：
    {
        "endpoints": [{
            "type": "wireguard",
            "tag": "warp-out",
            "address": ["172.16.0.2/32", "fd00::2/128"],
            "private_key": "xxx",
            "peers": [{
                "address": "162.159.192.1",
                "port": 2408,
                "public_key": "bmXOC+F1FxEMF9dyiK2H5/1SUtzH0JuVo51h2wPfgyo=",
                "allowed_ips": ["0.0.0.0/0", "::/0"],
                "reserved": [100, 200, 30]
            }]
        }]
    }

    参数:
        wg_config: get_warp_config() 返回的配置

    返回:
        bool: 是否成功
    """
    if not os.path.isfile(SB_JSON):
        print(f"配置文件不存在: {SB_JSON}")
        return False

    # 备份
    backup = SB_JSON + '.bak.' + str(int(time.time()))
    subprocess.run(['cp', SB_JSON, backup])
    print(f"已备份配置: {backup}")

    with open(SB_JSON, 'r') as f:
        config = json.load(f)

    # 添加 endpoint
    if 'endpoints' not in config:
        config['endpoints'] = []

    # 检查是否已有 warp-out
    existing = [e for e in config['endpoints'] if e.get('tag') == 'warp-out']
    if existing:
        print("warp-out endpoint 已存在，将更新")
        config['endpoints'] = [e for e in config['endpoints'] if e.get('tag') != 'warp-out']

    warp_endpoint = {
        "type": "wireguard",
        "tag": "warp-out",
        "address": [
            wg_config['address_v4'],
            wg_config['address_v6']
        ] if wg_config['address_v6'] else [wg_config['address_v4']],
        "private_key": wg_config['private_key'],
        "peers": [{
            "address": WARP_ENDPOINT,
            "port": WARP_PORT,
            "public_key": WARP_PUBLIC_KEY,
            "allowed_ips": ["0.0.0.0/0", "::/0"],
            "reserved": wg_config['reserved'] if wg_config['reserved'] else gen_warp_reserved()
        }]
    }

    config['endpoints'].append(warp_endpoint)

    # 添加 WARP 分流规则到 route.rules
    if 'route' not in config:
        config['route'] = {}
    if 'rules' not in config['route']:
        config['route']['rules'] = []

    # 在 sniff 规则之后、direct 规则之前插入 WARP 规则
    warp_rule = {
        "outbound": "warp-out",
        "domain_suffix": [
            "openai.com",
            "chatgpt.com",
            "chat.openai.com",
            "oaistatic.com",
            "oaiusercontent.com",
            "anthropic.com",
            "claude.ai"
        ]
    }

    # 插入规则（在最后一条 direct 规则之前）
    rules = config['route']['rules']
    insert_idx = len(rules)
    for i, rule in enumerate(rules):
        if rule.get('outbound') == 'direct':
            insert_idx = i
            break
    rules.insert(insert_idx, warp_rule)

    # 写回配置
    with open(SB_JSON, 'w') as f:
        json.dump(config, f, indent=2, ensure_ascii=False)

    print("✓ WARP endpoint 已添加到配置")
    print("✓ WARP 分流规则已添加（默认分流 OpenAI、Claude 等）")
    return True


def remove_warp_from_config():
    """从配置中移除 WARP endpoint 和规则"""
    if not os.path.isfile(SB_JSON):
        return False

    backup = SB_JSON + '.bak.' + str(int(time.time()))
    subprocess.run(['cp', SB_JSON, backup])

    with open(SB_JSON, 'r') as f:
        config = json.load(f)

    # 移除 warp-out endpoint
    config['endpoints'] = [e for e in config.get('endpoints', []) if e.get('tag') != 'warp-out']

    # 移除 warp-out 规则
    config['route']['rules'] = [r for r in config.get('route', {}).get('rules', []) if r.get('outbound') != 'warp-out']

    with open(SB_JSON, 'w') as f:
        json.dump(config, f, indent=2, ensure_ascii=False)

    print("✓ WARP 已从配置中移除")
    return True


def show_warp_status():
    """显示 WARP 状态"""
    if not check_warp_installed():
        print("warp-go 未安装")
        return None

    wg_config = get_warp_config()
    if not wg_config:
        print("WARP 配置未找到")
        return None

    # 检查是否在 sb.json 中配置了
    with open(SB_JSON, 'r') as f:
        config = json.load(f)
    has_endpoint = any(e.get('tag') == 'warp-out' for e in config.get('endpoints', []))

    print("WARP 状态:")
    print(f"  warp-go: 已安装")
    print(f"  Private Key: {wg_config['private_key'][:20]}...")
    print(f"  Address v4: {wg_config['address_v4']}")
    print(f"  Address v6: {wg_config['address_v6']}")
    print(f"  Reserved: {wg_config['reserved']}")
    print(f"  sing-box endpoint: {'已配置' if has_endpoint else '未配置'}")

    # 显示分流域名
    warp_rules = [r for r in config.get('route', {}).get('rules', []) if r.get('outbound') == 'warp-out']
    if warp_rules:
        print(f"  分流域名:")
        for rule in warp_rules:
            for domain in rule.get('domain_suffix', []):
                print(f"    - {domain}")

    return wg_config


def setup_warp():
    """
    完整的 WARP 设置流程

    1. 检查 warp-go 是否安装
    2. 获取 WireGuard 配置
    3. 添加到 sb.json
    4. 重启 sing-box
    """
    print("=== WARP 分流设置 ===\n")

    if not check_warp_installed():
        print("warp-go 未安装")
        print("请先手动安装 warp-go:")
        print("  下载: https://github.com/nicedayzhu/warp-go/releases")
        print("  或使用其他 WARP 管理脚本安装")
        print("\n安装后重新运行此脚本即可配置分流。")
        return False

    wg_config = get_warp_config()
    if not wg_config:
        print("无法获取 WARP 配置")
        return False

    if not wg_config['private_key']:
        print("WARP 私钥为空，请检查 warp-go 配置")
        return False

    success = add_warp_endpoint_to_config(wg_config)
    if success:
        print("\n✓ WARP 分流配置完成")
        print("  请重启 sing-box 使配置生效: systemctl restart sing-box")
        print("\n  默认分流的域名:")
        print("    - openai.com / chatgpt.com")
        print("    - anthropic.com / claude.ai")
        print("\n  如需添加更多域名，编辑 sb.json 中 route.rules 的 warp-out 规则")

    return success


if __name__ == '__main__':
    if len(sys.argv) > 1:
        cmd = sys.argv[1]
        if cmd == 'setup':
            setup_warp()
        elif cmd == 'remove':
            remove_warp_from_config()
        elif cmd == 'status':
            show_warp_status()
        else:
            print(f"用法: python3 {sys.argv[0]} [setup|remove|status]")
    else:
        show_warp_status()
