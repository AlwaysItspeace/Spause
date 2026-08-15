# Spause 🎵

> Auto-pause Spotify on Windows whenever sound is detected from another application, and automatically resume music playback when the external sound stops.

![Spause App](https://img.shields.io/badge/Platform-Windows%2010%20%2F%2011-blue?logo=windows)
![Python](https://img.shields.io/badge/Python-3.10%2B-green?logo=python)

## 💡 How It Works

Spause uses the **Windows WASAPI Core Audio API** to monitor real-time audio output levels across all active Windows application streams. 
- When sound plays from another process (browser, game, video call, media player), Spotify playback pauses.
- Once silence is detected, Spotify automatically resumes after a configurable silence buffer.

## ✨ Features

- **Zero API Key Setup**: Controls Spotify via Windows System Media Transport Controls (SMTC).
- **Real-Time Sound Metering**: Visual audio level monitor with threshold trigger styling.
- **Customizable Sensitivity**: Adjust trigger threshold percentage (1% - 20%).
- **Silence Resume Delay**: Configurable delay buffer (0.5s - 5.0s) to prevent playback stuttering.
- **App Whitelist**: Exclude specific applications (e.g. Discord notification sounds, system beeps) from triggering pause.
- **Modern Dark UI**: Frameless window design with custom toggle switches and smooth animations.
- **System Tray Integration**: Minimizes cleanly to the Windows taskbar system tray.

## 🚀 Quick Start (Running Executable)

1. Download `Spause.exe` from the latest release or build it locally.
2. Double-click `Spause.exe` to run.
3. Play music on Spotify—sound from any other program will pause Spotify and automatically resume it when quiet!

## 🛠️ Running from Source / Building `.exe`

### Requirements
- Python 3.10+
- Windows 10 / 11

### Installation

```bash
git clone https://github.com/your-username/spause.git
cd spause
pip install -r requirements.txt
python main.py
```

### Build Standalone Executable (.exe)

```bash
pip install pyinstaller
python -m PyInstaller --noconfirm --onefile --windowed --name "Spause" main.py
```

The compiled `Spause.exe` file will be created in the `dist/` directory.

## 📜 License

MIT License.
