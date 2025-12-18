import customtkinter as ctk
from tkinter import filedialog, messagebox
import requests
import hashlib
import os
import psutil
import json
import threading
import time
import shutil
import platform
import subprocess
APP_VERSION = "8.5.0.0"

# import winreg  # Оставляем закомментированным или используем try-except для кроссплатформенности
try:
    import winreg  # Только для Windows
    WINDOWS_OS = True
except ImportError:
    WINDOWS_OS = False

from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
import webbrowser 
import random # Для новогодних элементов

NEW_YEAR_MESSAGES = [
    "🎄 Пусть в новом году ваш ПК будет чистым, а жизнь — яркой!",
    "✨ Новый год — лучшее время сделать резервную копию важных файлов!",
    "🎅 Даже в Новый год не открывайте подозрительные вложения — фишинг не отдыхает.",
    "🧨 Пусть все вирусы остаются только в тестовой песочнице, а не на вашем ПК!",
    "⭐ В новом году — меньше лагов, больше FPS и ноль троянов!"
]

NEW_YEAR_TIPS = [
    "Не ставьте пиратские игры и софт — даже под ёлкой в них часто прячутся трояны.",
    "Перед Новым годом сделайте резервную копию — флешка дешевле, чем потерянные фото и документы.",
    "Не вводите пароли на сайтах, куда пришли по ссылке из письма — откройте сайт вручную через браузер.",
    "Выключайте автозапуск флешек — особенно если вам их 'подарили' в школе или на работе.",
    "Используйте сложные пароли и менеджер паролей — в новом году будет меньше взломанных аккаунтов.",
    "Не отключайте антивирус ради +5 FPS — лучше оптимизируйте систему и автозагрузку.",
    "Обновляйте Windows и программы — старые уязвимости не знают, что наступил Новый год."
]




# --- КОНФИГУРАЦИЯ ---
CONFIG_FILE = "config.json"
HISTORY_FILE = "history.json"
COINS_FILE = "coins.json"
MB_CACHE_FILE = "mb_cache.json"  # cache for MalwareBazaar hash lookups
QUARANTINE_DIR = "Quarantine_Zone"
QUARANTINE_INDEX_FILE = os.path.join(QUARANTINE_DIR, "quarantine_index.json")

if not os.path.exists(QUARANTINE_DIR):
    os.makedirs(QUARANTINE_DIR)

# --- МЕНЕДЖЕРЫ ДАННЫХ ---

