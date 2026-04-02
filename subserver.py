#!/usr/bin/env python3
"""
subserver.py - 轻量订阅HTTP服务器

提供 /sub/<username> 端点，返回Base64订阅内容。
客户端通过URL导入全部协议，更新订阅即可刷新配置。
"""

import os
import sys
import json
import base64
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import load_config, get_public_ip
from links import gen_all_links, gen_links_for_user
from users import load_users, get_user_by_name

SUB_PORT = 18888
SB_JSON = '/etc/s-box-sn/sb.json'

class SubHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass  # 静默日志

    def do_GET(self):
        path = self.path.strip('/')

        # /sub/<username> - 返回指定用户的订阅
        if path.startswith('sub/'):
            username = path[4:].strip()
            if not username:
                self.send_error(400, 'missing username')
                return

            try:
                config = load_config(SB_JSON)
                users_data = load_users()

                # all 用户返回全部用户的订阅
                if username == 'all':
                    all_links = {}
                    for u in users_data.get('users', []):
                        links = gen_links_for_user(config, u)
                        all_links.update(links)
                    links = all_links
                else:
                    user = get_user_by_name(username)
                    if not user:
                        self.send_error(404, 'user not found: ' + username)
                        return
                    links = gen_links_for_user(config, user)

                if not links:
                    self.send_error(404, 'no links generated')
                    return

                # Base64编码（标准订阅格式）
                sub_text = '\n'.join(links.values())
                sub_b64 = base64.b64encode(sub_text.encode('utf-8')).decode('utf-8')

                self.send_response(200)
                self.send_header('Content-Type', 'text/plain; charset=utf-8')
                self.send_header('Subscription-Userinfo', 'upload=0; download=0; total=0; expire=0')
                self.end_headers()
                self.wfile.write(sub_b64.encode('utf-8'))

            except Exception as e:
                self.send_error(500, str(e))

        # /clash/<username> - 返回Clash YAML配置
        elif path.startswith('clash/'):
            username = path[6:].strip()
            try:
                from clash import generate_clash_yaml_for_user
                config = load_config(SB_JSON)
                user = get_user_by_name(username)
                if not user:
                    self.send_error(404, 'user not found')
                    return
                ip = get_public_ip()
                yaml_content = generate_clash_yaml_for_user(config, user, ip)
                self.send_response(200)
                self.send_header('Content-Type', 'text/yaml; charset=utf-8')
                self.end_headers()
                self.wfile.write(yaml_content.encode('utf-8'))
            except Exception as e:
                self.send_error(500, str(e))

        # / - 简单状态页
        elif path == '' or path == 'status':
            users_data = load_users()
            ip = get_public_ip()
            users = users_data.get('users', [])

            # 读取 Argo 域名
            argo_domain = ''
            try:
                with open('/etc/s-box-sn/argo-sub-domain.txt', 'r') as f:
                    argo_domain = f.read().strip()
            except:
                pass

            base = ('https://' + argo_domain) if argo_domain else ('http://' + ip + ':' + str(SUB_PORT))

            lines = ['sing-box Subscription Server', 'VPS: ' + ip, '']
            if argo_domain:
                lines.append('Argo Domain: ' + argo_domain)
            lines.append('')
            lines.append('Subscription URLs:')
            for u in users:
                lines.append('  ' + u['name'] + ': ' + base + '/sub/' + u['name'])
            lines.append('')
            lines.append('Clash URLs:')
            for u in users:
                lines.append('  ' + u['name'] + ': ' + base + '/clash/' + u['name'])

            body = '\n'.join(lines)
            self.send_response(200)
            self.send_header('Content-Type', 'text/plain; charset=utf-8')
            self.end_headers()
            self.wfile.write(body.encode('utf-8'))
        else:
            self.send_error(404)


def start_server(port=SUB_PORT):
    """启动订阅服务器"""
    server = HTTPServer(('0.0.0.0', port), SubHandler)
    print('订阅服务器启动: http://0.0.0.0:{}'.format(port))
    print('状态页: http://localhost:{}/status'.format(port))
    server.serve_forever()


if __name__ == '__main__':
    port = int(sys.argv[1]) if len(sys.argv) > 1 else SUB_PORT
    start_server(port)
