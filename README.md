# 🌤 Tray Weather

Multi-language weather app that lives in the system tray and shows the current temperature on its icon. Powered by [MET Norway](https://api.met.no/).

**English** | [Русский](README.ru.md)

## 📸 Screenshot

![Main window](<img width="457" height="673" alt="screenshot-main" src="https://github.com/user-attachments/assets/182fd5a9-96e5-464b-a4e4-c77566c75e36" />)

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

## ⚠️ Windows SmartScreen / Defender warning (first launch)

This app is **not digitally signed**. That's why on first launch Windows may show:

- **SmartScreen:** *"Windows protected your PC"* (blue dialog)
- **Defender:** *"This app has been blocked for your protection"*

This is a **false positive**. It happens because Windows doesn't recognize the publisher — not because the app contains a virus. All source code is available in this repository, so you can inspect it and even build the `.exe` yourself.

### ✅ How to run it anyway

**For SmartScreen (blue dialog):**

1. Click **More info**.
2. Click **Run anyway**.

**Alternative — unblock the file permanently:**

1. Right-click the downloaded `.exe` file → **Properties**.
2. At the bottom of the **General** tab, check **Unblock**.
3. Click **Apply** → **OK**.

**If Windows Defender blocks it entirely:**

1. Open **Windows Security** → **Virus & threat protection**.
2. Scroll down to **Virus & threat protection settings** → **Manage settings**.
3. Under **Exclusions**, click **Add or remove exclusions**.
4. Click **Add an exclusion** → **File** → select the `.exe` file.
5. Run the app again.

**If Defender blocks your `.bat` build:**

PyInstaller "packs" Python code into a single `.exe`, which sometimes looks suspicious to Defender. Just add the project folder to Windows Security exclusions:

1. Open **Windows Security** → **Virus & threat protection** → **Manage settings**.
2. Under **Exclusions**, click **Add or remove exclusions** → **Add an exclusion** → **Folder**.
3. Select the folder containing your `.pyw` file and `.bat` script.
4. Run the `.bat` again.

> 💡 **Safety tip:** You can also upload the `.exe` to [VirusTotal](https://www.virustotal.com/) to verify it before running.

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

## 🔗 More apps by the same author

- ⏻ [Shutdown Timer](https://github.com/SKRRIXZZ/shutdown-timer) — PC shutdown / restart / sleep / hibernate timer
- 🌐 [Mini Translator](https://github.com/SKRRIXZZ/mini-translator) — clipboard translator with a global hotkey
- ⬇ [Video & Music Downloader](https://github.com/SKRRIXZZ/video-music-downloader) — GUI downloader based on yt-dlp

---

## 📜 License
MIT
