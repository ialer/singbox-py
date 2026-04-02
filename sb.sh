#!/bin/bash
# ============================================================
# sb.sh — sing-box 主管理脚本
# 功能: 查看节点信息、生成配置文件、管理服务
# 兼容: AlmaLinux 8 / CentOS 8
# ============================================================

set -euo pipefail

# ------------------- 全局变量 -------------------
CONFIG_DIR="/etc/s-box-sn"
CONFIG_FILE="${CONFIG_DIR}/sb.json"
SERVICE_NAME="sing-box"
OUTPUT_DIR="${CONFIG_DIR}/output"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# ------------------- 工具函数 -------------------

# 打印带颜色的标题
print_header() {
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${GREEN}  $1${NC}"
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
}

# 打印信息行
print_info() {
    echo -e "${YELLOW}[$1]${NC} $2"
}

# 打印错误
print_error() {
    echo -e "${RED}[错误] $1${NC}" >&2
}

# 检查依赖工具
check_deps() {
    local deps=("jq" "curl")
    for dep in "${deps[@]}"; do
        if ! command -v "$dep" &>/dev/null; then
            print_error "缺少依赖: $dep，请先安装"
            exit 1
        fi
    done
    if [[ ! -f "$CONFIG_FILE" ]]; then
        print_error "配置文件不存在: $CONFIG_FILE"
        exit 1
    fi
}

# 从配置文件读取值（null 时返回空）
read_config() {
    local val
    val=$(jq -r "$1" "$CONFIG_FILE")
    [[ "$val" == "null" ]] && val=""
    echo "$val"
}

# 获取 VPS 公网 IP
get_public_ip() {
    local ip
    ip=$(curl -s4 --max-time 5 ifconfig.me 2>/dev/null || curl -s4 --max-time 5 ip.sb 2>/dev/null || echo "")
    if [[ -z "$ip" ]]; then
        # 从配置的 listen 地址推断不了，使用已知 IP
        ip="96.44.141.123"
    fi
    echo "$ip"
}

# 获取 SNI (用于 VMess/Hysteria2/Tuic5/AnyTLS)
get_sni() {
    # 从 vmess 的 tls.server_name 获取
    read_config '.inbounds[] | select(.type=="vmess") | .tls.server_name'
}

# ------------------- 读取配置 -------------------

load_config() {
    # 基础信息
    UUID=$(read_config '.inbounds[0].users[0].uuid')
    PUBLIC_IP=$(get_public_ip)
    SNI=$(get_sni)

    # VLESS-Reality
    VLESS_PORT=$(read_config '.inbounds[] | select(.type=="vless") | .listen_port')
    VLESS_SNI=$(read_config '.inbounds[] | select(.type=="vless") | .tls.server_name')
    VLESS_PRIVATE_KEY=$(read_config '.inbounds[] | select(.type=="vless") | .tls.reality.private_key')
    VLESS_SHORT_ID=$(read_config '.inbounds[] | select(.type=="vless") | .tls.reality.short_id[0]')
    # Public key 需要从 private key 推导，这里使用已知值
    VLESS_PUBLIC_KEY="mayeSAHMUyw96197nxS9QzuGj5R0B3WGcAmKhpR7e0Y"

    # VMess-WS
    VMESS_PORT=$(read_config '.inbounds[] | select(.type=="vmess") | .listen_port')
    VMESS_PATH=$(read_config '.inbounds[] | select(.type=="vmess") | .transport.path')
    VMESS_SNI=$(read_config '.inbounds[] | select(.type=="vmess") | .tls.server_name')

    # Hysteria2
    HY2_PORT=$(read_config '.inbounds[] | select(.type=="hysteria2") | .listen_port')
    HY2_SNI=$(read_config '.inbounds[] | select(.type=="hysteria2") | .tls.server_name')
    [[ -z "$HY2_SNI" ]] && HY2_SNI="racknerd-9edcd3"
    HY2_PASSWORD=$(read_config '.inbounds[] | select(.type=="hysteria2") | .users[0].password')

    # TUIC5
    TUIC_PORT=$(read_config '.inbounds[] | select(.type=="tuic") | .listen_port')
    TUIC_SNI=$(read_config '.inbounds[] | select(.type=="tuic") | .tls.server_name')
    [[ -z "$TUIC_SNI" ]] && TUIC_SNI="racknerd-9edcd3"
    TUIC_PASSWORD=$(read_config '.inbounds[] | select(.type=="tuic") | .users[0].password')
    TUIC_CC=$(read_config '.inbounds[] | select(.type=="tuic") | .congestion_control')

    # AnyTLS
    ANYTLS_PORT=$(read_config '.inbounds[] | select(.type=="anytls") | .listen_port')
    ANYTLS_SNI=$(read_config '.inbounds[] | select(.type=="anytls") | .tls.server_name')
    [[ -z "$ANYTLS_SNI" ]] && ANYTLS_SNI="racknerd-9edcd3"
    ANYTLS_PASSWORD=$(read_config '.inbounds[] | select(.type=="anytls") | .users[0].password')

    # 证书路径
    CERT_PATH=$(read_config '.inbounds[2].tls.certificate_path')
    KEY_PATH=$(read_config '.inbounds[2].tls.key_path')
}

