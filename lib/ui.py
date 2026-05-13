#!/usr/bin/env python3
"""ui.py - Terminal UI"""
RESET = ""; RED = ""; GREEN = ""; YELLOW = ""
BLUE = ""; CYAN = ""; BOLD = ""; DIM = ""

def red(s): print(f"{RED}{s}{RESET}")
def green(s): print(f"{GREEN}{s}{RESET}")
def yellow(s): print(f"{YELLOW}{s}{RESET}")
def cyan(s): print(f"{CYAN}{s}{RESET}")
def dim(s): print(f"{DIM}{s}{RESET}")

def banner(title):
    w = 50
    print()
    print(f"{CYAN}{'='*w}{RESET}")
    print(f"{CYAN}  {title}{RESET}")
    print(f"{CYAN}{'='*w}{RESET}")

def show_info(l, v): print(f"  {DIM}{l}:{RESET} {v}")

def show_status(l, v, ok):
    i = f"{GREEN}OK{RESET}" if ok else f"{RED}OFF{RESET}"
    print(f"  {i} {l}: {v}")

def progress(msg): print(f"  {YELLOW}... {msg}{RESET}", end="", flush=True)

def done(msg=""):
    print(f" {GREEN}OK{RESET} {msg}" if msg else f" {GREEN}OK{RESET}")

def fail(msg): print(f" {RED}FAIL{RESET} {msg}")

def prompt(t, d=""):
    h = f" [{d}]" if d else ""
    try:
        v = input(f"  {t}{h}: ").strip()
    except (EOFError, KeyboardInterrupt):
        print()
        return d
    return v if v else d

def prompt_int(t, d=0):
    v = prompt(t, str(d))
    try:
        return int(v)
    except (ValueError, TypeError):
        return d

def prompt_yn(t, d=True):
    h = "Y/n" if d else "y/N"
    v = prompt(f"{t} ({h})", "")
    if not v:
        return d
    return v.lower() in ("y", "yes")

def menu(title, opts, back="Back"):
    banner(title)
    for i, (l, _) in enumerate(opts, 1):
        print(f"  {CYAN}{i}{RESET}. {l}")
    print(f"  {DIM}0. {back}{RESET}")
    print()
    c = prompt_int("Choice", 0)
    if c == 0 or c > len(opts):
        return None
    return opts[c - 1][1]
