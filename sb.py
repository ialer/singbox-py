#!/usr/bin/env python3
"""
sb.py - sing-box 管理工具主入口

交互式菜单 + 命令行参数支持
调用各模块完成节点查看、配置生成、服务管理等功能
支持多用户管理

用法:
    python3 sb.py                     # 交互式菜单
    python3 sb.py --nodes             # 查看节点信息（默认用户）
    python3 sb.py --nodes <username>  # 查看指定用户的节点
    python3 sb.py --clash             # 生成 Clash 配置
    python3 sb.py --client            # 生成 sing-box 客户端配置
    python3 sb.py --sub               # 导出订阅文件
    python3 sb.py --qr                # 生成二维码
    python3 sb.py --restart           # 重启服务
    python3 sb.py --status            # 查看服务状态
    python3 sb.py --logs              # 查看最近日志
    python3 sb.py --add-user <name>   # 添加用户
    python3 sb.py --remove-user <name># 删除用户
    python3 sb.py --list-users        # 列出所有用户
"""

import os
import sys
import subprocess
import base64
import argparse

# 确保能导入同目录下的模块
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import (load_config, extract_config, extract_config_for_user,
                    get_public_ip, DEFAULT_CONFIG_PATH, select_protocols,
                    PROTOCOL_NAMES, get_config_protocols)
from links import gen_all_links, gen_links_for_user, gen_links_for_protocols
from clash import (save_clash_yaml, save_clash_yaml_for_user,
                   save_clash_yaml_for_protocols)
from client import save_client_config
from subscribe import save_subscription
from qrcode import show_qrcodes
from users import (load_users, list_users, add_user, remove_user, rename_user, rename_user,
                   get_user_by_name, restart_singbox)
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
    print("{}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{}".format(C.CYAN, C.NC))
    print("{}  {}{}".format(C.GREEN, title, C.NC))
    print("{}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{}".format(C.CYAN, C.NC))


def _display_links(links, ip, user_tag=""):
    """格式化显示链接和 Base64 订阅"""
    tag_str = " ({})".format(user_tag) if user_tag else ""
    header("节点信息{} - VPS: {}".format(tag_str, ip))

    idx = 1
    symbols = ['1', '2', '3', '4', '5']
    for name, link in links.items():
        sym = symbols[idx - 1] if idx <= len(symbols) else str(idx)
        print("\n{}{} {}{}".format(C.BLUE, sym, name, C.NC))
        print("   {}".format(link))
        idx += 1

    # Base64 订阅
    header("Base64 订阅")
    all_text = '\n'.join(links.values())
    sub_b64 = base64.b64encode(all_text.encode()).decode()
    print(sub_b64)
    # 显示订阅URL
    argo_domain = ''
    try:
        with open('/etc/s-box-sn/argo-sub-domain.txt', 'r') as f:
            argo_domain = f.read().strip()
    except:
        pass

    if argo_domain:
        print()
        print("  " + "-" * 48)
        print("    \u8ba2\u9605 URL (\u9690\u85cfIP)")
        print("  " + "-" * 48)
        uname = user_tag if user_tag else 'default'
        sub_url = "https://" + argo_domain + "/sub/" + uname
        clash_url = "https://" + argo_domain + "/clash/" + uname
        print("    \u4e00\u952e\u5bfc\u5165: " + sub_url)
        print("    Clash: " + clash_url)
        print("    \u5ba2\u6237\u7aef\u7c98\u8d34URL\u5373\u53ef\u5bfc\u5165\u5168\u90e8\u534f\u8bae")

    print("\n{}提示: 复制上面的 Base64 内容，可直接导入 v2rayN / NekoBox 等客户端{}\n".format(C.GREEN, C.NC))


