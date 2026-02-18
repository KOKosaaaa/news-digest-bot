"""Конфигурация бота"""

# === API КЛЮЧИ ===
import os
BOT_TOKEN = os.getenv("BOT_TOKEN", "YOUR_TELEGRAM_BOT_TOKEN")
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "YOUR_DEEPSEEK_API_KEY")
DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
DEEPSEEK_MODEL = "deepseek-chat"  # DeepSeek-V3

# === НАСТРОЙКИ ПО УМОЛЧАНИЮ ===
DEFAULT_LANGUAGE_LEVEL = "medium"  # простой/средний/продвинутый/экспертный
DEFAULT_READING_TIME = 7  # минут
DEFAULT_DIGEST_LANG = "ru"

# === ТЕМЫ ===
PRESET_TOPICS = {
    "geopolitics":    {"emoji": "🌍", "name_ru": "Геополитика",        "name_en": "Geopolitics"},
    "economy":        {"emoji": "💰", "name_ru": "Экономика",          "name_en": "Economy & Finance"},
    "it":             {"emoji": "💻", "name_ru": "IT / Технологии",    "name_en": "IT & Tech"},
    "ai":             {"emoji": "🤖", "name_ru": "AI / Нейросети",     "name_en": "AI & Neural Networks"},
    "science":        {"emoji": "🔬", "name_ru": "Наука",              "name_en": "Science"},
    "space":          {"emoji": "🚀", "name_ru": "Космос",             "name_en": "Space"},
    "gaming":         {"emoji": "🎮", "name_ru": "Игры",               "name_en": "Gaming"},
    "3dprint":        {"emoji": "🖨", "name_ru": "3D-печать",          "name_en": "3D Printing"},
    "gadgets":        {"emoji": "📱", "name_ru": "Гаджеты",            "name_en": "Gadgets"},
    "energy":         {"emoji": "⚡", "name_ru": "Энергетика",          "name_en": "Energy"},
    "medicine":       {"emoji": "🏥", "name_ru": "Медицина",           "name_en": "Medicine"},
    "cybersecurity":  {"emoji": "🔒", "name_ru": "Кибербезопасность",  "name_en": "Cybersecurity"},
    "crypto":         {"emoji": "📈", "name_ru": "Крипто",             "name_en": "Crypto"},
    "auto":           {"emoji": "🚗", "name_ru": "Авто / EV",          "name_en": "Auto & EV"},
    "cinema":         {"emoji": "🎬", "name_ru": "Кино / Сериалы",     "name_en": "Cinema & TV"},
    "sport":          {"emoji": "⚽", "name_ru": "Спорт",              "name_en": "Sport"},
    "russia":         {"emoji": "🇷🇺", "name_ru": "Россия",            "name_en": "Russia"},
    "europe":         {"emoji": "🇪🇺", "name_ru": "Европа",            "name_en": "Europe"},
    "usa":            {"emoji": "🇺🇸", "name_ru": "США",               "name_en": "USA"},
    "china":          {"emoji": "🇨🇳", "name_ru": "Китай",             "name_en": "China"},
}

# === УРОВНИ ЯЗЫКА ===
LANGUAGE_LEVELS = {
    "simple": {
        "emoji": "😊",
        "name_ru": "Простой",
        "prompt": "Объясняй как другу, без терминов, простыми словами. Короткие предложения."
    },
    "medium": {
        "emoji": "📝",
        "name_ru": "Средний",
        "prompt": "Нормальный новостной стиль. Понятно, но информативно."
    },
    "advanced": {
        "emoji": "📊",
        "name_ru": "Продвинутый",
        "prompt": "Используй профессиональную терминологию, давай больше контекста и деталей."
    },
    "expert": {
        "emoji": "🎯",
        "name_ru": "Экспертный",
        "prompt": "Максимум конкретики: цифры, даты, технические подробности, первоисточники. Без упрощений."
    },
}

# === ВРЕМЯ ЧТЕНИЯ ===
READING_TIMES = [3, 5, 7, 10, 15]  # минут

# Примерно 200 слов в минуту для чтения
WORDS_PER_MINUTE = 200

# === ПАРСИНГ ===
MAX_SEARCH_RESULTS_PER_TOPIC = 5
MAX_ARTICLE_LENGTH = 3000  # символов на статью для отправки в LLM
REQUEST_TIMEOUT = 10  # секунд
