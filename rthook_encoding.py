# -*- coding: utf-8 -*-
"""
Runtime hook để đảm bảo hỗ trợ tiếng Việt trong PyInstaller
"""
import sys
import os
import locale

def setup_vietnamese_support():
    """Thiết lập hỗ trợ tiếng Việt toàn diện"""
    
    # 1. Thiết lập environment variables
    os.environ['PYTHONIOENCODING'] = 'utf-8'
    os.environ['PYTHONLEGACYWINDOWSSTDIO'] = '0'  # Tắt legacy mode
    
    # 2. Force UTF-8 cho console trên Windows
    if sys.platform.startswith('win'):
        try:
            # Thiết lập console code page thành UTF-8
            import ctypes
            kernel32 = ctypes.windll.kernel32
            kernel32.SetConsoleCP(65001)  # UTF-8
            kernel32.SetConsoleOutputCP(65001)  # UTF-8
        except Exception:
            pass
    
    # 3. Thiết lập locale với nhiều fallback options
    locale_variants = [
        'Vietnamese_Vietnam.65001',  # UTF-8 trên Windows
        'vi_VN.UTF-8',               # UTF-8 trên Linux/Mac
        'Vietnamese_Vietnam.1258',    # Windows-1258
        'vi_VN',                     # Basic Vietnamese
        'C.UTF-8',                   # Generic UTF-8
        ''                           # System default
    ]
    
    for loc in locale_variants:
        try:
            locale.setlocale(locale.LC_ALL, loc)
            print(f"Locale set to: {loc}")
            break
        except locale.Error:
            continue
    
    # 4. Reconfigure stdout/stderr nếu có thể
    for stream_name in ['stdout', 'stderr', 'stdin']:
        stream = getattr(sys, stream_name, None)
        if stream and hasattr(stream, 'reconfigure'):
            try:
                stream.reconfigure(encoding='utf-8', errors='replace')
            except Exception:
                pass
    
    # 5. Patch sys.getdefaultencoding nếu cần
    if hasattr(sys, '_getframe'):  # Chỉ trong development
        try:
            import codecs
            # Đảm bảo default encoding là UTF-8
            if sys.getdefaultencoding() != 'utf-8':
                # Không thể thay đổi trực tiếp, nhưng có thể ảnh hưởng đến các import
                pass
        except Exception:
            pass
    
    # 6. Thiết lập tkinter encoding (quan trọng cho customtkinter)
    try:
        import tkinter as tk
        # Force UTF-8 cho Tkinter
        if hasattr(tk, 'TkVersion'):
            os.environ['TCL_LIBRARY'] = os.path.join(sys._MEIPASS, 'tcl') if hasattr(sys, '_MEIPASS') else ''
            os.environ['TK_LIBRARY'] = os.path.join(sys._MEIPASS, 'tk') if hasattr(sys, '_MEIPASS') else ''
    except ImportError:
        pass

# Chạy thiết lập
setup_vietnamese_support()