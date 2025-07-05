import sys
import json
import concurrent.futures
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QTabWidget, QVBoxLayout, QWidget, QLineEdit,
    QToolBar, QFileDialog, QMessageBox, QPushButton, QProgressBar, QStyle,
    QLabel, QHBoxLayout, QTabBar, QMenu
)
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWebEngineCore import QWebEngineProfile
from PySide6.QtCore import QUrl, Qt, Signal, QObject
from PySide6.QtGui import QAction, QKeySequence, QIcon

DARK_MODE_QSS = """
    QWidget {
        background-color: #2b2b2b;
        color: #ffffff;
        border: none;
    }
    QMainWindow {
        background-color: #2b2b2b;
    }
    QTabWidget::pane {
        border-top: 1px solid #3c3c3c;
    }
    QTabBar::tab {
        background: #2b2b2b;
        color: #ffffff;
        padding: 8px 20px;
        border-top-left-radius: 4px;
        border-top-right-radius: 4px;
        border: 1px solid #2b2b2b;
        border-bottom: none;
    }
    QTabBar::tab:selected {
        background: #3c3c3c;
        border: 1px solid #3c3c3c;
        border-bottom: none;
    }
    QTabBar::tab:hover {
        background: #4a4a4a;
    }
    QToolBar {
        background-color: #3c3c3c;
        padding: 5px;
        spacing: 5px;
    }
    QToolBar QToolButton, QPushButton {
        background-color: #555555;
        color: #ffffff;
        padding: 8px 12px;
        border-radius: 4px;
    }
    QToolBar QToolButton:hover, QPushButton:hover {
        background-color: #6a6a6a;
    }
    QLineEdit {
        background-color: #3c3c3c;
        color: #ffffff;
        padding: 8px;
        border-radius: 4px;
        border: 1px solid #555555;
    }
    QProgressBar {
        border: none;
        background-color: #3c3c3c;
        height: 3px;
    }
    QProgressBar::chunk {
        background-color: #007acc;
    }
    QMenu {
        background-color: #3c3c3c;
        color: #ffffff;
        border: 1px solid #555;
    }
    QMenu::item:selected {
        background-color: #007acc;
    }
"""

LIGHT_MODE_QSS = """
    QWidget {
        background-color: #f0f0f0;
        color: #000000;
        border: none;
    }
    QMainWindow {
        background-color: #f0f0f0;
    }
    QTabWidget::pane {
        border-top: 1px solid #dcdcdc;
    }
    QTabBar::tab {
        background: #f0f0f0;
        color: #000000;
        padding: 8px 20px;
        border-top-left-radius: 4px;
        border-top-right-radius: 4px;
        border: 1px solid #f0f0f0;
        border-bottom: none;
    }
    QTabBar::tab:selected {
        background: #ffffff;
        border: 1px solid #dcdcdc;
        border-bottom-color: #ffffff;
    }
    QTabBar::tab:hover {
        background: #e6e6e6;
    }
    QToolBar {
        background-color: #ffffff;
        padding: 5px;
        spacing: 5px;
        border-bottom: 1px solid #dcdcdc;
    }
    QToolBar QToolButton, QPushButton {
        background-color: #e0e0e0;
        color: #000000;
        padding: 8px 12px;
        border-radius: 4px;
    }
    QToolBar QToolButton:hover, QPushButton:hover {
        background-color: #d0d0d0;
    }
    QLineEdit {
        background-color: #ffffff;
        color: #000000;
        padding: 8px;
        border-radius: 4px;
        border: 1px solid #dcdcdc;
    }
    QProgressBar {
        border: none;
        background-color: #f0f0f0;
        height: 3px;
    }
    QProgressBar::chunk {
        background-color: #0078d7;
    }
    QMenu {
        background-color: #ffffff;
        color: #000000;
        border: 1px solid #dcdcdc;
    }
    QMenu::item:selected {
        background-color: #0078d7;
        color: #ffffff;
    }
"""

