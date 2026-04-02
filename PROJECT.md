# sing-box 管理项目 — 自有方案

> 安全可控、持续迭代、完全自写

## 一、项目概述

在 VPS (96.44.141.123, AlmaLinux 8.9) 上部署的 sing-box v1.13.4 代理服务管理工具。
所有代码自己写、自己审计、自己维护，不依赖第三方黑箱脚本。

## 二、功能清单与实现原理

### 2.1 五协议共存 ✅ 已完成

| 协议 | 特点 | 适用场景 |
|------|------|---------|
| VLess-Reality | 无需证书，抗审查最强 | 首选协议 |
| VMess-WS-TLS | 可走 CDN | 配合 Argo 隧道 |
| Hysteria2 | UDP 丢包重传，快 | 高延迟网络 |
| TUIC5 | QUIC，低延迟 | 游戏/实时 |
| AnyTLS | 新协议，抗封锁 | 备用 |

### 2.2 Argo 隧道 🟡 待实现

**原理：**
```
客户端 → Cloudflare 边缘节点 (443) → cloudflared隧道 → VPS本地VMess端口
```

关键点：
- VMess-WS 不开 TLS（`tls=false`），因为 TLS 由 Cloudflare 终结
- `cloudflared` 在 VPS 上运行，把本地 VMess 端口暴露给 Cloudflare 网络
- 客户端连接的是 `*.trycloudflare.com`（临时）或自定义域名（固定），**不是 VPS 真实 IP**

**两种模式：**

#### 临时隧道（零配置）
```bash
# 原理：cloudflared 启动时自动在 CF 网络注册一个随机域名
nohup cloudflared tunnel --url http://127.0.0.1:25132 --no-autoupdate &
# 等几秒后，日志里会出现: https://<随机字符>.trycloudflare.com
# 这个 URL 就是 VMess 的地址
```

获取临时域名：
```bash
# cloudflared 启动后从日志获取
grep trycloudflare.com /etc/s-box-sn/argo.log | awk '{print $NF}'
```

#### 固定隧道（需要 CF 账号）
```bash
# 1. 在 CF Dashboard 创建隧道，获取 token
# 2. 用 token 启动 cloudflared
cloudflared service install <tunnel-token>
```

**VMess + Argo 的分享链接格式：**
```
vmess://base64({
  "add": "<argo域名>",     // 不是 VPS IP
  "port": "8443",          // CF 标准端口
  "id": "<uuid>",
  "net": "ws",
  "path": "<uuid>-vm",
  "tls": "tls",
  "sni": "<argo域名>",
  "host": "<argo域名>",
  "fp": "chrome"
})
```

**自己实现步骤：**
1. 检查 cloudflared 是否安装，没有就下载二进制
2. 启动 cloudflared tunnel --url http://127.0.0.1:<vmess端口>
3. 从日志获取 trycloudflare.com 域名
4. 生成带 Argo 域名的 VMess 分享链接
5. 更新 Clash/sing-box 客户端配置

**测试方法：**
- `curl -s https://<argo域名>` → 应返回 CF 404 页面（说明隧道通了）
- 客户端用 Argo 节点连接 → 测试代理是否工作

### 2.3 WARP 分流 🟡 待实现

**原理：**
```
sing-box → WireGuard出站 → Cloudflare WARP → 目标网站
```

关键组件：
- WireGuard endpoint: `162.159.192.1:2408` (IPv4) 或 `2606:4700:d0::a29f:c001:2408` (IPv6)
- CF WARP 的公钥固定: `bmXOC+F1FxEMF9dyiK2H5/1SUtzH0JuVo51h2wPfgyo=`
- 需要自己的 WireGuard 私钥和 WARP 分配的地址

**获取 WARP 配置的方法：**

方式1: warp-go (推荐)
```bash
# warp-go 是 CF WARP 的 Linux 客户端
# 安装后会生成 WireGuard 配置，包含:
# - PrivateKey
# - Address (IPv4 + IPv6)
# - Reserved 字段（用于防指纹识别）
```

方式2: wgcf (旧方式)
```bash
# 注册 CF WARP 账号 → 生成 wgcf-profile.conf
# 从配置中提取 PrivateKey 和 Address
```

**sing-box 1.13 中的 WARP 配置（新格式 endpoints）：**
```json
{
  "endpoints": [{
    "type": "wireguard",
    "tag": "warp-out",
    "address": ["172.16.0.2/32", "<IPv6>/128"],
    "private_key": "<wg私钥>",
    "peers": [{
      "address": "162.159.192.1",
      "port": 2408,
      "public_key": "bmXOC+F1FxEMF9dyiK2H5/1SUtzH0JuVo51h2wPfgyo=",
      "allowed_ips": ["0.0.0.0/0", "::/0"],
      "reserved": [100, 200, 30]
    }]
  }]
}
```

