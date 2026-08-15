import sys
import os
import time

from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer, QPoint, QPropertyAnimation, QEasingCurve, QRectF, pyqtProperty
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QSlider, QLineEdit, QListWidget, QListWidgetItem,
    QFrame, QGraphicsDropShadowEffect, QSystemTrayIcon, QMenu, QSizePolicy
)
from PyQt6.QtGui import (
    QIcon, QFont, QColor, QPalette, QAction, QPixmap, QPainter, QBrush,
    QPen, QLinearGradient, QRadialGradient, QPainterPath
)

from audio_monitor import AudioMonitor
from spotify_control import SpotifyController


class AudioWorker(QThread):
    audio_update = pyqtSignal(float, list) # max_peak, active_sources
    status_change = pyqtSignal(str, str, str) # title, detail, state ('playing', 'paused', 'monitoring', 'disabled')

    def __init__(self, threshold=0.02, silence_delay=1.5, ignore_apps=None, controller=None):
        super().__init__()
        self.threshold = threshold
        self.silence_delay = silence_delay
        self.ignore_apps = ignore_apps or ['spotify.exe']
        self.controller = controller or SpotifyController()
        self.monitor = AudioMonitor(threshold=self.threshold, ignore_apps=self.ignore_apps)

        self.running = True
        self.enabled = True
        self.spotify_was_paused_by_us = False
        self.last_audio_time = 0

    def update_settings(self, threshold, silence_delay, ignore_apps):
        self.threshold = threshold
        self.silence_delay = silence_delay
        self.ignore_apps = ignore_apps
        self.monitor.threshold = threshold
        self.monitor.set_ignore_apps(ignore_apps)

    def set_enabled(self, enabled):
        self.enabled = enabled
        if not enabled and self.spotify_was_paused_by_us:
            self.controller.play()
            self.spotify_was_paused_by_us = False
            self.status_change.emit("Monitoring Disabled", "Auto-pause feature turned off", "disabled")

    def run(self):
        while self.running:
            if not self.enabled:
                time.sleep(0.2)
                continue

            max_peak, active_sources = self.monitor.get_other_audio_sessions()
            self.audio_update.emit(max_peak, active_sources)

            current_time = time.time()

            if len(active_sources) > 0 or max_peak >= self.threshold:
                self.last_audio_time = current_time
                if not self.spotify_was_paused_by_us:
                    sources_str = ", ".join([s['name'] for s in active_sources]) if active_sources else "Other Audio Source"
                    self.status_change.emit("Spotify Paused", f"Detected sound from {sources_str}", "paused")
                    self.controller.pause()
                    self.spotify_was_paused_by_us = True
            else:
                if self.spotify_was_paused_by_us:
                    time_since_silence = current_time - self.last_audio_time
                    remaining_delay = max(0.0, self.silence_delay - time_since_silence)
                    
                    if remaining_delay > 0:
                        self.status_change.emit("Silence Detected", f"Resuming Spotify in {remaining_delay:.1f}s...", "paused")
                    else:
                        self.status_change.emit("Spotify Playing", "Audio stopped. Music resumed automatically.", "playing")
                        self.controller.play()
                        self.spotify_was_paused_by_us = False
                else:
                    self.status_change.emit("Listening for Sounds", "Spotify is active. Standing by...", "monitoring")

            time.sleep(0.05)

    def stop(self):
        self.running = False
        self.wait()


class CustomToggleSwitch(QWidget):
    toggled = pyqtSignal(bool)

    def __init__(self, active=True, parent=None):
        super().__init__(parent)
        self.setFixedSize(54, 28)
        self._active = active
        self._position = 28.0 if active else 4.0

        self.anim = QPropertyAnimation(self, b"position", self)
        self.anim.setDuration(200)
        self.anim.setEasingCurve(QEasingCurve.Type.InOutCubic)

    def isChecked(self):
        return self._active

    def setChecked(self, checked):
        if self._active != checked:
            self._active = checked
            self.anim.stop()
            self.anim.setStartValue(self._position)
            self.anim.setEndValue(28.0 if checked else 4.0)
            self.anim.start()
            self.toggled.emit(checked)
            self.update()

    def get_position(self):
        return self._position

    def set_position(self, pos):
        self._position = pos
        self.update()

    position = pyqtProperty(float, get_position, set_position)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.setChecked(not self._active)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Track background
        track_color = QColor("#1DB954") if self._active else QColor("#3E3E42")
        painter.setBrush(QBrush(track_color))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(0, 0, 54, 28, 14, 14)

        # Thumb
        painter.setBrush(QBrush(QColor("#FFFFFF")))
        painter.drawEllipse(int(self._position), 4, 20, 20)


