# singbox-py

Sing-Box 多协议代理管理工具 — 支持 VLESS-Reality + AnyTLS，WARP 分流，SSL 订阅服务。

## 功能

- 🔐 VLESS-Reality / AnyTLS 协议管理
- 🌐 WARP 分流代理（ChatGPT/OpenAI 直连）
- 📱 订阅服务（HTTP/HTTPS + Token 认证）
- 🔗 节点链接 / Clash YAML / 订阅URL 生成
- 👥 多用户管理（添加/删除/列表/分享）
- 🛡️ 安全加固（安全配置、自动续约SSL）

## 快速开始

```bash
# 一键安装
bash install.sh

# 管理
sbm add <name>      # 添加用户
sbm del <name>      # 删除用户
sbm list            # 查看用户
sbm share <name>    # 分享链接
sbm url <name>      # 订阅URL
```

## 环境要求

- Python 3.9+
- sing-box 1.13+
- Caddy 2.x (SSL)

## 部署架构

```
中国设备 → VPS (sing-box VLESS-Reality/AnyTLS) → WARP → 目标网站
                 ↓
         Caddy (SSL) → 订阅服务
```

## 文件结构

```
/opt/sb-manager/          # 程序目录
├── sbm                   # 主入口
├── lib/                  # 功能模块
│   ├── config.py         # 配置管理
│   ├── protocols.py      # 协议生成
│   ├── users.py          # 用户管理
│   ├── sharing.py        # 分享链接
│   ├── subscription.py   # 订阅服务
│   ├── service.py        # 服务管理
│   ├── system.py         # 系统工具
│   ├── certs.py          # 证书管理
│   ├── upgrade.py        # 升级工具
│   └── ui.py             # 界面显示
/etc/s-box-sn/            # 配置目录
├── config.json           # 应用配置
├── sb.json               # sing-box配置
├── users.json            # 用户数据
└── sub-token             # 订阅Token
```

## License

MIT
