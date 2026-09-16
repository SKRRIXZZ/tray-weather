import tkinter as tk
from tkinter import messagebox, filedialog
import threading
import time
import os
import sys
import json
import tempfile
import collections
import ctypes
import urllib.request
import urllib.parse
from datetime import datetime, timedelta

try:
    import pystray
    from PIL import Image, ImageDraw, ImageFont, ImageTk
    TRAY_AVAILABLE = True
except ImportError:
    TRAY_AVAILABLE = False

try:
    import winreg
    WINREG_OK = True
except ImportError:
    WINREG_OK = False

try:
    from win10toast import ToastNotifier
    TOAST_OK = True
except ImportError:
    TOAST_OK = False


def _set_app_id(app_id):
    try:
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(app_id)
    except Exception:
        pass

_set_app_id("TrayWeather.MetNo.App.5")


SIGNAL_FILE = os.path.join(tempfile.gettempdir(),
                           "tray_weather_singleton.signal")
_mutex_handle = None
ERROR_ALREADY_EXISTS = 183

REG_PATH = r"Software\TrayWeather"
ICON_CACHE_DIR = os.path.join(tempfile.gettempdir(), "tray_weather_icons")


def acquire_single_instance():
    global _mutex_handle
    try:
        kernel32 = ctypes.windll.kernel32
        _mutex_handle = kernel32.CreateMutexW(
            None, False, "TrayWeather_SingleInstance_Mutex")
        return kernel32.GetLastError() != ERROR_ALREADY_EXISTS
    except Exception:
        return True


def signal_existing_instance():
    try:
        with open(SIGNAL_FILE, "w", encoding="utf-8") as f:
            f.write("1")
    except Exception:
        pass


def _app_dir():
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(sys.argv[0]))


APP_DIR = _app_dir()


# ============ РЕЕСТР ============
def _reg_read(name):
    if not WINREG_OK:
        return None
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_PATH, 0,
                             winreg.KEY_READ)
        try:
            val, _ = winreg.QueryValueEx(key, name)
            return val
        finally:
            winreg.CloseKey(key)
    except FileNotFoundError:
        return None
    except Exception:
        return None


def _reg_write(name, value):
    if not WINREG_OK:
        return False
    try:
        key = winreg.CreateKey(winreg.HKEY_CURRENT_USER, REG_PATH)
        try:
            winreg.SetValueEx(key, name, 0, winreg.REG_SZ, str(value))
            return True
        finally:
            winreg.CloseKey(key)
    except Exception:
        return False


def load_settings():
    raw = _reg_read("settings")
    if not raw:
        return {}
    try:
        return json.loads(raw)
    except Exception:
        return {}


def save_settings(data):
    try:
        _reg_write("settings", json.dumps(data, ensure_ascii=False))
    except Exception:
        pass


_LOG_BUFFER = collections.deque(maxlen=300)


def log_event(text):
    try:
        ts = time.strftime("%H:%M:%S")
        _LOG_BUFFER.append(f"[{ts}] {text}")
    except Exception:
        pass


def get_log_text():
    if not _LOG_BUFFER:
        return "(журнал пуст)"
    return "\n".join(_LOG_BUFFER)


# ============ ТЕМЫ ============
THEMES = {
    "dark": {
        "bg": "#1c1f26", "bg_dark": "#13161b",
        "fg": "#e8eaf0", "fg_dim": "#8b8f9c",
        "white": "#ffffff", "selected_fg": "#ffffff",
        "green": "#4ade80", "green_b": "#86efac",
        "orange": "#fbbf24", "orange_b": "#fde047",
        "red": "#f87171", "red_b": "#fca5a5",
        "blue": "#5a8fc9", "blue_hov": "#6a9fd9", "blue_b": "#7aa8dc",
        "purple": "#a274c9", "purple_hov": "#b284d9",
        "up_clr": "#6b6f7c",
        "action_bg": "#262a33", "action_hover": "#31363f",
        "action_active": "#16a34a",
        "btn_start": "#16a34a", "btn_start_hov": "#22c55e",
        "btn_cancel": "#7f1d1d", "btn_cancel_hov": "#991b1b",
        "entry_bg": "#13161b", "entry_border": "#31363f",
    },
    "light": {
        "bg": "#f6f8fb", "bg_dark": "#ffffff",
        "fg": "#1a1f29", "fg_dim": "#6b7280",
        "white": "#ffffff", "selected_fg": "#ffffff",
        "green": "#10b981", "green_b": "#059669",
        "orange": "#f59e0b", "orange_b": "#d97706",
        "red": "#ef4444", "red_b": "#dc2626",
        "blue": "#2563eb", "blue_hov": "#3b82f6", "blue_b": "#3b82f6",
        "purple": "#7c3aed", "purple_hov": "#8b5cf6",
        "up_clr": "#9aa1ad",
        "action_bg": "#e8ecf3", "action_hover": "#d8dee8",
        "action_active": "#059669",
        "btn_start": "#059669", "btn_start_hov": "#047857",
        "btn_cancel": "#dc2626", "btn_cancel_hov": "#b91c1c",
        "entry_bg": "#ffffff", "entry_border": "#cbd5e1",
    },
}


# ============ ЛОКАЛИЗАЦИЯ ============
UI_LANGS = {
    'en': 'English', 'ru': 'Русский', 'de': 'Deutsch', 'fr': 'Français',
    'es': 'Español', 'it': 'Italiano', 'pt': 'Português', 'nl': 'Nederlands',
    'pl': 'Polski', 'tr': 'Türkçe', 'cs': 'Čeština', 'hu': 'Magyar',
    'ro': 'Română', 'uk': 'Українська', 'sv': 'Svenska', 'fi': 'Suomi',
    'ja': '日本語', 'ko': '한국어', 'zh': '中文', 'ar': 'العربية'
}


def _mk(ru, en, **kw):
    d = {'ru': ru, 'en': en}
    d.update(kw)
    return d


