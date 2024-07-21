#!/usr/bin/python3
import os
import json
import time
from datetime import datetime, timedelta
from PyQt5.QtGui import QIcon, QPalette, QColor
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QSpinBox, QPushButton
from PyQt5.QtWidgets import QMessageBox, QCheckBox, QSpacerItem, QSizePolicy, QLineEdit, QPushButton, QLabel
from PyQt5.QtWidgets import QApplication, QWidget, QSystemTrayIcon, QMenu, QAction, QFileDialog
from PyQt5.QtCore import QUrl
from pathlib import Path
import pyglet

class RxNagWidget(QWidget):
    def __init__(self, medication, last_taken, interval, muted, parent=None):
        super().__init__(parent)
        self.medication = medication
        self.last_taken = last_taken
        self.muted = muted
        self.interval = interval  # in hours
        self.notice_delay = 6 # in seconds
        
        layout = QVBoxLayout()
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
        self.mute_checkbox.toggled.connect(self.toggle_mute)
        medline_layout.addWidget(self.mute_checkbox)
       
        layout.addLayout(medline_layout)

        self.last_taken_label = QLabel(self.get_last_taken_text())
        self.taken_button = QPushButton("Mark taken")
        self.taken_button.clicked.connect(self.mark_as_taken)
        layout.addWidget(self.last_taken_label)
        layout.addWidget(self.taken_button)        
               
        # keep the times updated in the gui
        self.update_timer = QTimer(self)
        self.update_timer.timeout.connect(self.update_time_labels)
        self.update_timer.start(60*1000) # 1 min

        self.setLayout(layout)

    def update_time_labels(self):
        self.last_taken_label.setText(self.get_last_taken_text())        

    def edit_medication(self):
        edit_dialog = EditMedicationDialog(self.medication, self.last_taken, self.interval,self.muted, self)
        if edit_dialog.exec_():
            self.medication = edit_dialog.medication_input.text()
            self.last_taken = datetime.strptime(edit_dialog.last_taken_input.text(), "%Y-%m-%d %H:%M")
            self.interval = edit_dialog.interval_input.value()
            self.medication_label.setText(self.medication)
            self.last_taken_label.setText(self.get_last_taken_text())
            self.parent().save_config()

    def toggle_mute(self, checked):
        self.muted = checked
        self.parent().save_config()

    def display_reminder(self):
        # Set the resource path to the directory containing the sound file
        sound_file_dir = os.path.dirname(self.parent().sound_file)
        pyglet.resource.path = [sound_file_dir]
        pyglet.resource.reindex()

        try:
            if not self.parent().has_played_audio:
                sound = pyglet.resource.media(os.path.basename(self.parent().sound_file), streaming=False)
                sound.play()
                # mark as having played audio to disable until next pass to prevent spamming user
                self.parent().has_played_audio = True

            self.parent().tray_icon.showMessage(
                "Medication Reminder",
                f"💊 Time to take {self.medication}",
                QSystemTrayIcon.Information,
                self.notice_delay * 1000
            )
        except pyglet.resource.ResourceNotFoundException:
            self.parent().has_played_audio = False
            QMessageBox.warning(self, "Sound File Not Found", f"The sound file '{self.parent().sound_file}' could not be found.")

    def check_all_reminders(self):
        for medication_widget in self.medication_list:
            medication_widget.check_reminder()

    def check_reminder(self):
        next_due = self.last_taken + timedelta(hours=self.interval)
        now = datetime.now()
        if now >= next_due and not self.muted:
            self.display_reminder()
            
    def get_last_taken_text(self):
        now = datetime.now()
        time_diff = now - self.last_taken
        hours_ago = time_diff.total_seconds() // 3600
        if hours_ago < 1:
            return f"Last taken: {int(time_diff.total_seconds() // 60)} mins ago"
        else:
            return f"Last taken: {int(hours_ago)} hours ago"

    def delete_medication(self):
        self.parent().delete_medication(self)

    def mark_as_taken(self):
        self.last_taken = datetime.now()
        self.last_taken_label.setText(self.get_last_taken_text())
        self.parent().save_config()

