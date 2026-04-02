#!/usr/bin/env python3
"""
sb.py — sing-box 管理工具主入口

交互式菜单 + 命令行参数支持
调用各模块完成节点查看、配置生成、服务管理等功能

用法:
    python3 sb.py                # 交互式菜单
    python3 sb.py --nodes        # 查看节点信息
    python3 sb.py --clash        # 生成 Clash 配置
    python3 sb.py --client       # 生成 sing-box 客户端配置
    python3 sb.py --sub          # 导出订阅文件
    python3 sb.py --qr           # 生成二维码
    python3 sb.py --restart      # 重启服务
    python3 sb.py --status       # 查看服务状态
    python3 sb.py --logs         # 查看最近日志
"""

import os
import sys
import subprocess
import argparse

# 确保能导入同目录下的模块
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import load_config, extract_config, get_public_ip, DEFAULT_CONFIG_PATH
from links import gen_all_links
from clash import save_clash_yaml
from client import save_client_config
from subscribe import save_subscription
from qrcode import show_qrcodes
from argo import setup_argo, stop_tunnel as stop_argo, show_argo_status, is_tunnel_running
from warp import setup_warp, show_warp_status, remove_warp_from_config

# 颜色
class C:
    RED    = '\033[0;31m'
    GREEN  = '\033[0;32m'
    YELLOW = '\033[1;33m'
    BLUE   = '\033[0;34m'
    CYAN   = '\033[0;36m'
    NC     = '\033[0m'

OUTPUT_DIR = "/etc/s-box-sn/output"
SERVICE_NAME = "sing-box"


def header(title):
    """打印带颜色的标题"""
    print(f"\n{C.CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{C.NC}")
    print(f"{C.GREEN}  {title}{C.NC}")
    print(f"{C.CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{C.NC}")


def show_nodes():
    """查看节点信息"""
    config = load_config()
    info = extract_config(config)
    ip = get_public_ip()
    links = gen_all_links(config, ip)

    header(f"节点信息 — VPS: {ip}")

    names = {
        'vless':     ('VLess-Reality', info['vless']['port']),
        'vmess':     ('VMess-WS-TLS', info['vmess']['port']),
        'hysteria2': ('Hysteria2', info['hysteria2']['port']),
        'tuic':      ('Tuic5', info['tuic']['port']),
        'anytls':    ('AnyTLS', info['anytls']['port']),
    }

    # 链接字典可能用不同键名，建立映射
    link_map = {
        'vless': 'VLess-Reality',
        'vmess': 'VMess-WS',
        'hysteria2': 'Hysteria2',
        'tuic': 'Tuic5',
        'anytls': 'AnyTLS',
    }

    for i, (key, (name, port)) in enumerate(names.items(), 1):
        lk = link_map.get(key, key)
        link = links.get(lk, links.get(key, links.get(name, 'N/A')))
        print(f"\n{C.BLUE}{'①②③④⑤'[i-1]} {name} (端口 {port}){C.NC}")
        print(f"   {link}")

    # Base64 订阅
    header("Base64 订阅")
    all_text = '\n'.join(links.values())
    import base64
    sub_b64 = base64.b64encode(all_text.encode()).decode()
    print(sub_b64)
    print(f"\n{C.GREEN}提示: 复制上面的 Base64 内容，可直接导入 v2rayN / NekoBox 等客户端{C.NC}\n")


def service_action(action):
    """systemctl 操作"""
    header(f"{action} sing-box 服务")
    result = subprocess.run(['systemctl', action, SERVICE_NAME], capture_output=True, text=True)
    if result.returncode == 0:
        print(f"{C.GREEN}✓ 服务已 {action}{C.NC}")
    else:
        print(f"{C.RED}✗ 操作失败: {result.stderr.strip()}{C.NC}")
    # 显示状态
    subprocess.run(['systemctl', 'status', SERVICE_NAME, '--no-pager', '-l'], capture_output=False)


def show_status():
    """查看服务状态"""
    header("sing-box 服务状态")
    subprocess.run(['systemctl', 'status', SERVICE_NAME, '--no-pager', '-l'])


