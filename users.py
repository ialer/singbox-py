#!/usr/bin/env python3
"""
users.py - 用户管理模块

管理 sing-box 多用户配置：
- 用户数据存储在 /etc/s-box-sn/users.json
- 同步修改 sb.json 中各协议入站的 users 数组
- 添加/删除用户时自动备份配置并验证
兼容 Python 3.6+，纯标准库实现。
"""

import json
import os
import shutil
import subprocess
import uuid
import sys

# 路径常量
USERS_FILE = "/etc/s-box-sn/users.json"
CONFIG_PATH = "/etc/s-box-sn/sb.json"
SING_BOX_BIN = "/etc/s-box-sn/sing-box"


def load_users():
    """加载用户数据。返回 dict: {"users": [{"name": str, "uuid": str, "password": str}]}"""
    if not os.path.isfile(USERS_FILE):
        return _init_users_from_config()
    with open(USERS_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)


def save_users(data):
    """保存用户数据到 users.json"""
    with open(USERS_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    os.chmod(USERS_FILE, 0o600)


def _init_users_from_config():
    """从现有 sb.json 初始化 users.json（首次运行）"""
    with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
        config = json.load(f)

    default_uuid = None
    for inbound in config.get('inbounds', []):
        if inbound.get('type') == 'vless':
            users = inbound.get('users', [])
            if users:
                default_uuid = users[0].get('uuid', '')
                break

    if not default_uuid:
        default_uuid = str(uuid.uuid4())

    data = {
        "users": [
            {
                "name": "default",
                "uuid": default_uuid,
                "password": default_uuid
            }
        ]
    }
    save_users(data)
    return data


def list_users():
    """列出所有用户。返回 list: [{"name": str, "uuid": str, "password": str}]"""
    data = load_users()
    return data.get('users', [])


def get_user_by_name(name):
    """根据名称查找用户。返回 dict or None"""
    for user in list_users():
        if user.get('name') == name:
            return user
    return None


def _backup_config():
    """备份 sb.json"""
    bak_path = CONFIG_PATH + '.bak'
    shutil.copy2(CONFIG_PATH, bak_path)


def _validate_config():
    """使用 sing-box check 验证配置。返回 bool"""
    result = subprocess.run(
        [SING_BOX_BIN, 'check', '-c', CONFIG_PATH],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True
    )
    return result.returncode == 0


def _add_user_to_config(user):
    """将用户添加到 sb.json 各协议入站的 users 数组。返回 bool"""
    _backup_config()

    with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
        config = json.load(f)

    for inbound in config.get('inbounds', []):
        proto = inbound.get('type', '')
        users = inbound.get('users', [])

        if proto == 'vless':
            users.append({"uuid": user['uuid'], "flow": "xtls-rprx-vision"})
        elif proto == 'vmess':
            users.append({"uuid": user['uuid'], "alterId": 0})
        elif proto == 'anytls':
            users.append({"password": user['password']})
        elif proto == 'hysteria2':
            users.append({"password": user['password']})
        elif proto == 'tuic':
            users.append({"uuid": user['uuid'], "password": user['password']})

        inbound['users'] = users

    with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=2, ensure_ascii=False)

    if not _validate_config():
        shutil.copy2(CONFIG_PATH + '.bak', CONFIG_PATH)
        print("配置验证失败，已回滚")
        return False
    return True


def _remove_user_from_config(user_uuid):
    """从 sb.json 各协议入站的 users 数组中移除指定 UUID 的用户。返回 bool"""
    _backup_config()

    with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
        config = json.load(f)

    for inbound in config.get('inbounds', []):
        proto = inbound.get('type', '')
        users = inbound.get('users', [])

        if proto == 'vless':
            users = [u for u in users if u.get('uuid') != user_uuid]
        elif proto == 'vmess':
            users = [u for u in users if u.get('uuid') != user_uuid]
        elif proto == 'anytls':
            users = [u for u in users if u.get('password') != user_uuid]
        elif proto == 'hysteria2':
            users = [u for u in users if u.get('password') != user_uuid]
        elif proto == 'tuic':
            users = [u for u in users if u.get('uuid') != user_uuid]

        inbound['users'] = users

    with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=2, ensure_ascii=False)

    if not _validate_config():
        shutil.copy2(CONFIG_PATH + '.bak', CONFIG_PATH)
        print("配置验证失败，已回滚")
        return False
    return True


def add_user(name):
    """添加新用户。返回 dict or None"""
    data = load_users()

    for u in data['users']:
        if u['name'] == name:
            print("用户 '{}' 已存在".format(name))
            return None

    new_uuid = str(uuid.uuid4())
    new_user = {"name": name, "uuid": new_uuid, "password": new_uuid}

    if not _add_user_to_config(new_user):
        print("添加用户到配置失败")
        return None

    data['users'].append(new_user)
    save_users(data)
    return new_user


def remove_user(name):
    """删除用户。返回 bool"""
    data = load_users()
    users = data.get('users', [])

    if name == 'default':
        print("不能删除默认用户 'default'")
        return False

    target = None
    for u in users:
        if u['name'] == name:
            target = u
            break

    if not target:
        print("用户 '{}' 不存在".format(name))
        return False

    if not _remove_user_from_config(target['uuid']):
        print("从配置中移除用户失败")
        return False

    data['users'] = [u for u in users if u['name'] != name]
    save_users(data)
    return True


def restart_singbox():
    """重启 sing-box 服务"""
    result = subprocess.run(
        ['systemctl', 'restart', 'sing-box'],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True
    )
    return result.returncode == 0




def rename_user(old_name, new_name):
    """Rename a user."""
    if old_name == new_name:
        return True
    if old_name == 'default':
        print("Cannot rename default user")
        return False

    data = load_users()
    found = False
    for u in data['users']:
        if u['name'] == old_name:
            u['name'] = new_name
            found = True
            break

    if not found:
        print("User '{}' not found".format(old_name))
        return False

    names = [u['name'] for u in data['users']]
    if names.count(new_name) > 1:
        print("Username '{}' already exists".format(new_name))
        return False

    save_users(data)
    return True


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("用法: python3 users.py [list|add <name>|remove <name>]")
        sys.exit(1)

    cmd = sys.argv[1]
    if cmd == 'list':
        users = list_users()
        print("用户列表 (共 {} 人)".format(len(users)))
        for u in users:
            print("  名称: {}  UUID: {}".format(u['name'], u['uuid']))
    elif cmd == 'add' and len(sys.argv) > 2:
        user = add_user(sys.argv[2])
        if user:
            print("用户 '{}' 已添加".format(user['name']))
            print("  UUID: {}".format(user['uuid']))
    elif cmd == 'remove' and len(sys.argv) > 2:
        if remove_user(sys.argv[2]):
            print("用户 '{}' 已删除".format(sys.argv[2]))
    else:
        print("用法: python3 users.py [list|add <name>|remove <name>]")
