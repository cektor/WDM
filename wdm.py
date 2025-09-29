import sys
import os
import time
import ctypes
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QFileDialog, QLabel, QTextEdit, QMessageBox, QMainWindow,
    QSpacerItem, QSizePolicy, QProgressBar, QStatusBar, QFrame,
    QToolButton, QMenu, QLineEdit, QCheckBox, QComboBox, QTableWidget,
    QTableWidgetItem, QHeaderView, QTabWidget, QPlainTextEdit, QGridLayout,
    QDialog, QScrollArea, QInputDialog,
    QScrollArea
)
from PyQt5.QtGui import QFont, QColor, QPalette, QIcon, QPixmap
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QSize
from PyQt5.QtWidgets import QActionGroup
import subprocess
import re
import datetime
import json
import shutil
import locale


class WorkerThread(QThread):
    progress = pyqtSignal(int)
    output = pyqtSignal(str)
    finished = pyqtSignal(bool, str)

    def __init__(self, cmd, file_count=None):
        super().__init__()
        self.cmd = cmd
        self.file_count = file_count
        self.progress_count = 0

    
            self.progress_count = 0
            total_processed = 0
            start_time = time.time()
            last_progress = 0

            while True:
                output_line = process.stdout.readline()
                if output_line == '' and process.poll() is not None:
                    break
                if output_line:
                    line = output_line.strip()
                    self.output.emit(line)
                    
                    # İlerleme hesaplama
                    if "successfully installed" in line.lower() or "başarıyla yüklendi" in line.lower():
                        self.progress_count += 1
                        if self.file_count:
                            progress = min(int((self.progress_count / self.file_count) * 100), 100)
                            if progress > last_progress:  # Sadece ilerleme arttığında güncelle
                                last_progress = progress
                                self.progress.emit(progress)
                    elif any(x in line.lower() for x in ['copying', 'exported', 'processing']):
                        total_processed += 1
                        if self.file_count:
                            progress = min(int((total_processed / self.file_count) * 100), 100)
                            if progress > last_progress:
                                last_progress = progress
                                self.progress.emit(progress)
                    elif "Driver package" in line:
                        if "Export-WindowsDriver" in command:
                            # Windows 8 ve üzeri için özel hesaplama
                            elapsed_minutes = (time.time() - start_time) / 60
                            if elapsed_minutes < 1:
                                progress = int(elapsed_minutes * 20)  # İlk dakika için yavaş ilerleme
                            else:
                                progress = min(20 + int(elapsed_minutes * 8), 100)  # Sonrası için daha hızlı
                            if progress > last_progress:
                                last_progress = progress
                                self.progress.emit(progress)

            returncode = process.poll()
            success = returncode == 0
            error = process.stderr.read() if not success else ""
            self.finished.emit(success, error)

        except Exception as e:
            self.output.emit(str(e))
            self.finished.emit(False, str(e))