**分流规则：**
```json
{
  "outbound": "warp-out",
  "domain_suffix": ["openai.com", "chatgpt.com", "..."]
}
```

**自己实现步骤：**
1. 安装 warp-go，获取 WireGuard 配置
2. 提取 private_key, address, reserved
3. 在 sing-box 配置中添加 endpoint
4. 添加路由规则，指定哪些域名走 WARP

### 2.4 Clash/Mihomo 配置 ✅ 已有基础

**原理差异：**
- sing-box 原生格式是 JSON，客户端用 sing-box 或 NekoBox
- Clash/Mihomo 用 YAML 格式，客户端用 Clash Verge, Clash Meta 等
- 需要从同一份配置生成两种格式

**DNS 策略（参考项目 vs 我们）：**

| 项目 | 模式 | 国内 DNS | 国外 DNS |
|------|------|---------|---------|
| 参考项目 | fake-ip | 阿里+腾讯 DoH | Google DoH |
| 我们的 | fake-ip | 阿里 223.5.5.5 | Google DoH |

fake-ip 模式的优点：速度快、不泄露真实 DNS
缺点：某些应用不兼容（如银行APP）

**分流规则：**
- GeoIP CN → direct
- GeoSite CN → direct
- GeoSite geolocation-!cn → proxy
- Private IP → direct

### 2.5 订阅与客户端 ✅ 已有基础

**Base64 订阅标准格式：**
```
vless://uuid@ip:port?params#name
vmess://base64(json)
hysteria2://password@ip:port?params#name
tuic://uuid:password@ip:port?params#name
anytls://password@ip:port?params#name
```

全部用 `\n` 连接后 base64 编码。

**各客户端兼容性：**

| 客户端 | VLess | VMess | Hysteria2 | TUIC | AnyTLS | 格式 |
|--------|-------|-------|-----------|------|--------|------|
| v2rayN | ✅ | ✅ | ✅ | ✅ | ✅ | 分享链接 |
| NekoBox | ✅ | ✅ | ✅ | ✅ | ✅ | 分享链接 |
| sing-box | ✅ | ✅ | ✅ | ✅ | ✅ | JSON |
| Clash Meta | ✅ | ✅ | ✅ | ✅ | ⚠️ | YAML |
| Shadowrocket | ✅ | ✅ | ✅ | ✅ | ⚠️ | 分享链接 |

### 2.6 ACME 域名证书 🟡 待实现

**原理：**
- Let's Encrypt 免费签发证书
- 两种验证方式：HTTP-80 端口验证 / DNS API 验证
- 证书用于 VMess-TLS, Hysteria2, TUIC5

**自己实现：**
1. 安装 acme.sh
2. 选择验证方式（80端口或DNS API）
3. 申请证书 → 存到指定路径
4. 更新 sing-box 配置的证书路径
5. 设置 cron 自动续期

### 2.7 协议管理 🟡 待实现

**功能：** 安装后动态添加/删除协议，修改端口

**实现思路：**
1. 读取当前 sb.json
2. 用 jq 增删 inbounds 条目
3. 重新生成节点信息文件
4. systemctl reload sing-box

### 2.8 二维码生成 ✅ 已有

**原理：** 用 qrencode 把分享链接转成终端可显示的 ANSI UTF8 二维码

## 三、技术架构

### 目录结构
```
/etc/s-box-sn/
├── sing-box              # sing-box 二进制
├── sb.json               # 主配置
├── cert.crt              # 自签证书
├── private.key           # 私钥
├── manager/              # 管理脚本（自己写）
│   ├── sb.sh             # 主菜单
│   ├── gen-clash.sh      # Clash 生成
│   ├── gen-subscription.sh # 订阅生成
│   ├── gen-qrcode.sh     # 二维码生成
│   ├── gen-argo.sh       # Argo 隧道（待写）
│   ├── gen-warp.sh       # WARP 分流（待写）
│   └── lib/              # 公共函数库
│       └── common.sh     # 读取配置、生成链接等
├── output/               # 生成的配置文件
│   ├── clash-config.yaml
│   ├── singbox-client.json
│   ├── subscription.txt
│   └── qrcodes/
├── warp/                 # WARP 配置（待建）
│   └── warp-config.json
└── argo.log              # Argo 隧道日志
```

### 模块划分

