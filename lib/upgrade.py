#!/usr/bin/env python3
"""upgrade.py - sing-box upgrade with architecture detection and checksum verification"""
import hashlib
import json
import os

from .system import run, run_raw, get_arch


def get_current_version():
    out, rc = run("/etc/s-box-sn/sing-box version")
    if rc == 0 and out:
        for l in out.split("\n"):
            if l.startswith("sing-box version"):
                return l.split()[-1]
    return None


def get_latest_version():
    """Fetch latest release tag from GitHub API."""
    out, rc = run(
        "curl -s https://api.github.com/repos/SagerNet/sing-box/releases/latest",
        timeout=15
    )
    if rc != 0 or not out:
        return None
    try:
        data = json.loads(out)
        tag = data.get("tag_name", "")
        return tag.lstrip("v") if tag else None
    except (json.JSONDecodeError, KeyError):
        return None


def _download_with_checksum(url, dest):
    """Download a file and verify its SHA256 checksum against .sha256 file."""
    # Download main file
    out, rc = run(f"curl -L -o {dest} {url}", timeout=120)
    if rc != 0:
        raise RuntimeError(f"Download failed: {url}")

    # Download checksum file
    sha256_url = url + ".sha256"
    out, rc = run(f"curl -s -L -o {dest}.sha256 {sha256_url}", timeout=30)

    # If checksum file exists, verify
    sha256_file = dest + ".sha256"
    if rc == 0 and os.path.isfile(sha256_file):
        with open(sha256_file) as f:
            expected = f.read().strip().split()[0]
        with open(dest, "rb") as f:
            actual = hashlib.sha256(f.read()).hexdigest()
        if actual != expected:
            os.remove(dest)
            raise RuntimeError(
                f"Checksum mismatch! Expected {expected[:16]}..., got {actual[:16]}..."
            )
    else:
        # No checksum available — log warning but proceed
        print("  Warning: No checksum file available, skipping verification")


def upgrade(ver=None):
    """Upgrade sing-box binary with architecture detection and checksum verification."""
    if not ver:
        ver = get_latest_version()
    if not ver:
        raise RuntimeError("Cannot get latest version")

    arch = get_arch()
    url = (
        f"https://github.com/SagerNet/sing-box/releases/download/v{ver}/"
        f"sing-box-{ver}-linux-{arch}.tar.gz"
    )

    print(f"  Downloading v{ver} for linux-{arch}...")
    binary_path = f"/tmp/sing-box-{ver}-linux-{arch}/sing-box"
    tar_path = "/tmp/sb-upgrade.tar.gz"

    try:
        _download_with_checksum(url, tar_path)
        out, rc = run(f"tar xzf {tar_path}", cwd="/tmp", timeout=30)
        if rc != 0:
            raise RuntimeError("Extract failed: " + out)

        if not os.path.isfile(binary_path):
            raise RuntimeError(f"Binary not found: {binary_path}")

        # Stop service, backup, replace, restart
        run("systemctl stop sing-box.service")
        run(f"cp /etc/s-box-sn/sing-box /etc/s-box-sn/sing-box.bak")
        run(f"cp {binary_path} /etc/s-box-sn/sing-box")
        run(f"chmod +x /etc/s-box-sn/sing-box")
        run("systemctl start sing-box.service")

        return get_current_version()
    finally:
        # Cleanup temp files
        for f in [tar_path, tar_path + ".sha256"]:
            if os.path.isfile(f):
                os.remove(f)
        import shutil
        for d in [f"/tmp/sing-box-{ver}-linux-{arch}"]:
            if os.path.isdir(d):
                shutil.rmtree(d, ignore_errors=True)


def check_python_version():
    out, _ = run("python3 --version")
    return out.strip() if out else None