class RxNag(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("RxNag - Medication Reminder")
        self.setGeometry(600, 200, 700, 500)
        self.notification_timer_mins = 1 
        self.sound_file = "reminder.wav"  # Default sound 
        self.has_played_audio = False
        self.setWindowIcon(QIcon('icon.png'))
        
        self.config_file = Path.home() / ".local" / "share" / "rxnag" / "config.json"
        self.load_config()

        self.tray_icon = QSystemTrayIcon(QIcon("icon.png"), self)
        self.tray_icon.activated.connect(self.show_window)
        self.tray_icon.setToolTip("RxNag")

        self.create_ui()
        self.create_tray_menu()
        
        self.timer = QTimer()
        self.start_notification_timer()

    def start_notification_timer(self):        
        self.timer.timeout.connect(self.check_all_reminders)        
        self.timer.start(self.notification_timer_mins * 60 * 1000) 

    def restart_timer(self):
        self.timer.stop()
        self.start_notification_timer()        

    def check_all_reminders(self):
        self.has_played_audio = False # reset audio status 
        for medication_widget in self.medication_list:
            medication_widget.check_reminder()
        self.update_ui()

    def update_ui(self):
        # Remove all existing medication widgets
        for i in reversed(range(self.layout().count())):
            widget = self.layout().itemAt(i).widget()
            if isinstance(widget, RxNagWidget):
                self.layout().removeWidget(widget)
                widget.setParent(None)

        # Add the updated medication widgets
        if self.medication_list:
            for medication_widget in self.medication_list:
                self.layout().addWidget(medication_widget)


    def delete_medication(self, medication_widget):
        msgBox = QMessageBox()
        msgBox.setIcon(QMessageBox.Information)
        msgBox.setText(f"Are you sure you wish to remove {medication_widget.medication}?")
        msgBox.setWindowTitle("Confirm delete medication?")
        msgBox.setStandardButtons(QMessageBox.Yes | QMessageBox.No)        
        msgBox.setDefaultButton(QMessageBox.No)
    
        returnValue = msgBox.exec()
        if returnValue == QMessageBox.Yes:       
            self.medication_list.remove(medication_widget)
            self.layout().removeWidget(medication_widget)
            medication_widget.deleteLater()
            self.save_config()

    def create_ui(self):
        layout = QVBoxLayout()

        self.medication_list = []
        for medication, last_taken, interval, muted in self.config:
            medication_widget = RxNagWidget(medication, last_taken, interval, muted, self)
            self.medication_list.append(medication_widget)
            layout.addWidget(medication_widget)
            
        add_medication_layout = QHBoxLayout()
        self.medication_input = QLineEdit()
        self.medication_input.setPlaceholderText("Add new medication")
        self.add_button = QPushButton("&Add")
        add_medication_layout.addWidget(self.medication_input)
        self.add_button.clicked.connect(self.add_medication)
        add_medication_layout.addWidget(self.medication_input)
        add_medication_layout.addWidget(self.add_button)
        

        layout.addLayout(add_medication_layout)        
        # Add a new line for the config button
        config_layout = QHBoxLayout()
        self.config_button = QPushButton("&Config")
        self.config_button.clicked.connect(self.show_config_dialog)
        config_layout.addWidget(self.config_button)
        layout.addLayout(config_layout)
        
        self.about_button = QPushButton("A&bout")
        self.about_button.clicked.connect(self.show_about_dialog)
        config_layout.addWidget(self.about_button)
        self.exit_button = QPushButton("&Exit")
        self.exit_button.clicked.connect(self.quit_app)
        config_layout.addWidget(self.exit_button)
        
        self.setLayout(layout)
        # self.setStyleSheet("""
        #     QWidget {
        #         background-color: #333;
        #         color: #eee;
        #         padding: 10px;
        #         border-radius: 5px;
        #     }
        #     QPushButton { 
        #         background-color: #001166;
        #         color: #eee;
        #     }
        #     QPushButton:hover { 
        #         background-color: #001199;
        #         color: #eee;
        #     }            
        # """)

    def show_about_dialog(self):
        about_dialog = AboutDialog(self)
        about_dialog.exec_()

    def show_config_dialog(self):
        config_dialog = ConfigDialog(self, self)
        if config_dialog.exec_():
            self.notification_timer_mins = config_dialog.notification_timer_mins_input.value()
            self.sound_file = config_dialog.sound_file_label.text()
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
        self.tray_icon.activated.connect(self.toggle_window)
        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.show()


    def add_medication(self, muted=False):
        medication = self.medication_input.text().strip()
        if medication:
            medication_widget = RxNagWidget(medication, datetime.now(), 6, muted, self)
            self.medication_list.append(medication_widget)
            self.layout().insertWidget(len(self.medication_list), medication_widget)
            self.medication_input.clear()
            self.save_config()
            self.update_ui()

    def show_window(self): # selected show from tray icon context menu
        if self.isHidden():
            self.show()
            self.activateWindow()
        else:
            self.hide()

    def toggle_window(self, reason=None):        
        print(f"vis {self.isHidden()} reason: {reason}")
        if reason == QSystemTrayIcon.Trigger: # left-clicked icon in systray
            print(f"self.isHidden {self.isHidden()}")
            if self.isHidden():
                self.activateWindow()
            else:
                if not self.hasFocus():
                    self.raise_()

    def quit_app(self):
        self.save_config()
        QApplication.instance().quit()

    def save_config(self):
        config = {
            "medications": [
                {"name": widget.medication, "last_taken": widget.last_taken.isoformat(), "interval": widget.interval, "muted": widget.muted}
                for widget in self.medication_list
            ],
            "notification_timer_mins": self.notification_timer_mins,
            "sound_file": self.sound_file
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
                    datetime.fromisoformat(medication["last_taken"]),
                    medication["interval"],
                    medication.get("muted", False)  # Use False as the default value if "muted" is not found
                )
                for medication in config.get("medications", [])
            ]
            self.notification_timer_mins = config.get("notification_timer_mins", 5)
            self.sound_file = config.get("sound_file", "reminder.wav")
        except (FileNotFoundError, json.JSONDecodeError, ValueError):
            self.config = []
            self.notification_timer_mins = 5
            self.sound_file = "reminder.wav"

        self.notification_timer_mins = max(1,self.notification_timer_mins)
        self.notification_timer_mins = min(60,self.notification_timer_mins)