class DataManager:
    # Ключи для демонстрации Премиум-доступа
    VALID_PREMIUM_KEYS = [
        "CYBER-SENTINEL-DEMO-001",
        "CYBER-PRO-VIP-2025-ALPHA",
        "DEV-KEY-003-TESTING",
        # НОВАЯ ПАСХАЛКА: Режим Деда Мороза 🎅
        "SANTA-CLAUS-IS-WATCHING-YOU" 
    ]
    
    DEFAULT_SETTINGS = {
        "api_key": "",
        "malwarebazaar": {"api_key": "", "enabled": True, "cache_ttl_hours": 72},
        "whitelist": [],
        "scan": {
            "use_heuristics": True,
            "scan_archives": False,
            "deep_scan": False,
            "vt_max_size_mb": 32,
            "auto_quarantine": False
        },
        "premium": { 
            "active": False,
            "key": "",
            "network_monitor": False,
            "realtime_guard": False,
            "santa_mode": False # Новая настройка
        },
        "gamer": {
            "silent_mode": False,
            "delay_full_scans": True,
            "optimize_notifications": True
        },
        "ui": {
            "theme": "Dark",
            "color": "blue",
            "scale": 1.0,
            "christmas_style": True # Новая настройка для новогоднего стиля
        }
    }

    @staticmethod
    def load_settings():
        default_settings = DataManager.DEFAULT_SETTINGS.copy()

        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r') as f:
                    data = json.load(f)
                    merged_data = default_settings.copy() 
                    
                    for key, value in data.items():
                        if key in merged_data:
                            if isinstance(merged_data[key], dict) and isinstance(value, dict):
                                merged_data[key].update(value)
                            else:
                                merged_data[key] = value
                        # Обработка новых ключей, которых нет в старом конфиге
                        elif key not in merged_data:
                            merged_data[key] = value
                    
                    # Проверка вложенных словарей
                    for sub_key in default_settings:
                        if sub_key in data and isinstance(default_settings[sub_key], dict):
                            for inner_key, inner_value in default_settings[sub_key].items():
                                if inner_key not in data.get(sub_key, {}):
                                    merged_data[sub_key][inner_key] = inner_value
                    
                    return merged_data

            except Exception as e:
                messagebox.showwarning("Ошибка чтения настроек", f"Сброс настроек. Ошибка: {e}")
                return default_settings

        DataManager.save_settings(default_settings)
        return default_settings

    @staticmethod
    def save_settings(data):
        """Save settings to CONFIG_FILE with small rotating backups (best-effort)."""
        try:
            # Backup existing config (keep last 10)
            try:
                if os.path.exists(CONFIG_FILE) and os.path.getsize(CONFIG_FILE) > 5:
                    bdir = "config_backups"
                    os.makedirs(bdir, exist_ok=True)
                    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                    bpath = os.path.join(bdir, f"config_{ts}.json")
                    shutil.copy2(CONFIG_FILE, bpath)
                    # rotate
                    backups = sorted(
                        [os.path.join(bdir, f) for f in os.listdir(bdir) if f.lower().startswith("config_") and f.lower().endswith(".json")],
                        key=lambda x: os.path.getmtime(x),
                        reverse=True
                    )
                    for old in backups[10:]:
                        try:
                            os.remove(old)
                        except Exception:
                            pass
            except Exception:
                pass

            with open(CONFIG_FILE, 'w', encoding="utf-8") as f:
                json.dump(data, f, indent=4, ensure_ascii=False)

            return os.path.exists(CONFIG_FILE) and os.path.getsize(CONFIG_FILE) > 5
        except Exception as e:
            messagebox.showerror("Ошибка Сохранения", f"Ошибка: {e}")
            return False

    @staticmethod
    def load_quarantine_index():
        """Return dict {id: item} stored in QUARANTINE_INDEX_FILE."""
        try:
            if os.path.exists(QUARANTINE_INDEX_FILE):
                with open(QUARANTINE_INDEX_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    return data if isinstance(data, dict) else {}
        except Exception:
            pass
        return {}

    @staticmethod
    def save_quarantine_index(index: dict) -> bool:
        try:
            os.makedirs(QUARANTINE_DIR, exist_ok=True)
            with open(QUARANTINE_INDEX_FILE, "w", encoding="utf-8") as f:
                json.dump(index if isinstance(index, dict) else {}, f, indent=2, ensure_ascii=False)
            return True
        except Exception:
            return False

    @staticmethod
    def add_history(record):
        history = []
        if os.path.exists(HISTORY_FILE):
            try:
                with open(HISTORY_FILE, 'r') as f:
                    history = json.load(f)
            except: pass
        
        record['date'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        history.insert(0, record) 
        
        if len(history) > 100:
            history = history[:100]
            
        with open(HISTORY_FILE, 'w') as f:
            json.dump(history, f, indent=4)
            
    @staticmethod
    def load_history():
        if os.path.exists(HISTORY_FILE):
            try:
                with open(HISTORY_FILE, 'r') as f:
                    return json.load(f)
            except: pass
        return []

    @staticmethod
    def save_whitelist(whitelist_paths):
        settings = DataManager.load_settings()
        settings["whitelist"] = whitelist_paths
        DataManager.save_settings(settings)
        
    @staticmethod
    def load_whitelist():
        return DataManager.load_settings().get("whitelist", [])

    @staticmethod
    def load_mb_cache():
        """Local cache for MalwareBazaar hash lookups to reduce API calls."""
        try:
            if os.path.exists(MB_CACHE_FILE):
                with open(MB_CACHE_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                return data if isinstance(data, dict) else {}
        except Exception:
            pass
        return {}

    @staticmethod
    def save_mb_cache(cache: dict) -> bool:
        try:
            with open(MB_CACHE_FILE, "w", encoding="utf-8") as f:
                json.dump(cache, f, indent=4, ensure_ascii=False)
            return True
        except Exception:
            return False

    # --- СИСТЕМА МОНЕТ (coins.json) ---
    @staticmethod
    def load_coins():
        if os.path.exists(COINS_FILE):
            try:
                with open(COINS_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if isinstance(data, dict):
                    data.setdefault("coins", 0)
                    data.setdefault("last_daily_bonus", "")
                    # Зимние ачивки и счётчик сканирований
                    ach = data.setdefault("winter_achievements", {})
                    if not isinstance(ach, dict):
                        ach = {}
                        data["winter_achievements"] = ach
                    ach.setdefault("first_scan", False)
                    ach.setdefault("ten_scans", False)
                    ach.setdefault("twentyfive_scans", False)
                    data.setdefault("winter_scan_count", 0)
                    # --- KIBER REBORN EVENT DATA ---
                    data.setdefault("reborn_cores", 0)
                    inv = data.setdefault("inventory", {})
                    if not isinstance(inv, dict):
                        inv = {}
                        data["inventory"] = inv
                    inv.setdefault("themes", [])
                    inv.setdefault("badges", [])
                    inv.setdefault("titles", [])
                    inv.setdefault("relics", [])
                    data.setdefault("reborn_teaser_seen", False)
                    # --- 8.5: Reborn Signal Levels / Streak / Mini-game ---
                    data.setdefault("reborn_signal_reward_claimed", False)
                    ss = data.setdefault("scan_streak", {})
                    if not isinstance(ss, dict):
                        ss = {}
                        data["scan_streak"] = ss
                    ss.setdefault("current", 0)
                    ss.setdefault("best", 0)
                    ss.setdefault("last_scan_date", "")
                    sc = data.setdefault("signal_catcher", {})
                    if not isinstance(sc, dict):
                        sc = {}
                        data["signal_catcher"] = sc
                    sc.setdefault("last_play_date", "")
                    sc.setdefault("plays_today", 0)
                    sc.setdefault("best_combo", 0)
                    sc.setdefault("best_score", 0)
                    data.setdefault("reborn_last_reward_popup", "")
                    return data
            except Exception:
                pass
        # Стартовая структура, если файла ещё нет
        return {
            "coins": 0,
            "last_daily_bonus": "",
            "winter_achievements": {
                "first_scan": False,
                "ten_scans": False,
                "twentyfive_scans": False,
            },
            "winter_scan_count": 0,
            # --- KIBER REBORN EVENT DATA ---
            "reborn_cores": 0,
            "inventory": {
                "themes": [],
                "badges": [],
                "titles": [],
                "relics": []
            },
            "reborn_teaser_seen": False,
            # --- 8.5: Reborn Signal Levels / Streak / Mini-game ---
            "reborn_signal_reward_claimed": False,
            "scan_streak": {"current": 0, "best": 0, "last_scan_date": ""},
            "signal_catcher": {"last_play_date": "", "plays_today": 0, "best_combo": 0, "best_score": 0},
            "reborn_last_reward_popup": "",
        }

    @staticmethod
    def save_coins(data):
        try:
            with open(COINS_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
        except Exception:
            pass


# --- ДВИЖОК СКАНЕРА ---

class ScannerEngine:
    SUSPICIOUS_SIGS = [
        # Скриптовые и командные конструкции
        b"powershell", b"wscript.shell", b"cmd.exe",
        b"invoke-expression", b"frombase64string", b"downloadstring", b"webclient",
        # Подозрительные API вызовы
        b"virtualalloc", b"writeprocessmemory", b"createremotethread",
        b"urldownloadtofile", b"getprocaddress", b"loadlibrary",
        # Общие паттерны выполнения кода
        b"eval(", b"execute(", b"run(",
    ]

    def __init__(self, app):
        self.app = app
        self.stop_event = threading.Event()
        # Для Real-time Guard
        self.guard_thread = None
        self.guard_running = False

        # MalwareBazaar cache (hash -> lookup result)
        self.mb_cache = DataManager.load_mb_cache()
        self._mb_auth_warned = False

    # --- REAL-TIME GUARD (PREMIUM) ---
    def start_realtime_guard(self):
        if self.guard_running: return
        self.guard_running = True
        self.guard_thread = threading.Thread(target=self._guard_loop, daemon=True)
        self.guard_thread.start()
        # Новогоднее уведомление
        self.app.after(0, lambda: messagebox.showinfo("🎅 Real-time Guard", "Начинаю следить за Загрузками, как Дед Мороз за хорошими мальчиками и девочками!"))

    def stop_realtime_guard(self):
        self.guard_running = False

    def _guard_loop(self):
        """Мониторинг папки Загрузки"""
        downloads_path = os.path.join(os.path.expanduser('~'), 'Downloads')
        known_files = set(os.listdir(downloads_path)) if os.path.exists(downloads_path) else set()
        
        while self.guard_running:
            try:
                if not os.path.exists(downloads_path):
                    time.sleep(5)
                    continue

                current_files = set(os.listdir(downloads_path))
                new_files = current_files - known_files
                
                if new_files:
                    for f in new_files:
                        full_path = os.path.join(downloads_path, f)
                        if os.path.isfile(full_path):
                            # Сканируем новый файл
                            res = self.scan_file(full_path)
                            # Если угроза - уведомляем через GUI
                            if res and res['status'] in ['infected', 'suspicious']:
                                self.app.after(0, lambda r=res: messagebox.showwarning("🛡️ Real-time Guard", f"Обнаружена угроза в загрузках!\n{os.path.basename(r['file'])}\nПроверьте, не уголек ли это вместо подарка!"))
                
                known_files = current_files
                time.sleep(2)
            except:
                time.sleep(5)
    # ---------------------------------

    def get_hash(self, path):
        sha256 = hashlib.sha256()
        try:
            with open(path, "rb") as f:
                while chunk := f.read(8192):
                    sha256.update(chunk)
            return sha256.hexdigest()
        except: return None

    def _mb_cache_get(self, sha256_hash: str):
        try:
            entry = self.mb_cache.get(sha256_hash)
            if not isinstance(entry, dict):
                return None
            ts = float(entry.get("ts", 0))
            ttl_h = float(self.app.settings.get("malwarebazaar", {}).get("cache_ttl_hours", 72))
            if time.time() - ts <= ttl_h * 3600:
                return entry
        except Exception:
            pass
        return None

    def _mb_cache_put(self, sha256_hash: str, payload: dict):
        try:
            payload = payload if isinstance(payload, dict) else {}
            payload["ts"] = time.time()
            self.mb_cache[sha256_hash] = payload
            # best-effort persist
            DataManager.save_mb_cache(self.mb_cache)
        except Exception:
            pass

    def query_malwarebazaar(self, any_hash: str):
        """
        MalwareBazaar hash lookup (get_info).
        Returns dict:
          - found: bool
          - signature, tags, first_seen, last_seen
          - auth_error (optional): str
        """
        if not any_hash:
            return None

        # cache
        cached = self._mb_cache_get(any_hash)
        if cached is not None:
            return cached

        cfg = self.app.settings.get("malwarebazaar", {})
        api_key = (cfg.get("api_key") or "").strip()
        if not api_key:
            return None

        url = "https://mb-api.abuse.ch/api/v1/"
        headers = {
            "User-Agent": f"CyberSentinel/{APP_VERSION}",
            "Auth-Key": api_key,
        }
        data = {"query": "get_info", "hash": any_hash}

        try:
            r = requests.post(url, data=data, headers=headers, timeout=10)
            # API returns JSON
            js = r.json()
        except Exception:
            return None

        status = (js or {}).get("query_status")
        if status == "ok":
            item = None
            if isinstance(js.get("data"), list) and js["data"]:
                item = js["data"][0]
            elif isinstance(js.get("data"), dict):
                item = js.get("data")
            item = item or {}

            payload = {
                "found": True,
                "signature": item.get("signature") or item.get("malware") or "",
                "tags": item.get("tags") if isinstance(item.get("tags"), list) else [],
                "first_seen": item.get("first_seen") or "",
                "last_seen": item.get("last_seen") or "",
                "sha256_hash": item.get("sha256_hash") or "",
            }
            self._mb_cache_put(any_hash, payload)
            return payload

        if status in ("hash_not_found", "no_results"):
            payload = {"found": False}
            self._mb_cache_put(any_hash, payload)
            return payload

        if status in ("no_api_key", "user_blacklisted"):
            return {"found": False, "auth_error": f"MalwareBazaar: ошибка Auth-Key ({status}). Проверь ключ в Настройках."}

        # other errors: illegal_hash, http_post_expected, etc.
        return {"found": False}

    def check_file_in_whitelist(self, file_path):
        whitelist = self.app.settings.get("whitelist", [])
        # Дополнительная проверка на нормализацию пути
        file_path = os.path.normpath(file_path) 
        if file_path in whitelist:
            return True
        parent_dir = os.path.normpath(os.path.dirname(file_path))
        if parent_dir in whitelist:
            return True
        return False

    def scan_file(self, file_path):
        if self.stop_event.is_set(): return None
        # Проверка на существование файла, особенно важно при многопоточности и работе с временными папками
        if not os.path.exists(file_path) or not os.path.isfile(file_path): return None

        # Пропуск Белого списка
        if self.check_file_in_whitelist(file_path):
            return {"status": "skipped", "file": file_path, "threat": "Whitelist"}

        result = {"file": file_path, "status": "clean", "threat": None}
        
        try:
            # --- Premium flags (used for Online checks) ---
            is_premium = self.app.settings.get("premium", {}).get("active", False)
            is_santa = self.app.settings.get("premium", {}).get("santa_mode", False)
            deep_scan_enabled = (self.app.settings["scan"].get("deep_scan", False) and is_premium) or is_santa

            _, _ext = os.path.splitext(file_path)
            ext0 = _ext.lower()
            file_hash = None

            # 1. Локальная эвристика (усиленная)
            if self.app.settings["scan"]["use_heuristics"]:
                suspicious_reasons = []

                # Тип файла и размер
                try:
                    file_size = os.path.getsize(file_path)
                except Exception:
                    file_size = 0

                _, ext = os.path.splitext(file_path)
                ext = ext.lower()

                # Читаем начало файла (до 128KB) для анализа
                try:
                    with open(file_path, "rb") as f:
                        head = f.read(128 * 1024)
                except Exception as e:
                    head = b""

                content = head.lower()

                # 1.1. Поиск известных подозрительных строк
                for sig in self.SUSPICIOUS_SIGS:
                    try:
                        if sig in content:
                            sig_text = sig.decode("utf-8", errors="ignore")
                            suspicious_reasons.append(f"подозрительная строка: {sig_text}")
                    except Exception:
                        continue

                # 1.2. Исполняемый код внутри неисполняемого расширения
                suspicious_container_exts = [
                    ".txt", ".rtf", ".log", ".jpg", ".jpeg", ".png", ".gif",
                    ".bmp", ".ico", ".pdf", ".doc", ".docx", ".xls", ".xlsx",
                    ".ppt", ".pptx", ".mp3", ".mp4", ".avi", ".mkv", ".zip", ".rar"
                ]
                if ext in suspicious_container_exts and head.startswith(b"MZ"):
                    suspicious_reasons.append("исполняемый заголовок MZ внутри неисполняемого файла")

                # 1.3. Скриптовые файлы с опасными конструкциями
                script_exts = [".vbs", ".vbe", ".js", ".jse", ".wsf", ".hta", ".ps1", ".psm1", ".bat", ".cmd"]
                if ext in script_exts:
                    if b"createobject(" in content or b"wscript.shell" in content:
                        suspicious_reasons.append("скрипт управляет системой через WScript/COM")
                    if b"powershell" in content or b"invoke-expression" in content:
                        suspicious_reasons.append("скрипт дергает PowerShell")
                    if b"downloadstring" in content or b"webclient" in content:
                        suspicious_reasons.append("скрипт скачивает данные из интернета")

                # 1.4. Очень длинные Base64-последовательности (часто скрытый код)
                try:
                    import re as _re
                    text_sample = head.decode("latin-1", errors="ignore")
                    b64_candidates = _re.findall(r"[A-Za-z0-9+/]{80,}={0,2}", text_sample)
                    if b64_candidates:
                        suspicious_reasons.append("обнаружены длинные base64-последовательности (возможен скрытый код)")
                except Exception:
                    pass

                # 1.5. Подозрительные URL/домены в исполняемых/скриптовых файлах
                if ext in script_exts or ext in [".exe", ".dll", ".scr", ".sys"]:
                    if b"http://" in content or b"https://" in content or b"hxxp://" in content:
                        suspicious_reasons.append("обнаружены встроенные URL/ссылки в коде")

                # Если набралось хотя бы одно серьёзное подозрение — помечаем файл
                if suspicious_reasons and result["status"] == "clean":
                    # Чем больше причин, тем убедительнее
                    reason_text = "; ".join(suspicious_reasons[:3])
                    result["status"] = "suspicious"
                    result["threat"] = f"Heuristic: {reason_text}"
            
            # 2. MalwareBazaar (hash база)
            try:
                mb_cfg = self.app.settings.get("malwarebazaar", {})
                mb_enabled = mb_cfg.get("enabled", True)
                mb_key = (mb_cfg.get("api_key") or "").strip()
                mb_exec_exts = {".exe", ".dll", ".scr", ".sys", ".msi", ".com", ".cpl", ".jar", ".apk", ".ps1", ".vbs", ".js", ".jse", ".wsf", ".bat", ".cmd"}
                mb_should_check = mb_enabled and mb_key and (result["status"] == "suspicious" or deep_scan_enabled or ext0 in mb_exec_exts)
                if mb_should_check and result["status"] != "infected":
                    if file_hash is None:
                        file_hash = self.get_hash(file_path)
                    if file_hash:
                        mb_info = self.query_malwarebazaar(file_hash)
                        if mb_info and mb_info.get("found"):
                            sig = (mb_info.get("signature") or "Known malware").strip()
                            tags = mb_info.get("tags") or []
                            tags_txt = f" [{', '.join(tags[:3])}]" if isinstance(tags, list) and tags else ""
                            result["status"] = "infected"
                            result["threat"] = f"MalwareBazaar: {sig}{tags_txt}"
                        elif mb_info and mb_info.get("auth_error") and not self._mb_auth_warned:
                            self._mb_auth_warned = True
                            msg = mb_info.get("auth_error")
                            self.app.after(0, lambda m=msg: messagebox.showerror("MalwareBazaar Ошибка", m))
            except Exception:
                pass

            # 3. VirusTotal (Deep Scan - требует Premium)

            api_key = self.app.settings.get("api_key")
            vt_max_size_bytes = self.app.settings["scan"].get("vt_max_size_mb", 32) * 1024 * 1024

            if api_key and result["status"] != "infected" and (result["status"] == "suspicious" or deep_scan_enabled):
                if os.path.getsize(file_path) > vt_max_size_bytes:
                    if result["status"] == "clean":
                        result["status"] = "skipped"
                        result["threat"] = "VT: File too large"
                    return result
                
                if file_hash is None:
                    file_hash = self.get_hash(file_path)
                if file_hash:
                    # Улучшение: Использование HTTP/2, если возможно (через requests это не всегда прямо, но можно настроить более надежный запрос)
                    url = f"https://www.virustotal.com/api/v3/files/{file_hash}"
                    headers = {"x-apikey": api_key, "User-Agent": "CyberSentinelPro-Xmas/2.0"}
                    try:
                        resp = requests.get(url, headers=headers, timeout=8) # Увеличен таймаут
                        if resp.status_code == 200:
                            stats = resp.json().get('data', {}).get('attributes', {}).get('last_analysis_stats', {})
                            if stats.get('malicious', 0) > 0:
                                result["status"] = "infected"
                                result["threat"] = f"VT Detection ({stats['malicious']}/70)"
                        elif resp.status_code == 404:
                             # Файл не найден на VT (можно пропустить или отправить на загрузку, что выходит за рамки текущего кода)
                             pass
                        elif resp.status_code == 401:
                             # Неверный API-ключ
                             self.app.after(0, lambda: messagebox.showerror("VT Ошибка", "Недействительный VirusTotal API-ключ."))
                    except requests.exceptions.RequestException as req_e: 
                        # Обработка сетевых ошибок
                        if result["status"] == "clean":
                            result["status"] = "skipped"
                            result["threat"] = "VT: Network error"
                    except Exception as e: 
                        if result["status"] == "clean":
                            result["status"] = "skipped"
                            result["threat"] = f"VT: Unknown error ({type(e).__name__})"
            
            # 3. Авто-карантин
            if result["status"] in ["infected", "suspicious"] and self.app.settings["scan"].get("auto_quarantine", False):
                self.quarantine_file(file_path, threat_label=result.get('threat',''), source='auto')
                result["status"] = "quarantined"

        except Exception as e:
            result["status"] = "error"
            result["threat"] = f"Local error: {type(e).__name__}"
        
        if result["status"] != "clean":
            DataManager.add_history(result)
            
        return result

    def quarantine_file(self, path, threat_label: str = "", source: str = "scan"):
        """Move a file to quarantine and record metadata in quarantine_index.json.
        Returns True on success.
        """
        try:
            if not path or not os.path.exists(path) or not os.path.isfile(path):
                return False

            os.makedirs(QUARANTINE_DIR, exist_ok=True)

            # Build a stable id based on sha256 (fallback to timestamp)
            file_hash = None
            try:
                file_hash = self.get_hash(path)
            except Exception:
                file_hash = None

            ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            safe_name = os.path.basename(path)
            # avoid insane filenames
            safe_name = safe_name.replace(":", "_").replace("\\", "_").replace("/", "_")[:180]

            qid = file_hash or f"nohash_{int(time.time())}"
            q_filename = f"{qid}_{int(time.time())}_{safe_name}.locked"
            q_path = os.path.join(QUARANTINE_DIR, q_filename)

            # Move to quarantine (best-effort)
            try:
                shutil.move(path, q_path)
            except Exception:
                # if move fails (cross-device), try copy+remove
                shutil.copy2(path, q_path)
                try:
                    os.remove(path)
                except Exception:
                    pass

            # Record in index
            try:
                index = DataManager.load_quarantine_index()
                index = index if isinstance(index, dict) else {}
                item = {
                    "id": qid,
                    "qfile": q_filename,
                    "qpath": q_path,
                    "original_path": path,
                    "name": safe_name,
                    "sha256": file_hash or "",
                    "ts": ts,
                    "source": source,
                    "threat": (threat_label or "").strip(),
                    "size": os.path.getsize(q_path) if os.path.exists(q_path) else 0,
                }
                # store by unique key (qid + q_filename)
                key = f"{qid}:{q_filename}"
                index[key] = item
                DataManager.save_quarantine_index(index)
            except Exception:
                pass

            return True
        except Exception:
            return False

    def start_scan(self, paths):
        self.stop_event.clear()
        total = len(paths)
        scanned = 0
        detected = 0

        with ThreadPoolExecutor(max_workers=8) as executor:
            # Используем submit + future.result() для более точного контроля
            futures = [executor.submit(self.scan_file, path) for path in paths]
            
            for future in futures:
                if self.stop_event.is_set(): break
                
                try:
                    res = future.result()
                except Exception:
                    res = None # Пропускаем ошибку потока
                    
                scanned += 1
                
                self.app.update_scan_progress(scanned, total, paths[scanned-1], res) # Добавляем имя текущего файла
                
                if res and res["status"] in ["infected", "suspicious", "quarantined"]:
                    detected += 1
        
        self.app.scan_finished(detected)

# --- ГРАФИЧЕСКИЙ ИНТЕРФЕЙС ---

class App(ctk.CTk):
    
    def __init__(self):
        super().__init__()
        self.settings = DataManager.load_settings()
        # Загружаем данные о монетах
        self.coins_data = DataManager.load_coins()
        
        # --- НОВОГОДНИЙ СТИЛЬ ---
        if self.settings["ui"]["christmas_style"]:
            ctk.set_appearance_mode("Dark") # Принудительно Dark для контраста
            # Красно-зеленая тема
            ctk.set_default_color_theme("green") 
            self.christmas_fg_color = "#C0392B" # Ярко-красный
            self.christmas_hover_color = "#E74C3C" # Светло-красный
            self.main_text_color = "#F7F9F9" # Белоснежный
            self.logo_font = ("Impact", 28, "bold")
        else:
            ctk.set_appearance_mode(self.settings["ui"]["theme"])
            ctk.set_default_color_theme(self.settings["ui"]["color"])
            self.christmas_fg_color = None
            self.christmas_hover_color = None
            self.main_text_color = None
            self.logo_font = ("Impact", 24)
        # --- КОНЕЦ НОВОГОДНЕГО СТИЛЯ ---

        self.title(f"🛡️ CYBER SENTINEL PRO v{APP_VERSION} 🎄")
        self.geometry("1100x800")
        
        self.scanner = ScannerEngine(self)

        # Параметры выезжающего бокового меню
        self.sidebar_expanded = False
        self.sidebar_width_collapsed = 6   # узкое состояние у левого края
        self.sidebar_width_expanded = 220  # полноценная ширина меню

        # Запуск Real-time Guard если включен и есть премиум
        if self.settings["premium"]["active"] and self.settings["premium"].get("realtime_guard", False):
            self.scanner.start_realtime_guard()

        self.setup_ui()
        # Включаем логику выезжающего бокового меню по движению мыши
        self.bind("<Motion>", self._on_mouse_move)

        self.monitor_active = True
        self.update_resources()
        
    def setup_ui(self):
        # Удаление старых виджетов
        for widget in self.winfo_children():
            widget.destroy()

        # Боковое меню
        # Колонка 1 — основной контент, растягивается
        self.grid_columnconfigure(1, weight=1)
        # Колонка 0 под боковым меню: по умолчанию ширина 0, меню спрятано
        self.grid_columnconfigure(0, minsize=0)
        self.grid_rowconfigure(0, weight=1)

        # Боковая панель: по умолчанию скрыта и выезжает при наведении мышью на левый край
        self.sidebar = ctk.CTkFrame(self, width=self.sidebar_width_expanded, corner_radius=0, 
                                    fg_color=self.christmas_fg_color if self.settings["ui"]["christmas_style"] else None)
        # Позиционируем панель только при расширении (expand_sidebar)
        # self.sidebar.grid(row=0, column=0, sticky="nsew")
        
        # Логотип
        logo_text = "CYBER\nSENTINEL 🎄" if self.settings["ui"]["christmas_style"] else "CYBER\nSENTINEL"
        self.logo_label = ctk.CTkLabel(self.sidebar, text=logo_text, font=self.logo_font, text_color=self.main_text_color)
        self.logo_label.pack(pady=18)

        # Индикатор монет
        self.coins_label = ctk.CTkLabel(self.sidebar, text=self.get_coins_text(), font=("Arial", 14, "bold"), text_color="#F1C40F")
        self.coins_label.pack(pady=(0, 10))

        # Индикатор REBORN (ядра + сигнал)
        self.reborn_label = ctk.CTkLabel(self.sidebar, text=self.get_reborn_sidebar_text(), font=("Arial", 11, "bold"), text_color="#7D3CFF")
        self.reborn_label.pack(pady=(0, 10))

        # Контейнер с прокруткой для кнопок (чтобы всё помещалось)
        self.sidebar_scroll = ctk.CTkScrollableFrame(self.sidebar, fg_color="transparent", corner_radius=0)
        self.sidebar_scroll.pack(fill="both", expand=True, padx=0, pady=(0, 10))


        is_premium = self.settings.get("premium", {}).get("active", False)
        is_santa = self.settings.get("premium", {}).get("santa_mode", False)
        
        # Специальный цвет для активного премиума
        premium_color = "#F1C40F" if is_premium else None # Золотистый

        # Кнопки меню 
        self.create_sidebar_btn("🏠 Дашборд", self.show_dashboard)
        self.create_sidebar_btn("🔍 Сканер", self.show_scanner)
        self.create_sidebar_btn("💎 Сундуки и монеты", self.show_cases)
        self.create_sidebar_btn("🗂️ Карантин", self.show_quarantine_center)
        self.create_sidebar_btn("📈 REBORN статистика", self.show_reborn_stats)
        self.create_sidebar_btn("🧪 Быстрая проверка файла", self.show_quick_file_scan)
        self.create_sidebar_btn("🎮 Игровой режим / FPS", self.show_gamer_mode)
        
        # Премиум функции (в том же стиле, что и раньше)
        self.whitelist_btn = self.create_sidebar_btn("✅ Белый список", self.show_whitelist_editor, 
                                                     enabled=is_premium, text_color=premium_color if is_premium else "gray")
        self.network_btn = self.create_sidebar_btn("🌐 Мониторинг Сети", self.show_network_monitor, 
                                                    enabled=is_premium, text_color=premium_color if is_premium else "gray")
        
        # Автозагрузка (Premium) - Включаем, если Windows
        startup_enabled = is_premium and WINDOWS_OS
        self.startup_btn = self.create_sidebar_btn("🚀 Автозагрузка", self.show_startup_manager, 
                                                    enabled=startup_enabled, text_color=premium_color if startup_enabled else "gray")

        self.create_sidebar_btn("📜 Журнал", self.show_history)
        self.create_sidebar_btn("💻 Система", self.show_system)
        self.create_sidebar_btn("📊 Диспетчер задач", self.show_task_manager)
        self.create_sidebar_btn("🛑 Экстренная защита", self.show_panic_center)
        
        # НОВАЯ ПАСХАЛКА: Скрытая кнопка-подарок
        if self.settings["ui"]["christmas_style"]:
            ctk.CTkButton(getattr(self, "sidebar_scroll", None) or self.sidebar, text="🎁 ПОДАРОК", command=self.show_christmas_gift,
                          fg_color="#3498db", hover_color="#2980b9", font=("Arial", 14, "bold")).pack(fill="x", padx=10, pady=20)


        # Основной контейнер
        self.main_frame = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        self.main_frame.grid(row=0, column=1, sticky="nsew", padx=20, pady=20)
        
        self.frames = {}
        self.show_dashboard()
        

    def expand_sidebar(self):
        """Разворачивает боковое меню, когда курсор у левого края окна."""
        # если уже раскрыто — ничего не делаем
        if getattr(self, "sidebar_expanded", False):
            return
        self.sidebar_expanded = True
        try:
            # показываем панель и даём ей нормальную ширину
            self.sidebar.grid(row=0, column=0, sticky="nsew")
            self.sidebar.configure(width=self.sidebar_width_expanded)
            # фиксируем ширину колонки под меню
            self.grid_columnconfigure(0, minsize=self.sidebar_width_expanded)
        except Exception:
            pass

    def collapse_sidebar(self):
        """Сворачивает боковое меню, когда курсор уходит вправо."""
        if not getattr(self, "sidebar_expanded", False):
            return
        self.sidebar_expanded = False
        try:
            # убираем панель из сетки и освобождаем место
            self.sidebar.grid_remove()
            self.grid_columnconfigure(0, minsize=0)
        except Exception:
            pass

    def _on_mouse_move(self, event):
        """Отслеживаем положение мыши и автоматически показываем/прячем боковое меню.

        Если курсор у самого левого края окна — меню выезжает.
        Если курсор уходит далеко вправо — меню снова прячется.
        """
        try:
            # абсолютная координата курсора на экране
            x_root = event.x_root
            # положение окна относительно экрана
            win_left = self.winfo_rootx()
            # координата относительно окна
            x_local = x_root - win_left

            # зона слева, при нахождении в которой панель должна быть видна
            show_zone = 4
            # зона справа, после которой панель можно прятать
            hide_zone = self.sidebar_width_expanded + 40
        except Exception:
            return

        # у самого левого края — раскрываем панель
        if x_local <= show_zone:
            self.expand_sidebar()
        # ушли далеко вправо — прячем
        elif x_local > hide_zone:
            self.collapse_sidebar()


    def create_sidebar_btn(self, text, command, enabled=True, text_color=None):
        """Компактная кнопка меню (влезает даже на небольших экранах)."""
        fg_color = "transparent"

        # Hover цвет (если нет christmas_style, оставим дефолтный)
        hover_color = "#3498db" if bool(self.settings.get("ui", {}).get("christmas_style", False)) and enabled else None

        # Куда пакуем кнопки: в прокрутку, если она есть
        try:
            parent = object.__getattribute__(self, "sidebar_scroll")
        except Exception:
            parent = self.sidebar

        kwargs = dict(
            master=parent,
            text=text,
            command=command if enabled else None,
            fg_color=fg_color,
            anchor="w",
            height=24,              # ещё ниже
            font=("Arial", 10, "bold"),
            state="normal" if enabled else "disabled",
        )

        # Цвет текста: только если реально задан
        chosen = text_color
        if chosen is None:
            try:
                chosen = object.__getattribute__(self, "main_text_color")
            except Exception:
                chosen = None
        if chosen:
            kwargs["text_color"] = chosen

        if hover_color:
            kwargs["hover_color"] = hover_color

        btn = ctk.CTkButton(**kwargs)
        btn.pack(fill="x", padx=6, pady=1)
        return btn

    def clear_main(self):
        for widget in self.main_frame.winfo_children():
            widget.destroy()

    def section(self, title, subtitle=""):
        """Универсальный заголовок раздела.
        FIX: безопасно работает даже если в окне нет атрибутов цветов.
        (CustomTkinter/Tk могут прокидывать getattr в tkapp, поэтому берём через object.__getattribute__)
        """
        container = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        container.pack(fill="x", padx=10, pady=(0, 10))

        def _safe_attr(name: str, default=None):
            try:
                return object.__getattribute__(self, name)
            except Exception:
                return default

        # Цвета (если None, CustomTkinter подставит тему)
        title_color = _safe_attr("main_text_color") or _safe_attr("primary_text_color")
        subtitle_color = _safe_attr("secondary_text_color")

        title_kwargs = dict(
            master=container,
            text=title,
            font=("Arial", 22, "bold"),
            anchor="w",
            justify="left",
            wraplength=1100,
        )
        if title_color:
            title_kwargs["text_color"] = title_color
        ctk.CTkLabel(**title_kwargs).pack(fill="x")

        if subtitle:
            sub_kwargs = dict(
                master=container,
                text=subtitle,
                font=("Arial", 14),
                anchor="w",
                justify="left",
                wraplength=1100,
            )
            if subtitle_color:
                sub_kwargs["text_color"] = subtitle_color
            ctk.CTkLabel(**sub_kwargs).pack(fill="x", pady=(4, 0))

        sep_color = _safe_attr("divider_color", "#2A2A2A")
        ctk.CTkFrame(self.main_frame, height=2, fg_color=sep_color).pack(fill="x", padx=10, pady=(0, 10))
        return container

    def open_link(self, url):
        webbrowser.open_new_tab(url)

    # --- НОВАЯ ПАСХАЛКА: ПОДАРОК ---
    def show_christmas_gift(self):
        self.clear_main()
        self.main_frame.grid_columnconfigure(0, weight=1)
        self.main_frame.grid_rowconfigure(0, weight=1)
        
        gift_text = "🎉 С Новым Годом и Рождеством! 🥳\n\nПусть этот год принесет вам только чистые файлы, стабильный интернет и массу положительных эмоций!"
        if self.settings["premium"].get("santa_mode", False):
            gift_text += "\n\nДед Мороз активировал все премиум-функции для вас! Пользуйтесь на здоровье!"
            
        
        ctk.CTkLabel(self.main_frame, text=gift_text,
                     font=("Impact", 30), text_color="#F1C40F", justify="center").pack(pady=100)
        
        ctk.CTkLabel(self.main_frame, text="✨ Ваш CYBER SENTINEL PRO", font=("Arial", 18)).pack(pady=20)
        
    # --- Вкладка: ДАШБОРД ---
    
    # --- KIBER REBORN: HUGE TEASER / SIGNAL ---
    def show_kiber_reborn_signal(self):
        self.clear_main()
        self.main_frame.grid_columnconfigure(0, weight=1)

        # Mark teaser as seen (so you can later unlock something in future updates)
        try:
            if not hasattr(self, "coins_data") or not isinstance(self.coins_data, dict):
                self.coins_data = DataManager.load_coins()
            self.coins_data["reborn_teaser_seen"] = True
            DataManager.save_coins(self.coins_data)
        except Exception:
            pass

        # Dynamic "cipher" hint
        try:
            part_a = random.choice(["RB", "KBR", "REB", "SIG"])
            part_b = random.randint(100, 999)
            part_c = random.choice(["ALPHA", "DELTA", "NEON", "NULL", "ECHO"])
            cipher = f"{part_a}-{part_b}-{part_c}"
        except Exception:
            cipher = "RB-404-NEON"

        # Read cores
        try:
            cores = int(getattr(self, "coins_data", {}).get("reborn_cores", 0))
        except Exception:
            cores = 0

        header = ctk.CTkFrame(self.main_frame, fg_color="#111827")
        header.pack(fill="x", pady=(0, 12))

        ctk.CTkLabel(
            header,
            text="⚡ KIBER REBORN // ШИФР-СИГНАЛ",
            font=("Impact", 28, "bold"),
            text_color="#F1C40F"
        ).pack(anchor="w", padx=14, pady=(14, 0))

        pct = self.get_reborn_signal_percent()
        preview = self.get_reborn_signal_preview_text(pct)
        ctk.CTkLabel(
            header,
            text=f"Код: {cipher}   •   REBORN-ЯДРА: {cores}   •   SIGNAL: {pct}%",
            font=("Arial", 14, "bold"),
            text_color="#E5E7EB"
        ).pack(anchor="w", padx=14, pady=(2, 8))

        ctk.CTkLabel(
            header,
            text=preview,
            font=("Consolas", 13, "bold"),
            text_color="#A78BFA"
        ).pack(anchor="w", padx=14, pady=(0, 8))

        pb = ctk.CTkProgressBar(header)
        pb.pack(fill="x", padx=14, pady=(0, 12))
        try:
            pb.set(pct / 100.0)
        except Exception:
            pb.set(0)

        try:
            self.maybe_claim_reborn_signal_reward(silent=False)
        except Exception:
            pass

        btn_row = ctk.CTkFrame(header, fg_color="transparent")
        btn_row.pack(fill="x", padx=14, pady=(0, 14))
        ctk.CTkButton(btn_row, text="🎯 Signal Catcher", fg_color="#7D3CFF", hover_color="#5B2CFF", command=self.show_signal_catcher).pack(side="left")
        ctk.CTkButton(btn_row, text="🧩 Артефакты", command=self.show_reborn_inventory).pack(side="left", padx=10)
        ctk.CTkButton(btn_row, text="💎 Сундуки", command=self.show_cases).pack(side="right")

        body = ctk.CTkFrame(self.main_frame)
        body.pack(fill="both", expand=True)

        ascii_art = (
            "┌───────────────────────────────────────────┐\n"
            "│   ░░░  S I G N A L   D E T E C T E D  ░░░  │\n"
            "│         K I B E R   R E B O R N            │\n"
            "│   > протокол: REBORN_CORE_SYNC             │\n"
            "│   > статус: ожидание активации             │\n"
            "└───────────────────────────────────────────┘"
        )

        ctk.CTkLabel(
            body,
            text=ascii_art,
            font=("Consolas", 14, "bold"),
            justify="left"
        ).pack(anchor="w", padx=14, pady=(12, 6))

        hint_text = (
            "ОГРОМНЫЙ НАМЁК: это не просто 'ивент'. Это перезапуск стиля и механик.\n\n"
            "Что уже можно сделать ПРЯМО СЕЙЧАС:\n"
            "1) Открывай ивентовый сундук KIBER REBORN — он даёт REBORN-ЯДРА и артефакты\n"
            "2) Делай сканы — некоторые награды будут усиливаться 'сериями'\n"
            "3) Следи за подсказками в интерфейсе — они будут меняться\n\n"
            "Фраза дня: 'Когда ядра стабилизируются — интерфейс проснётся.'"
        )

        ctk.CTkLabel(
            body,
            text=hint_text,
            font=("Arial", 13),
            justify="left",
            wraplength=860
        ).pack(anchor="w", padx=14, pady=(0, 10))

        btns = ctk.CTkFrame(body, fg_color="transparent")
        btns.pack(fill="x", padx=14, pady=(0, 14))

        ctk.CTkButton(btns, text="💎 Перейти к сундукам", command=self.show_cases).pack(side="left")
        ctk.CTkButton(btns, text="🏠 На дашборд", command=self.show_dashboard).pack(side="left", padx=10)


    # --- 8.5: REBORN Inventory ---
    def show_reborn_inventory(self):
        self.clear_main()
        self.ensure_coins_data()
        inv = self.coins_data.get("inventory", {}) if isinstance(self.coins_data, dict) else {}
        themes = inv.get("themes", []) if isinstance(inv, dict) else []
        badges = inv.get("badges", []) if isinstance(inv, dict) else []
        titles = inv.get("titles", []) if isinstance(inv, dict) else []
        relics = inv.get("relics", []) if isinstance(inv, dict) else []

        ctk.CTkLabel(self.main_frame, text="🧩 REBORN Артефакты", font=("Arial", 26, "bold")).pack(anchor="w", pady=(0, 10))
        ctk.CTkLabel(self.main_frame, text="Тут хранятся темы, бейджи, титулы и реликвии, которые ты выбил из сундуков и мини-игр.", text_color="#A78BFA", wraplength=760, justify="left").pack(anchor="w", pady=(0, 15))

        scroll = ctk.CTkScrollableFrame(self.main_frame)
        scroll.pack(fill="both", expand=True)

        def section(title, items):
            ctk.CTkLabel(scroll, text=title, font=("Arial", 16, "bold")).pack(anchor="w", padx=10, pady=(10, 6))
            if not items:
                ctk.CTkLabel(scroll, text="— пусто —", text_color="gray").pack(anchor="w", padx=10)
                return
            for it in items:
                ctk.CTkLabel(scroll, text=f"• {it}", anchor="w", justify="left").pack(anchor="w", padx=14, pady=2)

        section("🌌 Themes", themes)
        section("📛 Badges", badges)
        section("🏷️ Titles", titles)
        section("🧿 Relics", relics)

        ctk.CTkButton(self.main_frame, text="⬅ Назад", command=self.show_dashboard).pack(anchor="w", pady=10)

    # --- 8.5: Mini-game — Signal Catcher ---
    def show_signal_catcher(self):
        self.clear_main()
        self.ensure_coins_data()

        ctk.CTkLabel(self.main_frame, text="🎯 Signal Catcher", font=("Arial", 26, "bold")).pack(anchor="w", pady=(0, 10))
        ctk.CTkLabel(
            self.main_frame,
            text="Нажми CATCH когда бегунок попадает в целевую зону. Чем точнее, тем больше ядер и монет. Есть шанс артефакта.",
            wraplength=760, justify="left", text_color="#A78BFA"
        ).pack(anchor="w", pady=(0, 12))

        # Daily limit
        sc = self.coins_data.setdefault("signal_catcher", {})
        today = datetime.now().strftime("%Y-%m-%d")
        if sc.get("last_play_date", "") != today:
            sc["last_play_date"] = today
            sc["plays_today"] = 0
            DataManager.save_coins(self.coins_data)

        plays = int(sc.get("plays_today", 0))
        self._sc_daily_limit = 20
        self._sc_combo = 0
        self._sc_score = 0

        self._sc_status = ctk.CTkLabel(self.main_frame, text=f"Попытки сегодня: {plays}/{self._sc_daily_limit}    Комбо: 0    Score: 0", font=("Arial", 14, "bold"))
        self._sc_status.pack(anchor="w", pady=(0, 10))

        # Target zone (0..1)
        self._sc_target_center = random.uniform(0.25, 0.75)
        self._sc_target_half = 0.06  # ±6%
        self._sc_speed = 0.018
        self._sc_dir = 1
        self._sc_value = 0.0
        self._sc_running = True

        zone_text = self._format_sc_zone()
        self._sc_zone_label = ctk.CTkLabel(self.main_frame, text=zone_text, font=("Consolas", 13))
        self._sc_zone_label.pack(anchor="w", pady=(0, 8))

        self._sc_bar = ctk.CTkProgressBar(self.main_frame)
        self._sc_bar.pack(fill="x", padx=10, pady=(0, 12))
        self._sc_bar.set(0.0)

        btn_row = ctk.CTkFrame(self.main_frame)
        btn_row.pack(fill="x", pady=(0, 10))

        self._sc_catch_btn = ctk.CTkButton(btn_row, text="CATCH", fg_color="#7D3CFF", hover_color="#5B2CFF", command=self._signal_catcher_catch)
        self._sc_catch_btn.pack(side="left", padx=10, pady=10)

        ctk.CTkButton(btn_row, text="🔁 Новая зона", command=self._signal_catcher_new_zone).pack(side="left", padx=10, pady=10)
        ctk.CTkButton(btn_row, text="🧩 Артефакты", command=self.show_reborn_inventory).pack(side="left", padx=10, pady=10)
        ctk.CTkButton(btn_row, text="⬅ Назад", command=self._signal_catcher_back).pack(side="right", padx=10, pady=10)

        self._sc_feedback = ctk.CTkLabel(self.main_frame, text="Готов? Лови сигнал.", font=("Arial", 14), text_color="#E5E7EB")
        self._sc_feedback.pack(anchor="w", pady=(6, 0))

        self.after(25, self._signal_catcher_tick)

    def _format_sc_zone(self):
        a = max(0.0, self._sc_target_center - self._sc_target_half)
        b = min(1.0, self._sc_target_center + self._sc_target_half)
        return f"TARGET ZONE: {int(a*100)}% .. {int(b*100)}%"

    def _signal_catcher_new_zone(self):
        try:
            self._sc_target_center = random.uniform(0.18, 0.82)
            self._sc_target_half = random.choice([0.05, 0.06, 0.07])
            if hasattr(self, "_sc_zone_label") and self._sc_zone_label.winfo_exists():
                self._sc_zone_label.configure(text=self._format_sc_zone())
        except Exception:
            pass

    def _signal_catcher_tick(self):
        try:
            if not getattr(self, "_sc_running", False):
                return
            v = float(getattr(self, "_sc_value", 0.0))
            d = int(getattr(self, "_sc_dir", 1))
            sp = float(getattr(self, "_sc_speed", 0.018))
            v += sp * d
            if v >= 1.0:
                v = 1.0
                d = -1
            elif v <= 0.0:
                v = 0.0
                d = 1
            self._sc_value = v
            self._sc_dir = d
            if hasattr(self, "_sc_bar") and self._sc_bar.winfo_exists():
                self._sc_bar.set(v)
            self.after(25, self._signal_catcher_tick)
        except Exception:
            pass

    def _signal_catcher_catch(self):
        try:
            self.ensure_coins_data()
            sc = self.coins_data.setdefault("signal_catcher", {})
            today = datetime.now().strftime("%Y-%m-%d")
            if sc.get("last_play_date", "") != today:
                sc["last_play_date"] = today
                sc["plays_today"] = 0

            plays = int(sc.get("plays_today", 0))
            if plays >= getattr(self, "_sc_daily_limit", 20):
                if hasattr(self, "_sc_feedback") and self._sc_feedback.winfo_exists():
                    self._sc_feedback.configure(text="Лимит на сегодня исчерпан. Завтра сигнал снова будет в эфире.", text_color="#F1C40F")
                return

            sc["plays_today"] = plays + 1
            DataManager.save_coins(self.coins_data)

            v = float(getattr(self, "_sc_value", 0.0))
            a = self._sc_target_center - self._sc_target_half
            b = self._sc_target_center + self._sc_target_half

            hit = (v >= a and v <= b)
            # accuracy score: 0..1, 1 is perfect center
            dist = abs(v - self._sc_target_center)
            maxd = max(0.0001, self._sc_target_half)
            acc = max(0.0, 1.0 - (dist / maxd))

            if hit:
                self._sc_combo = int(getattr(self, "_sc_combo", 0)) + 1
                gain_cores = 1 + (1 if acc > 0.75 else 0) + (1 if self._sc_combo >= 3 else 0)
                gain_coins = 8 + int(acc * 20) + min(25, self._sc_combo * 2)
                self.add_reborn_cores(gain_cores)
                self.add_coins(gain_coins)
                self._sc_score += int(10 + acc * 40) + self._sc_combo

                # artifact chance scales with accuracy
                art_ch = 0.05 + (0.07 if acc > 0.80 else 0.0)
                art = None
                if random.random() < art_ch:
                    art = self._grant_random_reborn_artifact()

                msg = f"✅ HIT! Точность: {int(acc*100)}%  →  +{gain_cores} cores, +{gain_coins} coins  (комбо x{self._sc_combo})"
                if art:
                    msg += f"  |  🎁 {art}"
                if hasattr(self, "_sc_feedback") and self._sc_feedback.winfo_exists():
                    self._sc_feedback.configure(text=msg, text_color="#2ECC71")
            else:
                self._sc_combo = 0
                self._sc_score = max(0, int(getattr(self, "_sc_score", 0)) - 3)
                if hasattr(self, "_sc_feedback") and self._sc_feedback.winfo_exists():
                    self._sc_feedback.configure(text="❌ MISS. Сигнал сорвался. Комбо сброшено.", text_color="#E74C3C")

            # update bests
            sc = self.coins_data.setdefault("signal_catcher", {})
            best_combo = int(sc.get("best_combo", 0))
            best_score = int(sc.get("best_score", 0))
            if self._sc_combo > best_combo:
                sc["best_combo"] = self._sc_combo
            if self._sc_score > best_score:
                sc["best_score"] = self._sc_score
            DataManager.save_coins(self.coins_data)

            # refresh status line
            if hasattr(self, "_sc_status") and self._sc_status.winfo_exists():
                plays = int(sc.get("plays_today", 0))
                self._sc_status.configure(
                    text=f"Попытки сегодня: {plays}/{self._sc_daily_limit}    Комбо: {self._sc_combo}    Score: {self._sc_score}    Best: {sc.get('best_score', 0)}"
                )

            # new zone each catch
            self._signal_catcher_new_zone()

            # one-time reward check
            self.maybe_claim_reborn_signal_reward(silent=True)

        except Exception:
            pass

    def _signal_catcher_back(self):
        try:
            self._sc_running = False
        except Exception:
            pass
        self.show_dashboard()

    def show_dashboard(self):
        self.clear_main()
        ctk.CTkLabel(self.main_frame, text="Состояние защиты 🛡️🎄", font=("Arial", 28, "bold")).pack(anchor="w")
        # Информация о версии
        ctk.CTkLabel(self.main_frame, text=f"Версия продукта: {APP_VERSION}", font=("Arial", 14, "italic")).pack(anchor="w", pady=(0, 5))
        # Новогодний обратный отсчёт
        try:
            today = datetime.now()
            new_year = datetime(today.year + 1, 1, 1)
            days_left = (new_year - today).days
            ctk.CTkLabel(self.main_frame, text=f"До Нового года осталось: {days_left} дн.", font=("Arial", 14)).pack(anchor="w", pady=(0, 10))
        except Exception:
            pass

        # Новогоднее пожелание
        try:
            ny_msg = random.choice(NEW_YEAR_MESSAGES)
            ctk.CTkLabel(self.main_frame, text=ny_msg, font=("Arial", 13), text_color="#F1C40F").pack(anchor="w", pady=(0, 10))
        except Exception:
            pass

        # Статус
        is_premium = self.settings.get("premium", {}).get("active", False)
        is_santa = self.settings.get("premium", {}).get("santa_mode", False)
        vt_set = bool(self.settings.get("api_key", ""))
        mb_set = bool(self.settings.get("malwarebazaar", {}).get("api_key", ""))
        is_api_set = vt_set or mb_set
        is_network_monitor_active = self.settings.get("premium", {}).get("network_monitor", False) and is_premium
        is_guard_active = self.settings.get("premium", {}).get("realtime_guard", False) and is_premium
        
        status_color = "green"
        status_text = "✅ СИСТЕМА В БЕЗОПАСНОСТИ"
        
        if is_santa:
            status_color = "#E74C3C" # Красный Деда Мороза
            status_text = "🎅 РЕЖИМ ДЕДА МОРОЗА (ПОЛНАЯ ЗАЩИТА АКТИВЕН)"
        elif is_guard_active:
            status_text = "🛡️ REAL-TIME ЗАЩИТА АКТИВНА"
        elif is_network_monitor_active:
            status_text = "🌐 МОНИТОРИНГ СЕТИ АКТИВЕН"
        elif is_premium:
            status_text = "⭐ CYBER SENTINEL PRO АКТИВЕН"
        elif not is_api_set:
            status_color = "#f1c40f"
            status_text = "⚠️ ONLINE API НЕ УСТАНОВЛЕНЫ (VT / MalwareBazaar)"
        
        status_frame = ctk.CTkFrame(self.main_frame, fg_color=status_color)
        status_frame.pack(fill="x", pady=20)
            
        ctk.CTkLabel(status_frame, text=status_text, 
                     font=("Arial", 18, "bold"), text_color="white").pack(pady=15)

        # Новогодний совет по безопасности
        if self.settings["ui"].get("christmas_style", False):
            try:
                tip = random.choice(NEW_YEAR_TIPS)
                tip_frame = ctk.CTkFrame(self.main_frame)
                tip_frame.pack(fill="x", pady=10)
                ctk.CTkLabel(tip_frame, text="🎄 Новогодний совет по кибербезопасности", font=("Arial", 14, "bold")).pack(anchor="w", padx=10, pady=(5, 0))
                ctk.CTkLabel(tip_frame, text=tip, font=("Arial", 13), wraplength=700, justify="left").pack(anchor="w", padx=10, pady=(0, 10))
            except Exception:
                pass

        # Графики ресурсов
        self.cpu_progress_bar, self.cpu_label = self.create_resource_bar("CPU Usage")
        self.ram_progress_bar, self.ram_label = self.create_resource_bar("RAM Usage")
        
        # Быстрые действия
        act_frame = ctk.CTkFrame(self.main_frame)
        act_frame.pack(fill="x", pady=20)
        ctk.CTkLabel(act_frame, text="Быстрые действия:", font=("Arial", 14)).pack(anchor="w", padx=10, pady=5)
        
        # Новогодние цвета для кнопок
        scan_color = "#2ECC71" # Зеленый
        temp_color = "#C0392B" # Красный
        
        ctk.CTkButton(act_frame, text="⚡ Быстрое сканирование", command=self.quick_scan_start, 
                      fg_color=scan_color, hover_color="#27AE60").pack(side="left", padx=10, pady=10)
        ctk.CTkButton(act_frame, text="🗑 Очистить Temp", fg_color=temp_color, 
                      hover_color="#9B59B6", command=self.clean_temp).pack(side="left", padx=10, pady=10) # Фиолетовый ховер как "волшебство"
        ctk.CTkButton(act_frame, text="⚙️ Настройки", command=self.show_settings).pack(side="left", padx=10, pady=10)
        ctk.CTkButton(act_frame, text="🎯 Signal Catcher", fg_color="#7D3CFF", hover_color="#5B2CFF", command=self.show_signal_catcher).pack(side="left", padx=10, pady=10)



        # Спойлер следующего ивента (версия пока неизвестна)
        ctk.CTkLabel(
            self.main_frame,
            text=(
                "🕒 Спойлер: следующий крупный ивент — CYBER REBORN.\n"
                "В нём появятся цепочки заданий на сканирование и защиту,\n"
                "специальная ивентовая валюта и уникальные неоновые темы интерфейса.\n"
                "Будут добавлены новые достижения за серии сканов и очисток.\n"
                "Точная версия и дата запуска будут объявлены позже."
            ),
            font=("Arial", 12, "italic"),
            text_color="#BDC3C7",
            wraplength=720,
            justify="left",
        ).pack(anchor="w", padx=10, pady=(0, 5))


        # --- HUGE KIBER REBORN BANNER ---
        try:
            if not hasattr(self, "coins_data") or not isinstance(self.coins_data, dict):
                self.coins_data = DataManager.load_coins()
            cores = int(self.coins_data.get("reborn_cores", 0))
        except Exception:
            cores = 0

        try:
            banner = ctk.CTkFrame(self.main_frame, fg_color="#0B1220")
            banner.pack(fill="x", pady=(8, 14))

            ctk.CTkLabel(
                banner,
                text="⚡⚡⚡ KIBER REBORN // INCOMING ⚡⚡⚡",
                font=("Impact", 24, "bold"),
                text_color="#F1C40F"
            ).pack(anchor="w", padx=12, pady=(12, 0))

            pct = self.get_reborn_signal_percent()
            preview = self.get_reborn_signal_preview_text(pct)
            ctk.CTkLabel(
                banner,
                text=f"REBORN-ЯДРА: {cores}   •   SIGNAL: {pct}%   •   (сундук усиливает сигнал)",
                font=("Arial", 13, "bold"),
                text_color="#E5E7EB"
            ).pack(anchor="w", padx=12, pady=(2, 6))

            ctk.CTkLabel(
                banner,
                text=preview,
                font=("Consolas", 13),
                text_color="#A78BFA"
            ).pack(anchor="w", padx=12, pady=(0, 10))

            try:
                self.maybe_claim_reborn_signal_reward(silent=False)
            except Exception:
                pass

            ctk.CTkButton(banner, text="🔓 Открыть сигнал", command=self.show_kiber_reborn_signal).pack(anchor="w", padx=12, pady=(0, 12))
        except Exception:
            pass

        # --- Новогодняя пасхалка: найди 2 подарка 🎁 ---
        try:
            self.spawn_firetruck_easter_eggs()
        except Exception:
            pass

    def create_resource_bar(self, title):
        frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        frame.pack(fill="x", pady=5)
        ctk.CTkLabel(frame, text=title, width=80, anchor="w").pack(side="left")
        bar = ctk.CTkProgressBar(frame)
        bar.pack(side="left", fill="x", expand=True, padx=10)
        label = ctk.CTkLabel(frame, text="0%")
        label.pack(side="left", padx=5)
        return bar, label

    def update_resources(self):
        if hasattr(self, 'cpu_progress_bar') and self.cpu_progress_bar.winfo_exists():
            cpu_p = psutil.cpu_percent()
            ram_p = psutil.virtual_memory().percent
            
            self.cpu_progress_bar.set(cpu_p / 100)
            self.cpu_label.configure(text=f"{cpu_p:.1f}%")
            self.ram_progress_bar.set(ram_p / 100)
            self.ram_label.configure(text=f"{ram_p:.1f}%")
            
        self.after(1000, self.update_resources)
        # Автоматический запуск мягкого снегопада на дашборде
        try:
            self.start_snowfall()
        except Exception:
            pass


    # ---
    def start_snowfall(self):
        """Лёгкий снегопад: ❄ только в верхней части окна, чтобы не мешать интерфейсу."""
        import random as _rnd

        # Если анимация уже идёт, не создаём её повторно
        if getattr(self, "_snowfall_running", False):
            return

        self._snowfall_running = True

        # Создаём снежинки один раз
        if not hasattr(self, "snowflakes"):
            self.snowflakes = []

            try:
                width = self.main_frame.winfo_width()
                height = self.main_frame.winfo_height()
            except Exception:
                width, height = 900, 600

            if width < 200 or height < 200:
                width, height = 900, 600

            # Меньше снежинок, чтобы не мешали
            flakes_count = 18

            for _ in range(flakes_count):
                x = _rnd.randint(0, width)
                y = _rnd.randint(-int(height * 0.5), 0)
                # Медленнее движение
                speed = _rnd.uniform(0.7, 1.8)
                size = _rnd.randint(10, 16)
                flake = ctk.CTkLabel(
                    self.main_frame,
                    text="❄",
                    font=("Segoe UI Emoji", size),
                    text_color="white",
                    fg_color="transparent",
                )
                flake.place(x=x, y=y)
                self.snowflakes.append([flake, float(x), float(y), speed])

        def _animate_snow():
            if not getattr(self, "_snowfall_running", False):
                return

            try:
                width = self.main_frame.winfo_width()
                height = self.main_frame.winfo_height()
            except Exception:
                width, height = 900, 600

            for flake in list(self.snowflakes):
                label, x, y, speed = flake
                y += speed
                x += _rnd.uniform(-0.4, 0.4)

                # Ограничиваем снег верхней половиной
                limit = int(height * 0.6)
                if y > limit:
                    y = _rnd.randint(-80, -20)
                    x = _rnd.randint(0, width)

                try:
                    label.place(x=x, y=y)
                except Exception:
                    continue

                flake[1] = x
                flake[2] = y

            try:
                # Чуть реже обновляем, чтобы не грузить
                self.after(70, _animate_snow)
            except Exception:
                self._snowfall_running = False

        # Стартуем анимацию
        _animate_snow()

    def show_scanner(self):
        self.clear_main()
        ctk.CTkLabel(self.main_frame, text="Центр сканирования 🔍", font=("Arial", 24, "bold")).pack(anchor="w", pady=(0,20))
        
        btn_frame = ctk.CTkFrame(self.main_frame)
        btn_frame.pack(fill="x", pady=10)
        ctk.CTkButton(btn_frame, text="Выбрать файл", command=lambda: self.prepare_scan(False)).pack(side="left", padx=10, pady=10)
        ctk.CTkButton(btn_frame, text="Выбрать папку", command=lambda: self.prepare_scan(True)).pack(side="left", padx=10, pady=10)
        
        self.scan_file_label = ctk.CTkLabel(self.main_frame, text="Текущий файл: Ожидание...", font=("Arial", 14)) # Новый виджет
        self.scan_file_label.pack(anchor="w", pady=5)
        
        self.scan_status_label = ctk.CTkLabel(self.main_frame, text="Ожидание...", font=("Arial", 14))
        self.scan_status_label.pack(pady=5)
        
        self.scan_progress = ctk.CTkProgressBar(self.main_frame)
        self.scan_progress.set(0)
        self.scan_progress.pack(fill="x", pady=10)
        
        self.scan_log = ctk.CTkTextbox(self.main_frame, height=300)
        self.scan_log.pack(fill="both", expand=True)

    def prepare_scan(self, is_folder):
        path = filedialog.askdirectory() if is_folder else filedialog.askopenfilename()
        if not path: return
        
        files = []
        if is_folder:
            # Улучшение: Игнорируем недоступные системные папки (например, System Volume Information)
            for root, _, fnames in os.walk(path):
                for f in fnames:
                    try:
                        full_path = os.path.join(root, f)
                        if os.path.isfile(full_path):
                            files.append(full_path)
                    except UnicodeDecodeError:
                        # Игнорирование файлов с некорректными именами
                        pass
        else:
            files.append(path)
            
        self.scan_log.delete("1.0", "end")
        self.scan_log.insert("end", f"🚀🎄 Старт новогоднего сканирования: {len(files)} объектов\n")
        
        threading.Thread(target=self.scanner.start_scan, args=(files,), daemon=True).start()

    def update_scan_progress(self, scanned, total, current_file_path, result):
        # Отображение текущего сканируемого файла (УЛУЧШЕНИЕ)
        self.scan_file_label.configure(text=f"Текущий файл: {os.path.basename(current_file_path)}")
        
        val = scanned / total
        self.scan_progress.set(val)
        self.scan_status_label.configure(text=f"Обработано: {scanned}/{total}")
        
        if result and result["status"] != "clean":
            msg = f"⚠️ [{result['status'].upper()}] {os.path.basename(result['file'])} - {result['threat']}\n"
            self.scan_log.insert("end", msg, result["status"])
            self.scan_log.tag_config("infected", foreground="red")
            self.scan_log.tag_config("suspicious", foreground="orange")
            self.scan_log.tag_config("quarantined", foreground="#F1C40F") # Золотисто-желтый для новогоднего настроения
            self.scan_log.tag_config("skipped", foreground="gray")
            self.scan_log.see("end")


    def scan_finished(self, detected):
        # Игровой тихий режим: без всплывающих окон, только лог
        gamer_silent = self.settings.get("gamer", {}).get("silent_mode", False)

        if detected > 0:
            if not gamer_silent:
                messagebox.showwarning(
                    "Готово",
                    f"Сканирование завершено. 😥\nУгроз найдено: {detected}. Похоже, кто-то был непослушным."
                )
            self.scan_log.insert("end", f"⚠️ Обнаружено угроз: {detected}\n")
            reward = 10
        else:
            if not gamer_silent:
                # Новогоднее сообщение
                messagebox.showinfo(
                    "Готово",
                    f"Сканирование завершено. 🎉\nУгроз найдено: {detected}. Вы были хорошим мальчиком/девочкой!"
                )
            self.scan_log.insert("end", "✅ Угроз не обнаружено. Система чиста.\n")
            reward = 5

        # Небольшой новогодний буст монет (31 декабря и 1 января)
        from datetime import datetime as _dt
        today = _dt.now()
        new_year_multiplier = 2 if (today.month == 12 and today.day == 31) or (today.month == 1 and today.day == 1) else 1

        # Награда монетами за сканирование
        final_reward = reward * new_year_multiplier
        try:
            self.add_coins(final_reward)
        except Exception:
            pass

        # 8.5: Scan Streak + REBORN cores drip
        try:
            self.register_scan_streak()
        except Exception:
            pass
        try:
            self.reward_reborn_for_scan(detected)
        except Exception:
            pass

        # Зимние ачивки за количество сканов
        try:
            self.register_winter_scan_achievements()
        except Exception:
            pass



    # --- Вкладка: ИГРОВОЙ РЕЖИМ ---
    def show_gamer_mode(self):
        self.clear_main()
        ctk.CTkLabel(self.main_frame, text="🎮 Игровой режим и FPS-оптимизация", font=("Arial", 24, "bold")).pack(anchor="w", pady=(0, 20))

        info_text = (
            "Игровой режим помогает играть комфортнее:\n"
            "• Меньше всплывающих окон во время игр (если включён тихий режим).\n"
            "• Полные сканирования можно отложить, чтобы не мешать FPS.\n"
            "• Уведомления делаются более компактными."
        )
        ctk.CTkLabel(self.main_frame, text=info_text, font=("Arial", 13), justify="left").pack(anchor="w", pady=(0, 15))

        frame = ctk.CTkFrame(self.main_frame)
        frame.pack(fill="x", pady=10)

        self.var_gamer_silent = ctk.BooleanVar(value=self.settings.get("gamer", {}).get("silent_mode", False))
        self.var_gamer_delay = ctk.BooleanVar(value=self.settings.get("gamer", {}).get("delay_full_scans", True))
        self.var_gamer_opt = ctk.BooleanVar(value=self.settings.get("gamer", {}).get("optimize_notifications", True))

        ctk.CTkSwitch(frame, text="Тихий режим (минимум всплывающих окон во время игры)",
                      variable=self.var_gamer_silent).pack(anchor="w", padx=10, pady=5)
        ctk.CTkSwitch(frame, text="Откладывать полное сканирование, если запущена игра",
                      variable=self.var_gamer_delay).pack(anchor="w", padx=10, pady=5)
        ctk.CTkSwitch(frame, text="Оптимизировать уведомления для игр",
                      variable=self.var_gamer_opt).pack(anchor="w", padx=10, pady=5)

        def save_gamer_settings():
            self.settings.setdefault("gamer", {})
            self.settings["gamer"]["silent_mode"] = self.var_gamer_silent.get()
            self.settings["gamer"]["delay_full_scans"] = self.var_gamer_delay.get()
            self.settings["gamer"]["optimize_notifications"] = self.var_gamer_opt.get()
            DataManager.save_settings(self.settings)
            messagebox.showinfo("Игровой режим", "Настройки игрового режима сохранены. Приятной игры!")

        ctk.CTkButton(self.main_frame, text="💾 Сохранить настройки игрового режима",
                      command=save_gamer_settings).pack(anchor="w", padx=10, pady=15)

        # Блок анализа процессов для FPS
        sep = ctk.CTkFrame(self.main_frame, height=1, fg_color=("gray70", "gray30"))
        sep.pack(fill="x", padx=10, pady=10)

        ctk.CTkLabel(self.main_frame, text="⚡ Анализ процессов для повышения FPS", font=("Arial", 18, "bold")).pack(anchor="w", padx=10, pady=(0, 10))

        fps_frame = ctk.CTkFrame(self.main_frame)
        fps_frame.pack(fill="x", pady=10)
        ctk.CTkButton(fps_frame, text="🔄 Проанализировать процессы", command=self.analyze_fps_processes).pack(side="left", padx=10, pady=10)
        if WINDOWS_OS:
            ctk.CTkButton(fps_frame, text="🧰 Открыть диспетчер задач", command=lambda: subprocess.Popen("taskmgr")).pack(side="left", padx=10, pady=10)

        self.fps_text = ctk.CTkTextbox(self.main_frame, height=320)
        self.fps_text.pack(fill="both", expand=True, padx=10, pady=(5, 10))

        tips = (
            "Советы для повышения FPS:\n"
            "• Закрой браузеры с кучей вкладок, Discord, Telegram и т.п. перед игрой.\n"
            "• Не запускай несколько лаунчеров игр одновременно.\n"
            "• Отключи оверлеи, если они не нужны (Steam, Discord оверлей и т.д.).\n"
            "• Следи за температурой — перегрев снижает частоту CPU и видеокарты."
        )
        ctk.CTkLabel(self.main_frame, text=tips, font=("Arial", 12), justify="left").pack(anchor="w", padx=10, pady=(0, 10))


    # --- Вкладка: FPS-ОПТИМИЗАТОР ---
    def show_fps_optimizer(self):
        self.clear_main()
        ctk.CTkLabel(self.main_frame, text="⚡ FPS-оптимизатор", font=("Arial", 24, "bold")).pack(anchor="w", pady=(0, 20))

        info = (
            "Этот инструмент помогает немного разгрузить систему перед игрой:\n"
            "• Находит самые прожорливые процессы по памяти.\n"
            "• Даёт подсказки, что можно закрыть перед запуском игры.\n"
            "\n"
            "Важно: программа НИЧЕГО не завершает сама — только показывает, что можно закрыть вручную."
        )
        ctk.CTkLabel(self.main_frame, text=info, font=("Arial", 13), justify="left").pack(anchor="w", pady=(0, 10))

        btn_frame = ctk.CTkFrame(self.main_frame)
        btn_frame.pack(fill="x", pady=10)
        ctk.CTkButton(btn_frame, text="🔄 Проанализировать процессы", command=self.analyze_fps_processes).pack(side="left", padx=10, pady=10)

        if WINDOWS_OS:
            ctk.CTkButton(btn_frame, text="🧰 Открыть диспетчер задач", command=lambda: subprocess.Popen("taskmgr")).pack(side="left", padx=10, pady=10)

        # Поле для вывода списка процессов
        self.fps_text = ctk.CTkTextbox(self.main_frame, height=320)
        self.fps_text.pack(fill="both", expand=True, padx=10, pady=(5, 10))

        tips = (
            "Советы для повышении FPS:\n"
            "• Закрой браузеры с кучей вкладок, Discord, Telegram и т.п. перед игрой.\n"
            "• Не запускай несколько лаунчеров игр одновременно.\n"
            "• Отключи оверлеи, если они не нужны (Steam, Discord оверлей и т.д.).\n"
            "• Следи за температурой — перегрев снижает частоту CPU и видеокарты."
        )
        ctk.CTkLabel(self.main_frame, text=tips, font=("Arial", 12), justify="left").pack(anchor="w", padx=10, pady=(0, 10))

    def analyze_fps_processes(self):
        if not hasattr(self, "fps_text") or self.fps_text is None:
            return

        self.fps_text.delete("1.0", "end")
        self.fps_text.insert("end", "Сканирование процессов...\n\n")

        heavy = []
        try:
            for p in psutil.process_iter(["pid", "name", "memory_info"]):
                try:
                    info = p.info
                    name = info.get("name") or "unknown"
                    mem = info.get("memory_info")
                    if mem is None:
                        continue
                    mem_mb = mem.rss / (1024 * 1024)
                    # Отбрасываем совсем мелкие
                    if mem_mb < 50:
                        continue
                    heavy.append((mem_mb, name, info.get("pid")))
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
        except Exception as e:
            self.fps_text.insert("end", f"Ошибка анализа процессов: {e}\n")
            return

        if not heavy:
            self.fps_text.insert("end", "Не удалось найти тяжёлые процессы. Система и так достаточно свободна.\n")
            return

        heavy.sort(reverse=True)
        self.fps_text.insert("end", "Наиболее прожорливые процессы по памяти (рекомендуется закрыть лишние перед игрой):\n\n")
        for mem_mb, name, pid in heavy[:15]:
            self.fps_text.insert("end", f"{name} (PID {pid}) — ~{mem_mb:.1f} МБ RAM\n")

        self.fps_text.insert("end", "\nЗакрывайте ТОЛЬКО те процессы, которые вы узнаёте и понимаете, что это не системный компонент.\n")


    # --- Вкладка: КЕЙСЫ И МОНЕТЫ ---
    def show_cases(self):
        self.clear_main()
        ctk.CTkLabel(self.main_frame, text="💎 Сундуки и монеты", font=("Arial", 24, "bold")).pack(anchor="w", pady=(0, 20))

        # Баланс
        balance_frame = ctk.CTkFrame(self.main_frame)
        balance_frame.pack(fill="x", pady=10)
        self.coins_balance_label = ctk.CTkLabel(balance_frame, text=self.get_coins_text(), font=("Arial", 16, "bold"))
        self.coins_balance_label.pack(side="left", padx=10, pady=10)

        ctk.CTkButton(balance_frame, text="🎁 Новогодний бонус (+50 монет)", command=self.claim_daily_bonus).pack(
            side="left", padx=10, pady=10
        )

        # --- KIBER REBORN: EVENT PANEL (HUGE HINT) ---
        try:
            if not hasattr(self, "coins_data") or not isinstance(self.coins_data, dict):
                self.coins_data = DataManager.load_coins()
            cores = int(self.coins_data.get("reborn_cores", 0))
            inv = self.coins_data.get("inventory", {}) if isinstance(self.coins_data.get("inventory", {}), dict) else {}
            inv_themes = len(inv.get("themes", [])) if isinstance(inv.get("themes", []), list) else 0
            inv_badges = len(inv.get("badges", [])) if isinstance(inv.get("badges", []), list) else 0
            inv_relics = len(inv.get("relics", [])) if isinstance(inv.get("relics", []), list) else 0

            reborn_frame = ctk.CTkFrame(self.main_frame, fg_color="#2C3E50")
            reborn_frame.pack(fill="x", pady=(0, 10))

            ctk.CTkLabel(
                reborn_frame,
                text="⚡ KIBER REBORN // СИГНАЛ ОБНАРУЖЕН",
                font=("Impact", 22, "bold"),
                text_color="#F1C40F"
            ).pack(anchor="w", padx=12, pady=(10, 0))

            ctk.CTkLabel(
                reborn_frame,
                text=(
                    "Собирай REBORN-ЯДРА из сундуков и сканов. "
                    "Когда ядра стабилизируются — откроется новый слой интерфейса.\n"
                    "Подсказка: первые артефакты уже спрятаны в ивентовом сундуке…"
                ),
                font=("Arial", 12),
                justify="left",
                wraplength=760
            ).pack(anchor="w", padx=12, pady=(2, 8))

            stats_row = ctk.CTkFrame(reborn_frame, fg_color="transparent")
            stats_row.pack(fill="x", padx=12, pady=(0, 10))
            ctk.CTkLabel(stats_row, text=f"REBORN-ЯДРА: {cores}", font=("Arial", 14, "bold")).pack(side="left", padx=(0, 14))
            ctk.CTkLabel(stats_row, text=f"Артефакты: темы {inv_themes} | бейджи {inv_badges} | реликвии {inv_relics}", font=("Arial", 13)).pack(side="left")
            ctk.CTkButton(stats_row, text="🔓 Расшифровать сигнал", command=self.show_kiber_reborn_signal).pack(side="right")
        except Exception:
            pass

        # Описание кейсов
        cases_frame = ctk.CTkFrame(self.main_frame)
        cases_frame.pack(fill="both", expand=True, pady=10)

        self.case_definitions = [
            {
                "id": "basic",
                "name": "Бюджетный кейс",
                "price": 50,
                "chance": 1.0,
                "description": "Самый дешевый кейс. Шанс выпадения Премиум ≈ 1%."
            },
            {
                "id": "pro",
                "name": "Про кейс",
                "price": 150,
                "chance": 5.0,
                "description": "Баланс цена/шанс. Шанс Премиум ≈ 5%."
            },
            {
                "id": "legend",
                "name": "Легендарный кейс",
                "price": 400,
                "chance": 12.0,
                "description": "Дорогой, но шанс выше – около 12%. Маленький шанс поймать Santa Mode."
            },
            {
                "id": "reborn",
                "name": "⚡ KIBER REBORN сундук",
                "price": 250,
                "chance": 7.0,
                "description": "Ивентовый сундук. Даёт REBORN-ЯДРА и артефакты, а также шанс Премиума ≈ 7%."
            },
        ]

        for case in self.case_definitions:
            row = ctk.CTkFrame(cases_frame)
            row.pack(fill="x", pady=5, padx=10)

            ctk.CTkLabel(
                row, text=f"{case['name']} — {case['price']} монет", font=("Arial", 14, "bold"), anchor="w"
            ).pack(side="top", anchor="w", padx=10, pady=(5, 0))

            ctk.CTkLabel(
                row, text=f"Шанс Премиума: {case['chance']}%\n{case['description']}", anchor="w"
            ).pack(side="left", padx=10, pady=(0, 5))

            ctk.CTkButton(
                row, text="Открыть сундук", width=140, command=lambda c=case: self.open_case(c)
            ).pack(side="right", padx=10, pady=10)

    def get_coins_text(self):
        coins = 0
        try:
            if not hasattr(self, "coins_data") or not isinstance(self.coins_data, dict):
                self.coins_data = DataManager.load_coins()
            coins = int(self.coins_data.get("coins", 0))
        except Exception:
            coins = 0
        return f"Монеты: {coins}"

    def update_coins_labels(self):
        # Обновляем индикаторы монет в сайдбаре и на странице кейсов
        if hasattr(self, "coins_label"):
            self.coins_label.configure(text=self.get_coins_text())
        if hasattr(self, "coins_balance_label"):
            self.coins_balance_label.configure(text=self.get_coins_text())

        if hasattr(self, "reborn_label"):
            self.reborn_label.configure(text=self.get_reborn_sidebar_text())

    def add_coins(self, amount: int):
        try:
            if not hasattr(self, "coins_data") or not isinstance(self.coins_data, dict):
                self.coins_data = DataManager.load_coins()
            current = int(self.coins_data.get("coins", 0))
            self.coins_data["coins"] = max(0, current + int(amount))
            DataManager.save_coins(self.coins_data)
            self.update_coins_labels()
        except Exception:
            pass


    # ==========================
    # 8.5.0.0 — REBORN SYSTEMS
    # ==========================
    def ensure_coins_data(self):
        if not hasattr(self, "coins_data") or not isinstance(self.coins_data, dict):
            self.coins_data = DataManager.load_coins()
        # ensure upgraded keys (in case old coins.json existed)
        try:
            self.coins_data.setdefault("reborn_cores", 0)
            self.coins_data.setdefault("reborn_signal_reward_claimed", False)
            self.coins_data.setdefault("reborn_last_reward_popup", "")
            ss = self.coins_data.setdefault("scan_streak", {})
            if not isinstance(ss, dict):
                ss = {}
                self.coins_data["scan_streak"] = ss
            ss.setdefault("current", 0)
            ss.setdefault("best", 0)
            ss.setdefault("last_scan_date", "")
            sc = self.coins_data.setdefault("signal_catcher", {})
            if not isinstance(sc, dict):
                sc = {}
                self.coins_data["signal_catcher"] = sc
            sc.setdefault("last_play_date", "")
            sc.setdefault("plays_today", 0)
            sc.setdefault("best_combo", 0)
            sc.setdefault("best_score", 0)
            inv = self.coins_data.setdefault("inventory", {})
            if not isinstance(inv, dict):
                inv = {}
                self.coins_data["inventory"] = inv
            inv.setdefault("themes", [])
            inv.setdefault("badges", [])
            inv.setdefault("titles", [])
            inv.setdefault("relics", [])
        except Exception:
            pass

    def _calculate_reborn_signal_percent(self, cores=None) -> int:
        """Возвращает процент сигнала REBORN по количеству ядер.
        Поддерживает вызов как без аргумента, так и self._calculate_reborn_signal_percent(cores).
        """
        try:
            if cores is None:
                # Берём из coins_data, если доступно
                if hasattr(self, "ensure_coins_data"):
                    try:
                        self.ensure_coins_data()
                    except Exception:
                        pass
                cores = 0
                try:
                    cores = int(getattr(self, "coins_data", {}).get("reborn_cores", 0))
                except Exception:
                    cores = 0
            else:
                cores = int(cores)
        except Exception:
            cores = 0

        if cores >= 600:
            return 100
        if cores >= 300:
            return 70
        if cores >= 150:
            return 50
        if cores >= 50:
            return 30
        return 0

    def get_reborn_sidebar_text(self):
        try:
            self.ensure_coins_data()
            cores = int(self.coins_data.get("reborn_cores", 0))
            pct = self.get_reborn_signal_percent()
            return f"REBORN: {cores} • {pct}%"
        except Exception:
            return "REBORN: 0 • 0%"

    def add_reborn_cores(self, amount: int):
        try:
            self.ensure_coins_data()
            current = int(self.coins_data.get("reborn_cores", 0))
            self.coins_data["reborn_cores"] = max(0, current + int(amount))
            DataManager.save_coins(self.coins_data)
            self.update_coins_labels()
        except Exception:
            pass

    def get_reborn_signal_percent(self):
        """Signal percent derived from reborn_cores."""
        try:
            self.ensure_coins_data()
            cores = int(self.coins_data.get("reborn_cores", 0))
        except Exception:
            cores = 0

        if cores >= 600:
            return 100
        if cores >= 300:
            return 70
        if cores >= 150:
            return 50
        if cores >= 50:
            return 30
        return 0

    def get_reborn_signal_preview_text(self, percent=None):
        """Return a 'decoded' / 'garbled' preview depending on signal level."""
        if percent is None:
            percent = self.get_reborn_signal_percent()

        # Keep it short and punchy: looks like intercepted transmission
        if percent <= 0:
            return "-----------  NO SIGNAL  -----------"
        if percent == 30:
            return "o---bUd-----p----n---  [30%]"
        if percent == 50:
            return "oBNoVlEnI---  bU---pOs---  nOvOg---  [50%]"
        if percent == 70:
            return "ОБНОВЛЕНИЕ — БУДЕТ — ПОСЛЕ — НОВОГО — ГОДА  [70%]"
        return "ОБНОВЛЕНИЕ БУДЕТ ПОСЛЕ НОВОГО ГОДА ✅  [100%]"

    def maybe_claim_reborn_signal_reward(self, silent=False):
        """One-time reward when signal hits 100%."""
        try:
            self.ensure_coins_data()
            pct = self.get_reborn_signal_percent()
            claimed = bool(self.coins_data.get("reborn_signal_reward_claimed", False))
            if pct >= 100 and not claimed:
                self.coins_data["reborn_signal_reward_claimed"] = True
                DataManager.save_coins(self.coins_data)
                self.add_coins(1000)
                if not silent:
                    messagebox.showinfo("📡 Сигнал пойман", "Ты уловил 100% сигнала!\nНаграда: +1000 монет 💰")
        except Exception:
            pass

    def register_scan_streak(self):
        """Counts daily scan streak and rewards milestones."""
        try:
            self.ensure_coins_data()
            ss = self.coins_data.setdefault("scan_streak", {})
            last = str(ss.get("last_scan_date", ""))
            today = datetime.now().strftime("%Y-%m-%d")

            if last == today:
                return  # already counted today

            # compute yesterday
            try:
                from datetime import datetime as _dt, timedelta as _td
                y = (_dt.now() - _td(days=1)).strftime("%Y-%m-%d")
            except Exception:
                y = ""

            cur = int(ss.get("current", 0))
            if last == y and cur > 0:
                cur += 1
            else:
                cur = 1

            ss["current"] = cur
            ss["last_scan_date"] = today
            best = int(ss.get("best", 0))
            if cur > best:
                ss["best"] = cur

            DataManager.save_coins(self.coins_data)
            self.update_coins_labels()

            # milestone rewards
            milestone_rewards = {
                3: ("Серия сканов x3", 25, 1),
                7: ("Серия сканов x7", 80, 3),
                14: ("Серия сканов x14", 200, 7),
                30: ("Серия сканов x30", 500, 15),
            }
            if cur in milestone_rewards:
                title, coins, cores = milestone_rewards[cur]
                self.add_coins(coins)
                self.add_reborn_cores(cores)
                try:
                    messagebox.showinfo("🔥 Scan Streak", f"{title}!\nНаграда: +{coins} монет, +{cores} REBORN-ядер")
                except Exception:
                    pass
        except Exception:
            pass

    def reward_reborn_for_scan(self, detected: int):
        """Small REBORN core drip for scans."""
        try:
            base = 1
            if int(detected) > 0:
                base += 1
            # tiny randomness so it feels 'alive'
            if random.random() < 0.12:
                base += 1
            self.add_reborn_cores(base)

            # tiny artifact chance
            if random.random() < 0.02:
                art = self._grant_random_reborn_artifact()
                if art:
                    try:
                        messagebox.showinfo("🧩 Артефакт найден", f"Во время скана ты выцепил артефакт:\n{art}")
                    except Exception:
                        pass

            # check 100% reward
            self.maybe_claim_reborn_signal_reward(silent=True)
        except Exception:
            pass

    def _grant_random_reborn_artifact(self):
        """Returns artifact string or None."""
        try:
            self.ensure_coins_data()
            inv = self.coins_data.setdefault("inventory", {})
            inv.setdefault("themes", [])
            inv.setdefault("badges", [])
            inv.setdefault("titles", [])
            inv.setdefault("relics", [])

            artifacts = [
                ("themes", "🌌 Theme: Neon Pulse"),
                ("themes", "🟣 Theme: Violet Circuit"),
                ("themes", "⚡ Theme: Signal Storm"),
                ("badges", "📛 Badge: KIBER NODE"),
                ("badges", "📛 Badge: SIGNAL HUNTER"),
                ("titles", "🏷️ Title: REBORN Initiate"),
                ("titles", "🏷️ Title: Phase Breaker"),
                ("relics", "🧿 Relic: Glass Antenna"),
                ("relics", "🧿 Relic: Core Prism"),
            ]

            key, item = random.choice(artifacts)
            if item not in inv.get(key, []):
                inv[key].append(item)
                DataManager.save_coins(self.coins_data)
                self.update_coins_labels()
                return item
        except Exception:
            pass
        return None

    def register_winter_scan_achievements(self):
            """Регистрация зимних ачивок за количество сканирований."""
            try:
                if not hasattr(self, "coins_data") or not isinstance(self.coins_data, dict):
                    self.coins_data = DataManager.load_coins()
    
                ach = self.coins_data.setdefault("winter_achievements", {})
                if not isinstance(ach, dict):
                    ach = {}
                    self.coins_data["winter_achievements"] = ach
    
                count = int(self.coins_data.get("scan_total", self.coins_data.get("winter_scan_count", 0) or 0)) + 1
                self.coins_data["scan_total"] = count
                self.coins_data["winter_scan_count"] = count  # legacy key
    
                unlocked = []
    
                def unlock(key, title, bonus):
                    if not ach.get(key, False):
                        ach[key] = True
                        if bonus != 0:
                            current = int(self.coins_data.get("coins", 0))
                            self.coins_data["coins"] = max(0, current + int(bonus))
                        unlocked.append((title, bonus))
    
                # 1 сканирование
                if count >= 1:
                    unlock("first_scan", "❄ Первая зимняя проверка", 5)
                # 10 сканирований
                if count >= 10:
                    unlock("ten_scans", "⛄ 10 зимних сканирований", 15)
                # 25 сканирований
                if count >= 25:
                    unlock("twentyfive_scans", "🎁 25 зимних сканирований", 30)
    
                DataManager.save_coins(self.coins_data)
                self.update_coins_labels()
    
                if unlocked:
                    text = "Открыты зимние достижения:\n\n"
                    for title, bonus in unlocked:
                        if bonus:
                            text += f"{title} (+{bonus} монет)\n"
                        else:
                            text += f"{title}\n"
                    try:
                        messagebox.showinfo("Достижения", text)
                    except Exception:
                        print(text)
            except Exception:
                pass
    
    
    def claim_daily_bonus(self):
        try:
            if not hasattr(self, "coins_data") or not isinstance(self.coins_data, dict):
                self.coins_data = DataManager.load_coins()
            today = datetime.now().strftime("%Y-%m-%d")
            last = self.coins_data.get("last_daily_bonus", "")
            if last == today:
                messagebox.showinfo("Бонус", "Ты уже забрал сегодняшний бонус. Приходи завтра! 🎄")
                return
            # Обновляем дату и даем монеты
            self.coins_data["last_daily_bonus"] = today
            # Сохраняем дату сразу, а монеты добавит add_coins
            DataManager.save_coins(self.coins_data)
            self.add_coins(50)
            messagebox.showinfo("Бонус", "Ты получил +50 монет! 💰")
        except Exception:
            messagebox.showerror("Ошибка", "Не удалось выдать ежедневный бонус.")

    def open_case(self, case):
        try:
            if not hasattr(self, "coins_data") or not isinstance(self.coins_data, dict):
                self.coins_data = DataManager.load_coins()
            current = int(self.coins_data.get("coins", 0))
            price = int(case.get("price", 0))

            if current < price:
                messagebox.showerror(
                    "Недостаточно монет",
                    f"На балансе {current} монет, а нужно {price}.\n"
                    f"Сканируй систему и забирай ежедневный бонус, чтобы накопить!"
                )
                return

            
            # Списываем монеты за открытие сундука
            self.coins_data["coins"] = current - price

            # --- KIBER REBORN: event loot (cores + artifacts) ---
            case_id = case.get("id")
            reborn_cores_gain = 0
            reborn_artifact = None

            # tiny teaser even for обычных сундуков
            try:
                if case_id in ("basic", "pro", "legend") and random.random() < 0.03:
                    self.coins_data.setdefault("reborn_cores", 0)
                    self.coins_data["reborn_cores"] = int(self.coins_data.get("reborn_cores", 0)) + 1
            except Exception:
                pass

            if case_id == "reborn":
                try:
                    self.coins_data.setdefault("reborn_cores", 0)
                    inv = self.coins_data.setdefault("inventory", {})
                    if not isinstance(inv, dict):
                        inv = {}
                        self.coins_data["inventory"] = inv
                    inv.setdefault("themes", [])
                    inv.setdefault("badges", [])
                    inv.setdefault("titles", [])
                    inv.setdefault("relics", [])

                    reborn_cores_gain = random.randint(2, 7)
                    self.coins_data["reborn_cores"] = int(self.coins_data.get("reborn_cores", 0)) + reborn_cores_gain

                    # шанс на артефакт (не всегда, чтобы было желание крутить)
                    if random.random() < 0.55:
                        drop = random.choice([
                            "NEON THEME: Reborn Pulse",
                            "BADGE: KIBER REBORN // SIGNAL",
                            "TITLE: ядро-носитель",
                            "RELIC: Glitch Crystal",
                            "RELIC: Quantum Fuse",
                        ])
                        reborn_artifact = drop

                        # кладём в инвентарь без дублей
                        def _add_unique(lst, item):
                            if isinstance(lst, list) and item not in lst:
                                lst.append(item)

                        if drop.startswith("NEON THEME"):
                            _add_unique(inv["themes"], drop)
                        elif drop.startswith("BADGE"):
                            _add_unique(inv["badges"], drop)
                        elif drop.startswith("TITLE"):
                            _add_unique(inv["titles"], drop)
                        else:
                            _add_unique(inv["relics"], drop)
                except Exception:
                    pass

            # Ролл сундука на Премиум
            # Ролл сундука на Премиум
            roll = random.uniform(0, 100)
            chance = float(case.get("chance", 0.0))
            win = roll <= chance

            if win:
                # ВЫПАЛ ПРЕМИУМ
                already_premium = self.settings.get("premium", {}).get("active", False)
                self.settings["premium"]["active"] = True

                # Небольшой шанс Santa Mode для легендарного кейса
                if case.get("id") == "legend" and random.random() < 0.25:
                    self.settings["premium"]["santa_mode"] = True

                DataManager.save_settings(self.settings)
                DataManager.save_coins(self.coins_data)

                # Перерисовываем UI, чтобы премиум-функции сразу открылись
                self.setup_ui()
                self.show_cases()

                if self.settings.get("premium", {}).get("santa_mode", False) and case.get("id") == "legend":
                    messagebox.showinfo(
                        "Удача!",
                        "🎅 НЕВЕРОЯТНО! Из легендарного кейса выпал РЕЖИМ ДЕДА МОРОЗА!\n"
                        "Все премиум-функции активированы."
                    )
                else:
                    msg = "⭐ Поздравляем! Вы выбили Премиум-доступ CYBER SENTINEL PRO!"
                    if already_premium:
                        msg += "\n(Премиум уже был активен, но удача явно на вашей стороне 😎)"
                    if case_id == "reborn":
                        msg += f"\n\n⚡ KIBER REBORN: +{reborn_cores_gain} REBORN-ЯДЕР"
                        if reborn_artifact:
                            msg += f"\nАртефакт: {reborn_artifact}"
                        msg += "\n\nОГРОМНЫЙ НАМЁК: ядра уже откликаются… интерфейс скоро переродится."
                    messagebox.showinfo("Удача!", msg)

            else:
                # НЕ ВЫПАЛ ПРЕМИУМ — ДАЁМ УТЕШИТЕЛЬНЫЙ ЛУТ В ЗАВИСИМОСТИ ОТ КЕЙСА
                case_id = case.get("id")

                # МНОГО разных утешительных наград (все в монетах, но с разным вкусом)
                if case_id == "basic":
                    # Дешёвый кейс — мелкие, но частые плюшки
                    possible_rewards = [5, 7, 9, 10, 12, 15, 18, 20]
                elif case_id == "pro":
                    # Средний кейс — приличные награды
                    possible_rewards = [15, 20, 25, 30, 35, 40, 50, 60, 75]
                elif case_id == "legend":
                    # Легендарный — жирные утешительные призы
                    possible_rewards = [40, 60, 80, 100, 120, 150, 180, 200, 250]
                elif case_id == "reborn":
                    # Ивентовый сундук — монеты как бонус, но главная ценность в REBORN-ядрах
                    possible_rewards = [25, 35, 45, 60, 75, 90, 110]
                else:
                    # На всякий случай, если вдруг добавишь новый кейс
                    possible_rewards = [10, 20, 30, 40]

                consolation = random.choice(possible_rewards)
                self.coins_data["coins"] += consolation

                DataManager.save_coins(self.coins_data)
                self.show_cases()

                # Текст в зависимости от "щедрости" приза
                msg = (
                    "Премиум не выпал, но ты получил "
                    f"{consolation} монет утешительного приза! 💰"
                )

                if case_id == "reborn":
                    msg += f"\n\n⚡ KIBER REBORN: +{reborn_cores_gain} REBORN-ЯДЕР"
                    if reborn_artifact:
                        msg += f"\nАртефакт: {reborn_artifact}"
                    msg += "\n\nОГРОМНЫЙ НАМЁК: это только первый импульс. Следующий будет сильнее…"

                # Если вернули почти цену кейса — подчёркиваем
                if consolation >= price * 0.8:
                    msg += "\nТы почти полностью отбил стоимость кейса! 🤯"
                elif consolation >= price * 0.5:
                    msg += "\nНеплохо! Это примерно половина стоимости кейса 😉"
                elif consolation <= price * 0.2:
                    msg += "\nВ этот раз чуть меньше... Но фармим дальше и крутим ещё! 🔁"

                messagebox.showinfo("Утешительный приз", msg)

            # Обновляем отображение монет
            self.update_coins_labels()

        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось открыть кейс: {e}")



    # --- Вкладка: БЫСТРАЯ ПРОВЕРКА ОДНОГО ФАЙЛА ---
    def show_quick_file_scan(self):
        """Простая страница для анализа одного файла через движок антивируса."""
        self.clear_main()

        ctk.CTkLabel(
            self.main_frame,
            text="🧪 Быстрая проверка файла",
            font=("Arial", 24, "bold")
        ).pack(anchor="w", pady=(0, 20))

        info_text = (
            "Выберите любой файл на диске и запустите анализ. "
            "Файл будет проверен локальной эвристикой и (при наличии ключа) через VirusTotal.\n"
            "Это удобно, если вы скачали что-то подозрительное и хотите быстро его проверить."
        )
        ctk.CTkLabel(
            self.main_frame,
            text=info_text,
            justify="left"
        ).pack(anchor="w", pady=(0, 15))

        # Блок выбора файла
        select_frame = ctk.CTkFrame(self.main_frame)
        select_frame.pack(fill="x", pady=10)

        self.quick_file_path = None

        self.quick_file_label = ctk.CTkLabel(
            select_frame,
            text="Файл не выбран",
            anchor="w"
        )
        self.quick_file_label.pack(side="left", padx=10, pady=10, fill="x", expand=True)

        ctk.CTkButton(
            select_frame,
            text="Выбрать файл...",
            command=self.choose_quick_file
        ).pack(side="right", padx=10, pady=10)

        # Кнопка запуска проверки
        ctk.CTkButton(
            self.main_frame,
            text="🔍 Проверить файл",
            command=self.start_quick_file_scan
        ).pack(pady=10, anchor="w")

        # Статус / вывод результата
        self.quick_file_status_label = ctk.CTkLabel(
            self.main_frame,
            text="Результат: —",
            justify="left"
        )
        self.quick_file_status_label.pack(anchor="w", pady=(10, 0))

    def choose_quick_file(self):
        """Выбор файла для быстрой проверки."""
        path = filedialog.askopenfilename(title="Выберите файл для проверки")
        if not path:
            return
        self.quick_file_path = path
        if hasattr(self, "quick_file_label") and self.quick_file_label.winfo_exists():
            self.quick_file_label.configure(text=path)

    def start_quick_file_scan(self):
        """Запускает проверку файла в отдельном потоке, чтобы не вешать GUI."""
        if not getattr(self, "quick_file_path", None):
            messagebox.showwarning("Файл не выбран", "Сначала выбери файл для проверки.")
            return

        if hasattr(self, "quick_file_status_label") and self.quick_file_status_label.winfo_exists():
            self.quick_file_status_label.configure(text="Результат: выполняется проверка... ⏳")

        t = threading.Thread(target=self._quick_file_scan_worker, daemon=True)
        t.start()

    def _quick_file_scan_worker(self):
        """Рабочий поток для проверки файла через существующий движок сканера."""
        path = getattr(self, "quick_file_path", None)
        if not path:
            return

        try:
            res = self.scanner.scan_file(path)
        except Exception as e:
            res = {"status": "error", "threat": f"Ошибка движка: {type(e).__name__}"}

        # Для красоты можно сразу посчитать SHA-256
        try:
            file_hash = self.scanner.get_hash(path)
        except Exception:
            file_hash = None

        def _update_ui():
            if not hasattr(self, "quick_file_status_label") or not self.quick_file_status_label.winfo_exists():
                return

            if res is None:
                text = "Результат: файл не найден или был пропущен."
            else:
                status = res.get("status", "unknown")
                threat = res.get("threat") or "Неизвестно"

                status_human = {
                    "clean": "Файл выглядит чистым ✅",
                    "infected": "Обнаружена угроза! 🔥",
                    "suspicious": "Подозрительное поведение ⚠️",
                    "quarantined": "Файл отправлен в карантин 🧊",
                    "skipped": "Проверка пропущена (белый список / лимит VT) ⏭",
                    "error": "Ошибка при проверке ❌",
                }.get(status, f"Статус: {status}")

                text_lines = [
                    status_human,
                    f"Детали: {threat}",
                ]
                if file_hash:
                    text_lines.append(f"SHA-256: {file_hash}")

                text = "Результат: " + "\n".join(text_lines)

            self.quick_file_status_label.configure(text=text)

        try:
            self.after(0, _update_ui)
        except Exception:
            pass

# --- Вкладка: БЕЛЫЙ СПИСОК (ПРЕМИУМ) ---
    def show_whitelist_editor(self):
        # ... (код для show_whitelist_editor остается без изменений, кроме стилей кнопок/рамок)
        if not self.settings.get("premium", {}).get("active", False) and not self.settings.get("premium", {}).get("santa_mode", False):
            self.show_premium_gate("Белый Список")
            return

        self.clear_main()
        ctk.CTkLabel(self.main_frame, text="✅ Редактор Белого Списка 🎁", font=("Arial", 24, "bold")).pack(anchor="w", pady=(0,20))
        
        btn_frame = ctk.CTkFrame(self.main_frame)
        btn_frame.pack(anchor="w", pady=10)
        ctk.CTkButton(btn_frame, text="Добавить Файл", command=lambda: self.add_path_to_whitelist(False)).pack(side="left", padx=10, pady=10)
        ctk.CTkButton(btn_frame, text="Добавить Папку", command=lambda: self.add_path_to_whitelist(True)).pack(side="left", padx=10, pady=10)
        
        ctk.CTkLabel(self.main_frame, text="Пути, исключенные из сканирования:", font=("Arial", 14, "bold")).pack(anchor="w", pady=10)
        
        self.whitelist_listbox_frame = ctk.CTkScrollableFrame(self.main_frame, label_text="")
        self.whitelist_listbox_frame.pack(fill="both", expand=True)
        
        self.load_whitelist_list()

    def load_whitelist_list(self):
        for widget in self.whitelist_listbox_frame.winfo_children():
            widget.destroy()
            
        self.current_whitelist = DataManager.load_whitelist()
        
        if not self.current_whitelist:
            ctk.CTkLabel(self.whitelist_listbox_frame, text="Белый список пуст. Только чистые файлы!").pack(pady=20)
            return

        for i, path in enumerate(self.current_whitelist):
            row_color = ("#D5F5E3", "#145A32") if self.settings["ui"]["christmas_style"] else ("gray90", "gray20") # СВЕТЛО/ТЕМНО-зеленый
            row = ctk.CTkFrame(self.whitelist_listbox_frame, fg_color=row_color)
            row.pack(fill="x", pady=2, padx=5)
            
            ctk.CTkLabel(row, text=path, anchor="w").pack(side="left", padx=5, fill="x", expand=True)
            ctk.CTkButton(row, text="Удалить", fg_color="red", width=80, 
                          command=lambda p=path: self.remove_path_from_whitelist(p)).pack(side="right", padx=5)

    def add_path_to_whitelist(self, is_folder):
        path = filedialog.askdirectory() if is_folder else filedialog.askopenfilename()
        # Улучшение: нормализация пути
        path = os.path.normpath(path)
        if path and path not in self.current_whitelist:
            self.current_whitelist.append(path)
            DataManager.save_whitelist(self.current_whitelist)
            self.load_whitelist_list()
            messagebox.showinfo("Успех", f"Путь добавлен в белый список: {os.path.basename(path)}")
            
    def remove_path_from_whitelist(self, path):
        if path in self.current_whitelist:
            self.current_whitelist.remove(path)
            DataManager.save_whitelist(self.current_whitelist)
            self.load_whitelist_list()

    # --- Вкладка: МОНИТОРИНГ СЕТИ (ПРЕМИУМ) ---
    def show_network_monitor(self):
        if not self.settings.get("premium", {}).get("active", False) and not self.settings.get("premium", {}).get("santa_mode", False):
            self.show_premium_gate("Мониторинг Сети")
            return
            
        self.clear_main()
        ctk.CTkLabel(self.main_frame, text="🌐 Мониторинг Сети - Санный Путь", font=("Arial", 24, "bold")).pack(anchor="w", pady=(0,20))
        
        scroll = ctk.CTkScrollableFrame(self.main_frame)
        scroll.pack(fill="both", expand=True)
        
        ctk.CTkLabel(scroll, text="Активные Сетевые Соединения (Полетные Маршруты Санты):", font=("Arial", 16, "bold")).pack(anchor="w", pady=(10, 5), padx=5)

        connections = psutil.net_connections(kind='inet')
        if not connections:
            ctk.CTkLabel(scroll, text="Активные соединения не обнаружены. Проверьте, не спрятался ли Санта.", text_color="gray").pack(pady=5)
            
        for conn in connections:
            try:
                p = psutil.Process(conn.pid)
                pname = p.name()
                
                # НОВАЯ ПАСХАЛКА: Santa Mode - подменяем имена процессов
                if self.settings["premium"].get("santa_mode", False) and random.random() < 0.1:
                    santa_names = ["Deer_Sleigh.exe", "Magic_Firewall.sys", "Gift_Transmitter.dll", "Naughty_List_Reader.py"]
                    pname = random.choice(santa_names)
                    
            except:
                pname = "N/A"

            local_addr = f"{conn.laddr.ip}:{conn.laddr.port}" if conn.laddr else "N/A"
            remote_addr = f"{conn.raddr.ip}:{conn.raddr.port}" if conn.raddr else "N/A"
            
            row_text = f"[{conn.status:<10}] PID: {conn.pid:<5} | Процесс: {pname:<20} | Локальный: {local_addr:<25} | Удаленный: {remote_addr}"
            
            color = "white"
            if conn.status in ('CLOSE_WAIT', 'FIN_WAIT1', 'TIME_WAIT'):
                color = "gray"
            elif conn.status in ('ESTABLISHED', 'LISTEN'):
                color = "#2ECC71" # Ярко-зеленый
            
            ctk.CTkLabel(scroll, text=row_text, anchor="w", font=("Consolas", 10), text_color=color).pack(fill="x", padx=10, pady=1)

    # --- Вкладка: МЕНЕДЖЕР АВТОЗАГРУЗКИ (ПРЕМИУМ) ---
    def show_startup_manager(self):
        if not WINDOWS_OS:
            self.clear_main()
            ctk.CTkLabel(self.main_frame, text="⚠️ Менеджер Автозагрузки доступен только в Windows.", font=("Arial", 24, "bold")).pack(anchor="w", pady=(0,20))
            return
            
        if not self.settings.get("premium", {}).get("active", False) and not self.settings.get("premium", {}).get("santa_mode", False):
            self.show_premium_gate("Менеджер Автозагрузки")
            return

        self.clear_main()
        ctk.CTkLabel(self.main_frame, text="🚀 Менеджер Автозагрузки", font=("Arial", 24, "bold")).pack(anchor="w", pady=(0,20))
        
        self.startup_scroll = ctk.CTkScrollableFrame(self.main_frame)
        self.startup_scroll.pack(fill="both", expand=True)
        
        self.load_startup_items()

    def load_startup_items(self):
        for w in self.startup_scroll.winfo_children(): w.destroy()
        
        path = r"Software\Microsoft\Windows\CurrentVersion\Run"
        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, path, 0, winreg.KEY_ALL_ACCESS)
            count = winreg.QueryInfoKey(key)[1]
            
            if count == 0:
                ctk.CTkLabel(self.startup_scroll, text="Автозагрузка пуста.").pack(pady=20)

            for i in range(count):
                name, val, _ = winreg.EnumValue(key, i)
                
                row = ctk.CTkFrame(self.startup_scroll, fg_color=("gray90", "gray20"))
                row.pack(fill="x", pady=2, padx=5)
                
                ctk.CTkLabel(row, text=name, font=("Arial", 11, "bold"), width=150, anchor="w").pack(side="left", padx=5)
                ctk.CTkLabel(row, text=val, anchor="w").pack(side="left", padx=5, fill="x", expand=True)
                
                ctk.CTkButton(row, text="Удалить", fg_color="red", width=80, 
                              command=lambda n=name: self.remove_startup_item(n)).pack(side="right", padx=5)
            winreg.CloseKey(key)
        except Exception as e:
            ctk.CTkLabel(self.startup_scroll, text=f"Ошибка доступа к реестру: {e}").pack()

    def remove_startup_item(self, name):
        if messagebox.askyesno("Подтверждение", f"Удалить '{name}' из автозагрузки?"):
            path = r"Software\Microsoft\Windows\CurrentVersion\Run"
            try:
                key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, path, 0, winreg.KEY_ALL_ACCESS)
                winreg.DeleteValue(key, name)
                winreg.CloseKey(key)
                self.load_startup_items()
                messagebox.showinfo("Успех", f"'{name}' удалено из автозагрузки.")
            except Exception as e:
                messagebox.showerror("Ошибка", f"Не удалось удалить: {e}")

    

    # --- Вкладка: ЭКСТРЕННАЯ ЗАЩИТА ---
    def show_panic_center(self):
        """Панель для быстрого анализа и жёсткой зачистки подозрительных процессов."""
        self.clear_main()

        ctk.CTkLabel(
            self.main_frame,
            text="🛑 Экстренная защита системы",
            font=("Arial", 24, "bold")
        ).pack(anchor="w", pady=(0, 10))

        info = (
            "Этот режим быстро просматривает активные процессы и пытается найти подозрительные\n"
            "по пути запуска и названию. Используй осторожно: завершение процессов может закрыть программы."
        )
        ctk.CTkLabel(
            self.main_frame,
            text=info,
            justify="left"
        ).pack(anchor="w", pady=(0, 10))

        btn_frame = ctk.CTkFrame(self.main_frame)
        btn_frame.pack(fill="x", pady=(0, 10))

        ctk.CTkButton(
            btn_frame,
            text="🔍 Просканировать процессы",
            command=self.panic_scan_processes
        ).pack(side="left", padx=5, pady=5)

        ctk.CTkButton(
            btn_frame,
            text="💣 Завершить подозрительные",
            fg_color="#c0392b",
            hover_color="#e74c3c",
            command=self.panic_kill_suspicious
        ).pack(side="left", padx=5, pady=5)

        # Список результатов
        self.panic_scroll = ctk.CTkScrollableFrame(self.main_frame)
        self.panic_scroll.pack(fill="both", expand=True, pady=(5, 0))

        # Хранилище найденных подозрительных процессов
        self.panic_suspicious = []

    def panic_scan_processes(self):
        """Находит подозрительные процессы по простым, но жёстким правилам."""
        # Очищаем предыдущие результаты
        try:
            for w in self.panic_scroll.winfo_children():
                w.destroy()
        except Exception:
            pass

        self.panic_suspicious = []

        # Простые справочники путей
        user_home = os.path.expanduser("~")
        suspicious_roots = [
            os.path.join(user_home, "AppData", "Local", "Temp"),
            os.path.join(user_home, "AppData", "Roaming"),
            os.path.join(user_home, "Downloads"),
            os.path.join(user_home, "Desktop"),
        ]

        safe_roots = [
            os.environ.get("SystemRoot", r"C:\Windows"),
            os.environ.get("ProgramFiles", r"C:\Program Files"),
            os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)"),
        ]

        # Подозрительные куски в имени процесса
        bad_name_fragments = [
            "miner", "crypto", "stealer", "keylog", "rat", "hack", "cracker",
            "upd", "update", "patcher"
        ]

        rows = 0

        try:
            for proc in psutil.process_iter(["pid", "name", "exe"]):
                pid = proc.info.get("pid")
                name = (proc.info.get("name") or "").lower()
                exe = proc.info.get("exe") or ""

                reason_list = []

                # 1) Запущен из подозрительного каталога пользователя
                for root in suspicious_roots:
                    try:
                        if exe.lower().startswith(root.lower()):
                            reason_list.append(f"запущен из подозрительного каталога: {root}")
                            break
                    except Exception:
                        continue

                # 2) EXE не из системных/Program Files, но лежит где-то в профиле
                if exe and exe.lower().endswith(".exe"):
                    in_safe_root = any(exe.lower().startswith((r or "").lower()) for r in safe_roots if r)
                    if (user_home.lower() in exe.lower()) and not in_safe_root:
                        reason_list.append("исполняемый файл в профиле пользователя вне Program Files")

                # 3) Странное имя процесса
                if any(fragment in name for fragment in bad_name_fragments):
                    reason_list.append(f"подозрительное имя процесса: {name}")

                if not reason_list:
                    continue

                # Добавляем в список подозрительных
                self.panic_suspicious.append(
                    {"pid": pid, "name": name or "?", "exe": exe or "?", "reasons": reason_list}
                )

                row = ctk.CTkFrame(self.panic_scroll, fg_color=("gray90", "gray20"))
                row.pack(fill="x", pady=2, padx=5)
                rows += 1

                # Основная информация о процессе
                ctk.CTkLabel(row, text=f"PID: {pid}", width=80, anchor="w").pack(side="left", padx=5)
                ctk.CTkLabel(row, text=name or "?", width=180, anchor="w").pack(side="left", padx=5)
                ctk.CTkLabel(row, text=exe or "?", anchor="w").pack(side="left", padx=5, fill="x", expand=True)

                reason_text = "; ".join(reason_list[:3])
                ctk.CTkLabel(row, text=reason_text, text_color="#e67e22", anchor="w").pack(side="left", padx=5)

                # Кнопки действий над процессом
                btns = ctk.CTkFrame(row)
                btns.pack(side="right", padx=5)

                if exe:
                    ctk.CTkButton(
                        btns,
                        text="Папка",
                        width=70,
                        command=lambda p=exe: self.open_process_folder(p)
                    ).pack(side="top", pady=2, padx=2)

                    ctk.CTkButton(
                        btns,
                        text="В бел. список",
                        width=110,
                        command=lambda p=exe: self.add_exe_to_whitelist_from_panic(p)
                    ).pack(side="top", pady=2, padx=2)

        except Exception as e:
            ctk.CTkLabel(
                self.panic_scroll,
                text=f"Ошибка при анализе процессов: {type(e).__name__}",
                text_color="red"
            ).pack(pady=10)

        if rows == 0:
            ctk.CTkLabel(
                self.panic_scroll,
                text="Подозрительных процессов не найдено. Похоже, всё спокойно 💤",
                text_color="gray"
            ).pack(pady=20)

    def panic_kill_suspicious(self):
        """Пытается завершить все процессы, которые пометил panic_scan_processes."""
        if not getattr(self, "panic_suspicious", None):
            messagebox.showinfo("Экстренная защита", "Сначала просканируй процессы. Подозрительных пока нет.")
            return

        if not messagebox.askyesno(
            "Подтверждение",
            "Будет предпринята попытка завершить ВСЕ подозрительные процессы.\n"
            "Это может закрыть программы, в том числе несохранённые. Продолжить?"
        ):
            return

        killed = 0
        failed = 0

        for item in list(self.panic_suspicious):
            pid = item.get("pid")
            try:
                p = psutil.Process(pid)
                p.terminate()
                try:
                    p.wait(timeout=3)
                except Exception:
                    pass
                killed += 1
            except Exception:
                failed += 1

        messagebox.showinfo(
            "Экстренная защита",
            f"Попытка завершения процессов завершена.\n"
            f"Успешно завершено: {killed}\n"
            f"Не удалось завершить: {failed}"
        )



    def add_exe_to_whitelist_from_panic(self, exe_path):
        """Добавляет путь исполняемого файла процесса в Белый список прямо из Экстренной защиты."""
        if not exe_path or exe_path == "?":
            messagebox.showerror("Белый список", "Не удалось определить путь файла процесса.")
            return

        norm = os.path.normpath(exe_path)

        # Загружаем текущий whitelist
        settings = DataManager.load_settings()
        whitelist = settings.get("whitelist", [])

        if norm in whitelist:
            messagebox.showinfo("Белый список", "Этот путь уже есть в Белом списке.")
            return

        whitelist.append(norm)
        DataManager.save_whitelist(whitelist)

        # Обновляем локальные настройки приложения
        self.settings["whitelist"] = whitelist
        try:
            self.current_whitelist = whitelist
        except Exception:
            pass

        messagebox.showinfo(
            "Белый список",
            f"Путь добавлен в Белый список:\n{norm}"
        )

    def open_process_folder(self, exe_path):
        """Открывает проводник в папке, где лежит файл процесса."""
        if not exe_path or exe_path == "?":
            messagebox.showerror("Папка процесса", "Не удалось определить путь файла процесса.")
            return

        folder = os.path.dirname(exe_path)
        if not folder or not os.path.isdir(folder):
            messagebox.showerror("Папка процесса", "Папка для этого файла не найдена.")
            return

        try:
            if WINDOWS_OS:
                os.startfile(folder)
            else:
                # На всякий случай поддержка других платформ
                import subprocess as _sub
                _sub.Popen(["xdg-open", folder])
        except Exception as e:
            messagebox.showerror("Папка процесса", f"Не удалось открыть папку:\n{e}")

# --- Вкладка: ИСТОРИЯ ---
    def show_history(self):
        self.clear_main()
        ctk.CTkLabel(self.main_frame, text="Журнал угроз 📜", font=("Arial", 24, "bold")).pack(anchor="w", pady=(0,20))
        
        scroll = ctk.CTkScrollableFrame(self.main_frame)
        scroll.pack(fill="both", expand=True)
        
        history = DataManager.load_history()
        if not history:
            ctk.CTkLabel(scroll, text="Журнал пуст. Угроз не обнаружено. Вы в списке хороших!", text_color="gray").pack(pady=20)
            return

        for item in history:
            row = ctk.CTkFrame(scroll, fg_color=("gray90", "gray20"))
            row.pack(fill="x", pady=2, padx=5)
            
            ctk.CTkLabel(row, text=item.get('date', 'N/A'), width=120, anchor="w").pack(side="left", padx=5)
            
            status_map = {"infected": "red", "suspicious": "orange", "quarantined": "#F1C40F"}
            color = status_map.get(item['status'], "white")
            
            # Улучшение: Более наглядное отображение статуса
            status_text = item['status'].upper()
            if status_text == "QUARANTINED": status_text = "🔒 КАРАНТИН"
            
            ctk.CTkLabel(row, text=status_text, text_color=color, width=100, font=("bold", 12)).pack(side="left", padx=5)
            
            ctk.CTkLabel(row, text=os.path.basename(item['file']), anchor="w").pack(side="left", padx=5, fill="x", expand=True)
            ctk.CTkLabel(row, text=item.get('threat', 'Unknown'), text_color="gray").pack(side="right", padx=5)


    # --- Вкладка: ДИСПЕТЧЕР ЗАДАЧ ---
    def show_task_manager(self):
        self.clear_main()
        ctk.CTkLabel(self.main_frame, text="📊 Диспетчер задач", font=("Arial", 24, "bold")).pack(anchor="w", pady=(0, 20))

        info = (
            "Это упрощённый диспетчер задач внутри антивируса:\n"
            "• Показывает процессы с использованием памяти.\n"
            "• Помогает понять, что нагружает систему перед игрой.\n"
            "\n"
            "Внимание: программа НИЧЕГО не завершает автоматически — только показывает информацию."
        )
        ctk.CTkLabel(self.main_frame, text=info, font=("Arial", 13), justify="left").pack(anchor="w", pady=(0, 10))

        btn_frame = ctk.CTkFrame(self.main_frame)
        btn_frame.pack(fill="x", pady=10)
        ctk.CTkButton(btn_frame, text="🔄 Обновить список", command=self.update_tasklist).pack(side="left", padx=10, pady=10)
        if WINDOWS_OS:
            ctk.CTkButton(btn_frame, text="🧰 Открыть стандартный диспетчер задач", 
                          command=lambda: subprocess.Popen("taskmgr")).pack(side="left", padx=10, pady=10)

        self.taskmgr_text = ctk.CTkTextbox(self.main_frame, height=360)
        self.taskmgr_text.pack(fill="both", expand=True, padx=10, pady=(5, 10))

        self.update_tasklist()

    def update_tasklist(self):
        if not hasattr(self, "taskmgr_text") or self.taskmgr_text is None:
            return

        self.taskmgr_text.delete("1.0", "end")
        self.taskmgr_text.insert("end", "Сканирование процессов...\n\n")

        rows = []
        try:
            for p in psutil.process_iter(["pid", "name", "memory_info"]):
                try:
                    info = p.info
                    name = info.get("name") or "unknown"
                    mem = info.get("memory_info")
                    if mem is None:
                        continue
                    mem_mb = mem.rss / (1024 * 1024)
                    rows.append((mem_mb, name, info.get("pid")))
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
        except Exception as e:
            self.taskmgr_text.insert("end", f"Ошибка анализа процессов: {e}\n")
            return

        if not rows:
            self.taskmgr_text.insert("end", "Не удалось получить список процессов.\n")
            return

        rows.sort(reverse=True)

        self.taskmgr_text.insert("end", "Имя процесса / PID / Память (МБ)\n")
        self.taskmgr_text.insert("end", "---------------------------------\n\n")
        for mem_mb, name, pid in rows[:80]:
            self.taskmgr_text.insert("end", f"{name} (PID {pid}) — ~{mem_mb:.1f} МБ RAM\n")

        self.taskmgr_text.insert("end", "\nЗакрывать процессы рекомендуется через стандартный диспетчер задач Windows.\n")


    # --- Вкладка: ИНФОРМАЦИЯ О СИСТЕМЕ ---
    def show_system(self):
        self.clear_main()
        ctk.CTkLabel(self.main_frame, text="Информация о системе 💻", font=("Arial", 24, "bold")).pack(anchor="w", pady=(0,20))
        
        info_frame = ctk.CTkFrame(self.main_frame)
        info_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        uname = platform.uname()
        cpufreq = psutil.cpu_freq()
        mem = psutil.virtual_memory()
        
        data = [
            ("Система", f"{uname.system} {uname.release}"),
            ("Имя ПК", uname.node),
            ("Версия", uname.version),
            ("Архитектура", platform.machine()), # Добавлено: Архитектура
            ("Процессор", uname.processor),
            ("Ядра (Phys/Log)", f"{psutil.cpu_count(logical=False)} / {psutil.cpu_count(logical=True)}"),
            ("Частота CPU (max)", f"{cpufreq.max:.2f} Mhz" if cpufreq else "N/A"), # Улучшение: max частота
            ("ОЗУ (Всего)", f"{mem.total / (1024**3):.2f} GB"),
            ("ОЗУ (Доступно)", f"{mem.available / (1024**3):.2f} GB"),
        ]
        
        for i, (k, v) in enumerate(data):
            f = ctk.CTkFrame(info_frame, fg_color="transparent")
            f.pack(fill="x", pady=5, padx=10)
            ctk.CTkLabel(f, text=k, font=("Arial", 14, "bold"), width=150, anchor="w").pack(side="left")
            ctk.CTkLabel(f, text=v, font=("Arial", 14), anchor="w").pack(side="left")
            if i < len(data) - 1:
                ctk.CTkFrame(info_frame, height=1, fg_color=("gray70", "gray30")).pack(fill="x", padx=10)

    # --- Вкладка: НАСТРОЙКИ ---
    def show_settings(self):
        self.clear_main()
        ctk.CTkLabel(self.main_frame, text="Настройки программы ⚙️", font=("Arial", 24, "bold")).pack(anchor="w", pady=(0,20))
        
        scroll = ctk.CTkScrollableFrame(self.main_frame)
        scroll.pack(fill="both", expand=True)
        
        is_premium = self.settings.get("premium", {}).get("active", False)
        is_santa = self.settings.get("premium", {}).get("santa_mode", False)
        premium_status_text = "АКТИВНО (Режим Деда Мороза 🎅)" if is_santa else ("АКТИВНО" if is_premium else "НЕ АКТИВНО")
        premium_status_color = "#E74C3C" if is_santa else ("green" if is_premium else "red")
        
        # Секция: PREMIUM
        self.add_setting_header(scroll, "⭐️ CYBER SENTINEL PRO (Premium)")
        
        ctk.CTkLabel(scroll, text=f"Статус: {premium_status_text}", text_color=premium_status_color, font=("Arial", 14, "bold")).pack(anchor="w", padx=20, pady=5)
        
        premium_frame = ctk.CTkFrame(scroll, fg_color="transparent")
        premium_frame.pack(anchor="w", padx=20, pady=5)
        
        self.entry_premium_key = ctk.CTkEntry(premium_frame, placeholder_text="Введите Премиум ключ", width=400)
        self.entry_premium_key.insert(0, self.settings["premium"]["key"]) 
        self.entry_premium_key.pack(side="left", padx=(0, 10))
        
        ctk.CTkButton(premium_frame, text="Активировать", command=self.activate_premium).pack(side="left")
        
        # Секция: Мониторинг сети и защита
        self.add_setting_header(scroll, "🌐 Дополнительные модули")
        
        # Real-time Guard
        guard_active = is_premium or is_santa
        guard_text = "🛡️ Real-time Guard (Папка Загрузки) - 🔒 PREMIUM" if not guard_active else "🛡️ Real-time Guard (Папка Загрузки)"
        if not guard_active: self.settings["premium"]["realtime_guard"] = False
        self.var_guard = ctk.BooleanVar(value=self.settings["premium"].get("realtime_guard", False))
        ctk.CTkSwitch(scroll, text=guard_text, variable=self.var_guard, state="normal" if guard_active else "disabled").pack(anchor="w", padx=20, pady=5)

        # Network Monitor
        nm_active = is_premium or is_santa
        nm_text = "🌐 Мониторинг Сети - 🔒 PREMIUM" if not nm_active else "🌐 Мониторинг Сети"
        if not nm_active: self.settings["premium"]["network_monitor"] = False
        self.var_nm = ctk.BooleanVar(value=self.settings["premium"]["network_monitor"])
        ctk.CTkSwitch(scroll, text=nm_text, variable=self.var_nm, state="normal" if nm_active else "disabled").pack(anchor="w", padx=20, pady=5)

        # Секция: API
        self.add_setting_header(scroll, "☁️ VirusTotal API")
        
        api_input_frame = ctk.CTkFrame(scroll, fg_color="transparent")
        api_input_frame.pack(anchor="w", padx=20, pady=5)

        self.entry_api = ctk.CTkEntry(api_input_frame, placeholder_text="Введите API ключ VirusTotal", width=400)
        self.entry_api.insert(0, self.settings.get("api_key", ""))
        self.entry_api.pack(side="left", padx=(0, 10))
        
        ctk.CTkButton(api_input_frame, text="Получить ключ", command=lambda: self.open_link("https://www.virustotal.com/gui/join-us"),
                      fg_color="#3498db", hover_color="#2980b9").pack(side="left")

        # Секция: MalwareBazaar
        self.add_setting_header(scroll, "☁️ MalwareBazaar API (Hash база)")

        self.var_mb_enabled = ctk.BooleanVar(value=self.settings.get("malwarebazaar", {}).get("enabled", True))
        ctk.CTkSwitch(scroll, text="Проверять хеши через MalwareBazaar", variable=self.var_mb_enabled).pack(anchor="w", padx=20, pady=(0, 5))

        mb_input_frame = ctk.CTkFrame(scroll, fg_color="transparent")
        mb_input_frame.pack(anchor="w", padx=20, pady=5)

        self.entry_mb_api = ctk.CTkEntry(mb_input_frame, placeholder_text="Введите Auth-Key MalwareBazaar", width=400)
        self.entry_mb_api.insert(0, self.settings.get("malwarebazaar", {}).get("api_key", ""))
        self.entry_mb_api.pack(side="left", padx=(0, 10))

        ctk.CTkButton(mb_input_frame, text="Получить ключ", command=lambda: self.open_link("https://bazaar.abuse.ch/api/#auth-key"),
                      fg_color="#16a085", hover_color="#138d75").pack(side="left")

        # Секция: Сканирование
        self.add_setting_header(scroll, "🛡️ Параметры защиты")
        
        self.var_heur = ctk.BooleanVar(value=self.settings["scan"]["use_heuristics"])
        ctk.CTkSwitch(scroll, text="Использовать эвристику (Offline поиск)", variable=self.var_heur).pack(anchor="w", padx=20, pady=5)
        
        deep_scan_active = is_premium or is_santa
        deep_scan_text = "Глубокое сканирование (Всегда проверять через VT) - 🔒 PREMIUM" if not deep_scan_active else "Глубокое сканирование (Всегда проверять через VT)"
        
        if not deep_scan_active:
            self.settings["scan"]["deep_scan"] = False
        
        self.var_deep = ctk.BooleanVar(value=self.settings["scan"]["deep_scan"])
        ctk.CTkSwitch(scroll, text=deep_scan_text, variable=self.var_deep, 
                                    state="normal" if deep_scan_active else "disabled").pack(anchor="w", padx=20, pady=5)

        self.var_quarantine = ctk.BooleanVar(value=self.settings["scan"].get("auto_quarantine", False))
        ctk.CTkSwitch(scroll, text="Автоматический карантин (Без спроса)", variable=self.var_quarantine).pack(anchor="w", padx=20, pady=5)
        
        # Улучшение: Сканирование архивов - Premium (сложная реализация, помечаем как Premium)
        scan_archives_active = is_premium or is_santa
        archive_text = "Сканировать внутри архивов (Медленно) - 🔒 PREMIUM" if not scan_archives_active else "Сканировать внутри архивов (Медленно)"

        if not scan_archives_active: self.settings["scan"]["scan_archives"] = False
        self.var_archives = ctk.BooleanVar(value=self.settings["scan"].get("scan_archives", False))
        ctk.CTkSwitch(scroll, text=archive_text, variable=self.var_archives, state="normal" if scan_archives_active else "disabled").pack(anchor="w", padx=20, pady=5)
        
        # Секция: Интерфейс (добавлена опция Christmas Style)
        self.add_setting_header(scroll, "🎨 Интерфейс")
        
        self.var_christmas_style = ctk.BooleanVar(value=self.settings["ui"].get("christmas_style", False))
        ctk.CTkSwitch(scroll, text="🎄 Новогодний стиль", variable=self.var_christmas_style).pack(anchor="w", padx=20, pady=5)
        
        ctk.CTkLabel(scroll, text="Тема оформления:").pack(anchor="w", padx=20)
        self.theme_opt = ctk.CTkOptionMenu(scroll, values=["System", "Dark", "Light"])
        self.theme_opt.set(self.settings["ui"]["theme"])
        self.theme_opt.pack(anchor="w", padx=20, pady=5)

        # Кнопка сохранения
        ctk.CTkButton(scroll, text="💾 Сохранить и Применить", command=self.save_settings, 
                      height=40, fg_color="#2ECC71", hover_color="#27AE60").pack(pady=30)

    def add_setting_header(self, parent, text):
        ctk.CTkLabel(parent, text=text, font=("Arial", 16, "bold"), text_color="#F1C40F" if self.settings["ui"]["christmas_style"] else "gray").pack(anchor="w", padx=10, pady=(20, 5))
        ctk.CTkFrame(parent, height=2, fg_color=("gray70", "gray30")).pack(fill="x", padx=10, pady=(0, 10))

    def activate_premium(self):
        key = self.entry_premium_key.get().strip()
        
        self.settings["premium"]["key"] = key 
        
        is_santa_key = key == "SANTA-CLAUS-IS-WATCHING-YOU"
        
        if key in DataManager.VALID_PREMIUM_KEYS:
            self.settings["premium"]["active"] = True
            self.settings["premium"]["santa_mode"] = is_santa_key
            
            if DataManager.save_settings(self.settings): 
                if is_santa_key:
                    messagebox.showinfo("Активация", "🎅 Режим Деда Мороза активирован! С наступающим!")
                else:
                    messagebox.showinfo("Активация", "✅ Премиум-подписка активирована!")
            else:
                messagebox.showwarning("Активация", "✅ Активация прошла, но ключ не сохранен.")
        else:
            self.settings["premium"]["active"] = False
            self.settings["premium"]["network_monitor"] = False
            self.settings["premium"]["realtime_guard"] = False
            self.settings["premium"]["santa_mode"] = False
            self.settings["scan"]["deep_scan"] = False
            self.settings["scan"]["scan_archives"] = False
            DataManager.save_settings(self.settings) 
            messagebox.showerror("Активация", "❌ Неверный ключ. Вы в списке 'Непослушных'.")
            
        self.setup_ui() 

    def save_settings(self):
        self.settings["api_key"] = self.entry_api.get().strip()

        # MalwareBazaar
        self.settings.setdefault("malwarebazaar", {})
        if hasattr(self, "entry_mb_api"):
            self.settings["malwarebazaar"]["api_key"] = self.entry_mb_api.get().strip()
        if hasattr(self, "var_mb_enabled"):
            self.settings["malwarebazaar"]["enabled"] = bool(self.var_mb_enabled.get())

        self.settings["scan"]["use_heuristics"] = self.var_heur.get()
        self.settings["scan"]["auto_quarantine"] = self.var_quarantine.get()
        self.settings["ui"]["christmas_style"] = self.var_christmas_style.get()

        is_premium_active = self.settings.get("premium", {}).get("active", False) or self.settings.get("premium", {}).get("santa_mode", False)

        if is_premium_active:
            self.settings["scan"]["deep_scan"] = self.var_deep.get()
            self.settings["premium"]["network_monitor"] = self.var_nm.get() 
            self.settings["scan"]["scan_archives"] = self.var_archives.get()
            
            old_guard = self.settings["premium"].get("realtime_guard", False)
            new_guard = self.var_guard.get()
            self.settings["premium"]["realtime_guard"] = new_guard
            
            if new_guard and not old_guard:
                self.scanner.start_realtime_guard()
            elif not new_guard and old_guard:
                self.scanner.stop_realtime_guard()
        else:
            # Сброс премиум-настроек, если премиум неактивен
            self.settings["scan"]["deep_scan"] = False
            self.settings["premium"]["network_monitor"] = False
            self.settings["premium"]["realtime_guard"] = False
            self.settings["scan"]["scan_archives"] = False
            self.scanner.stop_realtime_guard()

        self.settings["ui"]["theme"] = self.theme_opt.get()
        
        if DataManager.save_settings(self.settings):
             messagebox.showinfo("Настройки", "Конфигурация сохранена. Применяю изменения.")
        
        # Перезапуск UI для применения темы и стилей
        self.setup_ui()
        self.show_dashboard()

    def show_premium_gate(self, feature_name):
        """Отображает заглушку для Премиум-функций"""
        self.clear_main()
        ctk.CTkLabel(self.main_frame, text=f"🔒 {feature_name} - Требуется CYBER SENTINEL PRO", 
                     font=("Arial", 28, "bold"), text_color="red").pack(pady=50)
        ctk.CTkLabel(self.main_frame, text="Активируйте премиум-ключ в Настройках, чтобы получить полный доступ!", 
                     font=("Arial", 16)).pack(pady=20)
        ctk.CTkButton(self.main_frame, text="Перейти в Настройки", command=self.show_settings, 
                      fg_color="#3498db", height=40).pack(pady=10)

    # --- ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ---

    def quick_scan_start(self):
        paths = [
            os.getenv('TEMP'), 
            os.path.join(os.path.expanduser('~'), 'Downloads')
        ]
        
        self.show_scanner()
        self.scan_log.delete("1.0", "end")
        self.scan_log.insert("end", "Запуск быстрого сканирования критических зон (Поиск угольков)... \n")
        
        files = []
        for p in paths:
            if os.path.exists(p):
                # Улучшение: os.walk для Temp, чтобы не пропустить вложенные папки
                for root, _, fnames in os.walk(p):
                    for f in fnames:
                        full_path = os.path.join(root, f)
                        if os.path.isfile(full_path):
                             files.append(full_path)
        
        if files:
            threading.Thread(target=self.scanner.start_scan, args=(files,), daemon=True).start()
        else:
            self.scan_log.insert("end", "⚠️ Файлы для быстрого сканирования не найдены.\n")


    # =============================
    # 🗂️ QUARANTINE CENTER (8.5 HF)
    # =============================
    def show_quarantine_center(self):
        self.clear_main()
        self.section("🗂️ Карантин", "Здесь лежат изолированные файлы. Можно восстановить или удалить.")

        index = DataManager.load_quarantine_index()
        index = index if isinstance(index, dict) else {}
        self._quarantine_index_cache = index

        top = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        top.pack(fill="x", padx=10, pady=(0, 10))

        ctk.CTkButton(top, text="🔄 Обновить", command=self._quarantine_refresh_list).pack(side="left", padx=5)
        ctk.CTkButton(top, text="🧹 Очистить пустые записи", command=self._quarantine_purge_missing).pack(side="left", padx=5)

        self._quarantine_scroll = ctk.CTkScrollableFrame(self.main_frame, height=520)
        self._quarantine_scroll.pack(fill="both", expand=True, padx=10, pady=10)

        self._quarantine_render(index)

    def _quarantine_refresh_list(self):
        try:
            index = DataManager.load_quarantine_index()
            index = index if isinstance(index, dict) else {}
            self._quarantine_index_cache = index
            if hasattr(self, "_quarantine_scroll"):
                for w in self._quarantine_scroll.winfo_children():
                    w.destroy()
                self._quarantine_render(index)
        except Exception:
            pass

    def _quarantine_purge_missing(self):
        try:
            index = DataManager.load_quarantine_index()
            index = index if isinstance(index, dict) else {}
            changed = False
            for k in list(index.keys()):
                item = index.get(k, {})
                qpath = item.get("qpath") or os.path.join(QUARANTINE_DIR, item.get("qfile", ""))
                if not qpath or not os.path.exists(qpath):
                    index.pop(k, None)
                    changed = True
            if changed:
                DataManager.save_quarantine_index(index)
            messagebox.showinfo("Карантин", "Готово: записи синхронизированы.")
            self._quarantine_refresh_list()
        except Exception:
            messagebox.showwarning("Карантин", "Не удалось очистить записи.")

    def _quarantine_render(self, index: dict):
        if not index:
            ctk.CTkLabel(self._quarantine_scroll, text="Карантин пуст 🟩", font=("Arial", 16, "bold")).pack(pady=30)
            return

        items = list(index.items())
        # newest first by ts (best-effort)
        def _ts(it):
            try:
                return it[1].get("ts", "")
            except Exception:
                return ""
        items.sort(key=_ts, reverse=True)

        for key, item in items:
            card = ctk.CTkFrame(self._quarantine_scroll, corner_radius=12)
            card.pack(fill="x", padx=8, pady=8)

            name = item.get("name", "file")
            threat = item.get("threat") or "Unknown"
            ts = item.get("ts", "")
            orig = item.get("original_path", "")
            sha = item.get("sha256", "")

            header = ctk.CTkFrame(card, fg_color="transparent")
            header.pack(fill="x", padx=12, pady=(10, 4))

            ctk.CTkLabel(header, text=f"🔒 {name}", font=("Arial", 15, "bold")).pack(side="left")
            ctk.CTkLabel(header, text=ts, font=("Arial", 12)).pack(side="right")

            ctk.CTkLabel(card, text=f"⚠️ Threat: {threat}", anchor="w").pack(fill="x", padx=12, pady=2)
            if orig:
                ctk.CTkLabel(card, text=f"📍 From: {orig}", anchor="w", wraplength=780).pack(fill="x", padx=12, pady=2)
            if sha:
                ctk.CTkLabel(card, text=f"🧬 SHA256: {sha}", anchor="w", wraplength=780).pack(fill="x", padx=12, pady=(2, 8))

            btns = ctk.CTkFrame(card, fg_color="transparent")
            btns.pack(fill="x", padx=12, pady=(0, 12))

            ctk.CTkButton(btns, text="♻️ Восстановить", command=lambda k=key: self._quarantine_restore_item(k)).pack(side="left", padx=5)
            ctk.CTkButton(btns, text="🗑️ Удалить", fg_color="#B00020", hover_color="#8A0019",
                          command=lambda k=key: self._quarantine_delete_item(k)).pack(side="left", padx=5)

    def _quarantine_restore_item(self, key: str):
        try:
            index = DataManager.load_quarantine_index()
            item = index.get(key, {})
            qpath = item.get("qpath") or os.path.join(QUARANTINE_DIR, item.get("qfile", ""))
            orig = item.get("original_path") or ""
            if not qpath or not os.path.exists(qpath):
                messagebox.showerror("Карантин", "Файл в карантине не найден.")
                return

            # choose restore path
            target = orig if orig and os.path.isdir(os.path.dirname(orig)) else ""
            if not target:
                target = filedialog.asksaveasfilename(initialfile=item.get("name", "restored_file"))
            if not target:
                return

            # restore
            os.makedirs(os.path.dirname(target), exist_ok=True) if os.path.dirname(target) else None
            shutil.move(qpath, target)

            # remove index entry
            index.pop(key, None)
            DataManager.save_quarantine_index(index)
            DataManager.add_history({"status": "restored", "file": target, "threat": item.get("threat", ""), "source": "quarantine"})
            messagebox.showinfo("Карантин", "Файл восстановлен ✅")
            self._quarantine_refresh_list()
        except Exception as e:
            messagebox.showerror("Карантин", f"Не удалось восстановить: {e}")

    def _quarantine_delete_item(self, key: str):
        try:
            index = DataManager.load_quarantine_index()
            item = index.get(key, {})
            qpath = item.get("qpath") or os.path.join(QUARANTINE_DIR, item.get("qfile", ""))
            if not messagebox.askyesno("Карантин", "Удалить файл из карантина навсегда?"):
                return
            if qpath and os.path.exists(qpath):
                try:
                    os.remove(qpath)
                except Exception:
                    try:
                        shutil.rmtree(qpath)
                    except Exception:
                        pass
            index.pop(key, None)
            DataManager.save_quarantine_index(index)
            DataManager.add_history({"status": "deleted", "file": item.get("name",""), "threat": item.get("threat",""), "source": "quarantine"})
            messagebox.showinfo("Карантин", "Удалено 🗑️")
            self._quarantine_refresh_list()
        except Exception as e:
            messagebox.showerror("Карантин", f"Не удалось удалить: {e}")

    # =============================
    # 📈 REBORN STATS (8.5 HF)
    # =============================
    def show_reborn_stats(self):
        self.clear_main()
        self.section("📈 REBORN статистика", "Сводка по сканам, сигналу, ядрам и карантину.")
        try:
            self.ensure_coins_data()
            coins = int(self.coins_data.get("coins", 0))
            cores = int(self.coins_data.get("reborn_cores", 0))
            signal = self._calculate_reborn_signal_percent(cores)

            # streak
            ss = self.coins_data.get("scan_streak", {}) if isinstance(self.coins_data.get("scan_streak", {}), dict) else {}
            cur = int(ss.get("current", 0))
            best = int(ss.get("best", 0))
            last = ss.get("last_scan_date", "")

            # totals (legacy: winter_scan_count)
            total_scans = int(self.coins_data.get("scan_total", self.coins_data.get("winter_scan_count", 0) or 0))

            # quarantine
            qindex = DataManager.load_quarantine_index()
            qcount = len(qindex) if isinstance(qindex, dict) else 0

            # inventory counts
            inv = self.coins_data.get("inventory", {}) if isinstance(self.coins_data.get("inventory", {}), dict) else {}
            themes = len(inv.get("themes", []) or [])
            badges = len(inv.get("badges", []) or [])
            titles = len(inv.get("titles", []) or [])
            relics = len(inv.get("relics", []) or [])

            box = ctk.CTkFrame(self.main_frame, corner_radius=14)
            box.pack(fill="x", padx=12, pady=12)

            def row(label, value):
                r = ctk.CTkFrame(box, fg_color="transparent")
                r.pack(fill="x", padx=14, pady=6)
                ctk.CTkLabel(r, text=label, font=("Arial", 13, "bold")).pack(side="left")
                ctk.CTkLabel(r, text=str(value), font=("Arial", 13)).pack(side="right")

            row("💰 Монеты", coins)
            row("🧿 REBORN cores", cores)
            row("📡 Сигнал", f"{signal}%")
            row("🧪 Всего сканов", total_scans)
            row("🔥 Streak (текущий / лучший)", f"{cur} / {best}")
            row("📅 Последний скан", last or "—")
            row("🗂️ В карантине", qcount)
            row("🎨 Themes", themes)
            row("🏷️ Badges", badges)
            row("👑 Titles", titles)
            row("🧿 Relics", relics)

            ctk.CTkButton(self.main_frame, text="🗂️ Открыть карантин", command=self.show_quarantine_center).pack(pady=8)
        except Exception as e:
            messagebox.showerror("Статистика", f"Ошибка: {e}")

    def clean_temp(self):
        if messagebox.askyesno("Очистка", "Удалить временные файлы (очистка системы)?"):
            
            # Кроссплатформенная поддержка
            if platform.system() == "Windows":
                 tmp_dirs = [p for p in [os.getenv('TEMP'), os.getenv('TMP')] if p]
            elif platform.system() == "Linux" or platform.system() == "Darwin": # macOS
                 tmp_dirs = ['/tmp', '/var/tmp', os.path.expanduser('~') + '/.cache']
            else:
                 messagebox.showerror("Ошибка", "Очистка временных файлов не поддерживается на этой ОС.")
                 return
                 
            cnt = 0
            for tmp in tmp_dirs:
                if not os.path.exists(tmp): continue
                for f in os.listdir(tmp):
                    try:
                        fp = os.path.join(tmp, f)
                        # Дополнительная проверка на защищенные файлы/папки (для Linux/macOS)
                        if os.path.isfile(fp): 
                            os.remove(fp)
                        elif os.path.isdir(fp):
                            shutil.rmtree(fp)
                        cnt += 1
                    except Exception as e: 
                        # Если не удалось удалить, пропускаем (обычно из-за используемых файлов)
                        pass 
                        
            messagebox.showinfo("Успех", f"Удалено {cnt} файлов/папок мусора. Система стала легче 🚀")

if __name__ == "__main__":
    app = App()
    app.mainloop()