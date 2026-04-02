#!/usr/bin/env python3
"""
qrcode.py — 二维码生成模块

为每个协议的分享链接生成终端二维码显示。
优先使用系统的 qrencode 命令，不可用时提示安装。
"""

import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import load_config, extract_config, get_public_ip
from links import gen_all_links


def check_qrencode():
    """检查 qrencode 是否可用"""
    try:
        subprocess.run(['qrencode', '--version'], capture_output=True, check=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def generate_qrcode_terminal(text, label=""):
    """
    在终端生成二维码 (ANSI UTF8)

    Args:
        text: 要编码的文本（分享链接）
        label: 标签说明
    """
    if label:
        print(f"\n\033[1;33m{label}\033[0m")

    try:
        subprocess.run(
            ['qrencode', '-o', '-', '-t', 'ANSIUTF8'],
            input=text.encode(),
            check=True
        )
    except subprocess.CalledProcessError as e:
        print(f"\033[0;31m二维码生成失败: {e}\033[0m")
    except FileNotFoundError:
        print("\033[0;31mqrencode 未安装，请先安装: yum install qrencode\033[0m")


def show_qrcodes(config=None, ip=None):
    """
    为所有协议生成并显示二维码

    Args:
        config: sing-box 配置字典，None 则自动加载
        ip: VPS 公网 IP，None 则自动获取
    """
    if config is None:
        config = load_config()
    if ip is None:
        ip = get_public_ip()

    if not check_qrencode():
        print("\033[0;31mqrencode 未安装，请先安装:\033[0m")
        print("  yum install qrencode")
        print("  或: apt install qrencode")
        return

    links = gen_all_links(config, ip)

    print(f"\n\033[0;36m━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\033[0m")
    print(f"\033[0;32m  二维码 — VPS: {ip}\033[0m")
    print(f"\033[0;36m━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\033[0m")

    protocol_names = {
        'vless': 'VLess-Reality',
        'vmess': 'VMess-WS-TLS',
        'hy2':   'Hysteria2',
        'tuic':  'Tuic5',
        'anytls':'AnyTLS',
    }

    for key, name in protocol_names.items():
        if key in links:
            generate_qrcode_terminal(links[key], f"【{name}】")

    print()


if __name__ == '__main__':
    show_qrcodes()
