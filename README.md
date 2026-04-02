# singbox-py

sing-box 多协议代理管理工具（Python 版本）— 服务端 + 客户端一体化

## 功能

- 🔗 节点链接生成（Vless-reality/Vmess-ws/Hysteria2/Tuic5/AnyTLS）
- 📋 Clash YAML 配置导出
- 📱 本地订阅生成 + HTTP 订阅服务器
- 📲 终端二维码显示
- 🌐 Argo 隧道管理
- 🔒 WARP 配置（AI 域名分流）
- 🖥️ sing-box 客户端配置生成
- 👥 多用户管理系统

## 文件结构

| 文件 | 行数 | 功能 |
|------|------|------|
| sb.py | 520 | 主入口，交互式菜单 + 命令行参数 |
| config.py | 315 | 配置加载、解析、公共 IP 检测 |
| clash.py | 382 | Clash YAML 导出（含 WARP 规则） |
| links.py | 275 | 节点链接生成（五协议） |
| client.py | 281 | sing-box 客户端配置生成 |
| subscribe.py | 129 | 订阅文件生成（Base64） |
| qrcode.py | 114 | 终端二维码显示 |
| argo.py | 312 | Cloudflare Argo 隧道管理 |
| warp.py | 351 | WARP WireGuard 配置 |
| subserver.py | 140 | HTTP 订阅服务器 |
| users.py | 275 | 多用户管理（UUID/流量） |

**总计：3094 行 Python**

## 使用

```bash
python3 sb.py                # 交互式菜单
python3 sb.py --nodes        # 查看节点信息
python3 sb.py --clash        # 生成 Clash 配置
python3 sb.py --client       # 生成 sing-box 客户端配置
python3 sb.py --sub          # 导出订阅文件
python3 sb.py --qr           # 生成二维码
python3 sb.py --users        # 用户管理
python3 sb.py --status       # 查看服务状态
```

## 依赖

- Python 3.8+
- qrcode (`pip install qrcode[pil]`)
- requests

## License

MIT
