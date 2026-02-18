"""Движок новостей: поиск, парсинг статей, суммаризация через DeepSeek"""

import asyncio
import logging
from datetime import datetime, timezone
from dateutil import parser as date_parser
from openai import AsyncOpenAI
from duckduckgo_search import DDGS
import aiohttp
from newspaper import Article

from config import (
    DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL, DEEPSEEK_MODEL,
    PRESET_TOPICS, LANGUAGE_LEVELS, WORDS_PER_MINUTE,
    MAX_SEARCH_RESULTS_PER_TOPIC, MAX_ARTICLE_LENGTH, REQUEST_TIMEOUT,
)

logger = logging.getLogger(__name__)

# DeepSeek клиент (OpenAI-совместимый)
client = AsyncOpenAI(
    api_key=DEEPSEEK_API_KEY,
    base_url=DEEPSEEK_BASE_URL,
)


def search_news(query: str, max_results: int = MAX_SEARCH_RESULTS_PER_TOPIC, since: datetime = None) -> list[dict]:
    """Поиск новостей через DuckDuckGo с фильтрацией по дате"""
    try:
        with DDGS() as ddgs:
            results = list(ddgs.news(query, max_results=max_results * 2, region="wt-wt"))

            if since:
                filtered = []
                for r in results:
                    try:
                        news_date = date_parser.parse(r.get("date", ""))
                        if news_date.tzinfo is None:
                            news_date = news_date.replace(tzinfo=timezone.utc)
                        if since.tzinfo is None:
                            since = since.replace(tzinfo=timezone.utc)
                        if news_date > since:
                            filtered.append(r)
                    except Exception:
                        # Если не можем распарсить дату — включаем новость
                        filtered.append(r)
                return filtered[:max_results]

            return results[:max_results]
    except Exception as e:
        logger.error(f"Ошибка поиска по '{query}': {e}")
        return []


async def parse_article(session: aiohttp.ClientSession, url: str) -> dict | None:
    """Парсинг одной статьи"""
    try:
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=REQUEST_TIMEOUT)) as resp:
            if resp.status != 200:
                return None
            html = await resp.text()

        article = Article(url)
        article.download(input_html=html)
        article.parse()

        text = article.text.strip()
        if len(text) < 100:
            return None

        return {
            "title": article.title or "Без заголовка",
            "text": text[:MAX_ARTICLE_LENGTH],
            "url": url,
            "source": url.split("/")[2] if "/" in url else url,
        }
    except Exception as e:
        logger.debug(f"Не удалось спарсить {url}: {e}")
        return None


async def fetch_articles_for_topic(
    session: aiohttp.ClientSession,
    topic_name: str,
    search_query: str,
    since: datetime = None,
) -> list[dict]:
    """Собрать статьи по одной теме"""
    # Поиск в отдельном потоке (duckduckgo_search синхронная)
    loop = asyncio.get_event_loop()
    search_results = await loop.run_in_executor(
        None, lambda: search_news(search_query, MAX_SEARCH_RESULTS_PER_TOPIC, since)
    )

    if not search_results:
        return []

    # Парсим все найденные статьи параллельно
    urls = [r.get("url") or r.get("href", "") for r in search_results if r.get("url") or r.get("href")]
    tasks = [parse_article(session, url) for url in urls[:MAX_SEARCH_RESULTS_PER_TOPIC]]
    articles = await asyncio.gather(*tasks)

    result = []
    for art in articles:
        if art:
            art["topic"] = topic_name
            result.append(art)

    return result


def build_search_queries(enabled_topics: list, custom_topics: list, lang: str = "ru") -> list[tuple[str, str]]:
    """Строим поисковые запросы из тем пользователя"""
    queries = []
    today = datetime.now().strftime("%Y-%m")

    for topic_id in enabled_topics:
        if topic_id in PRESET_TOPICS:
            topic = PRESET_TOPICS[topic_id]
            name = topic["name_ru"] if lang == "ru" else topic["name_en"]
            if lang == "ru":
                q = f"{name} новости {today}"
            else:
                q = f"{name} news {today}"
            queries.append((name, q))

    for custom in custom_topics:
        if lang == "ru":
            q = f"{custom} новости {today}"
        else:
            q = f"{custom} news {today}"
        queries.append((custom, q))

    return queries


async def collect_all_news(
    enabled_topics: list,
    custom_topics: list,
    lang: str = "ru",
    since: datetime = None,
) -> list[dict]:
    """Собрать все новости по всем темам"""
    queries = build_search_queries(enabled_topics, custom_topics, lang)

    if not queries:
        return []

    connector = aiohttp.TCPConnector(limit=10, ssl=False)
    async with aiohttp.ClientSession(
        connector=connector,
        headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    ) as session:
        tasks = [
            fetch_articles_for_topic(session, topic_name, query, since)
            for topic_name, query in queries
        ]
        results = await asyncio.gather(*tasks)

    # Объединяем все статьи
    all_articles = []
    for articles in results:
        all_articles.extend(articles)

    # Дедупликация по URL
    seen_urls = set()
    unique = []
    for art in all_articles:
        if art["url"] not in seen_urls:
            seen_urls.add(art["url"])
            unique.append(art)

    return unique


