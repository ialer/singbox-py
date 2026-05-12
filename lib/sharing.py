#!/usr/bin/env python3
"""sharing.py - Share link generation"""
def gen_vless_link(config,user,pc):
    port=pc["port"]; sni=pc.get("sni","apple.com"); uuid=user["uuid"]
    domain=config.get("domain",config.get("server_ip",""))
    pbk=config["public_key"]; sid=config["short_id"]
    params="encryption=none&flow=xtls-rprx-vision&security=reality&sni={}&fp=chrome&pbk={}&sid={}&type=tcp&headerType=none".format(sni,pbk,sid)
    name="vl-reality-"+config.get("hostname","node")
    return "vless://{}@{}:{}?{}#{}".format(uuid,domain,port,params,name)
def gen_anytls_link(config,user,pc):
    port=pc["port"]; pw=user.get("password",user["uuid"])
    domain=config.get("domain",config.get("server_ip","node"))
    params="sni={}&allowInsecure=1".format(domain)
    label=domain.split(".")[0] if "." in domain else domain
    return "anytls://{}@{}:{}?{}#anytls-{}".format(pw,domain,port,params,label)
def gen_all_links(config,user):
    links=[]; protos=config.get("protocols",{})
    vr=protos.get("vless_reality",{})
    if vr.get("enabled") and vr.get("port"): links.append(("VLESS-Reality",gen_vless_link(config,user,vr)))
    at=protos.get("anytls",{})
    if at.get("enabled") and at.get("port"): links.append(("AnyTLS",gen_anytls_link(config,user,at)))
    return links
def generate_subscription(links):
    import base64; text="\n".join(lk for _,lk in links)
    return base64.b64encode(text.encode()).decode()
