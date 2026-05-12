#!/usr/bin/env python3
"""certs.py - Certificate management"""
import os
from .system import run,CERT_FILE,KEY_FILE
def generate_self_signed():
    cmd="openssl req -x509 -nodes -days 3650 -newkey rsa:2048 -keyout {} -out {} -subj /CN=cloudflare-dns.com/O=Microsoft/C=US".format(KEY_FILE,CERT_FILE)
    out,rc=run(cmd)
    if rc!=0: raise RuntimeError("Cert failed: "+out)
    os.chmod(KEY_FILE,0o600)
def ensure_certs():
    if not os.path.isfile(CERT_FILE) or not os.path.isfile(KEY_FILE): generate_self_signed()
