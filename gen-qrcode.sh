#!/bin/bash
# ============================================================
# gen-qrcode.sh — 二维码生成器
# 为每个协议生成二维码并输出到终端 (ANSI UTF8)
# ============================================================

set -euo pipefail

# ------------------- 使用说明 -------------------
usage() {
    echo "用法: $0 -c <配置文件> -i <公网IP> [--public-key <key>]"
    echo ""
    echo "参数:"
    echo "  -c, --config       sing-box 配置文件路径 (sb.json)"
    echo "  -i, --ip           VPS 公网 IP 地址"
    echo "  --public-key       VLESS-Reality 公钥"
    exit 1
}

# ------------------- 参数解析 -------------------
CONFIG_FILE=""
PUBLIC_IP=""
PUBLIC_KEY="mayeSAHMUyw96197nxS9QzuGj5R0B3WGcAmKhpR7e0Y"

while [[ $# -gt 0 ]]; do
    case "$1" in
        -c|--config)   CONFIG_FILE="$2"; shift 2 ;;
        -i|--ip)       PUBLIC_IP="$2"; shift 2 ;;
        --public-key)  PUBLIC_KEY="$2"; shift 2 ;;
        -h|--help)     usage ;;
        *)             echo "未知参数: $1"; usage ;;
    esac
done

[[ -z "$CONFIG_FILE" || -z "$PUBLIC_IP" ]] && usage
[[ ! -f "$CONFIG_FILE" ]] && { echo "配置文件不存在: $CONFIG_FILE"; exit 1; }

# 检查 qrencode
if ! command -v qrencode &>/dev/null; then
    echo "[错误] qrencode 未安装，请先安装: yum install qrencode" >&2
    exit 1
fi

# ------------------- 读取配置 -------------------
UUID=$(jq -r '.inbounds[0].users[0].uuid' "$CONFIG_FILE")

# VLess-Reality
VLESS_PORT=$(jq -r '.inbounds[] | select(.type=="vless") | .listen_port' "$CONFIG_FILE")
VLESS_SNI=$(jq -r '.inbounds[] | select(.type=="vless") | .tls.server_name' "$CONFIG_FILE")
VLESS_SHORT_ID=$(jq -r '.inbounds[] | select(.type=="vless") | .tls.reality.short_id[0]' "$CONFIG_FILE")

# VMess-WS
VMESS_PORT=$(jq -r '.inbounds[] | select(.type=="vmess") | .listen_port' "$CONFIG_FILE")
VMESS_PATH=$(jq -r '.inbounds[] | select(.type=="vmess") | .transport.path' "$CONFIG_FILE")
VMESS_SNI=$(jq -r '.inbounds[] | select(.type=="vmess") | .tls.server_name' "$CONFIG_FILE")

# Hysteria2
HY2_PORT=$(jq -r '.inbounds[] | select(.type=="hysteria2") | .listen_port' "$CONFIG_FILE")
HY2_SNI=$(jq -r '.inbounds[] | select(.type=="hysteria2") | .tls.server_name' "$CONFIG_FILE")
[[ "$HY2_SNI" == "null" ]] && HY2_SNI="racknerd-9edcd3"
HY2_PASSWORD=$(jq -r '.inbounds[] | select(.type=="hysteria2") | .users[0].password' "$CONFIG_FILE")

# TUIC5
TUIC_PORT=$(jq -r '.inbounds[] | select(.type=="tuic") | .listen_port' "$CONFIG_FILE")
TUIC_SNI=$(jq -r '.inbounds[] | select(.type=="tuic") | .tls.server_name' "$CONFIG_FILE")
[[ "$TUIC_SNI" == "null" ]] && TUIC_SNI="racknerd-9edcd3"
TUIC_PASSWORD=$(jq -r '.inbounds[] | select(.type=="tuic") | .users[0].password' "$CONFIG_FILE")

# AnyTLS
ANYTLS_PORT=$(jq -r '.inbounds[] | select(.type=="anytls") | .listen_port' "$CONFIG_FILE")
ANYTLS_SNI=$(jq -r '.inbounds[] | select(.type=="anytls") | .tls.server_name' "$CONFIG_FILE")
[[ "$ANYTLS_SNI" == "null" ]] && ANYTLS_SNI="racknerd-9edcd3"
ANYTLS_PASSWORD=$(jq -r '.inbounds[] | select(.type=="anytls") | .users[0].password' "$CONFIG_FILE")

# ------------------- 生成分享链接 -------------------

VLESS_LINK="vless://${UUID}@${PUBLIC_IP}:${VLESS_PORT}?encryption=none&flow=xtls-rprx-vision&security=reality&sni=${VLESS_SNI}&fp=chrome&pbk=${PUBLIC_KEY}&sid=${VLESS_SHORT_ID}&type=tcp#VLess-Reality-${PUBLIC_IP}"

VMESS_JSON=$(cat <<EOJSON
{"v":"2","ps":"VMess-WS-${PUBLIC_IP}","add":"${PUBLIC_IP}","port":"${VMESS_PORT}","id":"${UUID}","aid":"0","scy":"auto","net":"ws","type":"none","host":"","path":"${VMESS_PATH}","tls":"tls","sni":"${VMESS_SNI}","alpn":"","fp":""}
EOJSON
)
VMESS_LINK="vmess://$(echo -n "$VMESS_JSON" | base64 -w 0)"

HY2_LINK="hysteria2://${HY2_PASSWORD}@${PUBLIC_IP}:${HY2_PORT}?sni=${HY2_SNI}&insecure=1#Hysteria2-${PUBLIC_IP}"

TUIC_LINK="tuic://${UUID}:${TUIC_PASSWORD}@${PUBLIC_IP}:${TUIC_PORT}?congestion_control=bbr&sni=${TUIC_SNI}&insecure=1&udp_relay_mode=native#Tuic5-${PUBLIC_IP}"

ANYTLS_LINK="anytls://${ANYTLS_PASSWORD}@${PUBLIC_IP}:${ANYTLS_PORT}?insecure=1&sni=${ANYTLS_SNI}#AnyTLS-${PUBLIC_IP}"

# ------------------- 输出二维码 -------------------

CYAN='\033[0;36m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo ""
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

# ① VLess-Reality
echo -e "${GREEN}① VLess-Reality (端口 ${VLESS_PORT})${NC}"
echo -e "${YELLOW}${VLESS_LINK}${NC}"
qrencode -t UTF8 "$VLESS_LINK"
echo ""

# ② VMess-WS
echo -e "${GREEN}② VMess-WS-TLS (端口 ${VMESS_PORT})${NC}"
echo -e "${YELLOW}${VMESS_LINK}${NC}"
qrencode -t UTF8 "$VMESS_LINK"
echo ""

# ③ Hysteria2
echo -e "${GREEN}③ Hysteria2 (端口 ${HY2_PORT})${NC}"
echo -e "${YELLOW}${HY2_LINK}${NC}"
qrencode -t UTF8 "$HY2_LINK"
echo ""

# ④ TUIC5
echo -e "${GREEN}④ TUIC5 (端口 ${TUIC_PORT})${NC}"
echo -e "${YELLOW}${TUIC_LINK}${NC}"
qrencode -t UTF8 "$TUIC_LINK"
echo ""

# ⑤ AnyTLS
echo -e "${GREEN}⑤ AnyTLS (端口 ${ANYTLS_PORT})${NC}"
echo -e "${YELLOW}${ANYTLS_LINK}${NC}"
qrencode -t UTF8 "$ANYTLS_LINK"
echo ""

echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}提示: 用手机扫描二维码即可导入对应协议${NC}"
echo ""
