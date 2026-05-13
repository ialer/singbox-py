# singbox-py

Sing-Box 多协议代理管理工具 — 支持 VLESS-Reality + AnyTLS，WARP 分流，SSL 订阅服务。

## 功能

- 🔐 VLESS-Reality / AnyTLS 协议管理
- 🌐 WARP 分流代理（ChatGPT/OpenAI 直连）
- 📱 订阅服务（HTTP/HTTPS + Token 认证）
- 🔗 节点链接 / Clash YAML / 订阅URL 生成
- 👥 多用户管理（添加/删除/列表/分享）
- 🛡️ 自动架构检测（amd64/arm64）+ 升级校验

## 快速开始

```bash
# 安装
sbm install

# 用户管理
sbm user add <name>       # 添加用户
sbm user del <name>       # 删除用户
sbm user list             # 查看用户列表

# 快速查看
sbm show [user]           # 查看所有节点链接
sbm share <user>          # 快速打印分享链接
sbm url <user>            # 快速打印订阅 URL

# 服务控制
sbm status                # 查看状态
sbm restart               # 重启服务
sbm stop / sbm start      # 停止/启动

# 订阅服务
sbm sub start [port]      # 启动订阅服务
sbm sub stop              # 停止订阅服务

# 其他
sbm export <user>         # 导出链接到文件
sbm upgrade               # 升级 sing-box
sbm migrate               # 从现有配置迁移
sbm backup                # 备份配置文件
sbm logs [n]              # 查看日志
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

## 安全说明

- 配置文件权限 0o600（仅 root 可读写）
- 订阅服务需要 Token 认证
- 升级下载自动校验 SHA256
- 自签证书包含 SAN 字段（兼容 Chrome 93+）

## License

MIT
