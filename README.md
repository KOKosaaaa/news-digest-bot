# News Digest Bot

Telegram бот для персональных новостных дайджестов с AI-суммаризацией.

## Функционал

- Персональные новостные дайджесты по выбранным темам
- Поиск новостей через DuckDuckGo
- Парсинг статей через newspaper3k
- AI-суммаризация через DeepSeek API
- Запоминает время последнего просмотра — показывает только свежие новости
- Настраиваемые темы, уровень языка, время чтения

## Установка

```bash
# Клонировать репозиторий
git clone https://github.com/KOKosaaaa/news-digest-bot.git
cd news-digest-bot

# Создать виртуальное окружение
python -m venv venv
source venv/bin/activate

# Установить зависимости
pip install -r requirements.txt

# Создать .env файл
cp .env.example .env
# Добавить BOT_TOKEN и DEEPSEEK_API_KEY
```

## Переменные окружения

```env
BOT_TOKEN=your_telegram_bot_token
DEEPSEEK_API_KEY=your_deepseek_api_key
DEEPSEEK_BASE_URL=https://api.deepseek.com/v1
```

## Запуск

```bash
python bot.py
```

## Структура

```
news-digest-bot/
├── bot.py           # Telegram бот (aiogram 3.x)
├── config.py        # Конфигурация
├── database.py      # SQLite база данных
├── news_engine.py   # Поиск, парсинг, суммаризация
└── requirements.txt
```

## Использование

1. `/start` — начать работу с ботом
2. Настроить интересующие темы
3. Получать персонализированные дайджесты

## Лицензия

MIT
