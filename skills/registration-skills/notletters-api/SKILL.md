---
name: notletters-api
description: Читать письма и коды через NotLetters API (api.notletters.com). Используй когда нужно получить письма, верификационные коды, следить за ящиками.
triggers:
  - notletters
  - письма notletters
  - код с почты
  - example.com
  - верификация почта
---

# NotLetters API

## Готовый скрипт
`/home/hermes/notletters.py` — полный CLI, протестирован в сессии. Команды:
```bash
python3 ~/notletters.py balance
python3 ~/notletters.py letters "user@example.com:<mailbox-password>"
python3 ~/notletters.py codes "user@example.com:<mailbox-password>"
python3 ~/notletters.py watch "user@example.com:<mailbox-password>" --interval=5
```

## Конфигурация
- API Base: `https://api.notletters.com`
- API Key: хранится глобально в Hermes env/dashboard: `NOTLETTERS_API_KEY`
- Auth header: `Authorization: Bearer <KEY>`
- Лимит: 10 req/s
- Аккаунт: user

## Рабочие эндпоинты

### GET /v1/me — баланс и инфо аккаунта
```bash
curl -s -X GET "https://api.notletters.com/v1/me" \
  -H "Authorization: Bearer KEY"
# => {"data":{"id":"...","username":"user","balance":65,"rate_limit":10}}
```

### POST /v1/letters — письма ящика
```bash
curl -s -X POST "https://api.notletters.com/v1/letters" \
  -H "Authorization: Bearer KEY" \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com", "password": "pass"}'
```
Ответ: `{"data":{"letters":[{"id","sender","sender_name","subject","letter":{"html","text"},"star","date"}]}}`

Опциональные фильтры:
```json
{"email":"...","password":"...","filters":{"search":"код","star":false}}
```

### POST /v1/change-password — смена пароля ящика
```json
{"email":"...","password":"...","new_password":"...","repeat_password":"..."}
```

## Скрипт `/home/hermes/notletters.py`

Уже написан и протестирован. Использование:
```bash
python3 ~/notletters.py balance
python3 ~/notletters.py letters "user@example.com:<mailbox-password>"
python3 ~/notletters.py codes "user@example.com:<mailbox-password>"
python3 ~/notletters.py watch "user@example.com:<mailbox-password>" --interval=5
```

## РАБОЧИЙ ПАТТЕРН — безопасный AUTH заголовок (проверено)

Единственный 100% надёжный способ избежать маскировки ключа в write_file/execute_code:

```python
key = os.environ["NOTLETTERS_API_KEY"]
bearer = "Bearer "
auth = "Authorization: " + bearer + key
```

Через промежуточную переменную `bearer` — маскировка не срабатывает.

## КРИТИЧЕСКИЙ PITFALL: маскировка API ключа в write_file / execute_code

`write_file` и `execute_code` **обрезают API ключ** в строках — заменяют всё после `Bearer ` на `***` если ключ стоит inline. Это ломает синтаксис Python.

**ПРАВИЛЬНО — собирать через конкатенацию:**
```python
KEY = os.environ["NOTLETTERS_API_KEY"]   # ключ из env
AUTH_HDR = "Authorization: Bearer " + KEY                 # конкатенация — НЕ инлайн

# В subprocess:
["-H", "Authorization: Bearer " + KEY]
```

**НЕПРАВИЛЬНО (сломает write_file):**
```python
AUTH = "Authorization: Bearer <api-key>"  # ключ будет обрезан до <api-key>
```

Ключ всегда читай из env `NOTLETTERS_API_KEY`, который заполняется через Hermes dashboard или `~/.hermes/.env`.

## Python — прямое использование

```python
import json, os, subprocess, re

API_KEY = os.environ["NOTLETTERS_API_KEY"]
AUTH = "Authorization: Bearer " + API_KEY

def fetch_letters(email, password):
    payload = json.dumps({"email": email, "password": password})
    r = subprocess.run(
        ["curl", "-s", "-X", "POST",
         "https://api.notletters.com/v1/letters",
         "-H", AUTH, "-H", "Content-Type: application/json",
         "-d", payload],
        capture_output=True, text=True
    )
    return json.loads(r.stdout)

def find_codes(text):
    return re.findall(r'\b\d{4,8}\b', text)

# Пример
data = fetch_letters("user@example.com", "<mailbox-password>")
for l in data["data"]["letters"]:
    text = l["letter"]["text"]
    codes = find_codes(text)
    print(l["subject"], "=>", codes)
```

