#!/usr/bin/env python3
"""subscription.py - Subscription HTTP server with token auth"""
import json,os,secrets,threading
from http.server import HTTPServer,BaseHTTPRequestHandler
from .config import load_config,load_users_data
from .sharing import gen_all_links,generate_subscription
_server=None; _server_thread=None
TOKEN_FILE="/etc/s-box-sn/sub-token"
def _load_token():
    if os.path.isfile(TOKEN_FILE):
        with open(TOKEN_FILE) as f: return f.read().strip()
    t=secrets.token_urlsafe(32)
    with open(TOKEN_FILE,"w") as f: f.write(t)
    os.chmod(TOKEN_FILE,0o600)
    return t
def get_token(): return _load_token()
class SubHandler(BaseHTTPRequestHandler):
    def log_message(self,*a): pass
    def do_GET(self):
        p=self.path.strip("/")
        if p=="" or p=="health": self._respond(200,"text/plain","OK"); return
        # 管理面板页面 - 需要 token 认证
        if p.startswith("admin"):
            token=self._extract_token()
            if token!=_load_token():
                self._respond(403,"text/plain","Forbidden. Need valid token."); return
            from .web import get_admin_page
            self._respond(200,"text/html",get_admin_page())
            return
        # API 请求处理
        if p.startswith("api/"):
            from .web import handle_api_request
            token=self._extract_token()
            api_path=p[4:].split("?")[0]  # 去掉查询字符串
            code,ct,body=handle_api_request(api_path,token)
            self._respond(code,ct,body)
            return
        # Extract token from query
        token=self._extract_token()
        if token!=_load_token():
            self._respond(403,"text/plain","Forbidden. Need valid token."); return
        parts=p.split("?")[0].split("/")
        if len(parts)<2: self._respond(400,"text/plain","Usage: /<action>/<user>?token=xxx"); return
        action,username=parts[0],parts[1]
        config=load_config(); ud=load_users_data()
        user=None
        for u in ud.get("users",[]):
            if u["name"]==username: user=u; break
        if not user: self._respond(404,"text/plain","User not found: "+username); return
        links=gen_all_links(config,user)
        if action=="sub": self._respond(200,"text/plain",generate_subscription(links))
        elif action=="sb":
            d={"user":user["name"],"domain":config.get("domain",""),"proxies":[{"name":l,"link":lk} for l,lk in links]}
            self._respond(200,"application/json",json.dumps(d,indent=2))
        elif action=="clash": self._respond(200,"text/yaml","\n".join(["proxies:"]+["  - name: "+l for l,_ in links]))
        else: self._respond(404,"text/plain","Unknown: "+action)
    def do_POST(self):
        p=self.path.strip("/")
        if not p.startswith("api/"):
            self._respond(404,"text/plain","Not found"); return
        token=self._extract_token()
        content_length=int(self.headers.get('Content-Length',0))
        body=self.rfile.read(content_length).decode('utf-8') if content_length>0 else ''
        from .web import handle_post_api
        api_path=p[4:]
        code,ct,response=handle_post_api(api_path,token,body)
        self._respond(code,ct,response)
    def do_DELETE(self):
        p=self.path.strip("/")
        if not p.startswith("api/"):
            self._respond(404,"text/plain","Not found"); return
        token=self._extract_token()
        from .web import handle_api_request
        api_path=p[4:]
        code,ct,body=handle_api_request(api_path,token)
        self._respond(code,ct,body)
    def _extract_token(self):
        if "?" in self.path:
            qs=self.path.split("?",1)[1]
            params=dict(x.split("=",1) for x in qs.split("&") if "=" in x)
            return params.get("token")
        return None
    def _respond(self,code,ct,body):
        self.send_response(code); self.send_header("Content-Type",ct+"; charset=utf-8")
        d=body.encode("utf-8"); self.send_header("Content-Length",str(len(d)))
        self.end_headers(); self.wfile.write(d)
def start_server(config,port=0):
    global _server,_server_thread
    if _server: stop_server()
    actual=port or config.get("subscription",{}).get("port",0)
    if not actual: import random; actual=random.randint(10000,65000)
    _server=HTTPServer(("0.0.0.0",actual),SubHandler)
    _server_thread=threading.Thread(target=_server.serve_forever,daemon=True)
    _server_thread.start(); return actual
def stop_server():
    global _server,_server_thread
    if _server: _server.shutdown(); _server=None; _server_thread=None
def get_subscription_urls(config,port):
    from .users import load_users
    domain=config.get("domain",config.get("server_ip","localhost"))
    token=_load_token(); urls=[]
    for u in load_users():
        n=u["name"]; base="https://{}".format(domain) if domain.count(".")>=2 else "http://{}:{}".format(domain,port)
        urls.append({"name":n,"sub_url":"{}/sub/{}?token={}".format(base,n,token),
            "singbox_url":"{}/sb/{}?token={}".format(base,n,token),
            "clash_url":"{}/clash/{}?token={}".format(base,n,token)})
    return urls