def show_logs(lines=50):
    """查看日志"""
    header(f"sing-box 最近日志 ({lines}行)")
    subprocess.run(['journalctl', '-u', SERVICE_NAME, '--no-pager', f'-n{lines}'])


def interactive_menu():
    """交互式主菜单"""
    ip = get_public_ip()
    while True:
        os.system('clear')
        print(f"{C.CYAN}╔══════════════════════════════════════════════╗{C.NC}")
        print(f"{C.CYAN}║{C.GREEN}       sing-box 管理工具 v1.0 (Python)       {C.CYAN}║{C.NC}")
        print(f"{C.CYAN}║{C.YELLOW}       VPS: {ip:<33s}{C.CYAN}║{C.NC}")
        print(f"{C.CYAN}╠══════════════════════════════════════════════╣{C.NC}")
        print(f"{C.CYAN}║{C.NC}  {C.BLUE}[1]{C.NC} 查看节点信息 (分享链接+订阅)         {C.CYAN}║{C.NC}")
        print(f"{C.CYAN}║{C.NC}  {C.BLUE}[2]{C.NC} 生成 Clash/Mihomo 配置 (YAML)         {C.CYAN}║{C.NC}")
        print(f"{C.CYAN}║{C.NC}  {C.BLUE}[3]{C.NC} 生成 sing-box 客户端配置 (JSON)       {C.CYAN}║{C.NC}")
        print(f"{C.CYAN}║{C.NC}  {C.BLUE}[4]{C.NC} 导出订阅文件                          {C.CYAN}║{C.NC}")
        print(f"{C.CYAN}║{C.NC}  {C.BLUE}[5]{C.NC} 生成二维码 (终端显示)                 {C.CYAN}║{C.NC}")
        print(f"{C.CYAN}║{C.NC}  {C.BLUE}[6]{C.NC} 重启 sing-box 服务                    {C.CYAN}║{C.NC}")
        print(f"{C.CYAN}║{C.NC}  {C.BLUE}[7]{C.NC} 停止 sing-box 服务                    {C.CYAN}║{C.NC}")
        print(f"{C.CYAN}║{C.NC}  {C.BLUE}[8]{C.NC} 启动 sing-box 服务                    {C.CYAN}║{C.NC}")
        print(f"{C.CYAN}║{C.NC}  {C.BLUE}[9]{C.NC} 查看服务状态                          {C.CYAN}║{C.NC}")
        print(f"{C.CYAN}║{C.NC}  {C.BLUE}[10]{C.NC} 查看日志 (最近50行)                  {C.CYAN}║{C.NC}")
        print(f"{C.CYAN}║{C.NC}  {C.BLUE}[11]{C.NC} Argo 隧道 - 启动/查看                 {C.CYAN}║{C.NC}")
        print(f"{C.CYAN}║{C.NC}  {C.BLUE}[12]{C.NC} Argo 隧道 - 停止                     {C.CYAN}║{C.NC}")
        print(f"{C.CYAN}║{C.NC}  {C.BLUE}[13]{C.NC} WARP 分流 - 配置/查看                 {C.CYAN}║{C.NC}")
        print(f"{C.CYAN}║{C.NC}  {C.BLUE}[14]{C.NC} WARP 分流 - 移除                     {C.CYAN}║{C.NC}")
        print(f"{C.CYAN}║{C.NC}  {C.BLUE}[0]{C.NC}  退出                                 {C.CYAN}║{C.NC}")
        print(f"{C.CYAN}╚══════════════════════════════════════════════╝{C.NC}")
        print()
        choice = input(f"{C.GREEN}请选择 [0-14]: {C.NC}").strip()

        try:
            if choice == '1':
                show_nodes()
            elif choice == '2':
                config = load_config()
                save_clash_yaml(config, ip, OUTPUT_DIR)
                print(f"\n{C.GREEN}✓ Clash 配置已生成{C.NC}\n")
            elif choice == '3':
                config = load_config()
                save_client_config(config, ip, OUTPUT_DIR)
                print(f"\n{C.GREEN}✓ sing-box 客户端配置已生成{C.NC}\n")
            elif choice == '4':
                config = load_config()
                save_subscription(config, ip, OUTPUT_DIR)
                print(f"\n{C.GREEN}✓ 订阅文件已生成{C.NC}\n")
            elif choice == '5':
                config = load_config()
                show_qrcodes(config, ip)
            elif choice == '6':
                service_action('restart')
            elif choice == '7':
                service_action('stop')
            elif choice == '8':
                service_action('start')
            elif choice == '9':
                show_status()
            elif choice == '10':
                show_logs()
            elif choice == '11':
                if is_tunnel_running():
                    show_argo_status()
                else:
                    config = load_config()
                    setup_argo(config)
            elif choice == '12':
                stop_argo()
                print(f"{C.GREEN}✓ Argo 隧道已停止{C.NC}")
            elif choice == '13':
                status = show_warp_status()
                if status is None:
                    setup_warp()
            elif choice == '14':
                remove_warp_from_config()
                print(f"{C.GREEN}✓ WARP 已移除，请重启 sing-box{C.NC}")
            elif choice == '0':
                print(f"{C.GREEN}再见! 🐱{C.NC}")
                sys.exit(0)
            else:
                print(f"{C.RED}无效选择{C.NC}")
        except Exception as e:
            print(f"\n{C.RED}错误: {e}{C.NC}")

        input(f"\n{C.YELLOW}按回车继续...{C.NC}")


