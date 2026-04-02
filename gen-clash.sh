#!/bin/bash
# ============================================================
# gen-clash.sh — Clash/Mihomo 配置生成器
# 从 sb.json 读取配置，生成完整的 Clash YAML 配置
# 包含: 5个协议代理、DNS、分流规则、代理组
# ============================================================

set -euo pipefail

# ------------------- 使用说明 -------------------
usage() {
    echo "用法: $0 -o <输出文件> -c <配置文件> -i <公网IP> [--public-key <key>]"
    echo ""
    echo "参数:"
    echo "  -o, --output       输出 YAML 文件路径"
    echo "  -c, --config       sing-box 配置文件路径 (sb.json)"
    echo "  -i, --ip           VPS 公网 IP 地址"
    echo "  --public-key       VLESS-Reality 公钥 (可选，从私钥推导)"
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

[[ -z "$OUTPUT_FILE" || -z "$CONFIG_FILE" || -z "$PUBLIC_IP" ]] && usage
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

# ------------------- 生成 YAML -------------------
cat > "$OUTPUT_FILE" << 'YAMLEOF'
# ============================================================
# Clash/Mihomo 配置文件 — sing-box 管理脚本自动生成
# 生成时间: GENERATION_TIME
# VPS: VPS_IP
# ============================================================

# ============================================================
# 端口与模式
# ============================================================
mixed-port: 7890
allow-lan: true
mode: rule
log-level: info

# ============================================================
# DNS 配置 (fake-ip 模式)
# ============================================================
dns:
  enable: true
  listen: 0.0.0.0:53
  enhanced-mode: fake-ip
  fake-ip-range: 198.18.0.1/16
  fake-ip-filter:
    - "*.lan"
    - "*.local"
    - localhost.ptlogin2.qq.com
    - +.srv.nintendo.net
    - +.stun.playstation.net
    - +.msftconnecttest.com
    - +.msftncsi.com
  nameserver:
    - 223.5.5.5       # 阿里 DNS
    - 119.29.29.29     # 腾讯 DNS
  fallback:
    - https://dns.google/dns-query
    - https://cloudflare-dns.com/dns-query
    - tls://8.8.4.4:853
  fallback-filter:
    geoip: true
    geoip-code: CN
    ipcidr:
      - 240.0.0.0/4

# ============================================================
# 代理配置
# ============================================================
proxies:
YAMLEOF

# 注入时间戳和 IP
sed -i "s/GENERATION_TIME/$(date '+%Y-%m-%d %H:%M:%S')/" "$OUTPUT_FILE"
sed -i "s/VPS_IP/${PUBLIC_IP}/" "$OUTPUT_FILE"

# 追加代理定义
cat >> "$OUTPUT_FILE" << YAMLEOF2

  # ─── VLess-Reality ───
  - name: "VLess-Reality"
    type: vless
    server: ${PUBLIC_IP}
    port: ${VLESS_PORT}
    uuid: ${UUID}
    flow: xtls-rprx-vision
    udp: true
    tls: true
    servername: ${VLESS_SNI}
    reality-opts:
      public-key: ${PUBLIC_KEY}
      short-id: ${VLESS_SHORT_ID}
    client-fingerprint: chrome
    network: tcp

  # ─── VMess-WS-TLS ───
  - name: "VMess-WS"
    type: vmess
    server: ${PUBLIC_IP}
    port: ${VMESS_PORT}
    uuid: ${UUID}
    alterId: 0
    cipher: auto
    udp: true
    tls: true
    servername: ${VMESS_SNI}
    skip-cert-verify: true
    network: ws
    ws-opts:
      path: ${VMESS_PATH}
      headers:
        Host: ${VMESS_SNI}

  # ─── Hysteria2 ───
  - name: "Hysteria2"
    type: hysteria2
    server: ${PUBLIC_IP}
    port: ${HY2_PORT}
    password: ${HY2_PASSWORD}
    up: "30 Mbps"
    down: "100 Mbps"
    sni: ${HY2_SNI}
    skip-cert-verify: true
    alpn:
      - h3

  # ─── TUIC5 ───
  - name: "Tuic5"
    type: tuic
    server: ${PUBLIC_IP}
    port: ${TUIC_PORT}
    uuid: ${UUID}
    password: ${TUIC_PASSWORD}
    congestion-controller: bbr
    udp-relay-mode: native
    alpn:
      - h3
    sni: ${TUIC_SNI}
    skip-cert-verify: true

  # ─── AnyTLS ───
  - name: "AnyTLS"
    type: anytls
    server: ${PUBLIC_IP}
    port: ${ANYTLS_PORT}
    password: ${ANYTLS_PASSWORD}
    sni: ${ANYTLS_SNI}
    skip-cert-verify: true
YAMLEOF2

# 追加代理组和规则
cat >> "$OUTPUT_FILE" << 'YAMLEOF3'

# ============================================================
# 代理组
# ============================================================
proxy-groups:

  # 手动选择
  - name: "proxy"
    type: select
    proxies:
      - "VLess-Reality"
      - "VMess-WS"
      - "Hysteria2"
      - "Tuic5"
      - "AnyTLS"
      - "auto"

  # 自动测速选择
  - name: "auto"
    type: url-test
    url: "https://www.gstatic.com/generate_204"
    interval: 300
    tolerance: 50
    lazy: true
    proxies:
      - "VLess-Reality"
      - "VMess-WS"
      - "Hysteria2"
      - "Tuic5"
      - "AnyTLS"

  # 节点选择 (通用 fallback)
  - name: "节点选择"
    type: select
    proxies:
      - "proxy"
      - "direct"

  # 自动选择 (所有节点测速)
  - name: "自动选择"
    type: url-test
    url: "https://www.gstatic.com/generate_204"
    interval: 300
    tolerance: 50
    lazy: true
    proxies:
      - "VLess-Reality"
      - "VMess-WS"
      - "Hysteria2"
      - "Tuic5"
      - "AnyTLS"

# ============================================================
# 规则
# ============================================================
rules:
  # --- 广告拦截 ---
  - DOMAIN-SUFFIX,ads.google.com,REJECT
  - DOMAIN-SUFFIX,pagead2.googlesyndication.com,REJECT
  - DOMAIN-SUFFIX,analytics.google.com,REJECT
  - DOMAIN-KEYWORD,admarvel,REJECT
  - DOMAIN-KEYWORD,admaster,REJECT
  - DOMAIN-KEYWORD,adsage,REJECT
  - DOMAIN-KEYWORD,adsensor,REJECT
  - DOMAIN-KEYWORD,adsmogo,REJECT
  - DOMAIN-KEYWORD,adsrvmedia,REJECT
  - DOMAIN-KEYWORD,adsserving,REJECT
  - DOMAIN-KEYWORD,adsystem,REJECT
  - DOMAIN-KEYWORD,adwords,REJECT
  - DOMAIN-KEYWORD,alywp,REJECT
  - DOMAIN-KEYWORD,domob,REJECT
  - DOMAIN-KEYWORD,wqtracker,REJECT

  # --- 国内直连 ---
  - GEOIP,CN,direct
  - DOMAIN-SUFFIX,cn,direct
  - DOMAIN-SUFFIX,taobao.com,direct
  - DOMAIN-SUFFIX,tmall.com,direct
  - DOMAIN-SUFFIX,alipay.com,direct
  - DOMAIN-SUFFIX,alibaba.com,direct
  - DOMAIN-SUFFIX,qq.com,direct
  - DOMAIN-SUFFIX,weixin.qq.com,direct
  - DOMAIN-SUFFIX,baidu.com,direct
  - DOMAIN-SUFFIX,bdstatic.com,direct
  - DOMAIN-SUFFIX,bilibili.com,direct
  - DOMAIN-SUFFIX,hdslb.com,direct
  - DOMAIN-SUFFIX,163.com,direct
  - DOMAIN-SUFFIX,126.com,direct
  - DOMAIN-SUFFIX,126.net,direct
  - DOMAIN-SUFFIX,netease.com,direct
  - DOMAIN-SUFFIX,jd.com,direct
  - DOMAIN-SUFFIX,360buyimg.com,direct
  - DOMAIN-SUFFIX,mi.com,direct
  - DOMAIN-SUFFIX,xiaomi.com,direct
  - DOMAIN-SUFFIX,huawei.com,direct
  - DOMAIN-SUFFIX,pinduoduo.com,direct
  - DOMAIN-SUFFIX,douyin.com,direct
  - DOMAIN-SUFFIX,toutiao.com,direct
  - DOMAIN-SUFFIX,zhihu.com,direct
  - DOMAIN-SUFFIX,weibo.com,direct
  - DOMAIN-SUFFIX,csdn.net,direct
  - DOMAIN-SUFFIX,jd.hk,direct
  - IP-CIDR,10.0.0.0/8,direct
  - IP-CIDR,172.16.0.0/12,direct
  - IP-CIDR,192.168.0.0/16,direct
  - IP-CIDR,127.0.0.0/8,direct

  # --- 国外代理 ---
  - DOMAIN-SUFFIX,google.com,proxy
  - DOMAIN-SUFFIX,googleapis.com,proxy
  - DOMAIN-SUFFIX,gstatic.com,proxy
  - DOMAIN-SUFFIX,googleusercontent.com,proxy
  - DOMAIN-SUFFIX,youtube.com,proxy
  - DOMAIN-SUFFIX,ytimg.com,proxy
  - DOMAIN-SUFFIX,twitter.com,proxy
  - DOMAIN-SUFFIX,twimg.com,proxy
  - DOMAIN-SUFFIX,x.com,proxy
  - DOMAIN-SUFFIX,facebook.com,proxy
  - DOMAIN-SUFFIX,fbcdn.net,proxy
  - DOMAIN-SUFFIX,instagram.com,proxy
  - DOMAIN-SUFFIX,github.com,proxy
  - DOMAIN-SUFFIX,githubusercontent.com,proxy
  - DOMAIN-SUFFIX,github.io,proxy
  - DOMAIN-SUFFIX,telegram.org,proxy
  - DOMAIN-SUFFIX,whatsapp.com,proxy
  - DOMAIN-SUFFIX,netflix.com,proxy
  - DOMAIN-SUFFIX,nflxext.com,proxy
  - DOMAIN-SUFFIX,nflximg.net,proxy
  - DOMAIN-SUFFIX,wikipedia.org,proxy
  - DOMAIN-SUFFIX,wikimedia.org,proxy
  - DOMAIN-SUFFIX,reddit.com,proxy
  - DOMAIN-SUFFIX,redd.it,proxy
  - DOMAIN-SUFFIX,medium.com,proxy
  - DOMAIN-SUFFIX,cloudflare.com,proxy
  - DOMAIN-SUFFIX,openai.com,proxy
  - DOMAIN-SUFFIX,chatgpt.com,proxy
  - DOMAIN-SUFFIX,anthropic.com,proxy
  - DOMAIN-SUFFIX,apple.com,proxy

  # --- 最终兜底 ---
  - MATCH,proxy
YAMLEOF3

echo "[gen-clash.sh] Clash 配置已生成: ${OUTPUT_FILE}"
