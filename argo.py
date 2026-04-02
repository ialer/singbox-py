#!/usr/bin/env python3
"""
argo.py — Cloudflare Argo 隧道管理模块

实现原理：
1. cloudflared 在 VPS 上运行，把本地 VMess WS 端口暴露给 Cloudflare 网络
2. 客户端连接的是 *.trycloudflare.com（临时）或自定义域名（固定）
3. TLS 由 Cloudflare 终结，VMess 本地不开 TLS
4. 客户端的 VMess 地址 = Argo 域名，端口 = 443/8443

两种模式：
- 临时隧道：零配置，重启后域名会变
- 固定隧道：需要 CF 账号 + 域名，域名固定
"""

import os
import sys
import json
import time
import base64
import subprocess
import signal
import re

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import load_config, extract_config, get_public_ip, DEFAULT_SNI

CLOUDFLARED_BIN = "/usr/local/bin/cloudflared"
ARGO_LOG = "/etc/s-box-sn/argo.log"
ARGO_PID_FILE = "/etc/s-box-sn/argo.pid"


def check_cloudflared():
    """检查 cloudflared 是否安装"""
    if os.path.isfile(CLOUDFLARED_BIN) and os.access(CLOUDFLARED_BIN, os.X_OK):
        return True
    # 尝试 PATH 中查找
    try:
        subprocess.run(['which', 'cloudflared'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def install_cloudflared():
    """安装 cloudflared"""
    print("正在下载 cloudflared...")
    arch = os.uname().machine
    if arch == 'x86_64':
        url = "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64"
    elif arch == 'aarch64':
        url = "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-arm64"
    else:
        raise RuntimeError(f"不支持的架构: {arch}")

    result = subprocess.run(
        ['curl', '-L', '-o', CLOUDFLARED_BIN, url],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True
    )
    if result.returncode != 0:
        raise RuntimeError(f"下载失败: {result.stderr}")

    os.chmod(CLOUDFLARED_BIN, 0o755)
    print(f"✓ cloudflared 安装成功: {get_cloudflared_version()}")


def get_cloudflared_version():
    """获取 cloudflared 版本"""
    try:
        result = subprocess.run(
            [CLOUDFLARED_BIN, '--version'],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True, timeout=5
        )
        # 输出格式: cloudflared version 2026.3.0 (built 2026-03-09-14:08 UTC)
        match = re.search(r'version (\S+)', result.stdout)
        return match.group(1) if match else 'unknown'
    except Exception:
        return 'unknown'


def is_tunnel_running():
    """检查隧道是否在运行"""
    try:
        result = subprocess.run(
            ['pgrep', '-f', 'cloudflared.*tunnel'],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True
        )
        return bool(result.stdout.strip())
    except Exception:
        return False


def stop_tunnel():
    """停止隧道"""
    if not is_tunnel_running():
        return False

    try:
        result = subprocess.run(
            ['pkill', '-f', 'cloudflared.*tunnel'],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True
        )
        time.sleep(1)
        # 清理 PID 文件
        if os.path.exists(ARGO_PID_FILE):
            os.remove(ARGO_PID_FILE)
        return True
    except Exception:
        return False


def start_quick_tunnel(local_port):
    """
    启动临时隧道

    原理：
    - cloudflared 向 CF 注册一个随机域名
    - 把本地端口通过该域名暴露到公网
    - 重启后域名会变

    参数:
        local_port: 本地 VMess WS 端口

    返回:
        str: trycloudflare.com 域名
    """
    if not check_cloudflared():
        install_cloudflared()

    # 先停止已有的隧道
    stop_tunnel()

    # 启动新隧道
    cmd = [
        CLOUDFLARED_BIN, 'tunnel',
        '--url', f'http://127.0.0.1:{local_port}',
        '--no-autoupdate',
        '--logfile', ARGO_LOG,
        '--loglevel', 'info'
    ]

    # 后台启动
    with open(ARGO_LOG, 'w') as log:
        proc = subprocess.Popen(cmd, stdout=log, stderr=log)

    # 保存 PID
    with open(ARGO_PID_FILE, 'w') as f:
        f.write(str(proc.pid))

    # 等待域名生成（最多30秒）
    domain = None
    for _ in range(30):
        time.sleep(1)
        if os.path.exists(ARGO_LOG):
            with open(ARGO_LOG, 'r') as f:
                content = f.read()
            match = re.search(r'https://([a-z0-9-]+\.trycloudflare\.com)', content)
            if match:
                domain = match.group(1)
                break

    if not domain:
        raise RuntimeError("隧道创建超时，请检查日志: " + ARGO_LOG)

    return domain


def get_tunnel_domain():
    """从日志获取当前隧道域名"""
    if not os.path.exists(ARGO_LOG):
        return None
    with open(ARGO_LOG, 'r') as f:
        content = f.read()
    match = re.search(r'https://([a-z0-9-]+\.trycloudflare\.com)', content)
    return match.group(1) if match else None


def gen_argo_vmess_link(uuid, domain, ws_path, port=8443):
    """
    生成 VMess + Argo 的分享链接

    注意：地址用 Argo 域名，不是 VPS IP
    端口用 CF 标准端口（8443 TLS / 8880 非 TLS）

    参数:
        uuid: VMess UUID
        domain: Argo 域名 (trycloudflare.com)
        ws_path: WebSocket 路径
        port: CF 端口（默认 8443 TLS）

    返回:
        str: vmess:// 链接
    """
    vmess_obj = {
        "v": "2",
        "ps": f"VMess-Argo-{domain}",
        "add": domain,
        "port": str(port),
        "id": uuid,
        "aid": "0",
        "scy": "auto",
        "net": "ws",
        "type": "none",
        "host": domain,
        "path": ws_path,
        "tls": "tls",
        "sni": domain,
        "fp": "chrome",
        "alpn": ""
    }
    encoded = base64.b64encode(json.dumps(vmess_obj).encode()).decode()
    return f"vmess://{encoded}"


def setup_argo(config=None):
    """
    完整的 Argo 隧道设置流程

    1. 从配置获取 VMess 端口
    2. 启动 cloudflared 临时隧道
    3. 获取隧道域名
    4. 生成 Argo VMess 链接

    参数:
        config: sing-box 配置字典

    返回:
        dict: 包含 domain, vmess_link, status 等信息
    """
    if config is None:
        config = load_config()

    info = extract_config(config)
    vmess_port = info['vmess']['port']
    uuid = info['vless']['uuid']
    ws_path = info['vmess']['path']

    print(f"启动 Argo 隧道 → 本地 VMess 端口 {vmess_port}...")

    if is_tunnel_running():
        domain = get_tunnel_domain()
        if domain:
            print(f"✓ 隧道已在运行: {domain}")
        else:
            stop_tunnel()
            domain = start_quick_tunnel(vmess_port)
    else:
        domain = start_quick_tunnel(vmess_port)

    vmess_link_tls = gen_argo_vmess_link(uuid, domain, ws_path, port=8443)
    vmess_link_nontls = gen_argo_vmess_link(uuid, domain, ws_path, port=8880)

    result = {
        'domain': domain,
        'vmess_link_tls': vmess_link_tls,
        'vmess_link_nontls': vmess_link_nontls,
        'status': 'running',
        'vmess_port': vmess_port
    }

    # 保存到文件
    with open('/etc/s-box-sn/argo-domain.txt', 'w') as f:
        f.write(domain)

    print(f"\n✓ Argo 隧道已建立")
    print(f"  域名: {domain}")
    print(f"  TLS 端口: 8443")
    print(f"  非 TLS 端口: 8880")
    print(f"\nVMess + Argo 分享链接 (TLS):")
    print(f"  {vmess_link_tls}")

    return result


def show_argo_status():
    """显示 Argo 隧道状态"""
    if not is_tunnel_running():
        print("Argo 隧道未运行")
        return None

    domain = get_tunnel_domain()
    if domain:
        print(f"Argo 隧道运行中")
        print(f"  域名: {domain}")
        return domain
    else:
        print("隧道进程在运行但域名未获取到")
        return None


if __name__ == '__main__':
    if len(sys.argv) > 1:
        cmd = sys.argv[1]
        if cmd == 'start':
            setup_argo()
        elif cmd == 'stop':
            stop_tunnel()
            print("隧道已停止")
        elif cmd == 'status':
            show_argo_status()
        elif cmd == 'restart':
            stop_tunnel()
            setup_argo()
        else:
            print(f"用法: python3 {sys.argv[0]} [start|stop|status|restart]")
    else:
        # 默认：显示状态或启动
        if is_tunnel_running():
            show_argo_status()
        else:
            setup_argo()
