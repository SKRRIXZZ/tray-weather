# 🌤 Погода в трее

Многоязычное приложение погоды, которое живёт в системном трее и показывает текущую температуру прямо на иконке. Источник данных — [MET Norway](https://api.met.no/).

[English](README.md) | **Русский**

---

## ✨ Возможности
- Температура прямо на иконке в трее
- Прогноз на 3 / 5 / 7 / 10 дней
- Уведомление о дожде за час
- Определение города по IP
- 20 языков интерфейса
- Тёмная / светлая тема
- Автозапуск с Windows

---

## ✅ Требования
- Windows 10 или 11
- Интернет (используется API MET Norway)
- **Python 3.11 или новее** — нужен даже для `.exe` версии

---

## 🚀 Установка

### Шаг 1 — Установить / обновить Python (всегда, одна команда)

Открой **CMD** (`Win + R` → введи `cmd` → Enter) и вставь целиком:

```cmd
winget install --id Python.Python.3.12 -e --accept-source-agreements --accept-package-agreements & winget upgrade --id Python.Python.3.12 -e --accept-source-agreements --accept-package-agreements
```

Эта команда **поставит Python, если его нет**, и **обновит, если уже есть**.

Затем **закрой и снова открой CMD** и проверь:

```cmd
py -3 --version
```

Если показывает `Python 3.12.x` — всё хорошо. Если `'py' не является внутренней командой` — смотри раздел **Проблемы**.

### Шаг 2 — Обновить pip, setuptools, wheel (всегда, одна команда)

```cmd
py -3 -m pip install --upgrade pip setuptools wheel
```

---

## 📥 Установка приложения

### 🟢 A. Если у тебя `.exe` файл
Больше ничего не нужно. Просто двойной клик по `TrayWeather.exe`.

### 🟡 B. Если у тебя `.pyw` файл
Установи библиотеки (устанавливает и обновляет автоматически):

```cmd
py -3 -m pip install --upgrade pystray Pillow win10toast pywin32
```

Запуск:

```cmd
pythonw tray_weather_world_multilang.pyw
```

### 🔴 C. Если у тебя `.bat`, который собирает `.exe`
Установи всё один раз:

```cmd
py -3 -m pip install --upgrade pyinstaller pystray Pillow win10toast pywin32
```

Затем двойной клик по `.bat` файлу. После сборки готовый `.exe` появится в папке `dist\`.

---

## ▶️ Использование
- Приложение запускается свёрнутым в трей.
- Левый клик по иконке — показать окно.
- Правый клик — меню (показать, настройки, журнал, выход).
- Укажи город в **Настройках** → поиск по названию или *Определить по IP*.

---

## 🛠 Проблемы

| Проблема | Решение |
|---|---|
| `'py' не является командой` | Переустанови Python с PrependPath: `winget install --id Python.Python.3.12 -e --accept-source-agreements --accept-package-agreements --override "/quiet InstallAllUsers=0 PrependPath=1 Include_pip=1 Include_launcher=1"`, потом открой CMD заново |
| `pip` не найден | Используй `py -3 -m pip ...` вместо `pip ...` |
| `winget` не найден | Обнови "App Installer" из Microsoft Store |
| Погода не грузится | Проверь интернет, смени город в Настройках |
| Нет Tkinter | Переустанови Python с `PrependPath=1` — Tkinter идёт в комплекте |

---

## 📜 Лицензия
MIT