UI_TR = {
    'Погода': _mk('Погода', 'Weather',
        de='Wetter', fr='Météo', es='Clima', it='Meteo', pt='Clima',
        nl='Weer', pl='Pogoda', tr='Hava durumu', cs='Počasí',
        hu='Időjárás', ro='Vreme', uk='Погода', sv='Väder', fi='Sää',
        ja='天気', ko='날씨', zh='天气', ar='الطقس'),
    'Погода в трее': _mk('Погода в трее', 'Weather Tray',
        de='Wetter im Infobereich', fr='Météo dans la barre',
        es='Clima en bandeja', it='Meteo nel vassoio',
        pt='Clima na bandeja', nl='Weer in systeemvak',
        pl='Pogoda w zasobniku', tr='Tepsi hava durumu',
        cs='Počasí v oznamovací oblasti', hu='Időjárás a tálcán',
        ro='Vreme în tavă', uk='Погода в треї',
        sv='Väder i aktivitetsfältet', fi='Sää ilmaisinalueella',
        ja='トレイ天気', ko='트레이 날씨', zh='托盘天气', ar='طقس شريط النظام'),
    'Настройки': _mk('Настройки', 'Settings',
        de='Einstellungen', fr='Paramètres', es='Configuración',
        it='Impostazioni', pt='Definições', nl='Instellingen',
        pl='Ustawienia', tr='Ayarlar', cs='Nastavení', hu='Beállítások',
        ro='Setări', uk='Налаштування', sv='Inställningar', fi='Asetukset',
        ja='設定', ko='설정', zh='设置', ar='الإعدادات'),
    'Журнал': _mk('Журнал', 'Log',
        de='Protokoll', fr='Journal', es='Registro', it='Registro',
        pt='Registo', nl='Logboek', pl='Dziennik', tr='Günlük',
        cs='Protokol', hu='Napló', ro='Jurnal', uk='Журнал',
        sv='Logg', fi='Loki', ja='ログ', ko='로그', zh='日志', ar='السجل'),
    'Выход': _mk('Выход', 'Exit',
        de='Beenden', fr='Quitter', es='Salir', it='Esci',
        pt='Sair', nl='Afsluiten', pl='Wyjście', tr='Çıkış',
        cs='Konec', hu='Kilépés', ro='Ieșire', uk='Вихід',
        sv='Avsluta', fi='Poistu',
        ja='終了', ko='종료', zh='退出', ar='خروج'),
    'Закрыть': _mk('Закрыть', 'Close',
        de='Schließen', fr='Fermer', es='Cerrar', it='Chiudi',
        pt='Fechar', nl='Sluiten', pl='Zamknij', tr='Kapat',
        cs='Zavřít', hu='Bezárás', ro='Închide', uk='Закрити',
        sv='Stäng', fi='Sulje', ja='閉じる', ko='닫기', zh='关闭', ar='إغلاق'),
    'Отмена': _mk('Отмена', 'Cancel',
        de='Abbrechen', fr='Annuler', es='Cancelar', it='Annulla',
        pt='Cancelar', nl='Annuleren', pl='Anuluj', tr='İptal',
        cs='Zrušit', hu='Mégse', ro='Anulare', uk='Скасувати',
        sv='Avbryt', fi='Peruuta', ja='キャンセル', ko='취소', zh='取消', ar='إلغاء'),
    'Сохранить': _mk('Сохранить', 'Save',
        de='Speichern', fr='Enregistrer', es='Guardar', it='Salva',
        pt='Guardar', nl='Opslaan', pl='Zapisz', tr='Kaydet',
        cs='Uložit', hu='Mentés', ro='Salvează', uk='Зберегти',
        sv='Spara', fi='Tallenna', ja='保存', ko='저장', zh='保存', ar='حفظ'),
    'Понятно': _mk('Понятно', 'OK',
        de='Verstanden', fr='OK', es='Entendido', it='OK',
        pt='OK', nl='Begrepen', pl='OK', tr='Tamam', cs='OK',
        hu='Rendben', ro='OK', uk='Зрозуміло', sv='OK', fi='OK',
        ja='了解', ko='확인', zh='好的', ar='حسنًا'),
    'Обновить': _mk('Обновить', 'Refresh',
        de='Aktualisieren', fr='Actualiser', es='Actualizar',
        it='Aggiorna', pt='Atualizar', nl='Vernieuwen',
        pl='Odśwież', tr='Yenile', cs='Obnovit', hu='Frissítés',
        ro='Reîmprospătează', uk='Оновити', sv='Uppdatera', fi='Päivitä',
        ja='更新', ko='새로고침', zh='刷新', ar='تحديث'),
    'Ошибка': _mk('Ошибка', 'Error',
        de='Fehler', fr='Erreur', es='Error', it='Errore',
        pt='Erro', nl='Fout', pl='Błąd', tr='Hata', cs='Chyba',
        hu='Hiba', ro='Eroare', uk='Помилка', sv='Fel', fi='Virhe',
        ja='エラー', ko='오류', zh='错误', ar='خطأ'),
    'Свернуть': _mk('Свернуть', 'Minimize',
        de='Minimieren', fr='Réduire', es='Minimizar', it='Riduci',
        pt='Minimizar', nl='Minimaliseren', pl='Zwiń', tr='Küçült',
        cs='Minimalizovat', hu='Kicsinyítés', ro='Minimizează',
        uk='Згорнути', sv='Minimera', fi='Pienennä',
        ja='最小化', ko='최소화', zh='最小化', ar='تصغير'),
    'Прогноз:': _mk('Прогноз:', 'Forecast:',
        de='Vorhersage:', fr='Prévisions :', es='Pronóstico:',
        it='Previsioni:', pt='Previsão:', nl='Verwachting:',
        pl='Prognoza:', tr='Tahmin:', cs='Předpověď:',
        hu='Előrejelzés:', ro='Prognoză:', uk='Прогноз:',
        sv='Prognos:', fi='Ennuste:',
        ja='予報：', ko='예보:', zh='预报：', ar='التوقعات:'),
    '💨 Ветер': _mk('💨 Ветер', '💨 Wind',
        de='💨 Wind', fr='💨 Vent', es='💨 Viento', it='💨 Vento',
        pt='💨 Vento', nl='💨 Wind', pl='💨 Wiatr', tr='💨 Rüzgar',
        cs='💨 Vítr', hu='💨 Szél', ro='💨 Vânt', uk='💨 Вітер',
        sv='💨 Vind', fi='💨 Tuuli',
        ja='💨 風', ko='💨 바람', zh='💨 风', ar='💨 الرياح'),
    '💧 Влажность': _mk('💧 Влажность', '💧 Humidity',
        de='💧 Luftfeuchtigkeit', fr='💧 Humidité', es='💧 Humedad',
        it='💧 Umidità', pt='💧 Humidade', nl='💧 Vochtigheid',
        pl='💧 Wilgotność', tr='💧 Nem', cs='💧 Vlhkost',
        hu='💧 Páratartalom', ro='💧 Umiditate', uk='💧 Вологість',
        sv='💧 Luftfuktighet', fi='💧 Kosteus',
        ja='💧 湿度', ko='💧 습도', zh='💧 湿度', ar='💧 الرطوبة'),
    '📊 Давление': _mk('📊 Давление', '📊 Pressure',
        de='📊 Druck', fr='📊 Pression', es='📊 Presión',
        it='📊 Pressione', pt='📊 Pressão', nl='📊 Druk',
        pl='📊 Ciśnienie', tr='📊 Basınç', cs='📊 Tlak',
        hu='📊 Légnyomás', ro='📊 Presiune', uk='📊 Тиск',
        sv='📊 Tryck', fi='📊 Paine',
        ja='📊 気圧', ko='📊 기압', zh='📊 气压', ar='📊 الضغط'),
    '☁ Облачность': _mk('☁ Облачность', '☁ Cloudiness',
        de='☁ Bewölkung', fr='☁ Nébulosité', es='☁ Nubosidad',
        it='☁ Nuvolosità', pt='☁ Nebulosidade', nl='☁ Bewolking',
        pl='☁ Zachmurzenie', tr='☁ Bulutluluk', cs='☁ Oblačnost',
        hu='☁ Felhőzet', ro='☁ Nori', uk='☁ Хмарність',
        sv='☁ Molnighet', fi='☁ Pilvisyys',
        ja='☁ 雲量', ko='☁ 구름', zh='☁ 云量', ar='☁ الغيوم'),
    'Загрузка…': _mk('Загрузка…', 'Loading…',
        de='Wird geladen…', fr='Chargement…', es='Cargando…',
        it='Caricamento…', pt='A carregar…', nl='Laden…',
        pl='Ładowanie…', tr='Yükleniyor…', cs='Načítání…',
        hu='Betöltés…', ro='Se încarcă…', uk='Завантаження…',
        sv='Laddar…', fi='Ladataan…',
        ja='読み込み中…', ko='로딩 중…', zh='加载中…', ar='جارٍ التحميل…'),
    'Обновление…': _mk('Обновление…', 'Refreshing…',
        de='Aktualisierung…', fr='Actualisation…', es='Actualizando…',
        it='Aggiornamento…', pt='A atualizar…', nl='Vernieuwen…',
        pl='Odświeżanie…', tr='Yenileniyor…', cs='Obnovování…',
        hu='Frissítés…', ro='Se actualizează…', uk='Оновлення…',
        sv='Uppdaterar…', fi='Päivitetään…',
        ja='更新中…', ko='새로고침 중…', zh='刷新中…', ar='جارٍ التحديث…'),
    'Укажите город в настройках': _mk(
        'Укажите город в настройках', 'Set the city in settings',
        de='Stadt in den Einstellungen festlegen',
        fr='Définissez la ville dans les paramètres',
        es='Configure la ciudad en ajustes',
        it='Imposta la città nelle impostazioni',
        pt='Defina a cidade nas definições',
        nl='Stel de stad in bij instellingen',
        pl='Ustaw miasto w ustawieniach',
        tr='Şehri ayarlardan belirleyin',
        cs='Nastavte město v nastavení',
        hu='Állítsa be a várost a beállításokban',
        ro='Setați orașul în setări',
        uk='Вкажіть місто в налаштуваннях',
        sv='Ange staden i inställningarna',
        fi='Aseta kaupunki asetuksissa',
        ja='設定で都市を指定してください',
        ko='설정에서 도시를 지정하세요',
        zh='在设置中指定城市', ar='حدد المدينة في الإعدادات'),
    'Сегодня': _mk('Сегодня', 'Today',
        de='Heute', fr="Aujourd'hui", es='Hoy', it='Oggi',
        pt='Hoje', nl='Vandaag', pl='Dziś', tr='Bugün', cs='Dnes',
        hu='Ma', ro='Astăzi', uk='Сьогодні', sv='Idag', fi='Tänään',
        ja='今日', ko='오늘', zh='今天', ar='اليوم'),
    'Завтра': _mk('Завтра', 'Tomorrow',
        de='Morgen', fr='Demain', es='Mañana', it='Domani',
        pt='Amanhã', nl='Morgen', pl='Jutro', tr='Yarın', cs='Zítra',
        hu='Holnap', ro='Mâine', uk='Завтра', sv='Imorgon', fi='Huomenna',
        ja='明日', ko='내일', zh='明天', ar='غدًا'),
    'м/с': _mk('м/с', 'm/s',
        de='m/s', fr='m/s', es='m/s', it='m/s', pt='m/s', nl='m/s',
        pl='m/s', tr='m/s', cs='m/s', hu='m/s', ro='m/s', uk='м/с',
        sv='m/s', fi='m/s', ja='m/s', ko='m/s', zh='m/s', ar='م/ث'),
    'мм': _mk('мм', 'mm',
        de='mm', fr='mm', es='mm', it='mm', pt='mm', nl='mm',
        pl='mm', tr='mm', cs='mm', hu='mm', ro='mm', uk='мм',
        sv='mm', fi='mm', ja='mm', ko='mm', zh='мм', ar='مم'),
    'мм рт.ст.': _mk('мм рт.ст.', 'mmHg',
        de='mmHg', fr='mmHg', es='mmHg', it='mmHg', pt='mmHg', nl='mmHg',
        pl='mmHg', tr='mmHg', cs='mmHg', hu='Hgmm', ro='mmHg',
        uk='мм рт.ст.', sv='mmHg', fi='mmHg',
        ja='mmHg', ko='mmHg', zh='毫米汞柱', ar='ملم زئبق'),
    'Показать окно': _mk('Показать окно', 'Show window',
        de='Fenster anzeigen', fr='Afficher la fenêtre',
        es='Mostrar ventana', it='Mostra finestra',
        pt='Mostrar janela', nl='Venster tonen',
        pl='Pokaż okno', tr='Pencereyi göster', cs='Zobrazit okno',
        hu='Ablak megjelenítése', ro='Arată fereastra', uk='Показати вікно',
        sv='Visa fönster', fi='Näytä ikkuna',
        ja='ウィンドウを表示', ko='창 표시', zh='显示窗口', ar='إظهار النافذة'),
    'Ветер:': _mk('Ветер:', 'Wind:',
        de='Wind:', fr='Vent :', es='Viento:', it='Vento:',
        pt='Vento:', nl='Wind:', pl='Wiatr:', tr='Rüzgar:',
        cs='Vítr:', hu='Szél:', ro='Vânt:', uk='Вітер:',
        sv='Vind:', fi='Tuuli:', ja='風：', ko='바람:', zh='风：', ar='الرياح:'),
    'Влажность:': _mk('Влажность:', 'Humidity:',
        de='Luftfeuchtigkeit:', fr='Humidité :', es='Humedad:',
        it='Umidità:', pt='Humidade:', nl='Vochtigheid:',
        pl='Wilgotność:', tr='Nem:', cs='Vlhkost:',
        hu='Páratartalom:', ro='Umiditate:', uk='Вологість:',
        sv='Luftfuktighet:', fi='Kosteus:',
        ja='湿度：', ko='습도:', zh='湿度：', ar='الرطوبة:'),
    'Давление:': _mk('Давление:', 'Pressure:',
        de='Druck:', fr='Pression :', es='Presión:',
        it='Pressione:', pt='Pressão:', nl='Druk:',
        pl='Ciśnienie:', tr='Basınç:', cs='Tlak:',
        hu='Légnyomás:', ro='Presiune:', uk='Тиск:',
        sv='Tryck:', fi='Paine:', ja='気圧：', ko='기압:', zh='气压：', ar='الضغط:'),
    'Облачность:': _mk('Облачность:', 'Cloudiness:',
        de='Bewölkung:', fr='Nébulosité :', es='Nubosidad:',
        it='Nuvolosità:', pt='Nebulosidade:', nl='Bewolking:',
        pl='Zachmurzenie:', tr='Bulutluluk:', cs='Oblačnost:',
        hu='Felhőzet:', ro='Nori:', uk='Хмарність:',
        sv='Molnighet:', fi='Pilvisyys:',
        ja='雲量：', ko='구름:', zh='云量：', ar='الغيوم:'),
    'Завтра:': _mk('Завтра:', 'Tomorrow:',
        de='Morgen:', fr='Demain :', es='Mañana:', it='Domani:',
        pt='Amanhã:', nl='Morgen:', pl='Jutro:', tr='Yarın:',
        cs='Zítra:', hu='Holnap:', ro='Mâine:', uk='Завтра:',
        sv='Imorgon:', fi='Huomenna:',
        ja='明日：', ko='내일:', zh='明天：', ar='غدًا:'),
    'Обновлено в': _mk('Обновлено в', 'Updated at',
        de='Aktualisiert um', fr='Mis à jour à', es='Actualizado a las',
        it='Aggiornato alle', pt='Atualizado às', nl='Bijgewerkt om',
        pl='Zaktualizowano o', tr='Güncellendi:', cs='Aktualizováno v',
        hu='Frissítve:', ro='Actualizat la', uk='Оновлено о',
        sv='Uppdaterad kl.', fi='Päivitetty klo',
        ja='更新：', ko='업데이트:', zh='更新时间：', ar='تم التحديث في'),
    'Город': _mk('Город', 'City',
        de='Stadt', fr='Ville', es='Ciudad', it='Città',
        pt='Cidade', nl='Stad', pl='Miasto', tr='Şehir',
        cs='Město', hu='Város', ro='Oraș', uk='Місто',
        sv='Stad', fi='Kaupunki',
        ja='都市', ko='도시', zh='城市', ar='المدينة'),
    'Поиск города': _mk('Поиск города', 'Search city',
        de='Stadt suchen', fr='Rechercher une ville',
        es='Buscar ciudad', it='Cerca città',
        pt='Procurar cidade', nl='Stad zoeken',
        pl='Szukaj miasta', tr='Şehir ara',
        cs='Hledat město', hu='Város keresése',
        ro='Caută oraș', uk='Пошук міста',
        sv='Sök stad', fi='Etsi kaupunki',
        ja='都市を検索', ko='도시 검색',
        zh='搜索城市', ar='البحث عن مدينة'),
    'Введите название на любом языке': _mk(
        'Введите название на любом языке', 'Type a name in any language',
        de='Namen in beliebiger Sprache eingeben',
        fr='Saisissez un nom dans n’importe quelle langue',
        es='Escriba un nombre en cualquier idioma',
        it='Inserisci un nome in qualsiasi lingua',
        pt='Introduza um nome em qualquer idioma',
        nl='Voer een naam in een willekeurige taal in',
        pl='Wpisz nazwę w dowolnym języku',
        tr='Herhangi bir dilde ad girin',
        cs='Zadejte název v libovolném jazyce',
        hu='Adjon meg egy nevet bármilyen nyelven',
        ro='Introduceți un nume în orice limbă',
        uk='Введіть назву будь-якою мовою',
        sv='Ange ett namn på valfritt språk',
        fi='Kirjoita nimi millä tahansa kielellä',
        ja='任意の言語で名前を入力',
        ko='아무 언어로 이름을 입력하세요',
        zh='用任何语言输入名称', ar='اكتب اسمًا بأي لغة'),
    'Текущий город:': _mk('Текущий город:', 'Current city:',
        de='Aktuelle Stadt:', fr='Ville actuelle :',
        es='Ciudad actual:', it='Città attuale:',
        pt='Cidade atual:', nl='Huidige stad:',
        pl='Aktualne miasto:', tr='Geçerli şehir:',
        cs='Aktuální město:', hu='Jelenlegi város:',
        ro='Orașul curent:', uk='Поточне місто:',
        sv='Aktuell stad:', fi='Nykyinen kaupunki:',
        ja='現在の都市：', ko='현재 도시:',
        zh='当前城市：', ar='المدينة الحالية:'),
    'Не задан': _mk('Не задан', 'Not set',
        de='Nicht festgelegt', fr='Non défini', es='No definido',
        it='Non impostato', pt='Não definido', nl='Niet ingesteld',
        pl='Nie ustawiono', tr='Ayarlanmadı', cs='Nenastaveno',
        hu='Nincs beállítva', ro='Nesetat', uk='Не задано',
        sv='Inte angiven', fi='Ei asetettu',
        ja='未設定', ko='설정되지 않음', zh='未设置', ar='غير محدد'),
    'Обновлять каждые (минут)': _mk('Обновлять каждые (минут)',
        'Update every (minutes)',
        de='Aktualisieren alle (Minuten)', fr='Actualiser toutes les (minutes)',
        es='Actualizar cada (minutos)', it='Aggiorna ogni (minuti)',
        pt='Atualizar a cada (minutos)', nl='Elke (minuten) vernieuwen',
        pl='Odświeżaj co (minuty)', tr='Her (dakika) güncelle',
        cs='Aktualizovat každých (minut)', hu='Frissítés (perc)',
        ro='Actualizează la fiecare (minute)',
        uk='Оновлювати кожні (хвилин)',
        sv='Uppdatera var (minut)', fi='Päivitä (minuutin) välein',
        ja='更新間隔（分）', ko='업데이트 간격(분)',
        zh='更新间隔（分钟）', ar='التحديث كل (دقيقة)'),
    'Уведомлять о дожде за час': _mk('Уведомлять о дожде за час',
        'Notify about rain an hour ahead',
        de='Eine Stunde vorher über Regen benachrichtigen',
        fr="Notifier la pluie une heure à l'avance",
        es='Notificar lluvia una hora antes',
        it='Notifica pioggia un\'ora prima',
        pt='Notificar chuva uma hora antes',
        nl='Een uur van tevoren regen melden',
        pl='Powiadom o deszczu godzinę wcześniej',
        tr='Bir saat önce yağmur bildir',
        cs='Upozornit na déšť hodinu předem',
        hu='Értesítés esőről egy órával előbb',
        ro='Notifică ploaia cu o oră înainte',
        uk='Повідомляти про дощ за годину',
        sv='Meddela om regn en timme i förväg',
        fi='Ilmoita sateesta tuntia aiemmin',
        ja='1時間前に雨を通知', ko='한 시간 전 비 알림',
        zh='提前一小时通知下雨', ar='إشعار بالمطر قبل ساعة'),
    'Определить город по IP': _mk('Определить город по IP', 'Detect city by IP',
        de='Stadt per IP ermitteln', fr="Détecter la ville par IP",
        es='Detectar ciudad por IP', it='Rileva città tramite IP',
        pt='Detetar cidade por IP', nl='Stad detecteren via IP',
        pl='Wykryj miasto przez IP', tr="IP ile şehir bul",
        cs='Zjistit město podle IP', hu='Város meghatározása IP alapján',
        ro='Detectează orașul după IP', uk='Визначити місто за IP',
        sv='Identifiera stad via IP', fi='Tunnista kaupunki IP:llä',
        ja='IPで都市を検出', ko='IP로 도시 감지',
        zh='根据 IP 检测城市', ar='تحديد المدينة عبر IP'),
    'Город не найден.': _mk('Город не найден.', 'City not found.',
        de='Stadt nicht gefunden.', fr='Ville introuvable.',
        es='Ciudad no encontrada.', it='Città non trovata.',
        pt='Cidade não encontrada.', nl='Stad niet gevonden.',
        pl='Miasto nie znalezione.', tr='Şehir bulunamadı.',
        cs='Město nenalezeno.', hu='A város nem található.',
        ro='Orașul nu a fost găsit.', uk='Місто не знайдено.',
        sv='Staden hittades inte.', fi='Kaupunkia ei löytynyt.',
        ja='都市が見つかりません。', ko='도시를 찾을 수 없습니다.',
        zh='未找到城市。', ar='لم يتم العثور على المدينة.'),
    'Введите название города.': _mk('Введите название города.',
        'Enter a city name.',
        de='Geben Sie einen Stadtnamen ein.',
        fr='Saisissez un nom de ville.',
        es='Introduzca un nombre de ciudad.',
        it='Inserisci il nome di una città.',
        pt='Introduza o nome de uma cidade.',
        nl='Voer een stadsnaam in.',
        pl='Wpisz nazwę miasta.',
        tr='Bir şehir adı girin.',
        cs='Zadejte název města.',
        hu='Adjon meg egy városnevet.',
        ro='Introduceți numele unui oraș.',
        uk='Введіть назву міста.',
        sv='Ange ett stadsnamn.',
        fi='Anna kaupungin nimi.',
        ja='都市名を入力してください。',
        ko='도시 이름을 입력하세요.',
        zh='请输入城市名称。', ar='أدخل اسم مدينة.'),
    'Не удалось определить город:': _mk('Не удалось определить город:',
        'Failed to detect city:',
        de='Stadt konnte nicht ermittelt werden:',
        fr='Impossible de détecter la ville :',
        es='No se pudo detectar la ciudad:',
        it='Impossibile rilevare la città:',
        pt='Falha ao detetar a cidade:',
        nl='Kan stad niet detecteren:',
        pl='Nie udało się wykryć miasta:',
        tr='Şehir belirlenemedi:',
        cs='Nepodařilo se zjistit město:',
        hu='Nem sikerült meghatározni a várost:',
        ro='Nu s-a putut detecta orașul:',
        uk='Не вдалося визначити місто:',
        sv='Kunde inte identifiera staden:',
        fi='Kaupunkia ei voitu tunnistaa:',
        ja='都市を検出できませんでした：',
        ko='도시를 감지하지 못했습니다:',
        zh='无法检测城市：', ar='فشل تحديد المدينة:'),
    'Не удалось получить погоду:': _mk('Не удалось получить погоду:',
        'Failed to get weather:',
        de='Wetter konnte nicht abgerufen werden:',
        fr='Impossible de récupérer la météo :',
        es='No se pudo obtener el clima:',
        it='Impossibile ottenere il meteo:',
        pt='Falha ao obter o clima:',
        nl='Kan weer niet ophalen:',
        pl='Nie udało się pobrać pogody:',
        tr='Hava durumu alınamadı:',
        cs='Nepodařilo se získat počasí:',
        hu='Nem sikerült lekérni az időjárást:',
        ro='Nu s-a putut obține vremea:',
        uk='Не вдалося отримати погоду:',
        sv='Kunde inte hämta vädret:',
        fi='Säätä ei voitu hakea:',
        ja='天気を取得できませんでした：',
        ko='날씨를 가져오지 못했습니다:',
        zh='无法获取天气：', ar='فشل جلب الطقس:'),
    'Скоро дождь!': _mk('Скоро дождь!', 'Rain soon!',
        de='Bald Regen!', fr='Pluie bientôt !', es='¡Lluvia pronto!',
        it='Pioggia in arrivo!', pt='Chuva em breve!',
        nl='Regen op komst!', pl='Wkrótce deszcz!',
        tr='Yakında yağmur!', cs='Brzy déšť!',
        hu='Hamarosan eső!', ro='Ploaie în curând!',
        uk='Скоро дощ!', sv='Regn snart!', fi='Sadetta pian!',
        ja='まもなく雨！', ko='곧 비!', zh='即将下雨！', ar='المطر قريبًا!'),
    'в течение часа': _mk('в течение часа', 'within an hour',
        de='innerhalb einer Stunde', fr='dans une heure',
        es='en una hora', it="entro un'ora",
        pt='dentro de uma hora', nl='binnen een uur',
        pl='w ciągu godziny', tr='bir saat içinde',
        cs='do hodiny', hu='egy órán belül',
        ro='într-o oră', uk='протягом години',
        sv='inom en timme', fi='tunnin sisällä',
        ja='1時間以内', ko='한 시간 이내', zh='一小时内', ar='خلال ساعة'),
    'Переключить на светлую тему': _mk('Переключить на светлую тему',
        'Switch to light theme',
        de='Zum hellen Design wechseln', fr='Passer au thème clair',
        es='Cambiar al tema claro', it='Passa al tema chiaro',
        pt='Mudar para tema claro', nl='Naar licht thema schakelen',
        pl='Przełącz na jasny motyw', tr='Açık temaya geç',
        cs='Přepnout na světlé téma', hu='Váltás világos témára',
        ro='Comută pe tema deschisă', uk='Перемкнути на світлу тему',
        sv='Byt till ljust tema', fi='Vaihda vaaleaan teemaan',
        ja='ライトテーマに切り替え', ko='라이트 테마로 전환',
        zh='切换到浅色主题', ar='التبديل إلى السمة الفاتحة'),
    'Переключить на тёмную тему': _mk('Переключить на тёмную тему',
        'Switch to dark theme',
        de='Zum dunklen Design wechseln', fr='Passer au thème sombre',
        es='Cambiar al tema oscuro', it='Passa al tema scuro',
        pt='Mudar para tema escuro', nl='Naar donker thema schakelen',
        pl='Przełącz na ciemny motyw', tr='Koyu temaya geç',
        cs='Přepnout na tmavé téma', hu='Váltás sötét témára',
        ro='Comută pe tema închisă', uk='Перемкнути на темну тему',
        sv='Byt till mörkt tema', fi='Vaihda tummaan teemaan',
        ja='ダークテーマに切り替え', ko='다크 테마로 전환',
        zh='切换到深色主题', ar='التبديل إلى السمة الداكنة'),
    'Сменить язык интерфейса': _mk('Сменить язык интерфейса',
        'Change interface language',
        de='Sprache der Oberfläche ändern',
        fr="Changer la langue de l'interface",
        es='Cambiar el idioma de la interfaz',
        it="Cambia la lingua dell'interfaccia",
        pt='Alterar o idioma da interface',
        nl='Interfacetaal wijzigen', pl='Zmień język interfejsu',
        tr='Arayüz dilini değiştir', cs='Změnit jazyk rozhraní',
        hu='Felület nyelvének módosítása',
        ro='Schimbă limba interfeței',
        uk='Змінити мову інтерфейсу',
        sv='Byt gränssnittsspråk',
        fi='Vaihda käyttöliittymän kieli',
        ja='インターフェース言語を変更',
        ko='인터페이스 언어 변경',
        zh='更改界面语言', ar='تغيير لغة الواجهة'),

    # ---- Погодные описания ----
    'w_nodata': _mk('Нет данных', 'No data',
        de='Keine Daten', fr='Pas de données', es='Sin datos',
        it='Nessun dato', pt='Sem dados', nl='Geen gegevens',
        pl='Brak danych', tr='Veri yok', cs='Žádná data',
        hu='Nincs adat', ro='Fără date', uk='Немає даних',
        sv='Inga data', fi='Ei tietoja',
        ja='データなし', ko='데이터 없음', zh='无数据', ar='لا توجد بيانات'),
    'w_clearsky': _mk('Ясно', 'Clear sky',
        de='Klarer Himmel', fr='Ciel dégagé', es='Cielo despejado',
        it='Cielo sereno', pt='Céu limpo', nl='Heldere lucht',
        pl='Bezchmurnie', tr='Açık', cs='Jasno', hu='Derült',
        ro='Cer senin', uk='Ясно', sv='Klart', fi='Selkeää',
        ja='快晴', ko='맑음', zh='晴朗', ar='سماء صافية'),
    'w_fair': _mk('Малооблачно', 'Fair',
        de='Heiter', fr='Peu nuageux', es='Poco nuboso',
        it='Poco nuvoloso', pt='Pouco nublado', nl='Licht bewolkt',
        pl='Prawie bezchmurnie', tr='Az bulutlu', cs='Skoro jasno',
        hu='Kissé felhős', ro='Aproape senin', uk='Майже ясно',
        sv='Nästan klart', fi='Melkein selkeää',
        ja='晴れ', ko='구름 조금', zh='晴', ar='صحو'),
    'w_partlycloudy': _mk('Переменная облачность', 'Partly cloudy',
        de='Teilweise bewölkt', fr='Partiellement nuageux',
        es='Parcialmente nublado', it='Parzialmente nuvoloso',
        pt='Parcialmente nublado', nl='Gedeeltelijk bewolkt',
        pl='Częściowo pochmurno', tr='Parçalı bulutlu',
        cs='Polojasno', hu='Részben felhős', ro='Parțial noros',
        uk='Мінлива хмарність', sv='Delvis molnigt', fi='Osittain pilvistä',
        ja='晴れ時々曇り', ko='구름 조금', zh='局部多云', ar='غائم جزئيًا'),
    'w_cloudy': _mk('Облачно', 'Cloudy',
        de='Bewölkt', fr='Nuageux', es='Nublado', it='Nuvoloso',
        pt='Nublado', nl='Bewolkt', pl='Pochmurno', tr='Bulutlu',
        cs='Zataženo', hu='Felhős', ro='Noros', uk='Хмарно',
        sv='Mulet', fi='Pilvistä',
        ja='曇り', ko='흐림', zh='多云', ar='غائم'),
    'w_fog': _mk('Туман', 'Fog',
        de='Nebel', fr='Brouillard', es='Niebla', it='Nebbia',
        pt='Nevoeiro', nl='Mist', pl='Mgła', tr='Sis',
        cs='Mlha', hu='Köd', ro='Ceață', uk='Туман',
        sv='Dimma', fi='Sumua',
        ja='霧', ko='안개', zh='雾', ar='ضباب'),
    'w_lightrain': _mk('Небольшой дождь', 'Light rain',
        de='Leichter Regen', fr='Pluie légère', es='Lluvia ligera',
        it='Pioggia leggera', pt='Chuva fraca', nl='Lichte regen',
        pl='Lekki deszcz', tr='Hafif yağmur', cs='Slabý déšť',
        hu='Enyhe eső', ro='Ploaie slabă', uk='Невеликий дощ',
        sv='Lätt regn', fi='Kevyttä sadetta',
        ja='小雨', ko='약한 비', zh='小雨', ar='مطر خفيف'),
    'w_rain': _mk('Дождь', 'Rain',
        de='Regen', fr='Pluie', es='Lluvia', it='Pioggia',
        pt='Chuva', nl='Regen', pl='Deszcz', tr='Yağmur',
        cs='Déšť', hu='Eső', ro='Ploaie', uk='Дощ',
        sv='Regn', fi='Sadetta',
        ja='雨', ko='비', zh='雨', ar='مطر'),
    'w_heavyrain': _mk('Сильный дождь', 'Heavy rain',
        de='Starker Regen', fr='Forte pluie', es='Lluvia intensa',
        it='Pioggia intensa', pt='Chuva forte', nl='Zware regen',
        pl='Silny deszcz', tr='Şiddetli yağmur', cs='Silný déšť',
        hu='Heves eső', ro='Ploaie puternică', uk='Сильний дощ',
        sv='Kraftigt regn', fi='Voimakasta sadetta',
        ja='大雨', ko='강한 비', zh='大雨', ar='مطر غزير'),
    'w_lightrainshowers': _mk('Небольшой ливень', 'Light rain showers',
        de='Leichte Regenschauer', fr='Averses légères',
        es='Chubascos ligeros', it='Rovesci leggeri',
        pt='Aguaceiros leves', nl='Lichte regenbuien',
        pl='Lekkie przelotne opady', tr='Hafif sağanak',
        cs='Slabé přeháňky', hu='Enyhe záporeső',
        ro='Averse slabe', uk='Невеликі зливи',
        sv='Lätta regnskurar', fi='Heikkoja sadekuuroja',
        ja='小雨のにわか雨', ko='약한 소나기', zh='小阵雨', ar='زخات مطر خفيفة'),
    'w_rainshowers': _mk('Ливень', 'Rain showers',
        de='Regenschauer', fr='Averses', es='Chubascos',
        it='Rovesci', pt='Aguaceiros', nl='Regenbuien',
        pl='Przelotne opady', tr='Sağanak', cs='Přeháňky',
        hu='Záporeső', ro='Averse', uk='Зливи',
        sv='Regnskurar', fi='Sadekuuroja',
        ja='にわか雨', ko='소나기', zh='阵雨', ar='زخات مطر'),
    'w_heavyrainshowers': _mk('Сильный ливень', 'Heavy rain showers',
        de='Starke Regenschauer', fr='Fortes averses',
        es='Chubascos fuertes', it='Rovesci intensi',
        pt='Aguaceiros fortes', nl='Zware regenbuien',
        pl='Silne przelotne opady', tr='Şiddetli sağanak',
        cs='Silné přeháňky', hu='Heves záporeső',
        ro='Averse puternice', uk='Сильні зливи',
        sv='Kraftiga regnskurar', fi='Voimakkaita sadekuuroja',
        ja='強いにわか雨', ko='강한 소나기', zh='强阵雨', ar='زخات مطر غزيرة'),
    'w_lightsleet': _mk('Небольшой дождь со снегом', 'Light sleet',
        de='Leichter Schneeregen', fr='Légère pluie verglaçante',
        es='Aguanieve ligera', it='Nevischio leggero',
        pt='Chuva com neve leve', nl='Lichte natte sneeuw',
        pl='Lekka śnieg z deszczem', tr='Hafif sulu kar',
        cs='Slabý déšť se sněhem', hu='Enyhe havas eső',
        ro='Ploaie cu zăpadă slabă', uk='Невеликий дощ зі снігом',
        sv='Lätt snöblandat regn', fi='Kevyttä räntää',
        ja='小雨と雪', ko='약한 진눈깨비', zh='小雨夹雪', ar='مطر خفيف مع ثلج'),
    'w_sleet': _mk('Дождь со снегом', 'Sleet',
        de='Schneeregen', fr='Grésil', es='Aguanieve',
        it='Nevischio', pt='Chuva com neve', nl='Natte sneeuw',
        pl='Śnieg z deszczem', tr='Sulu kar', cs='Déšť se sněhem',
        hu='Havas eső', ro='Ploaie cu zăpadă', uk='Дощ зі снігом',
        sv='Snöblandat regn', fi='Räntää',
        ja='みぞれ', ko='진눈깨비', zh='雨夹雪', ar='مطر وثلج'),
    'w_heavysleet': _mk('Сильный дождь со снегом', 'Heavy sleet',
        de='Starker Schneeregen', fr='Fort grésil',
        es='Aguanieve fuerte', it='Nevischio intenso',
        pt='Chuva com neve forte', nl='Zware natte sneeuw',
        pl='Silny śnieg z deszczem', tr='Şiddetli sulu kar',
        cs='Silný déšť se sněhem', hu='Heves havas eső',
        ro='Ploaie puternică cu zăpadă', uk='Сильний дощ зі снігом',
        sv='Kraftigt snöblandat regn', fi='Voimakasta räntää',
        ja='強いみぞれ', ko='강한 진눈깨비', zh='强雨夹雪', ar='مطر وثلج غزير'),
    'w_lightsnow': _mk('Небольшой снег', 'Light snow',
        de='Leichter Schnee', fr='Légère neige', es='Nevada ligera',
        it='Neve leggera', pt='Neve fraca', nl='Lichte sneeuw',
        pl='Lekki śnieg', tr='Hafif kar', cs='Slabý sníh',
        hu='Enyhe hó', ro='Zăpadă slabă', uk='Невеликий сніг',
        sv='Lätt snöfall', fi='Kevyttä lunta',
        ja='小雪', ko='약한 눈', zh='小雪', ar='ثلج خفيف'),
    'w_snow': _mk('Снег', 'Snow',
        de='Schnee', fr='Neige', es='Nieve', it='Neve',
        pt='Neve', nl='Sneeuw', pl='Śnieg', tr='Kar',
        cs='Sníh', hu='Hó', ro='Zăpadă', uk='Сніг',
        sv='Snö', fi='Lunta',
        ja='雪', ko='눈', zh='雪', ar='ثلج'),
    'w_heavysnow': _mk('Сильный снег', 'Heavy snow',
        de='Starker Schneefall', fr='Forte neige', es='Nevada fuerte',
        it='Neve intensa', pt='Neve forte', nl='Zware sneeuw',
        pl='Silny śnieg', tr='Yoğun kar', cs='Silný sníh',
        hu='Heves hó', ro='Zăpadă puternică', uk='Сильний сніг',
        sv='Kraftigt snöfall', fi='Voimakasta lunta',
        ja='大雪', ko='폭설', zh='大雪', ar='ثلج كثيف'),
    'w_lightsnowshowers': _mk('Небольшой снегопад', 'Light snow showers',
        de='Leichte Schneeschauer', fr='Légères averses de neige',
        es='Chubascos de nieve ligeros', it='Rovesci di neve leggeri',
        pt='Aguaceiros de neve leves', nl='Lichte sneeuwbuien',
        pl='Lekkie opady śniegu', tr='Hafif kar sağanağı',
        cs='Slabé sněhové přeháňky', hu='Enyhe hózápor',
        ro='Averse slabe de zăpadă', uk='Невеликі снігопади',
        sv='Lätta snöbyar', fi='Heikkoja lumikuuroja',
        ja='小雪のにわか雪', ko='약한 소나기눈', zh='小阵雪', ar='زخات ثلج خفيفة'),
    'w_snowshowers': _mk('Снегопад', 'Snow showers',
        de='Schneeschauer', fr='Averses de neige',
        es='Chubascos de nieve', it='Rovesci di neve',
        pt='Aguaceiros de neve', nl='Sneeuwbuien',
        pl='Opady śniegu', tr='Kar sağanağı',
        cs='Sněhové přeháňky', hu='Hózápor',
        ro='Averse de zăpadă', uk='Снігопади',
        sv='Snöbyar', fi='Lumikuuroja',
        ja='にわか雪', ko='소나기눈', zh='阵雪', ar='زخات ثلج'),
    'w_heavysnowshowers': _mk('Сильный снегопад', 'Heavy snow showers',
        de='Starke Schneeschauer', fr='Fortes averses de neige',
        es='Chubascos de nieve fuertes', it='Rovesci di neve intensi',
        pt='Aguaceiros de neve fortes', nl='Zware sneeuwbuien',
        pl='Silne opady śniegu', tr='Şiddetli kar sağanağı',
        cs='Silné sněhové přeháňky', hu='Heves hózápor',
        ro='Averse puternice de zăpadă', uk='Сильні снігопади',
        sv='Kraftiga snöbyar', fi='Voimakkaita lumikuuroja',
        ja='強いにわか雪', ko='강한 소나기눈', zh='强阵雪', ar='زخات ثلج غزيرة'),
    'w_rainandthunder': _mk('Гроза с дождём', 'Rain and thunder',
        de='Regen und Gewitter', fr='Pluie et orage',
        es='Lluvia y tormenta', it='Pioggia e tuoni',
        pt='Chuva e trovoada', nl='Regen en onweer',
        pl='Deszcz i burza', tr='Yağmur ve gök gürültüsü',
        cs='Déšť a bouřka', hu='Eső és villámlás',
        ro='Ploaie și tunete', uk='Гроза з дощем',
        sv='Regn och åska', fi='Sadetta ja ukkosta',
        ja='雨と雷', ko='비와 천둥', zh='雨和雷', ar='مطر ورعد'),
    'w_sleetandthunder': _mk('Гроза с дождём и снегом', 'Sleet and thunder',
        de='Schneeregen und Gewitter', fr='Grésil et orage',
        es='Aguanieve y tormenta', it='Nevischio e tuoni',
        pt='Chuva com neve e trovoada', nl='Natte sneeuw en onweer',
        pl='Śnieg z deszczem i burza', tr='Sulu kar ve gök gürültüsü',
        cs='Déšť se sněhem a bouřka', hu='Havas eső és villámlás',
        ro='Ploaie cu zăpadă și tunete', uk='Гроза з дощем і снігом',
        sv='Snöblandat regn och åska', fi='Räntää ja ukkosta',
        ja='みぞれと雷', ko='진눈깨비와 천둥', zh='雨夹雪和雷', ar='مطر وثلج ورعد'),
    'w_snowandthunder': _mk('Гроза со снегом', 'Snow and thunder',
        de='Schnee und Gewitter', fr='Neige et orage',
        es='Nieve y tormenta', it='Neve e tuoni',
        pt='Neve e trovoada', nl='Sneeuw en onweer',
        pl='Śnieg i burza', tr='Kar ve gök gürültüsü',
        cs='Sníh a bouřka', hu='Hó és villámlás',
        ro='Zăpadă și tunete', uk='Гроза зі снігом',
        sv='Snö och åska', fi='Lunta ja ukkosta',
        ja='雪と雷', ko='눈과 천둥', zh='雪和雷', ar='ثلج ورعد'),
    'w_lightrainandthunder': _mk('Небольшая гроза', 'Light rain and thunder',
        de='Leichter Regen und Gewitter', fr='Légère pluie et orage',
        es='Lluvia ligera y tormenta', it='Pioggia leggera e tuoni',
        pt='Chuva fraca e trovoada', nl='Lichte regen en onweer',
        pl='Lekki deszcz i burza', tr='Hafif yağmur ve gök gürültüsü',
        cs='Slabý déšť a bouřka', hu='Enyhe eső és villámlás',
        ro='Ploaie slabă și tunete', uk='Невелика гроза',
        sv='Lätt regn och åska', fi='Kevyttä sadetta ja ukkosta',
        ja='小雨と雷', ko='약한 비와 천둥', zh='小雨和雷', ar='مطر خفيف ورعد'),
}


