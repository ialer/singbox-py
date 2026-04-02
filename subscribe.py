#!/usr/bin/env python3
"""
subscribe.py — 订阅生成模块

收集所有协议的分享链接，生成人类可读文本和 Base64 编码订阅。
保存到 /etc/s-box-sn/output/subscription.txt
纯 Python 标准库实现。
"""

import base64
import os
import sys
import datetime

from config import load_config, get_public_ip
from links import gen_all_links


def generate_subscription_text(links, ip):
    """
    生成人类可读的订阅文本。

    参数:
        links (dict): {protocol_name: share_link} 格式
        ip (str): 公网 IP

    返回:
        str: 格式化的订阅文本
    """
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    lines = []
    lines.append("# " + "=" * 60)
    lines.append("# sing-box 订阅文件 — 自动生成")
    lines.append("# 生成时间: {}".format(now))
    lines.append("# VPS: {}".format(ip))
    lines.append("# " + "=" * 60)
    lines.append("")
    lines.append("# --- 分享链接 (原始) ---")
    lines.append("")

    for i, (name, link) in enumerate(links.items(), 1):
        lines.append("[{}] {}:".format(i, name))
        lines.append(link)
        lines.append("")

    return '\n'.join(lines)


def generate_subscription_b64(links):
    """
    生成 Base64 编码的订阅内容（标准订阅格式）。

    参数:
        links (dict): {protocol_name: share_link} 格式

    返回:
        str: Base64 编码的订阅字符串
    """
    raw = '\n'.join(links.values())
    return base64.b64encode(raw.encode('utf-8')).decode('utf-8')


def save_subscription(config=None, ip=None, output_dir="/etc/s-box-sn/output"):
    """
    生成并保存订阅文件。

    参数:
        config (dict, optional): load_config() 返回的配置，为 None 时自动加载
        ip (str, optional): 公网 IP
        output_dir (str): 输出目录

    返回:
        dict: 包含文件路径的字典
    """
    if config is None:
        config = load_config()
    if ip is None:
        ip = get_public_ip()

    os.makedirs(output_dir, exist_ok=True)

    # 生成所有分享链接
    links = gen_all_links(config, ip)

    # 生成可读文本
    text_content = generate_subscription_text(links, ip)

    # 生成 Base64 订阅
    b64_content = generate_subscription_b64(links)

    # 组合最终内容
    final_content = text_content
    final_content += "\n# --- Base64 编码订阅 ---\n\n"
    final_content += b64_content
    final_content += "\n"

    # 保存
    text_path = os.path.join(output_dir, "subscription.txt")
    with open(text_path, 'w', encoding='utf-8') as f:
        f.write(final_content)

    # 单独保存 base64 版本（方便直接导入）
    b64_path = os.path.join(output_dir, "subscription-b64.txt")
    with open(b64_path, 'w', encoding='utf-8') as f:
        f.write(b64_content)

    return {
        'text': text_path,
        'b64': b64_path,
        'links': links,
    }


# ──────────────────── 命令行测试 ────────────────────
if __name__ == '__main__':
    config_path = sys.argv[1] if len(sys.argv) > 1 else None
    try:
        cfg = load_config(config_path) if config_path else load_config()
        ip = get_public_ip()
        result = save_subscription(cfg, ip)
        print("✅ 订阅文件已生成:")
        print("  可读版: {}".format(result['text']))
        print("  Base64版: {}".format(result['b64']))
        print("\n共 {} 个节点:".format(len(result['links'])))
        for name in result['links']:
            print("  - {}".format(name))
    except Exception as e:
        print("❌ 错误: {}".format(e), file=sys.stderr)
        sys.exit(1)