# ------------------- 分享链接生成 -------------------

# 生成 VLESS-Reality 分享链接
gen_vless_link() {
    local uuid="$1" ip="$2" port="$3" sni="$4" pbk="$5" sid="$6"
    echo "vless://${uuid}@${ip}:${port}?encryption=none&flow=xtls-rprx-vision&security=reality&sni=${sni}&fp=chrome&pbk=${pbk}&sid=${sid}&type=tcp#VLess-Reality-${ip}"
}

# 生成 VMess 分享链接 (base64 编码的 JSON)
gen_vmess_link() {
    local uuid="$1" ip="$2" port="$3" sni="$4" path="$5"
    local vmess_json
    vmess_json=$(cat <<EOJSON
{
  "v": "2",
  "ps": "VMess-WS-${ip}",
  "add": "${ip}",
  "port": "${port}",
  "id": "${uuid}",
  "aid": "0",
  "scy": "auto",
  "net": "ws",
  "type": "none",
  "host": "",
  "path": "${path}",
  "tls": "tls",
  "sni": "${sni}",
  "alpn": "",
  "fp": ""
}
EOJSON
)
    echo "vmess://$(echo -n "$vmess_json" | base64 -w 0)"
}

# 生成 Hysteria2 分享链接
gen_hy2_link() {
    local ip="$1" port="$2" sni="$3" password="$4"
    echo "hysteria2://${password}@${ip}:${port}?sni=${sni}&insecure=1#Hysteria2-${ip}"
}

# 生成 TUIC5 分享链接
gen_tuic_link() {
    local uuid="$1" password="$2" ip="$3" port="$4" sni="$5"
    echo "tuic://${uuid}:${password}@${ip}:${port}?congestion_control=bbr&sni=${sni}&insecure=1&udp_relay_mode=native#Tuic5-${ip}"
}

# 生成 AnyTLS 分享链接
gen_anytls_link() {
    local password="$1" ip="$2" port="$3" sni="$4"
    echo "anytls://${password}@${ip}:${port}?insecure=1&sni=${sni}#AnyTLS-${ip}"
}

# ------------------- 功能 1: 查看节点信息 -------------------

show_nodes() {
    load_config
    echo ""
    print_header "节点信息 — VPS: ${PUBLIC_IP}"
    echo ""

    local vless_link vmess_link hy2_link tuic_link anytls_link
    vless_link=$(gen_vless_link "$UUID" "$PUBLIC_IP" "$VLESS_PORT" "$VLESS_SNI" "$VLESS_PUBLIC_KEY" "$VLESS_SHORT_ID")
    vmess_link=$(gen_vmess_link "$UUID" "$PUBLIC_IP" "$VMESS_PORT" "$VMESS_SNI" "$VMESS_PATH")
    hy2_link=$(gen_hy2_link "$PUBLIC_IP" "$HY2_PORT" "$HY2_SNI" "$HY2_PASSWORD")
    tuic_link=$(gen_tuic_link "$UUID" "$TUIC_PASSWORD" "$PUBLIC_IP" "$TUIC_PORT" "$TUIC_SNI")
    anytls_link=$(gen_anytls_link "$ANYTLS_PASSWORD" "$PUBLIC_IP" "$ANYTLS_PORT" "$ANYTLS_SNI")

    echo -e "${BLUE}① VLess-Reality (端口 ${VLESS_PORT})${NC}"
    echo "   $vless_link"
    echo ""
    echo -e "${BLUE}② VMess-WS-TLS (端口 ${VMESS_PORT})${NC}"
    echo "   $vmess_link"
    echo ""
    echo -e "${BLUE}③ Hysteria2 (端口 ${HY2_PORT})${NC}"
    echo "   $hy2_link"
    echo ""
    echo -e "${BLUE}④ TUIC5 (端口 ${TUIC_PORT})${NC}"
    echo "   $tuic_link"
    echo ""
    echo -e "${BLUE}⑤ AnyTLS (端口 ${ANYTLS_PORT})${NC}"
    echo "   $anytls_link"
    echo ""

    # Base64 订阅
    print_header "Base64 订阅"
    local all_links="${vless_link}
${vmess_link}
${hy2_link}
${tuic_link}
${anytls_link}"
    local subscription
    subscription=$(echo -n "$all_links" | base64 -w 0)
    echo "$subscription"
    echo ""
    echo -e "${GREEN}提示: 复制上面的 Base64 内容，可直接导入 v2rayN / NekoBox 等客户端${NC}"
    echo ""
}