def _tr(key, lang):
    entry = UI_TR.get(key)
    if not entry:
        return key
    return entry.get(lang) or entry.get('en') or entry.get('ru') or key


# ============ Символьные коды ============
SYMBOL_MAP = {
    "clearsky": ("clearsky_day", "w_clearsky"),
    "fair": ("fair_day", "w_fair"),
    "partlycloudy": ("partlycloudy_day", "w_partlycloudy"),
    "cloudy": ("cloudy", "w_cloudy"),
    "fog": ("fog", "w_fog"),
    "lightrain": ("lightrain", "w_lightrain"),
    "rain": ("rain", "w_rain"),
    "heavyrain": ("heavyrain", "w_heavyrain"),
    "lightrainshowers": ("lightrainshowers_day", "w_lightrainshowers"),
    "rainshowers": ("rainshowers_day", "w_rainshowers"),
    "heavyrainshowers": ("heavyrainshowers_day", "w_heavyrainshowers"),
    "lightsleet": ("lightsleet", "w_lightsleet"),
    "sleet": ("sleet", "w_sleet"),
    "heavysleet": ("heavysleet", "w_heavysleet"),
    "lightsnow": ("lightsnow", "w_lightsnow"),
    "snow": ("snow", "w_snow"),
    "heavysnow": ("heavysnow", "w_heavysnow"),
    "lightsnowshowers": ("lightsnowshowers_day", "w_lightsnowshowers"),
    "snowshowers": ("snowshowers_day", "w_snowshowers"),
    "heavysnowshowers": ("heavysnowshowers_day", "w_heavysnowshowers"),
    "rainandthunder": ("rainandthunder", "w_rainandthunder"),
    "sleetandthunder": ("sleetandthunder", "w_sleetandthunder"),
    "snowandthunder": ("snowandthunder", "w_snowandthunder"),
    "lightrainandthunder": ("lightrainandthunder", "w_lightrainandthunder"),
}


