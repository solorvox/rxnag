# 💊 RxNag - Medication Reminder

A very lightweight off-line application to nag you when it is time to take your medications.  It is 100% free and open source. (GPL-3)

## Requirements

You need Python3, PyQt5, and PyGame. (PyGame is for audio playback).

On Linux Mint, Ubuntu, Debian, etc. (Python3 should already be installed)

```apt install python3 python3-pyqt5 python3-pygame```

## Installation

### From github
Using git:
```git clone https://github.com/solorvox/rxnag```

Launching RxNag options:

1. Command line:  ```cd rxnag && ./rxnag.py```
2. File manager, navigate to the rxnag folder and double click ```rxnag.py``` then select run

It is possible to set RxNag to auto run when you login.  For example, in Linux Mint use **Mint Menu -> Startup Applications** then select the **[+]** icon. (plus)

Select **Custom Command** then the **Browse** button on the command line.  After selecting ```rxnag.py``` and anything you like for name/description, you can then **Add**.

### Releases
Binary/flatpak/Windows versions are "Coming soon &tm;"

## Usage
Add your medications, set their dose _interval_. (how often you take them) When you get a notification message simply click on the tray icon and then click the **[Mark taken]** button."  

These notifications will continue every _notification interval_. (default 5 minutes)  

You can **Mute** notifications to disable them per-medication.  While muted they will still be tracked when taken.

## Configuration
Select the **[Config]** button.

* Notification interval (in minutes) [Default 5] - This is how often to check for next dose
* Notification shown  (in seconds) [Default 10] - How long the popup notification lasts before closing
* Notification sound file [Default reminder.wav] - Custom audio file (.wav,.ogg,.mp3) 
* Notification volume [Default 75%]
* Start minimized - Start the application minimized to system tray.  (can also use `--minimized` argument)

Configuration and all data are only stored in your home folder.
```$HOME/.local/share/rxnag/config.json```

Please ensure you are backing up your home directory.

## Command line arguments

* `--show` - Shows the window regardless of minimized setting in config.
* `--minimized` - Start minimized to the system tray

## Tips
You can right click on the tray icon to exit/show.  Or you can simply just left-click the icon.

## Privacy Policy
There is no need as this is a **100% _off-line_** application.  

This app **_DOES NOT_** have any of the following "features":

* Requires an on-line account for use
* Requires a internet connection
* Sells your data to third parties
* Transmit anything to anywhere else
* Spam you with donation requests
* Take hundreds of MB/GB of disk space or RAM (currently < 1MB on disk)
* Does anything other than nag you to take your medications