class CustomAudioVisualizer(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(36)
        self._level = 0.0
        self._is_triggered = False

    def set_level(self, level, triggered):
        self._level = level
        self._is_triggered = triggered
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Background slot
        rect = QRectF(0, 8, self.width(), 20)
        painter.setBrush(QBrush(QColor("#1A1A22")))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(rect, 10, 10)

        # Level fill
        fill_width = max(0.0, min(self.width(), self.width() * self._level))
        if fill_width > 0:
            fill_rect = QRectF(0, 8, fill_width, 20)
            gradient = QLinearGradient(0, 0, self.width(), 0)
            if self._is_triggered:
                gradient.setColorAt(0.0, QColor("#FF5E62"))
                gradient.setColorAt(1.0, QColor("#FF9966"))
            else:
                gradient.setColorAt(0.0, QColor("#1DB954"))
                gradient.setColorAt(1.0, QColor("#1ED760"))
            
            painter.setBrush(QBrush(gradient))
            painter.drawRoundedRect(fill_rect, 10, 10)


class ModernMainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.resize(520, 620)

        self.threshold = 0.02
        self.silence_delay = 1.5
        self.ignore_apps = ['spotify.exe']
        self.controller = SpotifyController()

        self._drag_pos = QPoint()

        self.init_ui()
        self.init_tray()

        # Start Audio Worker Thread
        self.worker = AudioWorker(
            threshold=self.threshold,
            silence_delay=self.silence_delay,
            ignore_apps=self.ignore_apps,
            controller=self.controller
        )
        self.worker.audio_update.connect(self.on_audio_update)
        self.worker.status_change.connect(self.on_status_change)
        self.worker.start()

    def init_ui(self):
        # Outer container for rounded window with soft shadow
        self.container = QFrame(self)
        self.container.setObjectName("CentralContainer")
        self.setCentralWidget(self.container)

        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(25)
        shadow.setColor(QColor(0, 0, 0, 160))
        shadow.setOffset(0, 6)
        self.container.setGraphicsEffect(shadow)

        self.container.setStyleSheet("""
            QFrame#CentralContainer {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #181920, stop:1 #111216);
                border-radius: 16px;
                border: 1px solid rgba(255, 255, 255, 0.08);
            }
            QLabel {
                color: #F0F0F5;
                font-family: 'Inter', 'Segoe UI', sans-serif;
                border: none;
                background: transparent;
            }
            QFrame.Card {
                background-color: rgba(255, 255, 255, 0.04);
                border: 1px solid rgba(255, 255, 255, 0.06);
                border-radius: 14px;
            }
            QSlider {
                border: none;
                background: transparent;
            }
            QSlider::groove:horizontal {
                height: 6px;
                background: rgba(255, 255, 255, 0.1);
                border-radius: 3px;
                border: none;
            }
            QSlider::handle:horizontal {
                background: #1DB954;
                width: 16px;
                height: 16px;
                margin: -5px 0;
                border-radius: 8px;
                border: none;
            }
            QSlider::handle:horizontal:hover {
                background: #1ED760;
            }
            QLineEdit {
                background-color: rgba(0, 0, 0, 0.3);
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 10px;
                padding: 8px 12px;
                color: #FFFFFF;
                font-size: 13px;
            }
            QLineEdit:focus {
                border: 1px solid #1DB954;
            }
            QPushButton.PrimaryBtn {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #1DB954, stop:1 #1ED760);
                color: #FFFFFF;
                border: none;
                border-radius: 10px;
                padding: 8px 16px;
                font-weight: bold;
                font-size: 13px;
            }
            QPushButton.PrimaryBtn:hover {
                background: #20e367;
            }
            QPushButton.SecondaryBtn {
                background-color: rgba(255, 255, 255, 0.06);
                color: #DDDDDD;
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 10px;
                padding: 6px 12px;
                font-size: 12px;
            }
            QPushButton.SecondaryBtn:hover {
                background-color: rgba(255, 255, 255, 0.12);
                color: #FFFFFF;
            }
            QListWidget {
                background-color: rgba(0, 0, 0, 0.25);
                border: 1px solid rgba(255, 255, 255, 0.06);
                border-radius: 10px;
                padding: 4px;
                color: #E0E0E0;
            }
            QListWidget::item {
                padding: 6px 10px;
                border-radius: 6px;
                border: none;
            }
            QListWidget::item:selected {
                background-color: rgba(29, 185, 84, 0.25);
                color: #1DB954;
            }
        """)

        main_layout = QVBoxLayout(self.container)
        main_layout.setContentsMargins(20, 16, 20, 20)
        main_layout.setSpacing(14)

        # Window Titlebar / Header
        titlebar = QHBoxLayout()
        
        # App Icon + Title
        brand_layout = QHBoxLayout()
        logo_dot = QLabel()
        logo_dot.setFixedSize(12, 12)
        logo_dot.setStyleSheet("background-color: #1DB954; border-radius: 6px;")
        brand_layout.addWidget(logo_dot)

        title_text = QLabel("Spause")
        title_text.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
        brand_layout.addWidget(title_text)
        titlebar.addLayout(brand_layout)


        titlebar.addStretch()

        # Window Controls (Minimize / Close)
        min_btn = QPushButton("—")
        min_btn.setFixedSize(28, 28)
        min_btn.setStyleSheet("""
            QPushButton {
                background: transparent; color: #999; border: none; font-size: 14px;
            }
            QPushButton:hover { color: #FFF; background: rgba(255,255,255,0.1); border-radius: 14px; }
        """)
        min_btn.clicked.connect(self.showMinimized)
        titlebar.addWidget(min_btn)

        close_btn = QPushButton("✕")
        close_btn.setFixedSize(28, 28)
        close_btn.setStyleSheet("""
            QPushButton {
                background: transparent; color: #999; border: none; font-size: 13px;
            }
            QPushButton:hover { color: #FFF; background: #FF4D4D; border-radius: 14px; }
        """)
        close_btn.clicked.connect(self.hide_to_tray)
        titlebar.addWidget(close_btn)

        main_layout.addLayout(titlebar)

        # Status & Toggle Header Card
        status_card = QFrame()
        status_card.setProperty("class", "Card")
        status_card_layout = QHBoxLayout(status_card)
        status_card_layout.setContentsMargins(18, 16, 18, 16)

        status_info_v = QVBoxLayout()
        self.status_title = QLabel("Listening for External Sounds")
        self.status_title.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        self.status_title.setStyleSheet("color: #1DB954;")
        
        self.status_subtitle = QLabel("Spotify playback automatically managed")
        self.status_subtitle.setStyleSheet("color: #8E8E93; font-size: 11px;")
        status_info_v.addWidget(self.status_title)
        status_info_v.addWidget(self.status_subtitle)

        status_card_layout.addLayout(status_info_v)
        status_card_layout.addStretch()

        self.toggle = CustomToggleSwitch(active=True)
        self.toggle.toggled.connect(self.on_toggle_changed)
        status_card_layout.addWidget(self.toggle)

        main_layout.addWidget(status_card)

        # Live Sound Visualizer & Active Apps Card
        meter_card = QFrame()
        meter_card.setProperty("class", "Card")
        meter_card_layout = QVBoxLayout(meter_card)
        meter_card_layout.setContentsMargins(18, 14, 18, 16)

        meter_header = QHBoxLayout()
        meter_title = QLabel("Live System Audio Level")
        meter_title.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        meter_header.addWidget(meter_title)
        meter_header.addStretch()

        self.level_val_text = QLabel("0%")
        self.level_val_text.setStyleSheet("color: #8E8E93; font-size: 12px; font-weight: bold;")
        meter_header.addWidget(self.level_val_text)
        meter_card_layout.addLayout(meter_header)

        self.visualizer = CustomAudioVisualizer()
        meter_card_layout.addWidget(self.visualizer)

        self.active_sources_label = QLabel("Active Sound App: None")
        self.active_sources_label.setStyleSheet("color: #7C7C82; font-size: 11px;")
        meter_card_layout.addWidget(self.active_sources_label)

        main_layout.addWidget(meter_card)

        # Controls & Settings Card
        settings_card = QFrame()
        settings_card.setProperty("class", "Card")
        settings_layout = QVBoxLayout(settings_card)
        settings_layout.setContentsMargins(18, 14, 18, 16)
        settings_layout.setSpacing(12)

        set_title = QLabel("Sensitivity & Timing Settings")
        set_title.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        settings_layout.addWidget(set_title)

        # Threshold Slider Row
        thresh_row = QHBoxLayout()
        thresh_label = QLabel("Detection Sensitivity")
        thresh_label.setStyleSheet("font-size: 12px; color: #CCCCCC;")
        thresh_row.addWidget(thresh_label)
        thresh_row.addStretch()

        self.thresh_val_label = QLabel("2%")
        self.thresh_val_label.setStyleSheet("color: #1DB954; font-weight: bold; font-size: 12px;")
        thresh_row.addWidget(self.thresh_val_label)
        settings_layout.addLayout(thresh_row)

        self.thresh_slider = QSlider(Qt.Orientation.Horizontal)
        self.thresh_slider.setRange(1, 20)
        self.thresh_slider.setValue(2)
        self.thresh_slider.valueChanged.connect(self.on_settings_changed)
        settings_layout.addWidget(self.thresh_slider)

        # Delay Slider Row
        delay_row = QHBoxLayout()
        delay_label = QLabel("Resume Delay Buffer")
        delay_label.setStyleSheet("font-size: 12px; color: #CCCCCC;")
        delay_row.addWidget(delay_label)
        delay_row.addStretch()

        self.delay_val_label = QLabel("1.5s")
        self.delay_val_label.setStyleSheet("color: #1DB954; font-weight: bold; font-size: 12px;")
        delay_row.addWidget(self.delay_val_label)
        settings_layout.addLayout(delay_row)

        self.delay_slider = QSlider(Qt.Orientation.Horizontal)
        self.delay_slider.setRange(5, 50)
        self.delay_slider.setValue(15)
        self.delay_slider.valueChanged.connect(self.on_settings_changed)
        settings_layout.addWidget(self.delay_slider)

        main_layout.addWidget(settings_card)

        # App Exclusion Whitelist Card
        ignore_card = QFrame()
        ignore_card.setProperty("class", "Card")
        ignore_card_layout = QVBoxLayout(ignore_card)
        ignore_card_layout.setContentsMargins(18, 14, 18, 16)
        ignore_card_layout.setSpacing(10)

        ignore_title = QLabel("App Exclusion Whitelist")
        ignore_title.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        ignore_card_layout.addWidget(ignore_title)

        input_row = QHBoxLayout()
        self.ignore_input = QLineEdit()
        self.ignore_input.setPlaceholderText("Ignore process name (e.g. discord.exe)")
        add_btn = QPushButton("Add App")
        add_btn.setProperty("class", "PrimaryBtn")
        add_btn.clicked.connect(self.add_ignored_app)
        input_row.addWidget(self.ignore_input)
        input_row.addWidget(add_btn)
        ignore_card_layout.addLayout(input_row)

        self.ignore_list = QListWidget()
        self.ignore_list.setFixedHeight(68)
        self.refresh_ignore_list()
        ignore_card_layout.addWidget(self.ignore_list)

        remove_btn = QPushButton("Remove Selected App")
        remove_btn.setProperty("class", "SecondaryBtn")
        remove_btn.clicked.connect(self.remove_ignored_app)
        ignore_card_layout.addWidget(remove_btn, alignment=Qt.AlignmentFlag.AlignRight)

        main_layout.addWidget(ignore_card)

    # Window Dragging Logic (Frameless window movement)
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_pos)
            event.accept()

    def init_tray(self):
        pixmap = QPixmap(32, 32)
        pixmap.fill(QColor("#121216"))
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setBrush(QBrush(QColor("#1DB954")))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(6, 6, 20, 20)
        painter.end()

        self.tray_icon = QSystemTrayIcon(QIcon(pixmap), self)
        self.tray_icon.setToolTip("Spotify Audio Duct - Running in Tray")

        tray_menu = QMenu()
        tray_menu.setStyleSheet("""
            QMenu {
                background-color: #181920;
                color: #FFFFFF;
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 8px;
                padding: 4px;
            }
            QMenu::item {
                padding: 6px 16px;
                border-radius: 4px;
            }
            QMenu::item:selected {
                background-color: #1DB954;
            }
        """)

        show_act = QAction("Open Window", self)
        show_act.triggered.connect(self.show_normal)
        tray_menu.addAction(show_act)

        quit_act = QAction("Exit App", self)
        quit_act.triggered.connect(self.close_app)
        tray_menu.addAction(quit_act)

        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.activated.connect(self.on_tray_activated)
        self.tray_icon.show()

    def show_normal(self):
        self.show()
        self.activateWindow()

    def hide_to_tray(self):
        self.hide()
        if self.tray_icon.isVisible():
            self.tray_icon.showMessage(
                "Spotify Audio Duct",
                "App minimized to system tray.",
                QSystemTrayIcon.MessageIcon.Information,
                2000
            )

    def on_tray_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            if self.isVisible():
                self.hide()
            else:
                self.show_normal()

    def close_app(self):
        self.worker.stop()
        QApplication.quit()

    def on_toggle_changed(self, active):
        self.worker.set_enabled(active)

    def on_audio_update(self, max_peak, active_sources):
        val_pct = int(max_peak * 100)
        is_triggered = max_peak >= self.threshold or len(active_sources) > 0

        self.level_val_text.setText(f"{val_pct}%")
        self.visualizer.set_level(max_peak, is_triggered)

        if active_sources:
            names = list(set([s['name'] for s in active_sources]))
            self.active_sources_label.setText(f"Active Sound App: {', '.join(names)}")
        else:
            self.active_sources_label.setText("Active Sound App: None")

    def on_status_change(self, title, detail, state):
        self.status_title.setText(title)
        self.status_subtitle.setText(detail)

        color_map = {
            'playing': '#1DB954',
            'paused': '#FF5E62',
            'monitoring': '#1DB954',
            'disabled': '#8E8E93'
        }
        color = color_map.get(state, '#1DB954')
        self.status_title.setStyleSheet(f"color: {color};")

    def on_settings_changed(self):
        self.threshold = self.thresh_slider.value() / 100.0
        self.silence_delay = self.delay_slider.value() / 10.0

        self.thresh_val_label.setText(f"{int(self.threshold*100)}%")
        self.delay_val_label.setText(f"{self.silence_delay:.1f}s")

        self.worker.update_settings(
            threshold=self.threshold,
            silence_delay=self.silence_delay,
            ignore_apps=self.ignore_apps
        )

    def refresh_ignore_list(self):
        self.ignore_list.clear()
        for app in self.ignore_apps:
            self.ignore_list.addItem(app)

    def add_ignored_app(self):
        text = self.ignore_input.text().strip().lower()
        if text:
            if not text.endswith('.exe'):
                text += '.exe'
            if text not in self.ignore_apps:
                self.ignore_apps.append(text)
                self.refresh_ignore_list()
                self.on_settings_changed()
                self.ignore_input.clear()

    def remove_ignored_app(self):
        selected = self.ignore_list.selectedItems()
        for item in selected:
            app_name = item.text()
            if app_name != 'spotify.exe':
                self.ignore_apps.remove(app_name)
        self.refresh_ignore_list()
        self.on_settings_changed()


if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = ModernMainWindow()
    window.show()
    sys.exit(app.exec())
