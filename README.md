# singbox-py

sing-box 多协议代理管理工具（Python 版本）

## 功能

- 🔗 节点链接生成（Vless/Vmess/Hysteria2/Tuic5/AnyTLS）
- 📋 Clash 配置导出
- 📱 本地订阅生成
- 📲 二维码显示
- 🌐 Argo 隧道管理
- 🔒 WARP 配置
- 🖥️ sing-box 客户端配置生成

## 文件结构

| 文件 | 行数 | 功能 |
|------|------|------|
| sb.py | 272 | 主入口，交互式菜单 |
| config.py | 260 | 配置加载与解析 |
| links.py | 275 | 节点链接生成 |
| clash.py | 306 | Clash YAML 导出 |
| client.py | 281 | sing-box 客户端配置 |
| subscribe.py | 129 | 订阅文件生成 |
| qrcode.py | 92 | 二维码终端显示 |
| argo.py | 312 | Argo 隧道管理 |
| warp.py | 351 | WARP 配置管理 |

## 使用

```bash
python3 sb.py                # 交互式菜单
python3 sb.py --nodes        # 查看节点信息
python3 sb.py --clash        # 生成 Clash 配置
python3 sb.py --client       # 生成 sing-box 客户端配置
python3 sb.py --sub          # 导出订阅文件
python3 sb.py --qr           # 生成二维码
python3 sb.py --status       # 查看服务状态
```

## 依赖

- Python 3.8+
- qrcode (pip install qrcode[pil])
- requests

## License

MIT
