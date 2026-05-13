#!/usr/bin/env python3
"""certs.py - Certificate management with SAN support"""
import os
from .system import run, CERT_FILE, KEY_FILE


def generate_self_signed(domain="cloudflare-dns.com"):
    """Generate self-signed cert with SAN field (required by Chrome 93+)."""
    cmd = (
        f"openssl req -x509 -nodes -days 3650 -newkey rsa:2048 "
        f"-keyout {KEY_FILE} -out {CERT_FILE} "
        f"-subj '/CN={domain}/O=Microsoft/C=US' "
        f"-addext 'subjectAltName=DNS:{domain},IP:127.0.0.1'"
    )
    out, rc = run(cmd)
    if rc != 0:
        raise RuntimeError("Cert generation failed: " + out)
    os.chmod(KEY_FILE, 0o600)


def ensure_certs(domain="cloudflare-dns.com"):
    """Ensure certificates exist, regenerate if missing."""
    if not os.path.isfile(CERT_FILE) or not os.path.isfile(KEY_FILE):
        generate_self_signed(domain)
