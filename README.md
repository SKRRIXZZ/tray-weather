# 🌤 Tray Weather

Multi-language weather app that lives in the system tray and shows the current temperature on its icon. Powered by [MET Norway](https://api.met.no/).

**English** | [Русский](README.ru.md)

---

## ✨ Features
- Live temperature on the tray icon
- 3 / 5 / 7 / 10-day forecast
- Rain notification 1 hour ahead
- IP-based city detection
- 20 interface languages
- Dark / light theme
- Autostart with Windows

---

## ✅ Requirements
- Windows 10 or 11
- Internet connection (uses MET Norway API)
- **Python 3.11 or newer** — required even if you use the `.exe` version

---

## 🚀 Installation

### Step 1 — Install / update Python (always, one command)

Open **CMD** (`Win + R` → type `cmd` → Enter) and paste the whole line:

```cmd
winget install --id Python.Python.3.12 -e --accept-source-agreements --accept-package-agreements & winget upgrade --id Python.Python.3.12 -e --accept-source-agreements --accept-package-agreements
```

This command **installs Python if missing** and **updates it if already present**.

Then **close and reopen CMD** and verify:

```cmd
py -3 --version
```

If it prints `Python 3.12.x` — you are good. If it says `'py' is not recognized` — see **Troubleshooting**.

### Step 2 — Update pip, setuptools, wheel (always, one command)

```cmd
py -3 -m pip install --upgrade pip setuptools wheel
```

---

## 📥 Installing the app

### 🟢 A. If you have the `.exe` file
Nothing else to install. Just double-click `TrayWeather.exe`.

### 🟡 B. If you have the `.pyw` file
Install libraries (installs and updates automatically):

```cmd
py -3 -m pip install --upgrade pystray Pillow win10toast pywin32
```

Run:

```cmd
pythonw tray_weather_world_multilang.pyw
```

### 🔴 C. If you have a `.bat` that builds `.exe`
Install everything once:

```cmd
py -3 -m pip install --upgrade pyinstaller pystray Pillow win10toast pywin32
```

Then double-click your `.bat` file. When it finishes, the ready `.exe` will be inside the `dist\` folder.

---

## ▶️ Usage
- App starts minimized in the tray.
- Left-click tray icon — show window.
- Right-click tray icon — menu (show, settings, log, exit).
- Set your city in **Settings** → search by name or *Detect city by IP*.

---

## 🛠 Troubleshooting

| Problem | Solution |
|---|---|
| `'py' is not recognized` | Reinstall Python with PrependPath: `winget install --id Python.Python.3.12 -e --accept-source-agreements --accept-package-agreements --override "/quiet InstallAllUsers=0 PrependPath=1 Include_pip=1 Include_launcher=1"` then reopen CMD |
| `pip` not found | Use `py -3 -m pip ...` instead of `pip ...` |
| `winget` not found | Update "App Installer" from Microsoft Store |
| Weather does not load | Check internet, try changing city in Settings |
| Tkinter missing | Reinstall Python with `PrependPath=1` — Tkinter is bundled |

---

## 📜 License
MIT