# ------------------- 功能 2: 生成 Clash 配置 -------------------

gen_clash_config() {
    load_config
    mkdir -p "$OUTPUT_DIR"
    local output_file="${OUTPUT_DIR}/clash-config.yaml"
    bash "${SCRIPT_DIR}/gen-clash.sh" -o "$output_file" \
        -c "$CONFIG_FILE" -i "$PUBLIC_IP" \
        --public-key "$VLESS_PUBLIC_KEY"
    echo ""
    echo -e "${GREEN}Clash 配置已生成: ${output_file}${NC}"
    echo ""
}

# ------------------- 功能 3: 生成 sing-box 客户端配置 -------------------

gen_singbox_client_config() {
    load_config
    mkdir -p "$OUTPUT_DIR"
    local output_file="${OUTPUT_DIR}/singbox-client.json"

    # 生成客户端 JSON 配置
    jq -n \
        --arg uuid "$UUID" \
        --arg ip "$PUBLIC_IP" \
        --argjson vless_port "$VLESS_PORT" \
        --arg vless_sni "$VLESS_SNI" \
        --arg vless_pkey "$VLESS_PUBLIC_KEY" \
        --arg vless_sid "$VLESS_SHORT_ID" \
        --argjson vmess_port "$VMESS_PORT" \
        --arg vmess_sni "$VMESS_SNI" \
        --arg vmess_path "$VMESS_PATH" \
        --argjson hy2_port "$HY2_PORT" \
        --arg hy2_sni "$HY2_SNI" \
        --arg hy2_pw "$HY2_PASSWORD" \
        --argjson tuic_port "$TUIC_PORT" \
        --arg tuic_sni "$TUIC_SNI" \
        --arg tuic_pw "$TUIC_PASSWORD" \
        --argjson anytls_port "$ANYTLS_PORT" \
        --arg anytls_sni "$ANYTLS_SNI" \
        --arg anytls_pw "$ANYTLS_PASSWORD" \
    '{
  "log": {
    "level": "info"
  },
  "inbounds": [
    {
      "type": "tun",
      "tag": "tun-in",
      "interface_name": "tun0",
      "inet4_address": "172.19.0.1/30",
      "auto_route": true,
      "strict_route": false
    },
    {
      "type": "mixed",
      "tag": "mixed-in",
      "listen": "127.0.0.1",
      "listen_port": 2080
    }
  ],
  "outbounds": [
    {
      "type": "vless",
      "tag": "VLess-Reality",
      "server": $ip,
      "server_port": $vless_port,
      "uuid": $uuid,
      "flow": "xtls-rprx-vision",
      "tls": {
        "enabled": true,
        "server_name": $vless_sni,
        "utls": {
          "enabled": true,
          "fingerprint": "chrome"
        },
        "reality": {
          "enabled": true,
          "public_key": $vless_pkey,
          "short_id": $vless_sid
        }
      }
    },
    {
      "type": "vmess",
      "tag": "VMess-WS",
      "server": $ip,
      "server_port": $vmess_port,
      "uuid": $uuid,
      "security": "auto",
      "alter_id": 0,
      "tls": {
        "enabled": true,
        "server_name": $vmess_sni,
        "insecure": true
      },
      "transport": {
        "type": "ws",
        "path": $vmess_path
      }
    },
    {
      "type": "hysteria2",
      "tag": "Hysteria2",
      "server": $ip,
      "server_port": $hy2_port,
      "password": $hy2_pw,
      "tls": {
        "enabled": true,
        "server_name": $hy2_sni,
        "insecure": true
      }
    },
    {
      "type": "tuic",
      "tag": "Tuic5",
      "server": $ip,
      "server_port": $tuic_port,
      "uuid": $uuid,
      "password": $tuic_pw,
      "congestion_control": "bbr",
      "tls": {
        "enabled": true,
        "server_name": $tuic_sni,
        "insecure": true
      }
    },
    {
      "type": "anytls",
      "tag": "AnyTLS",
      "server": $ip,
      "server_port": $anytls_port,
      "password": $anytls_pw,
      "tls": {
        "enabled": true,
        "server_name": $anytls_sni,
        "insecure": true
      }
    },
    {
      "type": "selector",
      "tag": "proxy",
      "outbounds": ["VLess-Reality", "VMess-WS", "Hysteria2", "Tuic5", "AnyTLS", "auto"],
      "default": "auto"
    },
    {
      "type": "urltest",
      "tag": "auto",
      "outbounds": ["VLess-Reality", "VMess-WS", "Hysteria2", "Tuic5", "AnyTLS"],
      "url": "https://www.gstatic.com/generate_204",
      "interval": "5m"
    },
    {
      "type": "direct",
      "tag": "direct"
    },
    {
      "type": "block",
      "tag": "block"
    }
  ],
  "route": {
    "rules": [
      {
        "outbound": "direct",
        "ip_is_private": true
      },
      {
        "outbound": "direct",
        "geoip": "cn"
      },
      {
        "outbound": "proxy",
        "geosite": "geolocation-!cn"
      }
    ],
    "final": "proxy",
    "auto_detect_interface": true
  },
    "dns": {
        "servers": [
            {
                "tag": "local",
                "address": "223.5.5.5",
                "detour": "direct"
            },
            {
                "tag": "remote",
                "address": "https://dns.google/dns-query",
                "detour": "proxy"
            }
        ],
        "rules": [
            {
                "outbound": "any",
                "server": "local"
            },
            {
                "geosite": "cn",
                "server": "local"
            },
            {
                "geosite": "geolocation-!cn",
                "server": "remote"
            }
        ],
        "final": "remote",
        "independent_cache": true
    }
}' > "$output_file"

    echo ""
    echo -e "${GREEN}sing-box 客户端配置已生成: ${output_file}${NC}"
    echo -e "${YELLOW}提示: 将此文件导入 sing-box 客户端即可使用${NC}"
    echo ""
}

