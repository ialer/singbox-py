#!/usr/bin/env python3
"""users.py - User management"""
import time
from .config import load_users_data,save_users_data,generate_uuid
def load_users(): return load_users_data().get("users",[])
def get_user(name):
    for u in load_users():
        if u["name"]==name: return u
    return None
def add_user(name):
    users=load_users()
    if any(u["name"]==name for u in users): raise ValueError("User exists: "+name)
    uuid=generate_uuid()
    user={"name":name,"uuid":uuid,"password":uuid,"created":int(time.time())}
    users.append(user); save_users_data({"users":users}); return user
def remove_user(name):
    users=load_users(); new=[u for u in users if u["name"]!=name]
    if len(new)==len(users): raise ValueError("User not found: "+name)
    save_users_data({"users":new})
