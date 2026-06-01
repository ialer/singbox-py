#!/usr/bin/env python3
"""warp.py - WARP routing toggle for sing-box"""
import json
import os
import shutil

from . import system
from .config import load_sb_config, save_sb_config

SB_JSON = system.SB_CONFIG_FILE
WARP_BACKUP = SB_JSON + ".warp-on"


def is_warp_enabled():
    """Check if WARP is currently enabled in sb.json"""
    sb = load_sb_config()
    if not sb:
        return False
    for ep in sb.get("endpoints", []):
        if ep.get("tag") == "warp-out":
            return True
    for rule in sb.get("route", {}).get("rules", []):
        if rule.get("outbound") == "warp-out":
            return True
    return False


def enable_warp():
    """Enable WARP routing by restoring from backup"""
    if not os.path.isfile(WARP_BACKUP):
        return False, "No WARP backup found (sb.json.warp-on)"
    with open(WARP_BACKUP) as f:
        sb = json.load(f)
    save_sb_config(sb)
    return True, "WARP enabled"


def disable_warp():
    """Disable WARP routing, save backup, switch all warp-out to direct"""
    sb = load_sb_config()
    if not sb:
        return False, "No sb.json found"

    # Save current as WARP ON backup
    shutil.copy2(SB_JSON, WARP_BACKUP)

    # Remove endpoints (WARP WireGuard tunnel)
    if "endpoints" in sb:
        del sb["endpoints"]

    # Replace all warp-out references with direct
    for rule in sb.get("route", {}).get("rules", []):
        if rule.get("outbound") == "warp-out":
            rule["outbound"] = "direct"

    # Ensure final is direct
    if "route" in sb:
        sb["route"]["final"] = "direct"

    save_sb_config(sb)
    return True, "WARP disabled (backup saved to sb.json.warp-on)"