def show_nodes(username=None):
    """
    查看节点信息。

    参数:
        username (str, optional): 指定用户名，None 表示默认用户
    """
    config = load_config()
    ip = get_public_ip()

    if username:
        user = get_user_by_name(username)
        if not user:
            print("{}用户 '{}' 不存在{}".format(C.RED, username, C.NC))
            return
        links = gen_links_for_user(config, user, ip)
        _display_links(links, ip, user_tag=username)
    else:
        # 显示默认用户 + 列出所有用户
        links = gen_all_links(config, ip)
        users = list_users()
        _display_links(links, ip, user_tag="default")

        if len(users) > 1:
            header("其他用户")
            for u in users:
                if u['name'] != 'default':
                    print("  {}- {} (UUID: {}...){}".format(
                        C.CYAN, u['name'], u['uuid'][:8], C.NC))


def show_user_menu():
    """用户管理子菜单"""
    while True:
        header("用户管理")
        users = list_users()
        print("当前用户 (共 {} 人):".format(len(users)))
        for u in users:
            tag = " [默认]" if u['name'] == 'default' else ""
            print("  {}{}{}{}".format(C.CYAN, u['name'], tag, C.NC))
            print("    UUID: {}".format(u['uuid']))

        print("\n{}[1]{} 添加用户".format(C.BLUE, C.NC))
        print("{}[2]{} 删除用户".format(C.BLUE, C.NC))
        print("{}[3]{} 查看用户链接".format(C.BLUE, C.NC))
        print("{}[4]{} 生成用户 Clash 配置".format(C.BLUE, C.NC))
        print("{}[5]{} 重命名用户".format(C.BLUE, C.NC))
        print("{}[0]{} 返回主菜单".format(C.BLUE, C.NC))

        choice = input("\n{}请选择 [0-5]: {}".format(C.GREEN, C.NC)).strip()

        if choice == '1':
            name = input("输入用户名: ").strip()
            if not name:
                print("{}用户名不能为空{}".format(C.RED, C.NC))
                continue
            user = add_user(name)
            if user:
                print("{}用户 '{}' 已添加{}".format(C.GREEN, name, C.NC))
                print("  UUID: {}".format(user['uuid']))
                # 重启 sing-box
                print("正在重启 sing-box...")
                if restart_singbox():
                    print("{}sing-box 已重启{}".format(C.GREEN, C.NC))
                else:
                    print("{}sing-box 重启失败，请手动重启{}".format(C.RED, C.NC))

        elif choice == '2':
            name = input("输入要删除的用户名: ").strip()
            if not name:
                continue
            if name == 'default':
                print("{}不能删除默认用户{}".format(C.RED, C.NC))
                continue
            confirm = input("确认删除用户 '{}'? (y/N): ".format(name)).strip().lower()
            if confirm == 'y':
                if remove_user(name):
                    print("{}用户 '{}' 已删除{}".format(C.GREEN, name, C.NC))
                    print("正在重启 sing-box...")
                    if restart_singbox():
                        print("{}sing-box 已重启{}".format(C.GREEN, C.NC))
                else:
                    print("{}删除失败{}".format(C.RED, C.NC))

        elif choice == '3':
            name = input("输入用户名 (留空=默认): ").strip()
            config = load_config()
            ip = get_public_ip()
            if name:
                user = get_user_by_name(name)
                if not user:
                    print("{}用户 '{}' 不存在{}".format(C.RED, name, C.NC))
                    continue
                links = gen_links_for_user(config, user, ip)
                _display_links(links, ip, user_tag=name)
            else:
                links = gen_all_links(config, ip)
                _display_links(links, ip, user_tag="default")

        elif choice == '4':
            name = input("输入用户名 (留空=默认): ").strip()
            config = load_config()
            ip = get_public_ip()
            if name:
                user = get_user_by_name(name)
                if not user:
                    print("{}用户 '{}' 不存在{}".format(C.RED, name, C.NC))
                    continue
                protocols = select_protocols(config)
                if protocols:
                    path = save_clash_yaml_for_protocols(config, user, protocols, ip, OUTPUT_DIR)
                else:
                    path = save_clash_yaml_for_user(config, user, ip, OUTPUT_DIR)
                print("{}Clash 配置已生成: {}{}".format(C.GREEN, path, C.NC))
            else:
                save_clash_yaml(config, ip, OUTPUT_DIR)
                print("{}Clash 配置已生成{}".format(C.GREEN, C.NC))

        elif choice == '5':
            old_name = input("输入当前用户名: ").strip()
            if not old_name:
                continue
            if old_name == 'default':
                print("{}不能重命名默认用户{}".format(C.RED, C.NC))
                continue
            user = get_user_by_name(old_name)
            if not user:
                print("{}用户 '{}' 不存在{}".format(C.RED, old_name, C.NC))
                continue
            new_name = input("输入新用户名: ").strip()
            if not new_name:
                continue
            if get_user_by_name(new_name):
                print("{}用户名 '{}' 已存在{}".format(C.RED, new_name, C.NC))
                continue
            if rename_user(old_name, new_name):
                print("{}已重命名: {} -> {}{}".format(C.GREEN, old_name, new_name, C.NC))
                print("正在重启 sing-box...")
                if restart_singbox():
                    print("{}sing-box 已重启{}".format(C.GREEN, C.NC))
            else:
                print("{}重命名失败{}".format(C.RED, C.NC))

        elif choice == '0':
            return

        input("\n{}按回车继续...{}".format(C.YELLOW, C.NC))