```
sb.py (主入口 + 交互菜单)
  ├── config.py   — 读取/修改 sb.json
  ├── links.py    — 生成各协议分享链接
  ├── clash.py    — 生成 Clash YAML 配置
  ├── client.py   — 生成 sing-box 客户端 JSON 配置
  ├── subscribe.py — 生成 Base64 订阅
  ├── qrcode.py   — 生成二维码
  ├── argo.py     — Argo 隧道管理
  └── warp.py     — WARP 分流配置
```

### 关键设计原则

1. **所有配置从 sb.json 读取** — 不硬编码任何值
2. **每个模块独立可测试** — 支持命令行直接调用
3. **生成的文件统一放 output/** — 不污染主目录
4. **错误处理清晰** — 异常时给出明确的错误信息和修复建议
5. **纯 Python 标准库** — 只依赖 json, base64, subprocess, os, sys（不需要 pip install）
6. **入口：sb.py** — 直接 `python3 sb.py` 或软链接到 `/usr/local/bin/sb`

## 四、安全设计

### 4.1 代码安全
- [x] 所有代码自己写，不复制第三方
- [x] 每行代码理解原理后再使用
- [x] 不执行远程脚本（curl | bash）
- [x] 二进制从 GitHub 官方仓库下载 + SHA256 校验

### 4.2 运行安全
- [x] sing-box 以 root 运行（需要绑定低端口），但限制 Capabilities
- [x] firewall-cmd / iptables 只开放必要端口
- [x] 不暴露管理端口到公网

### 4.3 配置安全
- [x] UUID/密钥自动生成，不用默认值
- [x] 证书定期检查过期
- [x] 配置文件权限限制（600）

### 4.4 更新安全
- [ ] sing-box 版本更新前先测试
- [ ] 保留上一版本的备份
- [ ] 配置变更前自动备份 sb.json

## 五、迭代计划

### Phase 1: 核心功能 ✅ 已完成
- [x] 五协议共存
- [x] 节点信息查看
- [x] Base64 订阅
- [x] Clash 配置生成
- [x] sing-box 客户端配置
- [x] 二维码生成
- [x] 服务管理
- [x] Python 重写（7个模块）
- [x] CLI 命令行支持

### Phase 2: Argo 隧道 ✅ 已完成
- [x] 安装 cloudflared
- [x] 临时隧道模式
- [x] 自动生成 Argo VMess 链接
- [x] 整合到主菜单和 CLI

### Phase 3: WARP 分流 ✅ 代码完成（待部署）
- [x] warp.py 模块
- [x] WireGuard endpoint 配置生成
- [x] 域名分流规则（OpenAI/Claude 默认）
- [x] 整合到主菜单和 CLI
- [ ] 部署到 VPS 测试（VPS SSH 暂时不可达）

### Phase 4: 高级功能（待做）
- [ ] ACME 域名证书
- [ ] 协议动态增删
- [ ] 配置自动备份/恢复
- [ ] IPv4/IPv6 切换

### Phase 5: 优化与维护
- [ ] 代码重构（提取公共函数库）
- [ ] 自动更新检查
- [ ] 性能监控
- [ ] 文档完善

## 六、优化建议（相比参考项目）

| 参考项目的问题 | 我们的改进 |
|---------------|----------|
| 单文件 2000+ 行，难维护 | 模块化，每个功能独立脚本 |
| 硬编码路径和配置 | 全部从 sb.json 动态读取 |
| 版本兼容用两套配置文件 | 统一配置，按版本动态适配 |
| 无错误处理 | set -euo pipefail + 检查 |
| 依赖远程脚本 (curl\|bash) | 所有代码本地，不执行远程 |
| 无配置备份 | 每次变更前自动备份 |
| 混合中英文输出 | 统一中文输出 |

## 七、验证清单

每个功能完成后按此清单验证：

### Argo 隧道
- [ ] cloudflared 安装成功
- [ ] 临时隧道生成 trycloudflare.com 域名
- [ ] VMess + Argo 节点客户端可连接
- [ ] 重启后隧道自动恢复

### WARP 分流
- [ ] warp-go 安装成功
- [ ] WireGuard 配置获取成功
- [ ] 指定域名走 WARP 出站
- [ ] 其他域名走 direct 出站

### Clash 配置
- [ ] YAML 格式正确，Clash Verge 可导入
- [ ] DNS 分流工作正常
- [ ] 所有协议节点可选择

### 订阅
- [ ] Base64 解码后是正确的分享链接
- [ ] v2rayN / NekoBox 可导入
- [ ] 包含所有已配置的协议

---

*本文档持续更新。每个功能实现后更新状态和经验教训。*
*创建: 2026-03-28 | 作者: 宁莺*
