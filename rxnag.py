#!/usr/bin/python3
# rxnag - Medication reminder app
# Copyright (c) 2024-2026 Solorvox solorvox (at) epic.geek.nz
# Source: https://github.com/solorvox/rxnag
# License: GPL-3 https://www.gnu.org/licenses/gpl-3.0.txt
import os
import json
import time
import argparse
import atexit
from dateutil import parser
from PyQt5.QtGui import QIcon, QPalette, QColor
from PyQt5.QtCore import Qt, QTimer, pyqtSignal
from PyQt5.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QSpinBox, QPushButton
from PyQt5.QtWidgets import QMessageBox, QCheckBox, QSpacerItem, QSizePolicy
from PyQt5.QtWidgets import QApplication, QWidget, QSystemTrayIcon, QMenu, QAction, QFileDialog
from PyQt5.QtWidgets import QSlider
from pathlib import Path
import datetime

os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = "hide"
import pygame

pid = str(os.getpid())
pidfile = os.path.join(os.path.sep, "tmp", "rxnag.pid")
default_sound_file = 'reminder.wav'

class RxNagWidget(QWidget):
    # Signals for decoupled communication
    taken = pyqtSignal()
    muted_changed = pyqtSignal(bool)
    edited = pyqtSignal()
    delete_requested = pyqtSignal()
    show_reminder = pyqtSignal(str)

    def __init__(self, medication: str, last_taken: int, interval: int, muted: bool, parent=None):
        super().__init__(parent)
        self.medication = medication
        self.last_taken = last_taken  # in seconds since epoch
        self.muted = muted
        self.interval = interval  # in hours

        # Create a container widget to hold all the other widgets
        self.container = QWidget()
        container_layout = QVBoxLayout()
        self.container.setObjectName("MedicationContainer")
        self.container.setLayout(container_layout)
        self.container.setContentsMargins(0, 0, 0, 0)

        medline_layout = QHBoxLayout()

        self.medication_label = QLabel(medication)
        medline_layout.addWidget(self.medication_label)

        spacer = QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum)
        medline_layout.addItem(spacer)

        self.edit_button = QPushButton("Edit")
        self.edit_button.clicked.connect(self.edit_medication)
        self.edit_button.setFixedWidth(80)
        medline_layout.addWidget(self.edit_button)

        # Mute checkbox
        self.mute_checkbox = QCheckBox("Mute")
        self.mute_checkbox.setChecked(self.muted)
        self.mute_checkbox.toggled.connect(self.on_mute_toggled)
        medline_layout.addWidget(self.mute_checkbox)

        container_layout.addLayout(medline_layout)

        time_text_layout = QHBoxLayout()
        self.last_taken_label = QLabel(self.get_last_taken_text())
        time_text_layout.addWidget(self.last_taken_label)
        self.next_dose_label = QLabel(self.get_next_dose_text())
        time_text_layout.addWidget(self.next_dose_label)
        container_layout.addLayout(time_text_layout)

        self.taken_button = QPushButton("Mark taken")
        self.taken_button.clicked.connect(self.on_taken_clicked)

        container_layout.addWidget(self.taken_button)

        # keep the times updated in the gui
        self.update_timer = QTimer(self)
        self.update_timer.timeout.connect(self.update_time_labels)
        self.update_timer.start(60 * 1000)  # 1 min

        # Add the container widget to the main layout
        layout = QVBoxLayout()
        layout.addWidget(self.container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.setLayout(layout)

        # Set the initial style
        self.update_style()

    def on_taken_clicked(self):
        self.last_taken = int(time.time())
        self.last_taken_label.setText(self.get_last_taken_text())
        self.next_dose_label.setText(self.get_next_dose_text())
        self.update_style()
        self.taken.emit()

    def on_mute_toggled(self, checked):
        self.muted = checked
        self.muted_changed.emit(checked)

    def edit_medication(self):
        edit_dialog = EditMedicationDialog(self.medication, self.last_taken, self.interval, self.muted, self)
        if edit_dialog.exec_():
            if edit_dialog.was_deleted:
                self.delete_requested.emit()
                return

            self.medication = edit_dialog.medication_input.text()
            strtime = edit_dialog.last_taken_input.text()
            self.last_taken = int(parser.parse(strtime).timestamp())
            self.interval = edit_dialog.interval_input.value()
            self.medication_label.setText(self.medication)
            self.last_taken_label.setText(self.get_last_taken_text())
            self.update_time_labels()
            self.update_style()
            self.edited.emit()

    def check_reminder(self):
        next_due = self.last_taken + (self.interval * 3600)
        now = int(time.time())
        if now >= next_due and not self.muted:
            self.show_reminder.emit(self.medication)
        self.update_style()

    def update_time_labels(self):
        self.last_taken_label.setText(self.get_last_taken_text())
        self.next_dose_label.setText(self.get_next_dose_text())

    def update_style(self):
        now = int(time.time())
        next_due = self.last_taken + (self.interval * 3600)

        # Get the current desktop theme's color
        palette = self.palette()
        border_color = palette.color(QPalette.Highlight)

        # Darken the border color a bit
        dark_color = palette.color(QPalette.Window).darker(64)

        if now >= next_due:
            # Set the border when the medication is due
            style = "QWidget#MedicationContainer {"
            style += "border: 2px solid "
            style += f"{border_color.name(QColor.HexRgb)}; "
            style += " background-color: "
            style += f"{dark_color.name(QColor.HexRgb)};}}"
            self.container.setStyleSheet(style)
        else:
            # Reset the style to the default
            self.container.setStyleSheet("")

    def get_last_taken_text(self):
        if self.last_taken > 0:
            time_diff = int(time.time()) - self.last_taken
            time_string = Utils.format_time(time_diff)
            return f"Last taken: {time_string} ago"
        else:
            return "Last taken: Never"

    def get_next_dose_text(self):
        next_dose_secs = self.last_taken + (self.interval * 3600) - int(time.time())
        if next_dose_secs <= 0:
            return "Next dose: <b>now</b>"
        else:
            time_string = Utils.format_time(next_dose_secs)
            return f"Next dose: {time_string}"

class Utils:
    @staticmethod
    def format_time(seconds: int) -> str:
        if seconds < 0:
            return "0 Seconds"
        days, rem = divmod(seconds, 86400)
        hours, rem = divmod(rem, 3600)
        minutes, secs = divmod(rem, 60)
        parts = []
        if days: parts.append(f"{days} {'Day' if days == 1 else 'Days'}")
        if hours: parts.append(f"{hours} {'Hour' if hours == 1 else 'Hours'}")
        if minutes and not days: parts.append(f"{minutes} {'Minute' if minutes == 1 else 'Minutes'}")
        if secs and not (days or hours or minutes):
            parts.append(f"{secs} Seconds")
        return ", ".join(parts) if parts else "0 Seconds"

class RxNag(QWidget):
    def __init__(self, audio_available: bool):
        super().__init__()
        self.setWindowTitle("RxNag - Medication Reminder")
        self.setGeometry(600, 200, 700, 500)
        self.notification_timer_mins = 1
        self.notification_shown_secs = 10
        self.audio_available = audio_available
        self.play_sound = True
        self.sound_file = default_sound_file
        self.sound_volume = 0.75  # default 75%
        self.has_played_audio = False
        self.setWindowIcon(QIcon(os.path.join(get_script_path(), 'icon.png')))
        self.mute_all = False
        self.start_minimized = False
        self.medication_interval_default = 6  # number of hours a dose defaults

        self.config_file = os.path.join(Path.home(), ".local", "share", "rxnag", "config.json")
        self.load_config()

        self.tray_icon = QSystemTrayIcon(QIcon(os.path.join(get_script_path(), 'icon.png')), self)
        self.tray_icon.setToolTip("RxNag")

        self.create_ui()
        self.create_tray_menu()

        # Single tray activation connection
        self.tray_icon.activated.connect(self.on_tray_activated)
        self.tray_icon.show()

        self.timer = QTimer()
        self.start_notification_timer()

    def play_notification_sound(self):
        # Check if sound is enabled and pygame/audio is available
        if not (self.play_sound and self.audio_available):
            return

        try:
            if not self.has_played_audio:
                snd_file = self.sound_file
                # If using relative path, ensure we append script's directory
                if snd_file == default_sound_file:
                    snd_file = os.path.join(get_script_path(), default_sound_file)
                sound = pygame.mixer.Sound(snd_file)
                sound.set_volume(self.sound_volume)
                sound.play()
                self.has_played_audio = True
        except FileNotFoundError:
            self.has_played_audio = False
            QMessageBox.warning(self, "Sound File Not Found",
                                f"The sound file '{self.sound_file}' could not be found.")
        except Exception as e:
            # Fallback silent handling to avoid crashes
            self.has_played_audio = False

    def start_notification_timer(self):
        self.timer.timeout.connect(self.check_all_reminders)
        self.timer.start(self.notification_timer_mins * 60 * 1000)

    def restart_timer(self):
        self.timer.stop()
        self.start_notification_timer()

    def check_all_reminders(self):
        self.has_played_audio = False  # reset audio status for this cycle
        for medication_widget in self.medication_list:
            medication_widget.check_reminder()

    # Signal handlers (decoupled from widgets)
    def on_med_taken(self, widget):
        self.save_config()

    def on_med_muted(self, widget, checked):
        self.save_config()

    def on_med_edited(self, widget):
        self.save_config()

    def on_med_delete_requested(self, widget):
        msg = QMessageBox(self)
        msg.setIcon(QMessageBox.Warning)
        msg.setText(f"Are you sure you wish to remove {widget.medication}?")
        msg.setWindowTitle("Confirm delete medication?")
        msg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        msg.setDefaultButton(QMessageBox.No)

        if msg.exec_() == QMessageBox.Yes:
            self.medication_list.remove(widget)
            self.layout().removeWidget(widget)
            widget.deleteLater()
            self.save_config()

    def on_show_reminder(self, medication_name):
        if self.mute_all:
            return

        self.play_notification_sound()
        self.tray_icon.showMessage(
            "Medication Reminder",
            f"💊 Time to take {medication_name}",
            QSystemTrayIcon.Information,
            self.notification_shown_secs * 1000
        )

    def create_ui(self):
        layout = QVBoxLayout()
        self.setLayout(layout)

        toolbar_area = QHBoxLayout()
        self.config_button = QPushButton("&Config")
        self.config_button.clicked.connect(self.show_config_dialog)
        toolbar_area.addWidget(self.config_button)

        self.about_button = QPushButton("A&bout")
        self.about_button.clicked.connect(self.show_about_dialog)
        toolbar_area.addWidget(self.about_button)

        self.mute_all_button = QPushButton("&Mute all")
        self.mute_all_button.clicked.connect(self.toggle_mute_all)
        self.mute_all_button.setCheckable(True)
        toolbar_area.addWidget(self.mute_all_button)

        self.exit_button = QPushButton("&Exit")
        self.exit_button.clicked.connect(self.handle_exit)
        toolbar_area.addWidget(self.exit_button)

        layout.addLayout(toolbar_area)

        add_medication_layout = QHBoxLayout()
        self.medication_input = QLineEdit()
        self.medication_input.setPlaceholderText("Add new medication")
        self.add_button = QPushButton("&Add")
        self.add_button.clicked.connect(self.add_medication)
        add_medication_layout.addWidget(self.medication_input)
        add_medication_layout.addWidget(self.add_button)
        layout.addLayout(add_medication_layout)

        self.medication_list = []
        for medication, last_taken, interval, muted in self.config:
            medication_widget = RxNagWidget(medication, last_taken, interval, muted, self)
            self.medication_list.append(medication_widget)
            layout.addWidget(medication_widget)

            # Connect signals (use default arg to capture widget)
            w = medication_widget
            w.taken.connect(lambda _, w=w: self.on_med_taken(w))
            w.muted_changed.connect(lambda c, w=w: self.on_med_muted(w, c))
            w.edited.connect(lambda _, w=w: self.on_med_edited(w))
            w.delete_requested.connect(lambda _, w=w: self.on_med_delete_requested(w))
            w.show_reminder.connect(self.on_show_reminder)

    def handle_exit(self):
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("Exit RxNag?")
        msg_box.setText("Would you like to exit RxNag or minimize to the system tray?")
        minimize_btn = msg_box.addButton("&Minimize to tray icon", QMessageBox.NoRole)
        exit_btn = msg_box.addButton("&Exit RxNag", QMessageBox.YesRole)
        msg_box.setIcon(QMessageBox.Question)

        msg_box.exec_()
        clicked = msg_box.clickedButton()
        if clicked == exit_btn:
            QApplication.instance().quit()
        else:
            self.hide()

    def toggle_mute_all(self):
        self.mute_all = not self.mute_all

    def show_about_dialog(self):
        about_dialog = AboutDialog(self)
        about_dialog.exec_()

    def show_config_dialog(self):
        config_dialog = ConfigDialog(self, self)
        if config_dialog.exec_():
            self.notification_timer_mins = config_dialog.notification_timer_mins_input.value()
            self.restart_timer()
            self.save_config()

    def create_tray_menu(self):
        tray_menu = QMenu()
        about_action = QAction("About", self)
        about_action.triggered.connect(self.show_about_dialog)
        show_action = QAction("Show", self)
        show_action.triggered.connect(self.show_window)
        exit_action = QAction("Exit", self)
        exit_action.triggered.connect(self.quit_app)
        tray_menu.addAction(about_action)
        tray_menu.addAction(show_action)
        tray_menu.addAction(exit_action)
        self.tray_icon.setContextMenu(tray_menu)

    def add_medication(self, muted=False):
        medication = self.medication_input.text().strip()
        if medication:
            medication_widget = RxNagWidget(medication, int(time.time()),
                                            self.medication_interval_default, muted, self)
            self.medication_list.append(medication_widget)
            self.layout().addWidget(medication_widget)

            # Connect signals
            w = medication_widget
            w.taken.connect(lambda _, w=w: self.on_med_taken(w))
            w.muted_changed.connect(lambda c, w=w: self.on_med_muted(w, c))
            w.edited.connect(lambda _, w=w: self.on_med_edited(w))
            w.delete_requested.connect(lambda _, w=w: self.on_med_delete_requested(w))
            w.show_reminder.connect(self.on_show_reminder)

            self.medication_input.clear()
            self.save_config()

    def closeEvent(self, event):
        # Always minimize to tray instead of closing
        event.ignore()
        self.hide()

    def show_window(self):
        # Used by tray menu "Show" action
        self.show()
        self.raise_()
        self.activateWindow()

    def on_tray_activated(self, reason):
        # Left-click (Trigger) or double-click (DoubleClick) depending on DE
        if reason in (QSystemTrayIcon.Trigger, QSystemTrayIcon.DoubleClick):
            if self.isVisible():
                self.hide()
            else:
                self.show()
                self.raise_()
                self.activateWindow()

    def quit_app(self):
        self.save_config()
        QApplication.instance().quit()

    def save_config(self):
        config = {
            "medications": [
                {"name": widget.medication,
                 "last_taken": widget.last_taken,
                 "interval": widget.interval,
                 "muted": widget.muted}
                for widget in self.medication_list
            ],
            "notification_timer_mins": self.notification_timer_mins,
            "notification_shown_secs": self.notification_shown_secs,
            "play_sound": self.play_sound,
            "sound_file": self.sound_file,
            "sound_volume": self.sound_volume,
            "start_minimized": self.start_minimized,
        }
        os.makedirs(os.path.dirname(self.config_file), exist_ok=True)
        with open(self.config_file, "w") as f:
            json.dump(config, f)

    def load_config(self):
        try:
            with open(self.config_file, "r") as f:
                config = json.load(f)
            self.config = [
                (
                    medication["name"],
                    medication["last_taken"],
                    medication["interval"],
                    medication.get("muted", False)
                )
                for medication in config.get("medications", [])
            ]
            self.notification_timer_mins = config.get("notification_timer_mins", 5)
            self.notification_shown_secs = config.get("notification_shown_secs", 10)
            self.play_sound = config.get("play_sound", True)
            self.sound_file = config.get("sound_file", default_sound_file)
            self.sound_volume = config.get("sound_volume", 0.75)
            self.sound_volume = max(0.0, min(1.0, self.sound_volume))
            self.start_minimized = config.get("start_minimized", False)
        except (FileNotFoundError, json.JSONDecodeError, ValueError):
            self.config = []
            self.sound_file = default_sound_file

        self.notification_timer_mins = max(1, min(60, self.notification_timer_mins))
        self.notification_shown_secs = max(1, min(60, self.notification_shown_secs))

class EditMedicationDialog(QDialog):
    def __init__(self, medication, last_taken, interval, muted, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Edit Medication")
        self.was_deleted = False

        layout = QVBoxLayout()

        medication_layout = QHBoxLayout()
        medication_label = QLabel("Medication:")
        self.medication_input = QLineEdit(medication)
        medication_layout.addWidget(medication_label)
        medication_layout.addWidget(self.medication_input)
        layout.addLayout(medication_layout)

        last_taken_layout = QHBoxLayout()
        last_taken_label = QLabel("Last Taken:")
        self.last_taken_input = QLineEdit(
            datetime.datetime.fromtimestamp(last_taken).strftime('%Y-%m-%d %H:%M')
        )
        last_taken_layout.addWidget(last_taken_label)
        last_taken_layout.addWidget(self.last_taken_input)
        layout.addLayout(last_taken_layout)

        interval_layout = QHBoxLayout()
        interval_label = QLabel("Interval (hours):")
        self.interval_input = QSpinBox()
        self.interval_input.setMinimum(1)
        self.interval_input.setMaximum(999)
        self.interval_input.setValue(interval)
        interval_layout.addWidget(interval_label)
        interval_layout.addWidget(self.interval_input)
        layout.addLayout(interval_layout)

        button_layout = QHBoxLayout()
        self.delete_button = QPushButton("Delete")
        self.delete_button.clicked.connect(self.delete)
        self.save_button = QPushButton("Save")
        self.save_button.setDefault(True)
        self.cancel_button = QPushButton("Cancel")
        self.save_button.clicked.connect(self.accept)
        self.cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(self.delete_button)
        button_layout.addWidget(self.save_button)
        button_layout.addWidget(self.cancel_button)
        layout.addLayout(button_layout)

        self.setLayout(layout)

    def delete(self):
        self.was_deleted = True
        self.accept()

class ConfigDialog(QDialog):
    def __init__(self, parent_widget, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Configuration")
        self.parent_widget = parent_widget
        self.setFixedWidth(600)

        layout = QVBoxLayout()

        interval_layout = QHBoxLayout()
        interval_label = QLabel("Notification timer interval (minutes): ")
        self.notification_timer_mins_input = QSpinBox()
        self.notification_timer_mins_input.setMinimum(1)
        self.notification_timer_mins_input.setRange(1, 60)
        self.notification_timer_mins_input.setFixedWidth(100)
        self.notification_timer_mins_input.setValue(int(self.parent_widget.notification_timer_mins))
        interval_layout.addWidget(interval_label)
        interval_layout.addWidget(self.notification_timer_mins_input)
        layout.addLayout(interval_layout)

        notification_shown_layout = QHBoxLayout()
        notification_shown_label = QLabel("Notification shown (seconds): ")
        self.notification_shown_secs_input = QSpinBox()
        self.notification_shown_secs_input.setMinimum(1)
        self.notification_shown_secs_input.setRange(1, 60)
        self.notification_shown_secs_input.setFixedWidth(100)
        self.notification_shown_secs_input.setValue(int(self.parent_widget.notification_shown_secs))
        notification_shown_layout.addWidget(notification_shown_label)
        notification_shown_layout.addWidget(self.notification_shown_secs_input)
        layout.addLayout(notification_shown_layout)

        # play sound
        play_sound_toggle_layout = QHBoxLayout()
        play_sound_toggle_label = QLabel("Play sound: ")
        self.play_sound_toggle = QCheckBox("")
        self.play_sound_toggle.setChecked(self.parent_widget.play_sound)
        self.play_sound_toggle.toggled.connect(self.toggle_play_sound)
        play_sound_toggle_layout.addWidget(play_sound_toggle_label)
        play_sound_toggle_layout.addWidget(self.play_sound_toggle)
        layout.addLayout(play_sound_toggle_layout)

        # Sound file
        sound_layout = QHBoxLayout()
        sound_label = QLabel("Notification sound file: ")
        self.sound_file_label = QLabel(os.path.basename(self.parent_widget.sound_file))
        self.sound_file_button = QPushButton("Choose File")
        self.sound_file_button.clicked.connect(self.select_sound_file)
        sound_layout.addWidget(sound_label)
        sound_layout.addWidget(self.sound_file_label)
        sound_layout.addWidget(self.sound_file_button)
        layout.addLayout(sound_layout)

        # Volume slider
        volume_layout = QHBoxLayout()
        volume_label = QLabel("Notification volume: ")
        self.volume_slider = QSlider(Qt.Horizontal)
        self.volume_slider.setMinimum(0)
        self.volume_slider.setMaximum(100)
        self.volume_slider.setTickPosition(QSlider.TicksBothSides)
        self.volume_slider.setTickInterval(5)
        self.volume_slider.setValue(int(self.parent_widget.sound_volume * 100))
        self.volume_slider.valueChanged.connect(self.update_volume)
        self.volume_slider.sliderReleased.connect(self.adjust_volume_feedback)
        volume_layout.addWidget(volume_label)
        volume_layout.addWidget(self.volume_slider)
        layout.addLayout(volume_layout)

        # start minimized
        start_minimized_layout = QHBoxLayout()
        start_minimized_label = QLabel("Start minimized: ")
        self.start_minimized_toggle = QCheckBox("")
        self.start_minimized_toggle.setChecked(self.parent_widget.start_minimized)
        self.start_minimized_toggle.toggled.connect(self.toggle_start_minimized)
        start_minimized_layout.addWidget(start_minimized_label)
        start_minimized_layout.addWidget(self.start_minimized_toggle)
        layout.addLayout(start_minimized_layout)

        button_layout = QHBoxLayout()
        self.save_button = QPushButton("&Save")
        self.save_button.setDefault(True)
        self.cancel_button = QPushButton("&Cancel")
        self.save_button.clicked.connect(self.save_and_update)
        self.cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_button)
        button_layout.addWidget(self.save_button)
        layout.addLayout(button_layout)

        self.setLayout(layout)

    def select_sound_file(self):
        file_dialog = QFileDialog(self, "Select Notification Sound File")
        file_dialog.setNameFilter("Audio files (*.wav *.mp3 *.ogg)")
        if file_dialog.exec_():
            selected_files = file_dialog.selectedFiles()
            if selected_files:
                selected_file = selected_files[0]
                self.parent_widget.sound_file = selected_file
                self.sound_file_label.setText(os.path.basename(selected_file))

    def toggle_play_sound(self):
        self.parent_widget.play_sound = not self.parent_widget.play_sound

    def toggle_start_minimized(self):
        self.parent_widget.start_minimized = not self.parent_widget.start_minimized

    def adjust_volume_feedback(self):
        self.parent_widget.play_notification_sound()
        self.parent_widget.has_played_audio = False

    def update_volume(self):
        self.parent_widget.sound_volume = self.volume_slider.value() / 100.0

    def save_and_update(self):
        self.parent_widget.notification_timer_mins = self.notification_timer_mins_input.value()
        self.parent_widget.notification_shown_secs = self.notification_shown_secs_input.value()
        self.update_volume()
        self.parent_widget.restart_timer()
        self.parent_widget.save_config()
        self.accept()

class AboutDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("About")

        layout = QVBoxLayout()

        label_text = """
            <p>RxNag - Medication Reminder</p>
            <p>Version 1.0.4</p>
            <p>Copyright (c) 2024 Solorvox @ <a href="https://epic.geek.nz/">epic.geek.nz</a></p>
            <p>License: GPL-3</p>
        """
        self.label = QLabel(label_text)
        self.label.setOpenExternalLinks(True)
        layout.addWidget(self.label)

        button_layout = QHBoxLayout()
        self.ok_button = QPushButton("OK")
        self.ok_button.clicked.connect(self.accept)
        button_layout.addWidget(self.ok_button)
        layout.addLayout(button_layout)
        self.setLayout(layout)

def single_instance_check():
    if os.path.isfile(pidfile):
        with open(pidfile, "r") as f:
            running_pid = f.read().strip()
        if running_pid and os.path.exists("/proc/" + running_pid):
            print(f"Another instance of the script is already running with PID {running_pid}")
            exit(1)

    with open(pidfile, "w") as f:
        f.write(pid)

    def cleanup_pid():
        try:
            os.remove(pidfile)
        except FileNotFoundError:
            pass
    atexit.register(cleanup_pid)

def get_script_path():
    return os.path.dirname(os.path.realpath(__file__))

if __name__ == "__main__":
    single_instance_check()
    argparser = argparse.ArgumentParser()
    argparser.add_argument("--minimized", action="store_true")
    argparser.add_argument("--show", action="store_true")
    args = argparser.parse_args()

    audio_available = False
    try:
        pygame.mixer.init()
        audio_available = True
    except Exception:
        audio_available = False

    app = QApplication([])
    app.setQuitOnLastWindowClosed(False)
    reminder = RxNag(audio_available)

    # if not set to minimize, show the main window
    if args.show or (not args.minimized and not reminder.start_minimized):
        reminder.show()

    app.exec_()
