import sys
import json
import concurrent.futures
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QTabWidget, QVBoxLayout, QWidget, QLineEdit,
    QToolBar, QFileDialog, QMessageBox, QPushButton, QProgressBar, QStyle,
    QLabel, QHBoxLayout, QTabBar, QMenu, QDockWidget, QListWidget, QListWidgetItem,
    QDialog, QGroupBox, QComboBox, QCheckBox
)
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWebEngineCore import (
    QWebEngineProfile, QWebEngineDownloadRequest, QWebEngineSettings,
    QWebEngineUrlRequestInterceptor
)
from PySide6.QtCore import QUrl, Qt, Signal, QObject, QSize
from PySide6.QtGui import QAction, QKeySequence, QIcon

DARK_MODE_QSS = """
    QWidget { background-color: #2b2b2b; color: #ffffff; border: none; }
    QMainWindow { background-color: #2b2b2b; }
    QDockWidget::title { background-color: #3c3c3c; padding: 4px; border-radius: 4px; }
    QTabWidget::pane { border-top: 1px solid #3c3c3c; }
    QTabBar::tab { background: #2b2b2b; color: #ffffff; padding: 8px 20px; border-top-left-radius: 4px; border-top-right-radius: 4px; border-bottom: none; }
    QTabBar::tab:selected { background: #3c3c3c; border-bottom: none; }
    QTabBar::tab:hover { background: #4a4a4a; }
    QToolBar { background-color: #3c3c3c; padding: 5px; spacing: 5px; }
    QToolBar QToolButton, QPushButton { background-color: #555555; color: #ffffff; padding: 8px 12px; border-radius: 4px; }
    QToolBar QToolButton:hover, QPushButton:hover { background-color: #6a6a6a; }
    QLineEdit { background-color: #3c3c3c; color: #ffffff; padding: 8px; border-radius: 4px; border: 1px solid #555555; }
    QProgressBar { border: 1px solid #555; border-radius: 4px; background-color: #3c3c3c; height: 12px; text-align: center; color: white; }
    QProgressBar::chunk { background-color: #007acc; border-radius: 4px; }
    QMenu { background-color: #3c3c3c; color: #ffffff; border: 1px solid #555; }
    QMenu::item:selected { background-color: #007acc; }
    QListWidget { background-color: #3c3c3c; border-radius: 4px; }
    QGroupBox { font-weight: bold; }
"""

LIGHT_MODE_QSS = """
    QWidget { background-color: #f0f0f0; color: #000000; border: none; }
    QMainWindow { background-color: #f0f0f0; }
    QDockWidget::title { background-color: #e0e0e0; padding: 4px; border-radius: 4px; }
    QTabWidget::pane { border-top: 1px solid #dcdcdc; }
    QTabBar::tab { background: #f0f0f0; color: #000000; padding: 8px 20px; border-top-left-radius: 4px; border-top-right-radius: 4px; border-bottom: none; }
    QTabBar::tab:selected { background: #ffffff; border: 1px solid #dcdcdc; border-bottom-color: #ffffff; }
    QTabBar::tab:hover { background: #e6e6e6; }
    QToolBar { background-color: #ffffff; padding: 5px; spacing: 5px; border-bottom: 1px solid #dcdcdc; }
    QToolBar QToolButton, QPushButton { background-color: #e0e0e0; color: #000000; padding: 8px 12px; border-radius: 4px; }
    QToolBar QToolButton:hover, QPushButton:hover { background-color: #d0d0d0; }
    QLineEdit { background-color: #ffffff; color: #000000; padding: 8px; border-radius: 4px; border: 1px solid #dcdcdc; }
    QProgressBar { border: 1px solid #dcdcdc; border-radius: 4px; background-color: #e0e0e0; height: 12px; text-align: center; color: black; }
    QProgressBar::chunk { background-color: #0078d7; border-radius: 4px; }
    QMenu { background-color: #ffffff; color: #000000; border: 1px solid #dcdcdc; }
    QMenu::item:selected { background-color: #0078d7; color: #ffffff; }
    QListWidget { background-color: #ffffff; border-radius: 4px; }
    QGroupBox { font-weight: bold; }
"""