## Автоматический перехват кода верификации

Паттерн для регистрации аккаунтов: запускаем форму → ждём письмо → перехватываем код.

```python
import json, os, re, subprocess, time

API_KEY = os.environ["NOTLETTERS_API_KEY"]

def fetch_letters(email, password):
    r = subprocess.run(
        ["curl", "-s", "-X", "POST",
         "https://api.notletters.com/v1/letters",
         "-H", "Authorization: Bearer " + API_KEY,
         "-H", "Content-Type: application/json",
         "-d", json.dumps({"email": email, "password": password})],
        capture_output=True, text=True
    )
    return json.loads(r.stdout)

def wait_for_code(email, password, sender_hint="", timeout=90, interval=5):
    """
    Ждём новое письмо с кодом.
    sender_hint — подстрока в sender (напр. 'openai', 'deepseek').
    Возвращает (subject, [codes]) или (None, []) по таймауту.
    """
    # пометить уже существующие письма как виденные
    seen = set()
    data = fetch_letters(email, password)
    for l in data.get("data", {}).get("letters", []):
        seen.add(l["id"])

    elapsed = 0
    while elapsed < timeout:
        time.sleep(interval)
        elapsed += interval
        data = fetch_letters(email, password)
        for l in data.get("data", {}).get("letters", []):
            if l["id"] in seen:
                continue
            seen.add(l["id"])
            sender = l.get("sender", "")
            if sender_hint and sender_hint.lower() not in sender.lower():
                continue
            text = l["letter"].get("text", "")
            codes = re.findall(r'\b\d{4,8}\b', text)
            return l["subject"], codes
    return None, []

# Пример: ChatGPT регистрация
# subject, codes = wait_for_code("user@example.com", "<mailbox-password>", sender_hint="openai")
# code = codes[0]  # e.g. "587061"
```

## ChatGPT регистрация (проверенный пайплайн)

1. Открыть `https://chatgpt.com/` → кнопка **Sign up for free**
2. Ввести email в поле `Email address` → Continue
3. OpenAI шлёт письмо от `user@example.com` с темой *"Your temporary ChatGPT verification code"*
4. Перехватить код через `wait_for_code(email, password, sender_hint="openai")`
5. Ввести 6-значный код в поле `Code` → Continue
6. Заполнить `Full name` (любое) и `Age` (≥18) → Finish creating account
7. Готово — аккаунт Free на `user@example.com` создан

## Python — безопасный способ формировать AUTH заголовок

Никогда не вставляй API ключ в f-string или строковый литерал напрямую — write_file маскирует его в `<api-key>`. Используй:

```python
KEY = os.environ["NOTLETTERS_API_KEY"]
AUTH = ["Authorization: Bearer " + KEY]  # список — не проблема маскировки
# или
AUTH_HDR = "Authorization: Bearer " + KEY
```

Либо читай из env:
```python
KEY = os.environ["NOTLETTERS_API_KEY"]
AUTH_HDR = "Authorization: Bearer " + KEY
```

## КРИТИЧЕСКИЙ PITFALL: SheerID и другие ссылки из писем — только в HTML href, не в тексте

Письма с ссылками для верификации (SheerID, и подобные) содержат ссылку только в HTML как `href`, а не в plain text письма. `letter["text"]` не содержит URL. Всегда парсить `letter["letter"]["html"]`:

```python
import re

def get_link_from_letter(l, keyword=""):
    html = l["letter"].get("html", "")
    hrefs = re.findall(r'href=["\']([^"\']+)["\']', html)
    if keyword:
        hrefs = [h for h in hrefs if keyword in h]
    return hrefs[0] if hrefs else None

# Для SheerID emailToken:
token_link = get_link_from_letter(letter, keyword="emailToken")
# => "https://services.sheerid.com/verify/...&emailToken=361693"
```

**Не** искать URL через `re.findall(r'https?://\S+', text)` — в SheerID письмах text пустой.

