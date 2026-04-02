#!/bin/bash
# ============================================================
# gen-subscription.sh — 订阅生成器
# 生成 Base64 编码的订阅内容，可导入 v2rayN/NekoBox 等客户端
# ============================================================

set -euo pipefail

# ------------------- 使用说明 -------------------
usage() {
    echo "用法: $0 -o <输出文件> -c <配置文件> -i <公网IP> [--public-key <key>]"
    echo ""
    echo "参数:"
    echo "  -o, --output       输出文件路径 (默认: stdout)"
    echo "  -c, --config       sing-box 配置文件路径 (sb.json)"
    echo "  -i, --ip           VPS 公网 IP 地址"
    echo "  --public-key       VLESS-Reality 公钥"
    exit 1
}

# ------------------- 参数解析 -------------------
OUTPUT_FILE=""
CONFIG_FILE=""
PUBLIC_IP=""
PUBLIC_KEY="mayeSAHMUyw96197nxS9QzuGj5R0B3WGcAmKhpR7e0Y"

while [[ $# -gt 0 ]]; do
    case "$1" in
        -o|--output)   OUTPUT_FILE="$2"; shift 2 ;;
        -c|--config)   CONFIG_FILE="$2"; shift 2 ;;
        -i|--ip)       PUBLIC_IP="$2"; shift 2 ;;
        --public-key)  PUBLIC_KEY="$2"; shift 2 ;;
        -h|--help)     usage ;;
        *)             echo "未知参数: $1"; usage ;;
    esac
done

[[ -z "$CONFIG_FILE" || -z "$PUBLIC_IP" ]] && usage
[[ ! -f "$CONFIG_FILE" ]] && { echo "配置文件不存在: $CONFIG_FILE"; exit 1; }

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

# VLess-Reality 链接
VLESS_LINK="vless://${UUID}@${PUBLIC_IP}:${VLESS_PORT}?encryption=none&flow=xtls-rprx-vision&security=reality&sni=${VLESS_SNI}&fp=chrome&pbk=${PUBLIC_KEY}&sid=${VLESS_SHORT_ID}&type=tcp#VLess-Reality-${PUBLIC_IP}"

# VMess 链接 (base64 JSON)
VMESS_JSON=$(cat <<EOJSON
{
  "v": "2",
  "ps": "VMess-WS-${PUBLIC_IP}",
  "add": "${PUBLIC_IP}",
  "port": "${VMESS_PORT}",
  "id": "${UUID}",
  "aid": "0",
  "scy": "auto",
  "net": "ws",
  "type": "none",
  "host": "",
  "path": "${VMESS_PATH}",
  "tls": "tls",
  "sni": "${VMESS_SNI}",
  "alpn": "",
  "fp": ""
}
EOJSON
)
VMESS_LINK="vmess://$(echo -n "$VMESS_JSON" | base64 -w 0)"

# Hysteria2 链接
HY2_LINK="hysteria2://${HY2_PASSWORD}@${PUBLIC_IP}:${HY2_PORT}?sni=${HY2_SNI}&insecure=1#Hysteria2-${PUBLIC_IP}"

# TUIC5 链接
TUIC_LINK="tuic://${UUID}:${TUIC_PASSWORD}@${PUBLIC_IP}:${TUIC_PORT}?congestion_control=bbr&sni=${TUIC_SNI}&insecure=1&udp_relay_mode=native#Tuic5-${PUBLIC_IP}"

# AnyTLS 链接
ANYTLS_LINK="anytls://${ANYTLS_PASSWORD}@${PUBLIC_IP}:${ANYTLS_PORT}?insecure=1&sni=${ANYTLS_SNI}#AnyTLS-${PUBLIC_IP}"

# ------------------- Base64 编码 -------------------
ALL_LINKS="${VLESS_LINK}
${VMESS_LINK}
${HY2_LINK}
${TUIC_LINK}
${ANYTLS_LINK}"

SUBSCRIPTION=$(echo -n "$ALL_LINKS" | base64 -w 0)

# ------------------- 输出 -------------------
if [[ -n "$OUTPUT_FILE" ]]; then
    # 写入详细信息 + Base64 订阅
    {
        echo "# ============================================================"
        echo "# sing-box 订阅文件 — 自动生成"
        echo "# 生成时间: $(date '+%Y-%m-%d %H:%M:%S')"
        echo "# VPS: ${PUBLIC_IP}"
        echo "# ============================================================"
        echo ""
        echo "# --- 分享链接 (原始) ---"
        echo ""
        echo "[1] VLess-Reality:"
        echo "${VLESS_LINK}"
        echo ""
        echo "[2] VMess-WS:"
        echo "${VMESS_LINK}"
        echo ""
        echo "[3] Hysteria2:"
        echo "${HY2_LINK}"
        echo ""
        echo "[4] TUIC5:"
        echo "${TUIC_LINK}"
        echo ""
        echo "[5] AnyTLS:"
        echo "${ANYTLS_LINK}"
        echo ""
        echo "# --- Base64 订阅 (复制以下内容导入客户端) ---"
        echo ""
        echo "${SUBSCRIPTION}"
    } > "$OUTPUT_FILE"
    echo "[gen-subscription.sh] 订阅文件已生成: ${OUTPUT_FILE}"
else
    echo "$SUBSCRIPTION"
fi