class AdBlockInterceptor(QWebEngineUrlRequestInterceptor):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.ad_domains = {
            "doubleclick.net", "adservice.google.com", "googlesyndication.com",
            "ad.doubleclick.net", "google-analytics.com", "c.amazon-adsystem.com",
            "pagead2.googlesyndication.com", "tpc.googlesyndication.com",
        }

    def interceptRequest(self, info):
        url = info.requestUrl().host()
        if any(domain in url for domain in self.ad_domains):
            info.block(True)

class SettingsDialog(QDialog):
    theme_changed = Signal(str)
    custom_theme_path_selected = Signal(str)
    javascript_toggled = Signal(bool)
    adblock_toggled = Signal(bool)
    homepage_changed = Signal(str)
    clear_data_requested = Signal()

    def __init__(self, parent):
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.setMinimumWidth(450)
        
        self.main_layout = QVBoxLayout(self)
        self.tab_widget = QTabWidget()

        self.setup_appearance_tab()
        self.setup_privacy_tab()
        self.setup_general_tab()

        close_button = QPushButton("Close")
        close_button.clicked.connect(self.accept)

        self.main_layout.addWidget(self.tab_widget)
        self.main_layout.addWidget(close_button, 0, Qt.AlignmentFlag.AlignRight)

    def setup_appearance_tab(self):
        appearance_tab = QWidget()
        layout = QVBoxLayout(appearance_tab)
        
        theme_layout = QHBoxLayout()
        theme_label = QLabel("Theme:")
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["Light", "Dark", "Custom"])
        theme_layout.addWidget(theme_label)
        theme_layout.addWidget(self.theme_combo)
        
        self.load_custom_button = QPushButton("Load Custom Theme...")
        self.load_custom_button.setEnabled(False)

        layout.addLayout(theme_layout)
        layout.addWidget(self.load_custom_button)
        layout.addStretch()
        
        self.tab_widget.addTab(appearance_tab, "Appearance")

        self.theme_combo.currentTextChanged.connect(self.on_theme_selection_changed)
        self.load_custom_button.clicked.connect(self.load_custom_theme_file)

    def setup_privacy_tab(self):
        privacy_tab = QWidget()
        layout = QVBoxLayout(privacy_tab)

        self.js_checkbox = QCheckBox("Enable JavaScript")
        self.adblock_checkbox = QCheckBox("Enable Basic Ad Blocker")
        clear_data_button = QPushButton("Clear Browse Data...")
        
        layout.addWidget(self.js_checkbox)
        layout.addWidget(self.adblock_checkbox)
        layout.addStretch()
        layout.addWidget(clear_data_button)
        
        self.tab_widget.addTab(privacy_tab, "Privacy & Content")
        
        self.js_checkbox.toggled.connect(self.javascript_toggled.emit)
        self.adblock_checkbox.toggled.connect(self.adblock_toggled.emit)
        clear_data_button.clicked.connect(self.clear_data_requested.emit)

    def setup_general_tab(self):
        general_tab = QWidget()
        layout = QVBoxLayout(general_tab)
        
        homepage_layout = QHBoxLayout()
        homepage_label = QLabel("Homepage URL:")
        self.homepage_edit = QLineEdit()
        homepage_layout.addWidget(homepage_label)
        homepage_layout.addWidget(self.homepage_edit)
        
        layout.addLayout(homepage_layout)
        layout.addStretch()

        self.tab_widget.addTab(general_tab, "General")

        self.homepage_edit.textChanged.connect(self.homepage_changed.emit)

    def on_theme_selection_changed(self, theme_name):
        self.load_custom_button.setEnabled(theme_name == "Custom")
        if theme_name != "Custom":
            self.theme_changed.emit(theme_name.lower())

    def load_custom_theme_file(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Select Stylesheet", "", "QSS Files (*.qss)")
        if file_path:
            self.custom_theme_path_selected.emit(file_path)
            
    def set_initial_values(self, js_enabled, adblock_enabled, homepage, current_theme):
        self.js_checkbox.setChecked(js_enabled)
        self.adblock_checkbox.setChecked(adblock_enabled)
        self.homepage_edit.setText(homepage)
        self.theme_combo.setCurrentText(current_theme.capitalize())

class DownloadItemWidget(QWidget):
    def __init__(self, download_item: QWebEngineDownloadRequest):
        super().__init__()
        self.download_item = download_item
        layout = QVBoxLayout(self); layout.setContentsMargins(5, 5, 5, 5)
        self.filename_label = QLabel(download_item.suggestedFileName()); self.filename_label.setWordWrap(True)
        self.progress_bar = QProgressBar(); self.status_label = QLabel("Initializing...")
        layout.addWidget(self.filename_label); layout.addWidget(self.progress_bar); layout.addWidget(self.status_label)
        download_item.receivedBytesChanged.connect(self.update_progress)
        download_item.stateChanged.connect(self.update_state)

    def format_bytes(self, size):
        if size < 1024: return f"{size} B"
        elif size < 1024**2: return f"{size/1024:.2f} KB"
        elif size < 1024**3: return f"{size/1024**2:.2f} MB"
        else: return f"{size/1024**3:.2f} GB"

    def update_progress(self):
        received = self.download_item.receivedBytes(); total = self.download_item.totalBytes()
        if total > 0:
            progress = int((received / total) * 100); self.progress_bar.setValue(progress)
            self.status_label.setText(f"{self.format_bytes(received)} / {self.format_bytes(total)}")
        else: self.status_label.setText(f"{self.format_bytes(received)}")

    def update_state(self):
        state = self.download_item.state()
        if state == QWebEngineDownloadRequest.State.DownloadCompleted:
            self.progress_bar.setValue(100); self.status_label.setText("Completed")
        elif state == QWebEngineDownloadRequest.State.DownloadCancelled: self.status_label.setText("Cancelled")
        elif state == QWebEngineDownloadRequest.State.DownloadInterrupted: self.status_label.setText(f"Failed: {self.download_item.interruptReasonString()}")

class Browser(QMainWindow):
    critical_error_signal = Signal(str)

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Borgor Browser")
        self.setGeometry(100, 100, 1200, 800)

        self.bookmarks = []
        self.current_theme_name = "light"
        self.javascript_enabled = True
        self.adblock_enabled = False
        self.homepage_url = "https://www.google.com"
        self.settings_dialog = None
        self.ad_block_interceptor = AdBlockInterceptor()
        
        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=4)
        self.critical_error_signal.connect(self.critical_error)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        self.layout = QVBoxLayout(central_widget); self.layout.setContentsMargins(0, 0, 0, 0); self.layout.setSpacing(0)

        self.tabs = QTabWidget(); self.tabs.setTabsClosable(True); self.tabs.setDocumentMode(True)
        self.tabs.tabCloseRequested.connect(self.close_tab)
        self.tabs.currentChanged.connect(self.update_address_bar)
        self.layout.addWidget(self.tabs)

        self.nav_bar = QToolBar("Navigation"); self.nav_bar.setMovable(False); self.addToolBar(self.nav_bar)

        self.back_action = QAction("Back", self); self.forward_action = QAction("Forward", self)
        self.reload_action = QAction("Reload", self); self.new_tab_action = QAction("New Tab", self)
        self.nav_bar.addAction(self.back_action); self.nav_bar.addAction(self.forward_action)
        self.nav_bar.addAction(self.reload_action); self.nav_bar.addAction(self.new_tab_action)
        self.back_action.triggered.connect(self.back); self.forward_action.triggered.connect(self.forward)
        self.reload_action.triggered.connect(self.reload); self.new_tab_action.triggered.connect(lambda: self.add_new_tab())
        
        self.address_bar = QLineEdit(); self.address_bar.returnPressed.connect(self.navigate_to_url)
        self.nav_bar.addWidget(self.address_bar)
        
        self.progress_bar = QProgressBar(); self.layout.addWidget(self.progress_bar); self.progress_bar.hide()
        
        self.setup_menus()
        self.setup_download_manager()
        self.apply_theme("light")
        self.add_new_tab()

        QWebEngineProfile.defaultProfile().downloadRequested.connect(self.on_download_requested)

    def setup_menus(self):
        self.menu_bar = self.menuBar()
        file_menu = self.menu_bar.addMenu("&File")
        self.load_bookmarks_action = QAction("Load Bookmarks", self)
        self.save_bookmarks_action = QAction("Save Bookmarks", self)
        self.exit_action = QAction("Exit", self)
        file_menu.addAction(self.load_bookmarks_action); file_menu.addAction(self.save_bookmarks_action)
        file_menu.addSeparator(); file_menu.addAction(self.exit_action)
        self.load_bookmarks_action.triggered.connect(self.load_bookmarks)
        self.save_bookmarks_action.triggered.connect(self.save_bookmarks)
        self.exit_action.triggered.connect(self.close)

        tools_menu = self.menu_bar.addMenu("&Tools")
        settings_action = QAction("Settings...", self); tools_menu.addAction(settings_action)
        settings_action.triggered.connect(self.show_settings_dialog)

        self.bookmark_menu = self.menu_bar.addMenu("&Bookmarks")
        self.bookmark_page_action = QAction("Bookmark This Page", self)
        self.bookmark_menu.addAction(self.bookmark_page_action); self.bookmark_menu.addSeparator()
        self.bookmark_menu.aboutToShow.connect(self.update_bookmark_menu)
        self.bookmark_page_action.triggered.connect(self.add_bookmark)

    def show_settings_dialog(self):
        if not self.settings_dialog:
            self.settings_dialog = SettingsDialog(self)
            self.settings_dialog.javascript_toggled.connect(self.set_javascript_enabled)
            self.settings_dialog.adblock_toggled.connect(self.set_adblock_enabled)
            self.settings_dialog.homepage_changed.connect(self.set_homepage)
            self.settings_dialog.clear_data_requested.connect(self.clear_Browse_data)
            self.settings_dialog.theme_changed.connect(self.apply_theme)
            self.settings_dialog.custom_theme_path_selected.connect(self.apply_custom_theme)
        
        self.settings_dialog.set_initial_values(self.javascript_enabled, self.adblock_enabled, self.homepage_url, self.current_theme_name)
        self.settings_dialog.show(); self.settings_dialog.raise_(); self.settings_dialog.activateWindow()

    def set_javascript_enabled(self, enabled):
        self.javascript_enabled = enabled
        for i in range(self.tabs.count()):
            if browser := self.tabs.widget(i):
                browser.settings().setAttribute(QWebEngineSettings.WebAttribute.JavascriptEnabled, enabled)

    def set_adblock_enabled(self, enabled):
        self.adblock_enabled = enabled
        interceptor = self.ad_block_interceptor if enabled else None
        QWebEngineProfile.defaultProfile().setUrlRequestInterceptor(interceptor)

    def set_homepage(self, url):
        self.homepage_url = url

    def clear_Browse_data(self):
        profile = QWebEngineProfile.defaultProfile()
        profile.clearHttpCache()
        profile.cookieStore().deleteAllCookies()
        QMessageBox.information(self, "Data Cleared", "Browse cache and cookies have been cleared.")

    def apply_custom_theme(self, file_path):
        try:
            with open(file_path, 'r') as f: self.setStyleSheet(f.read())
            self.current_theme_name = "custom"
        except Exception as e:
            self.critical_error(f"Could not load theme: {e}")

    def setup_download_manager(self):
        self.download_dock = QDockWidget("Downloads", self)
        self.download_dock.setAllowedAreas(Qt.DockWidgetArea.BottomDockWidgetArea)
        self.download_list = QListWidget()
        self.download_dock.setWidget(self.download_list)
        self.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, self.download_dock)
        self.download_dock.hide()

    def on_download_requested(self, download_item: QWebEngineDownloadRequest):
        save_path, _ = QFileDialog.getSaveFileName(self, "Save File", download_item.suggestedFileName())
        if save_path:
            download_item.setPath(save_path); download_item.accept()
            item_widget = DownloadItemWidget(download_item)
            list_item = QListWidgetItem(); list_item.setSizeHint(item_widget.sizeHint())
            self.download_list.addItem(list_item)
            self.download_list.setItemWidget(list_item, item_widget)
            self.download_dock.show()
        
    def setup_icons(self):
        self.back_action.setIcon(QIcon.fromTheme("go-previous")); self.forward_action.setIcon(QIcon.fromTheme("go-next"))
        self.reload_action.setIcon(QIcon.fromTheme("view-refresh")); self.new_tab_action.setIcon(QIcon.fromTheme("document-new"))
        self.load_bookmarks_action.setIcon(QIcon.fromTheme("document-open")); self.save_bookmarks_action.setIcon(QIcon.fromTheme("document-save"))
        self.exit_action.setIcon(QIcon.fromTheme("application-exit")); self.bookmark_page_action.setIcon(QIcon.fromTheme("user-bookmarks"))

    def apply_theme(self, theme_name):
        self.current_theme_name = theme_name
        is_dark_mode = theme_name == "dark"
        if is_dark_mode:
            self.setStyleSheet(DARK_MODE_QSS); QIcon.setThemeName("breeze-dark")
        else:
            self.setStyleSheet(LIGHT_MODE_QSS); QIcon.setThemeName("breeze")
        self.setup_icons()

    def add_new_tab(self, url=None, label="New Tab"):
        if url is None: url = self.homepage_url
        browser = QWebEngineView()
        browser.settings().setAttribute(QWebEngineSettings.WebAttribute.JavascriptEnabled, self.javascript_enabled)
        browser.setUrl(QUrl(url)); index = self.tabs.addTab(browser, label); self.tabs.setCurrentIndex(index)
        browser.urlChanged.connect(lambda q, b=browser: self.update_address_bar_on_change(q, b))
        browser.titleChanged.connect(lambda t, i=index: self.tabs.setTabText(i, t))
        browser.loadStarted.connect(self.on_load_started); browser.loadProgress.connect(self.on_load_progress)
        browser.loadFinished.connect(self.on_load_finished)

    def close_tab(self, index):
        if self.tabs.count() > 1: self.tabs.removeTab(index)
        else: self.close()

    def current_browser(self): return self.tabs.currentWidget()
    def back(self):
        if b := self.current_browser(): b.back()
    def forward(self):
        if b := self.current_browser(): b.forward()
    def reload(self):
        if b := self.current_browser(): b.reload()

    def navigate_to_url(self):
        url = self.address_bar.text().strip()
        if not url: return
        if not url.startswith(("http://", "https://")): url = "https://" + url
        if b := self.current_browser(): b.setUrl(QUrl(url))

    def update_address_bar_on_change(self, qurl, browser):
        if browser == self.current_browser():
            self.address_bar.setText(qurl.toString()); self.address_bar.setCursorPosition(0)
    def update_address_bar(self):
        if b := self.current_browser(): self.update_address_bar_on_change(b.url(), b)

    def add_bookmark(self):
        if b := self.current_browser():
            url = b.url().toString(); title = b.title()
            if (url, title) not in self.bookmarks: self.bookmarks.append((url, title))

    def update_bookmark_menu(self):
        for action in self.bookmark_menu.actions()[2:]: self.bookmark_menu.removeAction(action)
        for url, title in self.bookmarks:
            action = QAction(title, self); action.setData(url)
            action.triggered.connect(self.navigate_bookmark); self.bookmark_menu.addAction(action)

    def navigate_bookmark(self):
        if action := self.sender(): self.add_new_tab(url=action.data())
        
    def load_bookmarks(self):
        file_name, _ = QFileDialog.getOpenFileName(self, "Open", "", "JSON (*.json)")
        if file_name: self.executor.submit(self._load_bookmarks_from_file, file_name)

    def _load_bookmarks_from_file(self, file_name):
        try:
            with open(file_name, "r") as f: self.bookmarks = json.load(f)
        except Exception as e: self.critical_error_signal.emit(f"Failed to load: {e}")

    def save_bookmarks(self):
        file_name, _ = QFileDialog.getSaveFileName(self, "Save", "", "JSON (*.json)")
        if file_name: self.executor.submit(self._save_bookmarks_to_file, file_name)

    def _save_bookmarks_to_file(self, file_name):
        try:
            with open(file_name, "w") as f: json.dump(self.bookmarks, f, indent=4)
        except Exception as e: self.critical_error_signal.emit(f"Failed to save: {e}")

    def on_load_started(self): self.progress_bar.show()
    def on_load_progress(self, progress): self.progress_bar.setValue(progress)
    def on_load_finished(self, success):
        self.progress_bar.hide(); self.progress_bar.setValue(0)
    def critical_error(self, message): QMessageBox.critical(self, "Error", message)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle('Breeze')
    profile = QWebEngineProfile.defaultProfile()
    profile.setHttpCacheType(QWebEngineProfile.HttpCacheType.MemoryHttpCache)
    browser = Browser()
    browser.show()
    sys.exit(app.exec())
