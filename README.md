# RxNag - Medication Reminder

A very lightweight off-line application to nag you when it is time to take your medications.  It is 100% free and open source. (GPL-3)

## Requirements

You need Python3, PyQt5, and Pyglet for audio playback.

On Linux Mint, Ubuntu, Debian, etc. (Python3 should already be installed)

```apt install python3 python3-pyqt5 python3-pyglet```

## Usage
Add your medications, set their dose _interval_. (how often you take them) When you get a notification message simply click on the tray icon and then click the **[Mark taken]** button."  

These notifications will continue every _notification interval_. (default 5 minutes)  

You can ** Mute ** notifications disable them per-medication.  While muted they will still be tracked when taken.

## Auto run after login
It is possible to add RxNag to auto run when you login.  For example, in Linux Mint for use ** Mint Menu -> Startup Applications ** then select the ** + ** icon. (plus)

## Configuration
Select the **[Config]** button.

Notification interval (in minutes) [Default 5] - This is how often to check for next dose
Notification sound file [Default reminder.wav] - Custom audio file (.wav,.ogg,.mp3) 

Configuration and all data are only stored in your home folder.
```$HOME/.local/share/rxnag/config.json```

Please ensure you are backing up your home directory.

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
* Dose anything other than nag you to take your medications