def main():
    parser = argparse.ArgumentParser(description='sing-box 管理工具')
    parser.add_argument('--nodes', action='store_true', help='查看节点信息')
    parser.add_argument('--clash', action='store_true', help='生成 Clash 配置')
    parser.add_argument('--client', action='store_true', help='生成 sing-box 客户端配置')
    parser.add_argument('--sub', action='store_true', help='导出订阅文件')
    parser.add_argument('--qr', action='store_true', help='生成二维码')
    parser.add_argument('--restart', action='store_true', help='重启服务')
    parser.add_argument('--stop', action='store_true', help='停止服务')
    parser.add_argument('--start', action='store_true', help='启动服务')
    parser.add_argument('--status', action='store_true', help='查看服务状态')
    parser.add_argument('--logs', action='store_true', help='查看日志')
    parser.add_argument('--argo', action='store_true', help='启动/查看 Argo 隧道')
    parser.add_argument('--argo-stop', action='store_true', help='停止 Argo 隧道')
    parser.add_argument('--warp', action='store_true', help='配置/查看 WARP 分流')
    parser.add_argument('--warp-remove', action='store_true', help='移除 WARP 分流')
    parser.add_argument('--config', default=DEFAULT_CONFIG_PATH, help='配置文件路径')

    args = parser.parse_args()

    # 命令行模式
    if args.nodes:
        show_nodes()
    elif args.clash:
        config = load_config(args.config)
        save_clash_yaml(config, output_dir=OUTPUT_DIR)
        print(f"{C.GREEN}✓ Clash 配置已生成: {OUTPUT_DIR}/clash-config.yaml{C.NC}")
    elif args.client:
        config = load_config(args.config)
        save_client_config(config, output_dir=OUTPUT_DIR)
        print(f"{C.GREEN}✓ sing-box 客户端配置已生成: {OUTPUT_DIR}/singbox-client.json{C.NC}")
    elif args.sub:
        config = load_config(args.config)
        save_subscription(config, output_dir=OUTPUT_DIR)
        print(f"{C.GREEN}✓ 订阅文件已生成: {OUTPUT_DIR}/subscription.txt{C.NC}")
    elif args.qr:
        config = load_config(args.config)
        show_qrcodes(config)
    elif args.restart:
        service_action('restart')
    elif args.stop:
        service_action('stop')
    elif args.start:
        service_action('start')
    elif args.status:
        show_status()
    elif args.logs:
        show_logs()
    elif args.argo:
        config = load_config(args.config)
        setup_argo(config)
    elif args.argo_stop:
        stop_argo()
        print(f"{C.GREEN}✓ Argo 隧道已停止{C.NC}")
    elif args.warp:
        status = show_warp_status()
        if status is None:
            setup_warp()
    elif args.warp_remove:
        remove_warp_from_config()
        print(f"{C.GREEN}✓ WARP 已移除，请重启 sing-box{C.NC}")
    else:
        # 无参数 → 交互式菜单
        interactive_menu()


if __name__ == '__main__':
    main()
