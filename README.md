# SB-Manager v2.0

sing-box 代理服务器管理工具，支持 VLESS-Reality + AnyTLS 双协议。

## 安装

```bash
# 需要 Python 3.9+ 和 sing-box
sbm install
```

## 命令

```bash
sbm                          # 交互式菜单
sbm status                   # 查看系统状态
sbm show [user]              # 显示节点分享链接
sbm user add <name>          # 添加用户
sbm user del <name>          # 删除用户
sbm user list                # 列出所有用户
sbm restart                  # 重启 sing-box
sbm stop / sbm start         # 停止/启动
sbm upgrade                  # 升级 sing-box 内核
sbm export <user> [dir]      # 导出客户端配置
sbm sub start [port]         # 启动订阅服务器
sbm backup                   # 备份配置
sbm logs [lines]             # 查看日志
```

## 订阅服务器

```bash
# 启动（需认证）
sbm sub start 18888

# 访问格式（带 token）
https://rack.snbar.top/auth/sub/<用户名>?token=<token>
https://rack.snbar.top/auth/sb/<用户名>?token=<token>
```

Token 首次启动自动生成，存储在 `/etc/s-box-sn/sub-token`。

## 文件结构

```
/etc/s-box-sn/
├── config.json       # 应用配置
├── sb.json           # sing-box 运行配置（自动生成）
├── users.json        # 用户数据
├── sing-box          # sing-box 二进制
├── cert.crt          # 自签证书（AnyTLS）
├── private.key       # 私钥
├── sub-token         # 订阅认证 token
└── output/           # 导出目录

/opt/sb-manager/
├── sbm               # 入口命令
└── lib/              # 模块库
```

## 协议

| 协议 | 端口 | 说明 |
|------|------|------|
| VLESS-Reality | 60379 | 直连，TLS 伪装 |
| AnyTLS | 42119 | 直连，自签证书 |

## 依赖

- Python 3.9+
- sing-box 1.13+
- OpenSSL（自签证书）
- Caddy（SSL 反向代理，可选）