# ------------------- 功能 4: 生成二维码 -------------------

gen_qrcodes() {
    load_config
    if ! command -v qrencode &>/dev/null; then
        print_error "qrencode 未安装，请先安装: yum install qrencode"
        return 1
    fi
    bash "${SCRIPT_DIR}/gen-qrcode.sh" -c "$CONFIG_FILE" -i "$PUBLIC_IP" \
        --public-key "$VLESS_PUBLIC_KEY"
}

# ------------------- 功能 5: 服务管理 -------------------

service_start() {
    echo ""
    print_header "启动 sing-box 服务"
    systemctl start "$SERVICE_NAME"
    sleep 1
    systemctl status "$SERVICE_NAME" --no-pager -l
    echo ""
}

service_stop() {
    echo ""
    print_header "停止 sing-box 服务"
    systemctl stop "$SERVICE_NAME"
    echo -e "${YELLOW}服务已停止${NC}"
    echo ""
}

service_restart() {
    echo ""
    print_header "重启 sing-box 服务"
    systemctl restart "$SERVICE_NAME"
    sleep 1
    systemctl status "$SERVICE_NAME" --no-pager -l
    echo ""
}

service_status() {
    echo ""
    print_header "sing-box 服务状态"
    systemctl status "$SERVICE_NAME" --no-pager -l
    echo ""
}

show_logs() {
    echo ""
    print_header "sing-box 最近日志 (50行)"
    journalctl -u "$SERVICE_NAME" --no-pager -n 50
    echo ""
}

follow_logs() {
    echo ""
    print_header "实时日志 (Ctrl+C 退出)"
    journalctl -u "$SERVICE_NAME" -f
}

# ------------------- 功能 6: 导出 Base64 订阅到文件 -------------------

export_subscription() {
    load_config
    mkdir -p "$OUTPUT_DIR"
    local output_file="${OUTPUT_DIR}/subscription.txt"
    bash "${SCRIPT_DIR}/gen-subscription.sh" -o "$output_file" \
        -c "$CONFIG_FILE" -i "$PUBLIC_IP" \
        --public-key "$VLESS_PUBLIC_KEY"
    echo ""
    echo -e "${GREEN}订阅文件已生成: ${output_file}${NC}"
    echo ""
}