def build_prompt(
    articles: list[dict],
    language_level: str,
    reading_time: int,
    digest_lang: str,
    important_only: bool = False,
    importance_level: str = "medium",
) -> str:
    """Собрать промпт для DeepSeek"""
    target_words = reading_time * WORDS_PER_MINUTE
    level_prompt = LANGUAGE_LEVELS.get(language_level, LANGUAGE_LEVELS["medium"])["prompt"]

    lang_instruction = "Отвечай на русском языке." if digest_lang == "ru" else "Respond in English."

    # Собираем тексты статей
    articles_text = ""
    for i, art in enumerate(articles, 1):
        articles_text += f"\n--- Статья {i} ---\n"
        articles_text += f"Тема: {art['topic']}\n"
        articles_text += f"Заголовок: {art['title']}\n"
        articles_text += f"Источник: {art['source']}\n"
        articles_text += f"URL: {art['url']}\n"
        articles_text += f"Текст: {art['text']}\n"

    important_instruction = ""
    if important_only:
        level_map = {
            "low": "Включи все более-менее значимые новости (10-15 штук).",
            "medium": "Выбери только действительно важные новости (5-7 штук).",
            "high": "Только самые критичные, топовые новости дня (3-5 штук).",
        }
        important_instruction = f"""
РЕЖИМ "ТОЛЬКО ВАЖНОЕ": {level_map.get(importance_level, level_map["medium"])}
Отбирай новости по реальной значимости и влиянию на мир/отрасль.
"""

    prompt = f"""Ты — профессиональный новостной редактор. Твоя задача — создать структурированный новостной дайджест.

ПРАВИЛА:
1. Включай ТОЛЬКО подтверждённые факты. Если информация есть только в одном источнике и выглядит сомнительно — отметь это.
2. Убери всю "воду": мнения, спекуляции, кликбейт, рекламу.
3. Группируй новости по темам.
4. Каждая новость: заголовок + суть в 2-3 предложениях + источник (URL).
5. Если несколько источников пишут об одном — объедини и укажи все источники.
{important_instruction}

СТИЛЬ: {level_prompt}
ЯЗЫК: {lang_instruction}
ОБЪЁМ: примерно {target_words} слов (чтение ~{reading_time} минут).

ФОРМАТ ОТВЕТА:
Используй такой формат (Telegram MarkdownV2 НЕ используй, используй HTML):

<b>📌 НАЗВАНИЕ ТЕМЫ</b>

▸ <b>Заголовок новости</b>
Краткое описание сути. Что произошло, почему важно.
🔗 <a href="URL">Источник</a>

---

ВОТ СТАТЬИ ДЛЯ АНАЛИЗА:
{articles_text}

Создай дайджест:"""

    return prompt


async def generate_digest(
    articles: list[dict],
    language_level: str,
    reading_time: int,
    digest_lang: str,
    important_only: bool = False,
    importance_level: str = "medium",
) -> str:
    """Генерация дайджеста через DeepSeek"""
    if not articles:
        return "😕 Не удалось найти новости по выбранным темам. Попробуй позже или добавь больше тем."

    prompt = build_prompt(articles, language_level, reading_time, digest_lang, important_only, importance_level)

    try:
        response = await client.chat.completions.create(
            model=DEEPSEEK_MODEL,
            messages=[
                {"role": "system", "content": "Ты профессиональный новостной редактор. Твои дайджесты точные, структурированные и без воды."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.3,
            max_tokens=4000,
        )
        return response.choices[0].message.content
    except Exception as e:
        logger.error(f"Ошибка DeepSeek API: {e}")
        return f"❌ Ошибка генерации дайджеста: {e}"


async def get_news_digest(
    enabled_topics: list,
    custom_topics: list,
    language_level: str = "medium",
    reading_time: int = 7,
    digest_lang: str = "ru",
    important_only: bool = False,
    importance_level: str = "medium",
    last_viewed_at: str = None,
) -> str:
    """Полный пайплайн: поиск → парсинг → дайджест"""
    # Парсим дату последнего просмотра
    since = None
    if last_viewed_at:
        try:
            since = date_parser.parse(last_viewed_at)
        except Exception:
            pass

    articles = await collect_all_news(enabled_topics, custom_topics, digest_lang, since)

    digest = await generate_digest(
        articles=articles,
        language_level=language_level,
        reading_time=reading_time,
        digest_lang=digest_lang,
        important_only=important_only,
        importance_level=importance_level,
    )

    return digest