class DriverBackupApp(QMainWindow):
    def __init__(self):
        super().__init__()

       
        # Temel değişkenleri ayarla
        self.restart_button = None  # Yeniden başlatma butonu için değişken
        self.worker = None
        self.last_backup_folder = None
        self.backup_history = self.load_backup_history()
        self.current_drivers = []
        
        # Sürücü listesini yükle
        self.load_current_drivers()
        
        # Windows sürümünü al
        self.windows_version = sys.getwindowsversion()
      
    def tr(self, key):
        """Metni mevcut dile göre çevir"""
        try:
            translated = translations[self.current_lang].get(key, key)
            if translated == key and self.current_lang != 'en':
                # Eğer çeviri bulunamazsa İngilizce versiyonu dene
                translated = translations['en'].get(key, key)
            return translated
        except Exception as e:
            print(f"Translation error for key '{key}': {e}")
            return key

    def get_settings_path(self):
        """Get the correct path for settings file"""
        if getattr(sys, 'frozen', False):
            # PyInstaller ile build edilmiş exe için
            return os.path.join(os.path.dirname(sys.executable), "settings.json")
        else:
            # Normal Python script için
            return os.path.join(os.path.dirname(os.path.abspath(__file__)), "settings.json")

    def load_language_setting(self):
        """Load saved language setting or use system default"""
        try:
            settings_path = self.get_settings_path()
            if os.path.exists(settings_path):
                with open(settings_path, "r", encoding='utf-8') as f:
                    settings = json.load(f)
                    saved_lang = settings.get("language", "")
                    if saved_lang in translations:
                        return saved_lang
        except Exception as e:
            print(f"Error loading language settings: {e}")
            # Alternatif olarak registry'den oku (Windows)
            try:
                import winreg
                key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Software\\WDM")
                saved_lang, _ = winreg.QueryValueEx(key, "Language")
                winreg.CloseKey(key)
                if saved_lang in translations:
                    return saved_lang
            except:
                pass
        
        try:
            # Sistem diline göre varsayılan dili belirle
            system_lang = locale.getdefaultlocale()[0][:2].lower()
            if system_lang in translations:
                return system_lang
        except:
            pass
        
        return "tr"  # Eğer bir hata olursa varsayılan olarak Türkçe'yi kullan

    def save_language_setting(self, lang):
        """Save language setting"""
        try:
            settings = {}
            settings_path = self.get_settings_path()
            if os.path.exists(settings_path):
                with open(settings_path, "r", encoding='utf-8') as f:
                    settings = json.load(f)
            settings["language"] = lang
            with open(settings_path, "w", encoding='utf-8') as f:
                json.dump(settings, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Error saving language setting: {e}")
            # Alternatif olarak registry'ye kaydet (Windows)
            try:
                import winreg
                key = winreg.CreateKey(winreg.HKEY_CURRENT_USER, "Software\\WDM")
                winreg.SetValueEx(key, "Language", 0, winreg.REG_SZ, lang)
                winreg.CloseKey(key)
            except:
                pass

    def init_ui(self):
        self.setWindowTitle(self.tr("app_title"))
        self.resize(400, 400)  # Pencere boyutu
        
        # Pencere ikonunu ayarla
        app_icon = QIcon("wdm.png")
        self.setWindowIcon(app_icon)
        
        # Ekranın ortasına konumlandır
        screen = QApplication.desktop().screenGeometry()
        x = (screen.width() - self.width()) // 2
        y = (screen.height() - self.height()) // 2
        self.move(x, y)
        
        # Ana widget ve layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(8)  # Azaltılmış dikey boşluk
        main_layout.setContentsMargins(10, 10, 10, 10)  # Azaltılmış kenar boşlukları
        
        # Modern Karanlık Tema
        self.setStyleSheet("""
            QMainWindow {
                background-color: #1e1e1e;
            }
            QWidget {
                font-family: 'Segoe UI', 'Microsoft Sans Serif', sans-serif;
            }
        """)
        
        # Başlık çerçevesi
        title_frame = QFrame()
        title_frame.setStyleSheet("""
            QFrame {
                background-color: #252526;
                border: 1px solid #3e3e42;
                border-radius: 3px;
                padding: 8px;
            }
        """)
        title_layout = QHBoxLayout(title_frame)
        
        # Logo label
        logo_label = QLabel()
        logo_label.setFixedSize(48, 48)  # Logo boyutunu küçülttük
        logo_pixmap = QPixmap("wdm.png")
        logo_pixmap = logo_pixmap.scaled(48, 48, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        logo_label.setPixmap(logo_pixmap)
        logo_label.setStyleSheet("""
            background: transparent;
            border: none;
            padding: 5px;
        """)
        title_layout.addWidget(logo_label)
        
        # Başlık
        title_label = QLabel(self.tr('app_title'))
        title_label.setStyleSheet("""
            QLabel {
                color: #ffffff;
                font-size: 16px;
                font-weight: 600;
                font-family: 'Segoe UI', 'Microsoft Sans Serif';
            }
        """)
        title_layout.addWidget(title_label)
        title_layout.addStretch()
        
        # Menü butonu
        menu_button = QToolButton()
        menu_button.setPopupMode(QToolButton.InstantPopup)
        menu_button.setStyleSheet("""
            QToolButton {
                background-color: #2d2d2d;
                border: 1px solid #3e3e42;
                border-radius: 4px;
                padding: 5px;
                color: white;
            }
            QToolButton:hover {
                background-color: #3e3e3e;
                border-color: #007acc;
            }
        """)
        
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background-color: #1e1e1e;
                color: #d4d4d4;
                border: 1px solid #3e3e42;
                border-radius: 4px;
                padding: 4px 0px;
            }
            QMenu::item {
                padding: 6px 16px;
                font-size: 12px;
            }
            QMenu::item:selected {
                background-color: #094771;
                color: #ffffff;
            }
            QMenu::item:disabled {
                color: #6e6e6e;
            }
            QMenu::separator {
                height: 1px;
                background: #3e3e42;
                margin: 4px 0px;
            }
        """)
     
        for lang_code, lang_name in {
            'tr': self.tr('menu_turkish'),
            'en': self.tr('menu_english')
        }.items():
            action = language_menu.addAction(lang_name)
            action.setCheckable(True)
            action.setChecked(self.current_lang == lang_code)
            action.setData(lang_code)
            action.triggered.connect(lambda checked, code=lang_code: self.change_language(code))
            self.language_group.addAction(action)
            self.language_actions[lang_code] = action
        
        # Geçmiş ve yardım menüsü
        menu.addAction(self.tr("backup_history"), self.show_backup_history)
        menu.addSeparator()
        menu.addAction(self.tr("help"), self.show_help)
        menu.addAction(self.tr("about"), self.show_about)
        menu_button.setMenu(menu)
        
        title_layout.addWidget(menu_button)
        main_layout.addWidget(title_frame)

      
        font = QFont("Segoe UI", 10)
        font.setStyleStrategy(QFont.PreferAntialias)
        self.setFont(font)

        # Bilgi etiketi
        info_frame = QFrame()
        info_frame.setStyleSheet("""
            QFrame {
                background-color: #252526;
                border: 1px solid #3e3e42;
                border-radius: 4px;
                padding: 16px;
            }
        """)
        info_layout = QVBoxLayout(info_frame)
        
        self.info_label = QLabel(self.tr('info_label'))
        self.info_label.setStyleSheet("""
            QLabel {
                font-weight: normal;
                color: #d4d4d4;
                font-size: 14px;
                font-family: 'Segoe UI';
            }
        """)
        info_layout.addWidget(self.info_label)
        main_layout.addWidget(info_frame)

        # Çıktı ve ilerleme çubuğu için frame
        output_frame = QFrame()
        output_frame.setStyleSheet("""
            QFrame {
                background-color: #252526;
                border: 1px solid #3e3e42;
                border-radius: 4px;
                padding: 16px;
            }
        """)
        output_layout = QVBoxLayout(output_frame)
        output_layout.setSpacing(6)  # Çıktı alanı içindeki boşlukları azalt
        
        self.output_text = QTextEdit()
        self.output_text.setReadOnly(True)
        self.output_text.setStyleSheet("""
            QTextEdit {
                background-color: #1e1e1e;
                border: 1px solid #3e3e42;
                border-radius: 4px;
                padding: 12px;
                font-family: 'Cascadia Code', 'Consolas', 'Courier New', monospace;
                font-size: 13px;
                line-height: 1.5;
                selection-background-color: #264f78;
                color: #d4d4d4;
            }
        """)
        self.output_text.setTextInteractionFlags(Qt.TextSelectableByMouse | Qt.TextSelectableByKeyboard)
        self.output_text.setAcceptRichText(True)
        self.output_text.setMinimumHeight(150)  # Daha kompakt çıktı alanı
        output_layout.addWidget(self.output_text)

        # İlerleme çubuğu
        self.progress_bar = QProgressBar()
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 1px solid #3e3e42;
                border-radius: 2px;
                text-align: center;
                background-color: #252526;
                height: 16px;
                color: #ffffff;
                font-size: 11px;
                font-family: 'Segoe UI';
            }
            QProgressBar::chunk {
                background-color: #0078D4;
                border-radius: 2px;
            }
        """)
        self.progress_bar.hide()
        output_layout.addWidget(self.progress_bar)
        
        main_layout.addWidget(output_frame)

        # Buton container frame
        button_frame = QFrame()
        button_frame.setStyleSheet("""
            QFrame {
                background-color: #252526;
                border: 1px solid #3e3e42;
                border-radius: 4px;
                padding: 15px;
            }
        """)
        button_layout = QHBoxLayout(button_frame)
        button_layout.setSpacing(10)  # Butonlar arası boşluğu azalt

        button_style = """
            QPushButton {
                background-color: #0078D4;
                border: none;
                border-radius: 3px;
                color: white;
                padding: 6px 12px;
                font-weight: 500;
                min-width: 140px;
                font-size: 12px;
                font-family: 'Segoe UI';
            }
            QPushButton:hover {
                background-color: #2b8dee;
            }
            QPushButton:pressed {
                background-color: #005a9e;
            }
            QPushButton:disabled {
                background-color: #3e3e42;
                color: #6e6e6e;
                border: 1px solid #555555;
            }
        """

        backup_button_style = """
            QPushButton {
                background-color: #2ea043;  /* Yeşil renk */
                border: none;
                border-radius: 3px;
                color: white;
                padding: 6px 12px;
                font-weight: 500;
                min-width: 140px;
                font-size: 12px;
                font-family: 'Segoe UI';
            }
            QPushButton:hover {
                background-color: #3fb950;  /* Hover durumunda daha açık yeşil */
            }
            QPushButton:pressed {
                background-color: #238636;  /* Tıklama durumunda koyu yeşil */
            }
            QPushButton:disabled {
                background-color: #3e3e42;
                color: #6e6e6e;
                border: 1px solid #555555;
            }
        """
        
        self.backup_button = QPushButton(self.tr("backup_button"))
        self.backup_button.setStyleSheet(backup_button_style)
        self.backup_button.clicked.connect(self.backup_drivers)
        button_layout.addWidget(self.backup_button)

        button_layout.addSpacing(20)  # Butonlar arası boşluk

        self.restore_button = QPushButton(self.tr("restore_button"))
        self.restore_button.setStyleSheet(button_style)
        self.restore_button.clicked.connect(self.restore_drivers)
        button_layout.addWidget(self.restore_button)

        main_layout.addWidget(button_frame)

        # Durum çubuğu
        self.statusBar = QStatusBar()
        self.statusBar.setStyleSheet("""
            QStatusBar {
                background-color: #007acc;
                color: #ffffff;
                border-top: 1px solid #3e3e42;
                padding: 2px 6px;
                font-family: 'Segoe UI';
                font-size: 11px;
            }
        """)
        self.setStatusBar(self.statusBar)
        self.statusBar.showMessage(self.tr("ready"))

    def get_windows_username(self):
        """Windows kullanıcı adını döndür"""
        return os.getenv('USERNAME')

    def get_backup_history_path(self):
        """Get the correct path for backup history file"""
        if getattr(sys, 'frozen', False):
            # PyInstaller ile build edilmiş exe için
            return os.path.join(os.path.dirname(sys.executable), "backup_history.json")
        else:
            # Normal Python script için
            return "backup_history.json"

    def load_backup_history(self):
        try:
            history_path = self.get_backup_history_path()
            if os.path.exists(history_path):
                with open(history_path, "r", encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            print(f"Error loading backup history: {e}")
        return []

   
    def show_backup_history(self):
        """Yedekleme geçmişini göster"""
        if not self.backup_history:
            QMessageBox.information(self, self.tr("backup_history_title"), self.tr("no_backup_yet"))
            return

        dialog = QMainWindow(self)
        dialog.setWindowTitle(self.tr("backup_history_title"))
        dialog.resize(800, 600)
        dialog.setWindowIcon(QIcon("wdm.png"))
        
        # Ekranın ortasına konumlandır
        screen = QApplication.desktop().screenGeometry()
        x = (screen.width() - dialog.width()) // 2
        y = (screen.height() - dialog.height()) // 2
        dialog.move(x, y)

        central = QWidget()
        central.setStyleSheet("""
            QWidget {
                background-color: #1e1e1e;
                color: #d4d4d4;
                font-family: 'Segoe UI';
            }
        """)
        
        layout = QVBoxLayout(central)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        # Üst bilgi paneli
        info_frame = QFrame()
        info_frame.setStyleSheet("""
            QFrame {
                background-color: #252526;
                border: 1px solid #3e3e42;
                border-radius: 4px;
                padding: 15px;
            }
        """)
        info_layout = QVBoxLayout(info_frame)

        # Başlık ve istatistikler
        title = QLabel(self.tr("backup_history_stats"))
        title.setStyleSheet("""
            QLabel {
                color: #0078D4;
                font-size: 16px;
                font-weight: bold;
                margin-bottom: 10px;
            }
        """)
        info_layout.addWidget(title)

        # İstatistik bilgileri
        stats_layout = QHBoxLayout()
        
        total_backups = len(self.backup_history)
        total_size = sum(self.get_folder_size(backup['location']) for backup in self.backup_history)
        latest_backup = self.backup_history[-1]['date'] if self.backup_history else "Yok"
        
        stats_frame = QFrame()
        stats_frame.setStyleSheet("""
            QFrame {
                background-color: #2d2d2d;
                border: 1px solid #3e3e42;
                border-radius: 4px;
                padding: 10px;
            }
        """)
        stats_grid = QGridLayout(stats_frame)

        # İstatistik etiketleri
        stats = [
            (self.tr("total_backups"), f"{total_backups}"),
            (self.tr("total_size"), self.format_size(total_size)),
            (self.tr("last_backup"), latest_backup),
            (self.tr("average_size"), self.format_size(total_size / total_backups) if total_backups > 0 else "0 B")
        ]

        for i, (label, value) in enumerate(stats):
            label_widget = QLabel(label)
            label_widget.setStyleSheet("color: #0078D4; font-weight: bold;")
            value_widget = QLabel(value)
            value_widget.setStyleSheet("color: #ffffff;")
            stats_grid.addWidget(label_widget, i // 2, (i % 2) * 2)
            stats_grid.addWidget(value_widget, i // 2, (i % 2) * 2 + 1)

        stats_layout.addWidget(stats_frame)
        info_layout.addLayout(stats_layout)
        layout.addWidget(info_frame)

        # Yedekleme tablosu
        table = QTableWidget()
        table.setColumnCount(5)
        table.setHorizontalHeaderLabels([self.tr("date"), self.tr("location"), self.tr("size"), self.tr("status"), self.tr("actions")])
        table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        table.setAlternatingRowColors(True)
        table.setStyleSheet("""
            QTableWidget {
                background-color: #2d2d2d;
                gridline-color: #3e3e42;
                color: #ffffff;
                border: none;
            }
            QTableWidget::item {
                padding: 5px;
                color: #ffffff;
                background-color: #2d2d2d;
            }
            QTableWidget::item:alternate {
                background-color: #252526;
            }
            QTableWidget::item:selected {
                background-color: #094771;
                color: #ffffff;
            }
            QHeaderView::section {
                background-color: #1e1e1e;
                color: #0078D4;
                padding: 8px;
                border: none;
                border-right: 1px solid #3e3e42;
                border-bottom: 1px solid #3e3e42;
                font-weight: bold;
            }
            QTableWidget QTableCornerButton::section {
                background-color: #1e1e1e;
                border: none;
            }
        """)

     
            # Geri yükle butonu
            restore_btn = QPushButton(self.tr("restore"))
            restore_btn.setFixedHeight(30)
            restore_btn.setStyleSheet("""
                QPushButton {
                    background-color: #0078D4;
                    border: none;
                    border-radius: 3px;
                    color: white;
                    padding: 4px 8px;
                    min-width: 80px;
                }
                QPushButton:hover {
                    background-color: #2b8dee;
                }
                QPushButton:disabled {
                    background-color: #3e3e42;
                    color: #6e6e6e;
                }
            """)
            restore_btn.setEnabled(os.path.exists(backup['location']))
            restore_btn.clicked.connect(lambda checked, path=backup['location']: self.restore_drivers_from_history(path))
       

        # Alt bilgi paneli
        footer_frame = QFrame()
        footer_frame.setStyleSheet("""
            QFrame {
                background-color: #252526;
                border: 1px solid #3e3e42;
                border-radius: 4px;
                padding: 10px;
            }
        """)
        footer_layout = QHBoxLayout(footer_frame)
        
        # Temizleme butonları
        clear_old_btn = QPushButton(self.tr("clear_old_backups"))
        clear_old_btn.setStyleSheet("""
            QPushButton {
                background-color: #0078D4;
                border: none;
                border-radius: 3px;
                color: white;
                padding: 6px 12px;
            }
            QPushButton:hover {
                background-color: #2b8dee;
            }
        """)
        clear_old_btn.clicked.connect(lambda: self.clear_old_backups())
        
        clear_invalid_btn = QPushButton(self.tr("clear_invalid_backups"))
        clear_invalid_btn.setStyleSheet("""
            QPushButton {
                background-color: #c42b1c;
                border: none;
                border-radius: 3px;
                color: white;
                padding: 6px 12px;
            }
            QPushButton:hover {
                background-color: #d63c2e;
            }
        """)
        clear_invalid_btn.clicked.connect(lambda: self.clear_invalid_backups())

        footer_layout.addWidget(clear_old_btn)
        footer_layout.addWidget(clear_invalid_btn)
        layout.addWidget(footer_frame)

        dialog.setCentralWidget(central)
        dialog.show()

    def restore_drivers_from_history(self, folder_path):
        """Geçmişteki bir yedeklemeden sürücüleri geri yükle"""
        if os.path.exists(folder_path):
            self.restore_drivers(folder_path)
        else:
            QMessageBox.warning(self, self.tr("error"), self.tr("folder_not_found"))

    def clear_old_backups(self):
        """30 günden eski yedeklemeleri temizle"""
        if not self.backup_history:
            return

        current_time = datetime.datetime.now()
        new_history = []
        removed = 0

        for backup in self.backup_history:
            backup_time = datetime.datetime.strptime(backup['date'], "%Y-%m-%d %H:%M:%S")
            if (current_time - backup_time).days <= 30:
                new_history.append(backup)
            else:
                if os.path.exists(backup['location']):
                    try:
                        shutil.rmtree(backup['location'])
                    except:
                        pass
                removed += 1

        self.backup_history = new_history
        self.save_backup_history()
        QMessageBox.information(self, self.tr("cleanup_completed_title"), 
            self.tr("old_backups_cleared_msg").format(removed))

    def clear_invalid_backups(self):
        """Geçersiz (silinmiş) yedeklemeleri temizle"""
        if not self.backup_history:
            return

        new_history = []
        removed = 0

        for backup in self.backup_history:
            if os.path.exists(backup['location']):
                new_history.append(backup)
            else:
                removed += 1

        self.backup_history = new_history
        self.save_backup_history()
        QMessageBox.information(self, self.tr("cleanup_completed_title"), 
            self.tr("invalid_backups_cleared_msg").format(removed))

    def load_current_drivers(self):
        """Mevcut sürücüleri yükle"""
        try:
            cmd = ["pnputil", "/enum-drivers"]
            result = subprocess.run(cmd, capture_output=True, text=True, encoding='cp857')
            if result.returncode == 0:
                self.current_drivers = self.parse_driver_list(result.stdout)
            else:
                self.current_drivers = []
        except Exception as e:
            self.current_drivers = []
            print(f"Driver list loading error: {str(e)}")

    def parse_driver_list(self, output):
        """Sürücü listesini ayrıştır"""
        drivers = []
        current_driver = {}
        
        for line in output.split('\n'):
            line = line.strip()
            if not line:
                continue
                
            # Türkçe ve İngilizce anahtar kelimeler
            if 'Published Name:' in line or 'Yayınlanan İsim:' in line:
                if current_driver:
                    # Eksik alanları doldur
                    if 'original_name' not in current_driver:
                        current_driver['original_name'] = current_driver.get('published_name', self.tr('unknown_driver'))
                    if 'provider' not in current_driver:
                        current_driver['provider'] = self.tr('unknown_provider')
                    if 'class' not in current_driver:
                        current_driver['class'] = self.tr('unknown_class')
                    if 'date_version' not in current_driver:
                        current_driver['date_version'] = 'N/A'
                    drivers.append(current_driver.copy())
                    
                current_driver = {'published_name': line.split(':', 1)[1].strip()}
                
            elif 'Original Name:' in line or 'Özgün İsim:' in line:
                current_driver['original_name'] = line.split(':', 1)[1].strip()
            elif 'Provider Name:' in line or 'Sağlayıcı İsmi:' in line:
                current_driver['provider'] = line.split(':', 1)[1].strip()
            elif 'Class Name:' in line or 'Sınıf İsmi:' in line:
                current_driver['class'] = line.split(':', 1)[1].strip()
            elif 'Date and Version:' in line or 'Tarih ve Sürüm:' in line:
                current_driver['date_version'] = line.split(':', 1)[1].strip()
                
        # Son sürücüyü ekle
        if current_driver:
            if 'original_name' not in current_driver:
                current_driver['original_name'] = current_driver.get('published_name', self.tr('unknown_driver'))
            if 'provider' not in current_driver:
                current_driver['provider'] = self.tr('unknown_provider')
            if 'class' not in current_driver:
                current_driver['class'] = self.tr('unknown_class')
            if 'date_version' not in current_driver:
                current_driver['date_version'] = 'N/A'
            drivers.append(current_driver.copy())
            
        return drivers

    def analyze_drivers(self):
        """Sürücü analizi yap"""
        # Sürücü listesini yenile
        self.load_current_drivers()
        
        if not self.current_drivers:
            QMessageBox.warning(self, self.tr("warning"), self.tr("no_drivers_found"))
            return
            
        # Analiz penceresi oluştur
        dialog = QMainWindow(self)
        dialog.setWindowTitle(self.tr("analysis_window_title"))
        dialog.resize(900, 600)
        dialog.setWindowIcon(QIcon("wdm.png"))
        
        # Ekranın ortasına konumlandır
        screen = QApplication.desktop().screenGeometry()
        x = (screen.width() - dialog.width()) // 2
        y = (screen.height() - dialog.height()) // 2
        dialog.move(x, y)
        
        # Merkezi widget ve düzen
        central = QWidget()
        layout = QVBoxLayout(central)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)
        
        # Modern Karanlık Tema
        central.setStyleSheet("""
            QWidget {
                background-color: #1e1e1e;
                color: #d4d4d4;
                font-family: 'Segoe UI';
            }
        """)
        
        # Üst bilgi paneli
        info_frame = QFrame()
        info_frame.setStyleSheet("""
            QFrame {
                background-color: #252526;
                border: 1px solid #3e3e42;
                border-radius: 4px;
                padding: 10px;
            }
        """)
        info_layout = QHBoxLayout(info_frame)
        
        # Sol taraftaki istatistikler
        stats_layout = QVBoxLayout()
        total_drivers = len(self.current_drivers)
        stats_label = QLabel(self.tr("analysis_total_drivers").format(total_drivers))
        stats_label.setStyleSheet("font-size: 14px; font-weight: bold; color: #0078D4;")
        stats_layout.addWidget(stats_label)
        
        # Sürücü sınıflarını say
        class_counts = {}
        for driver in self.current_drivers:
            class_name = driver.get('class', self.tr('unknown_class'))
            class_counts[class_name] = class_counts.get(class_name, 0) + 1
        
        class_stats = QLabel(self.tr("analysis_different_classes").format(len(class_counts)))
        class_stats.setStyleSheet("color: #0078D4;")
        stats_layout.addWidget(class_stats)
        
        info_layout.addLayout(stats_layout)
        info_layout.addStretch()
        
        # Arama ve filtreleme
        search_layout = QHBoxLayout()
        search_box = QLineEdit()
        search_box.setPlaceholderText(self.tr("analysis_search_placeholder"))
        search_box.setStyleSheet("""
            QLineEdit {
                background-color: #2d2d2d;
                border: 1px solid #3e3e42;
                border-radius: 4px;
                padding: 6px;
                color: #d4d4d4;
            }
            QLineEdit:focus {
                border-color: #0078D4;
            }
        """)
        search_layout.addWidget(search_box)
        
        filter_combo = QComboBox()
        filter_combo.addItem(self.tr("analysis_all_classes"))
        filter_combo.addItems(sorted(class_counts.keys()))
        filter_combo.setStyleSheet("""
            QComboBox {
                background-color: #2d2d2d;
                border: 1px solid #3e3e42;
                border-radius: 4px;
                padding: 5px;
                color: #d4d4d4;
                min-width: 150px;
            }
            QComboBox::drop-down {
                border: none;
            }
            QComboBox::down-arrow {
                image: none;
                border-left: 5px solid #2d2d2d;
                border-right: 5px solid #2d2d2d;
                border-top: 5px solid #d4d4d4;
                margin-right: 5px;
            }
        """)
        search_layout.addWidget(filter_combo)
        
        info_layout.addLayout(search_layout)
        layout.addWidget(info_frame)
        
        # Tab widget for different views
        tab_widget = QTabWidget()
        tab_widget.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #3e3e42;
                background-color: #252526;
                border-radius: 4px;
            }
            QTabBar::tab {
                background-color: #2d2d2d;
                color: #d4d4d4;
                padding: 8px 16px;
                border: 1px solid #3e3e42;
                border-bottom: none;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
            }
            QTabBar::tab:selected {
                background-color: #252526;
                border-bottom: 2px solid #0078D4;
            }
            QTabBar::tab:hover {
                background-color: #3e3e42;
            }
        """)
        
        # Tablo görünümü
        table_widget = QWidget()
        table_layout = QVBoxLayout(table_widget)
        
        table = QTableWidget()
        table.setColumnCount(5)
        table.setHorizontalHeaderLabels([self.tr("published_name"), self.tr("original_name"), self.tr("provider"), self.tr("class"), self.tr("date_version")])
        table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        table.setAlternatingRowColors(True)
        table.setStyleSheet("""
            QTableWidget {
                background-color: #2d2d2d;
                gridline-color: #3e3e42;
                color: #ffffff;
                border: none;
            }
            QTableWidget::item {
                padding: 5px;
                color: #ffffff;
                background-color: #2d2d2d;
            }
            QTableWidget::item:alternate {
                background-color: #252526;
            }
            QTableWidget::item:selected {
                background-color: #094771;
                color: #ffffff;
            }
            QHeaderView::section {
                background-color: #1e1e1e;
                color: #0078D4;
                padding: 5px;
                border: none;
                border-right: 1px solid #3e3e42;
                border-bottom: 1px solid #3e3e42;
                font-weight: bold;
            }
            QTableWidget QTableCornerButton::section {
                background-color: #1e1e1e;
                border: none;
            }
            QHeaderView {
                background-color: #1e1e1e;
            }
            QHeaderView::section:hover {
                background-color: #3e3e42;
            }
        """)
        
        # Sürücüleri tabloya ekle
        table.setRowCount(len(self.current_drivers))
        for i, driver in enumerate(self.current_drivers):
            table.setItem(i, 0, QTableWidgetItem(driver.get('published_name', '')))
            table.setItem(i, 1, QTableWidgetItem(driver.get('original_name', '')))
            table.setItem(i, 2, QTableWidgetItem(driver.get('provider', '')))
            table.setItem(i, 3, QTableWidgetItem(driver.get('class', '')))
            table.setItem(i, 4, QTableWidgetItem(driver.get('date_version', '')))
        
        table_layout.addWidget(table)
        tab_widget.addTab(table_widget, self.tr("analysis_table_view"))
        
        # İstatistik görünümü
        stats_widget = QWidget()
        stats_layout = QVBoxLayout(stats_widget)
        
        # Sınıflara göre dağılım
        class_frame = QFrame()
        class_frame.setStyleSheet("""
            QFrame {
                background-color: #252526;
                border: 1px solid #3e3e42;
                border-radius: 4px;
                padding: 10px;
            }
        """)
        class_layout = QVBoxLayout(class_frame)
        class_title = QLabel(self.tr("analysis_class_distribution"))
        class_title.setStyleSheet("font-size: 14px; font-weight: bold; color: #0078D4; margin-bottom: 10px;")
        class_layout.addWidget(class_title)
        
        for class_name, count in sorted(class_counts.items(), key=lambda x: x[1], reverse=True):
            percentage = (count / total_drivers) * 100
            class_bar = QProgressBar()
            class_bar.setMaximum(100)
            class_bar.setValue(int(percentage))
            class_bar.setFormat(f"{class_name}: {count} (%{percentage:.1f})")
            class_bar.setStyleSheet("""
                QProgressBar {
                    border: 1px solid #3e3e42;
                    border-radius: 2px;
                    text-align: left;
                    padding: 1px;
                    background-color: #1e1e1e;
                    color: #d4d4d4;
                    height: 20px;
                }
                QProgressBar::chunk {
                    background-color: #094771;
                    border-radius: 2px;
                }
            """)
            class_layout.addWidget(class_bar)
        
        stats_layout.addWidget(class_frame)
        tab_widget.addTab(stats_widget, self.tr("analysis_statistics"))
        
        layout.addWidget(tab_widget)
        
        # Arama fonksiyonu
        def filter_table():
            search_text = search_box.text().lower()
            selected_class = filter_combo.currentText()
            
            for row in range(table.rowCount()):
                show_row = True
                if search_text:
                    show_row = False
                    for col in range(table.columnCount()):
                        item = table.item(row, col)
                        if item and search_text in item.text().lower():
                            show_row = True
                            break
                
                if show_row and selected_class != self.tr("analysis_all_classes"):
                    class_item = table.item(row, 3)
                    if class_item and class_item.text() != selected_class:
                        show_row = False
                
                table.setRowHidden(row, not show_row)
        
        search_box.textChanged.connect(filter_table)
        filter_combo.currentTextChanged.connect(filter_table)
        
        dialog.setCentralWidget(central)
        dialog.show()

    
        folder1_button.clicked.connect(lambda: self.select_folder(self.folder1_path))
        folder1_layout.addWidget(folder1_label)
        folder1_layout.addWidget(self.folder1_path)
        folder1_layout.addWidget(folder1_button)
        
        # İkinci klasör seçimi
        folder2_layout = QHBoxLayout()
        folder2_label = QLabel(self.tr("comparison_second_folder"))
        folder2_label.setStyleSheet("color: #d4d4d4;")
        self.folder2_path = QLineEdit()
        self.folder2_path.setStyleSheet("""
            QLineEdit {
                background-color: #1e1e1e;
                border: 1px solid #3e3e42;
                border-radius: 4px;
                padding: 6px;
                color: #d4d4d4;
            }
            QLineEdit:focus {
                border-color: #0078D4;
            }
        """)
        folder2_button = QPushButton(self.tr("comparison_browse"))
        folder2_button.setStyleSheet("""
            QPushButton {
                background-color: #0078D4;
                border: none;
                border-radius: 4px;
                color: white;
                padding: 6px 12px;
            }
            QPushButton:hover {
                background-color: #2b8dee;
            }
        """)
        folder2_button.clicked.connect(lambda: self.select_folder(self.folder2_path))
        folder2_layout.addWidget(folder2_label)
        folder2_layout.addWidget(self.folder2_path)
        folder2_layout.addWidget(folder2_button)
        
        selection_layout.addLayout(folder1_layout)
        selection_layout.addLayout(folder2_layout)
        
        # Karşılaştır butonu
        compare_button = QPushButton(self.tr("comparison_compare"))
        compare_button.setStyleSheet("""
            QPushButton {
                background-color: #2ea043;
                border: none;
                border-radius: 4px;
                color: white;
                padding: 8px 16px;
                font-weight: bold;
                margin-top: 10px;
            }
            QPushButton:hover {
                background-color: #3fb950;
            }
        """)
        compare_button.clicked.connect(lambda: self.perform_comparison(dialog))
        selection_layout.addWidget(compare_button, alignment=Qt.AlignCenter)
        
        info_layout.addWidget(selection_frame)
        layout.addWidget(info_frame)
        
        # Tab widget
        self.tab_widget = QTabWidget()
        self.tab_widget.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #3e3e42;
                background-color: #252526;
            }
            QTabBar::tab {
                background-color: #2d2d2d;
                color: #d4d4d4;
                padding: 8px 16px;
                border: none;
                border-right: 1px solid #3e3e42;
            }
            QTabBar::tab:selected {
                background-color: #1e1e1e;
                border-bottom: 2px solid #0078D4;
            }
            QTabBar::tab:hover {
                background-color: #3e3e42;
            }
        """)
        layout.addWidget(self.tab_widget)
        
        dialog.setCentralWidget(central)
        dialog.show()

  
        # Sadece ilk klasörde olanlar
        only_in_first = files1 - files2
        for file in only_in_first:
            results['only_in_first'].append({
                'name': file,
                'info': self.get_driver_info(os.path.join(folder1, file))
            })
            
        # Sadece ikinci klasörde olanlar
        only_in_second = files2 - files1
        for file in only_in_second:
            results['only_in_second'].append({
                'name': file,
                'info': self.get_driver_info(os.path.join(folder2, file))
            })
            
        return results

    def select_folder(self, line_edit):
        """Klasör seçme diyalogu"""
        folder = QFileDialog.getExistingDirectory(self, self.tr("select_folder_dialog"))
        if folder:
            line_edit.setText(folder)

    def perform_comparison(self, dialog):
        """Karşılaştırma işlemini gerçekleştir"""
        folder1 = self.folder1_path.text()
        folder2 = self.folder2_path.text()

        if not folder1 or not folder2:
            QMessageBox.warning(dialog, self.tr("error"), self.tr("comparison_select_both"))
            return

        if not os.path.exists(folder1) or not os.path.exists(folder2):
            QMessageBox.warning(dialog, self.tr("error"), self.tr("comparison_folders_not_exist"))
            return

        # Mevcut tabları temizle
        while self.tab_widget.count() > 0:
            self.tab_widget.removeTab(0)

        # Karşılaştırma yap
        results = self.compare_driver_folders(folder1, folder2)
        self.show_detailed_results(results, folder1, folder2)

    def get_driver_info(self, file_path):
        """Sürücü dosyasından versiyon bilgisini çıkar"""
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
                # Version bilgisini bul
                version_match = re.search(r'DriverVer\s*=\s*([^,]+),(.+)', content)
                if version_match:
                    return {
                        'date': version_match.group(1).strip(),
                        'version': version_match.group(2).strip()
                    }
                return {'date': 'Bilinmiyor', 'version': 'Bilinmiyor'}
        except:
            return {'date': 'Bilinmiyor', 'version': 'Bilinmiyor'}

    def show_detailed_results(self, results, folder1, folder2):
        """Karşılaştırma sonuçlarını detaylı olarak göster"""
        # Genel Bakış Tab'ı
        overview_widget = QWidget()
        overview_layout = QVBoxLayout(overview_widget)
        
        stats_frame = QFrame()
        stats_frame.setStyleSheet("""
            QFrame {
                background-color: #2d2d2d;
                border: 1px solid #3e3e42;
                border-radius: 4px;
                padding: 15px;
            }
        """)
        stats_layout = QVBoxLayout(stats_frame)
        
        total_drivers = len(results['identical']) + len(results['different_versions']) + \
                       len(results['only_in_first']) + len(results['only_in_second'])
        
        stats = [
            f"{self.tr('analysis_total_drivers').replace(': {}', '')}: {total_drivers}",
            f"{self.tr('comparison_identical')}: {len(results['identical'])}",
            f"{self.tr('comparison_different_versions')}: {len(results['different_versions'])}",
            f"{self.tr('comparison_only_first')}: {len(results['only_in_first'])}",
            f"{self.tr('comparison_only_second')}: {len(results['only_in_second'])}"
        ]
        
        for stat in stats:
            label = QLabel(stat)
            label.setStyleSheet("""
                QLabel {
                    color: #d4d4d4;
                    font-size: 14px;
                    padding: 5px;
                }
            """)
            stats_layout.addWidget(label)
        
        overview_layout.addWidget(stats_frame)
        self.tab_widget.addTab(overview_widget, self.tr("comparison_overview"))

        # Her kategori için ayrı tab oluştur
        categories = [
            ('identical', self.tr("comparison_identical"), True),
            ('different_versions', self.tr("comparison_different_versions"), True),
            ('only_in_first', self.tr("comparison_only_first"), False),
            ('only_in_second', self.tr("comparison_only_second"), False)
        ]

        for category, title, compare in categories:
            if results[category]:
                tab = QWidget()
                layout = QVBoxLayout(tab)
                
                table = QTableWidget()
                table.setStyleSheet("""
                    QTableWidget {
                        background-color: #2d2d2d;
                        gridline-color: #3e3e42;
                        color: #ffffff;
                        border: none;
                    }
                    QTableWidget::item {
                        padding: 5px;
                    }
                    QTableWidget::item:selected {
                        background-color: #094771;
                    }
                    QHeaderView::section {
                        background-color: #1e1e1e;
                        color: #0078D4;
                        padding: 5px;
                        border: none;
                        border-right: 1px solid #3e3e42;
                        border-bottom: 1px solid #3e3e42;
                    }
                """)

                if compare:
                    table.setColumnCount(5)
                    table.setHorizontalHeaderLabels([
                        self.tr("comparison_driver_name"),
                        self.tr("comparison_version1_date"),
                        self.tr("comparison_version1"),
                        self.tr("comparison_version2_date"),
                        self.tr("comparison_version2")
                    ])
                else:
                    table.setColumnCount(3)
                    table.setHorizontalHeaderLabels([
                        self.tr("comparison_driver_name"),
                        self.tr("date"),
                        self.tr("date_version")
                    ])

                table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
                table.setRowCount(len(results[category]))

                for i, item in enumerate(results[category]):
                    table.setItem(i, 0, QTableWidgetItem(item['name']))
                    
                    if compare:
                        if category == 'identical':
                            info = item['info']
                            table.setItem(i, 1, QTableWidgetItem(info['date']))
                            table.setItem(i, 2, QTableWidgetItem(info['version']))
                            table.setItem(i, 3, QTableWidgetItem(info['date']))
                            table.setItem(i, 4, QTableWidgetItem(info['version']))
                        else:
                            table.setItem(i, 1, QTableWidgetItem(item['version1']['date']))
                            table.setItem(i, 2, QTableWidgetItem(item['version1']['version']))
                            table.setItem(i, 3, QTableWidgetItem(item['version2']['date']))
                            table.setItem(i, 4, QTableWidgetItem(item['version2']['version']))
                            # Versiyonlar farklıysa satırı renklendir
                            if item['version1']['version'] != item['version2']['version']:
                                for col in range(table.columnCount()):
                                    cell = table.item(i, col)
                                    if cell:
                                        cell.setBackground(QColor("#2d0000"))
                    else:
                        info = item['info']
                        table.setItem(i, 1, QTableWidgetItem(info['date']))
                        table.setItem(i, 2, QTableWidgetItem(info['version']))

                layout.addWidget(table)
                self.tab_widget.addTab(tab, title)

    def search_drivers(self):
        """Sürücü arama penceresi"""
        # Sürücü listesini yenile
        self.load_current_drivers()
        
        if not self.current_drivers:
            QMessageBox.warning(self, self.tr("warning"), self.tr("no_drivers_found"))
            return
            
        dialog = QMainWindow(self)
        dialog.setWindowTitle(self.tr("search_window_title"))
        dialog.setGeometry(100, 100, 800, 600)
        dialog.setWindowIcon(QIcon("wdm.png"))
        
        central = QWidget()
        central.setStyleSheet("""
            QWidget {
                background-color: #1e1e1e;
                color: #d4d4d4;
                font-family: 'Segoe UI';
            }
        """)
        
        layout = QVBoxLayout(central)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)
        
        # Üst bilgi paneli
        search_frame = QFrame()
        search_frame.setStyleSheet("""
            QFrame {
                background-color: #252526;
                border: 1px solid #3e3e42;
                border-radius: 4px;
                padding: 15px;
            }
        """)
        search_layout = QVBoxLayout(search_frame)
        
        # Arama başlığı
        search_title = QLabel(self.tr("search_advanced_title"))
        search_title.setStyleSheet("""
            QLabel {
                color: #0078D4;
                font-size: 16px;
                font-weight: bold;
                margin-bottom: 10px;
            }
        """)
        search_layout.addWidget(search_title)
        
        # Arama seçenekleri
        search_options = QHBoxLayout()
        
        # Arama kutusu
        search_box = QLineEdit()
        search_box.setPlaceholderText(self.tr("search_placeholder"))
        search_box.setStyleSheet("""
            QLineEdit {
                background-color: #2d2d2d;
                border: 1px solid #3e3e42;
                border-radius: 4px;
                padding: 8px;
                color: #ffffff;
                font-size: 13px;
            }
            QLineEdit:focus {
                border-color: #0078D4;
            }
        """)
        search_options.addWidget(search_box)
        
        # Filtre combo box'ları
        filter_layout = QHBoxLayout()
        
        # Sınıf filtresi
        class_filter = QComboBox()
        class_filter.addItem(self.tr("search_all_classes"))
        class_counts = {}
        for driver in self.current_drivers:
            class_name = driver.get('class', self.tr('unknown_class'))
            if class_name not in class_counts:
                class_counts[class_name] = 1
                class_filter.addItem(class_name)
        
        # Sağlayıcı filtresi
        provider_filter = QComboBox()
        provider_filter.addItem(self.tr("search_all_providers"))
        providers = set()
        for driver in self.current_drivers:
            provider = driver.get('provider', self.tr('unknown_provider'))
            if provider not in providers:
                providers.add(provider)
                provider_filter.addItem(provider)
        
        for combo in [class_filter, provider_filter]:
            combo.setStyleSheet("""
                QComboBox {
                    background-color: #2d2d2d;
                    border: 1px solid #3e3e42;
                    border-radius: 4px;
                    padding: 7px;
                    color: #ffffff;
                    min-width: 150px;
                }
                QComboBox::drop-down {
                    border: none;
                }
                QComboBox::down-arrow {
                    image: none;
                    border-left: 5px solid #2d2d2d;
                    border-right: 5px solid #2d2d2d;
                    border-top: 5px solid #ffffff;
                    margin-right: 5px;
                }
                QComboBox QAbstractItemView {
                    background-color: #2d2d2d;
                    border: 1px solid #3e3e42;
                    selection-background-color: #0078D4;
                    color: #ffffff;
                }
            """)
            filter_layout.addWidget(combo)
        
        search_options.addLayout(filter_layout)
        search_layout.addLayout(search_options)
        
        # İstatistik bilgileri
        stats_label = QLabel()
        stats_label.setStyleSheet("color: #0078D4; margin-top: 5px;")
        search_layout.addWidget(stats_label)
        
        layout.addWidget(search_frame)
        
        # Sonuç tablosu
        result_table = QTableWidget()
        result_table.setColumnCount(5)
        result_table.setHorizontalHeaderLabels([self.tr("comparison_driver_name"), self.tr("provider"), self.tr("class"), self.tr("date_version"), self.tr("status")])
        result_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        result_table.setAlternatingRowColors(True)
        result_table.setStyleSheet("""
            QTableWidget {
                background-color: #2d2d2d;
                gridline-color: #3e3e42;
                color: #ffffff;
                border: none;
            }
            QTableWidget::item {
                padding: 5px;
                color: #ffffff;
                background-color: #2d2d2d;
            }
            QTableWidget::item:alternate {
                background-color: #252526;
            }
            QTableWidget::item:selected {
                background-color: #094771;
                color: #ffffff;
            }
            QHeaderView::section {
                background-color: #1e1e1e;
                color: #0078D4;
                padding: 8px;
                border: none;
                border-right: 1px solid #3e3e42;
                border-bottom: 1px solid #3e3e42;
                font-weight: bold;
            }
            QTableWidget QTableCornerButton::section {
                background-color: #1e1e1e;
                border: none;
            }
        """)
        
        def update_search_results():
            search_text = search_box.text().lower()
            selected_class = class_filter.currentText()
            selected_provider = provider_filter.currentText()
            
            # Sonuçları filtrele
            filtered_drivers = []
            for driver in self.current_drivers:
                if (search_text in driver.get('original_name', '').lower() or
                    search_text in driver.get('provider', '').lower() or
                    search_text in driver.get('class', '').lower()):
                    if (selected_class == self.tr("search_all_classes") or driver.get('class') == selected_class) and \
                       (selected_provider == self.tr("search_all_providers") or driver.get('provider') == selected_provider):
                        filtered_drivers.append(driver)
            
            # Tablo güncelleme
            result_table.setRowCount(len(filtered_drivers))
            for i, driver in enumerate(filtered_drivers):
                result_table.setItem(i, 0, QTableWidgetItem(driver.get('original_name', '')))
                result_table.setItem(i, 1, QTableWidgetItem(driver.get('provider', '')))
                result_table.setItem(i, 2, QTableWidgetItem(driver.get('class', '')))
                result_table.setItem(i, 3, QTableWidgetItem(driver.get('date_version', '')))
                
                # Sürücü durumu (aktif/pasif)
                status = self.tr("search_status_active") if driver.get('published_name', '') else self.tr("search_status_inactive")
                status_item = QTableWidgetItem(status)
                status_item.setForeground(QColor("#1DB954") if status == self.tr("search_status_active") else QColor("#ff0000"))
                result_table.setItem(i, 4, status_item)
            
            # İstatistik güncelleme
            stats_label.setText(self.tr("search_stats_format").format(
                len(self.current_drivers), len(filtered_drivers), selected_class, selected_provider))
        
        # Sinyal bağlantıları
        search_box.textChanged.connect(update_search_results)
        class_filter.currentTextChanged.connect(update_search_results)
        provider_filter.currentTextChanged.connect(update_search_results)
        
        layout.addWidget(result_table)
        
        # Detay paneli
        detail_frame = QFrame()
        detail_frame.setStyleSheet("""
            QFrame {
                background-color: #252526;
                border: 1px solid #3e3e42;
                border-radius: 4px;
                padding: 10px;
            }
        """)
        detail_layout = QVBoxLayout(detail_frame)
        
        detail_title = QLabel(self.tr("search_driver_details"))
        detail_title.setStyleSheet("color: #0078D4; font-weight: bold; font-size: 14px;")
        detail_layout.addWidget(detail_title)
        
        detail_text = QTextEdit()
        detail_text.setReadOnly(True)
        detail_text.setStyleSheet("""
            QTextEdit {
                background-color: #1e1e1e;
                border: 1px solid #3e3e42;
                border-radius: 4px;
                padding: 8px;
                color: #ffffff;
                font-family: 'Cascadia Code', 'Consolas', monospace;
            }
        """)
        detail_layout.addWidget(detail_text)
        
        def show_driver_details(row, column):
            if row >= 0:
                driver_name = result_table.item(row, 0).text()
                driver = next((d for d in self.current_drivers 
                             if d.get('original_name') == driver_name), None)
                if driver:
                    details = (f"{self.tr('comparison_driver_name').replace(':', '')}: {driver.get('original_name')}\n"
                             f"{self.tr('published_name').replace(':', '')}: {driver.get('published_name')}\n"
                             f"{self.tr('provider').replace(':', '')}: {driver.get('provider')}\n"
                             f"{self.tr('class').replace(':', '')}: {driver.get('class')}\n"
                             f"{self.tr('date_version').replace(':', '')}: {driver.get('date_version')}\n")
                    detail_text.setText(details)
        
        result_table.cellClicked.connect(show_driver_details)
        
        layout.addWidget(detail_frame)
        
        # İlk aramayı tetikle
        update_search_results()
        
        dialog.setCentralWidget(central)
        dialog.show()

    def generate_system_report(self):
        """Sistem raporu oluştur"""
        dialog = QMainWindow(self)
        dialog.setWindowTitle(self.tr("report_window_title"))
        dialog.setGeometry(100, 100, 900, 700)
        dialog.setWindowIcon(QIcon("wdm.png"))
        
        central = QWidget()
        central.setStyleSheet("""
            QWidget {
                background-color: #1e1e1e;
                color: #d4d4d4;
                font-family: 'Segoe UI';
            }
        """)
        
        layout = QVBoxLayout(central)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)
        
        # Üst bilgi paneli
        info_frame = QFrame()
        info_frame.setStyleSheet("""
            QFrame {
                background-color: #252526;
                border: 1px solid #3e3e42;
                border-radius: 4px;
                padding: 15px;
            }
        """)
        info_layout = QVBoxLayout(info_frame)
        
        title = QLabel(self.tr("report_generation_title"))
        title.setStyleSheet("color: #0078D4; font-size: 16px; font-weight: bold; margin-bottom: 10px;")
        info_layout.addWidget(title)
        
        # Rapor seçenekleri
        options_frame = QFrame()
        options_frame.setStyleSheet("""
            QFrame {
                background-color: #2d2d2d;
                border: 1px solid #3e3e42;
                border-radius: 4px;
                padding: 10px;
            }
        """)
        options_layout = QVBoxLayout(options_frame)
        
        # Rapor seçenekleri başlığı
        options_title = QLabel(self.tr("report_options_title"))
        options_title.setStyleSheet("color: #0078D4; font-weight: bold;")
        options_layout.addWidget(options_title)
        
        # Seçenekler için checkbox'lar
        checkbox_style = """
            QCheckBox {
                color: #ffffff;
                spacing: 8px;
            }
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
                border: 1px solid #3e3e42;
                border-radius: 3px;
                background: #2d2d2d;
            }
            QCheckBox::indicator:checked {
                background: #0078D4;
                border: 1px solid #0078D4;
            }
            QCheckBox::indicator:hover {
                border: 1px solid #0078D4;
            }
        """
        
        include_system_info = QCheckBox(self.tr("report_system_info"))
        include_system_info.setChecked(True)
        include_system_info.setStyleSheet(checkbox_style)
        
        include_driver_stats = QCheckBox(self.tr("report_driver_stats"))
        include_driver_stats.setChecked(True)
        include_driver_stats.setStyleSheet(checkbox_style)
        
        include_driver_list = QCheckBox(self.tr("report_detailed_list"))
        include_driver_list.setChecked(True)
        include_driver_list.setStyleSheet(checkbox_style)
        
        include_problem_drivers = QCheckBox(self.tr("report_problem_drivers"))
        include_problem_drivers.setChecked(True)
        include_problem_drivers.setStyleSheet(checkbox_style)
        
        include_backup_history = QCheckBox(self.tr("report_backup_history"))
        include_backup_history.setChecked(True)
        include_backup_history.setStyleSheet(checkbox_style)
        
        options_layout.addWidget(include_system_info)
        options_layout.addWidget(include_driver_stats)
        options_layout.addWidget(include_driver_list)
        options_layout.addWidget(include_problem_drivers)
        options_layout.addWidget(include_backup_history)
        
        info_layout.addWidget(options_frame)
        layout.addWidget(info_frame)
        
        # Rapor önizleme alanı
        preview_frame = QFrame()
        preview_frame.setStyleSheet("""
            QFrame {
                background-color: #252526;
                border: 1px solid #3e3e42;
                border-radius: 4px;
                padding: 15px;
            }
        """)
        preview_layout = QVBoxLayout(preview_frame)
        
        preview_title = QLabel(self.tr("report_preview_title"))
        preview_title.setStyleSheet("color: #0078D4; font-weight: bold; font-size: 14px;")
        preview_layout.addWidget(preview_title)
        
        preview_text = QTextEdit()
        preview_text.setReadOnly(True)
        preview_text.setStyleSheet("""
            QTextEdit {
                background-color: #1e1e1e;
                border: 1px solid #3e3e42;
                border-radius: 4px;
                padding: 10px;
                font-family: 'Cascadia Code', 'Consolas', monospace;
                font-size: 12px;
                line-height: 1.5;
            }
        """)
        preview_layout.addWidget(preview_text)
        
        layout.addWidget(preview_frame)
        
        # Alt buton paneli
        button_frame = QFrame()
        button_frame.setStyleSheet("""
            QFrame {
                background-color: #252526;
                border: 1px solid #3e3e42;
                border-radius: 4px;
                padding: 10px;
            }
        """)
        button_layout = QHBoxLayout(button_frame)
        
        # Format seçimi
        format_combo = QComboBox()
        format_combo.addItems(["TXT", "HTML", "PDF"])
        format_combo.setStyleSheet("""
            QComboBox {
                background-color: #2d2d2d;
                border: 1px solid #3e3e42;
                border-radius: 4px;
                padding: 5px;
                color: #ffffff;
                min-width: 100px;
            }
            QComboBox::drop-down {
                border: none;
            }
            QComboBox::down-arrow {
                image: none;
                border-left: 5px solid #2d2d2d;
                border-right: 5px solid #2d2d2d;
                border-top: 5px solid #ffffff;
                margin-right: 5px;
            }
        """)
        button_layout.addWidget(format_combo)
        
        button_layout.addStretch()
        
        # Önizle butonu
        preview_btn = QPushButton(self.tr("report_preview_btn"))
        preview_btn.setStyleSheet("""
            QPushButton {
                background-color: #2ea043;
                border: none;
                border-radius: 4px;
                color: white;
                padding: 8px 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #3fb950;
            }
        """)
        button_layout.addWidget(preview_btn)
        
        # Rapor oluştur butonu
        generate_btn = QPushButton(self.tr("report_generate_btn"))
        generate_btn.setStyleSheet("""
            QPushButton {
                background-color: #0078D4;
                border: none;
                border-radius: 4px;
                color: white;
                padding: 8px 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #2b8dee;
            }
        """)
        button_layout.addWidget(generate_btn)
        
        layout.addWidget(button_frame)
        
        def generate_report_content():
            """Rapor içeriğini oluştur"""
            content = []
            
            if include_system_info.isChecked():
                content.append(self.tr("report_system_info_section"))
                content.append(self.tr("report_os_info").format(self.windows_version.major, self.windows_version.minor))
                content.append(self.tr("report_date_info").format(datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
                content.append("")
            
            if include_driver_stats.isChecked():
                content.append(self.tr("report_driver_stats_section"))
                content.append(self.tr("report_total_drivers").format(len(self.current_drivers)))
                
                classes = {}
                providers = {}
                for driver in self.current_drivers:
                    class_name = driver.get('class', 'Diğer')
                    provider = driver.get('provider', 'Bilinmiyor')
                    classes[class_name] = classes.get(class_name, 0) + 1
                    providers[provider] = providers.get(provider, 0) + 1
                
                content.append(f"\n{self.tr('report_driver_classes').format(len(classes))}")
                for class_name, count in sorted(classes.items(), key=lambda x: x[1], reverse=True):
                    percentage = (count / len(self.current_drivers)) * 100
                    content.append(f"- {class_name}: {count} sürücü (%{percentage:.1f})")
                
                content.append(f"\n{self.tr('report_provider_distribution').format(len(providers))}")
                for provider, count in sorted(providers.items(), key=lambda x: x[1], reverse=True):
                    percentage = (count / len(self.current_drivers)) * 100
                    content.append(f"- {provider}: {count} sürücü (%{percentage:.1f})")
                content.append("")
            
            if include_driver_list.isChecked():
                content.append(self.tr("report_detailed_list_section"))
                for driver in self.current_drivers:
                    content.append(f"Sürücü: {driver.get('original_name', '')}")
                    content.append(f"Yayın Adı: {driver.get('published_name', '')}")
                    content.append(f"Sağlayıcı: {driver.get('provider', '')}")
                    content.append(f"Sınıf: {driver.get('class', '')}")
                    content.append(f"Tarih/Versiyon: {driver.get('date_version', '')}")
                    content.append("-" * 50)
                content.append("")
            
            if include_problem_drivers.isChecked():
                content.append(self.tr("report_problem_section"))
                problem_found = False
                for driver in self.current_drivers:
                    if not driver.get('published_name'):
                        problem_found = True
                        content.append(self.tr("report_missing_info").format(driver.get('original_name', '')))
                if not problem_found:
                    content.append(self.tr("report_no_problems"))
                content.append("")
            
            if include_backup_history.isChecked():
                content.append(self.tr("report_backup_section"))
                if self.backup_history:
                    for backup in self.backup_history:
                        content.append(f"{self.tr('date')}: {backup['date']}")
                        content.append(f"{self.tr('location')}: {backup['location']}")
                        content.append(f"{self.tr('size')}: {backup['size']}")
                        content.append("-" * 30)
                else:
                    content.append(self.tr("report_no_backups"))
            
            return "\n".join(content)
     
            try:
                if format_type == "TXT":
                    filename = f"driver_report_{timestamp}.txt"
                    with open(filename, "w", encoding="utf-8") as f:
                        f.write(content)
                
                elif format_type == "HTML":
                    filename = f"driver_report_{timestamp}.html"
                    html_content = f"""
                    <!DOCTYPE html>
                    <html>
                    <head>
                        <meta charset="utf-8">
                        <style>
                            body {{ 
                                font-family: 'Segoe UI', sans-serif;
                                line-height: 1.6;
                                max-width: 1000px;
                                margin: 20px auto;
                                padding: 20px;
                                background: #1e1e1e;
                                color: #d4d4d4;
                            }}
                            h2 {{ color: #0078D4; }}
                            pre {{ 
                                background: #2d2d2d;
                                padding: 10px;
                                border-radius: 4px;
                                overflow-x: auto;
                            }}
                            .section {{
                                background: #252526;
                                border: 1px solid #3e3e42;
                                border-radius: 4px;
                                padding: 15px;
                                margin: 10px 0;
                            }}
                        </style>
                    </head>
                    <body>
                        <div class="section">
                            {content.replace("\n", "<br>").replace("===", "<h2>").replace("===", "</h2>")}
                        </div>
                    </body>
                    </html>
                    """
                    with open(filename, "w", encoding="utf-8") as f:
                        f.write(html_content)
                
                elif format_type == "PDF":
                    filename = f"driver_report_{timestamp}.pdf"
                    # PDF oluşturma kodu buraya gelecek
                    pass
                
                QMessageBox.information(dialog, self.tr("report_success_title"), 
                    self.tr("report_success_msg").format(filename))
                
                # Raporu otomatik aç
                os.startfile(filename)
                
            except Exception as e:
                QMessageBox.critical(dialog, self.tr("report_error_title"), 
                    self.tr("report_error_msg").format(str(e)))
        
        # Sinyal bağlantıları
        preview_btn.clicked.connect(update_preview)
        generate_btn.clicked.connect(save_report)
        include_system_info.stateChanged.connect(update_preview)
        include_driver_stats.stateChanged.connect(update_preview)
        include_driver_list.stateChanged.connect(update_preview)
        include_problem_drivers.stateChanged.connect(update_preview)
        include_backup_history.stateChanged.connect(update_preview)
        
        # İlk önizlemeyi göster
        update_preview()
        
        dialog.setCentralWidget(central)
        dialog.show()

    def show_help(self):
        """Yardım menüsünü göster"""
        dialog = QMainWindow(self)
        dialog.setWindowTitle(self.tr("help_window_title"))
        dialog.setGeometry(100, 100, 900, 700)
        dialog.setWindowIcon(QIcon("wdm.png"))
        
        central = QWidget()
        central.setStyleSheet("""
            QWidget {
                background-color: #1e1e1e;
                color: #d4d4d4;
                font-family: 'Segoe UI';
            }
        """)
        
        layout = QVBoxLayout(central)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)
        
        # Üst bilgi paneli
        header_frame = QFrame()
        header_frame.setStyleSheet("""
            QFrame {
                background-color: #252526;
                border: 1px solid #3e3e42;
                border-radius: 4px;
                padding: 15px;
            }
        """)
        header_layout = QHBoxLayout(header_frame)
        
        # Logo
        logo_label = QLabel()
        logo_pixmap = QPixmap("wdm.png")
        logo_pixmap = logo_pixmap.scaled(48, 48, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        logo_label.setPixmap(logo_pixmap)
        header_layout.addWidget(logo_label)
        
      
        # Tab widget
        tab_widget = QTabWidget()
        tab_widget.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #3e3e42;
                background-color: #252526;
                border-radius: 4px;
            }
            QTabWidget::tab-bar {
                alignment: left;
            }
            QTabBar::tab {
                background-color: #2d2d2d;
                color: #d4d4d4;
                padding: 8px 16px;
                border: 1px solid #3e3e42;
                border-bottom: none;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
            }
            QTabBar::tab:selected {
                background-color: #252526;
                border-bottom: 2px solid #0078D4;
            }
            QTabBar::tab:hover {
                background-color: #3e3e42;
            }
        """)
        
        # Başlangıç Rehberi Tab'ı
        quick_start = QWidget()
        quick_layout = QVBoxLayout(quick_start)
        
        quick_scroll = QScrollArea()
        quick_scroll.setWidgetResizable(True)
        quick_scroll.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: transparent;
            }
            QScrollBar:vertical {
                background-color: #2d2d2d;
                width: 12px;
            }
            QScrollBar::handle:vertical {
                background-color: #3e3e42;
                border-radius: 6px;
                min-height: 30px;
            }
            QScrollBar::handle:vertical:hover {
                background-color: #0078D4;
            }
        """)
        
        quick_content = QWidget()
        quick_content_layout = QVBoxLayout(quick_content)
        
        sections = [
            (self.tr("help_backup_title"), [
                self.tr("help_backup_step1"),
                self.tr("help_backup_step2"),
                self.tr("help_backup_step3"),
                self.tr("help_backup_step4")
            ]),
            (self.tr("help_restore_title"), [
                self.tr("help_restore_step1"),
                self.tr("help_restore_step2"),
                self.tr("help_restore_step3"),
                self.tr("help_restore_step4")
            ])
        ]
        
        for title, steps in sections:
            section_frame = QFrame()
            section_frame.setStyleSheet("""
                QFrame {
                    background-color: #2d2d2d;
                    border: 1px solid #3e3e42;
                    border-radius: 4px;
                    padding: 15px;
                    margin: 5px;
                }
            """)
            section_layout = QVBoxLayout(section_frame)
            
            section_title = QLabel(title)
            section_title.setStyleSheet("color: #0078D4; font-size: 14px; font-weight: bold; margin-bottom: 10px;")
            section_layout.addWidget(section_title)
            
            for step in steps:
                step_label = QLabel(step)
                step_label.setWordWrap(True)
                section_layout.addWidget(step_label)
            
            quick_content_layout.addWidget(section_frame)
        
        quick_scroll.setWidget(quick_content)
        quick_layout.addWidget(quick_scroll)
        
        # Özellikler Tab'ı
        features = QWidget()
        features_layout = QVBoxLayout(features)
        
        features_scroll = QScrollArea()
        features_scroll.setWidgetResizable(True)
        features_scroll.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: transparent;
            }
        """)
        
        features_content = QWidget()
        features_content_layout = QVBoxLayout(features_content)
        
        feature_list = [
            (self.tr("driver_analysis"), self.tr("help_feature_analysis")),
            (self.tr("driver_comparison"), self.tr("help_feature_comparison")),
            (self.tr("driver_search"), self.tr("help_feature_search")),
            (self.tr("system_report"), self.tr("help_feature_report")),
            (self.tr("backup_history"), self.tr("help_feature_history")),
            ("Otomatik Kontrol", self.tr("help_feature_auto_check"))
        ]
        
        for title, desc in feature_list:
            feature_frame = QFrame()
            feature_frame.setStyleSheet("""
                QFrame {
                    background-color: #2d2d2d;
                    border: 1px solid #3e3e42;
                    border-radius: 4px;
                    padding: 15px;
                    margin: 5px;
                }
            """)
            feature_layout = QVBoxLayout(feature_frame)
            
            feature_title = QLabel(title)
            feature_title.setStyleSheet("color: #0078D4; font-size: 14px; font-weight: bold;")
            feature_desc = QLabel(desc)
            feature_desc.setWordWrap(True)
            
            feature_layout.addWidget(feature_title)
            feature_layout.addWidget(feature_desc)
            
            features_content_layout.addWidget(feature_frame)
        
        features_scroll.setWidget(features_content)
        features_layout.addWidget(features_scroll)
        
        # SSS Tab'ı
        faq = QWidget()
        faq_layout = QVBoxLayout(faq)
        
        faq_scroll = QScrollArea()
        faq_scroll.setWidgetResizable(True)
        faq_scroll.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: transparent;
            }
        """)
        
        faq_content = QWidget()
        faq_content_layout = QVBoxLayout(faq_content)
        
        faqs = [
            (self.tr("help_faq_q1"), self.tr("help_faq_a1")),
            (self.tr("help_faq_q2"), self.tr("help_faq_a2")),
            (self.tr("help_faq_q3"), self.tr("help_faq_a3")),
            (self.tr("help_faq_q4"), self.tr("help_faq_a4"))
        ]
        
        for question, answer in faqs:
            faq_frame = QFrame()
            faq_frame.setStyleSheet("""
                QFrame {
                    background-color: #2d2d2d;
                    border: 1px solid #3e3e42;
                    border-radius: 4px;
                    padding: 15px;
                    margin: 5px;
                }
            """)
            faq_item_layout = QVBoxLayout(faq_frame)
            
            q_label = QLabel(question)
            q_label.setStyleSheet("color: #0078D4; font-size: 14px; font-weight: bold;")
            a_label = QLabel(answer)
            a_label.setWordWrap(True)
            
            faq_item_layout.addWidget(q_label)
            faq_item_layout.addWidget(a_label)
            
            faq_content_layout.addWidget(faq_frame)
        
        faq_scroll.setWidget(faq_content)
        faq_layout.addWidget(faq_scroll)
        
        # İletişim Tab'ı
        contact = QWidget()
        contact_layout = QVBoxLayout(contact)
        
        contact_frame = QFrame()
        contact_frame.setStyleSheet("""
            QFrame {
                background-color: #2d2d2d;
                border: 1px solid #3e3e42;
                border-radius: 4px;
                padding: 20px;
                margin: 5px;
            }
        """)
        contact_info_layout = QVBoxLayout(contact_frame)
        
        contact_info = [
            (self.tr("help_contact_developer"), "Fatih ÖNDER (CekToR)"),
            (self.tr("help_contact_email"), "info@algyazilim.com"),
            (self.tr("help_contact_web"), "https://algyazilim.com"),
            (self.tr("help_contact_github"), "https://github.com/cektor")
        ]
        
        for label, value in contact_info:
            info_layout = QHBoxLayout()
            label_widget = QLabel(label)
            label_widget.setStyleSheet("color: #0078D4; font-weight: bold;")
            value_widget = QLabel(value)
            value_widget.setStyleSheet("color: #d4d4d4;")
            
            info_layout.addWidget(label_widget)
            info_layout.addWidget(value_widget)
            info_layout.addStretch()
            
            contact_info_layout.addLayout(info_layout)
        
        contact_layout.addWidget(contact_frame)
        contact_layout.addStretch()
        
        # Tab'ları ekle
        tab_widget.addTab(quick_start, self.tr("help_quick_start"))
        tab_widget.addTab(features, self.tr("help_features"))
        tab_widget.addTab(faq, self.tr("help_faq"))
        tab_widget.addTab(contact, self.tr("help_contact"))
        
        layout.addWidget(tab_widget)
        
        dialog.setCentralWidget(central)
        dialog.show()

  
        about_text = f"""
        <div style='text-align: center; font-family: "Segoe UI", sans-serif;'>
            <p style='margin: 20px 0;'><img src='wdm.png' width='128' height='128' style='margin-bottom: 15px;'></p>
            <h1 style='color: #0078D4; margin: 10px 0; font-size: 24px; font-weight: bold;'>{self.tr("about_app_name")}</h1>
            <p style='color: #d4d4d4; font-size: 16px; margin: 15px 0;'>{self.tr("about_subtitle")}</p>
            <p style='color: #0078D4; font-size: 14px; margin: 10px 0;'>{self.tr("about_version")}</p>
            
            <div style='background-color: #2d2d2d; padding: 15px; margin: 20px 0; border-radius: 8px;'>
                <p style='color: #d4d4d4; margin: 10px 0;'>{self.tr("about_description")}</p>
            </div>

            <div style='text-align: left; margin: 20px 40px;'>
                <h2 style='color: #0078D4; font-size: 18px; margin: 10px 0;'>{self.tr("about_features_title")}</h2>
                <ul style='color: #d4d4d4; list-style-type: none; padding: 0;'>
                    <li style='margin: 8px 0;'>{self.tr("about_feature_backup")}</li>
                    <li style='margin: 8px 0;'>{self.tr("about_feature_restore")}</li>
                    <li style='margin: 8px 0;'>{self.tr("about_feature_analysis")}</li>
                    <li style='margin: 8px 0;'>{self.tr("about_feature_comparison")}</li>
                    <li style='margin: 8px 0;'>{self.tr("about_feature_search")}</li>
                    <li style='margin: 8px 0;'>{self.tr("about_feature_report")}</li>
                    <li style='margin: 8px 0;'>{self.tr("about_feature_history")}</li>
                    <li style='margin: 8px 0;'>{self.tr("about_feature_progress")}</li>
                </ul>
            </div>

            <div style='margin-top: 20px; padding-top: 20px; border-top: 1px solid #3e3e42;'>
                <p style='color: #d4d4d4; margin: 5px 0;'>{self.tr("about_developer")} <a href='https://fatihonder.org.tr' style='color: #0078D4; text-decoration: none;'>Fatih ÖNDER (CekToR)</a></p>
                <p style='color: #d4d4d4; margin: 5px 0;'>{self.tr("about_website")} <a href='https://algyazilim.com' style='color: #0078D4; text-decoration: none;'>ALG Yazılım & Elektronik Inc.©</a></p>
                <p style='color: #d4d4d4; margin: 5px 0;'>{self.tr("about_github")} <a href='https://github.com/cektor' style='color: #0078D4; text-decoration: none;'>github.com/cektor</a></p>
                <p style='color: #888888; font-size: 12px; margin-top: 15px;'>{self.tr("about_copyright")}</p>
                <p style='color: #ff0000; font-size: 14px; margin-top: 20px; font-weight: bold; text-align: center;'>{self.tr("about_license").format(self.username)}</p>
            </div>
        </div>
        """
        
        about_dialog.setTextFormat(Qt.RichText)
        about_dialog.setText(about_text)
        about_dialog.setStyleSheet("""
            QMessageBox {
                background-color: #252526;
            }
            QLabel {
                color: #d4d4d4;
                min-width: 500px;
                font-family: 'Segoe UI';
            }
            QPushButton {
                background-color: #0078D4;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 6px 12px;
                min-width: 60px;
            }
            QPushButton:hover {
                background-color: #2b8dee;
            }
        """)
        about_dialog.exec_()

    def backup_drivers(self):
        folder = QFileDialog.getExistingDirectory(self, self.tr("backup_folder_select"))
        if folder:
            try:
                # Sürücü listesini al
                drivers = self.get_driver_list()
                
                # Sürücü seçim dialogunu göster
                selected_drivers = self.show_driver_selection_dialog(self.tr("backup_window_title"), drivers, self.tr("select_drivers_to_backup"))
                if not selected_drivers:
                    return
                
                self.last_backup_folder = folder
                self.output_text.clear()
                self.progress_bar.setValue(0)
                self.progress_bar.show()
                self.backup_button.setEnabled(False)
                self.restore_button.setEnabled(False)
                self.statusBar.showMessage(self.tr("drivers_backing_up"))
                
                self.output_text.append(f"<span style='color: #1DB954;'>{self.tr('backup_starting')}</span>")
                self.output_text.append(f"<span style='color: #d4d4d4;'>{self.tr('backup_folder_label').format(folder)}</span>")
                
                # Önce mevcut sürücüleri say
                result = subprocess.run(['pnputil', '/enum-drivers'], capture_output=True, text=True)
                if result.returncode == 0:
                    total_drivers = len([line for line in result.stdout.split('\n') if 'Published Name:' in line or 'Yayınlanan İsim:' in line])
                    self.output_text.append(f"<span style='color: #0078D4;'>{self.tr('total_drivers_to_backup').format(total_drivers)}</span>")
                else:
                    total_drivers = 0
                    
                processed_drivers = 0
                
                # Windows sürümünü kontrol et ve uygun yedekleme yöntemini seç
                if self.windows_version.major >= 6 and self.windows_version.minor >= 2:  # Windows 8 ve üzeri
                    self.output_text.append(f"<span style='color: #0078D4;'>{self.tr('windows_version_detected').format('8')}</span>")
                    
                    process = subprocess.Popen(
                        ['powershell.exe', '-NoProfile', '-ExecutionPolicy', 'Bypass', 
                         'Export-WindowsDriver', '-Online', '-Destination', folder],
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        universal_newlines=True
                    )
                    
                    while True:
                        output = process.stdout.readline()
                        if output == '' and process.poll() is not None:
                            break
                        if output:
                            output = output.strip()
                            if "Driver package" in output:
                                processed_drivers += 1
                                progress = min(int((processed_drivers / total_drivers) * 100), 100)
                                self.progress_bar.setValue(progress)
                                self.output_text.append(f"<span style='color: #1DB954;'>{self.tr('driver_backing_up').format(output)}</span>")
                            QApplication.processEvents()
                            
                else:  # Windows 7 için alternatif yöntem
                    self.output_text.append(f"<span style='color: #0078D4;'>{self.tr('windows7_detected')}</span>")
                    source_path = os.path.join(os.environ["SystemRoot"], "System32", "DriverStore", "FileRepository")
                    
                
                            progress = min(int((idx / total_files) * 100), 100)
                            self.progress_bar.setValue(progress)
                            self.output_text.append(f"<span style='color: #1DB954;'>{self.tr('driver_copied').format(rel_path)}</span>")
                        except Exception as e:
                            self.output_text.append(f"<span style='color: #ffd700;'>{self.tr('copy_warning').format(rel_path, str(e))}</span>")
                        
                        QApplication.processEvents()
                
                # Yedekleme geçmişine ekle
                backup_size = self.get_folder_size(folder)
                self.backup_history.append({
                    "date": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "location": folder,
                    "size": self.format_size(backup_size)
                })
                self.save_backup_history()
                
                success_msg = self.tr("backup_success_msg").format(folder, self.format_size(backup_size))
                self.start_operation_finished(True, "", success_msg)
                self.output_text.append(f"<span style='color: #1DB954;'>{self.tr('backup_history_updated')}</span>")
                
            except Exception as e:
                self.output_text.append(f"<span style='color: #ff0000;'>Hata oluştu: {str(e)}</span>")
                self.progress_bar.hide()
                self.backup_button.setEnabled(True)
                self.restore_button.setEnabled(True)
                self.statusBar.showMessage(self.tr("operation_error"))

    def get_driver_list(self):
        """Sistemdeki sürücüleri listele"""
        try:
            result = subprocess.run(['pnputil', '/enum-drivers'], capture_output=True, text=True, encoding='cp857')
            if result.returncode == 0:
                drivers = []
                current_driver = {}
                
                for line in result.stdout.split('\n'):
                    line = line.strip()
                    if not line:
                        continue
                        
                    if 'Yayınlanan İsim:' in line or 'Published Name:' in line:
                        if current_driver:
                            if not 'original_name' in current_driver:
                                current_driver['original_name'] = self.tr('unknown_driver')
                            if not 'provider' in current_driver:
                                current_driver['provider'] = self.tr('unknown_provider')
                            if not 'class' in current_driver:
                                current_driver['class'] = self.tr('unknown_class')
                            drivers.append(current_driver.copy())
                        current_driver = {'oem_inf': line.split(':', 1)[1].strip()}
                    elif 'Özgün İsim:' in line or 'Original Name:' in line:
                        current_driver['original_name'] = line.split(':', 1)[1].strip()
                    elif 'Sağlayıcı:' in line or 'Provider:' in line:
                        current_driver['provider'] = line.split(':', 1)[1].strip()
                    elif 'Sınıf:' in line or 'Class:' in line:
                        current_driver['class'] = line.split(':', 1)[1].strip()
                
                if current_driver:
                    if not 'original_name' in current_driver:
                        current_driver['original_name'] = self.tr('unknown_driver')
                    if not 'provider' in current_driver:
                        current_driver['provider'] = self.tr('unknown_provider')
                    if not 'class' in current_driver:
                        current_driver['class'] = self.tr('unknown_class')
                    drivers.append(current_driver.copy())
                
                if not drivers:
                    raise Exception(self.tr('no_drivers_found'))
                
                return drivers
            else:
                raise Exception(self.tr('no_drivers_found'))
        except Exception as e:
            raise Exception(f"{self.tr('error')}: {str(e)}")
    
    def get_folder_size(self, folder):
        total_size = 0
        for dirpath, dirnames, filenames in os.walk(folder):
            for f in filenames:
                fp = os.path.join(dirpath, f)
                total_size += os.path.getsize(fp)
        return total_size

    def show_driver_selection_dialog(self, title, drivers, operation_type):
        """Sürücü seçim dialogunu göster"""
        dialog = QDialog(self)
        dialog.setWindowTitle(title)
        dialog.setWindowIcon(QIcon("wdm.png"))
        dialog.setMinimumWidth(700)
        dialog.setMinimumHeight(500)
        dialog.setStyleSheet("""
            QDialog {
                background-color: #1e1e1e;
                color: #d4d4d4;
            }
            QWidget {
                background-color: #1e1e1e;
                color: #d4d4d4;
                font-family: 'Segoe UI';
            }
            QLabel {
                background: transparent;
                color: #d4d4d4;
                font-family: 'Segoe UI';
            }
            QScrollArea {
                border: 1px solid #3e3e42;
                background-color: #252526;
            }
            QScrollBar:vertical {
                background-color: #2d2d2d;
                width: 14px;
                margin: 0px;
            }
            QScrollBar::handle:vertical {
                background-color: #3e3e42;
                border-radius: 6px;
                min-height: 30px;
            }
            QScrollBar::handle:vertical:hover {
                background-color: #0078D4;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
            QCheckBox {
                spacing: 8px;
                color: #d4d4d4;
                padding: 5px;
                font-family: 'Segoe UI';
            }
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
                border: 1px solid #3e3e42;
                border-radius: 3px;
                background: #2d2d2d;
            }
            QCheckBox::indicator:checked {
                background: #0078D4;
                border: 1px solid #0078D4;
            }
            QCheckBox::indicator:hover {
                border: 1px solid #0078D4;
            }
        """)
        
        layout = QVBoxLayout(dialog)
        
        # Başlık ve açıklama
        header = QLabel(f"{self.tr('select_lang')} {operation_type} {self.tr('comparison_driver_name').lower()}:")
        header.setStyleSheet("color: #0078D4; font-size: 14px; font-weight: bold; margin: 10px 0;")
        layout.addWidget(header)
        
        # Üst bilgi paneli
        header_frame = QFrame()
        header_frame.setStyleSheet("""
            QFrame {
                background-color: #252526;
                border: 1px solid #3e3e42;
                border-radius: 4px;
                padding: 10px;
                margin-bottom: 10px;
            }
        """)
        header_layout = QVBoxLayout(header_frame)
        
        # Logo ve başlık
        title_layout = QHBoxLayout()
        logo_label = QLabel()
        logo_pixmap = QPixmap("wdm.png")
        logo_pixmap = logo_pixmap.scaled(32, 32, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        logo_label.setPixmap(logo_pixmap)
        title_layout.addWidget(logo_label)
        
        title_text = QLabel(f"{title}")
        title_text.setStyleSheet("color: #0078D4; font-size: 16px; font-weight: bold;")
        title_layout.addWidget(title_text)
        title_layout.addStretch()
        header_layout.addLayout(title_layout)
        
        # Açıklama
        desc_label = QLabel(f"{self.tr('select_lang')} {operation_type} {self.tr('comparison_driver_name').lower()}:")
        desc_label.setStyleSheet("color: #d4d4d4; font-size: 12px; margin-top: 5px;")
        header_layout.addWidget(desc_label)
        
        layout.addWidget(header_frame)
        
        # Sürücü listesi
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("""
            QScrollArea {
                border: 1px solid #3e3e42;
                background-color: #252526;
            }
            QScrollArea > QWidget > QWidget {
                background-color: #252526;
            }
        """)
        
        container = QWidget()
        container_layout = QVBoxLayout(container)
        
        # Tümünü Seç checkbox'ı
        select_all = QCheckBox(self.tr("select_all"))
        select_all.setStyleSheet("""
            QCheckBox {
                color: #0078D4;
                font-weight: bold;
                padding: 5px;
            }
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
                border: 1px solid #3e3e42;
                border-radius: 3px;
                background: #2d2d2d;
            }
            QCheckBox::indicator:checked {
                background: #0078D4;
                border: 1px solid #0078D4;
            }
            QCheckBox::indicator:hover {
                border: 1px solid #0078D4;
            }
        """)
        container_layout.addWidget(select_all)
        
        # Ayırıcı çizgi
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        line.setStyleSheet("background-color: #3e3e42;")
        container_layout.addWidget(line)
        
        # Sürücü checkbox'ları
        driver_checkboxes = []
        for driver in drivers:
            # Sürücü container frame'i
            driver_frame = QFrame()
            driver_frame.setStyleSheet("""
                QFrame {
                    background-color: #2d2d2d;
                    border: 1px solid #3e3e42;
                    border-radius: 6px;
                    margin: 4px;
                    padding: 10px;
                }
                QFrame:hover {
                    background-color: #333333;
                    border: 1px solid #0078D4;
                }
                QLabel {
                    color: #d4d4d4;
                }
            """)
            driver_layout = QVBoxLayout(driver_frame)
            driver_layout.setContentsMargins(5, 5, 5, 5)
            
            # Ana checkbox
            checkbox = QCheckBox()
            checkbox.setProperty("oem_inf", driver['oem_inf'])
            
            # Sürücü bilgileri
            name_label = QLabel(f"<b>{driver['original_name']}</b>")
            name_label.setStyleSheet("color: #0078D4; font-size: 12px;")
            
            info_label = QLabel(f"Sağlayıcı: {driver['provider']}\nSınıf: {driver['class']}\nINF: {driver['oem_inf']}")
            info_label.setStyleSheet("color: #d4d4d4; font-size: 11px;")
            
            driver_layout.addWidget(name_label)
            driver_layout.addWidget(info_label)
            
            # Checkbox'ı frame'in sol üst köşesine yerleştir
            checkbox_container = QHBoxLayout()
            checkbox_container.addWidget(checkbox)
            checkbox_container.addStretch()
            driver_layout.insertLayout(0, checkbox_container)
            
            driver_checkboxes.append(checkbox)
            container_layout.addWidget(driver_frame)
        
        scroll.setWidget(container)
        layout.addWidget(scroll)
        
        # Butonlar
        button_layout = QHBoxLayout()
        
        ok_button = QPushButton(self.tr("ok"))
        ok_button.setStyleSheet("""
            QPushButton {
                background-color: #0078D4;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
                min-width: 80px;
            }
            QPushButton:hover {
                background-color: #2b8dee;
            }
        """)
        
        cancel_button = QPushButton(self.tr("cancel"))
        cancel_button.setStyleSheet("""
            QPushButton {
                background-color: #2d2d2d;
                color: white;
                border: 1px solid #3e3e42;
                border-radius: 4px;
                padding: 8px 16px;
                min-width: 80px;
            }
            QPushButton:hover {
                background-color: #3e3e42;
            }
        """)
        
        button_layout.addWidget(ok_button)
        button_layout.addWidget(cancel_button)
        layout.addLayout(button_layout)
        
        # Tümünü Seç fonksiyonu
        def toggle_all(state):
            for cb in driver_checkboxes:
                cb.setChecked(state == Qt.Checked)
        
        select_all.stateChanged.connect(toggle_all)
        ok_button.clicked.connect(dialog.accept)
        cancel_button.clicked.connect(dialog.reject)
        
        if dialog.exec_() == QDialog.Accepted:
            return [cb.property("oem_inf") for cb in driver_checkboxes if cb.isChecked()]
        return None

  
    def restore_drivers(self):
        try:
            selected_folder = QFileDialog.getExistingDirectory(self, self.tr("restore_folder_select"))
            if not selected_folder:
                return
            
            print(f"Seçilen klasör: {selected_folder}")  # Debug için
                
            # INF dosyalarını bul ve sürücü bilgilerini hazırla
            inf_files = []
            drivers = []
            
            for root, dirs, files in os.walk(selected_folder):
                for file in files:
                    if file.endswith('.inf'):
                        inf_path = os.path.join(root, file)
                        relative_path = os.path.relpath(inf_path, selected_folder)
                        driver_info = {
                            'oem_inf': relative_path,
                            'original_name': os.path.splitext(file)[0],
                            'provider': self.tr('backed_up_driver'),
                            'class': os.path.basename(os.path.dirname(relative_path))
                        }
                        drivers.append(driver_info)
                        inf_files.append(inf_path)
            
            if not inf_files:
                QMessageBox.warning(self, self.tr("error"), self.tr("no_drivers_found"))
                return
                
            selected_drivers = self.show_driver_selection_dialog(self.tr("restore_window_title"), drivers, self.tr("select_drivers_to_restore"))
            if not selected_drivers:
                return
                
            selected_paths = [os.path.join(selected_folder, d['oem_inf']) for d in drivers if d['oem_inf'] in selected_drivers]
            
            self.output_text.clear()
            self.progress_bar.setValue(0)
            self.progress_bar.show()
            self.backup_button.setEnabled(False)
            self.restore_button.setEnabled(False)
            
            self.statusBar.showMessage(self.tr("drivers_loading"))
            self.output_text.append(f"<span style='color: #1DB954;'>{self.tr('restore_starting')}</span>")
            self.output_text.append(f"<span style='color: #d4d4d4;'>{self.tr('restore_folder_label').format(selected_folder)}</span>")
                
            # INF dosyalarını say ve işlem başlat
            self.output_text.append(f"<span style='color: #0078D4;'>{self.tr('total_drivers_found').format(len(inf_files))}</span>")
                
            # Sürücüleri tek tek kontrol ederek yükle
            skipped_drivers = []
            installed_drivers = []
            total_drivers = len(selected_paths)
            
            for idx, rel_path in enumerate(selected_paths, 1):
                inf_path = os.path.join(selected_folder, rel_path)
                
                # Önce sürücünün durumunu kontrol et
                check_cmd = f'pnputil /enum-drivers | findstr /i "{os.path.splitext(os.path.basename(inf_path))[0]}"'
                check_result = subprocess.run(check_cmd, shell=True, capture_output=True, text=True)
                
                if check_result.returncode == 0:
                    skipped_drivers.append(rel_path)
                    self.output_text.append(f"<span style='color: #ffd700;'>{self.tr('skipped_already_installed').format(rel_path)}</span>")
                else:
                    # Sürücüyü yükle
                    install_cmd = f'pnputil /add-driver "{inf_path}" /install'
                    install_result = subprocess.run(install_cmd, shell=True, capture_output=True, text=True)
                    
                    if install_result.returncode == 0:
                        installed_drivers.append(rel_path)
                        self.output_text.append(f"<span style='color: #1DB954;'>{self.tr('successfully_installed').format(rel_path)}</span>")
                    else:
                        self.output_text.append(f"<span style='color: #ff0000;'>{self.tr('installation_error').format(rel_path)}</span>")
                
                self.progress_bar.setValue(int((idx / total_drivers) * 100))
                QApplication.processEvents()
            
            # İşlem sonuç raporu
            summary = f"\n{self.tr('installation_summary')}\n"
            summary += f"{self.tr('total_drivers_label').format(total_drivers)}\n"
            summary += f"{self.tr('installed_label').format(len(installed_drivers))}\n"
            summary += f"{self.tr('skipped_label').format(len(skipped_drivers))}\n"
            
            self.output_text.append(f"<span style='color: #0078D4;'>{summary}</span>")
            
            if installed_drivers:
                self.show_restart_dialog(summary)
            else:
                self.start_operation_finished(True, "", self.tr("all_drivers_installed"))
                    
        except Exception as e:
            self.output_text.append(f"<span style='color: #ff0000;'>Hata oluştu: {str(e)}</span>")
            self.progress_bar.hide()
            self.backup_button.setEnabled(True)
            self.restore_button.setEnabled(True)
            QMessageBox.critical(self, "Hata", f"Geri yükleme başlatılırken hata oluştu: {str(e)}")
                        
        except Exception as e:
            self.output_text.append(f"<span style='color: #ff0000;'>Hata oluştu: {str(e)}</span>")
            self.progress_bar.hide()
            self.backup_button.setEnabled(True)
            self.restore_button.setEnabled(True)
            QMessageBox.critical(self, "Hata", f"Geri yükleme başlatılırken hata oluştu: {str(e)}")

    def start_operation(self, cmd, success_msg, error_msg, driver_count=None):
        self.output_text.clear()
        self.progress_bar.setValue(0)
        self.progress_bar.show()
        self.statusBar.showMessage("İşlem devam ediyor...")
        
        try:
            # Dosya sayısını belirle
            if driver_count is not None:
                # Eğer sürücü sayısı dışarıdan belirtilmişse onu kullan
                file_count = driver_count
            elif "System32\\DriverStore" in cmd:
                # Yedekleme işlemi için dosya sayısını hesapla
                source_path = os.path.join(os.environ["SystemRoot"], "System32", "DriverStore", "FileRepository")
                file_count = sum([len(files) for r, d, files in os.walk(source_path)])
            else:
                # Windows 8 ve üzeri için sürücü sayısını al
                result = subprocess.run(['pnputil', '/enum-drivers'], capture_output=True, text=True)
                if result.returncode == 0:
                    file_count = len([line for line in result.stdout.split('\n') if 'Yayınlanan İsim:' in line])
                else:
                    file_count = None
            
            self.worker = WorkerThread(cmd, file_count)
        except:
            self.worker = WorkerThread(cmd)
            
        self.worker.progress.connect(self.update_progress)
        self.worker.output.connect(self.update_output)
        self.worker.finished.connect(lambda success, error: self.operation_finished(success, error, success_msg, error_msg))
        self.worker.start()

    def update_progress(self, value):
        self.progress_bar.setValue(value)

    def update_output(self, text):
        if "sistemde zaten mevcut" in text:
            # Zaten var olan sürücüler için özel formatlama
            self.output_text.append(f"<span style='color: #ffd700;'>{text}</span>")
        elif "Sürücü paketi başarıyla eklendi" in text or "Sürücü paketi yüklü" in text:
            # Başarılı işlemler için yeşil renk
            self.output_text.append(f"<span style='color: #1DB954;'>{text}</span>")
        else:
            self.output_text.append(text)

    def operation_finished(self, success, error, success_msg, error_msg):
        self.progress_bar.hide()
        self.backup_button.setEnabled(True)
        self.restore_button.setEnabled(True)
        
        if success or "sistemde zaten mevcut" in error:
            # Eğer işlem bir geri yükleme işlemi ise, yeniden başlatma öner
            if "geri yükleme" in success_msg.lower():
                restart_msg = QMessageBox(self)
                restart_msg.setWindowTitle("Yeniden Başlatma Gerekli")
                restart_msg.setText("Sürücüler başarıyla geri yüklendi.\n\nDeğişikliklerin etkili olması için bilgisayarınızı yeniden başlatmanız önerilir.")
                restart_msg.setIcon(QMessageBox.Information)
                restart_msg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
                restart_msg.setDefaultButton(QMessageBox.Yes)
                restart_msg.setStyleSheet("""
                    QMessageBox {
                        background-color: #252526;
                    }
                    QLabel {
                        color: #d4d4d4;
                        font-family: 'Segoe UI';
                    }
                    QPushButton {
                        background-color: #0078D4;
                        color: white;
                        border: none;
                        border-radius: 4px;
                        padding: 6px 12px;
                        min-width: 60px;
                    }
                    QPushButton:hover {
                        background-color: #2b8dee;
                    }
                    QPushButton#qt_msgbox_no {
                        background-color: #2d2d2d;
                        border: 1px solid #3e3e42;
                    }
                    QPushButton#qt_msgbox_no:hover {
                        background-color: #3e3e42;
                    }
                """)
                
                if restart_msg.exec_() == QMessageBox.Yes:
                    # Bilgisayarı yeniden başlat
                    try:
                        os.system("shutdown /r /t 5")
                        QMessageBox.information(self, self.tr("restarting"), 
                            self.tr("restart_in_5_sec"))
                    except:
                        QMessageBox.warning(self, self.tr("warning"), 
                            self.tr("restart_failed"))
            else:
                QMessageBox.information(self, "Başarılı", success_msg)
            
            self.statusBar.showMessage("İşlem başarıyla tamamlandı")
        else:
            self.output_text.append(error)
            QMessageBox.critical(self, "Hata", error_msg)
            self.statusBar.showMessage("İşlem sırasında hata oluştu")
            
    def start_operation_finished(self, success, error, success_msg):
        """Özel işlem tamamlama metodu"""
        self.progress_bar.hide()
        self.backup_button.setEnabled(True)
        self.restore_button.setEnabled(True)
        
        if success:
            QMessageBox.information(self, "Başarılı", success_msg)
            self.statusBar.showMessage("İşlem başarıyla tamamlandı")
        else:
            self.output_text.append(error)
            QMessageBox.critical(self, "Hata", error)
            self.statusBar.showMessage("İşlem sırasında hata oluştu")

    def run_command(self, cmd, success_msg, error_msg):
        try:
            self.output_text.append(f"Komut çalıştırılıyor: {' '.join(cmd)}\n")
            result = subprocess.run(cmd, capture_output=True, text=True, shell=False)
            self.output_text.append(result.stdout)
            if result.returncode == 0:
                QMessageBox.information(self, "Başarılı", success_msg)
            else:
                self.output_text.append(result.stderr)
                QMessageBox.critical(self, "Hata", error_msg)
        except Exception as e:
            self.output_text.append(str(e))
            QMessageBox.critical(self, "Hata", str(e))

    def show_restart_dialog(self, summary):
        """Yeniden başlatma dialogunu göster"""
        restart_msg = QMessageBox(self)
        restart_msg.setWindowTitle(self.tr("restart_recommended_title"))
        restart_msg.setText(self.tr("restart_recommended_msg"))
        restart_msg.setInformativeText(summary)
        restart_msg.setIcon(QMessageBox.Information)
        restart_msg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        restart_msg.setDefaultButton(QMessageBox.Yes)
        restart_msg.setStyleSheet("""
            QMessageBox {
                background-color: #252526;
            }
            QLabel {
                color: #d4d4d4;
                font-family: 'Segoe UI';
            }
            QPushButton {
                background-color: #0078D4;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 6px 12px;
                min-width: 60px;
            }
            QPushButton:hover {
                background-color: #2b8dee;
            }
            QPushButton#qt_msgbox_no {
                background-color: #2d2d2d;
                border: 1px solid #3e3e42;
            }
            QPushButton#qt_msgbox_no:hover {
                background-color: #3e3e42;
            }
        """)
        
        if restart_msg.exec_() == QMessageBox.Yes:
            try:
                os.system("shutdown /r /t 5")
                QMessageBox.information(self, self.tr("restarting"), 
                    self.tr("restarting_in_5_sec"))
            except:
                QMessageBox.warning(self, self.tr("warning"), 
                    self.tr("restart_failed_manual"))
        else:
            self.start_operation_finished(True, "", self.tr("drivers_successfully_restored") + "\n" + summary)

    def restart_computer(self):
        """Bilgisayarı yeniden başlat"""
        reply = QMessageBox.question(
            self,
            self.tr('restart_title'),
            self.tr('restart_msg'),
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            try:
                if sys.platform == 'win32':
                    subprocess.run(['shutdown', '/r', '/t', '0'], check=True)
            except Exception as e:
                QMessageBox.critical(self, self.tr("error"), 
                    f"Yeniden başlatma sırasında hata oluştu: {str(e)}")
                    
    def change_language(self, lang_code):
        """Uygulama dilini değiştir"""
        if lang_code != self.current_lang:
            # Dil ayarını kaydet
            self.save_language_setting(lang_code)
            
            # Dil değişikliği onay mesajı
            msg = QMessageBox(self)
            msg.setWindowTitle(self.tr("restart_app_title"))
            msg.setText(self.tr("restart_app"))
            msg.setIcon(QMessageBox.Information)
            msg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
            msg.setDefaultButton(QMessageBox.Yes)
            
            # Mesaj kutusu stil
            msg.setStyleSheet("""
                QMessageBox {
                    background-color: #252526;
                }
                QLabel {
                    color: #d4d4d4;
                    font-family: 'Segoe UI';
                }
                QPushButton {
                    background-color: #0078D4;
                    color: white;
                    border: none;
                    border-radius: 4px;
                    padding: 6px 12px;
                    min-width: 60px;
                }
                QPushButton:hover {
                    background-color: #2b8dee;
                }
                QPushButton#qt_msgbox_no {
                    background-color: #2d2d2d;
                    border: 1px solid #3e3e42;
                }
                QPushButton#qt_msgbox_no:hover {
                    background-color: #3e3e42;
                }
            """)
            
            if msg.exec_() == QMessageBox.Yes:
                # Uygulamayı yeniden başlat
                if getattr(sys, 'frozen', False):
                    # PyInstaller ile build edilmiş exe için
                    os.execl(sys.executable, sys.executable)
                else:
                    # Normal Python script için
                    python = sys.executable
                    os.execl(python, python, *sys.argv)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    # Uygulama ikonunu ayarla
    app_icon = QIcon("wdm.png")
    app.setWindowIcon(app_icon)
    
    # Windows'ta görev çubuğu ikonunu ayarla
    if sys.platform == 'win32':
        import ctypes
        myappid = 'alg.wdm.driverbackup.1.0.2'  # Benzersiz bir uygulama kimliği
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
    
    window = DriverBackupApp()
    window.show()
    sys.exit(app.exec_())