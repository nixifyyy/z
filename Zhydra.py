import tkinter as tk
from tkinter import ttk, simpledialog, messagebox
import threading
import time
import json
import math
import os
import shutil
import re
import random
import ctypes
import sys
import hashlib
import secrets
import hmac
import traceback
import tkinter as tk
from tkinter import simpledialog, messagebox
def main():

    def get_app_storage_dir():
        base_dir = os.getenv("APPDATA") or os.path.expanduser("~")
        app_dir = os.path.join(base_dir, "Zhydra")
        os.makedirs(app_dir, exist_ok=True)
        return app_dir

    APP_STORAGE_DIR = get_app_storage_dir()
    ACCOUNTS_DIR = os.path.join(APP_STORAGE_DIR, "accounts")
    LICENSE_FILE = os.path.join(APP_STORAGE_DIR, "license.json")
    SESSION_FILE = os.path.join(APP_STORAGE_DIR, "session.json")
    LEGACY_SETTINGS_FILE = os.path.join(APP_STORAGE_DIR, "settings.json")

    def ensure_app_storage():
        os.makedirs(APP_STORAGE_DIR, exist_ok=True)
        os.makedirs(ACCOUNTS_DIR, exist_ok=True)

    def read_json_file(file_path, fallback=None):
        fallback = {} if fallback is None else fallback
        try:
            with open(file_path, "r", encoding="utf-8") as file_obj:
                return json.load(file_obj)
        except:
            return fallback

    def write_json_file(file_path, payload):
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, "w", encoding="utf-8") as file_obj:
            json.dump(payload, file_obj, indent=2)

    def hash_value(value):
        return hashlib.sha256(str(value).encode("utf-8")).hexdigest()

    def parse_cps(value, fallback=5.0):
        """Parse CPS without imposing an arbitrary upper limit."""
        try:
            parsed = float(value)
            if math.isfinite(parsed) and parsed > 0:
                return parsed
        except (TypeError, ValueError):
            pass
        return fallback

    def sanitize_account_name(username):
        cleaned = re.sub(r"[^A-Za-z0-9 _-]", "", str(username or "").strip())
        cleaned = re.sub(r"\s+", " ", cleaned).strip()
        return cleaned[:32]

    def get_account_dir(username):
        return os.path.join(ACCOUNTS_DIR, sanitize_account_name(username))

    def get_account_profile_file(username):
        return os.path.join(get_account_dir(username), "profile.json")

    def get_account_settings_file(username):
        return os.path.join(get_account_dir(username), "settings.json")

    def load_license_state():
        license_data = read_json_file(LICENSE_FILE, None)
        if not isinstance(license_data, dict):
            return {"state": "uninitialized", "key": ""}
        license_key = str(license_data.get("key", "")).strip()
        authenticated = license_data.get("authenticated", False)
        if not license_key or not isinstance(authenticated, bool):
            return {"state": "uninitialized", "key": ""}
        state = "authenticated" if authenticated else "generated"
        return {"state": state, "key": license_key}

    def save_generated_license(license_key):
        write_json_file(LICENSE_FILE, {
            "key": license_key,
            "authenticated": False,
            "generated_at": int(time.time())
        })

    def complete_license_authentication(entered_key):
        license_state = load_license_state()
        if license_state["state"] != "generated" or not hmac.compare_digest(entered_key, license_state["key"]):
            return False
        write_json_file(LICENSE_FILE, {
            "key": license_state["key"],
            "authenticated": True,
            "authenticated_at": int(time.time())
        })
        return True

    def load_session_state():
        session = read_json_file(SESSION_FILE, {})
        username = sanitize_account_name(session.get("active_user", ""))
        return {
            "active_user": username or None,
            "logged_in_at": int(session.get("logged_in_at", 0) or 0)
        }

    def save_session_state(username):
        write_json_file(SESSION_FILE, {
            "active_user": sanitize_account_name(username),
            "logged_in_at": int(time.time())
        })

    def clear_session_state():
        write_json_file(SESSION_FILE, {
            "active_user": None,
            "logged_in_at": 0
        })

    def build_default_account_settings():
        return {
            "cps": 5.0,
            "mode": "Toggle",
            "cycle_duty": 0.1,
            "cps_jitter": 0.0,
            "click_button": "Left",
            "click_repeat": "Single",
            "toggle_key": None,
            "toggle_keys": [],
            "theme": "Dark",
            "advanced_settings_enabled": False,
            "smart_cycle_enabled": False,
            "launch_on_startup_enabled": False,
            "multi_bind_enabled": False,
            "sound_feedback_enabled": False,
            "macro_preview_enabled": False,
            "anti_afk_enabled": False,
            "anti_afk_interval": 60,
            "pause_on_focus_loss_enabled": False,
            "auto_limiter_enabled": False,
            "auto_limiter_clicks": 1000,
            "break_reminder_enabled": False,
            "break_reminder_interval": 1800,
            "mouse_jitter_enabled": False,
            "mouse_jitter_keybind": None,
            "mouse_jitter_mode": "Toggle",
            "mouse_jitter_speed": 35,
            "mouse_jitter_x": 4,
            "mouse_jitter_y": 4,
            "profiles": [],
            "active_profile_name": None,
            "macros": []
        }

    def load_account_profile(username):
        cleaned_username = sanitize_account_name(username)
        if not cleaned_username:
            return None
        profile = read_json_file(get_account_profile_file(cleaned_username), {})
        if not profile:
            return None
        profile["username"] = sanitize_account_name(profile.get("username", cleaned_username)) or cleaned_username
        return profile

    def list_accounts():
        ensure_app_storage()
        accounts = []
        try:
            for entry in os.listdir(ACCOUNTS_DIR):
                account_dir = os.path.join(ACCOUNTS_DIR, entry)
                if not os.path.isdir(account_dir):
                    continue
                profile = load_account_profile(entry)
                if profile:
                    accounts.append(profile)
        except:
            pass
        accounts.sort(key=lambda item: item.get("username", "").lower())
        return accounts

    def authenticate_account(username, password):
        profile = load_account_profile(username)
        if not profile:
            return False
        return profile.get("password_hash") == hash_value(password)

    def migrate_legacy_settings_if_needed(username):
        account_settings_file = get_account_settings_file(username)
        if os.path.exists(account_settings_file) or not os.path.exists(LEGACY_SETTINGS_FILE):
            return
        try:
            legacy_settings = read_json_file(LEGACY_SETTINGS_FILE, None)
            if isinstance(legacy_settings, dict) and legacy_settings:
                write_json_file(account_settings_file, legacy_settings)
        except:
            pass

    def create_account(username, password):
        cleaned_username = sanitize_account_name(username)
        if not cleaned_username:
            return False, "Username must use letters, numbers, spaces, underscores, or hyphens."
        if len(cleaned_username) < 3:
            return False, "Username must be at least 3 characters long."
        if len(str(password)) < 4:
            return False, "Password must be at least 4 characters long."
        if load_account_profile(cleaned_username):
            return False, "That account already exists on this PC."

        profile = {
            "username": cleaned_username,
            "password_hash": hash_value(password),
            "created_at": int(time.time()),
            "last_login_at": int(time.time())
        }
        write_json_file(get_account_profile_file(cleaned_username), profile)
        write_json_file(get_account_settings_file(cleaned_username), build_default_account_settings())
        return True, cleaned_username

    def mark_account_login(username):
        profile = load_account_profile(username)
        if not profile:
            return
        profile["last_login_at"] = int(time.time())
        write_json_file(get_account_profile_file(username), profile)

    def create_brand_window(title_text, width=980, height=620):
        root = tk.Tk()
        root.title(title_text)
        root.geometry(f"{width}x{height}")
        root.minsize(width, height)
        root.configure(bg="#05080e")
        root.resizable(False, False)

        try:
            root.iconname("Zhydra")
        except:
            pass

        root.update_idletasks()
        x = (root.winfo_screenwidth() // 2) - (width // 2)
        y = (root.winfo_screenheight() // 2) - (height // 2)
        root.geometry(f"{width}x{height}+{x}+{y}")

        background = tk.Canvas(root, bg="#05080e", highlightthickness=0, bd=0)
        background.place(relx=0, rely=0, relwidth=1, relheight=1)

        def draw_background():
            background.delete("all")
            width_now = max(width, root.winfo_width())
            height_now = max(height, root.winfo_height())
            for band in range(0, height_now, 4):
                factor = band / max(1, height_now)
                r = int(5 + (8 * factor))
                g = int(8 + (13 * factor))
                b = int(14 + (24 * factor))
                color = f"#{r:02x}{g:02x}{b:02x}"
                background.create_rectangle(0, band, width_now, band + 4, fill=color, outline=color)
            background.create_oval(-170, -120, 360, 410, fill="#0a1d2b", outline="")
            background.create_oval(width_now - 390, -110, width_now + 130, 410, fill="#082e39", outline="")
            background.create_oval(width_now - 300, height_now - 210, width_now + 100, height_now + 120, fill="#102332", outline="")
            background.create_line(52, height_now - 74, width_now - 52, height_now - 74, fill="#123242", width=1)
            background.create_rectangle(28, 28, width_now - 28, height_now - 28, outline="#102638", width=1)
            background.create_rectangle(42, 42, width_now - 42, height_now - 42, outline="#091722", width=1)

        draw_background()
        root.bind("<Configure>", lambda _event: draw_background())
        return root

    def style_modal_entry(widget):
        widget.configure(
            bd=0,
            relief="flat",
            highlightthickness=1,
            highlightbackground="#1b3d4c",
            highlightcolor="#5ee7ea",
            bg="#08121b",
            readonlybackground="#08121b",
            fg="#edfaff",
            insertbackground="#edfaff",
            font=("Segoe UI", 11)
        )

    def style_modal_button(button, kind="primary"):
        palette = {
            "primary": {"bg": "#54d6d2", "fg": "#041014", "hover": "#7ce8e1", "border": "#a2fff7"},
            "secondary": {"bg": "#0b1722", "fg": "#c6e7ed", "hover": "#122635", "border": "#214454"},
            "danger": {"bg": "#4b1820", "fg": "#ffe9ec", "hover": "#63212c", "border": "#8f3343"}
        }
        colors = palette.get(kind, palette["primary"])
        button.configure(
            bd=0,
            relief="flat",
            bg=colors["bg"],
            fg=colors["fg"],
            activebackground=colors["hover"],
            activeforeground=colors["fg"],
            highlightthickness=0,
            highlightbackground=colors["border"],
            cursor="hand2",
            font=("Segoe UI", 10, "bold"),
            padx=14,
            pady=10
        )

        def on_enter(_event=None):
            button.configure(bg=colors["hover"])

        def on_leave(_event=None):
            button.configure(bg=colors["bg"])

        button.bind("<Enter>", on_enter, add="+")
        button.bind("<Leave>", on_leave, add="+")

    def show_generate_license_screen():
        root = create_brand_window("Zhydra Setup", width=1040, height=680)
        result = {"continue": False}
        status_var = tk.StringVar(value="Generate a local Authentication Key to begin setup.")
        key_var = tk.StringVar()

        shell = tk.Frame(root, bg="#07111f")
        shell.pack(fill="both", expand=True, padx=48, pady=48)
        shell.grid_columnconfigure(0, weight=9)
        shell.grid_columnconfigure(1, weight=11)
        shell.grid_rowconfigure(0, weight=1)

        hero = tk.Frame(shell, bg="#0a1730", highlightthickness=0)
        hero.grid(row=0, column=0, sticky="nsew", padx=(0, 18))
        hero.grid_rowconfigure(4, weight=1)

        badge = tk.Label(hero, text="ZHYDRA  /  INITIAL SETUP", font=("Segoe UI", 9, "bold"), bg="#113050", fg="#bfefff", padx=12, pady=6)
        badge.pack(anchor="w", padx=24, pady=(24, 14))
        hero_title = tk.Label(hero, text="Welcome to Zhydra", font=("Bahnschrift SemiBold", 28), bg="#0a1730", fg="#f7fcff", justify="left")
        hero_title.pack(anchor="w", padx=28)
        hero_copy = tk.Label(
            hero,
                text="Complete this one-time local setup to keep your Zhydra workspace ready on this device. No server, account, or network connection is involved.",
            font=("Segoe UI", 10),
            bg="#0a1730",
            fg="#8eb5d1",
            justify="left",
            wraplength=330
        )
        hero_copy.pack(anchor="w", padx=24, pady=(14, 18))

        bullets = [
                "Your key is generated securely on this device",
                "The key is saved locally in %APPDATA%\\Zhydra\\license.json",
                "After one successful verification, setup never appears again"
        ]
        for bullet in bullets:
            tk.Label(hero, text=f"• {bullet}", font=("Segoe UI", 9), bg="#0a1730", fg="#d9f4ff", anchor="w", justify="left", wraplength=330).pack(anchor="w", padx=24, pady=4)

        form_shadow = tk.Frame(shell, bg="#081320")
        form_shadow.grid(row=0, column=1, sticky="nsew", padx=(14, 0), pady=(10, 10))
        form_card = tk.Frame(form_shadow, bg="#0b1a2c", highlightthickness=1, highlightbackground="#2e7b8b")
        form_card.pack(fill="both", expand=True, padx=(0, 10), pady=(0, 10))

        tk.Label(form_card, text="Finish setup", font=("Bahnschrift SemiBold", 22), bg="#0b1a2c", fg="#f7fcff").pack(anchor="w", padx=26, pady=(28, 8))
        helper_text = "Generate your Authentication Key below. Save it somewhere secure, then continue to Zhydra."
        helper = tk.Label(form_card, text=helper_text, font=("Segoe UI", 10), bg="#0b1a2c", fg="#7394ad", justify="left", wraplength=360)
        helper.pack(anchor="w", padx=26, pady=(0, 18))
        tk.Label(form_card, text="AUTHENTICATION KEY", font=("Segoe UI", 9, "bold"), bg="#0b1a2c", fg="#95cce3").pack(anchor="w", padx=26)
        key_entry = tk.Entry(form_card, textvariable=key_var, show="", width=34, state="readonly")
        style_modal_entry(key_entry)
        key_entry.pack(fill="x", padx=26, pady=(8, 12), ipady=10)

        def copy_key():
            if key_var.get():
                root.clipboard_clear()
                root.clipboard_append(key_var.get())
                status_var.set("Authentication Key copied to the clipboard.")

        copy_button = tk.Button(form_card, text="Copy Key", command=copy_key, state="disabled")
        style_modal_button(copy_button, "secondary")
        copy_button.pack(anchor="w", padx=26, pady=(0, 6))

        status_label = tk.Label(form_card, textvariable=status_var, font=("Segoe UI", 9), bg="#0b1a2c", fg="#ffcf6e", justify="left", wraplength=320)
        status_label.pack(anchor="w", padx=26, pady=(16, 8))

        actions = tk.Frame(form_card, bg="#0b1a2c")
        actions.pack(fill="x", padx=26, pady=(16, 24))
        actions.grid_columnconfigure(0, weight=1)
        actions.grid_columnconfigure(1, weight=0)
        actions.grid_columnconfigure(2, weight=0)

        def generate_key():
            generated_key = "zhy_" + secrets.token_urlsafe(24)
            save_generated_license(generated_key)
            key_var.set(generated_key)
            key_entry.configure(state="normal")
            key_entry.configure(state="readonly")
            copy_button.configure(state="normal")
            continue_button.configure(state="normal")
            status_var.set("Key generated and saved locally. Copy it before continuing.")

        def continue_setup():
            if not key_var.get():
                status_var.set("Generate an Authentication Key before continuing.")
                key_entry.focus_set()
                return
            result["continue"] = True
            root.destroy()

        cancel_button = tk.Button(actions, text="Exit", command=root.destroy)
        style_modal_button(cancel_button, "secondary")
        cancel_button.grid(row=0, column=0, sticky="w")

        continue_button = tk.Button(actions, text="Continue", command=continue_setup, state="disabled")
        style_modal_button(continue_button, "primary")
        continue_button.grid(row=0, column=1, sticky="e")
        generate_button = tk.Button(actions, text="Generate Authentication Key", command=generate_key)
        style_modal_button(generate_button, "primary")
        generate_button.grid(row=0, column=1, sticky="e", padx=(0, 10))
        continue_button.grid(row=0, column=2, sticky="e")

        root.bind("<Return>", lambda _event: continue_setup())
        root.protocol("WM_DELETE_WINDOW", root.destroy)
        root.after(40, key_entry.focus_set)
        root.mainloop()
        return result["continue"] and show_enter_license_screen()

    def show_enter_license_screen():
        license_state = load_license_state()
        if license_state["state"] != "generated":
            return license_state["state"] == "authenticated"

        root = create_brand_window("Zhydra Authentication", width=760, height=520)
        result = {"authenticated": False}
        key_var = tk.StringVar()
        status_var = tk.StringVar(value="Enter the Authentication Key generated during initial setup.")

        shell = tk.Frame(root, bg="#07111f")
        shell.pack(fill="both", expand=True, padx=58, pady=58)
        shell.grid_columnconfigure(0, weight=1)
        shell.grid_rowconfigure(0, weight=1)

        card = tk.Frame(shell, bg="#0b1a2c", highlightthickness=1, highlightbackground="#2e7b8b")
        card.grid(row=0, column=0, sticky="nsew")
        tk.Label(card, text="ZHYDRA  /  ONE-TIME VERIFICATION", font=("Segoe UI", 9, "bold"), bg="#113050", fg="#bfefff", padx=12, pady=6).pack(anchor="w", padx=34, pady=(34, 18))
        tk.Label(card, text="Enter your Key", font=("Bahnschrift SemiBold", 28), bg="#0b1a2c", fg="#f7fcff").pack(anchor="w", padx=34)
        tk.Label(card, text="Verify this local installation once to open the full Zhydra workspace. This screen will not appear again after a successful match.", font=("Segoe UI", 10), bg="#0b1a2c", fg="#8eb5d1", justify="left", wraplength=560).pack(anchor="w", padx=34, pady=(12, 26))
        tk.Label(card, text="AUTHENTICATION KEY", font=("Segoe UI", 9, "bold"), bg="#0b1a2c", fg="#95cce3").pack(anchor="w", padx=34)
        key_entry = tk.Entry(card, textvariable=key_var, show="", width=44)
        style_modal_entry(key_entry)
        key_entry.pack(fill="x", padx=34, pady=(8, 12), ipady=11)
        tk.Label(card, textvariable=status_var, font=("Segoe UI", 9), bg="#0b1a2c", fg="#ffcf6e", justify="left", wraplength=560).pack(anchor="w", padx=34, pady=(6, 18))

        actions = tk.Frame(card, bg="#0b1a2c")
        actions.pack(fill="x", padx=34, pady=(0, 32))
        cancel_button = tk.Button(actions, text="Exit", command=root.destroy)
        style_modal_button(cancel_button, "secondary")
        cancel_button.pack(side="left")

        def submit_key():
            if complete_license_authentication(key_var.get().strip()):
                result["authenticated"] = True
                root.destroy()
                return
            status_var.set("That Authentication Key does not match this installation.")
            key_var.set("")
            key_entry.focus_set()

        continue_button = tk.Button(actions, text="Login / Continue", command=submit_key)
        style_modal_button(continue_button, "primary")
        continue_button.pack(side="right")
        root.bind("<Return>", lambda _event: submit_key())
        root.bind("<Escape>", lambda _event: root.destroy())
        root.protocol("WM_DELETE_WINDOW", root.destroy)
        root.after(40, key_entry.focus_set)
        root.mainloop()
        return result["authenticated"]

    def show_auth_screen():
        existing_accounts = list_accounts()
        root = create_brand_window("Zhydra Account Access", width=1080, height=680)
        result = {"username": None}
        mode_var = tk.StringVar(value="login" if existing_accounts else "signup")
        username_var = tk.StringVar(value=existing_accounts[0]["username"] if existing_accounts else "")
        password_var = tk.StringVar()
        confirm_password_var = tk.StringVar()
        status_var = tk.StringVar(value="Sign in to your Zhydra workspace." if existing_accounts else "Create the first local Zhydra account for this PC.")

        auth_style = ttk.Style(root)
        try:
            auth_style.theme_use("clam")
        except:
            pass
        auth_style.configure(
            "Auth.Vertical.TScrollbar",
            gripcount=0,
            background="#16384a",
            troughcolor="#07131d",
            bordercolor="#07131d",
            arrowcolor="#8cebe7",
            darkcolor="#16384a",
            lightcolor="#16384a",
            relief="flat",
            borderwidth=0,
            arrowsize=11
        )

        viewport = tk.Frame(root, bg="#07131d")
        viewport.pack(fill="both", expand=True, padx=28, pady=28)

        page_canvas = tk.Canvas(viewport, bg="#07131d", highlightthickness=0, bd=0, relief="flat")
        page_scrollbar = ttk.Scrollbar(
            viewport,
            orient="vertical",
            command=page_canvas.yview,
            style="Auth.Vertical.TScrollbar"
        )
        page_canvas.configure(yscrollcommand=page_scrollbar.set)
        page_canvas.pack(side="left", fill="both", expand=True, padx=(0, 8))
        page_scrollbar.pack(side="right", fill="y", padx=(0, 2))

        shell = tk.Frame(page_canvas, bg="#07131d")
        shell_window = page_canvas.create_window((12, 12), window=shell, anchor="nw")
        shell.grid_columnconfigure(0, weight=7)
        shell.grid_columnconfigure(1, weight=5)

        def refresh_auth_scrollregion(_event=None):
            page_canvas.configure(scrollregion=page_canvas.bbox("all"))

        def resize_auth_shell(event):
            page_canvas.itemconfigure(shell_window, width=max(event.width - 24, 1))

        def on_auth_page_mousewheel(event):
            if existing_accounts and event.widget == account_listbox:
                return None
            if getattr(event, "num", None) == 4:
                page_canvas.yview_scroll(-1, "units")
            elif getattr(event, "num", None) == 5:
                page_canvas.yview_scroll(1, "units")
            elif event.delta:
                page_canvas.yview_scroll(int(-event.delta / 120), "units")
            return "break"

        def close_auth_screen():
            root.unbind_all("<MouseWheel>")
            root.unbind_all("<Button-4>")
            root.unbind_all("<Button-5>")
            root.destroy()

        shell.bind("<Configure>", refresh_auth_scrollregion, add="+")
        page_canvas.bind("<Configure>", resize_auth_shell, add="+")
        root.bind_all("<MouseWheel>", on_auth_page_mousewheel, add="+")
        root.bind_all("<Button-4>", on_auth_page_mousewheel, add="+")
        root.bind_all("<Button-5>", on_auth_page_mousewheel, add="+")

        hero = tk.Frame(shell, bg="#07131d", highlightthickness=1, highlightbackground="#1b5362")
        hero.grid(row=0, column=0, sticky="nsew", padx=(0, 12))

        tk.Label(hero, text="ZHYDRA  /  CONTROL HUB", font=("Segoe UI", 9, "bold"), bg="#0c2730", fg="#8cebe7", padx=12, pady=6).pack(anchor="w", padx=26, pady=(26, 18))
        tk.Label(hero, text="Your workspace,\nready when you are.", font=("Bahnschrift SemiBold", 29), bg="#07131d", fg="#f2fbfc", justify="left", wraplength=470).pack(anchor="w", padx=26)
        tk.Label(
            hero,
            text="Log in to Zhydra to load your clicks, binds, macros, and preferences without rebuilding your setup each time. If you're new, create an account and start with a clean local profile in seconds.",
            font=("Segoe UI", 11),
            bg="#07131d",
            fg="#86aab2",
            justify="left",
            wraplength=430
        ).pack(anchor="w", padx=28, pady=(18, 24))

        info_grid = tk.Frame(hero, bg="#07131d")
        info_grid.pack(fill="x", padx=26, pady=(4, 20))

        cards = [
            ("Activation", "Premium access keeps the full Zhydra experience ready on this device"),
            ("Sessions", "Log back in faster with the last account restored automatically"),
            ("Accounts", f"{len(existing_accounts)} local account{'s' if len(existing_accounts) != 1 else ''} detected")
        ]
        for title_text, body_text in cards:
            card = tk.Frame(info_grid, bg="#0a1c27", highlightthickness=1, highlightbackground="#123444")
            card.pack(fill="x", pady=4)
            tk.Label(card, text=title_text.upper(), font=("Segoe UI", 8, "bold"), bg="#0a1c27", fg="#8cebe7").pack(anchor="w", padx=14, pady=(10, 2))
            tk.Label(card, text=body_text, font=("Segoe UI", 9), bg="#0a1c27", fg="#7f9da5", justify="left", wraplength=430).pack(anchor="w", padx=14, pady=(0, 10))

        if existing_accounts:
            quick_access = tk.Frame(hero, bg="#07131d")
            quick_access.pack(fill="both", expand=True, padx=26, pady=(0, 26))
            tk.Label(quick_access, text="RECENT LOCAL ACCOUNTS", font=("Segoe UI", 8, "bold"), bg="#07131d", fg="#8cebe7").pack(anchor="w")
            account_list_wrap = tk.Frame(quick_access, bg="#07131d")
            account_list_wrap.pack(fill="both", expand=True, pady=(10, 0))
            account_scrollbar = tk.Scrollbar(
                account_list_wrap,
                orient="vertical",
                bg="#102631",
                troughcolor="#060b11",
                activebackground="#54d6d2",
                bd=0,
                highlightthickness=0,
                relief="flat"
            )
            account_listbox = tk.Listbox(
                account_list_wrap,
                bg="#0a1c27",
                fg="#d8f1f3",
                selectbackground="#54d6d2",
                selectforeground="#041014",
                bd=0,
                highlightthickness=1,
                highlightbackground="#123444",
                font=("Segoe UI", 10),
                activestyle="none",
                height=8,
                yscrollcommand=account_scrollbar.set
            )
            account_scrollbar.configure(command=account_listbox.yview)
            account_listbox.pack(side="left", fill="both", expand=True)
            account_scrollbar.pack(side="right", fill="y", padx=(10, 0))
            for index, profile in enumerate(existing_accounts):
                account_listbox.insert(tk.END, profile.get("username", ""))
                if index == 0:
                    account_listbox.selection_set(index)

            def on_account_list_mousewheel(event):
                if getattr(event, "num", None) == 4:
                    account_listbox.yview_scroll(-1, "units")
                elif getattr(event, "num", None) == 5:
                    account_listbox.yview_scroll(1, "units")
                elif event.delta:
                    account_listbox.yview_scroll(int(-event.delta / 120), "units")
                return "break"

            def apply_account_selection(_event=None):
                selection = account_listbox.curselection()
                if not selection:
                    return
                username_var.set(account_listbox.get(selection[0]))

            account_listbox.bind("<Enter>", lambda _event: account_listbox.focus_set(), add="+")
            account_listbox.bind("<MouseWheel>", on_account_list_mousewheel, add="+")
            account_listbox.bind("<Button-4>", on_account_list_mousewheel, add="+")
            account_listbox.bind("<Button-5>", on_account_list_mousewheel, add="+")
            account_listbox.bind("<<ListboxSelect>>", apply_account_selection)
            account_listbox.bind("<Double-Button-1>", lambda _event: submit())
        else:
            account_listbox = None

        form_shadow = tk.Frame(shell, bg="#07101b")
        form_shadow.grid(row=0, column=1, sticky="nsew", padx=(12, 0), pady=(14, 14))
        form_card = tk.Frame(form_shadow, bg="#091a27", highlightthickness=1, highlightbackground="#2a6074")
        form_card.pack(fill="both", expand=True, padx=(0, 8), pady=(0, 8))

        toggle_row = tk.Frame(form_card, bg="#091a27")
        toggle_row.pack(fill="x", padx=28, pady=(28, 20))

        login_toggle = tk.Button(toggle_row, text="Log In", command=lambda: set_mode("login"))
        signup_toggle = tk.Button(toggle_row, text="Sign Up", command=lambda: set_mode("signup"))
        style_modal_button(login_toggle, "secondary")
        style_modal_button(signup_toggle, "secondary")
        login_toggle.pack(side="left", padx=(0, 10))
        signup_toggle.pack(side="left")

        title_label = tk.Label(form_card, text="", font=("Bahnschrift SemiBold", 22), bg="#091a27", fg="#f2fbfc")
        title_label.pack(anchor="w", padx=28)

        intro_label = tk.Label(form_card, text="", font=("Segoe UI", 10), bg="#091a27", fg="#7899a3", justify="left", wraplength=360)
        intro_label.pack(anchor="w", padx=28, pady=(10, 22))

        tk.Label(form_card, text="USERNAME", font=("Segoe UI", 8, "bold"), bg="#091a27", fg="#8cebe7").pack(anchor="w", padx=28)
        username_entry = tk.Entry(form_card, textvariable=username_var)
        style_modal_entry(username_entry)
        username_entry.pack(fill="x", padx=28, pady=(7, 16), ipady=9)

        tk.Label(form_card, text="PASSWORD", font=("Segoe UI", 8, "bold"), bg="#091a27", fg="#8cebe7").pack(anchor="w", padx=28)
        password_entry = tk.Entry(form_card, textvariable=password_var, show="*")
        style_modal_entry(password_entry)
        password_entry.pack(fill="x", padx=28, pady=(7, 16), ipady=9)

        confirm_wrap = tk.Frame(form_card, bg="#091a27")
        confirm_label = tk.Label(confirm_wrap, text="CONFIRM PASSWORD", font=("Segoe UI", 8, "bold"), bg="#091a27", fg="#8cebe7")
        confirm_entry = tk.Entry(confirm_wrap, textvariable=confirm_password_var, show="*")
        style_modal_entry(confirm_entry)
        confirm_label.pack(anchor="w")
        confirm_entry.pack(fill="x", pady=(8, 0), ipady=9)
        confirm_wrap.pack(fill="x", padx=28, pady=(0, 16))

        status_label = tk.Label(form_card, textvariable=status_var, font=("Segoe UI", 9), bg="#091a27", fg="#e5bd6b", justify="left", wraplength=360)
        status_label.pack(anchor="w", padx=28, pady=(8, 8))

        actions = tk.Frame(form_card, bg="#091a27")
        actions.pack(fill="x", padx=28, pady=(16, 28))
        actions.grid_columnconfigure(0, weight=1)
        actions.grid_columnconfigure(1, weight=0)

        cancel_button = tk.Button(actions, text="Exit", command=close_auth_screen)
        style_modal_button(cancel_button, "secondary")
        cancel_button.grid(row=0, column=0, sticky="w")

        submit_button = tk.Button(actions, text="Continue", command=lambda: submit())
        style_modal_button(submit_button, "primary")
        submit_button.grid(row=0, column=1, sticky="e")

        def set_mode(mode_name):
            mode_var.set(mode_name)
            is_signup = mode_name == "signup"
            login_toggle.configure(bg="#122f38" if not is_signup else "#0b1722")
            signup_toggle.configure(bg="#122f38" if is_signup else "#0b1722")
            title_label.configure(text="Log in to Zhydra" if mode_name == "login" else "Create a Zhydra account")
            intro_label.configure(text="Sign in to reopen your Zhydra setup, keep your preferred controls ready, and get back to clicking faster." if mode_name == "login" else "Create a Zhydra account to start fresh, save your preferred controls, and keep this device ready for future sessions.")
            if is_signup:
                confirm_wrap.pack(fill="x", padx=30, pady=(0, 14))
                submit_button.configure(text="Create Account")
                status_var.set("Create your Zhydra login for this PC and start building your setup.")
            else:
                confirm_wrap.pack_forget()
                submit_button.configure(text="Log In")
                status_var.set("Sign in to continue with your Zhydra setup.")

        def submit():
            username = sanitize_account_name(username_var.get())
            password = password_var.get()
            if not username:
                status_var.set("Enter a username to continue.")
                username_entry.focus_set()
                return
            if not password:
                status_var.set("Enter a password to continue.")
                password_entry.focus_set()
                return

            if mode_var.get() == "signup":
                if password != confirm_password_var.get():
                    status_var.set("Passwords do not match.")
                    confirm_entry.focus_set()
                    return
                created, payload = create_account(username, password)
                if not created:
                    status_var.set(payload)
                    return
                username = payload
            else:
                if not authenticate_account(username, password):
                    status_var.set("The username or password is incorrect for this device.")
                    password_var.set("")
                    password_entry.focus_set()
                    return

            mark_account_login(username)
            save_session_state(username)
            result["username"] = username
            close_auth_screen()

        set_mode(mode_var.get())
        root.bind("<Return>", lambda _event: submit())
        root.protocol("WM_DELETE_WINDOW", close_auth_screen)
        root.after_idle(refresh_auth_scrollregion)
        root.after(40, username_entry.focus_set)
        root.mainloop()
        return result["username"]

    high_resolution_timer_enabled = False
    disable_high_resolution_timer_func = None

    def _run(active_account_username):
        nonlocal high_resolution_timer_enabled, disable_high_resolution_timer_func
        from pynput import mouse, keyboard
        from pynput.mouse import Controller, Button

        def get_settings_file():
            ensure_app_storage()
            migrate_legacy_settings_if_needed(active_account_username)
            return get_account_settings_file(active_account_username)

        def hide_console_window():
            if os.name != "nt":
                return
            try:
                hwnd = ctypes.windll.kernel32.GetConsoleWindow()
                if hwnd:
                    ctypes.windll.user32.ShowWindow(hwnd, 0)
            except:
                pass

        def enable_high_resolution_timer():
            if os.name != "nt":
                return False
            try:
                return ctypes.windll.winmm.timeBeginPeriod(1) == 0
            except:
                return False

        def disable_high_resolution_timer():
            if os.name != "nt":
                return
            try:
                ctypes.windll.winmm.timeEndPeriod(1)
            except:
                pass

        disable_high_resolution_timer_func = disable_high_resolution_timer

        def set_current_thread_high_priority():
            if os.name != "nt":
                return
            try:
                ctypes.windll.kernel32.SetThreadPriority(
                    ctypes.windll.kernel32.GetCurrentThread(),
                    2
                )
            except:
                pass

        if os.name == "nt":
            INPUT_MOUSE = 0
            INPUT_KEYBOARD = 1
            MOUSEEVENTF_LEFTDOWN = 0x0002
            MOUSEEVENTF_MOVE = 0x0001
            MOUSEEVENTF_LEFTUP = 0x0004
            MOUSEEVENTF_RIGHTDOWN = 0x0008
            MOUSEEVENTF_RIGHTUP = 0x0010
            MOUSEEVENTF_MIDDLEDOWN = 0x0020
            MOUSEEVENTF_MIDDLEUP = 0x0040
            KEYEVENTF_KEYUP = 0x0002
            KEYEVENTF_UNICODE = 0x0004
            ULONG_PTR = ctypes.c_ulonglong if ctypes.sizeof(ctypes.c_void_p) == 8 else ctypes.c_ulong

            class MOUSEINPUT(ctypes.Structure):
                _fields_ = [
                    ("dx", ctypes.c_long),
                    ("dy", ctypes.c_long),
                    ("mouseData", ctypes.c_ulong),
                    ("dwFlags", ctypes.c_ulong),
                    ("time", ctypes.c_ulong),
                    ("dwExtraInfo", ULONG_PTR)
                ]

            class KEYBDINPUT(ctypes.Structure):
                _fields_ = [
                    ("wVk", ctypes.c_ushort),
                    ("wScan", ctypes.c_ushort),
                    ("dwFlags", ctypes.c_ulong),
                    ("time", ctypes.c_ulong),
                    ("dwExtraInfo", ULONG_PTR)
                ]

            class INPUTUNION(ctypes.Union):
                _fields_ = [("mi", MOUSEINPUT), ("ki", KEYBDINPUT)]

            class INPUT(ctypes.Structure):
                _anonymous_ = ("union",)
                _fields_ = [
                    ("type", ctypes.c_ulong),
                    ("union", INPUTUNION)
                ]

            native_mouse_button_flags = {
                Button.left: (MOUSEEVENTF_LEFTDOWN, MOUSEEVENTF_LEFTUP),
                Button.right: (MOUSEEVENTF_RIGHTDOWN, MOUSEEVENTF_RIGHTUP),
                Button.middle: (MOUSEEVENTF_MIDDLEDOWN, MOUSEEVENTF_MIDDLEUP)
            }
            native_keyboard_virtual_keys = {
                "backspace": 0x08,
                "tab": 0x09,
                "enter": 0x0D,
                "shift": 0x10,
                "shift_l": 0xA0,
                "shift_r": 0xA1,
                "ctrl": 0x11,
                "ctrl_l": 0xA2,
                "ctrl_r": 0xA3,
                "alt": 0x12,
                "alt_l": 0xA4,
                "alt_r": 0xA5,
                "pause": 0x13,
                "caps_lock": 0x14,
                "esc": 0x1B,
                "space": 0x20,
                "page_up": 0x21,
                "page_down": 0x22,
                "end": 0x23,
                "home": 0x24,
                "left": 0x25,
                "up": 0x26,
                "right": 0x27,
                "down": 0x28,
                "insert": 0x2D,
                "delete": 0x2E,
                "cmd": 0x5B,
                "cmd_l": 0x5B,
                "cmd_r": 0x5C,
                "menu": 0x5D,
                "num_lock": 0x90,
                "scroll_lock": 0x91
            }
            for function_index in range(1, 25):
                native_keyboard_virtual_keys[f"f{function_index}"] = 0x6F + function_index
            try:
                ctypes.windll.user32.SendInput.argtypes = (ctypes.c_uint, ctypes.POINTER(INPUT), ctypes.c_int)
                ctypes.windll.user32.SendInput.restype = ctypes.c_uint
                ctypes.windll.user32.mouse_event.argtypes = (ctypes.c_ulong, ctypes.c_ulong, ctypes.c_ulong, ctypes.c_ulong, ULONG_PTR)
                ctypes.windll.user32.mouse_event.restype = None
            except:
                pass
        else:
            native_mouse_button_flags = {}
            native_keyboard_virtual_keys = {}

        hide_console_window()
        high_resolution_timer_enabled = enable_high_resolution_timer()

        # Globals
        autoclicker_active = False
        cps = 5.0
        mode = "Toggle"
        toggle_key = None
        toggle_keys = []
        setting_keybind = False
        cycle_duty = 0.1
        cps_jitter = 0.0
        click_button_name = "Left"
        click_repeat_name = "Single"
        theme_name = "Azure"
        smart_cycle_enabled = False
        launch_on_startup_enabled = False
        multi_bind_enabled = False
        settings_file = get_settings_file()
        current_account_name = active_account_username
        m = Controller()
        kb_controller = keyboard.Controller()
        fullscreen = False
        advanced_settings_enabled = False
        stop_threads = False
        logout_requested = False
        reset_application_requested = False
        autoclicker_wake_event = threading.Event()
        mouse_action_lock = threading.RLock()
        mouse_jitter_enabled = False
        mouse_jitter_keybind = None
        mouse_jitter_mode = "Toggle"
        mouse_jitter_hold_active = False
        mouse_jitter_speed = 35
        mouse_jitter_x = 4
        mouse_jitter_y = 4
        mouse_jitter_capture = False
        mouse_jitter_stop_event = threading.Event()
        mouse_jitter_thread = None
        binding_warning_pending = False
        active_autoclicker_holds = set()
        themed_soft_buttons = []
        interactive_buttons = []
        themed_entries = []
        themed_toggle_widgets = []
        themed_text_views = []
        themed_listboxes = []
        macros = []
        next_macro_id = 1
        current_macro_id = None
        macro_trigger_capture_id = None
        multi_bind_capture_target = None
        active_macro_triggers = set()
        active_macro_hold_inputs = {}
        macro_runtime = {}
        pressed_modifiers = set()
        sound_feedback_enabled = False
        macro_preview_enabled = False
        anti_afk_enabled = False
        anti_afk_interval = 60
        pause_on_focus_loss_enabled = False
        auto_limiter_enabled = False
        auto_limiter_clicks = 1000
        break_reminder_enabled = False
        break_reminder_interval = 1800
        last_break_reminder_time = time.perf_counter()
        break_reminder_window = None
        break_reminder_countdown = break_reminder_interval
        profiles = []
        active_profile_name = None
        scheduler_job = None
        scheduler_remaining = 0
        scheduler_running = False
        session_stats = {
            "clicks": 0,
            "started_at": time.perf_counter()
        }
        timing_state = {
            "effective_cps": max(0.1, cps),
            "interval_target": 1.0 / max(0.1, cps),
            "scheduler_lag": 0.0,
            "profiles": {}
        }
        default_settings = build_default_account_settings()

        supported_mouse_binding_names = {"left", "right", "middle", "x1", "x2"}
        mouse_binding_aliases = {
            "button4": "x1",
            "button5": "x2",
            "xbutton1": "x1",
            "xbutton2": "x2",
            "mouse4": "x1",
            "mouse5": "x2",
            "back": "x1",
            "forward": "x2"
        }

        def normalize_mouse_binding_name(name):
            if hasattr(name, "name"):
                name = name.name
            button_name = str(name).lower().strip()
            if button_name in supported_mouse_binding_names:
                return button_name
            return mouse_binding_aliases.get(button_name)

        modifier_key_names = {"ctrl", "shift", "alt", "cmd"}

        def normalize_keyboard_combo(key_combo):
            if not key_combo:
                return None
            parts = [normalize_keyboard_action_name(part.strip()) for part in str(key_combo).lower().split("+") if part.strip()]
            if not parts:
                return None
            normalized_modifiers = []
            primary_key = None
            for part in parts:
                if part in {"ctrl", "control", "control_l", "control_r"}:
                    part = "ctrl"
                elif part in {"shift", "shift_l", "shift_r"}:
                    part = "shift"
                elif part in {"alt", "alt_l", "alt_r"}:
                    part = "alt"
                elif part in {"cmd", "command", "win", "meta", "super"}:
                    part = "cmd"
                if part in modifier_key_names:
                    if part not in normalized_modifiers:
                        normalized_modifiers.append(part)
                else:
                    if primary_key is None:
                        primary_key = part
                    else:
                        return None
            if not primary_key:
                return None
            order = ["ctrl", "alt", "shift", "cmd"]
            normalized_modifiers.sort(key=lambda x: order.index(x) if x in order else len(order))
            return "+".join(normalized_modifiers + [primary_key]) if normalized_modifiers else primary_key

        def is_modifier_key(key_name):
            return str(key_name).lower().strip() in modifier_key_names

        def get_active_key_combo(key_name):
            key_name = normalize_keyboard_action_name(key_name)
            if not key_name:
                return None
            if is_modifier_key(key_name):
                return None
            combo_parts = [m for m in ["ctrl", "alt", "shift", "cmd"] if m in pressed_modifiers]
            combo_parts.append(key_name)
            return normalize_keyboard_combo("+".join(combo_parts))

        def serialize_toggle_binding(binding):
            if not binding or not isinstance(binding, tuple) or len(binding) != 2:
                return None
            if binding[0] == "keyboard":
                key_name = normalize_keyboard_combo(str(binding[1]).lower().strip())
                return {"type": "keyboard", "key": key_name} if key_name else None
            if binding[0] == "mouse":
                button_name = normalize_mouse_binding_name(binding[1])
                return {"type": "mouse", "key": button_name} if button_name in supported_mouse_binding_names else None
            return None

        def normalize_toggle_binding(data):
            if not isinstance(data, dict):
                return None
            binding_type = data.get("type")
            binding_key = normalize_keyboard_combo(str(data.get("key", "")).lower().strip())
            if binding_type == "keyboard" and binding_key:
                return ("keyboard", binding_key)
            if binding_type == "mouse":
                binding_key = normalize_mouse_binding_name(str(data.get("key", "")).lower().strip())
                if binding_key and hasattr(Button, binding_key):
                    return ("mouse", getattr(Button, binding_key))
            return None

        def toggle_binding_token(binding):
            serialized = serialize_toggle_binding(binding)
            if not serialized:
                return None
            return serialized["type"], serialized["key"]

        def normalize_macro_binding(binding):
            if not isinstance(binding, dict):
                return None
            binding_type = binding.get("type")
            binding_key = normalize_keyboard_combo(str(binding.get("key", "")).lower().strip())
            if binding_type == "keyboard" and binding_key:
                return {"type": "keyboard", "key": binding_key}
            if binding_type == "mouse":
                binding_key = normalize_mouse_binding_name(str(binding.get("key", "")).lower().strip())
                if binding_key in supported_mouse_binding_names:
                    return {"type": "mouse", "key": binding_key}
            return None

        def normalize_macro_action(action):
            if not isinstance(action, dict):
                return None
            action_type = action.get("type")
            if action_type == "key":
                value = str(action.get("value", "")).lower().strip()
                return {"type": "key", "value": value} if value else None
            if action_type == "mouse":
                value = str(action.get("value", "")).title().strip()
                return {"type": "mouse", "value": value} if value in {"Left", "Right", "Middle"} else None
            if action_type == "delay":
                try:
                    value = max(0, int(float(action.get("value", 0))))
                except:
                    return None
                return {"type": "delay", "value": value}
            return None

        def normalize_macro(data, fallback_id):
            if not isinstance(data, dict):
                return None
            name = str(data.get("name", "")).strip()
            if not name:
                return None
            try:
                macro_id = int(data.get("id", fallback_id))
            except:
                macro_id = fallback_id
            triggers = []
            for trigger in data.get("triggers", []):
                normalized_trigger = normalize_macro_binding(trigger)
                if normalized_trigger and normalized_trigger not in triggers:
                    triggers.append(normalized_trigger)
            primary_trigger = normalize_macro_binding(data.get("trigger"))
            if primary_trigger and primary_trigger not in triggers:
                triggers.insert(0, primary_trigger)
            sequence = []
            for action in data.get("sequence", []):
                normalized = normalize_macro_action(action)
                if normalized:
                    sequence.append(normalized)
            trigger_mode = str(data.get("trigger_mode", "Click")).title()
            if trigger_mode not in {"Click", "Hold"}:
                trigger_mode = "Click"
            return {
                "id": macro_id,
                "name": name,
                "enabled": bool(data.get("enabled", False)),
                "trigger": triggers[0] if triggers else None,
                "triggers": triggers,
                "trigger_mode": trigger_mode,
                "sequence": sequence
            }

        def set_autoclicker_bindings(bindings):
            nonlocal toggle_key
            cleaned = []
            for binding in bindings:
                normalized = normalize_toggle_binding(serialize_toggle_binding(binding))
                token = toggle_binding_token(normalized)
                if normalized and token and token not in [toggle_binding_token(existing) for existing in cleaned]:
                    cleaned.append(normalized)
            if cleaned:
                cleaned = cleaned[:1]
            toggle_keys[:] = cleaned
            toggle_key = toggle_keys[0] if toggle_keys else None

        def set_primary_autoclicker_binding(binding):
            bindings = list(toggle_keys)
            if bindings:
                bindings[0] = binding
            else:
                bindings = [binding]
            set_autoclicker_bindings(bindings)

        def set_autoclicker_binding_at(index, binding):
            bindings = list(toggle_keys)
            if index < len(bindings):
                bindings[index] = binding
            else:
                bindings.append(binding)
            set_autoclicker_bindings(bindings)

        def remove_autoclicker_binding_at(index):
            bindings = list(toggle_keys)
            if 0 <= index < len(bindings):
                removed = bindings.pop(index)
                token = toggle_binding_token(removed)
                if token in active_autoclicker_holds:
                    active_autoclicker_holds.discard(token)
            set_autoclicker_bindings(bindings)

        def get_active_autoclicker_bindings():
            return list(toggle_keys) if multi_bind_enabled else ([toggle_key] if toggle_key else [])

        def get_macro_triggers(macro):
            if not macro:
                return []
            cleaned = []
            for trigger in macro.get("triggers", []):
                normalized = normalize_macro_binding(trigger)
                if normalized and normalized not in cleaned:
                    cleaned.append(normalized)
            primary = normalize_macro_binding(macro.get("trigger"))
            if primary and primary not in cleaned:
                cleaned.insert(0, primary)
            return cleaned

        def macro_uses_hold_mode(macro):
            return bool(macro and str(macro.get("trigger_mode", "Click")).strip().casefold() == "hold")

        def set_macro_triggers(macro, bindings):
            cleaned = []
            for binding in bindings:
                normalized = normalize_macro_binding(binding)
                if normalized and normalized not in cleaned:
                    cleaned.append(normalized)
            if cleaned:
                cleaned = cleaned[:1]
            macro["triggers"] = cleaned
            macro["trigger"] = cleaned[0] if cleaned else None

        def binding_token(binding):
            if isinstance(binding, tuple) and len(binding) == 2:
                return toggle_binding_token(binding)
            if isinstance(binding, dict):
                return macro_binding_token(binding)
            return None

        def binding_conflicts(candidate, owner):
            candidate_token = binding_token(candidate)
            if not candidate_token or multi_bind_enabled:
                return False

            if binding_token(toggle_key) == candidate_token and owner != "autoclicker":
                return True
            if binding_token(mouse_jitter_keybind) == candidate_token and owner != "mouse_jitter":
                return True
            for macro in macros:
                if owner == f"macro:{macro['id']}":
                    continue
                if binding_token(macro.get("trigger")) == candidate_token:
                    return True
            return False

        def warn_binding_conflict():
            nonlocal binding_warning_pending
            if binding_warning_pending:
                return
            binding_warning_pending = True

            def show_warning():
                nonlocal binding_warning_pending
                try:
                    if root.winfo_exists():
                        messagebox.showwarning(
                            "Binding already in use",
                            "You cannot bind the same key or mouse button to multiple modules. Enable Multi Binding in the Mods tab to allow shared bindings.",
                            parent=root
                        )
                finally:
                    binding_warning_pending = False

            root.after(0, show_warning)

        def can_assign_binding(candidate, owner):
            if binding_conflicts(candidate, owner):
                warn_binding_conflict()
                return False
            return True

        def remove_legacy_binding_duplicates():
            nonlocal mouse_jitter_keybind
            if multi_bind_enabled:
                return
            seen = set()
            if toggle_key:
                seen.add(binding_token(toggle_key))
            if mouse_jitter_keybind:
                jitter_token = binding_token(mouse_jitter_keybind)
                if jitter_token in seen:
                    mouse_jitter_keybind = None
                elif jitter_token:
                    seen.add(jitter_token)
            for macro in macros:
                trigger = macro.get("trigger")
                trigger_token = binding_token(trigger)
                if trigger_token in seen:
                    macro["trigger"] = None
                    macro["triggers"] = []
                elif trigger_token:
                    seen.add(trigger_token)

        def set_macro_trigger_at(macro, index, binding):
            bindings = get_macro_triggers(macro)
            if index < len(bindings):
                bindings[index] = binding
            else:
                bindings.append(binding)
            set_macro_triggers(macro, bindings)

        def remove_macro_trigger_at(macro, index):
            bindings = get_macro_triggers(macro)
            if 0 <= index < len(bindings):
                removed = bindings.pop(index)
                hold_inputs = active_macro_hold_inputs.setdefault(macro["id"], set())
                token = macro_binding_token(removed)
                if token in hold_inputs:
                    hold_inputs.discard(token)
            set_macro_triggers(macro, bindings)

        def trim_multi_bind_collections():
            changed = False
            if len(toggle_keys) > 1:
                changed = True
            set_autoclicker_bindings(toggle_keys[:1])
            for macro in macros:
                bindings = get_macro_triggers(macro)
                if len(bindings) > 1:
                    changed = True
                set_macro_triggers(macro, bindings[:1])
            return changed

        def macro_binding_token(binding):
            normalized = normalize_macro_binding(binding)
            if not normalized:
                return None
            return normalized["type"], normalized["key"]

        def get_macro_by_id(macro_id):
            for macro in macros:
                if macro["id"] == macro_id:
                    return macro
            return None

        def format_macro_binding_text(binding):
            if not binding:
                return "No macro keybind set"
            if binding["type"] == "keyboard":
                return f"Keybind: {binding['key'].upper()}"
            return f"Keybind: {binding['key'].upper()} CLICK"

        def format_autoclicker_keybind_text():
            if not toggle_key:
                return "No keybind set"
            text = format_keybind_text(toggle_key)
            if multi_bind_enabled and len(toggle_keys) > 1:
                text += f" (+{len(toggle_keys) - 1} more)"
            return text

        def format_macro_binding_summary(macro):
            bindings = get_macro_triggers(macro)
            if not bindings:
                return "No macro keybind set"
            text = format_macro_binding_text(bindings[0])
            if multi_bind_enabled and len(bindings) > 1:
                text += f" (+{len(bindings) - 1} more)"
            return text

        def format_toggle_binding_compact_text(binding):
            if not binding:
                return "No keybind set"
            return format_keybind_text(binding).replace("Keybind: ", "")

        def format_macro_binding_compact_text(binding):
            if not binding:
                return "No macro keybind set"
            return format_macro_binding_text(binding).replace("Keybind: ", "")

        def macro_status_symbol(macro):
            return "✓" if macro.get("enabled") else "○"

        def format_macro_action_text(action):
            if action["type"] == "key":
                return f"Key • {str(action['value']).upper()}"
            if action["type"] == "mouse":
                return f"Mouse • {action['value']} Click"
            return f"Delay • {action['value']} ms"

        def get_listener_key_name(key):
            key_name = getattr(key, "char", None)
            if isinstance(key_name, str):
                key_name = key_name.strip()
            if not key_name:
                key_name = getattr(key, "name", None)
            if not key_name:
                vk = getattr(key, "vk", None)
                if vk is not None:
                    try:
                        key_code = keyboard.KeyCode.from_vk(vk)
                        key_name = getattr(key_code, "char", None) or getattr(key_code, "vk", None)
                    except:
                        key_name = vk
            if key_name is None:
                return None
            key_name = normalize_keyboard_action_name(str(key_name).lower().strip())
            return key_name or None

        keyboard_key_aliases = {
            "return": "enter",
            "escape": "esc",
            "control": "ctrl",
            "control_l": "ctrl",
            "control_r": "ctrl",
            "shift": "shift",
            "shift_l": "shift",
            "shift_r": "shift",
            "alt": "alt",
            "alt_l": "alt",
            "alt_r": "alt",
            "command": "cmd",
            "cmd": "cmd",
            "win": "cmd",
            "meta": "cmd",
            "prior": "page_up",
            "next": "page_down",
            "del": "delete"
        }

        def normalize_keyboard_action_name(key_name):
            key_name = str(key_name or "").lower().strip()
            return keyboard_key_aliases.get(key_name, key_name)

        def resolve_keyboard_key(key_name):
            key_name = normalize_keyboard_action_name(key_name)
            if not key_name:
                return None
            if len(key_name) == 1:
                try:
                    return keyboard.KeyCode.from_char(key_name)
                except:
                    return key_name
            if hasattr(keyboard.Key, key_name):
                return getattr(keyboard.Key, key_name)
            return None

        def get_mouse_button_by_name(name):
            return {
                "left": Button.left,
                "right": Button.right,
                "middle": Button.middle,
                "x1": getattr(Button, "x1", Button.left),
                "x2": getattr(Button, "x2", Button.left)
            }.get(str(name).lower(), Button.left)

        def get_startup_command():
            if getattr(sys, "frozen", False):
                return f'"{sys.executable}"'
            executable = sys.executable
            if os.name == "nt" and os.path.basename(executable).lower() == "python.exe":
                candidate = os.path.join(os.path.dirname(executable), "pythonw.exe")
                if os.path.exists(candidate):
                    executable = candidate
            return f'"{executable}" "{os.path.abspath(__file__)}"'

        def read_launch_on_startup_state():
            if os.name != "nt":
                return False
            try:
                import winreg
                with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run", 0, winreg.KEY_READ) as key:
                    value, _ = winreg.QueryValueEx(key, "Zhydra")
                return str(value).strip() == get_startup_command()
            except FileNotFoundError:
                return False
            except:
                return False

        def set_launch_on_startup(enabled):
            if os.name != "nt":
                return False
            try:
                import winreg
                with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run", 0, winreg.KEY_SET_VALUE) as key:
                    if enabled:
                        winreg.SetValueEx(key, "Zhydra", 0, winreg.REG_SZ, get_startup_command())
                    else:
                        try:
                            winreg.DeleteValue(key, "Zhydra")
                        except FileNotFoundError:
                            pass
                return True
            except:
                return False

        def get_minimum_click_hold_time(button):
            if button == Button.left:
                return 0.0074
            if button == Button.middle:
                return 0.0058
            return 0.0056

        def get_minimum_release_settle_time(button):
            return 0.0017 if button == Button.left else 0.0014

        def get_minimum_registered_click_interval(button, repeat_count=1):
            repeat_count = max(1, int(repeat_count))
            return (get_minimum_click_hold_time(button) + get_minimum_release_settle_time(button) + 0.0005) * repeat_count

        def smooth_timing_value(current, sample, weight=0.18):
            sample = max(0.0, float(sample))
            if current is None or current <= 0:
                return sample
            return current + ((sample - current) * weight)

        def update_scheduler_lag(sample):
            timing_state["scheduler_lag"] = smooth_timing_value(
                timing_state["scheduler_lag"],
                max(0.0, float(sample)),
                0.16
            )
            return timing_state["scheduler_lag"]

        def get_timing_profile(button, repeat_count=1):
            key = (button, max(1, int(repeat_count)))
            if key not in timing_state["profiles"]:
                timing_state["profiles"][key] = {
                    "hold_target": None,
                    "hold_observed": get_minimum_click_hold_time(button),
                    "settle_observed": get_minimum_release_settle_time(button),
                    "cycle_elapsed": 0.0
                }
            return timing_state["profiles"][key]

        def update_click_timing_profile(button, repeat_count, sample):
            profile = get_timing_profile(button, repeat_count)
            hold_elapsed = sample.get("hold_elapsed")
            if hold_elapsed is not None:
                profile["hold_observed"] = smooth_timing_value(profile["hold_observed"], hold_elapsed, 0.20)
            settle_elapsed = sample.get("settle_elapsed")
            if settle_elapsed is not None:
                profile["settle_observed"] = smooth_timing_value(profile["settle_observed"], settle_elapsed, 0.18)
            cycle_elapsed = sample.get("cycle_elapsed")
            if cycle_elapsed is not None:
                profile["cycle_elapsed"] = smooth_timing_value(profile["cycle_elapsed"], cycle_elapsed, 0.16)

        def get_measured_registration_floor(button, repeat_count=1):
            repeat_count = max(1, int(repeat_count))
            profile = get_timing_profile(button, repeat_count)
            safety_margin = max(0.0008, (timing_state["scheduler_lag"] * 1.60) + (0.0003 if repeat_count > 1 else 0.0))
            measured_floor = (
                max(get_minimum_click_hold_time(button), profile["hold_observed"]) +
                max(get_minimum_release_settle_time(button), profile["settle_observed"]) +
                safety_margin
            ) * repeat_count
            if profile["cycle_elapsed"] > 0:
                measured_floor = max(measured_floor, profile["cycle_elapsed"] + safety_margin)
            return max(get_minimum_registered_click_interval(button, repeat_count), measured_floor)

        def get_effective_cycle_interval(button, repeat_count, effective_cps):
            effective_cps = max(0.1, float(effective_cps))
            # CPS is the source of truth. The only lower bound is the measured
            # physical time required to register the selected click profile.
            interval = max(1.0 / effective_cps, get_minimum_registered_click_interval(button, repeat_count))
            timing_state["interval_target"] = interval
            return interval

        def get_effective_jittered_cps():
            target_cps = max(0.1, float(cps))
            if cps_jitter > 0:
                target_cps = max(0.1, cps * (1.0 + random.uniform(-cps_jitter, cps_jitter) / 100.0))
            # Do not smooth this value: smoothing makes the actual rate lag
            # behind the configured CPS, especially after a setting change.
            timing_state["effective_cps"] = target_cps
            return target_cps

        def get_effective_release_settle_time(button, repeat_count=1, interval=None):
            repeat_count = max(1, int(repeat_count))
            base_settle = get_minimum_release_settle_time(button)
            profile = get_timing_profile(button, repeat_count)
            settle_time = max(
                base_settle,
                profile["settle_observed"],
                base_settle + (timing_state["scheduler_lag"] * 0.85)
            )
            if interval is not None and repeat_count > 1:
                slot_duration = max(0.001, float(interval)) / repeat_count
                settle_time = min(max(base_settle, slot_duration * 0.35), settle_time)
            return settle_time

        def get_inter_click_recovery_time(button, repeat_count, interval):
            repeat_count = max(1, int(repeat_count))
            if repeat_count <= 1:
                return 0.0
            slot_duration = max(0.001, float(interval)) / repeat_count
            profile = get_timing_profile(button, repeat_count)
            recovery_time = max(
                0.0005,
                max(get_minimum_release_settle_time(button), profile["settle_observed"]) * 0.60,
                timing_state["scheduler_lag"] * 0.90
            )
            return min(max(0.0005, slot_duration * 0.32), recovery_time)

        def get_effective_cycle_hold_time(button, repeat_count, interval):
            repeat_count = max(1, int(repeat_count))
            interval = max(0.001, float(interval))
            min_hold = get_minimum_click_hold_time(button)
            release_settle = get_minimum_release_settle_time(button)
            profile = get_timing_profile(button, repeat_count)
            observed_hold = max(min_hold, profile["hold_observed"])
            observed_settle = max(release_settle, profile["settle_observed"])
            duty_ratio = min(1.0, max(0.001, cycle_duty / 100.0))
            slot_duration = interval / repeat_count
            hold_guard = max(0.0009, (timing_state["scheduler_lag"] * 1.25) + (0.0003 if repeat_count > 1 else 0.0))
            hold_limit = max(min_hold, slot_duration - observed_settle - hold_guard)
            baseline = max(min_hold, observed_hold, (interval * duty_ratio) / repeat_count)
            if not smart_cycle_enabled:
                desired_hold = baseline
            else:
                pace_factor = 0.80 if slot_duration <= 0.020 else (0.84 if slot_duration <= 0.050 else 0.90)
                button_factor = 1.00 if button == Button.left else (0.97 if button == Button.middle else 0.95)
                adaptive_target = max(observed_hold, hold_limit * pace_factor * button_factor)
                desired_hold = max(baseline, adaptive_target)

            desired_hold = min(hold_limit, max(min_hold, desired_hold))
            previous_target = profile["hold_target"]
            if previous_target is None:
                profile["hold_target"] = desired_hold
            else:
                max_step = max(0.0003, slot_duration * 0.10)
                delta = max(-max_step, min(max_step, desired_hold - previous_target))
                profile["hold_target"] = min(hold_limit, max(min_hold, previous_target + delta))
            return profile["hold_target"]

        def get_smart_cycle_status_text():
            button = get_click_button()
            repeat_count = get_click_repeat_count()
            effective_cps = max(0.1, cps)
            interval = max(1.0 / effective_cps, get_measured_registration_floor(button, repeat_count))
            hold_time = get_effective_cycle_hold_time(button, repeat_count, interval)
            return f"Adaptive hold {hold_time * 1000:.2f} ms • Safe interval {interval * 1000:.2f} ms"

        def release_mouse_button_safely(button):
            if send_mouse_button_event(button, False):
                return True
            time.sleep(0.001)
            return send_mouse_button_event(button, False)

        def ensure_macro_runtime(macro_id):
            if macro_id not in macro_runtime:
                macro_runtime[macro_id] = {
                    "thread": None,
                    "stop_event": threading.Event(),
                    "running": False,
                    "hold_active": False
                }
            return macro_runtime[macro_id]

        def sleep_with_stop(duration, stop_event, step=0.01):
            end_time = time.perf_counter() + max(0.0, duration)
            while time.perf_counter() < end_time:
                if stop_event.is_set() or stop_threads:
                    return False
                time.sleep(min(step, max(0.0, end_time - time.perf_counter())))
            return True

        def wait_macro_duration(duration, stop_event):
            duration = max(0.0, float(duration))
            return precise_wait_until(
                time.perf_counter() + duration,
                cancel_check=lambda: stop_event.is_set() or stop_threads,
                spin_threshold=0.0005
            )

        def finalize_macro_trigger(macro_id):
            active_macro_triggers.discard(macro_id)

        def send_keyboard_event(key_name, pressed):
            key_name = normalize_keyboard_action_name(key_name)
            if not key_name:
                return False

            if os.name == "nt":
                try:
                    keyboard_input = None
                    if len(key_name) == 1:
                        keyboard_input = KEYBDINPUT(
                            0,
                            ord(key_name),
                            KEYEVENTF_UNICODE | (0 if pressed else KEYEVENTF_KEYUP),
                            0,
                            0
                        )
                    else:
                        vk_code = native_keyboard_virtual_keys.get(key_name)
                        if vk_code is not None:
                            keyboard_input = KEYBDINPUT(
                                vk_code,
                                0,
                                0 if pressed else KEYEVENTF_KEYUP,
                                0,
                                0
                            )

                    if keyboard_input is not None:
                        input_event = INPUT()
                        input_event.type = INPUT_KEYBOARD
                        input_event.union.ki = keyboard_input
                        if ctypes.windll.user32.SendInput(1, ctypes.byref(input_event), ctypes.sizeof(input_event)) == 1:
                            return True
                except:
                    pass

            key_obj = resolve_keyboard_key(key_name)
            if key_obj is None:
                return False

            try:
                if pressed:
                    kb_controller.press(key_obj)
                else:
                    kb_controller.release(key_obj)
                return True
            except:
                return False

        def tap_keyboard_key(key_name, stop_event):
            try:
                if not send_keyboard_event(key_name, True):
                    return False
                if not wait_macro_duration(0.001, stop_event):
                    return False
                if not send_keyboard_event(key_name, False):
                    return False
                return True
            except:
                try:
                    send_keyboard_event(key_name, False)
                except:
                    pass
                return False

        def execute_macro_sequence(macro, stop_event):
            for action in macro.get("sequence", []):
                if stop_event.is_set() or stop_threads:
                    return False
                if action["type"] == "delay":
                    if not wait_macro_duration(action["value"] / 1000.0, stop_event):
                        return False
                    continue
                if action["type"] == "mouse":
                    if not emit_registered_mouse_click(
                        get_mouse_button_by_name(action["value"]),
                        0.001,
                        release_settle=0.001,
                        cancel_check=lambda: stop_event.is_set() or stop_threads,
                        enforce_minimum=False
                    ):
                        return False
                    continue
                key_name = normalize_keyboard_action_name(action["value"])
                if not key_name:
                    continue
                if not tap_keyboard_key(key_name, stop_event):
                    return False
            return True

        def run_macro_worker(macro_id, repeat_while_held=False):
            set_current_thread_high_priority()
            runtime = ensure_macro_runtime(macro_id)
            runtime["running"] = True
            try:
                while not runtime["stop_event"].is_set() and not stop_threads:
                    macro = get_macro_by_id(macro_id)
                    if not macro or not macro.get("enabled"):
                        break
                    if not macro.get("sequence"):
                        if not sleep_with_stop(0.05, runtime["stop_event"]):
                            break
                    elif not execute_macro_sequence(macro, runtime["stop_event"]):
                        break
                    if not repeat_while_held:
                        break
                    if not runtime["hold_active"]:
                        break
                    if not sleep_with_stop(0.01, runtime["stop_event"], step=0.005):
                        break
            except:
                pass
            finally:
                runtime["running"] = False
                runtime["thread"] = None
                runtime["stop_event"].clear()
                if not repeat_while_held:
                    runtime["hold_active"] = False
                finalize_macro_trigger(macro_id)

        def start_macro_execution(macro_id, repeat_while_held=False):
            runtime = ensure_macro_runtime(macro_id)
            if repeat_while_held:
                runtime["hold_active"] = True
            if runtime["running"] and runtime["thread"] and not runtime["thread"].is_alive():
                runtime["running"] = False
                runtime["thread"] = None
            if runtime["running"] and runtime["thread"] and runtime["thread"].is_alive():
                return
            runtime["stop_event"].clear()
            runtime["thread"] = threading.Thread(
                target=run_macro_worker,
                args=(macro_id, repeat_while_held),
                daemon=True
            )
            runtime["thread"].start()

        def stop_macro_execution(macro_id):
            runtime = ensure_macro_runtime(macro_id)
            runtime["hold_active"] = False
            runtime["stop_event"].set()
            active_macro_hold_inputs.pop(macro_id, None)

        def toggle_macro_enabled_state(macro_id):
            macro = get_macro_by_id(macro_id)
            if not macro:
                return None
            macro["enabled"] = not macro.get("enabled", False)
            if not macro["enabled"]:
                stop_macro_execution(macro_id)
                active_macro_triggers.discard(macro_id)
                active_macro_hold_inputs.pop(macro_id, None)
            save_settings()
            return macro["enabled"]

        def arm_macro_for_use(macro):
            if not macro:
                return False
            if macro.get("enabled"):
                return False
            if not get_macro_triggers(macro) or not macro.get("sequence"):
                return False
            macro["enabled"] = True
            return True

        themes = {
            "Azure": {
                "window_bg": "#070C18",
                "bg_stops": [
                    (0.00, "#060A17"),
                    (0.18, "#091122"),
                    (0.46, "#0C1832"),
                    (0.74, "#08111E"),
                    (1.00, "#070C18")
                ],
                "bg_sheen": "#4A6FCC",
                "glow_palette": ["#3B30CC", "#0A8AEE", "#7B2FCC", "#1A4ABB"],
                "card_bg": "#0B1220",
                "card_border": "#1A2540",
                "tab_wrap_bg": "#070D1A",
                "tab_active_bg": "#0E1A32",
                "tab_inactive_bg": "#080E1E",
                "tab_active_fg": "#F0F6FF",
                "tab_inactive_fg": "#6A88B0",
                "tab_active_border": "#5B6CF9",
                "tab_inactive_border": "#111E35",
                "tab_hover_bg": "#0C1628",
                "tab_hover_fg": "#D8E8FF",
                "tab_hover_border": "#1E3660",
                "divider_bg": "#0F1E32",
                "title_fg": "#EEF4FF",
                "subtitle_fg": "#6A88B0",
                "section_shell_bg": "#080E1C",
                "section_border": "#131C32",
                "section_accent": "#5B6CF9",
                "section_title_bar_bg": "#0A1022",
                "section_title_fg": "#D8E8FF",
                "section_frame_bg": "#090E1E",
                "label_fg": "#C8D8F0",
                "secondary_fg": "#5A7898",
                "entry_bg": "#0A1226",
                "entry_fg": "#E8F0FF",
                "entry_insert": "#E8F0FF",
                "entry_border": "#162040",
                "entry_focus": "#5B6CF9",
                "combobox_bg": "#0A1226",
                "combobox_fg": "#D8E8FF",
                "combobox_arrow": "#8AAAD0",
                "scrollbar_trough": "#060A14",
                "scrollbar_thumb": "#111C30",
                "scrollbar_thumb_active": "#1A2B48",
                "scrollbar_arrow": "#C0D0E8",
                "scrollbar_border": "#182844",
                "log_bg": "#070C18",
                "log_fg": "#C8D8F0",
                "log_select_bg": "#0E1C38",
                "log_border": "#131C32",
                "popup_bg": "#090F1E",
                "popup_border": "#162440",
                "popup_title_fg": "#EEF4FF",
                "popup_text_fg": "#8AAAD0",
                "gear_bg": "#0A1226",
                "gear_fg": "#D8E8FF",
                "gear_active_bg": "#0E1A34",
                "gear_border": "#5B6CF9",
                "close_bg": "#0A1226",
                "close_fg": "#C8D8F0",
                "close_active_bg": "#0E1A34",
                "close_border": "#162440",
                "button_glow": "#0A1230",
                "button_shadow": "#020408",
                "button_body": "#5B6CF9",
                "button_body_hover": "#6B7CFF",
                "button_body_pressed": "#4A5FEA",
                "button_outline": "#5B6CF9",
                "button_outline_hover": "#A5B4FC",
                "button_label": "#FFFFFF",
                "prompt": "#6878E0",
                "success": "#10B981",
                "error": "#EF4444",
                "keyword": "#5898F0",
                "value": "#E8C040",
                "arrow": "#7090CC",
                "sidebar_bg": "#070D1A",
                "sidebar_border": "#131C32",
                "sidebar_inner": "#080E1E",
                "sidebar_active_bg": "#0E1A32",
                "sidebar_hover_bg": "#0B1426",
                "hero_bg": "#080F1E",
                "hero_border": "#131C36",
                "hero_chip": "#0A1428",
                "hero_chip_border": "#1C3060",
                "surface_alt": "#09101E",
                "panel_shadow": "#020408",
                "toast_bg": "#0A1428",
                "toast_border": "#182E50",
                "toast_fg": "#D8E8FF"
            },
            "Light": {
                "window_bg": "#F0F2F8",
                "bg_stops": [
                    (0.00, "#F8F9FD"),
                    (0.24, "#F4F5FA"),
                    (0.56, "#EDF0F7"),
                    (0.84, "#F2F4FA"),
                    (1.00, "#EDF0F7")
                ],
                "bg_sheen": "#B8C4DC",
                "glow_palette": ["#E0E6F4", "#D4DCF0", "#E6E8F8", "#CCD4EA"],
                "card_bg": "#FAFBFF",
                "card_border": "#CDD5E4",
                "tab_wrap_bg": "#EDF0F8",
                "tab_active_bg": "#FAFBFF",
                "tab_inactive_bg": "#E6EAF4",
                "tab_active_fg": "#0D1526",
                "tab_inactive_fg": "#3A4A60",
                "tab_active_border": "#0D1526",
                "tab_inactive_border": "#CCD4E4",
                "tab_hover_bg": "#F4F6FC",
                "tab_hover_fg": "#0A1020",
                "tab_hover_border": "#7A88A0",
                "divider_bg": "#D0D8EC",
                "title_fg": "#0D1526",
                "subtitle_fg": "#3A4A60",
                "section_shell_bg": "#F6F8FD",
                "section_border": "#CDD5E8",
                "section_accent": "#2030A0",
                "section_title_bar_bg": "#EEF2FA",
                "section_title_fg": "#0D1526",
                "section_frame_bg": "#FAFBFF",
                "label_fg": "#0D1526",
                "secondary_fg": "#3A4A60",
                "entry_bg": "#FAFBFF",
                "entry_fg": "#0D1526",
                "entry_insert": "#0D1526",
                "entry_border": "#BEC8DC",
                "entry_focus": "#2030A0",
                "combobox_bg": "#FAFBFF",
                "combobox_fg": "#0D1526",
                "combobox_arrow": "#2030A0",
                "scrollbar_trough": "#EDF0F8",
                "scrollbar_thumb": "#C8D2E4",
                "scrollbar_thumb_active": "#B8C4D8",
                "scrollbar_arrow": "#3A4A60",
                "scrollbar_border": "#BEC8DC",
                "log_bg": "#FAFBFF",
                "log_fg": "#0D1526",
                "log_select_bg": "#D4DCF0",
                "log_border": "#BDC8DC",
                "popup_bg": "#FAFBFF",
                "popup_border": "#CCD4E4",
                "popup_title_fg": "#0D1526",
                "popup_text_fg": "#1E2E44",
                "gear_bg": "#FAFBFF",
                "gear_fg": "#0D1526",
                "gear_active_bg": "#EEF2FA",
                "gear_border": "#BEC8DC",
                "close_bg": "#FAFBFF",
                "close_fg": "#0D1526",
                "close_active_bg": "#EEF2FA",
                "close_border": "#BEC8DC",
                "button_glow": "#DDE4F2",
                "button_shadow": "#CCD4E8",
                "button_body": "#FAFBFF",
                "button_body_hover": "#F0F4FC",
                "button_body_pressed": "#E4EAF6",
                "button_outline": "#B4C0D4",
                "button_outline_hover": "#0D1526",
                "button_label": "#0D1526",
                "prompt": "#2A3A58",
                "success": "#0A6A40",
                "error": "#A01C14",
                "keyword": "#0D1526",
                "value": "#3A4A60",
                "arrow": "#4A5870"
            },
            "Dark": {
                "window_bg": "#08090E",
                "bg_stops": [
                    (0.00, "#07080D"),
                    (0.24, "#0B0D14"),
                    (0.56, "#10121A"),
                    (0.84, "#090B12"),
                    (1.00, "#08090E")
                ],
                "bg_sheen": "#282E3C",
                "glow_palette": ["#10141C", "#161C28", "#0E1018", "#1E2430"],
                "card_bg": "#0E1016",
                "card_border": "#1E2230",
                "tab_wrap_bg": "#0B0D14",
                "tab_active_bg": "#141820",
                "tab_inactive_bg": "#181B24",
                "tab_active_fg": "#E8ECF4",
                "tab_inactive_fg": "#9AA0B0",
                "tab_active_border": "#3A4050",
                "tab_inactive_border": "#1E2230",
                "tab_hover_bg": "#1C2030",
                "tab_hover_fg": "#EEF2F8",
                "tab_hover_border": "#3A4458",
                "divider_bg": "#1A1E28",
                "title_fg": "#E8ECF4",
                "subtitle_fg": "#7A8498",
                "section_shell_bg": "#0C0E14",
                "section_border": "#18202E",
                "section_accent": "#3A4258",
                "section_title_bar_bg": "#10141E",
                "section_title_fg": "#D8DCE8",
                "section_frame_bg": "#121620",
                "label_fg": "#D0D4E0",
                "secondary_fg": "#8A90A0",
                "entry_bg": "#181C28",
                "entry_fg": "#E8ECF4",
                "entry_insert": "#E8ECF4",
                "entry_border": "#262C3C",
                "entry_focus": "#4A5068",
                "combobox_bg": "#181C28",
                "combobox_fg": "#E8ECF4",
                "combobox_arrow": "#E8ECF4",
                "scrollbar_trough": "#0C0E14",
                "scrollbar_thumb": "#1E2430",
                "scrollbar_thumb_active": "#282E3E",
                "scrollbar_arrow": "#D0D4E0",
                "scrollbar_border": "#2C3040",
                "log_bg": "#0B0D14",
                "log_fg": "#D0D4E0",
                "log_select_bg": "#1E2430",
                "log_border": "#242A38",
                "popup_bg": "#101420",
                "popup_border": "#202434",
                "popup_title_fg": "#E8ECF4",
                "popup_text_fg": "#A0A8B8",
                "gear_bg": "#141820",
                "gear_fg": "#D0D4E0",
                "gear_active_bg": "#1C2030",
                "gear_border": "#303848",
                "close_bg": "#141820",
                "close_fg": "#D0D4E0",
                "close_active_bg": "#1C2030",
                "close_border": "#303848",
                "button_glow": "#10141E",
                "button_shadow": "#08090E",
                "button_body": "#1E2434",
                "button_body_hover": "#282E40",
                "button_body_pressed": "#161A28",
                "button_outline": "#363C4E",
                "button_outline_hover": "#5A6070",
                "button_label": "#E8ECF4",
                "prompt": "#8890A0",
                "success": "#50D890",
                "error": "#E07070",
                "keyword": "#B0B8C8",
                "value": "#C0C4D0",
                "arrow": "#707880"
            }
        }

        def get_theme():
            return themes.get(theme_name, themes["Azure"])

        def format_keybind_text(keybind):
            if not keybind:
                return "No keybind set"
            if keybind[0] == "keyboard":
                return f"Keybind: {str(keybind[1]).upper()}"
            return f"Keybind: {keybind[1].name.upper()}"

        def get_click_button():
            return {
                "Left": Button.left,
                "Right": Button.right,
                "Middle": Button.middle
            }.get(click_button_name, Button.left)

        def play_feedback_sound(success=True):
            if not sound_feedback_enabled:
                return
            if os.name == "nt":
                try:
                    import winsound
                    winsound.MessageBeep(winsound.MB_OK if success else winsound.MB_ICONHAND)
                except:
                    pass

        def show_system_notification(title, message, duration=5):
            if os.name == "nt":
                try:
                    from win10toast import ToastNotifier
                    toaster = ToastNotifier()
                    toaster.show_toast(title, message, duration=duration, threaded=True)
                except:
                    pass

        def show_break_reminder_timer():
            nonlocal break_reminder_window, break_reminder_countdown
            
            # Close existing window if open
            if break_reminder_window:
                try:
                    if tk.Toplevel.winfo_exists(break_reminder_window):
                        break_reminder_window.destroy()
                except:
                    pass
            
            # Create new timer window
            window = tk.Toplevel(root)
            break_reminder_window = window
            window.title("Break Reminder Timer")
            window.attributes("-topmost", True)
            window.resizable(False, False)
            
            theme = get_theme()
            
            # Set window background
            window.configure(bg=theme["surface_alt"])
            
            # Create main content frame
            content = tk.Frame(window, bg=theme["surface_alt"], padx=40, pady=30)
            content.pack(fill="both", expand=True)
            
            # Title
            title_label = tk.Label(
                content,
                text="⏱ Time for a Break!",
                font=("Segoe UI", 18, "bold"),
                bg=theme["surface_alt"],
                fg=theme["section_title_fg"]
            )
            title_label.pack(pady=(0, 10))
            
            # Subtitle
            subtitle_label = tk.Label(
                content,
                text="You've been working hard. Rest your hands and eyes.",
                font=("Segoe UI", 10),
                bg=theme["surface_alt"],
                fg=theme["secondary_fg"]
            )
            subtitle_label.pack(pady=(0, 25))
            
            # Timer display frame with accent border
            timer_border = tk.Frame(
                content,
                bg=theme["section_accent"],
                height=4
            )
            timer_border.pack(fill="x", pady=(0, 2))
            
            timer_frame = tk.Frame(
                content,
                bg=blend(theme["entry_bg"], theme["surface_alt"], 0.3),
                bd=1,
                relief="solid",
                highlightthickness=0
            )
            timer_frame.pack(fill="x", pady=(0, 25))
            
            # Countdown timer display
            timer_label = tk.Label(
                timer_frame,
                text=f"{int(break_reminder_countdown // 60):02d}:{int(break_reminder_countdown % 60):02d}",
                font=("Segoe UI", 56, "bold"),
                bg=blend(theme["entry_bg"], theme["surface_alt"], 0.3),
                fg=theme["section_accent"],
                padx=40,
                pady=20
            )
            timer_label.pack()
            
            # Message
            message_label = tk.Label(
                content,
                text="Next reminder in",
                font=("Segoe UI", 9),
                bg=theme["surface_alt"],
                fg=theme["secondary_fg"]
            )
            message_label.pack(pady=(0, 15))
            
            # Button frame
            button_frame = tk.Frame(content, bg=theme["surface_alt"])
            button_frame.pack(fill="x", pady=(10, 0))
            
            # Dismiss button
            dismiss_btn = tk.Button(
                button_frame,
                text="Dismiss",
                command=lambda: close_timer_window(),
                font=("Segoe UI", 10),
                bd=0,
                padx=16,
                pady=8,
                cursor="hand2"
            )
            style_modern_button(dismiss_btn, "secondary")
            dismiss_btn.pack(side="right", padx=(5, 0))
            
            # Snooze button
            snooze_btn = tk.Button(
                button_frame,
                text="Snooze 5 min",
                command=lambda: snooze_break_reminder(),
                font=("Segoe UI", 10),
                bd=0,
                padx=16,
                pady=8,
                cursor="hand2"
            )
            style_modern_button(snooze_btn, "primary")
            snooze_btn.pack(side="right")
            
            def close_timer_window():
                nonlocal break_reminder_window
                try:
                    if window and tk.Toplevel.winfo_exists(window):
                        window.destroy()
                except:
                    pass
                break_reminder_window = None
            
            # Update timer every second
            def update_timer():
                nonlocal break_reminder_countdown
                try:
                    if window and tk.Toplevel.winfo_exists(window):
                        break_reminder_countdown -= 1
                        if break_reminder_countdown <= 0:
                            close_timer_window()
                        else:
                            timer_label.config(text=f"{int(break_reminder_countdown // 60):02d}:{int(break_reminder_countdown % 60):02d}")
                            window.after(1000, update_timer)
                except:
                    break_reminder_window = None
            
            # Center window on screen
            window.update_idletasks()
            width = window.winfo_width()
            height = window.winfo_height()
            x = (window.winfo_screenwidth() // 2) - (width // 2)
            y = (window.winfo_screenheight() // 2) - (height // 2)
            window.geometry(f"+{x}+{y}")
            
            # Start timer update
            update_timer()
        
        def snooze_break_reminder():
            nonlocal last_break_reminder_time, break_reminder_countdown, break_reminder_window
            last_break_reminder_time = time.perf_counter()
            break_reminder_countdown = break_reminder_interval
            if break_reminder_window:
                try:
                    if tk.Toplevel.winfo_exists(break_reminder_window):
                        break_reminder_window.destroy()
                except:
                    pass
                break_reminder_window = None

        def get_click_repeat_count():
            return {
                "Single": 1,
                "Double": 2,
                "Triple": 3
            }.get(click_repeat_name, 1)

        def set_autoclicker_state(active, source="Keybind"):
            nonlocal autoclicker_active
            active = bool(active)
            if not active:
                active_autoclicker_holds.clear()
            if autoclicker_active == active:
                autoclicker_wake_event.set()
                return
            autoclicker_active = active
            autoclicker_wake_event.set()
            log(f"{source} {'enabled' if active else 'disabled'} autoclicker")

        def toggle_autoclicker(source="Keybind"):
            set_autoclicker_state(not autoclicker_active, source)

        def set_mouse_jitter_state(active, source="Keybind"):
            nonlocal mouse_jitter_enabled, mouse_jitter_thread
            mouse_jitter_enabled = bool(active)
            if mouse_jitter_enabled:
                mouse_jitter_stop_event.clear()
                if mouse_jitter_thread is None or not mouse_jitter_thread.is_alive():
                    mouse_jitter_thread = threading.Thread(target=mouse_jitter_loop, daemon=True)
                    mouse_jitter_thread.start()
            else:
                mouse_jitter_stop_event.set()
            render_mouse_page()

        def stop_mouse_jitter():
            nonlocal mouse_jitter_hold_active
            mouse_jitter_hold_active = False
            set_mouse_jitter_state(False, "Mouse Jitter")

        def toggle_mouse_jitter():
            set_mouse_jitter_state(not mouse_jitter_enabled, "Mouse Jitter")
            save_settings()
            log(f"Mouse Jitter {'enabled' if mouse_jitter_enabled else 'disabled'}")

        def mouse_jitter_trigger_pressed():
            nonlocal mouse_jitter_hold_active
            if mouse_jitter_mode == "Hold":
                if not mouse_jitter_hold_active:
                    mouse_jitter_hold_active = True
                    set_mouse_jitter_state(True, "Mouse Jitter hold")
            else:
                toggle_mouse_jitter()

        def mouse_jitter_trigger_released():
            nonlocal mouse_jitter_hold_active
            if mouse_jitter_mode == "Hold" and mouse_jitter_hold_active:
                mouse_jitter_hold_active = False
                set_mouse_jitter_state(False, "Mouse Jitter hold")

        def mouse_jitter_loop():
            while not stop_threads:
                if not mouse_jitter_enabled:
                    mouse_jitter_stop_event.wait(0.05)
                    mouse_jitter_stop_event.clear()
                    continue
                offset_x = 0
                offset_y = 0
                try:
                    # Relative movement preserves pointer movement made by the user.
                    offset_x = random.randint(-mouse_jitter_x, mouse_jitter_x)
                    offset_y = random.randint(-mouse_jitter_y, mouse_jitter_y)
                    if not send_relative_mouse_move(offset_x, offset_y):
                        m.move(offset_x, offset_y)
                    delay = max(0.01, (101 - mouse_jitter_speed) / 1000.0)
                    mouse_jitter_stop_event.wait(delay)
                except:
                    time.sleep(0.05)
                finally:
                    if offset_x or offset_y:
                        try:
                            if not send_relative_mouse_move(-offset_x, -offset_y):
                                m.move(-offset_x, -offset_y)
                        except:
                            pass

        # ------------------------------------
        # Load / Save
        # ------------------------------------
        def load_settings():
            nonlocal cps, mode, cycle_duty, cps_jitter, click_button_name, click_repeat_name, toggle_key, theme_name, advanced_settings_enabled, next_macro_id, smart_cycle_enabled, launch_on_startup_enabled, multi_bind_enabled, sound_feedback_enabled, macro_preview_enabled, anti_afk_enabled, anti_afk_interval, pause_on_focus_loss_enabled, auto_limiter_enabled, auto_limiter_clicks, break_reminder_enabled, break_reminder_interval, break_reminder_countdown, mouse_jitter_enabled, mouse_jitter_keybind, mouse_jitter_mode, mouse_jitter_speed, mouse_jitter_x, mouse_jitter_y, profiles, active_profile_name
            if not os.path.exists(settings_file):
                return
            try:
                with open(settings_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                cps = parse_cps(data.get("cps", 5.0))
                mode = data.get("mode", "Toggle")
                cycle_duty = min(100.0, max(0.1, float(data.get("cycle_duty", 0.1))))
                cps_jitter = min(100.0, max(0.0, float(data.get("cps_jitter", 0.0))))
                click_button_name = data.get("click_button", "Left") if data.get("click_button", "Left") in {"Left", "Right", "Middle"} else "Left"
                click_repeat_name = data.get("click_repeat", "Single") if data.get("click_repeat", "Single") in {"Single", "Double", "Triple"} else "Single"
                theme_name = data.get("theme", "Azure") if data.get("theme", "Azure") in themes else "Azure"
                advanced_settings_enabled = bool(data.get("advanced_settings_enabled", False))
                smart_cycle_enabled = bool(data.get("smart_cycle_enabled", False))
                launch_on_startup_enabled = bool(data.get("launch_on_startup_enabled", False))
                multi_bind_enabled = bool(data.get("multi_bind_enabled", False))
                sound_feedback_enabled = bool(data.get("sound_feedback_enabled", False))
                macro_preview_enabled = bool(data.get("macro_preview_enabled", False))
                anti_afk_enabled = bool(data.get("anti_afk_enabled", False))
                anti_afk_interval = max(10, int(data.get("anti_afk_interval", 60)))
                pause_on_focus_loss_enabled = bool(data.get("pause_on_focus_loss_enabled", False))
                auto_limiter_enabled = bool(data.get("auto_limiter_enabled", False))
                auto_limiter_clicks = max(1, int(data.get("auto_limiter_clicks", 1000)))
                break_reminder_enabled = bool(data.get("break_reminder_enabled", False))
                break_reminder_interval = max(60, int(data.get("break_reminder_interval", 1800)))
                break_reminder_countdown = break_reminder_interval
                mouse_jitter_enabled = bool(data.get("mouse_jitter_enabled", False))
                mouse_jitter_keybind = normalize_toggle_binding(data.get("mouse_jitter_keybind"))
                mouse_jitter_mode = data.get("mouse_jitter_mode", "Toggle") if data.get("mouse_jitter_mode", "Toggle") in {"Toggle", "Hold"} else "Toggle"
                mouse_jitter_speed = min(100, max(1, int(data.get("mouse_jitter_speed", 35))))
                mouse_jitter_x = min(30, max(1, int(data.get("mouse_jitter_x", 4))))
                mouse_jitter_y = min(30, max(1, int(data.get("mouse_jitter_y", 4))))
                profiles[:] = [profile for profile in data.get("profiles", []) if isinstance(profile, dict) and profile.get("name")]
                active_profile_name = data.get("active_profile_name")

                loaded_toggle_bindings = []
                for binding in data.get("toggle_keys", []):
                    normalized_binding = normalize_toggle_binding(binding)
                    if normalized_binding:
                        loaded_toggle_bindings.append(normalized_binding)

                key_data = data.get("toggle_key", None)
                primary_toggle_binding = normalize_toggle_binding(key_data) if key_data else None
                if primary_toggle_binding and toggle_binding_token(primary_toggle_binding) not in [toggle_binding_token(existing) for existing in loaded_toggle_bindings]:
                    loaded_toggle_bindings.insert(0, primary_toggle_binding)
                set_autoclicker_bindings(loaded_toggle_bindings)

                macros.clear()
                loaded_macros = data.get("macros", [])
                highest_id = 0
                for fallback_id, macro_data in enumerate(loaded_macros, start=1):
                    normalized = normalize_macro(macro_data, fallback_id)
                    if not normalized:
                        continue
                    macros.append(normalized)
                    highest_id = max(highest_id, normalized["id"])
                next_macro_id = highest_id + 1 if highest_id > 0 else 1
                remove_legacy_binding_duplicates()
                if not multi_bind_enabled:
                    trim_multi_bind_collections()
            except:
                pass

        def save_settings():
            key_data = serialize_toggle_binding(toggle_key)

            os.makedirs(os.path.dirname(settings_file), exist_ok=True)
            with open(settings_file, "w", encoding="utf-8") as f:
                json.dump({
                    "cps": cps,
                    "mode": mode,
                    "cycle_duty": cycle_duty,
                    "cps_jitter": cps_jitter,
                    "click_button": click_button_name,
                    "click_repeat": click_repeat_name,
                    "toggle_key": key_data,
                    "toggle_keys": [serialize_toggle_binding(binding) for binding in toggle_keys if serialize_toggle_binding(binding)],
                    "theme": theme_name,
                    "advanced_settings_enabled": advanced_settings_enabled,
                    "smart_cycle_enabled": smart_cycle_enabled,
                    "launch_on_startup_enabled": launch_on_startup_enabled,
                    "multi_bind_enabled": multi_bind_enabled,
                    "sound_feedback_enabled": sound_feedback_enabled,
                    "macro_preview_enabled": macro_preview_enabled,
                    "anti_afk_enabled": anti_afk_enabled,
                    "anti_afk_interval": anti_afk_interval,
                    "pause_on_focus_loss_enabled": pause_on_focus_loss_enabled,
                    "auto_limiter_enabled": auto_limiter_enabled,
                    "auto_limiter_clicks": auto_limiter_clicks,
                    "break_reminder_enabled": break_reminder_enabled,
                    "break_reminder_interval": break_reminder_interval,
                    "mouse_jitter_enabled": mouse_jitter_enabled,
                    "mouse_jitter_keybind": serialize_toggle_binding(mouse_jitter_keybind),
                    "mouse_jitter_mode": mouse_jitter_mode,
                    "mouse_jitter_speed": mouse_jitter_speed,
                    "mouse_jitter_x": mouse_jitter_x,
                    "mouse_jitter_y": mouse_jitter_y,
                    "profiles": profiles,
                    "active_profile_name": active_profile_name,
                    "macros": macros
                }, f)

        load_settings()
        if os.name == "nt":
            launch_on_startup_enabled = read_launch_on_startup_state()

        # ------------------------------------
        # High-precision autoclicker loop
        # ------------------------------------
        def precise_wait_until(target_time, cancel_check=None, spin_threshold=0.0015, telemetry=None):
            reached_at = None
            while not stop_threads:
                if cancel_check and cancel_check():
                    return False

                now = time.perf_counter()
                remaining = target_time - now
                if remaining <= 0:
                    reached_at = now
                    break

                if remaining > 0.020:
                    time.sleep(max(0.001, remaining - 0.006))
                elif remaining > 0.006:
                    time.sleep(max(0.0005, remaining - 0.002))
                elif remaining > spin_threshold:
                    time.sleep(max(0.0005, remaining - spin_threshold))
                else:
                    while not stop_threads:
                        if cancel_check and cancel_check():
                            return False
                        reached_at = time.perf_counter()
                        if reached_at >= target_time:
                            break
                        if target_time - reached_at > 0.0010:
                            time.sleep(0)
                    if reached_at is not None and reached_at >= target_time:
                        break

            if reached_at is None:
                return False
            if telemetry is not None:
                telemetry["target_time"] = target_time
                telemetry["reached_at"] = reached_at
                telemetry["overshoot"] = max(0.0, reached_at - target_time)
            return True

        def send_mouse_button_event(button, pressed):
            flags = native_mouse_button_flags.get(button)
            if os.name == "nt" and flags:
                button_flag = flags[0 if pressed else 1]
                try:
                    mouse_input = MOUSEINPUT(
                        0,
                        0,
                        0,
                        button_flag,
                        0,
                        0
                    )
                    input_event = INPUT()
                    input_event.type = INPUT_MOUSE
                    input_event.union.mi = mouse_input
                    if ctypes.windll.user32.SendInput(1, ctypes.byref(input_event), ctypes.sizeof(input_event)) == 1:
                        return True
                except:
                    pass
                try:
                    ctypes.windll.user32.mouse_event(button_flag, 0, 0, 0, 0)
                    return True
                except:
                    pass

            try:
                if pressed:
                    m.press(button)
                else:
                    m.release(button)
                return True
            except:
                return False

        def send_relative_mouse_move(offset_x, offset_y):
            if os.name != "nt":
                return False
            try:
                mouse_input = MOUSEINPUT(
                    int(offset_x),
                    int(offset_y),
                    0,
                    MOUSEEVENTF_MOVE,
                    0,
                    0
                )
                input_event = INPUT()
                input_event.type = INPUT_MOUSE
                input_event.union.mi = mouse_input
                return ctypes.windll.user32.SendInput(1, ctypes.byref(input_event), ctypes.sizeof(input_event)) == 1
            except:
                return False

        def emit_registered_mouse_click(button, hold_time, release_settle=0.0, cancel_check=None, timing_sample=None, enforce_minimum=True):
            pressed = False
            completed = False
            press_started_at = None
            hold_completed_at = None
            release_completed_at = None
            settle_completed_at = None
            if enforce_minimum:
                hold_time = max(get_minimum_click_hold_time(button), float(hold_time))
                release_settle = max(get_minimum_release_settle_time(button), float(release_settle))
            else:
                hold_time = max(0.0005, float(hold_time))
                release_settle = max(0.0005, float(release_settle))

            with mouse_action_lock:
                try:
                    press_started_at = time.perf_counter()
                    pressed = send_mouse_button_event(button, True)
                    if pressed:
                        hold_wait = {}
                        completed = precise_wait_until(
                            press_started_at + hold_time,
                            cancel_check=cancel_check,
                            telemetry=hold_wait
                        )
                        hold_completed_at = hold_wait.get("reached_at", time.perf_counter())
                finally:
                    if pressed:
                        try:
                            release_mouse_button_safely(button)
                            release_completed_at = time.perf_counter()
                        except:
                            pass

            if pressed and release_completed_at is None:
                release_completed_at = time.perf_counter()

            if not completed:
                return False

            settle_completed_at = release_completed_at
            if release_settle > 0:
                settle_wait = {}
                if not precise_wait_until(
                    release_completed_at + release_settle,
                    cancel_check=cancel_check,
                    telemetry=settle_wait
                ):
                    return False
                settle_completed_at = settle_wait.get("reached_at", time.perf_counter())

            if timing_sample is not None and press_started_at is not None:
                timing_sample["hold_elapsed"] = max(0.0, (hold_completed_at or release_completed_at or time.perf_counter()) - press_started_at)
                timing_sample["settle_elapsed"] = max(0.0, (settle_completed_at or time.perf_counter()) - (release_completed_at or time.perf_counter()))
                timing_sample["completed_at"] = settle_completed_at or release_completed_at or time.perf_counter()

            return True

        def emit_precise_clicks(button, repeat_count, interval, cycle_started_at=None):
            repeat_count = max(1, int(repeat_count))
            interval = max(0.001, float(interval))
            cycle_started = cycle_started_at if cycle_started_at is not None else time.perf_counter()
            cycle_target_end = cycle_started + interval
            release_settle = get_effective_release_settle_time(button, repeat_count, interval)
            hold_time = get_effective_cycle_hold_time(button, repeat_count, interval)
            inter_click_recovery = get_inter_click_recovery_time(button, repeat_count, interval)

            def cancelled():
                return stop_threads or not autoclicker_active

            clicks_sent = 0
            last_click_completed_at = cycle_started
            for index in range(repeat_count):
                if cancelled():
                    break

                target_start = cycle_started + ((interval * index) / repeat_count)
                if repeat_count > 1:
                    target_start = max(target_start, last_click_completed_at + inter_click_recovery)

                start_wait = {}
                if not precise_wait_until(target_start, cancel_check=cancelled, telemetry=start_wait):
                    break
                update_scheduler_lag(start_wait.get("overshoot", 0.0))

                click_sample = {}
                if not emit_registered_mouse_click(
                    button,
                    hold_time,
                    release_settle=release_settle,
                    cancel_check=cancelled,
                    timing_sample=click_sample
                ):
                    break

                clicks_sent += 1
                last_click_completed_at = click_sample.get("completed_at", time.perf_counter())
                update_click_timing_profile(button, repeat_count, click_sample)

            completed_at = max(time.perf_counter(), last_click_completed_at)
            active_cycle_completed_at = completed_at
            if clicks_sent and completed_at < cycle_target_end:
                end_wait = {}
                precise_wait_until(cycle_target_end, cancel_check=cancelled, telemetry=end_wait)
                update_scheduler_lag(end_wait.get("overshoot", 0.0))
                completed_at = end_wait.get("reached_at", time.perf_counter())

            if clicks_sent:
                update_click_timing_profile(button, repeat_count, {
                    "cycle_elapsed": max(0.0, active_cycle_completed_at - cycle_started)
                })

            return clicks_sent, completed_at

        def autoclicker_loop():
            nonlocal autoclicker_active, stop_threads, cps, cycle_duty, break_reminder_enabled, last_break_reminder_time, break_reminder_interval
            set_current_thread_high_priority()
            next_click = time.perf_counter()
            last_cycle_completion = next_click

            while not stop_threads:
                if not autoclicker_active:
                    autoclicker_wake_event.wait(0.05)
                    autoclicker_wake_event.clear()
                    next_click = time.perf_counter()
                    last_cycle_completion = next_click
                    continue

                effective_cps = get_effective_jittered_cps()
                button = get_click_button()
                repeat_count = get_click_repeat_count()
                interval = get_effective_cycle_interval(button, repeat_count, effective_cps)
                now = time.perf_counter()

                if next_click < last_cycle_completion:
                    next_click = last_cycle_completion

                if now - next_click > max(0.004, interval * 0.35):
                    update_scheduler_lag(now - next_click)
                    next_click = now

                cycle_wait = {}
                if not precise_wait_until(next_click, cancel_check=lambda: not autoclicker_active, telemetry=cycle_wait):
                    next_click = time.perf_counter()
                    last_cycle_completion = next_click
                    continue

                cycle_started_at = cycle_wait.get("reached_at", time.perf_counter())
                update_scheduler_lag(cycle_wait.get("overshoot", 0.0))

                if stop_threads or not autoclicker_active:
                    next_click = time.perf_counter()
                    last_cycle_completion = next_click
                    continue

                clicks_sent, cycle_completed_at = emit_precise_clicks(
                    button,
                    repeat_count,
                    interval,
                    cycle_started_at=cycle_started_at
                )

                if clicks_sent:
                    session_stats["clicks"] += clicks_sent
                last_cycle_completion = max(last_cycle_completion, cycle_completed_at)

                ideal_next = next_click + interval
                scheduler_delay = max(0.0, last_cycle_completion - ideal_next)
                if scheduler_delay > 0:
                    update_scheduler_lag(scheduler_delay)

                if scheduler_delay > max(0.004, interval * 0.35):
                    next_click = last_cycle_completion + interval
                else:
                    next_click = max(ideal_next, last_cycle_completion)
                
                # Check break reminder
                if break_reminder_enabled:
                    now = time.perf_counter()
                    if now - last_break_reminder_time >= break_reminder_interval:
                        last_break_reminder_time = now
                        root.after(0, show_break_reminder_timer)

        threading.Thread(target=autoclicker_loop, daemon=True).start()

        # ------------------------------------
        # Keyboard listeners
        # ------------------------------------
        def on_press_key(key):
            nonlocal toggle_key, autoclicker_active, setting_keybind, macro_trigger_capture_id, multi_bind_capture_target, mouse_jitter_keybind, mouse_jitter_capture
            try:
                lowered = get_listener_key_name(key)
                if not lowered:
                    return
                if is_modifier_key(lowered):
                    pressed_modifiers.add(lowered)
                    return
                active_key = get_active_key_combo(lowered) or lowered
                kname = active_key

                if mouse_jitter_capture:
                    if active_key == "esc":
                        mouse_jitter_capture = False
                        mouse_jitter_key_label.config(text=format_keybind_text(mouse_jitter_keybind))
                        return
                    if lowered != "left":
                        candidate = ("keyboard", active_key)
                        if not can_assign_binding(candidate, "mouse_jitter"):
                            return
                        mouse_jitter_keybind = candidate
                        mouse_jitter_capture = False
                        mouse_jitter_key_label.config(text=format_keybind_text(mouse_jitter_keybind))
                        save_settings()
                        render_mouse_page()
                    return

                if multi_bind_capture_target is not None:
                    if active_key in {"esc", "escape"}:
                        multi_bind_capture_target = None
                        render_mods_page()
                        log("Keybind capture cancelled")
                        return
                    if lowered == "left":
                        log("❌ Left click cannot be keybind")
                        return
                    target = dict(multi_bind_capture_target)
                    if target["owner"] == "autoclicker":
                        set_autoclicker_binding_at(target["index"], ("keyboard", active_key))
                        key_label.config(text=format_autoclicker_keybind_text())
                        log(f"✔ Autoclicker keybind set to {str(kname).upper()}")
                    else:
                        macro = get_macro_by_id(target["macro_id"])
                        if macro:
                            set_macro_trigger_at(macro, target["index"], {"type": "keyboard", "key": active_key})
                            arm_macro_for_use(macro)
                            log(f"✔ Macro keybind set to {str(kname).upper()}")
                    multi_bind_capture_target = None
                    save_settings()
                    render_macro_editor()
                    render_macro_list()
                    render_mods_page()
                    return

                if setting_keybind:
                    if active_key in {"esc", "escape"}:
                        setting_keybind = False
                        key_label.config(text=format_autoclicker_keybind_text())
                        log("Keybind capture cancelled")
                        return

                    if lowered == "left":
                        log("❌ Left click cannot be keybind")
                        return

                    candidate = ("keyboard", active_key)
                    if not can_assign_binding(candidate, "autoclicker"):
                        return
                    set_primary_autoclicker_binding(candidate)
                    key_label.config(text=format_autoclicker_keybind_text())
                    save_settings()
                    log(f"✔ Keybind set to {str(kname).upper()}")
                    setting_keybind = False
                    render_mods_page()
                    return

                if macro_trigger_capture_id is not None:
                    macro = get_macro_by_id(macro_trigger_capture_id)
                    if macro:
                        candidate = {"type": "keyboard", "key": active_key}
                        if not can_assign_binding(candidate, f"macro:{macro['id']}"):
                            return
                        set_macro_trigger_at(macro, 0, candidate)
                        arm_macro_for_use(macro)
                        macro_trigger_capture_id = None
                        save_settings()
                        log(f"✔ Macro keybind set to {str(kname).upper()}")
                        render_macro_editor()
                        render_macro_list()
                        render_mods_page()
                    else:
                        macro_trigger_capture_id = None
                    return

                if active_key == "esc":
                    set_autoclicker_state(False, "Panic stop")
                    return

                matching_autoclicker_bindings = [binding for binding in get_active_autoclicker_bindings() if binding and binding[0] == "keyboard" and active_key == binding[1]]
                if matching_autoclicker_bindings:
                    if mode_var.get() == "Toggle":
                        toggle_autoclicker("Keyboard keybind")
                    else:
                        for binding in matching_autoclicker_bindings:
                            token = toggle_binding_token(binding)
                            if token:
                                active_autoclicker_holds.add(token)
                        set_autoclicker_state(True, "Keyboard hold")

                for macro in macros:
                    if not macro.get("enabled"):
                        continue
                    matching_triggers = [trigger for trigger in get_macro_triggers(macro) if trigger.get("type") == "keyboard" and active_key == trigger.get("key")]
                    if not matching_triggers:
                        continue
                    if macro_uses_hold_mode(macro):
                        hold_inputs = active_macro_hold_inputs.setdefault(macro["id"], set())
                        added = False
                        for trigger in matching_triggers:
                            token = macro_binding_token(trigger)
                            if token and token not in hold_inputs:
                                hold_inputs.add(token)
                                added = True
                        if added:
                            active_macro_triggers.add(macro["id"])
                            start_macro_execution(macro["id"], repeat_while_held=True)
                    else:
                        if macro["id"] in active_macro_triggers:
                            continue
                        active_macro_triggers.add(macro["id"])
                        start_macro_execution(macro["id"], repeat_while_held=False)

                if mouse_jitter_keybind and mouse_jitter_keybind[0] == "keyboard" and active_key == mouse_jitter_keybind[1]:
                    mouse_jitter_trigger_pressed()
            except:
                pass

        def on_release_key(key):
            nonlocal autoclicker_active
            try:
                lowered = get_listener_key_name(key)
                if not lowered:
                    return
                is_modifier = is_modifier_key(lowered)
                released_combo = None
                if not is_modifier:
                    released_combo = get_active_key_combo(lowered) or lowered

                matching_autoclicker_bindings = []
                if mode_var.get() == "Hold":
                    for binding in get_active_autoclicker_bindings():
                        if not binding or binding[0] != "keyboard":
                            continue
                        if is_modifier:
                            if lowered in str(binding[1]).split("+"):
                                matching_autoclicker_bindings.append(binding)
                        elif released_combo == binding[1]:
                            matching_autoclicker_bindings.append(binding)
                    if matching_autoclicker_bindings:
                        for binding in matching_autoclicker_bindings:
                            token = toggle_binding_token(binding)
                            if token in active_autoclicker_holds:
                                active_autoclicker_holds.discard(token)
                        if not active_autoclicker_holds:
                            set_autoclicker_state(False, "Keyboard hold")

                for macro in macros:
                    matching_triggers = []
                    for trigger in get_macro_triggers(macro):
                        if trigger.get("type") != "keyboard":
                            continue
                        if is_modifier:
                            if lowered in str(trigger.get("key", "")).split("+"):
                                matching_triggers.append(trigger)
                        elif released_combo == trigger.get("key"):
                            matching_triggers.append(trigger)
                    if not matching_triggers:
                        continue
                    if macro_uses_hold_mode(macro):
                        hold_inputs = active_macro_hold_inputs.setdefault(macro["id"], set())
                        for trigger in matching_triggers:
                            token = macro_binding_token(trigger)
                            if token in hold_inputs:
                                hold_inputs.discard(token)
                        if not hold_inputs:
                            active_macro_triggers.discard(macro["id"])
                            stop_macro_execution(macro["id"])
                    else:
                        active_macro_triggers.discard(macro["id"])

                if mouse_jitter_keybind and mouse_jitter_keybind[0] == "keyboard":
                    jitter_released = lowered in str(mouse_jitter_keybind[1]).split("+") if is_modifier else released_combo == mouse_jitter_keybind[1]
                    if jitter_released:
                        mouse_jitter_trigger_released()

                if is_modifier:
                    pressed_modifiers.discard(lowered)
            except:
                pass

        # ------------------------------------
        # Mouse listener
        # ------------------------------------
        def on_click_mouse(x, y, button, pressed):
            nonlocal toggle_key, autoclicker_active, setting_keybind, macro_trigger_capture_id, multi_bind_capture_target, mouse_jitter_keybind, mouse_jitter_capture
            button_name = normalize_mouse_binding_name(button)

            if mouse_jitter_capture:
                if button == Button.left:
                    return
                if pressed:
                    candidate = ("mouse", button)
                    if not can_assign_binding(candidate, "mouse_jitter"):
                        return
                    mouse_jitter_keybind = candidate
                    mouse_jitter_capture = False
                    mouse_jitter_key_label.config(text=format_keybind_text(mouse_jitter_keybind))
                    save_settings()
                    render_mouse_page()
                return

            if multi_bind_capture_target is not None:
                if button == Button.left:
                    log("❌ Left click cannot be keybind")
                    return
                target = dict(multi_bind_capture_target)
                if target["owner"] == "autoclicker":
                    set_autoclicker_binding_at(target["index"], ("mouse", button))
                    key_label.config(text=format_autoclicker_keybind_text())
                    log(f"✔ Autoclicker keybind set to {(button_name or button.name).upper()} CLICK")
                else:
                    macro = get_macro_by_id(target["macro_id"])
                    if macro:
                        set_macro_trigger_at(macro, target["index"], {"type": "mouse", "key": button_name or button.name})
                        arm_macro_for_use(macro)
                        log(f"✔ Macro keybind set to {(button_name or button.name).upper()} CLICK")
                multi_bind_capture_target = None
                save_settings()
                render_macro_editor()
                render_macro_list()
                render_mods_page()
                return

            if setting_keybind:
                if button == Button.left:
                    log("❌ Cannot bind left click")
                    return

                candidate = ("mouse", button)
                if not can_assign_binding(candidate, "autoclicker"):
                    return
                set_primary_autoclicker_binding(candidate)
                key_label.config(text=format_autoclicker_keybind_text())
                save_settings()
                log(f"✔ Mouse keybind set to {button_name or button.name}")
                setting_keybind = False
                render_mods_page()
                return

            if macro_trigger_capture_id is not None:
                if button == Button.left:
                    log("❌ Left click cannot be macro keybind")
                    return
                macro = get_macro_by_id(macro_trigger_capture_id)
                if macro:
                    candidate = {"type": "mouse", "key": button_name or button.name}
                    if not can_assign_binding(candidate, f"macro:{macro['id']}"):
                        return
                    set_macro_trigger_at(macro, 0, candidate)
                    arm_macro_for_use(macro)
                    macro_trigger_capture_id = None
                    save_settings()
                    log(f"✔ Macro keybind set to {(button_name or button.name).upper()} CLICK")
                    render_macro_editor()
                    render_macro_list()
                    render_mods_page()
                else:
                    macro_trigger_capture_id = None
                return

            matching_autoclicker_bindings = [binding for binding in get_active_autoclicker_bindings() if binding and binding[0] == "mouse" and binding[1] == button]
            if matching_autoclicker_bindings:
                if mode_var.get() == "Toggle" and pressed:
                    toggle_autoclicker("Mouse keybind")
                elif mode_var.get() == "Hold":
                    for binding in matching_autoclicker_bindings:
                        token = toggle_binding_token(binding)
                        if not token:
                            continue
                        if pressed:
                            active_autoclicker_holds.add(token)
                        elif token in active_autoclicker_holds:
                            active_autoclicker_holds.discard(token)
                    if pressed:
                        set_autoclicker_state(True, "Mouse hold")
                    elif not active_autoclicker_holds:
                        set_autoclicker_state(False, "Mouse hold")

            for macro in macros:
                if not macro.get("enabled"):
                    continue
                matching_triggers = [
                    trigger for trigger in get_macro_triggers(macro)
                    if trigger.get("type") == "mouse" and button_name and button_name == trigger.get("key")
                ]
                if not matching_triggers:
                    continue
                if macro_uses_hold_mode(macro):
                    if pressed:
                        hold_inputs = active_macro_hold_inputs.setdefault(macro["id"], set())
                        added = False
                        for trigger in matching_triggers:
                            token = macro_binding_token(trigger)
                            if token and token not in hold_inputs:
                                hold_inputs.add(token)
                                added = True
                        if added and macro["id"] not in active_macro_triggers:
                            active_macro_triggers.add(macro["id"])
                            start_macro_execution(macro["id"], repeat_while_held=True)
                    else:
                        hold_inputs = active_macro_hold_inputs.setdefault(macro["id"], set())
                        for trigger in matching_triggers:
                            token = macro_binding_token(trigger)
                            if token in hold_inputs:
                                hold_inputs.discard(token)
                        if not hold_inputs:
                            active_macro_triggers.discard(macro["id"])
                            stop_macro_execution(macro["id"])
                elif pressed and macro["id"] not in active_macro_triggers:
                    active_macro_triggers.add(macro["id"])
                    start_macro_execution(macro["id"], repeat_while_held=False)
                elif not pressed:
                    active_macro_triggers.discard(macro["id"])

            if mouse_jitter_keybind and mouse_jitter_keybind[0] == "mouse" and button == mouse_jitter_keybind[1]:
                if pressed:
                    mouse_jitter_trigger_pressed()
                else:
                    mouse_jitter_trigger_released()

        # ------------------------------------
        # GUI
        # ------------------------------------
        root = tk.Tk()
        root.title("Zhydra")
        root.geometry("1280x820")
        root.minsize(980, 620)
        root.configure(bg=get_theme()["window_bg"])
        try:
            root.attributes("-alpha", 0.0)
        except:
            pass

        size_state = {
            "width_compact": False,
            "height_compact": False,
            "normal_width": 1280,
            "normal_height": 820,
            "compact_width": 980,
            "compact_height": 620
        }

        def refresh_window_size():
            width = size_state["compact_width"] if size_state["width_compact"] else size_state["normal_width"]
            height = size_state["compact_height"] if size_state["height_compact"] else size_state["normal_height"]
            root.geometry(f"{width}x{height}")

        def toggle_width_compact():
            size_state["width_compact"] = not size_state["width_compact"]
            width_shrink_button.configure(text="▶" if size_state["width_compact"] else "◀")
            refresh_window_size()

        def toggle_height_compact():
            size_state["height_compact"] = not size_state["height_compact"]
            height_shrink_button.configure(text="▲" if size_state["height_compact"] else "▼")
            refresh_window_size()

        def hex_to_rgb(color):
            color = color.lstrip("#")
            return tuple(int(color[i:i + 2], 16) for i in (0, 2, 4))

        def rgb_to_hex(rgb):
            return "#%02x%02x%02x" % tuple(max(0, min(255, int(v))) for v in rgb)

        def blend(color_a, color_b, factor):
            factor = max(0.0, min(1.0, factor))
            a = hex_to_rgb(color_a)
            b = hex_to_rgb(color_b)
            return rgb_to_hex(tuple(a[i] + (b[i] - a[i]) * factor for i in range(3)))

        def nudge(color, toward="#FFFFFF", amount=0.12):
            return blend(color, toward, amount)

        def gradient_color(stops, factor):
            factor = max(0.0, min(1.0, factor))
            for index in range(len(stops) - 1):
                left_stop, left_color = stops[index]
                right_stop, right_color = stops[index + 1]
                if left_stop <= factor <= right_stop:
                    local = (factor - left_stop) / max(0.0001, right_stop - left_stop)
                    return blend(left_color, right_color, local)
            return stops[-1][1]

        def rounded_rect_points(x1, y1, x2, y2, radius):
            radius = max(1, min(radius, (x2 - x1) / 2, (y2 - y1) / 2))
            return [
                x1 + radius, y1,
                x1 + radius, y1,
                x2 - radius, y1,
                x2 - radius, y1,
                x2, y1,
                x2, y1 + radius,
                x2, y1 + radius,
                x2, y2 - radius,
                x2, y2 - radius,
                x2, y2,
                x2 - radius, y2,
                x2 - radius, y2,
                x1 + radius, y2,
                x1 + radius, y2,
                x1, y2,
                x1, y2 - radius,
                x1, y2 - radius,
                x1, y1 + radius,
                x1, y1 + radius,
                x1, y1
            ]

        def draw_rounded_rect(canvas, x1, y1, x2, y2, radius, **kwargs):
            return canvas.create_polygon(
                rounded_rect_points(x1, y1, x2, y2, radius),
                smooth=True,
                splinesteps=24,
                **kwargs
            )

        background = tk.Canvas(root, bg=get_theme()["window_bg"], highlightthickness=0, bd=0)
        background.place(relx=0, rely=0, relwidth=1, relheight=1)

        content = tk.Frame(root, bg=get_theme()["window_bg"])
        content.place(relx=0, rely=0, relwidth=1, relheight=1)

        style = ttk.Style()
        try:
            style.theme_use("clam")
        except:
            pass

        style.configure(
            "Clean.TCombobox",
            fieldbackground="#241D31",
            background="#241D31",
            foreground="#F3EEFF",
            bordercolor="#8B5CF6",
            lightcolor="#241D31",
            darkcolor="#241D31",
            arrowcolor="#D7C3FF",
            borderwidth=0,
            relief="flat",
            padding=7
        )
        style.map(
            "Clean.TCombobox",
            fieldbackground=[("readonly", "#241D31")],
            background=[("readonly", "#241D31")],
            foreground=[("readonly", "#F3EEFF")]
        )
        style.configure(
            "Clean.Vertical.TScrollbar",
            gripcount=0,
            background=get_theme()["scrollbar_thumb"],
            troughcolor=get_theme()["scrollbar_trough"],
            bordercolor=get_theme()["scrollbar_border"],
            arrowcolor=get_theme()["scrollbar_arrow"],
            darkcolor=get_theme()["scrollbar_thumb"],
            lightcolor=get_theme()["scrollbar_thumb"],
            relief="flat",
            borderwidth=1,
            arrowsize=13
        )
        style.map(
            "Clean.Vertical.TScrollbar",
            background=[("active", get_theme()["scrollbar_thumb_active"]), ("pressed", get_theme()["scrollbar_thumb_active"])],
            darkcolor=[("active", get_theme()["scrollbar_thumb_active"]), ("pressed", get_theme()["scrollbar_thumb_active"])],
            lightcolor=[("active", get_theme()["scrollbar_thumb_active"]), ("pressed", get_theme()["scrollbar_thumb_active"])],
            arrowcolor=[("active", get_theme()["scrollbar_arrow"]), ("pressed", get_theme()["scrollbar_arrow"])]
        )

        glow_state = {
            "tick": 0.0,
            "running": True,
            "intro": 0.0
        }
        pending_redraw = None

        def draw_background(event=None):
            theme = get_theme()
            t = glow_state["tick"]
            w = max(root.winfo_width(), 980)
            h = max(root.winfo_height(), 720)
            background.delete("bgfx")
            background.configure(bg=theme["window_bg"])

            # --- Animated multi-directional gradient ---
            # Define 4 moving color stops (corners)
            stops = [
                (int(w * (0.18 + 0.08 * math.sin(t * 0.7))), int(h * (0.18 + 0.07 * math.cos(t * 0.6))), theme["glow_palette"][0]),
                (int(w * (0.82 + 0.07 * math.cos(t * 0.9))), int(h * (0.22 + 0.08 * math.sin(t * 0.8))), theme["glow_palette"][1]),
                (int(w * (0.68 + 0.06 * math.sin(t * 0.5))), int(h * (0.82 + 0.07 * math.cos(t * 0.4))), theme["glow_palette"][2]),
                (int(w * (0.32 + 0.07 * math.cos(t * 0.8))), int(h * (0.78 + 0.08 * math.sin(t * 0.7))), theme["glow_palette"][3]),
            ]

            # Fill with a grid of rectangles, each color is a blend of the 4 stops
            grid = 16
            for gy in range(grid):
                for gx in range(grid):
                    px = int(w * gx / (grid - 1))
                    py = int(h * gy / (grid - 1))
                    # Blend all stops by inverse distance
                    total = 0.0
                    color_accum = [0, 0, 0]
                    for sx, sy, scol in stops:
                        dist = max(0.001, math.hypot(px - sx, py - sy))
                        weight = 1.0 / (dist ** 1.7)
                        rgb = hex_to_rgb(scol)
                        color_accum[0] += rgb[0] * weight
                        color_accum[1] += rgb[1] * weight
                        color_accum[2] += rgb[2] * weight
                        total += weight
                    rgb = tuple(int(c / total) for c in color_accum)
                    color = rgb_to_hex(rgb)
                    x1 = int(px - w / grid / 2)
                    y1 = int(py - h / grid / 2)
                    x2 = int(px + w / grid / 2)
                    y2 = int(py + h / grid / 2)
                    background.create_rectangle(x1, y1, x2, y2, fill=color, outline="", tags="bgfx")

            # --- Animated light rays overlay ---
            ray_count = 7
            for i in range(ray_count):
                angle = t * 0.7 + i * (math.pi * 2 / ray_count) + math.sin(t * 0.5 + i)
                cx = w // 2
                cy = h // 2
                length = int(0.7 * max(w, h))
                width = int(0.13 * min(w, h))
                x1 = int(cx + math.cos(angle) * length * 0.2)
                y1 = int(cy + math.sin(angle) * length * 0.2)
                x2 = int(cx + math.cos(angle) * length)
                y2 = int(cy + math.sin(angle) * length)
                color = blend(theme["glow_palette"][i % 4], theme["window_bg"], 0.65)
                background.create_line(x1, y1, x2, y2, fill=color, width=width, tags="bgfx", stipple="gray50")

            # --- Soft blobs (subtler, more blended) ---
            def draw_blob(cx, cy, radius, color, layers=4):
                for ring in range(layers, 0, -1):
                    outer = ring / layers
                    r = int(radius * (0.22 + outer * 0.82))
                    fill = blend(color, theme["window_bg"], 0.62 + outer * 0.32)
                    background.create_oval(
                        cx - r, cy - r, cx + r, cy + r,
                        fill=fill, outline="", tags="bgfx"
                    )
            blobs = [
                (0.18 + math.sin(t * 0.52) * 0.09,  0.16 + math.cos(t * 0.38) * 0.07,  320, theme["glow_palette"][0]),
                (0.82 + math.cos(t * 0.44) * 0.07,  0.24 + math.sin(t * 0.60) * 0.09,  260, theme["glow_palette"][1]),
            ]
            for rel_x, rel_y, radius, color in blobs:
                draw_blob(int(w * rel_x), int(h * rel_y), radius, color)

            # --- Flowing ribbon waves (subtle, more transparent) ---
            ribbon_defs = [
                (theme["glow_palette"][0], 0.15, 32, 0.70, 0.0,  60, 18),
                (theme["glow_palette"][1], 0.46, 28, 0.58, 1.6,  44, 12),
            ]
            for color, base_y, amp, speed, phase, thick_outer, thick_inner in ribbon_defs:
                pts = []
                for x in range(-100, w + 120, 32):
                    y = (
                        h * base_y
                        + math.sin((x / 140.0) + t * speed * 2.0 + phase) * amp
                        + math.cos((x / 240.0) - t * speed * 1.2 - phase) * (amp * 1.5)
                    )
                    pts.extend([x, y])
                if len(pts) >= 4:
                    background.create_line(
                        pts, fill=blend(color, theme["window_bg"], 0.82),
                        width=thick_outer, smooth=True, splinesteps=10, capstyle="round", tags="bgfx"
                    )
                    background.create_line(
                        pts, fill=blend(color, theme["window_bg"], 0.70),
                        width=thick_inner, smooth=True, splinesteps=10, capstyle="round", tags="bgfx"
                    )

            # --- Borders ---
            border_tone = blend(theme["section_accent"], theme["window_bg"], 0.91)
            inner_border = blend(theme["card_border"], theme["window_bg"], 0.78)
            background.create_rectangle(12, 12, w - 12, h - 12, outline=border_tone, width=1, tags="bgfx")
            background.create_rectangle(26, 26, w - 26, h - 26, outline=inner_border, width=1, tags="bgfx")

        def animate_background():
            if not glow_state["running"]:
                return
            glow_state["tick"] += 0.018
            draw_background()
            root.after(100, animate_background)

        def fade_in_window(alpha=0.0):
            next_alpha = min(1.0, alpha + 0.06)
            glow_state["intro"] = next_alpha
            try:
                root.attributes("-alpha", next_alpha)
            except:
                glow_state["intro"] = 1.0
                return
            if next_alpha < 1.0:
                root.after(16, lambda: fade_in_window(next_alpha))

        def create_settings_gear_button(parent, command):
            canvas = tk.Canvas(
                parent,
                width=34,
                height=34,
                bg=parent.cget("bg"),
                highlightthickness=0,
                bd=0,
                relief="flat",
                cursor="hand2"
            )

            state = {"hover": False, "pressed": False}

            def gear_points(cx, cy, inner_radius, outer_radius, teeth=8, start_angle=-90):
                points = []
                for index in range(teeth * 2):
                    angle = math.radians(start_angle + (360 / (teeth * 2)) * index)
                    radius = outer_radius if index % 2 == 0 else inner_radius
                    points.extend([cx + math.cos(angle) * radius, cy + math.sin(angle) * radius])
                return points

            def redraw():
                theme = get_theme()
                canvas.delete("all")
                canvas.configure(bg=parent.cget("bg"))

                shell_fill = theme["gear_active_bg"] if state["hover"] else theme["gear_bg"]
                shell_outline = theme["gear_border"]
                if state["pressed"]:
                    shell_fill = blend(shell_fill, theme["window_bg"], 0.2)

                draw_rounded_rect(canvas, 1, 1, 33, 33, 12, fill=shell_fill, outline=shell_outline, width=1)
                draw_rounded_rect(canvas, 4, 4, 30, 30, 10, fill=blend(shell_fill, theme["window_bg"], 0.14), outline="")

                gear_fill = blend(theme["gear_fg"], theme["button_outline_hover"], 0.15 if state["hover"] else 0.0)
                gear_outline = blend(theme["gear_border"], theme["gear_fg"], 0.55)
                cx, cy = 17, 17
                canvas.create_polygon(
                    gear_points(cx, cy, 7.0, 9.4),
                    fill=gear_fill,
                    outline=gear_outline,
                    width=1,
                    smooth=True,
                    splinesteps=24
                )
                canvas.create_oval(cx - 6.4, cy - 6.4, cx + 6.4, cy + 6.4, fill=shell_fill, outline=shell_fill)
                canvas.create_oval(cx - 4.2, cy - 4.2, cx + 4.2, cy + 4.2, fill=gear_fill, outline=gear_outline, width=1)
                canvas.create_oval(cx - 1.5, cy - 1.5, cx + 1.5, cy + 1.5, fill=shell_fill, outline="")

            def on_enter(_event=None):
                state["hover"] = True
                redraw()

            def on_leave(_event=None):
                state["hover"] = False
                state["pressed"] = False
                redraw()

            def on_press(_event=None):
                state["pressed"] = True
                redraw()

            def on_release(_event=None):
                was_pressed = state["pressed"]
                state["pressed"] = False
                redraw()
                if was_pressed:
                    command()

            canvas.bind("<Enter>", on_enter)
            canvas.bind("<Leave>", on_leave)
            canvas.bind("<ButtonPress-1>", on_press)
            canvas.bind("<ButtonRelease-1>", on_release)
            canvas._refresh_theme = redraw
            themed_soft_buttons.append(canvas)
            redraw()
            return canvas

        def create_soft_button(parent, text, command, width=190):
            BTN_H = 44
            RADIUS = 14
            canvas = tk.Canvas(
                parent,
                width=width,
                height=BTN_H,
                bg=parent.cget("bg"),
                highlightthickness=0,
                bd=0,
                relief="flat",
                cursor="hand2"
            )

            cx = width / 2
            cy = BTN_H / 2

            body  = draw_rounded_rect(canvas, 2, 2, width - 2, BTN_H - 2, RADIUS, fill="", outline="", width=1, tags=("button_art", "button_body"))
            label = canvas.create_text(
                cx, cy,
                text=text,
                fill="#FFFFFF",
                font=("Segoe UI", 10, "bold"),
                tags=("button_art", "button_label")
            )

            state = {"hover": False, "pressed": False}

            def repaint():
                if not canvas.winfo_exists():
                    return
                theme = get_theme()
                hov = state["hover"]
                prs = state["pressed"]

                body_color = (
                    theme["button_body_pressed"] if prs
                    else theme["button_body_hover"] if hov
                    else theme["button_body"]
                )
                outline_col = theme["button_outline_hover"] if hov else theme["button_outline"]

                canvas.configure(bg=parent.cget("bg"))
                canvas.coords(body,  *rounded_rect_points(2, 2, width - 2, BTN_H - 2, RADIUS))
                canvas.coords(label, cx, cy)

                canvas.itemconfigure(body,  fill=body_color, outline=outline_col)
                canvas.itemconfigure(label, fill=theme["button_label"])

            def on_enter(_e=None):
                state["hover"] = True
                repaint()

            def on_leave(_e=None):
                state["hover"] = False
                state["pressed"] = False
                repaint()

            def on_press(_e=None):
                state["pressed"] = True
                repaint()

            def on_release(ev=None):
                was = state["pressed"]
                state["pressed"] = False
                repaint()
                if was and ev and 0 <= ev.x <= width and 0 <= ev.y <= BTN_H:
                    command()

            repaint()
            canvas.bind("<Enter>", on_enter)
            canvas.bind("<Leave>", on_leave)
            canvas.bind("<ButtonPress-1>", on_press)
            canvas.bind("<ButtonRelease-1>", on_release)
            for tag in ("button_body", "button_label"):
                canvas.tag_bind(tag, "<Enter>", on_enter)
                canvas.tag_bind(tag, "<Leave>", on_leave)
                canvas.tag_bind(tag, "<ButtonPress-1>", on_press)
                canvas.tag_bind(tag, "<ButtonRelease-1>", on_release)
            canvas._refresh_theme = repaint
            themed_soft_buttons.append(canvas)
            return canvas

        def style_modern_button(button, kind="secondary", compact=False, tiny=False):
            state = {"hover": False, "pressed": False}

            def palette():
                theme = get_theme()
                if kind == "primary":
                    base   = theme["button_body"]
                    hov    = theme["button_body_hover"]
                    prs    = theme["button_body_pressed"]
                    border = theme["button_outline"]
                    bh     = theme["button_outline_hover"]
                    fg     = theme["button_label"]
                elif kind == "subtle":
                    base   = blend(theme["entry_bg"],         theme["section_frame_bg"], 0.18)
                    hov    = blend(theme["entry_bg"],         theme["section_accent"],   0.08)
                    prs    = blend(theme.get("panel_shadow", theme["button_shadow"]), theme["entry_bg"], 0.14)
                    border = blend(theme["entry_border"],     theme["section_border"],   0.28)
                    bh     = blend(theme["entry_focus"],      theme["entry_border"],     0.38)
                    fg     = theme["title_fg"]
                else:
                    base   = blend(theme["close_bg"],         theme["section_frame_bg"], 0.12)
                    hov    = blend(theme["close_active_bg"],  theme["button_body"],       0.06)
                    prs    = blend(theme["close_active_bg"],  theme["window_bg"],         0.08)
                    border = blend(theme["close_border"],     theme["entry_border"],      0.22)
                    bh     = blend(theme["button_outline"],   theme["close_border"],      0.30)
                    fg     = theme["close_fg"]
                return {"bg": base, "hover": hov, "pressed": prs, "border": border, "border_hover": bh, "fg": fg}

            def repaint():
                c = palette()
                bg     = c["pressed"] if state["pressed"] else (c["hover"] if state["hover"] else c["bg"])
                border = c["border_hover"] if state["hover"] else c["border"]
                button.configure(
                    bg=bg,
                    fg=c["fg"],
                    activebackground=c["pressed"],
                    activeforeground=c["fg"],
                    highlightthickness=0 if tiny else 1,
                    highlightbackground=border,
                    highlightcolor=border,
                    relief="flat",
                    bd=0,
                    cursor="hand2",
                    font=("Segoe UI", 8 if tiny else (9 if compact else 10), "bold"),
                    padx=4 if tiny else (8 if compact else 16),
                    pady=2 if tiny else (4 if compact else 9)
                )

            def on_enter(_event=None):
                state["hover"] = True
                repaint()

            def on_leave(_event=None):
                state["hover"] = False
                state["pressed"] = False
                repaint()

            def on_press(_event=None):
                state["pressed"] = True
                repaint()

            def on_release(_event=None):
                state["pressed"] = False
                repaint()

            button.bind("<Enter>", on_enter, add="+")
            button.bind("<Leave>", on_leave, add="+")
            button.bind("<ButtonPress-1>", on_press, add="+")
            button.bind("<ButtonRelease-1>", on_release, add="+")
            button._refresh_theme = repaint
            interactive_buttons.append(button)
            repaint()

        def style_entry_widget(widget, surface_key="section_frame_bg"):
            state = {"hover": False, "focus": False}

            def repaint():
                theme = get_theme()
                surface = theme.get(surface_key, theme["section_frame_bg"])
                bg = blend(theme["entry_bg"], surface, 0.22 if state["hover"] or state["focus"] else 0.10)
                border = theme["entry_focus"] if state["focus"] else blend(theme["entry_border"], theme["entry_focus"], 0.24 if state["hover"] else 0.08)
                widget.configure(
                    bg=bg,
                    fg=theme["entry_fg"],
                    insertbackground=theme["entry_insert"],
                    selectbackground=blend(theme["section_accent"], theme["entry_bg"], 0.34),
                    selectforeground=theme["entry_fg"],
                    highlightthickness=1,
                    highlightbackground=border,
                    highlightcolor=theme["entry_focus"],
                    relief="flat",
                    bd=0,
                    font=("Segoe UI", 10)
                )

            def on_enter(_event=None):
                state["hover"] = True
                repaint()

            def on_leave(_event=None):
                state["hover"] = False
                repaint()

            def on_focus_in(_event=None):
                state["focus"] = True
                repaint()

            def on_focus_out(_event=None):
                state["focus"] = False
                repaint()

            widget.bind("<Enter>", on_enter, add="+")
            widget.bind("<Leave>", on_leave, add="+")
            widget.bind("<FocusIn>", on_focus_in, add="+")
            widget.bind("<FocusOut>", on_focus_out, add="+")
            widget._refresh_theme = repaint
            themed_entries.append(widget)
            repaint()

        def style_toggle_control(widget, popup=False):
            state = {"hover": False}

            def is_selected():
                try:
                    variable_name = str(widget.cget("variable"))
                    current_value = str(widget.getvar(variable_name))
                    if isinstance(widget, tk.Radiobutton):
                        return current_value == str(widget.cget("value"))
                    return current_value == str(widget.cget("onvalue"))
                except:
                    return False

            def refresh_all():
                root.after(50, lambda: [getattr(item, "_refresh_theme", lambda: None)() for item in list(themed_toggle_widgets) if getattr(item, "winfo_exists", lambda: False)()])

            def repaint():
                theme = get_theme()
                base_bg = theme["popup_bg"] if popup else widget.master.cget("bg")
                selected = is_selected()
                bg = blend(theme["button_body"], base_bg, 0.18) if selected else blend(theme["entry_bg"], base_bg, 0.14 if state["hover"] else 0.07)
                fg = theme["popup_title_fg"] if popup and selected else (theme["section_title_fg"] if selected else (theme["popup_text_fg"] if popup else theme["label_fg"]))
                border = theme["button_outline_hover"] if selected else blend(theme["entry_border"], theme["entry_focus"], 0.16 if state["hover"] else 0.06)
                widget.configure(
                    bg=bg,
                    fg=fg,
                    activebackground=bg,
                    activeforeground=fg,
                    selectcolor=bg,
                    highlightthickness=1,
                    highlightbackground=border,
                    highlightcolor=border,
                    bd=0,
                    relief="flat",
                    indicatoron=False,
                    cursor="hand2",
                    padx=14,
                    pady=6,
                    font=("Segoe UI", 9, "bold")
                )

            def on_enter(_event=None):
                state["hover"] = True
                repaint()

            def on_leave(_event=None):
                state["hover"] = False
                repaint()

            widget.bind("<Enter>", on_enter, add="+")
            widget.bind("<Leave>", on_leave, add="+")
            widget.bind("<ButtonRelease-1>", lambda _event: refresh_all(), add="+")
            widget.bind("<KeyRelease>", lambda _event: refresh_all(), add="+")
            widget._refresh_theme = repaint
            themed_toggle_widgets.append(widget)
            repaint()

        def create_slider_toggle(parent, variable, command=None, width=72, height=36):
            canvas = tk.Canvas(
                parent,
                width=width,
                height=height,
                bg=parent.cget("bg"),
                highlightthickness=0,
                bd=0,
                relief="flat",
                cursor="hand2"
            )

            state = {
                "hover": False,
                "pressed": False,
                "position": 1.0 if bool(variable.get()) else 0.0,
                "target": 1.0 if bool(variable.get()) else 0.0,
                "job": None
            }

            def is_on():
                try:
                    return bool(variable.get())
                except:
                    return False

            def repaint():
                if not canvas.winfo_exists():
                    return
                theme = get_theme()
                canvas.delete("all")
                canvas.configure(bg=parent.cget("bg"))

                on = is_on()
                hover = state["hover"]
                pressed = state["pressed"]
                track_fill = theme["button_body_hover"] if on else blend(theme["entry_bg"], theme["section_frame_bg"], 0.10)
                if hover:
                    track_fill = blend(track_fill, theme["button_outline_hover"], 0.14 if on else 0.07)
                if pressed:
                    track_fill = blend(track_fill, theme["window_bg"], 0.08)
                track_outline = theme["button_outline"] if on else blend(theme["entry_border"], theme["section_border"], 0.24)
                glow_fill = blend(theme["button_glow"], track_fill, 0.18 if on else 0.08)

                draw_rounded_rect(canvas, 4, 6, width - 4, height - 6, (height - 12) / 2, fill=glow_fill, outline="")
                draw_rounded_rect(canvas, 2, 4, width - 2, height - 4, (height - 8) / 2, fill=track_fill, outline=track_outline, width=1)

                inset = 6
                knob_size = height - (inset * 2)
                travel = max(0, width - (inset * 2) - knob_size)
                knob_x = inset + (travel * state["position"])
                knob_fill = theme["button_label"]
                knob_outline = blend(theme["button_outline_hover"], theme["window_bg"], 0.18 if on else 0.30)
                if hover:
                    knob_fill = blend(knob_fill, theme["button_outline_hover"], 0.10)

                if not on:
                    canvas.create_line(18, height / 2, 28, height / 2, fill=theme["secondary_fg"], width=2, capstyle=tk.ROUND)
                else:
                    canvas.create_line(width - 28, (height / 2) + 1, width - 23, (height / 2) + 6, fill=theme["button_label"], width=2, capstyle=tk.ROUND)
                    canvas.create_line(width - 23, (height / 2) + 6, width - 15, (height / 2) - 4, fill=theme["button_label"], width=2, capstyle=tk.ROUND)

                canvas.create_oval(
                    knob_x,
                    inset,
                    knob_x + knob_size,
                    inset + knob_size,
                    fill=knob_fill,
                    outline=knob_outline,
                    width=1
                )
                canvas.create_oval(
                    knob_x + 4,
                    inset + 4,
                    knob_x + knob_size - 8,
                    inset + knob_size - 8,
                    fill=blend(theme["button_label"], track_fill, 0.22),
                    outline=""
                )

            def animate_step():
                if not canvas.winfo_exists():
                    state["job"] = None
                    return
                diff = state["target"] - state["position"]
                if abs(diff) < 0.02:
                    state["position"] = state["target"]
                    state["job"] = None
                    repaint()
                    return
                state["position"] += diff * 0.30
                repaint()
                state["job"] = root.after(16, animate_step)

            def sync_state(animated=True):
                state["target"] = 1.0 if is_on() else 0.0
                if not animated:
                    state["position"] = state["target"]
                    repaint()
                    return
                if state["job"] is None:
                    animate_step()

            def on_enter(_event=None):
                state["hover"] = True
                repaint()

            def on_leave(_event=None):
                state["hover"] = False
                state["pressed"] = False
                repaint()

            def on_press(_event=None):
                state["pressed"] = True
                repaint()

            def on_release(_event=None):
                was_pressed = state["pressed"]
                state["pressed"] = False
                repaint()
                if not was_pressed:
                    return
                try:
                    variable.set(not is_on())
                except:
                    return
                sync_state(True)
                if command:
                    root.after(90, command)

            canvas.bind("<Enter>", on_enter)
            canvas.bind("<Leave>", on_leave)
            canvas.bind("<ButtonPress-1>", on_press)
            canvas.bind("<ButtonRelease-1>", on_release)
            canvas._refresh_theme = lambda: sync_state(False)
            themed_soft_buttons.append(canvas)
            sync_state(False)
            return canvas

        def style_text_widget(widget):
            state = {"hover": False, "focus": False}

            def repaint():
                theme = get_theme()
                border = theme["entry_focus"] if state["focus"] else blend(theme["log_border"], theme["entry_focus"], 0.16 if state["hover"] else 0.06)
                widget.configure(
                    bg=theme["log_bg"],
                    fg=theme["log_fg"],
                    insertbackground=theme["entry_insert"],
                    selectbackground=theme["log_select_bg"],
                    selectforeground=theme["log_fg"],
                    highlightthickness=1,
                    highlightbackground=border,
                    highlightcolor=theme["entry_focus"],
                    relief="flat",
                    bd=0
                )

            def sync_visual_state(_event=None):
                state["focus"] = bool(widget.focus_displayof() == widget)
                repaint()

            def on_enter(_event=None):
                state["hover"] = True
                repaint()

            def on_leave(_event=None):
                state["hover"] = False
                repaint()

            def on_focus_in(_event=None):
                state["focus"] = True
                repaint()

            def on_focus_out(_event=None):
                state["focus"] = False
                repaint()

            widget.bind("<Enter>", on_enter, add="+")
            widget.bind("<Leave>", on_leave, add="+")
            widget.bind("<FocusIn>", on_focus_in, add="+")
            widget.bind("<FocusOut>", on_focus_out, add="+")
            widget.bind("<ButtonPress-1>", sync_visual_state, add="+")
            widget.bind("<ButtonRelease-1>", lambda _event=None: widget.after_idle(sync_visual_state), add="+")
            widget.bind("<KeyRelease>", lambda _event=None: widget.after_idle(sync_visual_state), add="+")
            widget.bind("<<Selection>>", lambda _event=None: widget.after_idle(sync_visual_state), add="+")
            widget._refresh_theme = repaint
            themed_text_views.append(widget)
            repaint()

        def style_listbox_widget(widget):

            state = {"hover": False, "focus": False, "right_click": False, "double_click": False}


            def repaint():
                theme = get_theme()
                # Border color logic
                border = theme["entry_focus"] if state["focus"] else blend(theme["log_border"], theme["entry_focus"], 0.16 if state["hover"] else 0.06)
                # Right-click highlight mod
                bg = theme["log_bg"]
                if state["right_click"]:
                    bg = blend(theme["log_bg"], theme["entry_focus"], 0.18)
                # Double-click animation mod
                if state["double_click"]:
                    bg = blend(bg, "#FFD700", 0.25)  # Gold highlight
                widget.configure(
                    bg=bg,
                    fg=theme["log_fg"],
                    highlightthickness=1,
                    highlightbackground=border,
                    highlightcolor=theme["entry_focus"],
                    selectbackground=theme["log_select_bg"],
                    selectforeground=theme["log_fg"],
                    activestyle="none",
                    exportselection=False,
                    relief="flat",
                    bd=0
                )


            def sync_visual_state(_event=None):
                state["focus"] = bool(widget.focus_displayof() == widget)
                repaint()

            def on_right_click(event=None):
                state["right_click"] = True
                repaint()
                widget.after(200, clear_right_click)

            def clear_right_click():
                state["right_click"] = False
                repaint()

            def on_double_click(event=None):
                state["double_click"] = True
                repaint()
                widget.after(300, clear_double_click)

            def clear_double_click():
                state["double_click"] = False
                repaint()


            def on_enter(_event=None):
                state["hover"] = True
                repaint()

            def on_leave(_event=None):
                state["hover"] = False
                repaint()

            def on_focus_in(_event=None):
                state["focus"] = True
                repaint()

            def on_focus_out(_event=None):
                state["focus"] = False
                repaint()

            widget.bind("<Enter>", on_enter, add="+")
            widget.bind("<Leave>", on_leave, add="+")
            widget.bind("<FocusIn>", on_focus_in, add="+")
            widget.bind("<FocusOut>", on_focus_out, add="+")
            widget.bind("<ButtonPress-1>", sync_visual_state, add="+")
            widget.bind("<ButtonRelease-1>", lambda _event=None: widget.after_idle(sync_visual_state), add="+")
            widget.bind("<KeyRelease>", lambda _event=None: widget.after_idle(sync_visual_state), add="+")
            widget.bind("<<ListboxSelect>>", lambda _event=None: widget.after_idle(sync_visual_state), add="+")
            # Right-click mod
            widget.bind("<Button-3>", on_right_click, add="+")
            # Double-click mod
            widget.bind("<Double-Button-1>", on_double_click, add="+")
            widget._refresh_theme = repaint
            themed_listboxes.append(widget)
            repaint()

        def on_configure_debounced(event=None):
            nonlocal pending_redraw
            if pending_redraw is not None:
                root.after_cancel(pending_redraw)
            pending_redraw = root.after(200, draw_background)

        root.bind("<Configure>", on_configure_debounced)
        draw_background()
        animate_background()
        fade_in_window()

        card_shell = tk.Frame(content, bg=get_theme()["window_bg"], bd=0, highlightthickness=0)
        card_shell.pack(fill="both", expand=True, padx=18, pady=18)

        card_shadow = tk.Frame(card_shell, bg=blend(get_theme().get("panel_shadow", get_theme()["button_shadow"]), get_theme()["window_bg"], 0.20), bd=0, highlightthickness=0)
        card_shadow.pack(fill="both", expand=True, padx=(10, 0), pady=(12, 0))

        card = tk.Frame(card_shell, bg=get_theme()["card_bg"], bd=0, highlightthickness=1, highlightbackground=get_theme()["card_border"])
        card.place(x=0, y=0, relwidth=1, relheight=1, width=-10, height=-12)

        current_tab = tk.StringVar(value="autoclicker")
        tab_buttons = {}
        sections = []
        settings_visible = False

        sidebar = tk.Frame(card, bg=get_theme().get("sidebar_bg", get_theme()["tab_wrap_bg"]), width=224)
        sidebar.pack(side="left", fill="y")
        sidebar.pack_propagate(False)

        tab_divider = tk.Frame(card, bg=blend(get_theme().get("sidebar_border", get_theme()["divider_bg"]), get_theme()["window_bg"], 0.40), width=1)
        tab_divider.pack(side="left", fill="y", pady=18)

        workspace = tk.Frame(card, bg=get_theme()["card_bg"])
        workspace.pack(side="left", fill="both", expand=True)

        tab_bar_wrap = tk.Frame(sidebar, bg=get_theme().get("sidebar_bg", get_theme()["tab_wrap_bg"]))
        tab_bar_wrap.pack(fill="both", expand=True, padx=18, pady=20)

        sidebar_brand = tk.Frame(tab_bar_wrap, bg=get_theme().get("sidebar_bg", get_theme()["tab_wrap_bg"]))
        sidebar_brand.pack(fill="x", pady=(0, 16))

        sidebar_brand_top = tk.Frame(sidebar_brand, bg=get_theme().get("sidebar_bg", get_theme()["tab_wrap_bg"]))
        sidebar_brand_top.pack(fill="x")

        sidebar_brand_copy = tk.Frame(sidebar_brand, bg=get_theme().get("sidebar_bg", get_theme()["tab_wrap_bg"]))
        sidebar_brand_copy.pack(fill="x", pady=(12, 0))

        sidebar_badge = tk.Label(
            sidebar_brand_top,
            text="ZHYDRA",
            font=("Segoe UI", 8, "bold"),
            padx=10,
            pady=5,
            bd=0,
            relief="flat",
            highlightthickness=1
        )
        sidebar_badge.pack(side="left", anchor="w")

        width_shrink_button = tk.Button(
            sidebar_brand_top,
            text="◀",
            font=("Segoe UI", 8, "bold"),
            bd=0,
            relief="flat",
            cursor="hand2",
            command=toggle_width_compact,
            width=1,
            height=1
        )
        style_modern_button(width_shrink_button, "subtle", compact=True, tiny=True)
        width_shrink_button.pack(side="right", anchor="ne")

        sidebar_title = tk.Label(
            sidebar_brand_copy,
            text="Control Hub",
            font=("Segoe UI", 16, "bold"),
            anchor="w",
            justify="left"
        )
        sidebar_title.pack(fill="x")

        sidebar_subtitle = tk.Label(
            sidebar_brand_copy,
            text="A premium desktop workspace for precision clicking, macros, and live telemetry.",
            font=("Segoe UI", 9),
            justify="left",
            anchor="w",
            wraplength=198
        )
        sidebar_subtitle.pack(fill="x", pady=(8, 0))

        sidebar_section_label = tk.Label(
            tab_bar_wrap,
            text="WORKSPACE",
            font=("Segoe UI", 8, "bold"),
            anchor="w",
            justify="left"
        )
        sidebar_section_label.pack(fill="x", pady=(0, 8))

        tab_bar = tk.Frame(tab_bar_wrap, bg=get_theme().get("sidebar_bg", get_theme()["tab_wrap_bg"]))
        tab_bar.pack(fill="x", pady=(0, 0))

        tab_indicator = tk.Frame(tab_bar, width=4, bd=0)

        sidebar_footer = tk.Frame(tab_bar_wrap, bg=get_theme().get("sidebar_bg", get_theme()["tab_wrap_bg"]))
        sidebar_footer.pack(side="bottom", fill="x")

        sidebar_footer_label = tk.Label(
            sidebar_footer,
            text="Theme, advanced controls, and workspace preferences live here.",
            font=("Segoe UI", 9),
            justify="left",
            anchor="w",
            wraplength=192
        )
        sidebar_footer_label.pack(fill="x", pady=(0, 12))

        header = tk.Frame(workspace, bg=get_theme()["card_bg"])
        header.pack(fill="x", padx=24, pady=(22, 8))
        header.grid_columnconfigure(0, weight=1)
        header.grid_columnconfigure(1, weight=0)

        hero_copy = tk.Frame(header, bd=0, highlightthickness=1, padx=24, pady=20)
        hero_copy.grid(row=0, column=0, sticky="nsew", padx=(0, 14))

        header_badge = tk.Label(
            hero_copy,
            text="AUTOMATION",
            font=("Segoe UI", 8, "bold"),
            padx=10,
            pady=5,
            bd=0,
            relief="flat",
            highlightthickness=1
        )
        header_badge.pack(anchor="w", pady=(0, 12))

        title = tk.Label(
            hero_copy,
            text="Zhydra",
            font=("Segoe UI", 26, "bold"),
            fg=get_theme()["title_fg"],
            bg=get_theme()["card_bg"],
            anchor="w"
        )
        title.pack(anchor="w")

        subtitle = tk.Label(
            hero_copy,
            text="Precision automation, macros, and live telemetry.",
            font=("Segoe UI", 10),
            fg=get_theme()["subtitle_fg"],
            bg=get_theme()["card_bg"],
            anchor="w",
            justify="left"
        )
        subtitle.pack(anchor="w", pady=(6, 0))

        hero_caption = tk.Label(
            hero_copy,
            text="A redesigned control surface with immersive motion, sharper hierarchy, and faster access to every tool.",
            font=("Segoe UI", 9),
            justify="left",
            anchor="w",
            wraplength=600
        )
        hero_caption.pack(anchor="w", pady=(12, 0))

        hero_rule = tk.Frame(
            hero_copy,
            height=2,
            bg=blend(get_theme()["section_accent"], get_theme()["card_bg"], 0.22)
        )
        hero_rule.pack(fill="x", pady=(14, 0))

        status_panel = tk.Frame(header, bd=0, highlightthickness=1, padx=20, pady=18)
        status_panel.grid(row=0, column=1, sticky="nsew")

        status_collapsed = False

        sidebar_collapsed = False
        sidebar_saved_geometry = None

        status_header = tk.Frame(status_panel, bg=get_theme()["card_bg"])
        status_header.pack(fill="x")

        status_panel_title = tk.Label(
            status_header,
            text="Live Telemetry",
            font=("Segoe UI", 10, "bold"),
            anchor="w"
        )
        status_panel_title.pack(side="left", anchor="w")

        def toggle_sidebar():
            nonlocal sidebar_collapsed, sidebar_saved_geometry
            sidebar_collapsed = not sidebar_collapsed
            workspace.pack_forget()
            if sidebar_collapsed:
                sidebar_saved_geometry = sidebar_saved_geometry or root.geometry()
                sidebar.pack_forget()
                tab_divider.pack_forget()
                sidebar_toggle_button.configure(text="▶")
                workspace.pack(side="left", fill="both", expand=True)
                root.update_idletasks()
                width = max(980, root.winfo_width() - 224)
                height = root.winfo_height()
                root.geometry(f"{width}x{height}")
            else:
                sidebar_toggle_button.configure(text="◀")
                sidebar.pack(side="left", fill="y")
                tab_divider.pack(side="left", fill="y", pady=18)
                workspace.pack(side="left", fill="both", expand=True)
                if sidebar_saved_geometry:
                    root.geometry(sidebar_saved_geometry)
                    sidebar_saved_geometry = None

        sidebar_toggle_button = tk.Button(
            status_header,
            text="◀",
            font=("Segoe UI", 8, "bold"),
            bd=0,
            relief="flat",
            cursor="hand2",
            command=toggle_sidebar,
            width=1,
            height=1
        )
        style_modern_button(sidebar_toggle_button, "subtle", compact=True, tiny=True)
        sidebar_toggle_button.pack(side="right", padx=(0, 4))

        def toggle_status_panel():
            nonlocal status_collapsed
            status_collapsed = not status_collapsed
            if status_collapsed:
                status_grid.pack_forget()
                status_toggle_button.configure(text="▼")
            else:
                status_grid.pack(fill="x", pady=(14, 0))
                status_toggle_button.configure(text="▲")

        status_toggle_button = tk.Button(
            status_header,
            text="▲",
            font=("Segoe UI", 8, "bold"),
            bd=0,
            relief="flat",
            cursor="hand2",
            command=toggle_status_panel,
            width=1,
            height=1
        )
        style_modern_button(status_toggle_button, "subtle", compact=True, tiny=True)
        status_toggle_button.pack(side="right")

        status_grid = tk.Frame(status_panel, bd=0)
        status_grid.pack(fill="x", pady=(12, 0))
        status_grid.grid_columnconfigure(0, weight=1)
        status_grid.grid_columnconfigure(1, weight=1)
        status_grid.grid_columnconfigure(2, weight=1)
        status_grid.grid_columnconfigure(3, weight=1)

        status_cards = {}

        def create_status_card(parent, key, title_text, row, column):
            theme = get_theme()
            shadow = tk.Frame(parent, bd=0, highlightthickness=0, bg=blend(theme.get("panel_shadow", theme["button_shadow"]), theme["window_bg"], 0.30))
            shadow.grid(row=row, column=column, sticky="nsew", padx=5, pady=5)

            card_shell = tk.Frame(shadow, bd=0, highlightthickness=1, padx=13, pady=11)
            card_shell.pack(fill="both", expand=True, padx=(0, 8), pady=(0, 8))

            accent = tk.Frame(card_shell, height=3, width=42, bd=0)
            accent.pack(anchor="w")

            body = tk.Frame(card_shell, bd=0)
            body.pack(fill="both", expand=True, pady=(8, 0))

            title_label = tk.Label(
                body,
                text=title_text,
                font=("Segoe UI", 8, "bold"),
                anchor="w"
            )
            title_label.pack(anchor="w")

            value_label = tk.Label(
                body,
                text="—",
                font=("Segoe UI", 16, "bold"),
                anchor="w"
            )
            value_label.pack(anchor="w", pady=(4, 1))

            detail_label = tk.Label(
                body,
                text="",
                font=("Segoe UI", 8),
                anchor="w"
            )
            detail_label.pack(anchor="w")

            status_cards[key] = {
                "shadow": shadow,
                "shell": card_shell,
                "accent": accent,
                "body": body,
                "title": title_label,
                "value": value_label,
                "detail": detail_label
            }

        create_status_card(status_grid, "state", "STATUS", 0, 0)
        create_status_card(status_grid, "clicks", "CLICKS", 0, 1)
        create_status_card(status_grid, "profile", "PROFILE", 0, 2)
        create_status_card(status_grid, "rate", "RATE", 0, 3)

        settings_button = create_soft_button(sidebar_footer, "Interface Settings", lambda: toggle_settings_panel(), width=188)
        settings_button.pack(fill="x")

        pages_container = tk.Frame(workspace, bg=get_theme()["card_bg"])
        pages_container.pack(fill="both", expand=True)

        pages_canvas = tk.Canvas(
            pages_container,
            bg=get_theme()["card_bg"],
            highlightthickness=0,
            bd=0,
            relief="flat"
        )
        pages_canvas.pack(side="left", fill="both", expand=True)

        pages_scrollbar = ttk.Scrollbar(pages_container, orient="vertical", command=pages_canvas.yview, style="Clean.Vertical.TScrollbar")
        pages_scrollbar.pack(side="right", fill="y")
        pages_canvas.configure(yscrollcommand=pages_scrollbar.set)

        pages_view = tk.Frame(pages_canvas, bg=get_theme()["card_bg"])
        pages_window = pages_canvas.create_window((0, 0), window=pages_view, anchor="nw")

        toast_host = tk.Frame(content, bg=content.cget("bg"), bd=0, highlightthickness=0)
        toast_host.place(relx=1.0, rely=1.0, x=34, y=-24, anchor="se")

        toast_card = tk.Frame(toast_host, bd=0, highlightthickness=1)
        toast_card.pack(fill="both", expand=True)

        resize_handle_host = tk.Frame(content, bg=content.cget("bg"), bd=0, highlightthickness=0)
        resize_handle_host.place(relx=1.0, rely=1.0, x=-12, y=-12, anchor="se")

        height_shrink_button = tk.Button(
            resize_handle_host,
            text="▼",
            font=("Segoe UI", 8, "bold"),
            bd=0,
            relief="flat",
            cursor="hand2",
            command=toggle_height_compact,
            width=1,
            height=1
        )
        style_modern_button(height_shrink_button, "subtle", compact=True, tiny=True)
        height_shrink_button.pack()

        toast_accent = tk.Frame(toast_card, width=4, bd=0)
        toast_accent.pack(side="left", fill="y")

        toast_body = tk.Frame(toast_card, bd=0, padx=13, pady=10)
        toast_body.pack(side="left", fill="both", expand=True)

        toast_title = tk.Label(toast_body, text="Activity", font=("Segoe UI", 9, "bold"), anchor="w", justify="left")
        toast_title.pack(fill="x")

        toast_message = tk.Label(toast_body, text="", font=("Segoe UI", 9), anchor="w", justify="left", wraplength=300)
        toast_message.pack(fill="x", pady=(4, 0))

        toast_state = {
            "progress": 0.0,
            "target": 0.0,
            "job": None,
            "hide_job": None,
            "tone": "info",
            "title": "Activity"
        }

        def toast_palette(tone="info"):
            theme = get_theme()
            base_bg = theme.get("toast_bg", blend(theme["popup_bg"], theme["card_bg"], 0.12))
            if tone == "success":
                accent = theme["success"]
            elif tone == "error":
                accent = theme["error"]
            else:
                accent = theme["section_accent"]
            return {
                "bg": base_bg,
                "border": theme.get("toast_border", blend(theme["popup_border"], accent, 0.18)),
                "accent": accent,
                "title": theme.get("toast_fg", theme["popup_title_fg"]),
                "text": theme["popup_text_fg"]
            }

        def position_toast(progress=None):
            if progress is not None:
                toast_state["progress"] = progress
            x = -28 + int((1.0 - toast_state["progress"]) * 56)
            toast_host.place_configure(x=x, y=-28)
            if toast_state["progress"] <= 0.01:
                toast_host.lower()
            else:
                toast_host.lift()

        def animate_toast():
            diff = toast_state["target"] - toast_state["progress"]
            if abs(diff) < 0.03:
                toast_state["progress"] = toast_state["target"]
                position_toast()
                toast_state["job"] = None
                return
            toast_state["progress"] += diff * 0.30
            position_toast()
            toast_state["job"] = root.after(16, animate_toast)

        def set_toast_target(target):
            toast_state["target"] = max(0.0, min(1.0, target))
            if toast_state["job"] is None:
                animate_toast()

        def hide_toast():
            toast_state["hide_job"] = None
            set_toast_target(0.0)

        def show_toast(message, tone="info", title_text=None):
            palette = toast_palette(tone)
            title_text = title_text or {"success": "Update", "error": "Attention", "info": "Activity"}.get(tone, "Activity")
            toast_state["tone"] = tone
            toast_state["title"] = title_text
            toast_card.configure(bg=palette["bg"], highlightbackground=palette["border"])
            toast_body.configure(bg=palette["bg"])
            toast_accent.configure(bg=palette["accent"])
            toast_title.configure(bg=palette["bg"], fg=palette["title"], text=title_text)
            toast_message.configure(bg=palette["bg"], fg=palette["text"], text=message[:160])
            if toast_state["hide_job"] is not None:
                root.after_cancel(toast_state["hide_job"])
            set_toast_target(1.0)
            toast_state["hide_job"] = root.after(2600, hide_toast)

        position_toast(0.0)

        def refresh_pages_scrollregion(event=None):
            pages_canvas.configure(scrollregion=pages_canvas.bbox("all"))

        def resize_pages_view(event):
            pages_canvas.itemconfigure(pages_window, width=event.width)
            refresh_pages_scrollregion()

        def mousewheel_steps(event):
            if getattr(event, "delta", 0):
                delta = int(-event.delta / 120)
                return delta if delta != 0 else (-1 if event.delta > 0 else 1)
            if getattr(event, "num", None) == 4:
                return -1
            if getattr(event, "num", None) == 5:
                return 1
            return 0

        def on_app_mousewheel(event):
            steps = mousewheel_steps(event)
            if steps:
                pages_canvas.yview_scroll(steps, "units")
                return "break"

        def block_combobox_mousewheel(widget):
            def stop_wheel(_event):
                return "break"

            widget.bind("<MouseWheel>", stop_wheel, add="+")
            widget.bind("<Button-4>", stop_wheel, add="+")
            widget.bind("<Button-5>", stop_wheel, add="+")

        pages_view.bind("<Configure>", refresh_pages_scrollregion)
        pages_canvas.bind("<Configure>", resize_pages_view)

        def style_tab(tab_name, active):
            theme = get_theme()
            button = tab_buttons[tab_name]
            button.configure(
                bg=theme.get("sidebar_active_bg", theme["tab_active_bg"]) if active else theme.get("sidebar_bg", theme["tab_wrap_bg"]),
                fg=theme["tab_active_fg"] if active else theme["tab_inactive_fg"],
                highlightbackground=theme["section_accent"] if active else blend(theme.get("sidebar_border", theme["tab_inactive_border"]), theme.get("sidebar_bg", theme["tab_wrap_bg"]), 0.16),
                highlightcolor=theme["section_accent"] if active else blend(theme.get("sidebar_border", theme["tab_inactive_border"]), theme.get("sidebar_bg", theme["tab_wrap_bg"]), 0.16),
                font=("Segoe UI", 10, "bold")
            )

        tab_indicator_state = {"y": None, "height": None, "job": None}

        def parse_pad_value(value):
            if isinstance(value, tuple):
                if len(value) == 1:
                    return int(value[0]), int(value[0])
                return int(value[0]), int(value[1])
            text = str(value).replace("{", "").replace("}", "").strip()
            if not text:
                return 0, 0
            parts = text.split()
            if len(parts) == 1:
                pad = int(float(parts[0]))
                return pad, pad
            return int(float(parts[0])), int(float(parts[1]))

        def animate_page_reveal(page):
            for index, widget in enumerate([child for child in page.winfo_children() if child.winfo_manager() == "pack"]):
                try:
                    info = widget.pack_info()
                except:
                    continue
                base_pady = getattr(widget, "_base_reveal_pady", None)
                if base_pady is None:
                    base_pady = parse_pad_value(info.get("pady", 0))
                    widget._base_reveal_pady = base_pady
                start_pady = (base_pady[0] + 12 + (index * 3), base_pady[1])
                try:
                    widget.pack_configure(pady=start_pady)
                except:
                    continue

                def step(current=0, target_widget=widget, base=base_pady, start=start_pady):
                    if not target_widget.winfo_exists():
                        return
                    total_steps = 8
                    ratio = (current + 1) / total_steps
                    top = int(round(start[0] + ((base[0] - start[0]) * ratio)))
                    bottom = int(round(start[1] + ((base[1] - start[1]) * ratio)))
                    try:
                        target_widget.pack_configure(pady=(top, bottom))
                    except:
                        return
                    if current + 1 < total_steps:
                        root.after(20, lambda: step(current + 1, target_widget, base, start))

                root.after(index * 34, step)

        def position_tab_indicator(animate=True):
            active_widget = tab_buttons.get(current_tab.get())
            if not active_widget or not active_widget.winfo_ismapped():
                tab_indicator.place_forget()
                return
            tab_bar.update_idletasks()
            target_y = active_widget.winfo_y() + 8
            target_height = max(28, active_widget.winfo_height() - 16)
            if tab_indicator_state["y"] is None or not animate:
                tab_indicator_state["y"] = target_y
                tab_indicator_state["height"] = target_height
                tab_indicator.place(x=2, y=target_y, width=4, height=target_height)
                return

            if tab_indicator_state["job"] is not None:
                try:
                    root.after_cancel(tab_indicator_state["job"])
                except:
                    pass

            def step():
                delta_y = target_y - tab_indicator_state["y"]
                delta_h = target_height - tab_indicator_state["height"]
                if abs(delta_y) < 1 and abs(delta_h) < 1:
                    tab_indicator_state["y"] = target_y
                    tab_indicator_state["height"] = target_height
                    tab_indicator.place(x=2, y=target_y, width=4, height=target_height)
                    tab_indicator_state["job"] = None
                    return
                tab_indicator_state["y"] += delta_y * 0.28
                tab_indicator_state["height"] += delta_h * 0.28
                tab_indicator.place(x=2, y=int(tab_indicator_state["y"]), width=4, height=int(tab_indicator_state["height"]))
                tab_indicator_state["job"] = root.after(16, step)

            step()

        def switch_tab(tab_name):
            current_tab.set(tab_name)
            autoclicker_page.pack_forget()
            macros_page.pack_forget()
            mods_page.pack_forget()
            overview_page.pack_forget()
            profiles_page.pack_forget()
            scheduler_page.pack_forget()
            toolkit_page.pack_forget()
            mouse_page.pack_forget()
            selected_page = overview_page

            if tab_name == "autoclicker":
                autoclicker_page.pack(fill="both", expand=True)
                selected_page = autoclicker_page
            elif tab_name == "macros":
                macros_page.pack(fill="both", expand=True)
                selected_page = macros_page
            elif tab_name == "mouse":
                mouse_page.pack(fill="both", expand=True)
                selected_page = mouse_page
            elif tab_name == "mods":
                mods_page.pack(fill="both", expand=True)
                selected_page = mods_page
            elif tab_name == "profiles":
                profiles_page.pack(fill="both", expand=True)
                selected_page = profiles_page
            elif tab_name == "scheduler":
                scheduler_page.pack(fill="both", expand=True)
                selected_page = scheduler_page
            elif tab_name == "toolkit":
                toolkit_page.pack(fill="both", expand=True)
                selected_page = toolkit_page
            else:
                overview_page.pack(fill="both", expand=True)
                selected_page = overview_page

            pages_canvas.yview_moveto(0)
            root.after_idle(refresh_pages_scrollregion)
            root.after_idle(lambda page=selected_page: animate_page_reveal(page))

            for name in tab_buttons:
                style_tab(name, name == tab_name)
            root.after_idle(lambda: position_tab_indicator(True))

        def create_tab(tab_name, title):
            theme = get_theme()
            tab = tk.Label(
                tab_bar,
                text=title,
                font=("Segoe UI", 10, "bold"),
                bg=theme.get("sidebar_bg", theme["tab_inactive_bg"]),
                fg=theme["tab_inactive_fg"],
                padx=16,
                pady=10,
                anchor="w",
                justify="left",
                cursor="hand2",
                bd=0,
                relief="flat",
                highlightthickness=1,
                highlightbackground=theme["tab_inactive_border"],
                highlightcolor=theme["tab_inactive_border"]
            )
            tab.pack(side="top", fill="x", padx=(10, 6), pady=3, anchor="w")
            tab.bind("<Button-1>", lambda e, name=tab_name: switch_tab(name))
            tab.bind(
                "<Enter>",
                lambda e, name=tab_name, widget=tab: current_tab.get() != name and widget.configure(
                    bg=get_theme().get("sidebar_hover_bg", blend(get_theme()["tab_hover_bg"], get_theme()["tab_wrap_bg"], 0.18)),
                    fg=get_theme()["tab_hover_fg"],
                    highlightbackground=get_theme()["tab_hover_border"],
                    highlightcolor=get_theme()["tab_hover_border"],
                    font=("Segoe UI", 10, "bold")
                )
            )
            tab.bind("<Leave>", lambda e, name=tab_name: style_tab(name, current_tab.get() == name))
            tab_buttons[tab_name] = tab

        create_tab("autoclicker", "Autoclicker")
        create_tab("macros", "Macros")
        create_tab("mouse", "Mouse")
        create_tab("mods", "Mods")
        create_tab("overview", "Overview")
        create_tab("profiles", "Profiles")
        create_tab("scheduler", "Scheduler")
        create_tab("toolkit", "Utility")
        tab_bar_wrap.bind("<Configure>", lambda _event: root.after_idle(position_tab_indicator), add="+")
        tab_bar.bind("<Configure>", lambda _event: root.after_idle(position_tab_indicator), add="+")

        def section(name, parent, expand=False):
            theme = get_theme()
            shadow = tk.Frame(
                parent,
                bg=blend(theme.get("panel_shadow", theme["button_shadow"]), theme["window_bg"], 0.18),
                bd=0,
                highlightthickness=0
            )
            shadow.pack(fill="both" if expand else "x", expand=expand, padx=24, pady=10)

            shell = tk.Frame(
                shadow,
                bg=blend(theme["section_shell_bg"], theme["card_bg"], 0.06),
                bd=0,
                highlightthickness=1,
                highlightbackground=blend(theme["section_border"], theme["section_accent"], 0.25)
            )
            shell.pack(fill="both", expand=True, padx=(0, 6), pady=(0, 6))

            accent = tk.Frame(shell, bg=theme["section_accent"], height=2)
            accent.pack(fill="x", side="top")

            title_bar = tk.Frame(
                shell,
                bg=blend(theme["section_title_bar_bg"], theme["section_frame_bg"], 0.10)
            )
            title_bar.pack(fill="x")

            title_label = tk.Label(
                title_bar,
                text=name,
                bg=title_bar.cget("bg"),
                fg=theme["section_title_fg"],
                font=("Segoe UI", 11, "bold")
            )
            title_label.pack(anchor="w", padx=18, pady=(11, 8))

            frame = tk.Frame(
                shell,
                bg=blend(theme["section_frame_bg"], theme["card_bg"], 0.06),
                padx=20, pady=16
            )
            frame.pack(fill="both", expand=True, padx=14, pady=(0, 14))
            sections.append({
                "shadow": shadow,
                "shell": shell,
                "accent": accent,
                "title_bar": title_bar,
                "title_label": title_label,
                "frame": frame
            })
            return frame

        autoclicker_page = tk.Frame(pages_view, bg=get_theme()["card_bg"])
        macros_page = tk.Frame(pages_view, bg=get_theme()["card_bg"])
        mods_page = tk.Frame(pages_view, bg=get_theme()["card_bg"])
        overview_page = tk.Frame(pages_view, bg=get_theme()["card_bg"])
        profiles_page = tk.Frame(pages_view, bg=get_theme()["card_bg"])
        scheduler_page = tk.Frame(pages_view, bg=get_theme()["card_bg"])
        toolkit_page = tk.Frame(pages_view, bg=get_theme()["card_bg"])
        mouse_page = tk.Frame(pages_view, bg=get_theme()["card_bg"])
        mods_mods_page = tk.Frame(pages_view, bg=get_theme()["card_bg"])
        macro_panels = []

        ac_frame = section("Autoclicker Settings", autoclicker_page)
        ac_frame.grid_columnconfigure(1, weight=1)

        # ------------------ Inputs ------------------
        def only_nums(v):
            if v == "":
                return True
            try:
                float(v)
                return True
            except:
                return False

        vcmd = (root.register(only_nums), "%P")

        # CPS
        label_style = {"bg": get_theme()["section_frame_bg"], "fg": get_theme()["label_fg"], "font": ("Segoe UI", 10)}
        entry_style = {
            "width": 12,
            "bg": get_theme()["entry_bg"],
            "fg": get_theme()["entry_fg"],
            "insertbackground": get_theme()["entry_insert"],
            "validate": "key",
            "validatecommand": vcmd,
            "bd": 0,
            "highlightthickness": 1,
            "highlightbackground": get_theme()["entry_border"],
            "highlightcolor": get_theme()["entry_focus"],
            "font": ("Segoe UI", 10),
            "relief": "flat"
        }

        cps_label = tk.Label(ac_frame, text="CPS:", **label_style)
        cps_label.grid(row=0, column=0, sticky="w", pady=(0, 8))
        cps_entry = tk.Entry(ac_frame,
                             insertbackground=get_theme()["entry_insert"], validate="key",
                             validatecommand=vcmd, bd=0)
        cps_entry.configure(**entry_style)
        style_entry_widget(cps_entry)
        cps_entry.grid(row=0, column=1, padx=(8, 0), pady=(0, 8), sticky="ew")
        cps_entry.insert(0, cps)

        # Cycle duty
        cycle_label = tk.Label(ac_frame, text="Cycle Duty %:", **label_style)
        cycle_label.grid(row=1, column=0, sticky="w", pady=(0, 8))
        cycle_entry = tk.Entry(ac_frame)
        cycle_entry.configure(**entry_style)
        style_entry_widget(cycle_entry)
        cycle_entry.grid(row=1, column=1, padx=(8, 0), pady=(0, 8), sticky="ew")
        cycle_entry.insert(0, cycle_duty)

        # CPS jitter
        jitter_label = tk.Label(ac_frame, text="CPS Jitter %:", **label_style)
        jitter_label.grid(row=2, column=0, sticky="w", pady=(0, 8))
        jitter_entry = tk.Entry(ac_frame)
        jitter_entry.configure(**entry_style)
        style_entry_widget(jitter_entry)
        jitter_entry.grid(row=2, column=1, padx=(8, 0), pady=(0, 8), sticky="ew")
        jitter_entry.insert(0, cps_jitter)

        # Mode
        mode_label = tk.Label(ac_frame, text="Mode:", **label_style)
        mode_label.grid(row=3, column=0, sticky="w", pady=(0, 8))
        mode_var = tk.StringVar(value=mode)
        mode_menu = ttk.Combobox(ac_frame, textvariable=mode_var,
                                 values=["Hold", "Toggle"], state="readonly", width=12,
                                 style="Clean.TCombobox")
        mode_menu.grid(row=3, column=1, padx=(8, 0), pady=(0, 8), sticky="ew")
        block_combobox_mousewheel(mode_menu)

        # Click button
        click_button_label = tk.Label(ac_frame, text="Click Button:", **label_style)
        click_button_label.grid(row=4, column=0, sticky="w", pady=(0, 8))
        click_button_var = tk.StringVar(value=click_button_name)
        click_button_menu = ttk.Combobox(
            ac_frame,
            textvariable=click_button_var,
            values=["Left", "Right", "Middle"],
            state="readonly",
            width=12,
            style="Clean.TCombobox"
        )
        click_button_menu.grid(row=4, column=1, padx=(8, 0), pady=(0, 8), sticky="ew")
        block_combobox_mousewheel(click_button_menu)

        # Click count
        click_repeat_label = tk.Label(ac_frame, text="Click Count:", **label_style)
        click_repeat_label.grid(row=5, column=0, sticky="w", pady=(0, 8))
        click_repeat_var = tk.StringVar(value=click_repeat_name)
        click_repeat_menu = ttk.Combobox(
            ac_frame,
            textvariable=click_repeat_var,
            values=["Single", "Double", "Triple"],
            state="readonly",
            width=12,
            style="Clean.TCombobox"
        )
        click_repeat_menu.grid(row=5, column=1, padx=(8, 0), pady=(0, 8), sticky="ew")
        block_combobox_mousewheel(click_repeat_menu)

        def update_advanced_settings_visibility():
            if advanced_settings_enabled:
                jitter_label.grid()
                jitter_entry.grid()
                click_repeat_label.grid()
                click_repeat_menu.grid()
            else:
                jitter_label.grid_remove()
                jitter_entry.grid_remove()
                click_repeat_label.grid_remove()
                click_repeat_menu.grid_remove()

        # Keybind
        key_label = tk.Label(ac_frame, text="No keybind set", bg=get_theme()["section_frame_bg"], fg=get_theme()["secondary_fg"], font=("Segoe UI", 10))
        key_label.grid(row=6, column=0, columnspan=2, pady=(6, 4), sticky="w")

        def set_bind():
            nonlocal setting_keybind
            setting_keybind = True
            key_label.config(text="Press a key or mouse button...")

        def clear_bind():
            nonlocal toggle_key, setting_keybind
            setting_keybind = False
            toggle_key = None
            key_label.config(text=format_keybind_text(toggle_key))
            save_settings()
            log("Keybind cleared")

        bind_actions = tk.Frame(ac_frame, bg=get_theme()["section_frame_bg"])
        bind_actions.grid(row=7, column=0, columnspan=2, pady=(6, 2), sticky="ew")
        bind_actions.grid_columnconfigure(0, weight=1)
        bind_actions.grid_columnconfigure(1, weight=1)

        set_bind_button = create_soft_button(bind_actions, "Set Keybind", set_bind, width=146)
        set_bind_button.grid(row=0, column=0, padx=(0, 8), sticky="w")

        clear_bind_button = create_soft_button(bind_actions, "Clear Keybind", clear_bind, width=146)
        clear_bind_button.grid(row=0, column=1, sticky="e")

        # Auto apply
        def apply(e=None):
            nonlocal cps, mode, cycle_duty, cps_jitter, click_button_name, click_repeat_name
            old_cps = cps
            old_mode = mode
            old_cycle_duty = cycle_duty
            old_cps_jitter = cps_jitter
            old_click_button = click_button_name
            old_click_repeat = click_repeat_name

            new_cps = parse_cps(cps_entry.get(), cps)

            new_mode = mode_var.get()

            try:
                new_cycle_duty = min(100, max(0.1, float(cycle_entry.get())))
            except:
                new_cycle_duty = 100

            try:
                new_cps_jitter = min(100, max(0.0, float(jitter_entry.get())))
            except:
                new_cps_jitter = 0.0

            new_click_button = click_button_var.get() if click_button_var.get() in {"Left", "Right", "Middle"} else "Left"
            new_click_repeat = click_repeat_var.get() if click_repeat_var.get() in {"Single", "Double", "Triple"} else "Single"

            cps = new_cps
            mode = new_mode
            cycle_duty = new_cycle_duty
            cps_jitter = new_cps_jitter
            click_button_name = new_click_button
            click_repeat_name = new_click_repeat

            if old_mode != mode:
                log(f"Mode changed: {old_mode} -> {mode}")

            if old_cps != cps:
                log(f"CPS changed: {old_cps:g} -> {cps:g}")

            if old_cycle_duty != cycle_duty:
                log(f"Cycle Duty changed: {old_cycle_duty:g}% -> {cycle_duty:g}%")

            if old_cps_jitter != cps_jitter:
                log(f"CPS Jitter changed: {old_cps_jitter:g}% -> {cps_jitter:g}%")

            if old_click_button != click_button_name:
                log(f"Click Button changed: {old_click_button} -> {click_button_name}")

            if old_click_repeat != click_repeat_name:
                log(f"Click Count changed: {old_click_repeat} -> {click_repeat_name}")

            save_settings()

        cps_entry.bind("<KeyRelease>", apply)
        cycle_entry.bind("<KeyRelease>", apply)
        jitter_entry.bind("<KeyRelease>", apply)
        mode_menu.bind("<<ComboboxSelected>>", apply)
        click_button_menu.bind("<<ComboboxSelected>>", apply)
        click_repeat_menu.bind("<<ComboboxSelected>>", apply)

        # ------------------ PROFILE WORKSPACE ------------------
        profiles_page_frame = section("Saved Click Profiles", profiles_page)
        profiles_page_frame.grid_columnconfigure(0, weight=1)
        profiles_page_frame.grid_columnconfigure(1, weight=2)

        profile_name_var = tk.StringVar()
        profile_status_var = tk.StringVar(value="Save the current autoclicker controls as a reusable local profile.")
        profile_list = tk.Listbox(
            profiles_page_frame,
            bg=get_theme()["log_bg"],
            fg=get_theme()["log_fg"],
            selectbackground=get_theme()["log_select_bg"],
            selectforeground=get_theme()["log_fg"],
            relief="flat",
            bd=0,
            highlightthickness=1,
            highlightbackground=get_theme()["log_border"],
            font=("Segoe UI", 10),
            height=9,
            exportselection=False
        )
        profile_list.grid(row=0, column=0, rowspan=5, sticky="nsew", padx=(0, 18), pady=(0, 8))
        profile_form = tk.Frame(profiles_page_frame, bg=get_theme()["section_frame_bg"])
        profile_form.grid(row=0, column=1, sticky="nsew")
        tk.Label(profile_form, text="PROFILE NAME", bg=get_theme()["section_frame_bg"], fg=get_theme()["label_fg"], font=("Segoe UI", 9, "bold")).pack(anchor="w")
        profile_name_entry = tk.Entry(profile_form, textvariable=profile_name_var)
        style_entry_widget(profile_name_entry)
        profile_name_entry.pack(fill="x", pady=(7, 14), ipady=8)
        tk.Label(profile_form, text="Profiles capture CPS, cycle duty, jitter, mode, button, and click count. Keybinds stay independent for safety.", bg=get_theme()["section_frame_bg"], fg=get_theme()["secondary_fg"], font=("Segoe UI", 9), justify="left", wraplength=420).pack(fill="x", pady=(0, 18))
        profile_status = tk.Label(profile_form, textvariable=profile_status_var, bg=get_theme()["section_frame_bg"], fg=get_theme()["secondary_fg"], font=("Segoe UI", 9), justify="left", wraplength=420)
        profile_status.pack(fill="x", pady=(0, 14))

        def refresh_profile_list():
            profile_list.delete(0, tk.END)
            for profile in profiles:
                profile_list.insert(tk.END, profile["name"])
            if active_profile_name:
                for index, profile in enumerate(profiles):
                    if profile["name"] == active_profile_name:
                        profile_list.selection_set(index)
                        profile_list.see(index)
                        break

        def capture_profile(name):
            return {
                "name": name,
                "cps": cps,
                "mode": mode_var.get(),
                "cycle_duty": cycle_duty,
                "cps_jitter": cps_jitter,
                "click_button": click_button_var.get(),
                "click_repeat": click_repeat_var.get()
            }

        def save_current_profile():
            nonlocal active_profile_name
            name = profile_name_var.get().strip()
            if not name:
                profile_status_var.set("Enter a profile name first.")
                profile_name_entry.focus_set()
                return
            existing = next((profile for profile in profiles if profile["name"].lower() == name.lower()), None)
            captured = capture_profile(existing["name"] if existing else name)
            if existing:
                existing.update(captured)
                active_profile_name = existing["name"]
                profile_status_var.set(f"Updated profile: {existing['name']}")
            else:
                profiles.append(captured)
                active_profile_name = name
                profile_status_var.set(f"Saved profile: {name}")
            save_settings()
            refresh_profile_list()

        def load_selected_profile():
            nonlocal active_profile_name
            selection = profile_list.curselection()
            if not selection:
                profile_status_var.set("Select a profile to load.")
                return
            profile = profiles[selection[0]]
            active_profile_name = profile["name"]
            cps_entry.delete(0, tk.END)
            cps_entry.insert(0, profile.get("cps", 5.0))
            cycle_entry.delete(0, tk.END)
            cycle_entry.insert(0, profile.get("cycle_duty", 0.1))
            jitter_entry.delete(0, tk.END)
            jitter_entry.insert(0, profile.get("cps_jitter", 0.0))
            mode_var.set(profile.get("mode", "Toggle"))
            click_button_var.set(profile.get("click_button", "Left"))
            click_repeat_var.set(profile.get("click_repeat", "Single"))
            apply()
            profile_name_var.set(profile["name"])
            profile_status_var.set(f"Loaded profile: {profile['name']}")
            refresh_profile_list()

        def delete_selected_profile():
            nonlocal active_profile_name
            selection = profile_list.curselection()
            if not selection:
                profile_status_var.set("Select a profile to delete.")
                return
            deleted_name = profiles[selection[0]]["name"]
            del profiles[selection[0]]
            if active_profile_name == deleted_name:
                active_profile_name = None
                profile_name_var.set("")
            save_settings()
            refresh_profile_list()
            profile_status_var.set(f"Deleted profile: {deleted_name}")

        profile_actions = tk.Frame(profile_form, bg=get_theme()["section_frame_bg"])
        profile_actions.pack(fill="x")
        for text_value, command, kind in (
            ("Save Current", save_current_profile, "primary"),
            ("Load Selected", load_selected_profile, "secondary"),
            ("Delete Selected", delete_selected_profile, "secondary")
        ):
            button = tk.Button(profile_actions, text=text_value, command=command)
            style_modern_button(button, kind, compact=True)
            button.pack(side="left", padx=(0, 8))
        profile_list.bind("<Double-Button-1>", lambda _event: load_selected_profile())
        refresh_profile_list()

        # ------------------ SESSION SCHEDULER ------------------
        scheduler_frame = section("Session Scheduler", scheduler_page)
        scheduler_frame.grid_columnconfigure(0, weight=1)
        scheduler_frame.grid_columnconfigure(1, weight=1)
        scheduler_status_var = tk.StringVar(value="Ready to schedule an autoclicker session.")
        scheduler_time_var = tk.StringVar(value="15")
        scheduler_remaining_var = tk.StringVar(value="00:00:00")
        tk.Label(scheduler_frame, text="Run a timed session", bg=get_theme()["section_frame_bg"], fg=get_theme()["section_title_fg"], font=("Bahnschrift SemiBold", 18)).grid(row=0, column=0, columnspan=2, sticky="w")
        tk.Label(scheduler_frame, text="Start the current autoclicker configuration and stop it automatically when the timer ends.", bg=get_theme()["section_frame_bg"], fg=get_theme()["secondary_fg"], font=("Segoe UI", 10), justify="left", wraplength=700).grid(row=1, column=0, columnspan=2, sticky="w", pady=(7, 22))
        tk.Label(scheduler_frame, text="DURATION (MINUTES)", bg=get_theme()["section_frame_bg"], fg=get_theme()["label_fg"], font=("Segoe UI", 9, "bold")).grid(row=2, column=0, sticky="w")
        scheduler_time_entry = tk.Entry(scheduler_frame, textvariable=scheduler_time_var, width=16)
        style_entry_widget(scheduler_time_entry)
        scheduler_time_entry.grid(row=3, column=0, sticky="w", pady=(7, 16), ipady=8)
        scheduler_remaining_label = tk.Label(scheduler_frame, textvariable=scheduler_remaining_var, bg=get_theme()["section_frame_bg"], fg=get_theme()["section_accent"], font=("Bahnschrift SemiBold", 28))
        scheduler_remaining_label.grid(row=2, column=1, rowspan=2, sticky="e", padx=(20, 0))
        scheduler_status = tk.Label(scheduler_frame, textvariable=scheduler_status_var, bg=get_theme()["section_frame_bg"], fg=get_theme()["secondary_fg"], font=("Segoe UI", 9), justify="left", wraplength=700)
        scheduler_status.grid(row=4, column=0, columnspan=2, sticky="w", pady=(0, 16))

        def format_scheduler_time(seconds):
            seconds = max(0, int(seconds))
            return f"{seconds // 3600:02d}:{(seconds % 3600) // 60:02d}:{seconds % 60:02d}"

        def update_scheduler():
            nonlocal scheduler_job, scheduler_remaining, scheduler_running
            if not scheduler_running:
                return
            scheduler_remaining = max(0, scheduler_remaining - 1)
            scheduler_remaining_var.set(format_scheduler_time(scheduler_remaining))
            if scheduler_remaining <= 0:
                scheduler_running = False
                scheduler_job = None
                set_autoclicker_state(False, "Scheduler")
                scheduler_status_var.set("Scheduled session complete. Autoclicker stopped.")
                return
            scheduler_job = root.after(1000, update_scheduler)

        def start_scheduler():
            nonlocal scheduler_job, scheduler_remaining, scheduler_running
            try:
                duration = max(1, int(float(scheduler_time_var.get()) * 60))
            except ValueError:
                scheduler_status_var.set("Duration must be a positive number of minutes.")
                return
            if scheduler_job is not None:
                root.after_cancel(scheduler_job)
            scheduler_remaining = duration
            scheduler_running = True
            scheduler_remaining_var.set(format_scheduler_time(scheduler_remaining))
            set_autoclicker_state(True, "Scheduler")
            scheduler_status_var.set("Scheduled session running.")
            scheduler_job = root.after(1000, update_scheduler)

        def pause_scheduler():
            nonlocal scheduler_job, scheduler_running
            scheduler_running = False
            if scheduler_job is not None:
                root.after_cancel(scheduler_job)
                scheduler_job = None
            set_autoclicker_state(False, "Scheduler")
            scheduler_status_var.set("Scheduled session paused.")

        def reset_scheduler():
            nonlocal scheduler_job, scheduler_remaining, scheduler_running
            scheduler_running = False
            if scheduler_job is not None:
                root.after_cancel(scheduler_job)
                scheduler_job = None
            scheduler_remaining = 0
            scheduler_remaining_var.set("00:00:00")
            set_autoclicker_state(False, "Scheduler")
            scheduler_status_var.set("Scheduler reset and autoclicker stopped.")

        scheduler_actions = tk.Frame(scheduler_frame, bg=get_theme()["section_frame_bg"])
        scheduler_actions.grid(row=5, column=0, columnspan=2, sticky="w")
        for text_value, command, kind in (("Start Session", start_scheduler, "primary"), ("Pause", pause_scheduler, "secondary"), ("Reset", reset_scheduler, "secondary")):
            button = tk.Button(scheduler_actions, text=text_value, command=command)
            style_modern_button(button, kind, compact=True)
            button.pack(side="left", padx=(0, 8))

        # ------------------ LOCAL TOOLKIT ------------------
        toolkit_frame = section("Local Toolkit", toolkit_page)
        toolkit_frame.grid_columnconfigure(0, weight=1)
        toolkit_frame.grid_columnconfigure(1, weight=1)
        tk.Label(toolkit_frame, text="Utilities for a cleaner local workspace", bg=get_theme()["section_frame_bg"], fg=get_theme()["section_title_fg"], font=("Bahnschrift SemiBold", 18)).grid(row=0, column=0, columnspan=2, sticky="w")
        tk.Label(toolkit_frame, text="Keep session maintenance, settings access, and quick actions in one place. Everything stays on this PC.", bg=get_theme()["section_frame_bg"], fg=get_theme()["secondary_fg"], font=("Segoe UI", 10), justify="left", wraplength=700).grid(row=1, column=0, columnspan=2, sticky="w", pady=(7, 22))

        def reset_session_stats():
            session_stats["clicks"] = 0
            session_stats["started_at"] = time.perf_counter()
            toolkit_status_var.set("Session statistics reset.")

        def open_storage_folder():
            try:
                if os.name == "nt":
                    os.startfile(APP_STORAGE_DIR)
                else:
                    toolkit_status_var.set(APP_STORAGE_DIR)
            except Exception:
                toolkit_status_var.set(f"Storage path: {APP_STORAGE_DIR}")

        def export_settings_snapshot():
            try:
                snapshot_file = os.path.join(APP_STORAGE_DIR, f"{sanitize_account_name(active_account_username) or 'account'}_settings_backup.json")
                with open(settings_file, "r", encoding="utf-8") as source_file:
                    snapshot = json.load(source_file)
                write_json_file(snapshot_file, snapshot)
                toolkit_status_var.set(f"Settings backup written to {os.path.basename(snapshot_file)}.")
            except Exception:
                toolkit_status_var.set("Settings backup could not be created.")

        def reset_entire_application():
            nonlocal reset_application_requested
            if not messagebox.askyesno(
                "Reset Zhydra",
                "This deletes every local account and all saved settings. Your Authentication Key will be preserved, and you will return to the Enter Key page. Continue?",
                parent=root
            ):
                return
            shutdown_runtime()
            try:
                if os.path.isdir(ACCOUNTS_DIR):
                    shutil.rmtree(ACCOUNTS_DIR)
                if os.path.exists(LEGACY_SETTINGS_FILE):
                    os.remove(LEGACY_SETTINGS_FILE)
                ensure_app_storage()
                clear_session_state()
                reset_application_requested = True
                root.destroy()
            except Exception:
                toolkit_status_var.set("The full reset could not be completed.")

        toolkit_status_var = tk.StringVar(value="Choose a local utility.")
        toolkit_status = tk.Label(toolkit_frame, textvariable=toolkit_status_var, bg=get_theme()["section_frame_bg"], fg=get_theme()["secondary_fg"], font=("Segoe UI", 9), justify="left", wraplength=700)
        toolkit_status.grid(row=3, column=0, columnspan=2, sticky="w", pady=(20, 0))
        toolkit_actions = tk.Frame(toolkit_frame, bg=get_theme()["section_frame_bg"])
        toolkit_actions.grid(row=2, column=0, columnspan=2, sticky="w")
        for text_value, command, kind in (("Reset Session Stats", reset_session_stats, "primary"), ("Open Zhydra Folder", open_storage_folder, "secondary"), ("Backup Settings", export_settings_snapshot, "secondary"), ("Factor Reset", reset_entire_application, "danger")):
            button = tk.Button(toolkit_actions, text=text_value, command=command)
            style_modern_button(button, kind, compact=True)
            button.pack(side="left", padx=(0, 8))

        # ------------------ MOUSE CONTROL ------------------
        mouse_frame = section("Mouse Control", mouse_page)
        mouse_frame.grid_columnconfigure(0, weight=1)
        mouse_frame.grid_columnconfigure(1, weight=1)
        tk.Label(mouse_frame, text="Mouse motion laboratory", bg=get_theme()["section_frame_bg"], fg=get_theme()["section_title_fg"], font=("Bahnschrift SemiBold", 18)).grid(row=0, column=0, columnspan=2, sticky="w")
        tk.Label(mouse_frame, text="Create a controlled pointer shake for first-person camera testing or pointer calibration. Movement stays within the X and Y limits below.", bg=get_theme()["section_frame_bg"], fg=get_theme()["secondary_fg"], font=("Segoe UI", 10), justify="left", wraplength=720).grid(row=1, column=0, columnspan=2, sticky="w", pady=(7, 20))

        mouse_jitter_status = tk.StringVar(value="Mouse Jitter is idle.")
        mouse_jitter_key_label = tk.Label(mouse_frame, text="No keybind set", bg=get_theme()["section_frame_bg"], fg=get_theme()["secondary_fg"], font=("Segoe UI", 10))
        mouse_jitter_key_label.grid(row=2, column=0, sticky="w", pady=(4, 12))

        mouse_jitter_mode_var = tk.StringVar(value=mouse_jitter_mode)
        tk.Label(mouse_frame, text="TRIGGER MODE", bg=get_theme()["section_frame_bg"], fg=get_theme()["label_fg"], font=("Segoe UI", 9, "bold")).grid(row=2, column=1, sticky="e", padx=(12, 8), pady=(4, 12))
        mouse_jitter_mode_menu = ttk.Combobox(mouse_frame, textvariable=mouse_jitter_mode_var, values=["Toggle", "Hold"], state="readonly", width=11, style="Clean.TCombobox")
        mouse_jitter_mode_menu.grid(row=2, column=1, sticky="e", pady=(4, 12))
        block_combobox_mousewheel(mouse_jitter_mode_menu)

        def change_mouse_jitter_mode(_event=None):
            nonlocal mouse_jitter_mode, mouse_jitter_hold_active
            mouse_jitter_mode = mouse_jitter_mode_var.get() if mouse_jitter_mode_var.get() in {"Toggle", "Hold"} else "Toggle"
            if mouse_jitter_mode == "Toggle":
                mouse_jitter_hold_active = False
            save_settings()
            render_mouse_page()

        def capture_mouse_jitter_key():
            nonlocal mouse_jitter_capture
            mouse_jitter_capture = True
            mouse_jitter_key_label.config(text="Press a keyboard or mouse button, or Esc to cancel...")

        def clear_mouse_jitter_key():
            nonlocal mouse_jitter_keybind
            mouse_jitter_keybind = None
            mouse_jitter_key_label.config(text="No keybind set")
            save_settings()

        mouse_key_actions = tk.Frame(mouse_frame, bg=get_theme()["section_frame_bg"])
        mouse_key_actions.grid(row=3, column=0, sticky="w", pady=(0, 20))
        capture_mouse_key_button = tk.Button(mouse_key_actions, text="Set Jitter Keybind", command=capture_mouse_jitter_key)
        style_modern_button(capture_mouse_key_button, "primary", compact=True)
        capture_mouse_key_button.pack(side="left", padx=(0, 8))
        clear_mouse_key_button = tk.Button(mouse_key_actions, text="Clear", command=clear_mouse_jitter_key)
        style_modern_button(clear_mouse_key_button, "secondary", compact=True)
        clear_mouse_key_button.pack(side="left")

        jitter_toggle_button = tk.Button(mouse_frame, text="Start Mouse Jitter", command=toggle_mouse_jitter)
        style_modern_button(jitter_toggle_button, "primary", compact=True)
        jitter_toggle_button.grid(row=3, column=1, sticky="e", pady=(0, 20))

        def make_mouse_scale(row, title_text, variable, from_value, to_value, command):
            tk.Label(mouse_frame, text=title_text, bg=get_theme()["section_frame_bg"], fg=get_theme()["label_fg"], font=("Segoe UI", 10, "bold")).grid(row=row, column=0, sticky="w", pady=(8, 2))
            slider = tk.Canvas(
                mouse_frame,
                width=380,
                height=42,
                bg=get_theme()["section_frame_bg"],
                highlightthickness=0,
                bd=0,
                cursor="hand2"
            )
            slider.grid(row=row + 1, column=0, sticky="w", pady=(0, 8))
            state = {"dragging": False}

            def value_from_event(event):
                track_left = 10
                track_right = 350
                ratio = max(0.0, min(1.0, (event.x - track_left) / (track_right - track_left)))
                return int(round(from_value + ratio * (to_value - from_value)))

            def set_value(event):
                value = value_from_event(event)
                variable.set(value)
                command(str(value))
                redraw()

            def redraw():
                if not slider.winfo_exists():
                    return
                theme = get_theme()
                slider.delete("all")
                slider.configure(bg=theme["section_frame_bg"])
                try:
                    value = max(from_value, min(to_value, int(variable.get())))
                except (TypeError, ValueError, tk.TclError):
                    value = from_value
                ratio = (value - from_value) / max(1, to_value - from_value)
                knob_x = 10 + (340 * ratio)
                slider.create_line(10, 21, 350, 21, fill=theme["entry_border"], width=6, capstyle=tk.ROUND)
                slider.create_line(10, 21, knob_x, 21, fill=theme["section_accent"], width=6, capstyle=tk.ROUND)
                slider.create_oval(knob_x - 8, 13, knob_x + 8, 29, fill=theme["button_label"], outline=theme["section_accent"], width=2)
                slider.create_text(370, 21, text=str(value), anchor="e", fill=theme["label_fg"], font=("Segoe UI", 9, "bold"))

            slider.bind("<Button-1>", set_value)
            slider.bind("<B1-Motion>", set_value)
            slider._refresh_theme = redraw
            themed_soft_buttons.append(slider)
            redraw()
            return slider

        mouse_speed_var = tk.IntVar(value=mouse_jitter_speed)
        mouse_x_var = tk.IntVar(value=mouse_jitter_x)
        mouse_y_var = tk.IntVar(value=mouse_jitter_y)

        def update_mouse_jitter_settings(_value=None):
            nonlocal mouse_jitter_speed, mouse_jitter_x, mouse_jitter_y
            mouse_jitter_speed = min(100, max(1, int(mouse_speed_var.get())))
            mouse_jitter_x = min(30, max(1, int(mouse_x_var.get())))
            mouse_jitter_y = min(30, max(1, int(mouse_y_var.get())))
            mouse_jitter_status.set(f"Shake range: X ±{mouse_jitter_x}px, Y ±{mouse_jitter_y}px")
            save_settings()

        mouse_speed_scale = make_mouse_scale(4, "SHAKE SPEED", mouse_speed_var, 1, 100, update_mouse_jitter_settings)
        mouse_x_scale = make_mouse_scale(6, "HORIZONTAL RANGE (PX)", mouse_x_var, 1, 30, update_mouse_jitter_settings)
        mouse_y_scale = make_mouse_scale(8, "VERTICAL RANGE (PX)", mouse_y_var, 1, 30, update_mouse_jitter_settings)
        tk.Label(mouse_frame, textvariable=mouse_jitter_status, bg=get_theme()["section_frame_bg"], fg=get_theme()["secondary_fg"], font=("Segoe UI", 9), justify="left").grid(row=10, column=0, columnspan=2, sticky="w", pady=(10, 0))

        mouse_jitter_mode_menu.bind("<<ComboboxSelected>>", change_mouse_jitter_mode)

        utility_frame = section("Mouse Utilities", mouse_page)
        utility_frame.grid_columnconfigure(0, weight=1)
        utility_frame.grid_columnconfigure(1, weight=1)
        mouse_position_var = tk.StringVar(value="Position unavailable")
        scroll_steps_var = tk.IntVar(value=3)

        tk.Label(utility_frame, text="Pointer tools", bg=get_theme()["section_frame_bg"], fg=get_theme()["section_title_fg"], font=("Bahnschrift SemiBold", 18)).grid(row=0, column=0, columnspan=2, sticky="w")
        tk.Label(utility_frame, textvariable=mouse_position_var, bg=get_theme()["section_frame_bg"], fg=get_theme()["secondary_fg"], font=("Segoe UI", 10)).grid(row=1, column=0, sticky="w", pady=(8, 16))

        def refresh_mouse_position():
            try:
                x, y = m.position
                mouse_position_var.set(f"Cursor position: {x}, {y}")
            except:
                mouse_position_var.set("Cursor position unavailable")

        def center_mouse_pointer():
            try:
                m.position = (root.winfo_screenwidth() // 2, root.winfo_screenheight() // 2)
                refresh_mouse_position()
            except:
                mouse_position_var.set("Could not center cursor")

        def scroll_mouse(amount):
            try:
                m.scroll(0, amount * max(1, int(scroll_steps_var.get())))
                refresh_mouse_position()
            except:
                mouse_position_var.set("Scroll input unavailable")

        utility_actions = tk.Frame(utility_frame, bg=get_theme()["section_frame_bg"])
        utility_actions.grid(row=2, column=0, columnspan=2, sticky="w")
        for text_value, command, kind in (("Refresh Position", refresh_mouse_position, "secondary"), ("Center Pointer", center_mouse_pointer, "primary"), ("Scroll Up", lambda: scroll_mouse(1), "secondary"), ("Scroll Down", lambda: scroll_mouse(-1), "secondary")):
            button = tk.Button(utility_actions, text=text_value, command=command)
            style_modern_button(button, kind, compact=True)
            button.pack(side="left", padx=(0, 8))

        tk.Label(utility_frame, text="SCROLL STEPS", bg=get_theme()["section_frame_bg"], fg=get_theme()["label_fg"], font=("Segoe UI", 9, "bold")).grid(row=3, column=0, sticky="w", pady=(16, 0))
        scroll_steps_entry = tk.Spinbox(utility_frame, from_=1, to=20, textvariable=scroll_steps_var, width=8, bg=get_theme()["entry_bg"], fg=get_theme()["entry_fg"], buttonbackground=get_theme()["entry_bg"], relief="flat", highlightthickness=1, highlightbackground=get_theme()["entry_border"])
        scroll_steps_entry.grid(row=4, column=0, sticky="w", pady=(6, 0))
        refresh_mouse_position()

        def render_mouse_page():
            mouse_jitter_key_label.config(text=format_keybind_text(mouse_jitter_keybind) if mouse_jitter_keybind else "No keybind set")
            jitter_toggle_button.config(text="Stop Mouse Jitter" if mouse_jitter_enabled else "Start Mouse Jitter")
            mouse_jitter_status.set(f"{'Running' if mouse_jitter_enabled else 'Idle'} | Shake range: X ±{mouse_jitter_x}px, Y ±{mouse_jitter_y}px")

        render_mouse_page()
        if mouse_jitter_enabled and mouse_jitter_mode == "Toggle":
            set_mouse_jitter_state(True, "Mouse Jitter")

        # ------------------ LOG WINDOW ------------------
        log_frame = section("Activity Log", autoclicker_page, expand=True)
        log_frame.configure(height=190)
        log_frame.pack_propagate(False)

        log_scrollbar = ttk.Scrollbar(log_frame, orient="vertical", style="Clean.Vertical.TScrollbar")
        log_box = tk.Text(log_frame, height=8, bg=get_theme()["log_bg"], fg=get_theme()["log_fg"],
                  bd=0, state="disabled", font=("Consolas", 10, "bold"),
                  insertbackground=get_theme()["entry_insert"], relief="flat",
              selectbackground=get_theme()["log_select_bg"], selectforeground=get_theme()["log_fg"],
              highlightthickness=1, highlightbackground=get_theme()["log_border"], highlightcolor=get_theme()["entry_focus"],
              yscrollcommand=log_scrollbar.set)
        log_box.pack(side="left", fill="both", expand=True)
        log_scrollbar.pack(side="right", fill="y", padx=(10, 0))
        log_scrollbar.configure(command=log_box.yview)
        style_text_widget(log_box)

        def on_log_mousewheel(event):
            steps = mousewheel_steps(event)
            if steps:
                log_box.yview_scroll(steps, "units")
                return "break"

        log_box.bind("<MouseWheel>", on_log_mousewheel)
        log_box.bind("<Button-4>", on_log_mousewheel)
        log_box.bind("<Button-5>", on_log_mousewheel)

        def create_macro_panel(parent, title, width=None, height=None):
            theme = get_theme()
            shadow = tk.Frame(
                parent,
                bg=blend(theme.get("panel_shadow", theme["button_shadow"]), theme["window_bg"], 0.30),
                bd=0,
                highlightthickness=0
            )
            if width is not None or height is not None:
                if width is not None:
                    shadow.configure(width=width + 8)
                if height is not None:
                    shadow.configure(height=height + 8)
                shadow.pack_propagate(False)

            shell = tk.Frame(
                shadow,
                bg=theme["section_shell_bg"],
                bd=0,
                highlightthickness=1,
                highlightbackground=theme["section_border"]
            )
            shell.pack(fill="both", expand=True, padx=(0, 8), pady=(0, 8))

            accent = tk.Frame(shell, bg=theme["section_accent"], height=2)
            accent.pack(fill="x", side="top")

            title_bar = tk.Frame(shell, bg=theme["section_title_bar_bg"])
            title_bar.pack(fill="x")

            title_label = tk.Label(
                title_bar,
                text=title,
                bg=theme["section_title_bar_bg"],
                fg=theme["section_title_fg"],
                font=("Segoe UI", 11, "bold")
            )
            title_label.pack(anchor="w", padx=16, pady=(12, 8))

            frame = tk.Frame(shell, bg=theme["section_frame_bg"], padx=18, pady=18)
            frame.pack(fill="both", expand=True, padx=16, pady=(0, 16))
            macro_panels.append({
                "shadow": shadow,
                "shell": shell,
                "accent": accent,
                "title_bar": title_bar,
                "title_label": title_label,
                "frame": frame
            })
            return shadow, frame

        macros_workspace = tk.Frame(macros_page, bg=get_theme()["card_bg"])
        macros_workspace.pack(fill="both", expand=True, padx=28, pady=(22, 14))

        macro_panel_height = 500

        macro_sidebar_shell, macro_sidebar_frame = create_macro_panel(macros_workspace, "Macro List", width=272, height=macro_panel_height)
        macro_sidebar_shell.pack(side="left", fill="y", padx=(0, 14))

        macro_editor_shell, macro_editor_frame = create_macro_panel(macros_workspace, "Macro Editor", height=macro_panel_height)
        macro_editor_shell.pack(side="left", fill="both", expand=True)

        macro_list_container = tk.Frame(macro_sidebar_frame, bg=get_theme()["section_frame_bg"])
        macro_list_actions = tk.Frame(macro_sidebar_frame, bg=get_theme()["section_frame_bg"])
        macro_list_actions.pack(fill="x", pady=(0, 12))

        macro_add_hint = tk.Label(
            macro_list_actions,
            text="Add Macro",
            bg=get_theme()["section_frame_bg"],
            fg=get_theme()["secondary_fg"],
            font=("Segoe UI", 9, "bold"),
            anchor="w"
        )
        macro_add_hint.pack(side="left")

        macro_list_container.pack(fill="both", expand=True)

        macro_list_canvas = tk.Canvas(
            macro_list_container,
            bg=get_theme()["section_frame_bg"],
            highlightthickness=0,
            bd=0,
            relief="flat"
        )
        macro_list_scrollbar = ttk.Scrollbar(
            macro_list_container,
            orient="vertical",
            command=macro_list_canvas.yview,
            style="Clean.Vertical.TScrollbar"
        )
        macro_list_canvas.configure(yscrollcommand=macro_list_scrollbar.set)
        macro_list_canvas.pack(side="left", fill="both", expand=True)
        macro_list_scrollbar.pack(side="right", fill="y", padx=(8, 0))

        macro_list_view = tk.Frame(macro_list_canvas, bg=get_theme()["section_frame_bg"])
        macro_list_window = macro_list_canvas.create_window((0, 0), window=macro_list_view, anchor="nw")

        def refresh_macro_list_scrollregion(event=None):
            macro_list_canvas.configure(scrollregion=macro_list_canvas.bbox("all"))

        def resize_macro_list_view(event):
            macro_list_canvas.itemconfigure(macro_list_window, width=event.width)
            refresh_macro_list_scrollregion()

        def on_macro_list_mousewheel(event):
            steps = mousewheel_steps(event)
            if steps:
                macro_list_canvas.yview_scroll(steps, "units")
                return "break"

        def bind_macro_list_mousewheel(widget):
            widget.bind("<MouseWheel>", on_macro_list_mousewheel, add="+")
            widget.bind("<Button-4>", on_macro_list_mousewheel, add="+")
            widget.bind("<Button-5>", on_macro_list_mousewheel, add="+")

        macro_list_view.bind("<Configure>", refresh_macro_list_scrollregion)
        macro_list_canvas.bind("<Configure>", resize_macro_list_view)
        bind_macro_list_mousewheel(macro_list_canvas)
        bind_macro_list_mousewheel(macro_list_view)

        macro_editor_body = tk.Frame(macro_editor_frame, bg=get_theme()["section_frame_bg"])
        macro_editor_body.pack(fill="both", expand=True)

        macro_log_frame = section("Activity Log", macros_page, expand=True)
        macro_log_frame.configure(height=170)
        macro_log_frame.pack_propagate(False)

        macro_log_scrollbar = ttk.Scrollbar(macro_log_frame, orient="vertical", style="Clean.Vertical.TScrollbar")
        macro_log_box = tk.Text(
            macro_log_frame,
            height=7,
            bg=get_theme()["log_bg"],
            fg=get_theme()["log_fg"],
            bd=0,
            state="disabled",
            font=("Consolas", 10, "bold"),
            insertbackground=get_theme()["entry_insert"],
            relief="flat",
            selectbackground=get_theme()["log_select_bg"],
            selectforeground=get_theme()["log_fg"],
            highlightthickness=1,
            highlightbackground=get_theme()["log_border"],
            highlightcolor=get_theme()["entry_focus"],
            yscrollcommand=macro_log_scrollbar.set
        )
        macro_log_box.pack(side="left", fill="both", expand=True)
        macro_log_scrollbar.pack(side="right", fill="y", padx=(10, 0))
        macro_log_scrollbar.configure(command=macro_log_box.yview)
        style_text_widget(macro_log_box)

        def on_macro_log_mousewheel(event):
            steps = mousewheel_steps(event)
            if steps:
                macro_log_box.yview_scroll(steps, "units")
                return "break"

        macro_log_box.bind("<MouseWheel>", on_macro_log_mousewheel)
        macro_log_box.bind("<Button-4>", on_macro_log_mousewheel)
        macro_log_box.bind("<Button-5>", on_macro_log_mousewheel)

        mods_features_frame = section("Installed Mods", mods_page)
        mods_cards_frame = tk.Frame(mods_features_frame, bg=get_theme()["section_frame_bg"])
        mods_cards_frame.pack(fill="x")

        mods_bindings_frame = tk.Frame(mods_page, bg=get_theme()["card_bg"])

        launch_on_startup_var = tk.BooleanVar(value=launch_on_startup_enabled)
        smart_cycle_var = tk.BooleanVar(value=smart_cycle_enabled)
        multi_bind_var = tk.BooleanVar(value=multi_bind_enabled)
        sound_feedback_var = tk.BooleanVar(value=sound_feedback_enabled)
        macro_preview_var = tk.BooleanVar(value=macro_preview_enabled)
        anti_afk_var = tk.BooleanVar(value=anti_afk_enabled)
        pause_on_focus_loss_var = tk.BooleanVar(value=pause_on_focus_loss_enabled)
        auto_limiter_var = tk.BooleanVar(value=auto_limiter_enabled)
        break_reminder_var = tk.BooleanVar(value=break_reminder_enabled)
        mods_macro_var = tk.StringVar(value="")

        def format_macro_option(macro):
            return f"{macro['id']} • {macro['name']}"

        def toggle_launch_on_startup_mod():
            nonlocal launch_on_startup_enabled
            desired = bool(launch_on_startup_var.get())
            if desired == launch_on_startup_enabled:
                return
            action = "enable" if desired else "disable"
            if not messagebox.askyesno("Confirm", f"Are you sure you want to {action} Launch on Startup?"):
                launch_on_startup_var.set(launch_on_startup_enabled)
                return
            if not set_launch_on_startup(desired):
                launch_on_startup_var.set(launch_on_startup_enabled)
                log("❌ Launch on Startup could not be updated")
                render_mods_page()
                return
            launch_on_startup_enabled = read_launch_on_startup_state() if os.name == "nt" else desired
            launch_on_startup_var.set(launch_on_startup_enabled)
            save_settings()
            render_mods_page()
            status = "✔ enabled" if launch_on_startup_enabled else "disabled"
            log(f"Launch on Startup {status}")
            show_system_notification("Zhydra", f"Launch on Startup {status}")

        def toggle_smart_cycle_mod():
            nonlocal smart_cycle_enabled
            desired = bool(smart_cycle_var.get())
            if desired == smart_cycle_enabled:
                return
            action = "enable" if desired else "disable"
            if not messagebox.askyesno("Confirm", f"Are you sure you want to {action} Smart Cycle?"):
                smart_cycle_var.set(smart_cycle_enabled)
                return
            smart_cycle_enabled = desired
            save_settings()
            render_mods_page()
            status = "✔ enabled" if smart_cycle_enabled else "disabled"
            log(f"Smart Cycle {status}")
            show_system_notification("Zhydra", f"Smart Cycle {status}")

        def toggle_multi_bind_mod():
            nonlocal multi_bind_enabled, multi_bind_capture_target
            desired = bool(multi_bind_var.get())
            if desired == multi_bind_enabled:
                return
            multi_bind_enabled = desired
            multi_bind_capture_target = None
            save_settings()
            render_mods_page()
            status = "✔ enabled" if multi_bind_enabled else "disabled"
            log(f"Multi Binding {status}")
            show_system_notification("Zhydra", f"Multi Binding {status}")

        def toggle_sound_feedback_mod():
            nonlocal sound_feedback_enabled
            desired = bool(sound_feedback_var.get())
            if desired == sound_feedback_enabled:
                return
            action = "enable" if desired else "disable"
            if not messagebox.askyesno("Confirm", f"Are you sure you want to {action} Sound Feedback?"):
                sound_feedback_var.set(sound_feedback_enabled)
                return
            sound_feedback_enabled = desired
            save_settings()
            render_mods_page()
            status = "✔ enabled" if sound_feedback_enabled else "disabled"
            log(f"Sound Feedback {status}")
            show_system_notification("Zhydra", f"Sound Feedback {status}")

        def toggle_macro_preview_mod():
            nonlocal macro_preview_enabled
            desired = bool(macro_preview_var.get())
            if desired == macro_preview_enabled:
                return
            action = "enable" if desired else "disable"
            if not messagebox.askyesno("Confirm", f"Are you sure you want to {action} Macro Preview?"):
                macro_preview_var.set(macro_preview_enabled)
                return
            macro_preview_enabled = desired
            save_settings()
            render_mods_page()
            status = "✔ enabled" if macro_preview_enabled else "disabled"
            log(f"Macro Preview {status}")
            show_system_notification("Zhydra", f"Macro Preview {status}")

        def toggle_anti_afk_mod():
            nonlocal anti_afk_enabled
            desired = bool(anti_afk_var.get())
            if desired == anti_afk_enabled:
                return
            action = "enable" if desired else "disable"
            if not messagebox.askyesno("Confirm", f"Are you sure you want to {action} Anti-AFK Mode?"):
                anti_afk_var.set(anti_afk_enabled)
                return
            anti_afk_enabled = desired
            save_settings()
            render_mods_page()
            status = "✔ enabled" if anti_afk_enabled else "disabled"
            log(f"Anti-AFK Mode {status}")
            show_system_notification("Zhydra", f"Anti-AFK Mode {status}")

        def toggle_pause_on_focus_loss_mod():
            nonlocal pause_on_focus_loss_enabled
            desired = bool(pause_on_focus_loss_var.get())
            if desired == pause_on_focus_loss_enabled:
                return
            action = "enable" if desired else "disable"
            if not messagebox.askyesno("Confirm", f"Are you sure you want to {action} Pause on Focus Loss?"):
                pause_on_focus_loss_var.set(pause_on_focus_loss_enabled)
                return
            pause_on_focus_loss_enabled = desired
            save_settings()
            render_mods_page()
            status = "✔ enabled" if pause_on_focus_loss_enabled else "disabled"
            log(f"Pause on Focus Loss {status}")
            show_system_notification("Zhydra", f"Pause on Focus Loss {status}")

        def toggle_auto_limiter_mod():
            nonlocal auto_limiter_enabled
            desired = bool(auto_limiter_var.get())
            if desired == auto_limiter_enabled:
                return
            action = "enable" if desired else "disable"
            if not messagebox.askyesno("Confirm", f"Are you sure you want to {action} Auto-Limiter?"):
                auto_limiter_var.set(auto_limiter_enabled)
                return
            auto_limiter_enabled = desired
            save_settings()
            render_mods_page()
            status = "✔ enabled" if auto_limiter_enabled else "disabled"
            log(f"Auto-Limiter {status}")
            show_system_notification("Zhydra", f"Auto-Limiter {status}")

        def toggle_break_reminder_mod():
            nonlocal break_reminder_enabled, last_break_reminder_time, break_reminder_countdown
            desired = bool(break_reminder_var.get())
            if desired == break_reminder_enabled:
                return
            action = "enable" if desired else "disable"
            if not messagebox.askyesno("Confirm", f"Are you sure you want to {action} Break Reminder?"):
                break_reminder_var.set(break_reminder_enabled)
                return
            break_reminder_enabled = desired
            if break_reminder_enabled:
                last_break_reminder_time = time.perf_counter()
                break_reminder_countdown = break_reminder_interval
            save_settings()
            render_mods_page()
            status = "✔ enabled" if break_reminder_enabled else "disabled"
            log(f"Break Reminder {status}")
            show_system_notification("Zhydra", f"Break Reminder {status}")

        def render_mods_page():
            theme = get_theme()
            launch_on_startup_var.set(launch_on_startup_enabled)
            smart_cycle_var.set(smart_cycle_enabled)
            multi_bind_var.set(multi_bind_enabled)
            sound_feedback_var.set(sound_feedback_enabled)
            macro_preview_var.set(macro_preview_enabled)

            for child in mods_cards_frame.winfo_children():
                child.destroy()
            for child in mods_bindings_frame.winfo_children():
                child.destroy()

            def create_mod_card(parent, title_text, description_text, variable, command, detail_text):
                enabled = bool(variable.get())
                card_bg = blend(theme["surface_alt"], theme["section_frame_bg"], 0.08 if enabled else 0.18)
                card_border = blend(theme["section_accent"], theme["section_border"], 0.74 if enabled else 0.18)
                card = tk.Frame(parent, bg=card_bg, bd=0, highlightthickness=1, highlightbackground=card_border)
                card.pack(fill="x", pady=(0, 12))

                accent = tk.Frame(card, bg=theme["section_accent"] if enabled else blend(theme["entry_border"], theme["section_border"], 0.26), height=3)
                accent.pack(fill="x", side="top")

                body = tk.Frame(card, bg=card_bg)
                body.pack(fill="both", expand=True, padx=16, pady=15)

                header = tk.Frame(body, bg=card_bg)
                header.pack(fill="x")

                copy = tk.Frame(header, bg=card_bg)
                copy.pack(side="left", fill="x", expand=True)

                tk.Label(copy, text=title_text, bg=card_bg, fg=theme["section_title_fg"], font=("Segoe UI", 11, "bold"), anchor="w").pack(fill="x")
                tk.Label(copy, text=description_text, bg=card_bg, fg=theme["secondary_fg"], font=("Segoe UI", 9), justify="left", wraplength=560, anchor="w").pack(fill="x", pady=(4, 0))

                status_chip = tk.Label(
                    copy,
                    text="Enabled" if enabled else "Disabled",
                    bg=blend(theme["button_body"], card_bg, 0.18) if enabled else blend(theme["entry_bg"], card_bg, 0.06),
                    fg=theme["button_label"] if enabled else theme["secondary_fg"],
                    font=("Segoe UI", 8, "bold"),
                    padx=8,
                    pady=3,
                    bd=0,
                    relief="flat",
                    highlightthickness=1,
                    highlightbackground=theme["button_outline"] if enabled else blend(theme["entry_border"], card_bg, 0.16)
                )
                status_chip.pack(anchor="w", pady=(10, 0))

                toggle_wrap = tk.Frame(header, bg=card_bg)
                toggle_wrap.pack(side="right", padx=(16, 0), anchor="n")

                toggle = create_slider_toggle(toggle_wrap, variable, command)
                toggle.pack(anchor="e")

                tk.Label(body, text=detail_text, bg=card_bg, fg=theme["label_fg"], font=("Segoe UI", 9), justify="left", anchor="w", wraplength=660).pack(fill="x", pady=(14, 0))

            create_mod_card(
                mods_cards_frame,
                "Multi Binding",
                "Allows the same key or mouse button to be shared by the autoclicker, macros, and Mouse Jitter.",
                multi_bind_var,
                toggle_multi_bind_mod,
                "When disabled, each keybind must belong to only one module."
            )

            startup_detail = "Adds or removes a real Windows startup entry for this app." if os.name == "nt" else "Startup registration is only available on Windows."
            startup_detail += f" Current state: {'Enabled' if launch_on_startup_enabled else 'Disabled'}."
            create_mod_card(
                mods_cards_frame,
                "Launch on Startup",
                "Automatically starts Zhydra when you sign into Windows, so the autoclicker is always ready to go without manual launch.",
                launch_on_startup_var,
                toggle_launch_on_startup_mod,
                startup_detail
            )
            create_mod_card(
                mods_cards_frame,
                "Smart Cycle",
                "Dynamically adjusts click hold time based on your CPS, mouse button, and click count to maximize accuracy and reduce timing errors.",
                smart_cycle_var,
                toggle_smart_cycle_mod,
                get_smart_cycle_status_text() if smart_cycle_enabled else "When disabled, manually set Cycle Duty % in the main tab to control hold timing."
            )
            create_mod_card(
                mods_cards_frame,
                "Sound Feedback",
                "Produces a system beep whenever you enable/disable mods, create/delete macros, or change keybinds. Great for audible confirmation of actions.",
                sound_feedback_var,
                toggle_sound_feedback_mod,
                "When enabled, plays a success beep on valid changes and an error beep when something fails. Works even if the app window is minimized."
            )
            create_mod_card(
                mods_cards_frame,
                "Macro Preview",
                "Shows a live preview card in the Overview tab that displays the currently selected macro name and total number of steps in it.",
                macro_preview_var,
                toggle_macro_preview_mod,
                "Displays active macro details in real-time. Useful for monitoring which macro is loaded and how many actions it contains."
            )
            create_mod_card(
                mods_cards_frame,
                "Anti-AFK Mode",
                "Automatically keeps the autoclicker active by simulating periodic activity every few seconds, preventing inactivity timeouts and disconnects.",
                anti_afk_var,
                toggle_anti_afk_mod,
                f"When enabled, performs a passive action every {anti_afk_interval} seconds while the autoclicker is active. Does not interfere with your actual clicking."
            )
            create_mod_card(
                mods_cards_frame,
                "Pause on Focus Loss",
                "Automatically halts the autoclicker whenever the active window loses focus or another app comes to the foreground, preventing unintended clicks.",
                pause_on_focus_loss_var,
                toggle_pause_on_focus_loss_mod,
                "Keeps the autoclicker safe by pausing it when your game/app window is not in focus. Resumes clicking when you return to the window."
            )
            create_mod_card(
                mods_cards_frame,
                "Auto-Limiter",
                "Stops the autoclicker automatically after reaching a specified number of total clicks, useful for farming quotas or limit-based tasks.",
                auto_limiter_var,
                toggle_auto_limiter_mod,
                f"Session click limit is set to {auto_limiter_clicks} clicks. When reached, the autoclicker will disable itself. Configure the limit in settings."
            )
            create_mod_card(
                mods_cards_frame,
                "Break Reminder",
                "Sends you a notification every 30 minutes (or custom interval) to remind you to take a break and rest your hands.",
                break_reminder_var,
                toggle_break_reminder_mod,
                f"When enabled, you'll receive a gentle reminder notification every {break_reminder_interval} seconds to take a break. Your health matters!"
            )

            return

            intro = tk.Label(
                mods_bindings_frame,
                text="Manage extra bindings here. The + buttons create real new binding inputs that listen for keyboard keys or mouse buttons.",
                bg=theme["section_frame_bg"],
                fg=theme["secondary_fg"],
                font=("Segoe UI", 9),
                justify="left",
                anchor="w",
                wraplength=760
            )
            intro.pack(fill="x", pady=(0, 14))

            def create_bind_card(parent, title_text, description_text):
                card_bg = blend(theme["entry_bg"], theme["section_frame_bg"], 0.14)
                card_border = blend(theme["entry_border"], theme["section_border"], 0.32)
                shell = tk.Frame(parent, bg=card_bg, bd=0, highlightthickness=1, highlightbackground=card_border)
                shell.pack(fill="x", pady=(0, 14))

                body = tk.Frame(shell, bg=card_bg)
                body.pack(fill="both", expand=True, padx=14, pady=14)

                header = tk.Frame(body, bg=card_bg)
                header.pack(fill="x")

                copy = tk.Frame(header, bg=card_bg)
                copy.pack(side="left", fill="x", expand=True)
                tk.Label(copy, text=title_text, bg=card_bg, fg=theme["section_title_fg"], font=("Segoe UI", 10, "bold"), anchor="w").pack(fill="x")
                tk.Label(copy, text=description_text, bg=card_bg, fg=theme["secondary_fg"], font=("Segoe UI", 9), justify="left", anchor="w", wraplength=620).pack(fill="x", pady=(4, 0))

                rows_host = tk.Frame(body, bg=card_bg)
                rows_host.pack(fill="x", pady=(12, 0))
                return card_bg, header, rows_host

            autoclicker_card_bg, autoclicker_header, autoclicker_rows = create_bind_card(
                mods_bindings_frame,
                "Autoclicker Binds",
                "Primary and extra keybinds for starting or holding the autoclicker."
            )

            if multi_bind_enabled:
                add_auto_button = tk.Button(
                    autoclicker_header,
                    text="+ Add",
                    command=lambda: begin_multi_bind_capture({"owner": "autoclicker", "index": len(toggle_keys)}),
                    bd=0,
                    relief="flat",
                    cursor="hand2",
                    padx=10,
                    pady=5
                )
                style_modern_button(add_auto_button, "primary", compact=True)
                add_auto_button.pack(side="right")

            auto_row_count = max(1, len(toggle_keys))
            if multi_bind_capture_target and multi_bind_capture_target.get("owner") == "autoclicker":
                auto_row_count = max(auto_row_count, multi_bind_capture_target.get("index", 0) + 1)

            for index in range(auto_row_count):
                binding = toggle_keys[index] if index < len(toggle_keys) else None
                capturing = multi_bind_capture_target == {"owner": "autoclicker", "index": index}
                row_bg = blend(theme["section_frame_bg"], autoclicker_card_bg, 0.20)
                row = tk.Frame(autoclicker_rows, bg=row_bg, bd=0, highlightthickness=1, highlightbackground=blend(theme["entry_border"], theme["entry_focus"], 0.10))
                row.pack(fill="x", pady=(0, 8))

                tk.Label(row, text=f"{index + 1:02d}", width=4, bg=row_bg, fg=theme["secondary_fg"], font=("Segoe UI", 9, "bold")).pack(side="left", padx=(10, 4), pady=9)
                tk.Label(
                    row,
                    text="Press a key or mouse button..." if capturing else format_toggle_binding_compact_text(binding),
                    bg=row_bg,
                    fg=theme["label_fg"] if binding or capturing else theme["secondary_fg"],
                    font=("Segoe UI", 9),
                    anchor="w"
                ).pack(side="left", fill="x", expand=True, padx=(0, 8))

                set_button = tk.Button(row, text="Set", command=lambda current=index: begin_multi_bind_capture({"owner": "autoclicker", "index": current}), bd=0, relief="flat", cursor="hand2", padx=10, pady=5)
                style_modern_button(set_button, "primary", compact=True)
                set_button.pack(side="right", padx=(0, 8), pady=6)

                remove_button = tk.Button(
                    row,
                    text="Remove" if index > 0 else "Clear",
                    command=lambda current=index: (remove_autoclicker_binding_at(current), key_label.config(text=format_autoclicker_keybind_text()), save_settings(), render_mods_page(), log("Autoclicker keybind removed")),
                    bd=0,
                    relief="flat",
                    cursor="hand2",
                    padx=10,
                    pady=5
                )
                style_modern_button(remove_button, "secondary", compact=True)
                remove_button.pack(side="right", padx=(0, 8), pady=6)

            macro_card_bg, macro_header, macro_rows = create_bind_card(
                mods_bindings_frame,
                "Macro Binds",
                "Select a macro and assign one or many triggers that can fire it."
            )

            selected_macro = None
            if macros:
                options = [format_macro_option(macro) for macro in macros]
                current_option = mods_macro_var.get()
                option_map = {format_macro_option(macro): macro for macro in macros}
                if current_option not in option_map:
                    selected_macro = get_macro_by_id(current_macro_id) or macros[0]
                    mods_macro_var.set(format_macro_option(selected_macro))
                else:
                    selected_macro = option_map[current_option]

                selector = ttk.Combobox(macro_header, textvariable=mods_macro_var, values=options, state="readonly", width=26, style="Clean.TCombobox")
                selector.pack(side="right", padx=(8, 0))
                block_combobox_mousewheel(selector)

                def on_select_macro(_event=None):
                    nonlocal current_macro_id
                    chosen_macro = option_map.get(mods_macro_var.get())
                    if not chosen_macro:
                        return
                    current_macro_id = chosen_macro["id"]
                    render_macro_list()
                    render_macro_editor()
                    render_mods_page()

                selector.bind("<<ComboboxSelected>>", on_select_macro)

                if multi_bind_enabled:
                    add_macro_button = tk.Button(
                        macro_header,
                        text="+ Add",
                        command=lambda: begin_multi_bind_capture({"owner": "macro", "macro_id": selected_macro["id"], "index": len(get_macro_triggers(selected_macro))}),
                        bd=0,
                        relief="flat",
                        cursor="hand2",
                        padx=10,
                        pady=5
                    )
                    style_modern_button(add_macro_button, "primary", compact=True)
                    add_macro_button.pack(side="right", padx=(8, 0))

                selected_macro_bindings = get_macro_triggers(selected_macro)
                macro_row_count = max(1, len(selected_macro_bindings))
                if multi_bind_capture_target and multi_bind_capture_target.get("owner") == "macro" and multi_bind_capture_target.get("macro_id") == selected_macro["id"]:
                    macro_row_count = max(macro_row_count, multi_bind_capture_target.get("index", 0) + 1)

                for index in range(macro_row_count):
                    binding = selected_macro_bindings[index] if index < len(selected_macro_bindings) else None
                    capturing = multi_bind_capture_target == {"owner": "macro", "macro_id": selected_macro["id"], "index": index}
                    row_bg = blend(theme["section_frame_bg"], macro_card_bg, 0.20)
                    row = tk.Frame(macro_rows, bg=row_bg, bd=0, highlightthickness=1, highlightbackground=blend(theme["entry_border"], theme["entry_focus"], 0.10))
                    row.pack(fill="x", pady=(0, 8))

                    tk.Label(row, text=f"{index + 1:02d}", width=4, bg=row_bg, fg=theme["secondary_fg"], font=("Segoe UI", 9, "bold")).pack(side="left", padx=(10, 4), pady=9)
                    tk.Label(
                        row,
                        text="Press a key or mouse button..." if capturing else format_macro_binding_compact_text(binding),
                        bg=row_bg,
                        fg=theme["label_fg"] if binding or capturing else theme["secondary_fg"],
                        font=("Segoe UI", 9),
                        anchor="w"
                    ).pack(side="left", fill="x", expand=True, padx=(0, 8))

                    set_button = tk.Button(row, text="Set", command=lambda current=index, macro_id=selected_macro["id"]: begin_multi_bind_capture({"owner": "macro", "macro_id": macro_id, "index": current}), bd=0, relief="flat", cursor="hand2", padx=10, pady=5)
                    style_modern_button(set_button, "primary", compact=True)
                    set_button.pack(side="right", padx=(0, 8), pady=6)

                    remove_button = tk.Button(
                        row,
                        text="Remove" if index > 0 else "Clear",
                        command=lambda current=index, macro_obj=selected_macro: (remove_macro_trigger_at(macro_obj, current), save_settings(), render_macro_list(), render_macro_editor(), render_mods_page(), log(f"Macro keybind removed: {macro_obj['name']}")),
                        bd=0,
                        relief="flat",
                        cursor="hand2",
                        padx=10,
                        pady=5
                    )
                    style_modern_button(remove_button, "secondary", compact=True)
                    remove_button.pack(side="right", padx=(0, 8), pady=6)
            else:
                tk.Label(
                    macro_rows,
                    text="Create a macro to manage extra triggers here.",
                    bg=macro_card_bg,
                    fg=theme["secondary_fg"],
                    font=("Segoe UI", 9),
                    anchor="w"
                ).pack(fill="x", pady=(4, 0))

            root.after_idle(refresh_pages_scrollregion)

        overview_settings_cards = {}
        overview_stats_cards = {}

        def create_overview_info_card(parent, store, key, title_text, detail_text, row, column):
            theme = get_theme()
            shadow = tk.Frame(parent, bd=0, highlightthickness=0, bg=blend(theme.get("panel_shadow", theme["button_shadow"]), theme["window_bg"], 0.30))
            shadow.grid(row=row, column=column, sticky="nsew", padx=6, pady=6)

            card_shell = tk.Frame(shadow, bd=0, highlightthickness=1, padx=14, pady=12)
            card_shell.pack(fill="both", expand=True, padx=(0, 8), pady=(0, 8))

            body = tk.Frame(card_shell, bd=0)
            body.pack(fill="both", expand=True)

            title_label = tk.Label(
                body,
                text=title_text,
                font=("Segoe UI", 8, "bold"),
                anchor="w"
            )
            title_label.pack(anchor="w")

            value_label = tk.Label(
                body,
                text="—",
                font=("Segoe UI", 13, "bold"),
                anchor="w"
            )
            value_label.pack(anchor="w", pady=(4, 2))

            detail_label = tk.Label(
                body,
                text=detail_text,
                font=("Segoe UI", 9),
                justify="left",
                wraplength=240,
                anchor="w"
            )
            detail_label.pack(anchor="w", fill="x")

            store[key] = {
                "shadow": shadow,
                "shell": card_shell,
                "body": body,
                "title": title_label,
                "value": value_label,
                "detail": detail_label
            }

        overview_settings_frame = section("Current Settings", overview_page)
        overview_settings_grid = tk.Frame(overview_settings_frame, bg=get_theme()["section_frame_bg"])
        overview_settings_grid.pack(fill="x")
        overview_settings_grid.grid_columnconfigure(0, weight=1)
        overview_settings_grid.grid_columnconfigure(1, weight=1)

        create_overview_info_card(overview_settings_grid, overview_settings_cards, "mode", "MODE", "How the autoclicker starts and stops from your keybind.", 0, 0)
        create_overview_info_card(overview_settings_grid, overview_settings_cards, "cps", "TARGET CPS", "The requested click rate before safety limits are applied.", 0, 1)
        create_overview_info_card(overview_settings_grid, overview_settings_cards, "profile", "CLICK PROFILE", "Selected mouse button and multi-click count used for each cycle.", 1, 0)
        create_overview_info_card(overview_settings_grid, overview_settings_cards, "keybind", "KEYBIND", "The current keyboard or mouse trigger assigned to the autoclicker.", 1, 1)
        create_overview_info_card(overview_settings_grid, overview_settings_cards, "theme", "THEME", "The active interface preset applied across the app.", 2, 0)
        create_overview_info_card(overview_settings_grid, overview_settings_cards, "advanced", "ADVANCED SETTINGS", "Controls whether extra tuning options are visible in the main tab.", 2, 1)
        create_overview_info_card(overview_settings_grid, overview_settings_cards, "duty", "CYCLE DUTY", "Controls how long each click is held during a cycle.", 3, 0)
        create_overview_info_card(overview_settings_grid, overview_settings_cards, "jitter", "CPS JITTER", "Adds random variation to the target CPS for less uniform timing.", 3, 1)
        create_overview_info_card(overview_settings_grid, overview_settings_cards, "sound_feedback", "SOUND FEEDBACK", "Whether audible feedback is enabled for success and error notifications.", 4, 0)
        create_overview_info_card(overview_settings_grid, overview_settings_cards, "macro_preview", "MACRO PREVIEW", "Shows a quick active macro summary in the Overview page.", 4, 1)

        overview_stats_frame = section("Detailed Statistics", overview_page)
        overview_stats_grid = tk.Frame(overview_stats_frame, bg=get_theme()["section_frame_bg"])
        overview_stats_grid.pack(fill="x")
        overview_stats_grid.grid_columnconfigure(0, weight=1)
        overview_stats_grid.grid_columnconfigure(1, weight=1)

        create_overview_info_card(overview_stats_grid, overview_stats_cards, "runtime", "SESSION RUNTIME", "How long this app session has been active.", 0, 0)
        create_overview_info_card(overview_stats_grid, overview_stats_cards, "session_clicks", "SESSION CLICKS", "Total registered clicks sent by the autoclicker this session.", 0, 1)
        create_overview_info_card(overview_stats_grid, overview_stats_cards, "average_cps", "AVERAGE CPS", "Average clicks per second across the whole session so far.", 1, 0)
        create_overview_info_card(overview_stats_grid, overview_stats_cards, "estimated_interval", "ESTIMATED INTERVAL", "The current cycle timing after CPS and safety timing are combined.", 1, 1)
        create_overview_info_card(overview_stats_grid, overview_stats_cards, "minimum_interval", "MINIMUM SAFE INTERVAL", "Lowest interval allowed for the selected click profile.", 2, 0)
        create_overview_info_card(overview_stats_grid, overview_stats_cards, "configured_macros", "CONFIGURED MACROS", "Total number of macros currently stored in settings.", 2, 1)
        create_overview_info_card(overview_stats_grid, overview_stats_cards, "enabled_macros", "ENABLED MACROS", "How many stored macros are currently ready to run.", 3, 0)
        create_overview_info_card(overview_stats_grid, overview_stats_cards, "active_triggers", "ACTIVE TRIGGERS", "Macro triggers that are currently being held or processed.", 3, 1)
        create_overview_info_card(overview_stats_grid, overview_stats_cards, "macro_steps", "TOTAL MACRO STEPS", "Combined number of saved actions across every macro.", 4, 0)
        create_overview_info_card(overview_stats_grid, overview_stats_cards, "settings_file", "SETTINGS FILE", "Where your current profile is being saved on disk.", 4, 1)

        overview_log_frame = section("Audit Log", overview_page, expand=True)
        overview_log_frame.configure(height=300)
        overview_log_frame.pack_propagate(False)

        overview_log_scrollbar = ttk.Scrollbar(overview_log_frame, orient="vertical", style="Clean.Vertical.TScrollbar")
        overview_log_box = tk.Text(
            overview_log_frame,
            height=16,
            bg=get_theme()["log_bg"],
            fg=get_theme()["log_fg"],
            bd=0,
            state="disabled",
            font=("Consolas", 10, "bold"),
            insertbackground=get_theme()["entry_insert"],
            relief="flat",
            selectbackground=get_theme()["log_select_bg"],
            selectforeground=get_theme()["log_fg"],
            highlightthickness=1,
            highlightbackground=get_theme()["log_border"],
            highlightcolor=get_theme()["entry_focus"],
            yscrollcommand=overview_log_scrollbar.set
        )
        overview_log_box.pack(side="left", fill="both", expand=True)
        overview_log_scrollbar.pack(side="right", fill="y", padx=(10, 0))
        overview_log_scrollbar.configure(command=overview_log_box.yview)
        style_text_widget(overview_log_box)

        def on_overview_log_mousewheel(event):
            steps = mousewheel_steps(event)
            if steps:
                overview_log_box.yview_scroll(steps, "units")
                return "break"

        overview_log_box.bind("<MouseWheel>", on_overview_log_mousewheel)
        overview_log_box.bind("<Button-4>", on_overview_log_mousewheel)
        overview_log_box.bind("<Button-5>", on_overview_log_mousewheel)

        def prompt_for_macro_name(title_text, initial_value=""):
            name = simpledialog.askstring(title_text, "Enter a macro name:", initialvalue=initial_value, parent=root)
            if name is None:
                return None
            name = name.strip()
            if not name:
                log("❌ Macro name cannot be empty")
                return None
            return name

        def create_macro_prompt():
            nonlocal next_macro_id, current_macro_id
            macro_name = prompt_for_macro_name("Create Macro")
            if not macro_name:
                return
            macro = {
                "id": next_macro_id,
                "name": macro_name,
                "enabled": False,
                "trigger": None,
                "triggers": [],
                "trigger_mode": "Click",
                "sequence": []
            }
            macros.append(macro)
            current_macro_id = macro["id"]
            next_macro_id += 1
            save_settings()
            render_macro_list()
            render_macro_editor()
            render_mods_page()
            log(f"✔ Macro created: {macro_name}")

        macro_create_button = tk.Button(
            macro_list_actions,
            text="+ New",
            command=create_macro_prompt,
            bd=0,
            relief="flat",
            cursor="hand2",
            font=("Segoe UI", 9, "bold"),
            padx=12,
            pady=5,
            anchor="center"
        )
        style_modern_button(macro_create_button, "primary", compact=True)
        macro_create_button.pack(side="right")

        def rename_macro_prompt(macro_id):
            macro = get_macro_by_id(macro_id)
            if not macro:
                return
            new_name = prompt_for_macro_name("Rename Macro", macro["name"])
            if not new_name or new_name == macro["name"]:
                return
            old_name = macro["name"]
            macro["name"] = new_name
            save_settings()
            render_macro_list()
            render_macro_editor()
            render_mods_page()
            log(f"Macro renamed: {old_name} -> {new_name}")

        def delete_macro_confirmed(macro_id):
            nonlocal current_macro_id
            macro = get_macro_by_id(macro_id)
            if not macro:
                return
            stop_macro_execution(macro_id)
            active_macro_triggers.discard(macro_id)
            macros.remove(macro)
            if current_macro_id == macro_id:
                current_macro_id = macros[0]["id"] if macros else None
            save_settings()
            render_macro_list()
            render_macro_editor()
            render_mods_page()
            log(f"Macro deleted: {macro['name']}")

        def show_delete_macro_popup(macro_id):
            macro = get_macro_by_id(macro_id)
            if not macro:
                return
            theme = get_theme()
            popup = tk.Toplevel(root)
            popup.title("Delete Macro")
            popup.geometry("360x180")
            popup.resizable(False, False)
            popup.transient(root)
            popup.grab_set()
            popup.configure(bg=theme["popup_bg"])

            card_frame = tk.Frame(
                popup,
                bg=theme["popup_bg"],
                bd=0,
                highlightthickness=1,
                highlightbackground=theme["popup_border"]
            )
            card_frame.pack(fill="both", expand=True, padx=12, pady=12)

            tk.Label(
                card_frame,
                text="Delete this macro?",
                font=("Segoe UI", 12, "bold"),
                bg=theme["popup_bg"],
                fg=theme["popup_title_fg"]
            ).pack(anchor="w", padx=14, pady=(14, 8))

            tk.Label(
                card_frame,
                text="This permanently removes the macro, its trigger, and every event saved inside it.",
                font=("Segoe UI", 9),
                bg=theme["popup_bg"],
                fg=theme["popup_text_fg"],
                justify="left",
                wraplength=320,
                anchor="w"
            ).pack(fill="x", padx=14)

            buttons = tk.Frame(card_frame, bg=theme["popup_bg"])
            buttons.pack(fill="x", padx=14, pady=(18, 14))

            no_button = tk.Button(
                buttons,
                text="No",
                command=popup.destroy,
                bd=0,
                relief="flat",
                cursor="hand2",
                padx=12,
                pady=6,
                bg=theme["close_bg"],
                fg=theme["close_fg"],
                activebackground=theme["close_active_bg"],
                activeforeground=theme["close_fg"],
                highlightthickness=1,
                highlightbackground=theme["close_border"]
            )
            style_modern_button(no_button, "secondary")
            no_button.pack(side="right", padx=(8, 0))

            yes_button = tk.Button(
                buttons,
                text="Yes",
                command=lambda: (popup.destroy(), delete_macro_confirmed(macro_id)),
                bd=0,
                relief="flat",
                cursor="hand2",
                padx=12,
                pady=6,
                bg=theme["button_body"],
                fg=theme["button_label"],
                activebackground=theme["button_body_hover"],
                activeforeground=theme["button_label"],
                highlightthickness=1,
                highlightbackground=theme["button_outline"]
            )
            style_modern_button(yes_button, "primary")
            yes_button.pack(side="right")

        def edit_macro(macro_id):
            nonlocal current_macro_id
            if not get_macro_by_id(macro_id):
                return
            current_macro_id = macro_id
            render_macro_list()
            render_macro_editor()
            render_mods_page()

        def show_macro_context_menu(event, macro_id):
            theme = get_theme()
            menu = tk.Menu(
                root,
                tearoff=0,
                bg=theme["popup_bg"],
                fg=theme["popup_title_fg"],
                activebackground=theme["button_body_hover"],
                activeforeground=theme["button_label"],
                bd=0,
                relief="flat"
            )
            menu.add_command(label="Rename", command=lambda: rename_macro_prompt(macro_id))
            menu.add_command(label="Edit", command=lambda: edit_macro(macro_id))
            menu.add_command(label="Delete", command=lambda: show_delete_macro_popup(macro_id))
            try:
                menu.tk_popup(event.x_root, event.y_root)
            finally:
                menu.grab_release()

        def render_macro_list():
            theme = get_theme()
            for child in macro_list_view.winfo_children():
                child.destroy()

            if not macros:
                empty_label = tk.Label(
                    macro_list_view,
                    text="No macros yet.\nCreate one to start building it.",
                    bg=theme["section_frame_bg"],
                    fg=theme["secondary_fg"],
                    justify="left",
                    anchor="nw",
                    font=("Segoe UI", 10)
                )
                empty_label.pack(fill="both", expand=True, anchor="nw")
                bind_macro_list_mousewheel(empty_label)
                refresh_macro_list_scrollregion()
                return

            for macro in macros:
                is_current = macro["id"] == current_macro_id
                row_bg = blend(theme["entry_bg"], theme["section_frame_bg"], 0.18 if is_current else 0.05)
                row_border = theme["entry_focus"] if is_current else theme["entry_border"]
                row = tk.Frame(
                    macro_list_view,
                    bg=row_bg,
                    bd=0,
                    highlightthickness=1,
                    highlightbackground=row_border
                )
                row.pack(fill="x", pady=(0, 10))
                row_body = tk.Frame(row, bg=row_bg)
                row_body.pack(fill="x", padx=2, pady=2)

                name_row = tk.Frame(row_body, bg=row_bg)
                name_row.pack(fill="x", padx=10, pady=(8, 0))

                label = tk.Label(
                    name_row,
                    text=macro["name"],
                    bg=row_bg,
                    fg=theme["label_fg"],
                    anchor="w",
                    padx=0,
                    pady=0,
                    font=("Segoe UI", 10, "bold" if is_current else "normal"),
                    cursor="hand2"
                )
                label.pack(side="left", fill="x", expand=True)

                status_badge = tk.Label(
                    name_row,
                    text=macro_status_symbol(macro),
                    bg=row_bg,
                    fg=theme["success"] if macro.get("enabled") else theme["secondary_fg"],
                    font=("Segoe UI", 11, "bold"),
                    padx=0,
                    pady=0,
                    cursor="hand2"
                )
                status_badge.pack(side="right")

                step_count = len(macro.get("sequence", []))
                detail_text = f"{format_macro_binding_summary(macro).replace('Keybind: ', '')} • {step_count} step{'s' if step_count != 1 else ''} • {macro.get('trigger_mode', 'Click')}"
                detail_label = tk.Label(
                    row_body,
                    text=detail_text,
                    bg=row_bg,
                    fg=theme["secondary_fg"],
                    anchor="w",
                    justify="left",
                    wraplength=186,
                    padx=10,
                    pady=0,
                    font=("Segoe UI", 8)
                )
                detail_label.pack(fill="x", pady=(4, 9))

                hover_bg = blend(theme["button_body"], row_bg, 0.14 if is_current else 0.08)
                hover_border = blend(theme["entry_focus"], row_border, 0.22)

                def set_row_appearance(hovered=False, current=is_current, enabled=macro.get("enabled", False)):
                    active_bg = hover_bg if hovered else row_bg
                    active_border = hover_border if hovered else row_border
                    row.configure(bg=active_bg, highlightbackground=active_border if hovered or not current else row_border)
                    row_body.configure(bg=active_bg)
                    name_row.configure(bg=active_bg)
                    label.configure(bg=active_bg, fg=theme["title_fg"] if hovered or current else theme["label_fg"])
                    status_badge.configure(bg=active_bg, fg=theme["success"] if enabled else theme["secondary_fg"])
                    detail_label.configure(bg=active_bg, fg=theme["secondary_fg"])

                def on_row_enter(_event=None):
                    set_row_appearance(True)

                def on_row_leave(_event=None):
                    set_row_appearance(False)

                def on_left_click(_event, macro_id=macro["id"]):
                    new_state = toggle_macro_enabled_state(macro_id)
                    if new_state is not None:
                        render_macro_list()
                        render_macro_editor()
                        render_mods_page()
                        log(f"Macro {'enabled' if new_state else 'disabled'}: {get_macro_by_id(macro_id)['name']}")

                def on_right_click(evt, macro_id=macro["id"]):
                    show_macro_context_menu(evt, macro_id)

                for widget in (row, row_body, name_row, label, status_badge, detail_label):
                    widget.bind("<Enter>", on_row_enter)
                    widget.bind("<Leave>", on_row_leave)
                    widget.bind("<Button-1>", on_left_click)
                    widget.bind("<Button-3>", on_right_click)
                    bind_macro_list_mousewheel(widget)

                set_row_appearance(False)

            refresh_macro_list_scrollregion()

        def show_macro_event_editor(macro_id, action_index=None):
            macro = get_macro_by_id(macro_id)
            if not macro:
                return
            theme = get_theme()
            existing = None
            if action_index is not None and 0 <= action_index < len(macro["sequence"]):
                existing = macro["sequence"][action_index]

            popup = tk.Toplevel(root)
            popup.title("Macro Event")
            popup.geometry("400x340")
            popup.resizable(False, False)
            popup.transient(root)
            popup.grab_set()
            popup.configure(bg=theme["popup_bg"])

            try:
                root_x = root.winfo_rootx()
                root_y = root.winfo_rooty()
                root_w = root.winfo_width()
                root_h = root.winfo_height()
                popup.geometry(f"400x340+{root_x + max(0, (root_w - 400) // 2)}+{root_y + max(0, (root_h - 340) // 2)}")
            except:
                pass

            frame = tk.Frame(
                popup,
                bg=theme["popup_bg"],
                bd=0,
                highlightthickness=1,
                highlightbackground=theme["popup_border"]
            )
            frame.pack(fill="both", expand=True, padx=12, pady=12)

            tk.Label(
                frame,
                text="Macro Event",
                font=("Segoe UI", 12, "bold"),
                bg=theme["popup_bg"],
                fg=theme["popup_title_fg"]
            ).pack(anchor="w", padx=14, pady=(14, 8))

            form = tk.Frame(frame, bg=theme["popup_bg"])
            form.pack(fill="both", expand=True, padx=14, pady=(0, 12))

            event_type_var = tk.StringVar(value=existing["type"] if existing else "key")
            key_var = tk.StringVar(value=existing["value"] if existing and existing["type"] == "key" else "")
            mouse_var = tk.StringVar(value=existing["value"] if existing and existing["type"] == "mouse" else "Left")
            delay_var = tk.StringVar(value=str(existing["value"]) if existing and existing["type"] == "delay" else "100")
            capture_status = tk.StringVar(value="Use capture or type a key name.")
            capture_state = {"armed": False}

            tk.Label(form, text="Type", bg=theme["popup_bg"], fg=theme["popup_text_fg"], anchor="w").pack(fill="x")
            type_row = tk.Frame(form, bg=theme["popup_bg"])
            type_row.pack(fill="x", pady=(6, 10))
            type_buttons = {}

            def refresh_type_buttons():
                selected_value = event_type_var.get()
                for value, button in type_buttons.items():
                    selected = selected_value == value
                    button.configure(
                        bg=theme["button_body"] if selected else blend(theme["entry_bg"], theme["popup_bg"], 0.14),
                        fg=theme["button_label"] if selected else theme["popup_text_fg"],
                        activebackground=theme["button_body_hover"] if selected else blend(theme["entry_bg"], theme["popup_bg"], 0.22),
                        activeforeground=theme["button_label"] if selected else theme["popup_title_fg"],
                        highlightthickness=1,
                        highlightbackground=theme["button_outline"] if selected else blend(theme["entry_border"], theme["popup_bg"], 0.20),
                        highlightcolor=theme["button_outline"] if selected else blend(theme["entry_border"], theme["popup_bg"], 0.20),
                        relief="flat",
                        bd=0,
                        cursor="hand2",
                        padx=12,
                        pady=6,
                        font=("Segoe UI", 9, "bold")
                    )

            def select_event_type(value):
                event_type_var.set(value)
                refresh_event_sections()

            for value, title_text in (("key", "Key"), ("mouse", "Mouse"), ("delay", "Delay")):
                button = tk.Button(
                    type_row,
                    text=title_text,
                    command=lambda current=value: select_event_type(current),
                    bd=0,
                    relief="flat"
                )
                button.pack(side="left", padx=(0, 12))
                type_buttons[value] = button

            key_section = tk.Frame(form, bg=theme["popup_bg"])
            tk.Label(key_section, text="Keyboard key", bg=theme["popup_bg"], fg=theme["popup_text_fg"], anchor="w").pack(fill="x")
            key_entry = tk.Entry(
                key_section,
                textvariable=key_var,
                bg=theme["entry_bg"],
                fg=theme["entry_fg"],
                insertbackground=theme["entry_insert"],
                bd=0,
                relief="flat",
                highlightthickness=1,
                highlightbackground=theme["entry_border"],
                highlightcolor=theme["entry_focus"]
            )
            key_entry.pack(fill="x", pady=(6, 6))
            style_entry_widget(key_entry, "popup_bg")

            def arm_key_capture():
                capture_state["armed"] = True
                capture_status.set("Press any key now...")
                popup.focus_force()

            tk.Button(
                key_section,
                text="Capture Key",
                command=arm_key_capture,
                bd=0,
                relief="flat",
                cursor="hand2",
                bg=theme["button_body"],
                fg=theme["button_label"],
                activebackground=theme["button_body_hover"],
                activeforeground=theme["button_label"],
                padx=10,
                pady=5
            ).pack(anchor="w")
            tk.Label(key_section, textvariable=capture_status, bg=theme["popup_bg"], fg=theme["secondary_fg"], anchor="w").pack(fill="x", pady=(6, 0))

            def on_popup_keypress(event):
                if not capture_state["armed"]:
                    return
                capture_state["armed"] = False
                captured = getattr(event, "char", None)
                if not isinstance(captured, str) or not captured.strip():
                    captured = event.keysym or ""
                captured = normalize_keyboard_action_name(captured).lower().strip()
                if not captured:
                    return "break"
                key_var.set(captured)
                capture_status.set(f"Captured: {captured.upper()}")
                return "break"

            popup.bind("<KeyPress>", on_popup_keypress)

            mouse_section = tk.Frame(form, bg=theme["popup_bg"])
            tk.Label(mouse_section, text="Mouse button", bg=theme["popup_bg"], fg=theme["popup_text_fg"], anchor="w").pack(fill="x")
            mouse_menu = ttk.Combobox(
                mouse_section,
                textvariable=mouse_var,
                values=["Left", "Right", "Middle"],
                state="readonly",
                style="Clean.TCombobox"
            )
            mouse_menu.pack(fill="x", pady=(6, 0))
            block_combobox_mousewheel(mouse_menu)

            delay_section = tk.Frame(form, bg=theme["popup_bg"])
            tk.Label(delay_section, text="Delay in milliseconds", bg=theme["popup_bg"], fg=theme["popup_text_fg"], anchor="w").pack(fill="x")
            delay_entry = tk.Entry(
                delay_section,
                textvariable=delay_var,
                bg=theme["entry_bg"],
                fg=theme["entry_fg"],
                insertbackground=theme["entry_insert"],
                bd=0,
                relief="flat",
                highlightthickness=1,
                highlightbackground=theme["entry_border"],
                highlightcolor=theme["entry_focus"]
            )
            delay_entry.pack(fill="x", pady=(6, 0))
            style_entry_widget(delay_entry, "popup_bg")

            def refresh_event_sections(*_args):
                key_section.pack_forget()
                mouse_section.pack_forget()
                delay_section.pack_forget()
                refresh_type_buttons()
                if event_type_var.get() == "key":
                    key_section.pack(fill="x", pady=(0, 10))
                elif event_type_var.get() == "mouse":
                    mouse_section.pack(fill="x", pady=(0, 10))
                else:
                    delay_section.pack(fill="x", pady=(0, 10))

            event_type_var.trace_add("write", refresh_event_sections)
            refresh_event_sections()

            buttons = tk.Frame(frame, bg=theme["popup_bg"])
            buttons.pack(fill="x", side="bottom", padx=14, pady=(0, 14))

            def save_event():
                event_type = event_type_var.get()
                if event_type == "key":
                    value = key_var.get().strip().lower()
                    if not value:
                        log("❌ Macro key event needs a key")
                        return
                    action = {"type": "key", "value": value}
                elif event_type == "mouse":
                    action = {"type": "mouse", "value": mouse_var.get() if mouse_var.get() in {"Left", "Right", "Middle"} else "Left"}
                else:
                    try:
                        delay_value = max(0, int(float(delay_var.get())))
                    except:
                        log("❌ Delay must be a number")
                        return
                    action = {"type": "delay", "value": delay_value}

                if action_index is None:
                    macro["sequence"].append(action)
                    log(f"✔ Added event to {macro['name']}")
                else:
                    macro["sequence"][action_index] = action
                    log(f"✔ Updated event in {macro['name']}")
                arm_macro_for_use(macro)
                save_settings()
                popup.destroy()
                render_macro_editor()

            cancel_event_button = tk.Button(
                buttons,
                text="Cancel",
                command=popup.destroy,
                bd=0,
                relief="flat",
                cursor="hand2",
                padx=12,
                pady=6,
                bg=theme["close_bg"],
                fg=theme["close_fg"],
                activebackground=theme["close_active_bg"],
                activeforeground=theme["close_fg"],
                highlightthickness=1,
                highlightbackground=theme["close_border"]
            )
            style_modern_button(cancel_event_button, "secondary")
            cancel_event_button.pack(side="right", padx=(8, 0))

            save_event_button = tk.Button(
                buttons,
                text="Save Event",
                command=save_event,
                bd=0,
                relief="flat",
                cursor="hand2",
                padx=12,
                pady=6,
                bg=theme["button_body"],
                fg=theme["button_label"],
                activebackground=theme["button_body_hover"],
                activeforeground=theme["button_label"],
                highlightthickness=1,
                highlightbackground=theme["button_outline"]
            )
            style_modern_button(save_event_button, "primary")
            save_event_button.pack(side="right")

        def render_macro_editor():
            nonlocal macro_trigger_capture_id
            theme = get_theme()
            for child in macro_editor_body.winfo_children():
                child.destroy()

            macro = get_macro_by_id(current_macro_id)
            if not macro:
                tk.Label(
                    macro_editor_body,
                    text="Right-click a macro and choose Edit to open the editor.",
                    bg=theme["section_frame_bg"],
                    fg=theme["secondary_fg"],
                    font=("Segoe UI", 10),
                    justify="left",
                    anchor="nw"
                ).pack(fill="both", expand=True, anchor="nw")
                return

            split = tk.Frame(macro_editor_body, bg=theme["section_frame_bg"])
            split.pack(fill="both", expand=True)

            left = tk.Frame(split, bg=theme["section_frame_bg"], width=210)
            left.pack(side="left", fill="y", padx=(0, 14))
            left.pack_propagate(False)

            right = tk.Frame(split, bg=theme["section_frame_bg"])
            right.pack(side="left", fill="both", expand=True)

            tk.Label(left, text=macro["name"], bg=theme["section_frame_bg"], fg=theme["section_title_fg"], font=("Segoe UI", 12, "bold"), anchor="w").pack(fill="x")
            tk.Label(left, text=f"Status: {'Enabled' if macro['enabled'] else 'Disabled'} {macro_status_symbol(macro)}", bg=theme["section_frame_bg"], fg=theme["secondary_fg"], anchor="w").pack(fill="x", pady=(6, 14))

            trigger_text = "Waiting for a key or mouse button..." if macro_trigger_capture_id == macro["id"] else format_macro_binding_text(macro.get("trigger"))
            trigger_text = "Waiting for a key or mouse button..." if macro_trigger_capture_id == macro["id"] else format_macro_binding_summary(macro)
            trigger_label = tk.Label(left, text=trigger_text, bg=theme["section_frame_bg"], fg=theme["label_fg"], anchor="w", justify="left", wraplength=190)
            trigger_label.pack(fill="x")

            def start_trigger_capture():
                nonlocal macro_trigger_capture_id
                macro_trigger_capture_id = macro["id"]
                render_macro_editor()

            def clear_trigger():
                nonlocal macro_trigger_capture_id
                remove_macro_trigger_at(macro, 0)
                macro_trigger_capture_id = None
                save_settings()
                render_macro_editor()
                render_macro_list()
                render_mods_page()
                log(f"Macro keybind cleared: {macro['name']}")

            trigger_buttons = tk.Frame(left, bg=theme["section_frame_bg"])
            trigger_buttons.pack(fill="x", pady=(8, 16))

            set_trigger_button = tk.Button(
                trigger_buttons,
                text="Set Keybind",
                command=start_trigger_capture,
                bd=0,
                relief="flat",
                cursor="hand2",
                bg=theme["button_body"],
                fg=theme["button_label"],
                activebackground=theme["button_body_hover"],
                activeforeground=theme["button_label"],
                padx=8,
                pady=5
            )
            style_modern_button(set_trigger_button, "primary", compact=True)
            set_trigger_button.pack(side="left")

            clear_trigger_button = tk.Button(
                trigger_buttons,
                text="Clear",
                command=clear_trigger,
                bd=0,
                relief="flat",
                cursor="hand2",
                bg=theme["close_bg"],
                fg=theme["close_fg"],
                activebackground=theme["close_active_bg"],
                activeforeground=theme["close_fg"],
                padx=8,
                pady=5
            )
            style_modern_button(clear_trigger_button, "secondary", compact=True)
            clear_trigger_button.pack(side="left", padx=(8, 0))

            tk.Label(left, text="Run mode", bg=theme["section_frame_bg"], fg=theme["label_fg"], anchor="w").pack(fill="x")
            mode_choice = tk.StringVar(value=macro.get("trigger_mode", "Click"))
            mode_box = ttk.Combobox(left, textvariable=mode_choice, values=["Click", "Hold"], state="readonly", style="Clean.TCombobox")
            mode_box.pack(fill="x", pady=(6, 10))
            block_combobox_mousewheel(mode_box)

            tk.Label(
                left,
                text="Click runs the macro once. Hold repeats while the trigger stays pressed and stops mid-cycle when released.",
                bg=theme["section_frame_bg"],
                fg=theme["secondary_fg"],
                justify="left",
                wraplength=190,
                anchor="w"
            ).pack(fill="x")

            def update_mode(_event=None):
                new_mode = mode_choice.get() if mode_choice.get() in {"Click", "Hold"} else "Click"
                if macro["trigger_mode"] == new_mode:
                    return
                macro["trigger_mode"] = new_mode
                save_settings()
                render_mods_page()
                log(f"Macro mode changed: {macro['name']} -> {new_mode}")

            mode_box.bind("<<ComboboxSelected>>", update_mode)

            header_row = tk.Frame(right, bg=theme["section_frame_bg"])
            header_row.pack(fill="x")
            tk.Label(header_row, text="Macro Steps", bg=theme["section_frame_bg"], fg=theme["section_title_fg"], font=("Segoe UI", 11, "bold"), anchor="w").pack(side="left")

            add_step_button = tk.Button(
                header_row,
                text="+ Add",
                command=lambda: show_macro_event_editor(macro["id"]),
                bd=0,
                relief="flat",
                cursor="hand2",
                bg=theme["button_body"],
                fg=theme["button_label"],
                activebackground=theme["button_body_hover"],
                activeforeground=theme["button_label"],
                padx=10,
                pady=5
            )
            style_modern_button(add_step_button, "primary", compact=True)
            add_step_button.pack(side="right")

            steps_wrap = tk.Frame(right, bg=theme["section_frame_bg"])
            steps_wrap.pack(fill="both", expand=True, pady=(10, 10))

            steps_list = tk.Listbox(
                steps_wrap,
                bg=theme["log_bg"],
                fg=theme["log_fg"],
                bd=0,
                relief="flat",
                highlightthickness=1,
                highlightbackground=theme["log_border"],
                highlightcolor=theme["entry_focus"],
                selectbackground=theme["log_select_bg"],
                selectforeground=theme["log_fg"],
                font=("Consolas", 10)
            )
            steps_scroll = ttk.Scrollbar(steps_wrap, orient="vertical", command=steps_list.yview, style="Clean.Vertical.TScrollbar")
            steps_list.configure(yscrollcommand=steps_scroll.set)
            steps_list.pack(side="left", fill="both", expand=True)
            steps_scroll.pack(side="right", fill="y", padx=(8, 0))
            style_listbox_widget(steps_list)

            for index, action in enumerate(macro["sequence"], start=1):
                steps_list.insert(tk.END, f"{index:02d}. {format_macro_action_text(action)}")

            if not macro["sequence"]:
                steps_list.insert(tk.END, "01. No steps yet. Use + Add to build the macro.")

            button_row = tk.Frame(right, bg=theme["section_frame_bg"])
            button_row.pack(fill="x")

            def selected_index():
                selection = steps_list.curselection()
                if not selection or not macro["sequence"]:
                    return None
                return selection[0]

            def edit_selected():
                index = selected_index()
                if index is None:
                    return
                show_macro_event_editor(macro["id"], index)

            def delete_selected():
                index = selected_index()
                if index is None:
                    return
                del macro["sequence"][index]
                save_settings()
                render_macro_editor()
                render_mods_page()
                log(f"Macro step deleted: {macro['name']}")

            def move_selected(direction):
                index = selected_index()
                if index is None:
                    return
                new_index = index + direction
                if new_index < 0 or new_index >= len(macro["sequence"]):
                    return
                macro["sequence"][index], macro["sequence"][new_index] = macro["sequence"][new_index], macro["sequence"][index]
                save_settings()
                render_macro_editor()
                render_mods_page()

            def delete_all_steps():
                if not macro["sequence"]:
                    return
                if not messagebox.askyesno(
                    "Delete All Steps",
                    f"Delete all {len(macro['sequence'])} steps from '{macro['name']}'?"
                ):
                    return
                macro["sequence"].clear()
                save_settings()
                render_macro_editor()
                render_mods_page()
                log(f"All macro steps deleted: {macro['name']}")

            for text_value, command in (
                ("Edit Step", edit_selected),
                ("Delete Step", delete_selected),
                ("Clear All", delete_all_steps),
                ("Move Up", lambda: move_selected(-1)),
                ("Move Down", lambda: move_selected(1))
            ):
                action_button = tk.Button(
                    button_row,
                    text=text_value,
                    command=command,
                    bd=0,
                    relief="flat",
                    cursor="hand2",
                    bg=theme["close_bg"],
                    fg=theme["close_fg"],
                    activebackground=theme["close_active_bg"],
                    activeforeground=theme["close_fg"],
                    padx=10,
                    pady=6
                )
                style_modern_button(action_button, "secondary", compact=True)
                action_button.pack(side="left", padx=(0, 8))

        settings_panel = tk.Frame(workspace, bd=0, highlightthickness=1)
        settings_header = tk.Frame(settings_panel, bd=0)
        settings_header.pack(fill="x", padx=16, pady=(16, 10))

        settings_title = tk.Label(settings_header, text="Settings", font=("Segoe UI", 11, "bold"))
        settings_title.pack(side="left")

        def hide_settings_panel():
            nonlocal settings_visible
            settings_visible = False
            settings_panel.place_forget()

        settings_close_button = tk.Button(
            settings_header,
            text="✕",
            font=("Segoe UI", 10, "bold"),
            bd=0,
            relief="flat",
            cursor="hand2",
            command=hide_settings_panel,
            padx=8,
            pady=2
        )
        style_modern_button(settings_close_button, "subtle", compact=True)
        settings_close_button.pack(side="right")

        settings_body = tk.Frame(settings_panel, bd=0)
        settings_body.pack(fill="both", expand=True, padx=16, pady=(0, 16))

        account_label = tk.Label(settings_body, text="Account", font=("Segoe UI", 10, "bold"), anchor="w")
        account_label.pack(fill="x")

        account_value_label = tk.Label(settings_body, text=current_account_name, font=("Segoe UI", 11), anchor="w", justify="left")
        account_value_label.pack(fill="x", pady=(8, 4))

        account_desc = tk.Label(
            settings_body,
            text="This workspace stays signed in across launches until you explicitly log out.",
            font=("Segoe UI", 9),
            anchor="w",
            justify="left",
            wraplength=240
        )
        account_desc.pack(fill="x", pady=(0, 14))

        theme_label = tk.Label(settings_body, text="Theme", font=("Segoe UI", 10, "bold"), anchor="w")
        theme_label.pack(fill="x")

        theme_var = tk.StringVar(value=theme_name)
        theme_menu = ttk.Combobox(
            settings_body,
            textvariable=theme_var,
            values=["Azure", "Light", "Dark"],
            state="readonly",
            style="Clean.TCombobox"
        )
        theme_menu.pack(fill="x", pady=(8, 8))
        block_combobox_mousewheel(theme_menu)

        theme_desc = tk.Label(settings_body, text="Choose the interface palette and motion styling for the workspace.", font=("Segoe UI", 9), anchor="w", justify="left", wraplength=240)
        theme_desc.pack(fill="x")

        advanced_settings_var = tk.BooleanVar(value=advanced_settings_enabled)

        def toggle_advanced_settings():
            nonlocal advanced_settings_enabled
            new_value = bool(advanced_settings_var.get())
            if new_value == advanced_settings_enabled:
                update_advanced_settings_visibility()
                return
            old_value = advanced_settings_enabled
            advanced_settings_enabled = new_value
            update_advanced_settings_visibility()
            save_settings()
            log(f"Advanced Settings changed: {'ON' if old_value else 'OFF'} -> {'ON' if advanced_settings_enabled else 'OFF'}")

        advanced_settings_check = tk.Checkbutton(
            settings_body,
            text="Advanced Settings",
            variable=advanced_settings_var,
            command=toggle_advanced_settings,
            anchor="w",
            justify="left",
            bd=0,
            relief="flat",
            highlightthickness=0,
            cursor="hand2"
        )
        advanced_settings_check.pack(fill="x", pady=(10, 0))
        style_toggle_control(advanced_settings_check, popup=True)

        def reset_settings_to_defaults():
            nonlocal cps, mode, cycle_duty, cps_jitter, click_button_name, click_repeat_name, toggle_key, theme_name, advanced_settings_enabled, setting_keybind, smart_cycle_enabled, launch_on_startup_enabled, multi_bind_enabled, multi_bind_capture_target, sound_feedback_enabled, macro_preview_enabled, anti_afk_enabled, anti_afk_interval, pause_on_focus_loss_enabled, auto_limiter_enabled, auto_limiter_clicks, break_reminder_enabled, break_reminder_interval, break_reminder_countdown, mouse_jitter_mode, mouse_jitter_hold_active
            set_autoclicker_state(False, "Reset settings")
            setting_keybind = False
            multi_bind_capture_target = None
            cps = default_settings["cps"]
            mode = default_settings["mode"]
            cycle_duty = default_settings["cycle_duty"]
            cps_jitter = default_settings["cps_jitter"]
            click_button_name = default_settings["click_button"]
            click_repeat_name = default_settings["click_repeat"]
            mouse_jitter_mode = default_settings["mouse_jitter_mode"]
            mouse_jitter_hold_active = False
            set_autoclicker_bindings(default_settings["toggle_keys"])
            theme_name = default_settings["theme"]
            advanced_settings_enabled = default_settings["advanced_settings_enabled"]
            smart_cycle_enabled = default_settings["smart_cycle_enabled"]
            multi_bind_enabled = default_settings["multi_bind_enabled"]
            sound_feedback_enabled = default_settings["sound_feedback_enabled"]
            macro_preview_enabled = default_settings["macro_preview_enabled"]
            anti_afk_enabled = default_settings["anti_afk_enabled"]
            anti_afk_interval = default_settings["anti_afk_interval"]
            pause_on_focus_loss_enabled = default_settings["pause_on_focus_loss_enabled"]
            auto_limiter_enabled = default_settings["auto_limiter_enabled"]
            auto_limiter_clicks = default_settings["auto_limiter_clicks"]
            break_reminder_enabled = default_settings["break_reminder_enabled"]
            break_reminder_interval = default_settings["break_reminder_interval"]
            break_reminder_countdown = break_reminder_interval
            set_launch_on_startup(False)
            launch_on_startup_enabled = read_launch_on_startup_state() if os.name == "nt" else default_settings["launch_on_startup_enabled"]

            cps_entry.delete(0, tk.END)
            cps_entry.insert(0, cps)
            cycle_entry.delete(0, tk.END)
            cycle_entry.insert(0, cycle_duty)
            jitter_entry.delete(0, tk.END)
            jitter_entry.insert(0, cps_jitter)
            mode_var.set(mode)
            click_button_var.set(click_button_name)
            click_repeat_var.set(click_repeat_name)
            mouse_jitter_mode_var.set(mouse_jitter_mode)
            theme_var.set(theme_name)
            advanced_settings_var.set(advanced_settings_enabled)
            smart_cycle_var.set(smart_cycle_enabled)
            launch_on_startup_var.set(launch_on_startup_enabled)
            multi_bind_var.set(multi_bind_enabled)
            sound_feedback_var.set(sound_feedback_enabled)
            macro_preview_var.set(macro_preview_enabled)
            anti_afk_var.set(anti_afk_enabled)
            pause_on_focus_loss_var.set(pause_on_focus_loss_enabled)
            auto_limiter_var.set(auto_limiter_enabled)
            break_reminder_var.set(break_reminder_enabled)
            key_label.config(text=format_autoclicker_keybind_text())

            update_advanced_settings_visibility()
            apply_theme()
            save_settings()
            render_macro_list()
            render_macro_editor()
            render_mods_page()
            log("Settings reset to defaults")

        def show_reset_settings_popup():
            theme = get_theme()
            popup = tk.Toplevel(root)
            popup.title("Reset Settings")
            popup.geometry("360x190")
            popup.resizable(False, False)
            popup.transient(root)
            popup.grab_set()
            popup.configure(bg=theme["popup_bg"])

            try:
                root_x = root.winfo_rootx()
                root_y = root.winfo_rooty()
                root_w = root.winfo_width()
                root_h = root.winfo_height()
                popup.geometry(f"360x190+{root_x + max(0, (root_w - 360) // 2)}+{root_y + max(0, (root_h - 190) // 2)}")
            except:
                pass

            popup_card = tk.Frame(
                popup,
                bg=theme["popup_bg"],
                bd=0,
                highlightthickness=1,
                highlightbackground=theme["popup_border"]
            )
            popup_card.pack(fill="both", expand=True, padx=12, pady=12)

            popup_title = tk.Label(
                popup_card,
                text="Are you sure?",
                font=("Segoe UI", 12, "bold"),
                bg=theme["popup_bg"],
                fg=theme["popup_title_fg"]
            )
            popup_title.pack(anchor="w", padx=14, pady=(14, 8))

            popup_text = tk.Label(
                popup_card,
                text="This resets all autoclicker settings, keybinds, theme, and advanced options back to the default first-launch state.",
                font=("Segoe UI", 9),
                bg=theme["popup_bg"],
                fg=theme["popup_text_fg"],
                justify="left",
                wraplength=320,
                anchor="w"
            )
            popup_text.pack(fill="x", padx=14)

            popup_buttons = tk.Frame(popup_card, bg=theme["popup_bg"])
            popup_buttons.pack(fill="x", padx=14, pady=(18, 14))

            def confirm_reset():
                popup.destroy()
                reset_settings_to_defaults()

            cancel_button = tk.Button(
                popup_buttons,
                text="Cancel",
                command=popup.destroy,
                bd=0,
                relief="flat",
                cursor="hand2",
                padx=12,
                pady=6,
                bg=theme["close_bg"],
                fg=theme["close_fg"],
                activebackground=theme["close_active_bg"],
                activeforeground=theme["close_fg"],
                highlightthickness=1,
                highlightbackground=theme["close_border"]
            )
            style_modern_button(cancel_button, "secondary")
            cancel_button.pack(side="right", padx=(8, 0))

            confirm_button = tk.Button(
                popup_buttons,
                text="Reset Settings",
                command=confirm_reset,
                bd=0,
                relief="flat",
                cursor="hand2",
                padx=12,
                pady=6,
                bg=theme["button_body"],
                fg=theme["button_label"],
                activebackground=theme["button_body_hover"],
                activeforeground=theme["button_label"],
                highlightthickness=1,
                highlightbackground=theme["button_outline"]
            )
            style_modern_button(confirm_button, "primary")
            confirm_button.pack(side="right")

            popup.bind("<Escape>", lambda _event: popup.destroy())
            popup.protocol("WM_DELETE_WINDOW", popup.destroy)

        reset_settings_button = tk.Button(
            settings_body,
            text="Reset Settings",
            command=show_reset_settings_popup,
            bd=0,
            relief="flat",
            cursor="hand2",
            padx=10,
            pady=6,
            anchor="center"
        )
        style_modern_button(reset_settings_button, "secondary")
        reset_settings_button.pack(fill="x", pady=(12, 0))

        def logout_current_account():
            nonlocal logout_requested
            if not messagebox.askyesno("Log Out", f"Log out {current_account_name} and return to the account screen?"):
                return
            clear_session_state()
            logout_requested = True
            shutdown_runtime()
            root.destroy()

        logout_button = tk.Button(
            settings_body,
            text="Log Out",
            command=logout_current_account,
            bd=0,
            relief="flat",
            cursor="hand2",
            padx=10,
            pady=6,
            anchor="center"
        )
        style_modern_button(logout_button, "subtle")
        logout_button.pack(fill="x", pady=(12, 0))

        def show_settings_panel():
            nonlocal settings_visible
            settings_visible = True
            settings_panel.place(relx=1.0, x=-26, y=26, width=280, anchor="ne")
            settings_panel.lift()

        def toggle_settings_panel():
            if settings_visible:
                hide_settings_panel()
            else:
                show_settings_panel()

        def apply_theme():
            theme = get_theme()
            sidebar_bg = theme.get("sidebar_bg", theme["tab_wrap_bg"])
            sidebar_border = theme.get("sidebar_border", theme["tab_inactive_border"])
            hero_bg = theme.get("hero_bg", blend(theme["section_frame_bg"], theme["card_bg"], 0.16))
            hero_border = theme.get("hero_border", blend(theme["section_border"], theme["entry_border"], 0.28))
            hero_badge_bg = theme.get("hero_chip", blend(theme["section_accent"], theme["card_bg"], 0.72))
            hero_badge_border = theme.get("hero_chip_border", blend(theme["section_accent"], theme["entry_border"], 0.24))
            hero_badge_fg = theme["title_fg"]
            panel_shadow = theme.get("panel_shadow", theme["button_shadow"])
            status_panel_bg = blend(theme.get("surface_alt", theme["section_frame_bg"]), hero_bg, 0.16)
            status_panel_border = blend(theme["section_border"], theme["entry_border"], 0.30)
            status_card_bg = blend(theme["section_frame_bg"], theme["entry_bg"], 0.18)
            status_card_border = blend(theme["entry_border"], theme["section_border"], 0.36)
            root.configure(bg=theme["window_bg"])
            content.configure(bg=theme["window_bg"])
            card_shell.configure(bg=theme["window_bg"])
            card_shadow.configure(bg=blend(panel_shadow, theme["window_bg"], 0.20))
            card.configure(bg=theme["card_bg"], highlightbackground=theme["card_border"])
            sidebar.configure(bg=sidebar_bg)
            workspace.configure(bg=theme["card_bg"])
            tab_bar_wrap.configure(bg=sidebar_bg)
            sidebar_brand.configure(bg=sidebar_bg)
            sidebar_brand_top.configure(bg=sidebar_bg)
            sidebar_brand_copy.configure(bg=sidebar_bg)
            sidebar_badge.configure(bg=hero_badge_bg, fg=hero_badge_fg, highlightbackground=hero_badge_border, highlightcolor=hero_badge_border)
            sidebar_title.configure(bg=sidebar_bg, fg=theme["title_fg"])
            sidebar_subtitle.configure(bg=sidebar_bg, fg=theme["subtitle_fg"])
            sidebar_section_label.configure(bg=sidebar_bg, fg=theme["secondary_fg"])
            sidebar_footer.configure(bg=sidebar_bg)
            sidebar_footer_label.configure(bg=sidebar_bg, fg=theme["subtitle_fg"])
            tab_bar.configure(bg=sidebar_bg)
            tab_indicator.configure(bg=theme["section_accent"])
            tab_divider.configure(bg=blend(sidebar_border, theme["window_bg"], 0.42))
            header.configure(bg=theme["card_bg"])
            hero_copy.configure(bg=hero_bg, highlightbackground=hero_border)
            header_badge.configure(bg=hero_badge_bg, fg=hero_badge_fg, highlightbackground=hero_badge_border, highlightcolor=hero_badge_border)
            title.configure(bg=hero_bg, fg=theme["title_fg"])
            subtitle.configure(bg=hero_bg, fg=theme["subtitle_fg"])
            hero_caption.configure(bg=hero_bg, fg=theme["secondary_fg"])
            hero_rule.configure(bg=blend(theme["section_accent"], hero_bg, 0.22))
            status_panel.configure(bg=status_panel_bg, highlightbackground=status_panel_border)
            status_panel_title.configure(bg=status_panel_bg, fg=theme["label_fg"])
            status_grid.configure(bg=status_panel_bg)

            status_accents = {
                "state": theme["section_accent"],
                "clicks": theme["success"],
                "profile": theme["button_outline_hover"],
                "rate": theme["value"]
            }
            for key, card_info in status_cards.items():
                card_info["shadow"].configure(bg=blend(panel_shadow, theme["window_bg"], 0.30))
                card_info["shell"].configure(bg=status_card_bg, highlightbackground=status_card_border)
                card_info["accent"].configure(bg=status_accents.get(key, theme["section_accent"]))
                card_info["body"].configure(bg=status_card_bg)
                card_info["title"].configure(bg=status_card_bg, fg=theme["secondary_fg"])
                card_info["value"].configure(bg=status_card_bg, fg=theme["label_fg"])
                card_info["detail"].configure(bg=status_card_bg, fg=theme["secondary_fg"])

            pages_container.configure(bg=theme["card_bg"])
            pages_canvas.configure(bg=theme["card_bg"])
            pages_view.configure(bg=theme["card_bg"])
            autoclicker_page.configure(bg=theme["card_bg"])
            macros_page.configure(bg=theme["card_bg"])
            mods_page.configure(bg=theme["card_bg"])
            overview_page.configure(bg=theme["card_bg"])
            profiles_page.configure(bg=theme["card_bg"])
            scheduler_page.configure(bg=theme["card_bg"])
            toolkit_page.configure(bg=theme["card_bg"])
            macros_workspace.configure(bg=theme["card_bg"])
            mods_cards_frame.configure(bg=theme["section_frame_bg"])
            mods_bindings_frame.configure(bg=theme["section_frame_bg"])
            overview_settings_grid.configure(bg=theme["section_frame_bg"])
            overview_stats_grid.configure(bg=theme["section_frame_bg"])

            style.configure(
                "Clean.TCombobox",
                fieldbackground=theme["combobox_bg"],
                background=theme["combobox_bg"],
                foreground=theme["combobox_fg"],
                bordercolor=theme["entry_focus"],
                lightcolor=theme["combobox_bg"],
                darkcolor=theme["combobox_bg"],
                arrowcolor=theme["combobox_arrow"],
                borderwidth=0,
                relief="flat",
                padding=7
            )
            style.map(
                "Clean.TCombobox",
                fieldbackground=[("readonly", theme["combobox_bg"])],
                background=[("readonly", theme["combobox_bg"])],
                foreground=[("readonly", theme["combobox_fg"])],
                arrowcolor=[("readonly", theme["combobox_arrow"])]
            )
            style.configure(
                "Clean.Vertical.TScrollbar",
                gripcount=0,
                background=theme["scrollbar_thumb"],
                troughcolor=theme["scrollbar_trough"],
                bordercolor=theme["scrollbar_border"],
                arrowcolor=theme["scrollbar_arrow"],
                darkcolor=theme["scrollbar_thumb"],
                lightcolor=theme["scrollbar_thumb"],
                relief="flat",
                borderwidth=1,
                arrowsize=13
            )
            style.map(
                "Clean.Vertical.TScrollbar",
                background=[("active", theme["scrollbar_thumb_active"]), ("pressed", theme["scrollbar_thumb_active"])],
                darkcolor=[("active", theme["scrollbar_thumb_active"]), ("pressed", theme["scrollbar_thumb_active"])],
                lightcolor=[("active", theme["scrollbar_thumb_active"]), ("pressed", theme["scrollbar_thumb_active"])],
                arrowcolor=[("active", theme["scrollbar_arrow"]), ("pressed", theme["scrollbar_arrow"])]
            )

            for section_info in sections:
                section_info["shadow"].configure(bg=blend(panel_shadow, theme["window_bg"], 0.18))
                section_info["shell"].configure(
                    bg=blend(theme["section_shell_bg"], theme["card_bg"], 0.06),
                    highlightbackground=blend(theme["section_border"], theme["section_accent"], 0.20)
                )
                section_info["accent"].configure(bg=theme["section_accent"])
                title_bar_bg = blend(theme["section_title_bar_bg"], theme["section_frame_bg"], 0.10)
                section_info["title_bar"].configure(bg=title_bar_bg)
                section_info["title_label"].configure(bg=title_bar_bg, fg=theme["section_title_fg"])
                section_info["frame"].configure(bg=theme["section_frame_bg"])

            for panel in macro_panels:
                panel["shadow"].configure(bg=blend(panel_shadow, theme["window_bg"], 0.30))
                panel["shell"].configure(bg=theme["section_shell_bg"], highlightbackground=theme["section_border"])
                panel["accent"].configure(bg=theme["section_accent"])
                panel["title_bar"].configure(bg=theme["section_title_bar_bg"])
                panel["title_label"].configure(bg=theme["section_title_bar_bg"], fg=theme["section_title_fg"])
                panel["frame"].configure(bg=theme["section_frame_bg"])

            for label in (cps_label, cycle_label, jitter_label, mode_label, click_button_label, click_repeat_label):
                label.configure(bg=theme["section_frame_bg"], fg=theme["label_fg"])

            key_label.configure(bg=theme["section_frame_bg"], fg=theme["secondary_fg"])
            bind_actions.configure(bg=theme["section_frame_bg"])

            for entry in (cps_entry, cycle_entry, jitter_entry):
                entry.configure(
                    bg=theme["entry_bg"],
                    fg=theme["entry_fg"],
                    insertbackground=theme["entry_insert"],
                    highlightbackground=theme["entry_border"],
                    highlightcolor=theme["entry_focus"]
                )

            log_box.configure(
                bg=theme["log_bg"],
                fg=theme["log_fg"],
                insertbackground=theme["entry_insert"],
                selectbackground=theme["log_select_bg"],
                selectforeground=theme["log_fg"],
                highlightbackground=theme["log_border"],
                highlightcolor=theme["entry_focus"]
            )
            log_box.tag_configure("prompt", foreground=theme["prompt"])
            log_box.tag_configure("success", foreground=theme["success"])
            log_box.tag_configure("error", foreground=theme["error"])
            log_box.tag_configure("keyword", foreground=theme["keyword"])
            log_box.tag_configure("value", foreground=theme["value"])
            log_box.tag_configure("arrow", foreground=theme["arrow"])

            macro_log_box.configure(
                bg=theme["log_bg"],
                fg=theme["log_fg"],
                insertbackground=theme["entry_insert"],
                selectbackground=theme["log_select_bg"],
                selectforeground=theme["log_fg"],
                highlightbackground=theme["log_border"],
                highlightcolor=theme["entry_focus"]
            )
            macro_log_box.tag_configure("prompt", foreground=theme["prompt"])
            macro_log_box.tag_configure("success", foreground=theme["success"])
            macro_log_box.tag_configure("error", foreground=theme["error"])
            macro_log_box.tag_configure("keyword", foreground=theme["keyword"])
            macro_log_box.tag_configure("value", foreground=theme["value"])
            macro_log_box.tag_configure("arrow", foreground=theme["arrow"])

            overview_log_box.configure(
                bg=theme["log_bg"],
                fg=theme["log_fg"],
                insertbackground=theme["entry_insert"],
                selectbackground=theme["log_select_bg"],
                selectforeground=theme["log_fg"],
                highlightbackground=theme["log_border"],
                highlightcolor=theme["entry_focus"]
            )
            overview_log_box.tag_configure("prompt", foreground=theme["prompt"])
            overview_log_box.tag_configure("success", foreground=theme["success"])
            overview_log_box.tag_configure("error", foreground=theme["error"])
            overview_log_box.tag_configure("keyword", foreground=theme["keyword"])
            overview_log_box.tag_configure("value", foreground=theme["value"])
            overview_log_box.tag_configure("arrow", foreground=theme["arrow"])

            overview_card_bg = blend(theme["section_frame_bg"], theme["entry_bg"], 0.16)
            overview_card_border = blend(theme["entry_border"], theme["section_border"], 0.34)
            for card_store in (overview_settings_cards, overview_stats_cards):
                for card_info in card_store.values():
                    card_info["shadow"].configure(bg=blend(panel_shadow, theme["window_bg"], 0.30))
                    card_info["shell"].configure(bg=overview_card_bg, highlightbackground=overview_card_border)
                    card_info["body"].configure(bg=overview_card_bg)
                    card_info["title"].configure(bg=overview_card_bg, fg=theme["secondary_fg"])
                    card_info["value"].configure(bg=overview_card_bg, fg=theme["label_fg"])
                    card_info["detail"].configure(bg=overview_card_bg, fg=theme["secondary_fg"])

            settings_button._refresh_theme()

            settings_panel.configure(bg=theme["popup_bg"], highlightbackground=theme["popup_border"])
            settings_header.configure(bg=theme["popup_bg"])
            settings_body.configure(bg=theme["popup_bg"])
            settings_title.configure(bg=theme["popup_bg"], fg=theme["popup_title_fg"])
            settings_close_button.configure(
                bg=theme["close_bg"],
                fg=theme["close_fg"],
                activebackground=theme["close_active_bg"],
                activeforeground=theme["close_fg"],
                highlightthickness=1,
                highlightbackground=theme["close_border"]
            )
            account_label.configure(bg=theme["popup_bg"], fg=theme["popup_title_fg"])
            account_value_label.configure(bg=theme["popup_bg"], fg=theme["popup_title_fg"])
            account_desc.configure(bg=theme["popup_bg"], fg=theme["popup_text_fg"])
            theme_label.configure(bg=theme["popup_bg"], fg=theme["popup_title_fg"])
            theme_desc.configure(bg=theme["popup_bg"], fg=theme["popup_text_fg"])
            advanced_settings_check.configure(
                bg=theme["popup_bg"],
                fg=theme["popup_text_fg"],
                activebackground=theme["popup_bg"],
                activeforeground=theme["popup_title_fg"],
                selectcolor=theme["popup_bg"]
            )
            reset_settings_button.configure(
                bg=theme["close_bg"],
                fg=theme["close_fg"],
                activebackground=theme["close_active_bg"],
                activeforeground=theme["close_fg"],
                highlightthickness=1,
                highlightbackground=theme["close_border"]
            )
            logout_button.configure(
                bg=theme["close_bg"],
                fg=theme["close_fg"],
                activebackground=theme["close_active_bg"],
                activeforeground=theme["close_fg"],
                highlightthickness=1,
                highlightbackground=theme["close_border"]
            )
            macro_list_actions.configure(bg=theme["section_frame_bg"])
            macro_add_hint.configure(bg=theme["section_frame_bg"], fg=theme["secondary_fg"])
            macro_list_container.configure(bg=theme["section_frame_bg"])
            macro_list_canvas.configure(bg=theme["section_frame_bg"])
            macro_list_view.configure(bg=theme["section_frame_bg"])
            macro_editor_body.configure(bg=theme["section_frame_bg"])
            macro_create_button.configure(
                bg=theme["button_body"],
                fg=theme["button_label"],
                activebackground=theme["button_body_hover"],
                activeforeground=theme["button_label"],
                highlightthickness=1,
                highlightbackground=theme["button_outline"]
            )

            toast_colors = toast_palette(toast_state.get("tone", "info"))
            toast_card.configure(bg=toast_colors["bg"], highlightbackground=toast_colors["border"])
            toast_body.configure(bg=toast_colors["bg"])
            toast_accent.configure(bg=toast_colors["accent"])
            toast_title.configure(bg=toast_colors["bg"], fg=toast_colors["title"], text=toast_state.get("title", "Activity"))
            toast_message.configure(bg=toast_colors["bg"], fg=toast_colors["text"])
            position_toast()

            theme_var.set(theme_name)
            advanced_settings_var.set(advanced_settings_enabled)

            for button in themed_soft_buttons:
                button._refresh_theme()

            alive_buttons = []
            for button in interactive_buttons:
                try:
                    if button.winfo_exists():
                        button._refresh_theme()
                        alive_buttons.append(button)
                except:
                    pass
            interactive_buttons[:] = alive_buttons

            for widget_store in (themed_entries, themed_toggle_widgets, themed_text_views, themed_listboxes):
                alive_widgets = []
                for widget in widget_store:
                    try:
                        if widget.winfo_exists():
                            widget._refresh_theme()
                            alive_widgets.append(widget)
                    except:
                        pass
                widget_store[:] = alive_widgets

            for name in tab_buttons:
                style_tab(name, name == current_tab.get())
            root.after_idle(lambda: position_tab_indicator(False))

            render_macro_list()
            render_macro_editor()
            render_mods_page()

            draw_background()

        def change_theme(event=None):
            nonlocal theme_name
            selected_theme = theme_var.get()
            if selected_theme not in themes:
                return
            if selected_theme == theme_name:
                apply_theme()
                return
            old_theme = theme_name
            theme_name = selected_theme
            apply_theme()
            save_settings()
            log(f"Theme changed: {old_theme} -> {theme_name}")

        theme_menu.bind("<<ComboboxSelected>>", change_theme)

        def log_token_tag(token):
            cleaned = token.strip()
            normalized = re.sub(r"[^a-zA-Z]", "", cleaned).lower()
            numeric = cleaned.rstrip(",:;.!?")

            if "✔" in cleaned or normalized in {"set", "saved", "loaded"}:
                return "success"
            if "❌" in cleaned or normalized in {"cannot", "fatal", "error"}:
                return "error"
            if cleaned == "->":
                return "arrow"
            if normalized in {"mode", "cps", "cycle", "duty", "keybind", "left", "click"}:
                return "keyword"
            if re.fullmatch(r"[-+]?\d+(\.\d+)?%?", numeric):
                return "value"
            return None

        def log(msg):
            for target_log in (log_box, macro_log_box, overview_log_box):
                target_log.configure(state="normal")
                target_log.insert(tk.END, "PS ", "prompt")
                target_log.insert(tk.END, "Zhydra> ", "prompt")

                for token in re.findall(r"\S+|\s+", msg):
                    if token.isspace():
                        target_log.insert(tk.END, token)
                    else:
                        tag = log_token_tag(token)
                        if tag:
                            target_log.insert(tk.END, token, tag)
                        else:
                            target_log.insert(tk.END, token)

                target_log.insert(tk.END, "\n")
                target_log.see(tk.END)
                target_log.configure(state="disabled")

            if sound_feedback_enabled:
                if "✔" in msg:
                    play_feedback_sound(True)
                elif "❌" in msg:
                    play_feedback_sound(False)

            lowered = msg.lower()
            if "❌" in msg or "error" in lowered or "fatal" in lowered or "cannot" in lowered:
                show_toast(msg, "error", "Attention")
            elif "✔" in msg or any(keyword in lowered for keyword in ("enabled", "disabled", "created", "deleted", "renamed", "theme changed", "settings reset", "keybind", "mode changed")):
                show_toast(msg, "success", "Update")
            elif any(keyword in lowered for keyword in ("panic stop", "loaded", "saved", "macro")):
                show_toast(msg, "info", "Activity")

        def format_runtime(seconds):
            total_seconds = max(0, int(seconds))
            hours = total_seconds // 3600
            minutes = (total_seconds % 3600) // 60
            secs = total_seconds % 60
            return f"{hours:02d}:{minutes:02d}:{secs:02d}"

        def update_overview_details():
            runtime_seconds = max(0.0001, time.perf_counter() - session_stats["started_at"])
            button = get_click_button()
            repeat_count = get_click_repeat_count()
            minimum_interval = get_minimum_registered_click_interval(button, repeat_count)
            estimated_interval = max(1.0 / max(0.1, cps), minimum_interval)
            average_cps = session_stats["clicks"] / runtime_seconds
            enabled_macro_count = sum(1 for macro in macros if macro.get("enabled"))
            total_macro_steps = sum(len(macro.get("sequence", [])) for macro in macros)

            overview_settings_cards["mode"]["value"].configure(text=mode)
            overview_settings_cards["cps"]["value"].configure(text=f"{cps:g} CPS")
            overview_settings_cards["profile"]["value"].configure(text=f"{click_button_name} • {click_repeat_name}")
            overview_settings_cards["keybind"]["value"].configure(text=format_autoclicker_keybind_text())
            overview_settings_cards["theme"]["value"].configure(text=theme_name)
            overview_settings_cards["advanced"]["value"].configure(text="Enabled" if advanced_settings_enabled else "Disabled")
            overview_settings_cards["duty"]["value"].configure(text=f"{cycle_duty:g}%")
            overview_settings_cards["jitter"]["value"].configure(text=f"±{cps_jitter:g}%")
            overview_settings_cards["sound_feedback"]["value"].configure(text="Enabled" if sound_feedback_enabled else "Disabled")
            overview_settings_cards["macro_preview"]["value"].configure(text=f"{get_macro_by_id(current_macro_id)['name']} ({len(get_macro_by_id(current_macro_id)['sequence'])} steps)" if macro_preview_enabled and get_macro_by_id(current_macro_id) else ("Enabled" if macro_preview_enabled else "Disabled"))

            overview_stats_cards["runtime"]["value"].configure(text=format_runtime(runtime_seconds))
            overview_stats_cards["session_clicks"]["value"].configure(text=str(session_stats["clicks"]))
            overview_stats_cards["average_cps"]["value"].configure(text=f"{average_cps:.2f}")
            overview_stats_cards["estimated_interval"]["value"].configure(text=f"{estimated_interval * 1000:.2f} ms")
            overview_stats_cards["minimum_interval"]["value"].configure(text=f"{minimum_interval * 1000:.2f} ms")
            overview_stats_cards["configured_macros"]["value"].configure(text=str(len(macros)))
            overview_stats_cards["enabled_macros"]["value"].configure(text=str(enabled_macro_count))
            overview_stats_cards["active_triggers"]["value"].configure(text=str(len(active_macro_triggers)))
            overview_stats_cards["macro_steps"]["value"].configure(text=str(total_macro_steps))
            overview_stats_cards["settings_file"]["value"].configure(text=os.path.basename(settings_file))
            overview_stats_cards["settings_file"]["detail"].configure(text=settings_file)

        def update_status_display():
            theme = get_theme()
            runtime_text = format_runtime(time.perf_counter() - session_stats["started_at"])
            rate_detail = f"Duty {cycle_duty:g}%"
            if cps_jitter > 0:
                rate_detail += f" • ±{cps_jitter:g}% jitter"
            if smart_cycle_enabled:
                rate_detail += " • Smart Cycle"

            status_cards["state"]["value"].configure(
                text="ACTIVE" if autoclicker_active else "IDLE",
                fg=theme["success"] if autoclicker_active else theme["label_fg"]
            )
            status_cards["state"]["detail"].configure(text=f"Session {runtime_text}")
            status_cards["state"]["accent"].configure(bg=theme["success"] if autoclicker_active else theme["section_accent"])

            status_cards["clicks"]["value"].configure(text=f"{session_stats['clicks']}")
            status_cards["clicks"]["detail"].configure(text="Clicks this session")

            status_cards["profile"]["value"].configure(text=f"{click_button_name} • {click_repeat_name}")
            status_cards["profile"]["detail"].configure(text=f"{mode} mode")

            status_cards["rate"]["value"].configure(text=f"{cps:g} CPS")
            status_cards["rate"]["detail"].configure(text=rate_detail)

            if current_tab.get() == "overview":
                update_overview_details()

            if not stop_threads and root.winfo_exists():
                root.after(250, update_status_display)

        apply_theme()
        cps_entry.delete(0, tk.END)
        cps_entry.insert(0, cps)
        cycle_entry.delete(0, tk.END)
        cycle_entry.insert(0, cycle_duty)
        jitter_entry.delete(0, tk.END)
        jitter_entry.insert(0, cps_jitter)
        mode_var.set(mode)
        click_button_var.set(click_button_name)
        click_repeat_var.set(click_repeat_name)
        theme_var.set(theme_name)
        advanced_settings_var.set(advanced_settings_enabled)
        key_label.config(text=format_keybind_text(toggle_key))
        update_advanced_settings_visibility()
        if macros and current_macro_id is None:
            current_macro_id = macros[0]["id"]
        render_macro_list()
        render_macro_editor()
        render_mods_page()
        switch_tab("autoclicker")
        update_status_display()

        root.bind_all("<MouseWheel>", on_app_mousewheel)
        root.bind_all("<Button-4>", on_app_mousewheel)
        root.bind_all("<Button-5>", on_app_mousewheel)

        keyboard_listener = keyboard.Listener(on_press=on_press_key, on_release=on_release_key)
        mouse_listener = mouse.Listener(on_click=on_click_mouse)
        keyboard_listener.start()
        mouse_listener.start()

        runtime_shutdown = {"completed": False}

        def shutdown_runtime():
            nonlocal stop_threads, autoclicker_active, scheduler_job, scheduler_running
            if runtime_shutdown["completed"]:
                return
            runtime_shutdown["completed"] = True
            scheduler_running = False
            if scheduler_job is not None:
                try:
                    root.after_cancel(scheduler_job)
                except:
                    pass
                scheduler_job = None
            save_settings()
            autoclicker_active = False
            stop_threads = True
            autoclicker_wake_event.set()
            glow_state["running"] = False
            for macro in macros:
                stop_macro_execution(macro["id"])
            try:
                keyboard_listener.stop()
            except:
                pass
            try:
                mouse_listener.stop()
            except:
                pass
            if high_resolution_timer_enabled:
                disable_high_resolution_timer()

        def on_close():
            shutdown_runtime()
            root.destroy()

        root.protocol("WM_DELETE_WINDOW", on_close)
        root.mainloop()
        return "logout" if logout_requested else "exit"

    ensure_app_storage()

    def recover_workspace_startup(active_account, error):
        """Keep a failed workspace launch from trapping the user in a crash loop."""
        settings_file = get_account_settings_file(active_account)
        diagnostic_file = os.path.join(APP_STORAGE_DIR, "startup_error.log")
        try:
            with open(diagnostic_file, "w", encoding="utf-8") as file_obj:
                traceback.print_exc(file=file_obj)
                file_obj.write(f"\nAccount: {active_account}\nError: {error!r}\n")
        except Exception:
            pass

        try:
            if os.path.exists(settings_file):
                backup_file = f"{settings_file}.startup-failure-{int(time.time())}.json"
                shutil.move(settings_file, backup_file)
        except Exception:
            pass
        clear_session_state()
        try:
            if tk._default_root is not None and tk._default_root.winfo_exists():
                tk._default_root.destroy()
        except Exception:
            pass
        try:
            messagebox.showerror(
                "Zhydra workspace recovery",
                "Zhydra could not open the saved workspace. Your account is safe, and the saved settings were moved aside so the workspace can start with clean defaults. Please log in again.\n\nDetails were saved in startup_error.log.",
            )
        except Exception:
            pass

    try:
        license_state = load_license_state()
        if license_state["state"] == "uninitialized" and not show_generate_license_screen():
            return
        if load_license_state()["state"] == "generated" and not show_enter_license_screen():
            return

        while True:
            session_state = load_session_state()
            active_account = session_state.get("active_user")
            if active_account and not load_account_profile(active_account):
                clear_session_state()
                active_account = None

            if not active_account:
                active_account = show_auth_screen()
                if not active_account:
                    return

            try:
                run_result = _run(active_account)
            except Exception as error:
                recover_workspace_startup(active_account, error)
                continue
            if run_result != "logout":
                break
    except Exception as e:
        try:
            if high_resolution_timer_enabled and disable_high_resolution_timer_func:
                disable_high_resolution_timer_func()
        except:
            pass
        print("Fatal error:", e)

if __name__ == "__main__":
    main()