class EditMedicationDialog(QDialog):
    def __init__(self, medication, last_taken, interval, muted, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Edit Medication")
        self.parent_widget = parent
        self.medication = medication
        layout = QVBoxLayout()

        medication_layout = QHBoxLayout()
        medication_label = QLabel("Medication:")
        self.medication_input = QLineEdit(medication)
        medication_layout.addWidget(medication_label)
        medication_layout.addWidget(self.medication_input)
        layout.addLayout(medication_layout)

        last_taken_layout = QHBoxLayout()
        last_taken_label = QLabel("Last Taken:")
        self.last_taken_input = QLineEdit(last_taken.strftime("%Y-%m-%d %H:%M"))
        last_taken_layout.addWidget(last_taken_label)
        last_taken_layout.addWidget(self.last_taken_input)
        layout.addLayout(last_taken_layout)

        interval_layout = QHBoxLayout()
        interval_label = QLabel("Interval (hours):")
        self.interval_input = QSpinBox()
        self.interval_input.setMinimum(1)        
        self.interval_input.setValue(interval)
        interval_layout.addWidget(interval_label)
        interval_layout.addWidget(self.interval_input)        
        layout.addLayout(interval_layout)

        button_layout = QHBoxLayout()
        self.delete_button = QPushButton("Delete")
        self.delete_button.clicked.connect(self.delete)
        self.save_button = QPushButton("Save")
        self.cancel_button = QPushButton("Cancel")
        self.save_button.clicked.connect(self.accept)
        self.cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(self.delete_button)
        button_layout.addWidget(self.save_button)
        button_layout.addWidget(self.cancel_button)
        layout.addLayout(button_layout)

        self.setLayout(layout)
        
    def delete(self):   
        self.parent().delete_medication()     
        self.accept()

class ConfigDialog(QDialog):
    def __init__(self, parent_widget, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Configuration")
        self.parent_widget = parent_widget

        layout = QVBoxLayout()
        interval_layout = QHBoxLayout()
        interval_label = QLabel("Notification timer interval (minutes): ")
        self.notification_timer_mins_input = QSpinBox()        
        self.notification_timer_mins_input.setMinimum(1)
        self.notification_timer_mins_input.setRange(1, 60)
        self.notification_timer_mins_input.adjustSize()
        
        self.notification_timer_mins_input.setValue(int(self.parent_widget.notification_timer_mins))
        interval_layout.addWidget(interval_label)
        interval_layout.addWidget(self.notification_timer_mins_input)
        layout.addLayout(interval_layout)

        # Sound file
        sound_layout = QHBoxLayout()
        sound_label = QLabel("Notification sound file: ")
        self.sound_file_label = QLabel(self.parent_widget.sound_file)
        self.sound_file_button = QPushButton("Choose File")
        self.sound_file_button.clicked.connect(self.select_sound_file)
        sound_layout.addWidget(sound_label)
        sound_layout.addWidget(self.sound_file_label)
        sound_layout.addWidget(self.sound_file_button)
        layout.addLayout(sound_layout)


        button_layout = QHBoxLayout()
        self.save_button = QPushButton("&Save")
        self.save_button.setDefault(True)
        self.cancel_button = QPushButton("&Cancel")
        self.save_button.clicked.connect(self.update)
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
                self.sound_file_label.setText(selected_file)

    def update(self):
        self.parent_widget.notification_timer_mins = self.notification_timer_mins_input.value()
        self.parent_widget.sound_file = self.sound_file_label.text()
        self.parent_widget.restart_timer()
        self.parent_widget.save_config()
        self.hide()

class AboutDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("About")

        layout = QVBoxLayout()

        label_text = """
            <p>RxNag - Medication Reminder</p>
            <p>Version 1.0.0</p>
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

if __name__ == "__main__":
    app = QApplication([])
    app.setQuitOnLastWindowClosed(False)
    reminder = RxNag()
    reminder.show()
    app.exec_()