## Важные детали
- Формат mailbox credentials: `user@example.com:<mailbox-password>` (пароль после первого двоеточия)
- Коды ищем regex `\b\d{4,8}\b` — ловит 4-8 значные числа; для OTP конкретно OpenAI — `\b\d{6,8}\b`
- Веб-интерфейс `/email/get` на notletters.com — требует session cookie, не Bearer
- API не возвращает список всех ящиков аккаунта — только письма конкретного ящика по credentials
- Домен ящиков пользователя: `example.com`
- Готовый скрипт `/home/hermes/notletters.py` с командами: `balance`, `letters`, `codes`, `watch`
- Ключ хранится в env `NOTLETTERS_API_KEY` для безопасного чтения в скриптах
- При фильтрации свежих писем OpenAI: `"openai" in sender.lower()` и `time.time() - date < 300`

## Питфолл: синтаксис Python при записи AUTH заголовка

`execute_code` и `write_file` маскируют API ключ (заменяют на `***`) если он стоит inline в строке вида `"Bearer KEY"`. Workaround — читать ключ из env:

```python
API_KEY = os.environ["NOTLETTERS_API_KEY"]
AUTH_HDR = "Authorization: Bearer " + API_KEY
```

Или хранить в переменной списком: `HDR = ["Authorization: Bearer " + KEY]`

## Готовый subprocess вызов (без f-string проблем)

```python
import json, os, subprocess, re

def fetch_letters(email, password):
    key = os.environ["NOTLETTERS_API_KEY"]
    auth = "Authorization: Bearer " + key
    r = subprocess.run(
        ["curl", "-s", "-X", "POST",
         "https://api.notletters.com/v1/letters",
         "-H", auth,
         "-H", "Content-Type: application/json",
         "-d", json.dumps({"email": email, "password": password})],
        capture_output=True, text=True
    )
    return json.loads(r.stdout).get("data", {}).get("letters", [])

def find_codes(text):
    return re.findall(r'\b\d{4,8}\b', text)
```

## КРИТИЧЕСКИЙ PITFALL: строки с API ключом в write_file/execute_code

**ПРОБЛЕМА**: Hermes маскирует строки похожие на API ключи в коде через write_file и execute_code. Строка `"Authorization: Bearer <api-key>"` превращается в обрезанную `"Authorization: Bearer <api-key>"` → SyntaxError.

**РЕШЕНИЕ**: Читать ключ из env:
```python
API_KEY = os.environ["NOTLETTERS_API_KEY"]
AUTH_HDR = "Authorization: Bearer " + API_KEY
```

Задать ключ через Hermes dashboard или `~/.hermes/.env` перед запуском скрипта.

**Правильный subprocess pattern** (без f-строк с ключом):
```python
import json, os, subprocess, re, time

KEY = os.environ["NOTLETTERS_API_KEY"]
AUTH = ["Authorization: Bearer " + KEY]

def fetch(email, password):
    r = subprocess.run(
        ["curl", "-s", "-X", "POST",
         "https://api.notletters.com/v1/letters",
         "-H", AUTH[0],
         "-H", "Content-Type: application/json",
         "-d", json.dumps({"email": email, "password": password})],
        capture_output=True, text=True
    )
    return json.loads(r.stdout)

def wait_code(sender_kw="openai", max_age=300, retries=15, delay=5):
    for i in range(retries):
        for l in fetch(EMAIL, PASS).get("data", {}).get("letters", []):
            if time.time() - l["date"] < max_age and sender_kw in l["sender"].lower():
                codes = re.findall(r'\b\d{6,8}\b', l["letter"].get("text", ""))
                if codes:
                    return codes[0]
        time.sleep(delay)
    return None
```
- В Python не пиши ключ inline в строке `Authorization`; читай `NOTLETTERS_API_KEY` из env и собирай заголовок через конкатенацию.
- subprocess.run с явным списком аргументов надёжнее чем shell=True для curl с Bearer токенами

## Паттерн ожидания кода (polling)
```python
import time, re

def wait_for_code(email, password, sender_filter="openai", timeout_sec=120):
    for _ in range(timeout_sec // 5):
        data = fetch_letters(email, password)
        for l in data.get("data", {}).get("letters", []):
            ts = l.get("date", 0)
            sender = l.get("sender", "")
            if time.time() - ts < 300 and sender_filter in sender.lower():
                codes = re.findall(r'\b\d{6}\b', l["letter"].get("text", ""))
                if codes:
                    return codes[0]
        time.sleep(5)
    return None
```

## Ссылки
- Скрипт: `/home/hermes/notletters.py`
- Шаблон скрипта: `templates/notletters_script.py`
- Готовый CLI скрипт: `/home/hermes/notletters.py`
- ChatGPT код приходит за ~5-15 секунд, таймаут 90с достаточно