class Browser(QMainWindow):
    critical_error_signal = Signal(str)

    def __init__(self):
        super().__init__()

        self.setWindowTitle("Dandified Borgor Browser")
        self.setGeometry(100, 100, 1200, 800)

        self.bookmarks = []
        self.is_dark_mode = False
        self.is_fullscreen = False

        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=4)
        self.critical_error_signal.connect(self.critical_error)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        self.layout = QVBoxLayout(central_widget)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)

        self.tabs = QTabWidget()
        self.tabs.setTabsClosable(True)
        self.tabs.setDocumentMode(True)
        self.tabs.tabCloseRequested.connect(self.close_tab)
        self.tabs.currentChanged.connect(self.update_address_bar)
        self.layout.addWidget(self.tabs)

        self.nav_bar = QToolBar("Navigation")
        self.nav_bar.setMovable(False)
        self.addToolBar(self.nav_bar)

        self.back_action = QAction("Back", self)
        self.back_action.setStatusTip("Back to previous page")
        self.back_action.setShortcut(QKeySequence(QKeySequence.StandardKey.Back))
        self.back_action.triggered.connect(self.back)
        self.nav_bar.addAction(self.back_action)

        self.forward_action = QAction("Forward", self)
        self.forward_action.setStatusTip("Forward to next page")
        self.forward_action.setShortcut(QKeySequence(QKeySequence.StandardKey.Forward))
        self.forward_action.triggered.connect(self.forward)
        self.nav_bar.addAction(self.forward_action)

        self.reload_action = QAction("Reload", self)
        self.reload_action.setStatusTip("Reload page")
        self.reload_action.setShortcut(QKeySequence(QKeySequence.StandardKey.Refresh))
        self.reload_action.triggered.connect(self.reload)
        self.nav_bar.addAction(self.reload_action)

        self.new_tab_action = QAction("New Tab", self)
        self.new_tab_action.setStatusTip("Open a new tab")
        self.new_tab_action.setShortcut(QKeySequence(QKeySequence.StandardKey.New))
        self.new_tab_action.triggered.connect(lambda: self.add_new_tab())
        self.nav_bar.addAction(self.new_tab_action)

        self.address_bar = QLineEdit()
        self.address_bar.returnPressed.connect(self.navigate_to_url)
        self.nav_bar.addWidget(self.address_bar)
        
        self.progress_bar = QProgressBar()
        self.layout.addWidget(self.progress_bar)
        self.progress_bar.hide()
        
        self.menu_bar = self.menuBar()
        file_menu = self.menu_bar.addMenu("&File")

        self.load_bookmarks_action = QAction("Load Bookmarks", self)
        self.load_bookmarks_action.triggered.connect(self.load_bookmarks)
        file_menu.addAction(self.load_bookmarks_action)

        self.save_bookmarks_action = QAction("Save Bookmarks", self)
        self.save_bookmarks_action.triggered.connect(self.save_bookmarks)
        file_menu.addAction(self.save_bookmarks_action)
        
        file_menu.addSeparator()
        
        self.mode_toggle_action = QAction("Switch to Dark Mode", self)
        self.mode_toggle_action.triggered.connect(self.toggle_dark_mode)
        file_menu.addAction(self.mode_toggle_action)

        self.fullscreen_action = QAction("Toggle Fullscreen", self)
        self.fullscreen_action.setShortcut(QKeySequence(Qt.Key.Key_F11))
        self.fullscreen_action.triggered.connect(self.toggle_fullscreen)
        file_menu.addAction(self.fullscreen_action)
        
        file_menu.addSeparator()

        self.exit_action = QAction("Exit", self)
        self.exit_action.setShortcut(QKeySequence(QKeySequence.StandardKey.Quit))
        self.exit_action.triggered.connect(self.close)
        file_menu.addAction(self.exit_action)

        self.bookmark_menu = self.menu_bar.addMenu("&Bookmarks")
        self.bookmark_menu.aboutToShow.connect(self.update_bookmark_menu)

        self.bookmark_page_action = QAction("Bookmark This Page", self)
        self.bookmark_page_action.setShortcut(QKeySequence("Ctrl+D"))
        self.bookmark_page_action.triggered.connect(self.add_bookmark)
        self.bookmark_menu.addAction(self.bookmark_page_action)
        self.bookmark_menu.addSeparator()
        
        self.apply_theme(self.is_dark_mode)
        self.add_new_tab(url="https://www.google.com")

    def setup_icons(self):
        self.back_action.setIcon(QIcon.fromTheme("go-previous"))
        self.forward_action.setIcon(QIcon.fromTheme("go-next"))
        self.reload_action.setIcon(QIcon.fromTheme("view-refresh"))
        self.new_tab_action.setIcon(QIcon.fromTheme("document-new"))
        self.load_bookmarks_action.setIcon(QIcon.fromTheme("document-open"))
        self.save_bookmarks_action.setIcon(QIcon.fromTheme("document-save"))
        self.fullscreen_action.setIcon(QIcon.fromTheme("view-fullscreen"))
        self.exit_action.setIcon(QIcon.fromTheme("application-exit"))
        self.bookmark_page_action.setIcon(QIcon.fromTheme("user-bookmarks"))

    def apply_theme(self, dark=False):
        self.is_dark_mode = dark
        if dark:
            self.setStyleSheet(DARK_MODE_QSS)
            QIcon.setThemeName("breeze-dark")
            self.mode_toggle_action.setText("Switch to Light Mode")
        else:
            self.setStyleSheet(LIGHT_MODE_QSS)
            QIcon.setThemeName("breeze")
            self.mode_toggle_action.setText("Switch to Dark Mode")
        
        self.setup_icons()

    def toggle_dark_mode(self):
        self.apply_theme(not self.is_dark_mode)

    def toggle_fullscreen(self):
        if self.is_fullscreen:
            self.showNormal()
        else:
            self.showFullScreen()
        self.is_fullscreen = not self.is_fullscreen

    def add_new_tab(self, url="https://www.google.com", label="New Tab"):
        browser = QWebEngineView()
        browser.setUrl(QUrl(url))

        index = self.tabs.addTab(browser, label)
        self.tabs.setCurrentIndex(index)

        browser.urlChanged.connect(lambda q, b=browser: self.update_address_bar_on_change(q, b))
        browser.titleChanged.connect(lambda t, i=index: self.tabs.setTabText(i, t))
        browser.loadStarted.connect(self.on_load_started)
        browser.loadProgress.connect(self.on_load_progress)
        browser.loadFinished.connect(self.on_load_finished)

    def close_tab(self, index):
        if self.tabs.count() > 1:
            self.tabs.removeTab(index)
        else:
            self.close()

    def current_browser(self):
        return self.tabs.currentWidget()

    def back(self):
        browser = self.current_browser()
        if browser:
            browser.back()

    def forward(self):
        browser = self.current_browser()
        if browser:
            browser.forward()

    def reload(self):
        browser = self.current_browser()
        if browser:
            browser.reload()

    def navigate_to_url(self):
        url = self.address_bar.text().strip()
        if not url:
            return
            
        if not url.startswith("http://") and not url.startswith("https://"):
            url = "https://" + url
            
        browser = self.current_browser()
        if browser:
            browser.setUrl(QUrl(url))

    def update_address_bar_on_change(self, qurl, browser):
        if browser == self.current_browser():
            self.address_bar.setText(qurl.toString())
            self.address_bar.setCursorPosition(0)

    def update_address_bar(self):
        browser = self.current_browser()
        if browser:
            self.update_address_bar_on_change(browser.url(), browser)

    def add_bookmark(self):
        browser = self.current_browser()
        if browser:
            url = browser.url().toString()
            title = browser.title()
            if (url, title) not in self.bookmarks:
                self.bookmarks.append((url, title))

    def update_bookmark_menu(self):
        for action in self.bookmark_menu.actions()[2:]:
            self.bookmark_menu.removeAction(action)
            
        for url, title in self.bookmarks:
            action = QAction(title, self)
            action.setData(url)
            action.triggered.connect(self.navigate_bookmark)
            self.bookmark_menu.addAction(action)

    def navigate_bookmark(self):
        action = self.sender()
        url = action.data()
        self.add_new_tab(url=url)
        
    def load_bookmarks(self):
        file_name, _ = QFileDialog.getOpenFileName(self, "Open Bookmark File", "", "JSON Files (*.json)")
        if file_name:
            self.executor.submit(self._load_bookmarks_from_file, file_name)

    def _load_bookmarks_from_file(self, file_name):
        try:
            with open(file_name, "r") as file:
                self.bookmarks = json.load(file)
        except Exception as e:
            self.critical_error_signal.emit(f"Failed to load bookmarks: {e}")

    def save_bookmarks(self):
        file_name, _ = QFileDialog.getSaveFileName(self, "Save Bookmark File", "", "JSON Files (*.json)")
        if file_name:
            self.executor.submit(self._save_bookmarks_to_file, file_name)

    def _save_bookmarks_to_file(self, file_name):
        try:
            with open(file_name, "w") as file:
                json.dump(self.bookmarks, file, indent=4)
        except Exception as e:
            self.critical_error_signal.emit(f"Failed to save bookmarks: {e}")

    def on_load_started(self):
        self.progress_bar.setValue(0)
        self.progress_bar.show()

    def on_load_progress(self, progress):
        self.progress_bar.setValue(progress)

    def on_load_finished(self, success):
        self.progress_bar.hide()
        if not success:
            self.progress_bar.setValue(0)

    def critical_error(self, message):
        QMessageBox.critical(self, "Error", message)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    profile = QWebEngineProfile.defaultProfile()
    profile.setHttpCacheType(QWebEngineProfile.HttpCacheType.MemoryHttpCache)
    profile.setHttpCacheMaximumSize(100 * 1024 * 1024)

    browser = Browser()
    browser.show()
    sys.exit(app.exec())