# ------------------- 主菜单 -------------------

show_menu() {
    clear
    echo -e "${CYAN}╔══════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║${GREEN}       sing-box 管理脚本 v1.0                 ${CYAN}║${NC}"
    echo -e "${CYAN}║${YELLOW}       VPS: ${PUBLIC_IP:-加载中...}                 ${CYAN}║${NC}"
    echo -e "${CYAN}╠══════════════════════════════════════════════╣${NC}"
    echo -e "${CYAN}║${NC}  ${BLUE}[1]${NC} 查看节点信息 (分享链接+订阅)         ${CYAN}║${NC}"
    echo -e "${CYAN}║${NC}  ${BLUE}[2]${NC} 生成 Clash/Mihomo 配置 (YAML)         ${CYAN}║${NC}"
    echo -e "${CYAN}║${NC}  ${BLUE}[3]${NC} 生成 sing-box 客户端配置 (JSON)       ${CYAN}║${NC}"
    echo -e "${CYAN}║${NC}  ${BLUE}[4]${NC} 导出订阅文件                          ${CYAN}║${NC}"
    echo -e "${CYAN}║${NC}  ${BLUE}[5]${NC} 生成二维码 (终端显示)                 ${CYAN}║${NC}"
    echo -e "${CYAN}║${NC}  ${BLUE}[6]${NC} 重启 sing-box 服务                    ${CYAN}║${NC}"
    echo -e "${CYAN}║${NC}  ${BLUE}[7]${NC} 停止 sing-box 服务                    ${CYAN}║${NC}"
    echo -e "${CYAN}║${NC}  ${BLUE}[8]${NC} 启动 sing-box 服务                    ${CYAN}║${NC}"
    echo -e "${CYAN}║${NC}  ${BLUE}[9]${NC} 查看服务状态                          ${CYAN}║${NC}"
    echo -e "${CYAN}║${NC}  ${BLUE}[10]${NC} 查看日志 (最近50行)                  ${CYAN}║${NC}"
    echo -e "${CYAN}║${NC}  ${BLUE}[11]${NC} 实时日志                             ${CYAN}║${NC}"
    echo -e "${CYAN}║${NC}  ${BLUE}[0]${NC}  退出                                 ${CYAN}║${NC}"
    echo -e "${CYAN}╚══════════════════════════════════════════════╝${NC}"
    echo ""
    echo -n -e "${GREEN}请选择 [0-11]: ${NC}"
}

# ------------------- 入口 -------------------

main() {
    check_deps

    while true; do
        show_menu
        read -r choice
        case "$choice" in
            1) show_nodes ;;
            2) gen_clash_config ;;
            3) gen_singbox_client_config ;;
            4) export_subscription ;;
            5) gen_qrcodes ;;
            6) service_restart ;;
            7) service_stop ;;
            8) service_start ;;
            9) service_status ;;
            10) show_logs ;;
            11) follow_logs ;;
            0)
                echo -e "${GREEN}再见! 🐱${NC}"
                exit 0
                ;;
            *)
                echo -e "${RED}无效选择，请重试${NC}"
                ;;
        esac
        echo ""
        echo -e "${YELLOW}按回车继续...${NC}"
        read -r
    done
}

# 支持非交互式调用
case "${1:-}" in
    --nodes) check_deps; show_nodes; exit 0 ;;
    --clash) check_deps; gen_clash_config; exit 0 ;;
    --client) check_deps; gen_singbox_client_config; exit 0 ;;
    --sub) check_deps; export_subscription; exit 0 ;;
    --qr) check_deps; gen_qrcodes; exit 0 ;;
    --restart) service_restart; exit 0 ;;
    --stop) service_stop; exit 0 ;;
    --start) service_start; exit 0 ;;
    --status) service_status; exit 0 ;;
    --logs) show_logs; exit 0 ;;
    --help|-h)
        echo "用法: $0 [选项]"
        echo "  --nodes     查看节点信息"
        echo "  --clash     生成 Clash 配置"
        echo "  --client    生成 sing-box 客户端配置"
        echo "  --sub       导出订阅文件"
        echo "  --qr        生成二维码"
        echo "  --restart   重启服务"
        echo "  --stop      停止服务"
        echo "  --start     启动服务"
        echo "  --status    查看服务状态"
        echo "  --logs      查看日志"
        echo "  (无参数)    交互式菜单"
        exit 0
        ;;
esac

main