def service_action(action):
    """systemctl 操作"""
    header("{} sing-box 服务".format(action))
    result = subprocess.run(['systemctl', action, SERVICE_NAME], stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
    if result.returncode == 0:
        print("{}服务已 {}{}".format(C.GREEN, action, C.NC))
    else:
        print("{}操作失败: {}{}".format(C.RED, result.stderr.strip(), C.NC))
    subprocess.run(['systemctl', 'status', SERVICE_NAME, '--no-pager', '-l'], stdout=None, stderr=None)


def show_status():
    """查看服务状态"""
    header("sing-box 服务状态")
    subprocess.run(['systemctl', 'status', SERVICE_NAME, '--no-pager', '-l'])


def show_logs(lines=50):
    """查看日志"""
    header("sing-box 最近日志 ({}行)".format(lines))
    subprocess.run(['journalctl', '-u', SERVICE_NAME, '--no-pager', '-n{}'.format(lines)])


def interactive_menu():
    """交互式主菜单"""
    ip = get_public_ip()
    while True:
        os.system('clear')
        print("{}╔══════════════════════════════════════════════╗{}".format(C.CYAN, C.NC))
        print("{}║{}       sing-box 管理工具 v1.1 (Python)       {}║{}".format(C.CYAN, C.GREEN, C.CYAN, C.NC))
        print("{}║{}       VPS: {:<33s}{}║{}".format(C.CYAN, C.YELLOW, ip, C.CYAN, C.NC))
        print("{}╠══════════════════════════════════════════════╣{}".format(C.CYAN, C.NC))
        print("{}║{}  {}[1]{}  查看节点信息 (分享链接+订阅)         {}║{}".format(C.CYAN, C.NC, C.BLUE, C.NC, C.CYAN, C.NC))
        print("{}║{}  {}[2]{}  生成 Clash/Mihomo 配置 (YAML)         {}║{}".format(C.CYAN, C.NC, C.BLUE, C.NC, C.CYAN, C.NC))
        print("{}║{}  {}[3]{}  生成 sing-box 客户端配置 (JSON)       {}║{}".format(C.CYAN, C.NC, C.BLUE, C.NC, C.CYAN, C.NC))
        print("{}║{}  {}[4]{}  导出订阅文件                          {}║{}".format(C.CYAN, C.NC, C.BLUE, C.NC, C.CYAN, C.NC))
        print("{}║{}  {}[5]{}  生成二维码 (终端显示)                 {}║{}".format(C.CYAN, C.NC, C.BLUE, C.NC, C.CYAN, C.NC))
        print("{}║{}  {}[6]{}  重启 sing-box 服务                    {}║{}".format(C.CYAN, C.NC, C.BLUE, C.NC, C.CYAN, C.NC))
        print("{}║{}  {}[7]{}  停止 sing-box 服务                    {}║{}".format(C.CYAN, C.NC, C.BLUE, C.NC, C.CYAN, C.NC))
        print("{}║{}  {}[8]{}  启动 sing-box 服务                    {}║{}".format(C.CYAN, C.NC, C.BLUE, C.NC, C.CYAN, C.NC))
        print("{}║{}  {}[9]{}  查看服务状态                          {}║{}".format(C.CYAN, C.NC, C.BLUE, C.NC, C.CYAN, C.NC))
        print("{}║{}  {}[10]{} 查看日志 (最近50行)                  {}║{}".format(C.CYAN, C.NC, C.BLUE, C.NC, C.CYAN, C.NC))
        print("{}║{}  {}[11]{} Argo 隧道 - 启动/查看                 {}║{}".format(C.CYAN, C.NC, C.BLUE, C.NC, C.CYAN, C.NC))
        print("{}║{}  {}[12]{} Argo 隧道 - 停止                     {}║{}".format(C.CYAN, C.NC, C.BLUE, C.NC, C.CYAN, C.NC))
        print("{}║{}  {}[13]{} WARP 分流 - 配置/查看                 {}║{}".format(C.CYAN, C.NC, C.BLUE, C.NC, C.CYAN, C.NC))
        print("{}║{}  {}[14]{} WARP 分流 - 移除                     {}║{}".format(C.CYAN, C.NC, C.BLUE, C.NC, C.CYAN, C.NC))
        print("{}║{}  {}[15]{} 用户管理 (添加/删除/查看)             {}║{}".format(C.CYAN, C.NC, C.BLUE, C.NC, C.CYAN, C.NC))
        print("{}║{}  {}[0]{}  退出                                 {}║{}".format(C.CYAN, C.NC, C.BLUE, C.NC, C.CYAN, C.NC))
        print("{}╚══════════════════════════════════════════════╝{}".format(C.CYAN, C.NC))
        print()
        choice = input("{}请选择 [0-15]: {}".format(C.GREEN, C.NC)).strip()

        try:
            if choice == '1':
                name = input("输入用户名 (留空=查看所有): ").strip()
                show_nodes(username=name if name else None)
            elif choice == '2':
                config = load_config()
                # 选择用户
                users = list_users()
                print("\n选择用户:")
                for i, u in enumerate(users):
                    print("  [{}] {}".format(i + 1, u['name']))
                user_choice = input("选择用户编号 (留空=默认): ").strip()
                if user_choice and user_choice.isdigit():
                    idx = int(user_choice) - 1
                    if 0 <= idx < len(users):
                        user = users[idx]
                    else:
                        user = users[0]
                else:
                    user = users[0]

                # 选择协议
                protocols = select_protocols(config)
                if protocols:
                    path = save_clash_yaml_for_protocols(config, user, protocols, ip, OUTPUT_DIR)
                else:
                    path = save_clash_yaml_for_user(config, user, ip, OUTPUT_DIR)
                print("\n{}Clash 配置已生成: {}{}".format(C.GREEN, path, C.NC))
            elif choice == '3':
                config = load_config()
                users = list_users()
                print("\n选择用户:")
                for i, u in enumerate(users):
                    print("  [{}] {}".format(i + 1, u['name']))
                user_choice = input("选择用户编号 (留空=默认): ").strip()
                if user_choice and user_choice.isdigit():
                    idx = int(user_choice) - 1
                    user = users[idx] if 0 <= idx < len(users) else users[0]
                else:
                    user = users[0]
                path = save_client_config_for_user(config, user, OUTPUT_DIR)
                print("\n{}sing-box 客户端配置已生成: {}{}".format(C.GREEN, path, C.NC))
            elif choice == '4':
                config = load_config()
                users = list_users()
                print("\n选择用户:")
                for i, u in enumerate(users):
                    print("  [{}] {}".format(i + 1, u['name']))
                user_choice = input("选择用户编号 (留空=默认): ").strip()
                if user_choice and user_choice.isdigit():
                    idx = int(user_choice) - 1
                    user = users[idx] if 0 <= idx < len(users) else users[0]
                else:
                    user = users[0]
                txt, b64 = save_subscription_for_user(config, user, OUTPUT_DIR)
                print("\n{}订阅文件已生成: {}{}".format(C.GREEN, txt, C.NC))
            elif choice == '5':
                config = load_config()
                users = list_users()
                print("\n选择用户:")
                for i, u in enumerate(users):
                    print("  [{}] {}".format(i + 1, u['name']))
                user_choice = input("选择用户编号 (留空=默认): ").strip()
                if user_choice and user_choice.isdigit():
                    idx = int(user_choice) - 1
                    user = users[idx] if 0 <= idx < len(users) else users[0]
                else:
                    user = users[0]
                show_qrcodes_for_user(config, user, ip)
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
                print("{}Argo 隧道已停止{}".format(C.GREEN, C.NC))
            elif choice == '13':
                status = show_warp_status()
                if status is None:
                    setup_warp()
            elif choice == '14':
                remove_warp_from_config()
                print("{}WARP 已移除，请重启 sing-box{}".format(C.GREEN, C.NC))
            elif choice == '15':
                show_user_menu()
            elif choice == '0':
                print("{}再见! {}".format(C.GREEN, C.NC))
                sys.exit(0)
            else:
                print("{}无效选择{}".format(C.RED, C.NC))
        except Exception as e:
            print("\n{}错误: {}{}".format(C.RED, e, C.NC))

        input("\n{}按回车继续...{}".format(C.YELLOW, C.NC))


def main():
    parser = argparse.ArgumentParser(description='sing-box 管理工具')
    parser.add_argument('--nodes', nargs='?', const='', default=None, metavar='USER',
                        help='查看节点信息 (可指定用户名)')
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
    parser.add_argument('--add-user', metavar='NAME', help='添加用户')
    parser.add_argument('--remove-user', metavar='NAME', help='删除用户')
    parser.add_argument('--list-users', action='store_true', help='列出所有用户')
    parser.add_argument('--config', default=DEFAULT_CONFIG_PATH, help='配置文件路径')

    args = parser.parse_args()

    # 用户管理命令行
    if args.add_user:
        user = add_user(args.add_user)
        if user:
            print("用户 '{}' 已添加".format(user['name']))
            print("  UUID: {}".format(user['uuid']))
            print("正在重启 sing-box...")
            if restart_singbox():
                print("sing-box 已重启")
        sys.exit(0)

    if args.remove_user:
        if remove_user(args.remove_user):
            print("用户 '{}' 已删除".format(args.remove_user))
            print("正在重启 sing-box...")
            if restart_singbox():
                print("sing-box 已重启")
        sys.exit(0)

    if args.list_users:
        users = list_users()
        print("用户列表 (共 {} 人):".format(len(users)))
        for u in users:
            tag = " [默认]" if u['name'] == 'default' else ""
            print("  {}{} - UUID: {}".format(u['name'], tag, u['uuid']))
        sys.exit(0)

    # 其他命令行模式
    if args.nodes is not None:
        username = args.nodes if args.nodes else None
        show_nodes(username=username)
    elif args.clash:
        config = load_config(args.config)
        users = list_users()
        user = users[0] if users else {"name": "default", "uuid": "", "password": ""}
        protocols = get_config_protocols(config)
        path = save_clash_yaml_for_protocols(config, user, protocols, output_dir=OUTPUT_DIR)
        print("Clash 配置已生成: {}".format(path))
    elif args.client:
        config = load_config(args.config)
        save_client_config(config, output_dir=OUTPUT_DIR)
        print("sing-box 客户端配置已生成")
    elif args.sub:
        config = load_config(args.config)
        save_subscription(config, output_dir=OUTPUT_DIR)
        print("订阅文件已生成")
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
        print("Argo 隧道已停止")
    elif args.warp:
        status = show_warp_status()
        if status is None:
            setup_warp()
    elif args.warp_remove:
        remove_warp_from_config()
        print("WARP 已移除，请重启 sing-box")
    else:
        # 无参数 -> 交互式菜单
        interactive_menu()


if __name__ == '__main__':
    main()