def weather_info(code, lang="ru"):
    if not code:
        return (None, _tr("w_nodata", lang))
    base = code.split("_")[0]
    icon_name, key = SYMBOL_MAP.get(base, (None, "w_nodata"))
    if "night" in code and icon_name and icon_name.endswith("_day"):
        icon_name = icon_name.replace("_day", "_night")
    return (icon_name, _tr(key, lang))


def get_icon_path(icon_name):
    if not icon_name:
        return None
    os.makedirs(ICON_CACHE_DIR, exist_ok=True)
    path = os.path.join(ICON_CACHE_DIR, f"{icon_name}.png")
    if os.path.exists(path):
        return path
    try:
        url = f"https://api.met.no/weatherapi/weathericon/2.0/data/{icon_name}.png"
        req = urllib.request.Request(url, headers={
            "User-Agent": "TrayWeather/1.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = resp.read()
        with open(path, "wb") as f:
            f.write(data)
        return path
    except Exception as e:
        log_event(f"Иконка не скачалась: {e}")
        return None


class Tooltip:
    def __init__(self, widget, key, app=None, delay=450):
        self.widget = widget
        self.app = app
        self.key = key
        self.delay = delay
        self.tip = None
        self.after_id = None
        widget.bind("<Enter>", self._on_enter, add="+")
        widget.bind("<Leave>", self._on_leave, add="+")
        widget.bind("<ButtonPress>", self._on_leave, add="+")

    def set_key(self, key):
        self.key = key

    def _get_text(self):
        if self.app is None or self.key is None:
            return ""
        return self.app._t(self.key)

    def refresh(self):
        was_visible = self.tip is not None
        self._cancel()
        self._hide()
        if not was_visible:
            return
        try:
            px, py = self.widget.winfo_pointerxy()
            wx = self.widget.winfo_rootx()
            wy = self.widget.winfo_rooty()
            ww = self.widget.winfo_width()
            wh = self.widget.winfo_height()
            if wx <= px <= wx + ww and wy <= py <= wy + wh:
                self._show()
        except Exception:
            pass

    def _on_enter(self, event=None):
        self._cancel()
        try:
            self.after_id = self.widget.after(self.delay, self._show)
        except Exception:
            pass

    def _on_leave(self, event=None):
        self._cancel()
        self._hide()

    def _cancel(self):
        if self.after_id:
            try:
                self.widget.after_cancel(self.after_id)
            except Exception:
                pass
            self.after_id = None

    def _show(self):
        if self.tip:
            return
        text = self._get_text()
        if not text:
            return
        try:
            x = self.widget.winfo_rootx() + 12
            y = self.widget.winfo_rooty() + self.widget.winfo_height() + 6
        except Exception:
            return
        self.tip = tk.Toplevel(self.widget)
        self.tip.wm_overrideredirect(True)
        self.tip.wm_attributes("-topmost", True)
        self.tip.configure(bg="#e0a030")
        inner = tk.Frame(self.tip, bg="#1a1a1a")
        inner.pack(padx=1, pady=1)
        tk.Label(inner, text=text, bg="#1a1a1a", fg="#ffffff",
                 font=("Segoe UI", 9), justify="left",
                 padx=12, pady=8, wraplength=420).pack()
        self.tip.update_idletasks()
        tw = self.tip.winfo_width()
        th = self.tip.winfo_height()
        sw = self.tip.winfo_screenwidth()
        sh = self.tip.winfo_screenheight()
        if x + tw > sw - 6:
            x = sw - tw - 6
        if x < 6:
            x = 6
        if y + th > sh - 6:
            y = self.widget.winfo_rooty() - th - 6
        self.tip.wm_geometry(f"+{x}+{y}")

    def _hide(self):
        if self.tip:
            try:
                self.tip.destroy()
            except Exception:
                pass
            self.tip = None


def _world_city_search(query):
    q = (query or "").strip()
    if not q:
        return None
    url = "https://geocoding-api.open-meteo.com/v1/search?" + urllib.parse.urlencode({
        "name": q, "count": 8, "language": "en", "format": "json"
    })
    try:
        with urllib.request.urlopen(url, timeout=8) as r:
            data = json.loads(r.read().decode("utf-8"))
        results = data.get("results") or []
        if not results:
            return None
        x = results[0]
        label = x.get("name", q)
        country = x.get("country", "")
        if country:
            label = f"{label}, {country}"
        return label, float(x["latitude"]), float(x["longitude"])
    except Exception as e:
        log_event(f"World geocoding error: {e}")
        return None


class App:
    def __init__(self):
        self.settings = load_settings()
        self._autorun_launch = "--minimized" in sys.argv

        # Тема: если нет — всегда тёмная
        saved_theme = self.settings.get("theme")
        if saved_theme in THEMES:
            self.theme_name = saved_theme
        else:
            self.theme_name = "dark"
        self.T = {}
        self.T.update(THEMES[self.theme_name])

        self._ui_lang = self.settings.get("ui_lang", "en")
        if self._ui_lang not in UI_LANGS:
            self._ui_lang = "en"

        # Город по умолчанию — пусто
        self.city_name = self.settings.get("city_name", "") or ""
        self.lat = self.settings.get("lat", None)
        self.lon = self.settings.get("lon", None)
        try:
            if self.lat is not None:
                self.lat = float(self.lat)
            if self.lon is not None:
                self.lon = float(self.lon)
        except Exception:
            self.lat = None
            self.lon = None

        self.update_interval = int(self.settings.get("update_interval", 30))
        self.forecast_days = int(self.settings.get("forecast_days", 3))
        self.notify_rain = bool(self.settings.get("notify_rain", True))
        self._notified_rain = set()

        self.weather_data = None
        self.forecast_data = []
        self.last_update = 0
        self.tray_icon = None
        self._icon_photo = None
        self._current_icon_photo = None
        self._forecast_photos = []
        self._styled = []
        self._i18n_widgets = []
        self._tooltips = []
        self.stop_flag = False
        self._auto_thread_started = False
        self._warning_dlg = None
        self._settings_dlg = None
        self._settings_current_lbl = None
        self._settings_update_current = None
        self._log_dlg = None
        self._theme_btn = None
        self._lang_btn = None
        self._theme_tooltip = None
        self._lang_tooltip = None
        self._toaster = None

        if TOAST_OK:
            try:
                self._toaster = ToastNotifier()
            except Exception:
                self._toaster = None

        self._base_w = 460
        self._base_h = 680

        self._build_ui()

        self.root.after(200, self._apply_icon)
        self.root.after(500, self._poll_signal)
        self.root.after(1000, self._setup_tray)
        self.root.after(1500, self._start_auto_update)

        log_event("=== Погода запущена ===")
        if not self.city_name:
            log_event("Город не задан — откройте настройки")

    # ============ i18n ============
    def _t(self, key, **fmt):
        text = _tr(key, self._ui_lang)
        if fmt:
            try:
                return text.format(**fmt)
            except Exception:
                return text
        return text

    def _reg_i18n(self, widget, key):
        self._i18n_widgets.append((widget, key))

    def _rebuild_all_texts(self):
        for w, key in self._i18n_widgets:
            try:
                if w.winfo_exists():
                    w.config(text=self._t(key))
            except Exception:
                pass
        try:
            self.root.title(self._t('Погода в трее'))
        except Exception:
            pass

        self._update_city_label()

        try:
            if self.weather_data:
                raw = self.weather_data.get("raw_symbol")
                if raw:
                    _, desc = weather_info(raw, self._ui_lang)
                    self.weather_data["desc"] = desc
                self._render_weather()
        except Exception:
            pass

        # Статус пустого города
        try:
            if not self.city_name:
                self.desc_lbl.config(text=self._t('Укажите город в настройках'))
        except Exception:
            pass

        try:
            if self._theme_tooltip is not None:
                self._theme_tooltip.set_key(self._theme_tooltip_key())
        except Exception:
            pass

        try:
            self._render_forecast()
        except Exception:
            pass

        try:
            if (getattr(self, "_settings_current_lbl", None) is not None
                    and self._settings_current_lbl.winfo_exists()
                    and getattr(self, "_settings_update_current", None)):
                self._settings_update_current()
        except Exception:
            pass

        try:
            if TRAY_AVAILABLE and self.tray_icon is not None:
                self._update_tray()
        except Exception:
            pass



    def _set_ui_lang(self, code):
        if code not in UI_LANGS:
            return
        self._ui_lang = code
        self.settings["ui_lang"] = code
        save_settings(self.settings)
        self._update_lang_button()
        self._rebuild_all_texts()
        self._fit_window()

    def _update_lang_button(self):
        text = f"🌐 {self._ui_lang.upper()}"
        try:
            if self._lang_btn is not None and self._lang_btn.winfo_exists():
                self._lang_btn.config(text=text)
        except Exception:
            pass

    def _update_city_label(self):
        """Обновляет надпись с городом в главном окне (учитывает язык)."""
        try:
            if not hasattr(self, "city_lbl") or not self.city_lbl.winfo_exists():
                return
            if self.city_name:
                text = "📍 " + self.city_name
            else:
                text = "📍 " + self._t('Укажите город в настройках')
            self.city_lbl.config(text=text)
        except Exception:
            pass

    def _show_lang_menu(self):
        T = self.T
        m = tk.Menu(self.root, tearoff=0,
                    bg=T["bg_dark"], fg=T["fg"],
                    activebackground=T["action_active"],
                    activeforeground=T["selected_fg"],
                    bd=0, relief="flat",
                    font=("Segoe UI", 10))
        for code, name in UI_LANGS.items():
            prefix = "✓  " if code == self._ui_lang else "     "
            m.add_command(label=prefix + name,
                          command=lambda c=code: self._set_ui_lang(c))
        try:
            x = self._lang_btn.winfo_rootx()
            y = self._lang_btn.winfo_rooty() + self._lang_btn.winfo_height() + 2
            m.tk_popup(x, y)
        finally:
            try:
                m.grab_release()
            except Exception:
                pass

    def _lang_press(self, e):
        self._lang_click_x = e.x_root
        self._lang_click_y = e.y_root

    def _lang_release(self, e):
        try:
            if (abs(e.x_root - self._lang_click_x) < 5 and
                    abs(e.y_root - self._lang_click_y) < 5):
                self._show_lang_menu()
        except Exception:
            pass

    def _fit_window(self):
        try:
            self.root.update_idletasks()
            req_w = self.root.winfo_reqwidth()
            req_h = self.root.winfo_reqheight()
            cur_w = self.root.winfo_width()
            cur_h = self.root.winfo_height()
            cur_x = self.root.winfo_x()
            cur_y = self.root.winfo_y()

            w = max(self._base_w, req_w + 8)
            h = max(self._base_h, req_h + 8)

            sw = self.root.winfo_screenwidth()
            sh = self.root.winfo_screenheight()
            if w > sw - 40:
                w = sw - 40
            if h > sh - 60:
                h = sh - 60

            new_x = cur_x + (cur_w - w) // 2
            new_y = cur_y + (cur_h - h) // 2
            if new_x < 0: new_x = 0
            if new_y < 0: new_y = 0
            if new_x + w > sw: new_x = sw - w
            if new_y + h > sh: new_y = sh - h

            self.root.geometry(f"{w}x{h}+{new_x}+{new_y}")
            self.root.update_idletasks()
        except Exception:
            pass

    def _theme_tooltip_key(self):
        if self.theme_name == "dark":
            return 'Переключить на светлую тему'
        return 'Переключить на тёмную тему'

    def _update_theme_button(self):
        text = "☾" if self.theme_name == "dark" else "☀"
        try:
            if self._theme_btn is not None and self._theme_btn.winfo_exists():
                self._theme_btn.config(text=text)
        except Exception:
            pass
        try:
            if self._theme_tooltip is not None:
                self._theme_tooltip.set_key(self._theme_tooltip_key())
                self._theme_tooltip.refresh()
        except Exception:
            pass

    # ============ UI ============
    def _reg(self, widget, role):
        self._styled.append((widget, role))

    def _build_ui(self):
        T = self.T
        self.root = tk.Tk()
        self.root.title(self._t('Погода в трее'))
        self.root.configure(bg=T["bg"])
        self.root.resizable(False, False)
        try:
            self.root.overrideredirect(True)
        except Exception:
            pass

        w, h = self._base_w, self._base_h
        self.root.update_idletasks()
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        x = (sw - w) // 2
        y = (sh - h) // 2
        self.root.geometry(f"{w}x{h}+{x}+{y}")

        if self._autorun_launch:
            try:
                self.root.withdraw()
            except Exception:
                pass

        # Header
        header = tk.Frame(self.root, bg=T["bg"])
        header.pack(fill="x", padx=18, pady=(14, 0))
        self._reg(header, "frame")

        icon_lbl = tk.Label(header, text="🌤", bg=T["bg"], fg=T["blue"],
                             font=("Segoe UI", 22))
        icon_lbl.pack(side="left", padx=(0, 8))
        self._reg(icon_lbl, "icon_blue")

        title_lbl = tk.Label(header, text=self._t('Погода'),
                              bg=T["bg"], fg=T["fg"],
                              font=("Segoe UI", 16, "bold"))
        title_lbl.pack(side="left")
        self._reg(title_lbl, "label")
        self._reg_i18n(title_lbl, 'Погода')

        self._theme_btn = tk.Label(header, text="", bg=T["bg"], fg=T["fg_dim"],
                                    font=("Segoe UI", 16), cursor="hand2")
        self._theme_btn.pack(side="right", padx=(8, 0))
        self._reg(self._theme_btn, "theme_btn")
        self._theme_btn.bind("<Button-1>", lambda e: self._toggle_theme())
        self._theme_btn.bind("<Enter>",
                              lambda e: self._theme_btn.config(fg=self.T["green"]))
        self._theme_btn.bind("<Leave>",
                              lambda e: self._theme_btn.config(fg=self.T["fg_dim"]))
        self._theme_tooltip = Tooltip(self._theme_btn,
                                        self._theme_tooltip_key(), app=self)
        self._tooltips.append(self._theme_tooltip)

        self._lang_btn = tk.Label(header, text=f"🌐 {self._ui_lang.upper()}",
                                   bg=T["bg"], fg=T["fg_dim"],
                                   font=("Segoe UI", 10, "bold"),
                                   cursor="hand2", padx=6, pady=2)
        self._lang_btn.pack(side="right", padx=(8, 0))
        self._reg(self._lang_btn, "lang_btn")
        self._lang_btn.bind("<ButtonPress-1>", self._lang_press, add="+")
        self._lang_btn.bind("<ButtonRelease-1>", self._lang_release, add="+")
        self._lang_btn.bind("<Enter>",
                             lambda e: self._lang_btn.config(fg=self.T["green"]),
                             add="+")
        self._lang_btn.bind("<Leave>",
                             lambda e: self._lang_btn.config(fg=self.T["fg_dim"]),
                             add="+")
        self._lang_tooltip = Tooltip(self._lang_btn,
                                       'Сменить язык интерфейса', app=self)
        self._tooltips.append(self._lang_tooltip)

        self._update_theme_button()
        self._update_lang_button()
        self._enable_drag(header)

        # Main card
        card = tk.Frame(self.root, bg=T["bg_dark"])
        card.pack(fill="x", padx=18, pady=(14, 0))
        self._reg(card, "bg_dark")

        # === Город (в выбранном языке) ===
        self.city_lbl = tk.Label(card, text="", bg=T["bg_dark"], fg=T["blue"],
                                  font=("Segoe UI", 11, "bold"))
        self.city_lbl.pack(pady=(12, 0))
        self._reg(self.city_lbl, "icon_blue_on_dark")
        self._update_city_label()

        top = tk.Frame(card, bg=T["bg_dark"])
        top.pack(pady=(6, 0))
        self._reg(top, "bg_dark")

        self.weather_icon_lbl = tk.Label(top, bg=T["bg_dark"])
        self.weather_icon_lbl.pack(side="left", padx=(0, 12))
        self._reg(self.weather_icon_lbl, "bg_dark")

        self.temp_lbl = tk.Label(top, text="—", bg=T["bg_dark"], fg=T["fg"],
                                  font=("Segoe UI", 40, "bold"))
        self.temp_lbl.pack(side="left")
        self._reg(self.temp_lbl, "label_on_dark")

        initial_desc = (self._t('Укажите город в настройках')
                        if not self.city_name else self._t('Загрузка…'))
        self.desc_lbl = tk.Label(card, text=initial_desc,
                                  bg=T["bg_dark"], fg=T["fg_dim"],
                                  font=("Segoe UI", 12))
        self.desc_lbl.pack(pady=(0, 4))
        self._reg(self.desc_lbl, "label_dim_on_dark")
        self._desc_lbl_key = ('Укажите город в настройках'
                              if not self.city_name else 'Загрузка…')

        self.feels_lbl = tk.Label(card, text="", bg=T["bg_dark"],
                                   fg=T["fg_dim"], font=("Segoe UI", 10))
        self.feels_lbl.pack(pady=(0, 12))
        self._reg(self.feels_lbl, "label_dim_on_dark")

        # Details
        details = tk.Frame(self.root, bg=T["bg"])
        details.pack(fill="x", padx=18, pady=(10, 0))
        self._reg(details, "frame")

        self.detail_labels = {}
        row1 = tk.Frame(details, bg=T["bg"])
        row1.pack(fill="x")
        self._reg(row1, "frame")
        for key, txt_key in (("wind", "💨 Ветер"),
                              ("humidity", "💧 Влажность")):
            f = tk.Frame(row1, bg=T["bg"])
            f.pack(side="left", expand=True, fill="x")
            self._reg(f, "frame")
            lbl = tk.Label(f, text=self._t(txt_key), bg=T["bg"],
                            fg=T["fg_dim"], font=("Segoe UI", 9))
            lbl.pack()
            self._reg(lbl, "label_dim")
            self._reg_i18n(lbl, txt_key)
            self.detail_labels[key] = tk.Label(
                f, text="—", bg=T["bg"], fg=T["fg"],
                font=("Segoe UI", 11, "bold"))
            self.detail_labels[key].pack()
            self._reg(self.detail_labels[key], "label")

        row2 = tk.Frame(details, bg=T["bg"])
        row2.pack(fill="x", pady=(8, 0))
        self._reg(row2, "frame")
        for key, txt_key in (("pressure", "📊 Давление"),
                              ("clouds", "☁ Облачность")):
            f = tk.Frame(row2, bg=T["bg"])
            f.pack(side="left", expand=True, fill="x")
            self._reg(f, "frame")
            lbl = tk.Label(f, text=self._t(txt_key), bg=T["bg"],
                            fg=T["fg_dim"], font=("Segoe UI", 9))
            lbl.pack()
            self._reg(lbl, "label_dim")
            self._reg_i18n(lbl, txt_key)
            self.detail_labels[key] = tk.Label(
                f, text="—", bg=T["bg"], fg=T["fg"],
                font=("Segoe UI", 11, "bold"))
            self.detail_labels[key].pack()
            self._reg(self.detail_labels[key], "label")

        # Forecast switcher
        fc_switch = tk.Frame(self.root, bg=T["bg"])
        fc_switch.pack(fill="x", padx=18, pady=(14, 4))
        self._reg(fc_switch, "frame")

        fc_lbl = tk.Label(fc_switch, text=self._t('Прогноз:'),
                           bg=T["bg"], fg=T["fg_dim"], font=("Segoe UI", 9))
        fc_lbl.pack(side="left", padx=(0, 6))
        self._reg(fc_lbl, "label_dim")
        self._reg_i18n(fc_lbl, 'Прогноз:')

        self.fc_var = tk.StringVar(value=str(self.forecast_days))
        for days in (3, 5, 7, 10):
            rb = tk.Radiobutton(
                fc_switch, text=f"{days}д",
                variable=self.fc_var, value=str(days),
                indicatoron=0, bd=0, relief="flat",
                bg=T["action_bg"], fg=T["fg"],
                activebackground=T["action_hover"],
                activeforeground=T["fg"],
                selectcolor=T["action_active"],
                font=("Segoe UI", 9, "bold"),
                padx=10, pady=4, cursor="hand2",
                command=self._on_forecast_days_changed)
            rb.pack(side="left", padx=2)
            self._reg(rb, "action_btn")

        self.forecast_frame = tk.Frame(self.root, bg=T["bg"])
        self.forecast_frame.pack(fill="x", padx=18, pady=(4, 0))
        self._reg(self.forecast_frame, "frame")

        # Bottom bar
        bottom = tk.Frame(self.root, bg=T["bg"])
        bottom.pack(side="bottom", fill="x", pady=(10, 12))
        self._reg(bottom, "frame")

        for key, cmd, color in (
            ('Свернуть', self._hide_to_tray, T["green"]),
            ('Обновить', self._manual_refresh, T["green"]),
            ('Настройки', self._open_settings_dialog, T["blue"]),
            ('Журнал', self._open_log_window, T["orange"]),
            ('Выход', self._really_quit, T["red"]),
        ):
            lbl = tk.Label(bottom, text=self._t(key), bg=T["bg"],
                            fg=T["fg_dim"],
                            font=("Segoe UI", 9, "underline"), cursor="hand2")
            lbl.pack(side="left", padx=7)
            self._reg(lbl, "label_dim")
            self._reg_i18n(lbl, key)
            lbl.bind("<Button-1>", lambda e, c=cmd: c())
            lbl.bind("<Enter>", lambda e, l=lbl, c=color: l.config(fg=c))
            lbl.bind("<Leave>", lambda e, l=lbl: l.config(fg=T["fg_dim"]))

        self._refresh_theme_colors()

    def _hide_to_tray(self):
        try:
            self.root.withdraw()
        except Exception:
            pass

    def _enable_drag(self, widget):
        widget.bind("<Button-1>", self._drag_start, add="+")
        widget.bind("<B1-Motion>", self._drag_move, add="+")
        for child in widget.winfo_children():
            self._enable_drag(child)

    def _drag_start(self, e):
        self._dx = e.x_root - self.root.winfo_x()
        self._dy = e.y_root - self.root.winfo_y()

    def _drag_move(self, e):
        x = e.x_root - self._dx
        y = e.y_root - self._dy
        self.root.geometry(f"+{x}+{y}")

    def _refresh_theme_colors(self):
        T = self.T
        for widget, role in self._styled:
            try:
                if not widget.winfo_exists():
                    continue
                if role == "frame":
                    widget.config(bg=T["bg"])
                elif role == "label":
                    widget.config(bg=T["bg"], fg=T["fg"])
                elif role == "label_dim":
                    widget.config(bg=T["bg"], fg=T["fg_dim"])
                elif role == "bg_dark":
                    widget.config(bg=T["bg_dark"])
                elif role == "label_on_dark":
                    widget.config(bg=T["bg_dark"], fg=T["fg"])
                elif role == "label_dim_on_dark":
                    widget.config(bg=T["bg_dark"], fg=T["fg_dim"])
                elif role == "icon_blue":
                    widget.config(bg=T["bg"], fg=T["blue"])
                elif role == "icon_blue_on_dark":
                    widget.config(bg=T["bg_dark"], fg=T["blue"])
                elif role == "theme_btn":
                    widget.config(bg=T["bg"], fg=T["fg_dim"])
                elif role == "lang_btn":
                    widget.config(bg=T["bg"], fg=T["fg_dim"])
                elif role == "action_btn":
                    widget.config(bg=T["action_bg"], fg=T["fg"],
                                  activebackground=T["action_hover"],
                                  activeforeground=T["fg"],
                                  selectcolor=T["action_active"])
            except Exception:
                pass

    def _toggle_theme(self):
        new = "light" if self.theme_name == "dark" else "dark"
        self.theme_name = new
        self.settings["theme"] = new
        save_settings(self.settings)
        self.T.clear()
        self.T.update(THEMES[new])
        try:
            self.root.configure(bg=self.T["bg"])
        except Exception:
            pass
        self._refresh_theme_colors()
        self._update_theme_button()
        try:
            self._render_forecast()
        except Exception:
            pass
        self.root.after(50, self._fit_window)

    def _on_forecast_days_changed(self):
        try:
            self.forecast_days = int(self.fc_var.get())
            self.settings["forecast_days"] = self.forecast_days
            save_settings(self.settings)
            if self.forecast_data:
                self._render_forecast()
        except Exception:
            pass

    # ============ IP-геолокация ============
    def _detect_city_by_ip(self, callback=None):
        def _worker():
            try:
                url = ("http://ip-api.com/json/?fields=status,city,country,"
                       "lat,lon&lang=ru")
                req = urllib.request.Request(url, headers={
                    "User-Agent": "TrayWeather/1.0"})
                with urllib.request.urlopen(req, timeout=10) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                if data.get("status") != "success":
                    raise RuntimeError("IP geolocation failed")
                city = data.get("city", "")
                country = data.get("country", "")
                label = f"{city}, {country}" if country else city
                lat = float(data.get("lat"))
                lon = float(data.get("lon"))
                log_event(f"IP-геолокация: {label} ({lat:.3f}, {lon:.3f})")
                if callback:
                    self.root.after(0, lambda: callback(label, lat, lon))
            except Exception as e:
                log_event(f"Ошибка IP-геолокации: {e}")
                if callback:
                    self.root.after(0, lambda: callback(None, None, None))

        threading.Thread(target=_worker, daemon=True).start()

    def _apply_detected_city(self, label, lat, lon):
        if not label or lat is None:
            self._show_warning('Ошибка',
                                self._t('Не удалось определить город:') +
                                " IP")
            return
        self.city_name = label
        self.lat = lat
        self.lon = lon
        self._update_city_label()
        self._persist_settings()
        self._start_auto_update()

    # ============ Погода ============
    def _fetch_weather(self):
        if self.lat is None or self.lon is None:
            try:
                self.desc_lbl.config(text=self._t('Укажите город в настройках'))
                self._desc_lbl_key = 'Укажите город в настройках'
            except Exception:
                pass
            return

        lat = self.lat
        lon = self.lon

        def _worker():
            try:
                params = {
                    "lat": f"{lat:.4f}",
                    "lon": f"{lon:.4f}",
                }
                url = ("https://api.met.no/weatherapi/locationforecast/2.0/compact?"
                       + urllib.parse.urlencode(params))
                req = urllib.request.Request(url, headers={
                    "User-Agent": "TrayWeather/1.0 (tray-weather-app)"
                })
                with urllib.request.urlopen(req, timeout=15) as resp:
                    data = json.loads(resp.read().decode("utf-8"))

                timeseries = data.get("properties", {}).get("timeseries", [])
                if not timeseries:
                    raise RuntimeError("Empty met.no response")

                first = timeseries[0]
                details = first.get("data", {}).get("instant", {}).get("details", {})
                next_1h = first.get("data", {}).get("next_1_hours", {})
                summary = next_1h.get("summary", {})
                symbol = summary.get("symbol_code", "")

                temp = details.get("air_temperature")
                wind = details.get("wind_speed")
                humidity = details.get("relative_humidity")
                pressure = details.get("air_pressure_at_sea_level")
                clouds = details.get("cloud_area_fraction")

                icon_name, desc = weather_info(symbol, self._ui_lang)

                self.weather_data = {
                    "temp": temp,
                    "desc": desc,
                    "icon_name": icon_name,
                    "wind": wind,
                    "humidity": humidity,
                    "pressure": pressure,
                    "clouds": clouds,
                    "raw_symbol": symbol,
                }

                daily = {}
                for entry in timeseries:
                    t = entry.get("time", "")
                    if not t:
                        continue
                    date = t.split("T")[0]
                    det = entry.get("data", {}).get("instant", {}).get("details", {})
                    next6 = entry.get("data", {}).get("next_6_hours", {})
                    sym = next6.get("summary", {}).get("symbol_code", "")
                    precip = next6.get("details", {}).get(
                        "precipitation_amount", 0)
                    if date not in daily:
                        daily[date] = {
                            "temps": [], "icons": [], "precip": 0,
                            "humidity": [], "wind": [],
                        }
                    ta = det.get("air_temperature")
                    if ta is not None:
                        daily[date]["temps"].append(ta)
                    if sym:
                        daily[date]["icons"].append(sym)
                    daily[date]["precip"] += precip
                    if det.get("relative_humidity") is not None:
                        daily[date]["humidity"].append(det["relative_humidity"])
                    if det.get("wind_speed") is not None:
                        daily[date]["wind"].append(det["wind_speed"])

                self.forecast_data = []
                for i, (date, d) in enumerate(sorted(daily.items())):
                    if i >= 10:
                        break
                    if not d["temps"]:
                        continue
                    mid_icon = ""
                    if d["icons"]:
                        mid_icon = d["icons"][len(d["icons"]) // 2]
                    icon_n, _ = weather_info(mid_icon, self._ui_lang)
                    tmax = max(d["temps"])
                    tmin = min(d["temps"])
                    avg_hum = (sum(d["humidity"]) / len(d["humidity"])
                               if d["humidity"] else None)
                    max_wind = max(d["wind"]) if d["wind"] else None
                    self.forecast_data.append({
                        "date": date,
                        "tmax": tmax,
                        "tmin": tmin,
                        "icon_name": icon_n,
                        "precip": d["precip"],
                        "humidity": avg_hum,
                        "wind": max_wind,
                    })

                self._check_rain_notification(timeseries)

                self.last_update = time.time()
                log_event(f"Погода: {temp:.0f}° {desc}")
                self.root.after(0, self._render_weather)
                self.root.after(0, self._render_forecast)
                self.root.after(0, self._update_tray)

            except Exception as e:
                log_event(f"Ошибка: {e}")
                self.root.after(0, lambda: self._show_warning(
                    'Ошибка',
                    self._t('Не удалось получить погоду:') + f"\n{e}"))

        threading.Thread(target=_worker, daemon=True).start()

    def _check_rain_notification(self, timeseries):
        if not self.notify_rain or not self._toaster:
            return
        try:
            now = datetime.utcnow()
            for entry in timeseries[:12]:
                t = entry.get("time", "")
                try:
                    dt = datetime.strptime(t, "%Y-%m-%dT%H:%M:%SZ")
                except Exception:
                    continue
                hours_ahead = (dt - now).total_seconds() / 3600
                if 0.8 <= hours_ahead <= 1.5:
                    next6 = entry.get("data", {}).get("next_6_hours", {})
                    sym = next6.get("summary", {}).get("symbol_code", "")
                    base = sym.split("_")[0] if sym else ""
                    if "rain" in base and sym not in self._notified_rain:
                        self._notified_rain.add(sym)
                        _, desc = weather_info(sym, self._ui_lang)
                        self._toaster.show_toast(
                            self._t('Скоро дождь!'),
                            f"{desc} {self._t('в течение часа')}",
                            duration=8, threaded=True)
                        log_event(f"Уведомление: {desc}")
                        break
        except Exception as e:
            log_event(f"Ошибка уведомления: {e}")

    def _render_weather(self):
        if not self.weather_data:
            return
        try:
            d = self.weather_data

            if d.get("icon_name"):
                icon_path = get_icon_path(d["icon_name"])
                if icon_path and os.path.exists(icon_path):
                    try:
                        img = Image.open(icon_path).convert("RGBA")
                        img = img.resize((64, 64), Image.LANCZOS)
                        photo = ImageTk.PhotoImage(img)
                        self.weather_icon_lbl.config(image=photo, text="")
                        self._current_icon_photo = photo
                    except Exception:
                        self.weather_icon_lbl.config(image="", text="🌡️")
                else:
                    self.weather_icon_lbl.config(image="", text="🌡️")
            else:
                self.weather_icon_lbl.config(image="", text="🌡️")

            if d.get("temp") is not None:
                self.temp_lbl.config(text=f"{int(round(d['temp']))}°")
            else:
                self.temp_lbl.config(text="—°")

            self.desc_lbl.config(text=d.get("desc", ""))
            self.feels_lbl.config(text="")

            ms = self._t('м/с')
            mm = self._t('мм')

            if d.get("wind") is not None:
                self.detail_labels["wind"].config(text=f"{d['wind']:.1f} {ms}")
            else:
                self.detail_labels["wind"].config(text="—")

            if d.get("humidity") is not None:
                self.detail_labels["humidity"].config(
                    text=f"{int(d['humidity'])}%")
            else:
                self.detail_labels["humidity"].config(text="—")

            if d.get("pressure") is not None:
                mmhg = d["pressure"] * 0.750062
                unit = self._t('мм рт.ст.') if self._ui_lang == 'ru' else mm
                self.detail_labels["pressure"].config(
                    text=f"{int(round(mmhg))} {unit}")
            else:
                self.detail_labels["pressure"].config(text="—")

            if d.get("clouds") is not None:
                self.detail_labels["clouds"].config(
                    text=f"{int(d['clouds'])}%")
            else:
                self.detail_labels["clouds"].config(text="—")

            self._update_city_label()
        except Exception as e:
            log_event(f"Ошибка отображения: {e}")

    def _render_forecast(self):
        try:
            for w in self.forecast_frame.winfo_children():
                w.destroy()
            self._forecast_photos = []

            days_to_show = min(self.forecast_days, len(self.forecast_data))
            if days_to_show == 0:
                return

            for i in range(days_to_show):
                day = self.forecast_data[i]
                col = tk.Frame(self.forecast_frame, bg=self.T["bg_dark"])
                col.pack(side="left", expand=True, fill="both", padx=2)
                self._reg(col, "bg_dark")

                try:
                    dt = datetime.strptime(day["date"], "%Y-%m-%d")
                    if i == 0:
                        date_str = self._t('Сегодня')
                    elif i == 1:
                        date_str = self._t('Завтра')
                    else:
                        date_str = dt.strftime("%d.%m")
                except Exception:
                    date_str = day["date"]

                tk.Label(col, text=date_str, bg=self.T["bg_dark"],
                         fg=self.T["fg_dim"], font=("Segoe UI", 8)).pack(
                             pady=(6, 2))

                icon_lbl = tk.Label(col, bg=self.T["bg_dark"])
                icon_lbl.pack()
                if day.get("icon_name"):
                    icon_path = get_icon_path(day["icon_name"])
                    if icon_path and os.path.exists(icon_path):
                        try:
                            img = Image.open(icon_path).convert("RGBA")
                            img = img.resize((32, 32), Image.LANCZOS)
                            photo = ImageTk.PhotoImage(img)
                            icon_lbl.config(image=photo)
                            self._forecast_photos.append(photo)
                        except Exception:
                            icon_lbl.config(text="🌡️", fg=self.T["fg"])
                else:
                    icon_lbl.config(text="🌡️", fg=self.T["fg"])

                tk.Label(col, text=f"{int(round(day['tmax']))}°",
                         bg=self.T["bg_dark"], fg=self.T["fg"],
                         font=("Segoe UI", 10, "bold")).pack()
                tk.Label(col, text=f"{int(round(day['tmin']))}°",
                         bg=self.T["bg_dark"], fg=self.T["fg_dim"],
                         font=("Segoe UI", 8)).pack()

                if day.get("precip", 0) > 0.1:
                    tk.Label(col, text=f"{day['precip']:.1f}{self._t('мм')}",
                             bg=self.T["bg_dark"], fg=self.T["blue"],
                             font=("Segoe UI", 7)).pack(pady=(2, 6))
                else:
                    tk.Label(col, text=" ", bg=self.T["bg_dark"],
                             font=("Segoe UI", 7)).pack(pady=(2, 6))
        except Exception as e:
            log_event(f"Ошибка прогноза: {e}")

    # ============ Tray ============
    def _make_tray_image(self, temp_text="--°"):
        size = 64
        img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        color = self.T["blue"]
        d.ellipse((2, 2, size - 2, size - 2), fill=color)
        font = None
        for fname in ("arialbd.ttf", "segoeuib.ttf", "arial.ttf"):
            try:
                font = ImageFont.truetype(fname, 22)
                break
            except Exception:
                continue
        if font is None:
            font = ImageFont.load_default()
        try:
            bbox = d.textbbox((0, 0), temp_text, font=font)
            tw = bbox[2] - bbox[0]
            th = bbox[3] - bbox[1]
            d.text(((size - tw) / 2 - bbox[0], (size - th) / 2 - bbox[1]),
                   temp_text, font=font, fill="white")
        except Exception:
            d.text((10, 20), temp_text, fill="white")
        return img

    def _build_tray_tooltip(self):
        if not self.city_name:
            return self._t('Погода в трее') + ": " + self._t('Не задан')
        if not self.weather_data:
            return f"{self.city_name}: {self._t('Загрузка…')}"
        d = self.weather_data
        temp = d.get("temp")
        desc = d.get("desc", "")
        parts = []
        if temp is not None:
            parts.append(f"{int(round(temp))}°")
        if desc:
            parts.append(desc)
        wind = d.get("wind")
        if wind is not None:
            parts.append(f"{self._t('Ветер:')} {wind:.1f} {self._t('м/с')}")
        text = f"{self.city_name}: " + ", ".join(parts)
        return text[:120]

    def _build_tray_menu(self):
        items = []

        if not self.city_name:
            items.append(pystray.MenuItem(
                self._t('Укажите город в настройках'), None, enabled=False))
            items.append(pystray.Menu.SEPARATOR)
        elif self.weather_data:
            d = self.weather_data
            temp = d.get("temp")
            desc = d.get("desc", "")
            wind = d.get("wind")
            hum = d.get("humidity")
            press = d.get("pressure")
            clouds = d.get("clouds")

            header = f"{self.city_name}"
            if temp is not None:
                header += f": {int(round(temp))}°"
            items.append(pystray.MenuItem(header, None, enabled=False))

            if desc:
                items.append(pystray.MenuItem(desc, None, enabled=False))

            if wind is not None:
                items.append(pystray.MenuItem(
                    f"{self._t('Ветер:')} {wind:.1f} {self._t('м/с')}",
                    None, enabled=False))
            if hum is not None:
                items.append(pystray.MenuItem(
                    f"{self._t('Влажность:')} {int(hum)}%",
                    None, enabled=False))
            if press is not None:
                mmhg = press * 0.750062
                unit = self._t('мм рт.ст.') if self._ui_lang == 'ru' else \
                       self._t('мм')
                items.append(pystray.MenuItem(
                    f"{self._t('Давление:')} {int(round(mmhg))} {unit}",
                    None, enabled=False))
            if clouds is not None:
                items.append(pystray.MenuItem(
                    f"{self._t('Облачность:')} {int(clouds)}%",
                    None, enabled=False))

            if len(self.forecast_data) > 1:
                tmr = self.forecast_data[1]
                items.append(pystray.MenuItem(
                    f"{self._t('Завтра:')} {int(round(tmr['tmax']))}° / "
                    f"{int(round(tmr['tmin']))}°",
                    None, enabled=False))

            if self.last_update:
                t = time.strftime("%H:%M",
                                   time.localtime(self.last_update))
                items.append(pystray.MenuItem(
                    f"{self._t('Обновлено в')} {t}",
                    None, enabled=False))

            items.append(pystray.Menu.SEPARATOR)
        else:
            items.append(pystray.MenuItem(
                f"{self.city_name}: {self._t('Загрузка…')}",
                None, enabled=False))
            items.append(pystray.Menu.SEPARATOR)

        items.append(pystray.MenuItem(self._t('Показать окно'),
                                        self._tray_open, default=True))
        items.append(pystray.MenuItem(self._t('Обновить'),
                                        self._tray_refresh))
        items.append(pystray.Menu.SEPARATOR)
        items.append(pystray.MenuItem(self._t('Настройки'),
                                        self._tray_settings))
        items.append(pystray.Menu.SEPARATOR)
        items.append(pystray.MenuItem(self._t('Выход'),
                                        self._tray_quit))

        return pystray.Menu(*items)

    def _update_tray(self):
        if not self.tray_icon:
            return
        try:
            if (self.weather_data and self.weather_data.get("temp") is not None
                    and self.city_name):
                text = f"{int(round(self.weather_data['temp']))}°"
            else:
                text = "--°"

            self.tray_icon.icon = self._make_tray_image(text)

            try:
                self.tray_icon.title = self._build_tray_tooltip()
            except Exception:
                pass

            try:
                self.tray_icon.menu = self._build_tray_menu()
                self.tray_icon.update_menu()
            except Exception as e:
                log_event(f"Обновление меню трея: {e}")

        except Exception as e:
            log_event(f"Ошибка обновления трея: {e}")

    def _setup_tray(self):
        if not TRAY_AVAILABLE:
            log_event("Трей недоступен")
            return

        def _run():
            try:
                icon = pystray.Icon(
                    "tray_weather",
                    self._make_tray_image("--°"),
                    self._build_tray_tooltip(),
                    menu=self._build_tray_menu())
                self.tray_icon = icon
                self._update_tray()
                icon.run()
            except Exception as e:
                log_event(f"Ошибка трея: {e}")

        threading.Thread(target=_run, daemon=True).start()

    def _tray_open(self, icon=None, item=None):
        self.root.after(0, self._restore_main)

    def _tray_refresh(self, icon=None, item=None):
        self.root.after(0, self._manual_refresh)

    def _tray_settings(self, icon=None, item=None):
        self.root.after(0, self._open_settings_dialog)

    def _tray_quit(self, icon=None, item=None):
        self.root.after(0, self._really_quit)

    def _restore_main(self):
        self.root.deiconify()
        try:
            self.root.overrideredirect(True)
        except Exception:
            pass
        self.root.lift()
        self.root.focus_force()

    # ============ Auto-update ============
    def _start_auto_update(self):
        self._fetch_weather()
        if self._auto_thread_started:
            return
        self._auto_thread_started = True

        def _loop():
            while not self.stop_flag:
                interval = max(5, int(self.update_interval))
                time.sleep(interval * 60)
                if not self.stop_flag:
                    self.root.after(0, self._fetch_weather)

        threading.Thread(target=_loop, daemon=True).start()

    def _manual_refresh(self):
        if not self.city_name or self.lat is None:
            self._show_warning('Ошибка',
                                self._t('Укажите город в настройках'))
            return
        try:
            self.desc_lbl.config(text=self._t('Обновление…'))
        except Exception:
            pass
        self._fetch_weather()

    # ============ Settings ============
    def _open_settings_dialog(self):
        if self._settings_dlg is not None:
            try:
                if self._settings_dlg.winfo_exists():
                    self._settings_dlg.lift()
                    return
            except Exception:
                pass
            self._settings_dlg = None

        T = self.T
        dlg = tk.Toplevel(self.root)
        dlg.overrideredirect(True)
        dlg.attributes("-topmost", True)
        dlg.configure(bg=T["blue"])
        self._settings_dlg = dlg

        inner = tk.Frame(dlg, bg=T["bg"])
        inner.pack(fill="both", expand=True, padx=2, pady=2)

        top = tk.Frame(inner, bg=T["bg"])
        top.pack(fill="x", padx=22, pady=(18, 10))
        tk.Label(top, text="⚙", bg=T["bg"], fg=T["blue"],
                 font=("Segoe UI", 20)).pack(side="left", padx=(0, 10))
        tk.Label(top, text=self._t('Настройки'), bg=T["bg"], fg=T["fg"],
                 font=("Segoe UI", 14, "bold")).pack(side="left")

        # Текущий город
        current_lbl = tk.Label(
            inner, text="", bg=T["bg"], fg=T["fg_dim"],
            font=("Segoe UI", 10), anchor="w")
        current_lbl.pack(anchor="w", padx=22, pady=(4, 6))

        # Промежуточное состояние
        self._pending_city = {
            "name": self.city_name or "",
            "lat": self.lat,
            "lon": self.lon,
        }

        def update_current_lbl():
            name = self._pending_city["name"] or self._t('Не задан')
            current_lbl.config(
                text=f"{self._t('Текущий город:')} {name}")

        update_current_lbl()

        self._settings_current_lbl = current_lbl
        self._settings_update_current = update_current_lbl

        # Поле поиска
        tk.Label(inner, text=self._t('Поиск города'), bg=T["bg"],
                 fg=T["fg_dim"], font=("Segoe UI", 9)).pack(
                     anchor="w", padx=22, pady=(6, 2))

        search_var = tk.StringVar(value="")
        search_row = tk.Frame(inner, bg=T["bg"])
        search_row.pack(fill="x", padx=22, pady=(0, 4))
        search_entry = tk.Entry(search_row, textvariable=search_var,
                                 bg=T["entry_bg"], fg=T["fg"],
                                 insertbackground=T["fg"],
                                 font=("Segoe UI", 11),
                                 relief="flat", bd=0, highlightthickness=1,
                                 highlightbackground=T["entry_border"],
                                 highlightcolor=T["blue"])
        search_entry.pack(side="left", fill="x", expand=True, ipady=7)
        try:
            search_entry.focus_set()
        except Exception:
            pass

        status_lbl = tk.Label(inner, text=self._t('Введите название на любом языке'),
                               bg=T["bg"], fg=T["fg_dim"],
                               font=("Segoe UI", 8), anchor="w")
        status_lbl.pack(anchor="w", padx=22, pady=(0, 4))

        def do_search():
            q = search_var.get().strip()
            if not q:
                self._show_warning('Ошибка',
                                    self._t('Введите название города.'))
                return
            status_lbl.config(text=self._t('Загрузка…'), fg=self.T["orange"])
            def _worker():
                result = _world_city_search(q)
                def _apply():
                    if not result:
                        status_lbl.config(text=self._t('Город не найден.'),
                                          fg=self.T["red"])
                        self._show_warning('Ошибка',
                                            self._t('Город не найден.'))
                        return
                    label, lat, lon = result
                    self._pending_city = {"name": label,
                                          "lat": lat, "lon": lon}
                    update_current_lbl()
                    status_lbl.config(text=f"✓ {label}",
                                      fg=self.T["green"])
                    search_var.set("")
                self.root.after(0, _apply)
            threading.Thread(target=_worker, daemon=True).start()

        search_btn = tk.Button(search_row, text="🔎", command=do_search,
                                bg=T["action_bg"], fg=T["fg"],
                                activebackground=T["action_hover"],
                                activeforeground=T["fg"],
                                font=("Segoe UI", 11), relief="flat", bd=0,
                                width=4, cursor="hand2")
        search_btn.pack(side="left", padx=(6, 0), ipady=3)

        search_entry.bind("<Return>", lambda e: do_search())

        # IP detect
        ip_row = tk.Frame(inner, bg=T["bg"])
        ip_row.pack(fill="x", padx=22, pady=(2, 4))

        def do_ip():
            status_lbl.config(text=self._t('Загрузка…'),
                              fg=self.T["orange"])
            def _cb(label, lat, lon):
                if not label:
                    status_lbl.config(text=self._t('Не удалось определить город:'),
                                      fg=self.T["red"])
                    return
                self._pending_city = {"name": label,
                                      "lat": lat, "lon": lon}
                update_current_lbl()
                status_lbl.config(text=f"✓ {label}", fg=self.T["green"])
            self._detect_city_by_ip(callback=_cb)

        ip_btn = tk.Label(ip_row, text="🌍 " + self._t('Определить город по IP'),
                           bg=T["action_bg"], fg=T["fg"],
                           font=("Segoe UI", 9, "bold"),
                           cursor="hand2", padx=10, pady=5)
        ip_btn.pack(side="left")
        ip_btn.bind("<Button-1>", lambda e: do_ip())
        ip_btn.bind("<Enter>", lambda e: ip_btn.config(bg=T["action_hover"]))
        ip_btn.bind("<Leave>", lambda e: ip_btn.config(bg=T["action_bg"]))

        # Interval
        tk.Label(inner, text=self._t('Обновлять каждые (минут)'),
                 bg=T["bg"], fg=T["fg_dim"], font=("Segoe UI", 9)).pack(
                     anchor="w", padx=22, pady=(10, 2))
        interval_var = tk.StringVar(value=str(self.update_interval))
        interval_entry = tk.Entry(inner, textvariable=interval_var,
                                   bg=T["entry_bg"], fg=T["fg"],
                                   insertbackground=T["fg"],
                                   font=("Segoe UI", 10),
                                   relief="flat", bd=0, highlightthickness=1,
                                   highlightbackground=T["entry_border"],
                                   highlightcolor=T["blue"])
        interval_entry.pack(fill="x", padx=22, ipady=6)

        # Notify
        notify_var = tk.BooleanVar(value=self.notify_rain)
        notify_cb = tk.Checkbutton(
            inner, text=self._t('Уведомлять о дожде за час'),
            variable=notify_var,
            bg=T["bg"], fg=T["fg"], selectcolor=T["bg_dark"],
            activebackground=T["bg"], activeforeground=T["fg"],
            font=("Segoe UI", 10), cursor="hand2",
            highlightthickness=0, bd=0)
        notify_cb.pack(anchor="w", padx=22, pady=(12, 0))

        btn_row = tk.Frame(inner, bg=T["bg"])
        btn_row.pack(pady=(18, 16))

        def close_dlg():
            self._settings_dlg = None
            self._settings_current_lbl = None
            self._settings_update_current = None
            try:
                dlg.destroy()
            except Exception:
                pass

        def do_save():
            pc = self._pending_city
            if not pc["name"] or pc["lat"] is None or pc["lon"] is None:
                self._show_warning('Ошибка',
                                    self._t('Введите название города.'))
                return
            try:
                interval = int(interval_var.get().strip())
                if interval < 5:
                    interval = 5
            except ValueError:
                interval = 30

            self.city_name = pc["name"]
            self.lat = pc["lat"]
            self.lon = pc["lon"]
            self.update_interval = interval
            self.notify_rain = bool(notify_var.get())
            self._notified_rain = set()
            self._persist_settings()
            log_event(f"Настройки: {self.city_name}, {interval}м, "
                      f"notify={self.notify_rain}")
            close_dlg()
            self._start_auto_update()

        tk.Button(btn_row, text=self._t('Отмена'), bg=T["action_bg"],
                  fg=T["fg"],
                  activebackground=T["action_hover"],
                  activeforeground=T["fg"],
                  font=("Segoe UI", 10, "bold"), relief="flat", bd=0,
                  padx=22, pady=8, cursor="hand2",
                  command=close_dlg).pack(side="left", padx=6)
        tk.Button(btn_row, text=self._t('Сохранить'), bg=T["btn_start"],
                  fg="white",
                  activebackground=T["btn_start_hov"],
                  activeforeground="white",
                  font=("Segoe UI", 10, "bold"),
                  relief="flat", bd=0, padx=22, pady=8, cursor="hand2",
                  command=do_save).pack(side="left", padx=6)

        dlg.update_idletasks()
        dw, dh = dlg.winfo_reqwidth(), dlg.winfo_reqheight()
        sw, sh = self.root.winfo_screenwidth(), self.root.winfo_screenheight()
        dlg.geometry(f"+{(sw - dw) // 2}+{(sh - dh) // 2}")

        def _drag_start(e):
            dlg._dx = e.x_root - dlg.winfo_x()
            dlg._dy = e.y_root - dlg.winfo_y()

        def _drag_move(e):
            dlg.geometry(f"+{e.x_root - dlg._dx}+{e.y_root - dlg._dy}")

        top.bind("<Button-1>", _drag_start)
        top.bind("<B1-Motion>", _drag_move)
        dlg.bind("<Escape>", lambda e: close_dlg())

    # ============ Log ============
    def _open_log_window(self):
        if self._log_dlg is not None:
            try:
                if self._log_dlg.winfo_exists():
                    self._log_dlg.lift()
                    self._refresh_log()
                    return
            except Exception:
                pass
            self._log_dlg = None

        T = self.T
        dlg = tk.Toplevel(self.root)
        dlg.overrideredirect(True)
        dlg.attributes("-topmost", True)
        dlg.configure(bg=T["green"])
        self._log_dlg = dlg

        inner = tk.Frame(dlg, bg=T["bg"])
        inner.pack(fill="both", expand=True, padx=2, pady=2)

        top = tk.Frame(inner, bg=T["bg"])
        top.pack(fill="x", padx=22, pady=(18, 8))
        tk.Label(top, text="📋", bg=T["bg"], fg=T["green"],
                 font=("Segoe UI", 18)).pack(side="left", padx=(0, 10))
        tk.Label(top, text=self._t('Журнал'), bg=T["bg"], fg=T["fg"],
                 font=("Segoe UI", 14, "bold")).pack(side="left")

        text_wrap = tk.Frame(inner, bg=T["entry_border"])
        text_wrap.pack(fill="both", expand=True, padx=22, pady=(0, 10))
        self._log_text = tk.Text(text_wrap, height=14, width=60,
                                  bg=T["entry_bg"], fg=T["fg"],
                                  insertbackground=T["fg"],
                                  font=("Consolas", 9), relief="flat",
                                  bd=0, wrap="word")
        self._log_text.pack(padx=1, pady=1, fill="both", expand=True)

        btn_row = tk.Frame(inner, bg=T["bg"])
        btn_row.pack(pady=(0, 16))

        def close_dlg():
            self._log_dlg = None
            try:
                dlg.destroy()
            except Exception:
                pass

        tk.Button(btn_row, text=self._t('Закрыть'), bg=T["btn_start"],
                  fg="white",
                  activebackground=T["btn_start_hov"],
                  activeforeground="white", font=("Segoe UI", 10, "bold"),
                  relief="flat", bd=0, padx=18, pady=8, cursor="hand2",
                  command=close_dlg).pack()

        dlg.update_idletasks()
        dw, dh = dlg.winfo_reqwidth(), dlg.winfo_reqheight()
        sw, sh = self.root.winfo_screenwidth(), self.root.winfo_screenheight()
        dlg.geometry(f"+{(sw - dw) // 2}+{(sh - dh) // 2}")
        dlg.bind("<Escape>", lambda e: close_dlg())
        self._refresh_log()

    def _refresh_log(self):
        try:
            self._log_text.config(state="normal")
            self._log_text.delete("1.0", "end")
            self._log_text.insert("end", get_log_text())
            self._log_text.see("end")
            self._log_text.config(state="disabled")
        except Exception:
            pass

    # ============ Warning ============
    def _show_warning(self, title_key, message):
        if self._warning_dlg is not None:
            try:
                if self._warning_dlg.winfo_exists():
                    self._warning_dlg.lift()
                    return
            except Exception:
                pass
            self._warning_dlg = None

        title = self._t(title_key) if title_key in UI_TR else title_key

        T = self.T
        dlg = tk.Toplevel(self.root)
        dlg.overrideredirect(True)
        dlg.attributes("-topmost", True)
        dlg.configure(bg=T["orange"])
        self._warning_dlg = dlg

        inner = tk.Frame(dlg, bg=T["bg"])
        inner.pack(fill="both", expand=True, padx=2, pady=2)

        top = tk.Frame(inner, bg=T["bg"])
        top.pack(fill="x", padx=22, pady=(20, 10))
        tk.Label(top, text="⚠", bg=T["bg"], fg=T["orange"],
                 font=("Segoe UI", 22)).pack(side="left", padx=(0, 12))
        tk.Label(top, text=title, bg=T["bg"], fg=T["fg"],
                 font=("Segoe UI", 13, "bold")).pack(side="left")

        tk.Label(inner, text=message, bg=T["bg"], fg=T["fg_dim"],
                 justify="left", font=("Segoe UI", 10),
                 wraplength=380).pack(padx=22, pady=(0, 16), anchor="w")

        def close_dlg():
            self._warning_dlg = None
            try:
                dlg.destroy()
            except Exception:
                pass

        ok = tk.Button(inner, text=self._t('Понятно'), bg=T["orange"],
                       fg="#1a1a1a",
                       activebackground=T["orange"],
                       activeforeground="#1a1a1a",
                       font=("Segoe UI", 10, "bold"), relief="flat", bd=0,
                       padx=26, pady=8, cursor="hand2", command=close_dlg)
        ok.pack(pady=(0, 18))

        dlg.update_idletasks()
        dw, dh = dlg.winfo_reqwidth(), dlg.winfo_reqheight()
        sw, sh = self.root.winfo_screenwidth(), self.root.winfo_screenheight()
        dlg.geometry(f"+{(sw - dw) // 2}+{(sh - dh) // 2}")
        dlg.bind("<Escape>", lambda e: close_dlg())
        dlg.bind("<Return>", lambda e: close_dlg())
        ok.focus_set()

    # ============ Misc ============
    def _persist_settings(self):
        data = {
            "city_name": self.city_name or "",
            "lat": self.lat,
            "lon": self.lon,
            "update_interval": self.update_interval,
            "forecast_days": self.forecast_days,
            "notify_rain": self.notify_rain,
            "theme": self.theme_name,
            "ui_lang": self._ui_lang,
        }
        save_settings(data)
        self.settings.update(data)

    def _poll_signal(self):
        try:
            if os.path.exists(SIGNAL_FILE):
                try:
                    os.remove(SIGNAL_FILE)
                except Exception:
                    pass
                self._restore_main()
        except Exception:
            pass
        try:
            self.root.after(500, self._poll_signal)
        except Exception:
            pass

    def _apply_icon(self):
        try:
            img = self._make_tray_image("--°")
            ico_path = os.path.join(tempfile.gettempdir(), "tray_weather.ico")
            img.save(ico_path, format="ICO",
                     sizes=[(16, 16), (32, 32), (48, 48), (64, 64)])
            self.root.iconbitmap(default=ico_path)
            photo = ImageTk.PhotoImage(img)
            self.root.iconphoto(True, photo)
            self._icon_photo = photo
        except Exception:
            pass

    def _really_quit(self):
        log_event("=== Выход ===")
        self.stop_flag = True
        self._persist_settings()
        try:
            if self.tray_icon:
                self.tray_icon.stop()
        except Exception:
            pass
        try:
            self.root.destroy()
        except Exception:
            pass
        try:
            os._exit(0)
        except Exception:
            pass

    def run(self):
        self.root.protocol("WM_DELETE_WINDOW", lambda: self._hide_to_tray())
        self.root.mainloop()


if __name__ == "__main__":
    if not acquire_single_instance():
        signal_existing_instance()
        time.sleep(0.15)
        sys.exit(0)

    if not TRAY_AVAILABLE:
        import tkinter.messagebox as mb
        mb.showerror("Ошибка",
                      "Нужны библиотеки pystray и Pillow.\n\n"
                      "Установите: pip install pystray Pillow")
        sys.exit(1)

    App().run()