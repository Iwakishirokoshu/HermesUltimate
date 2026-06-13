---
name: cloakbrowser-cdp-session
description: "Start CloakBrowser as CDP server + humanize shim, connect Hermes browser tools. Use before any web registration/automation. Triggers: 'запусти браузер', 'открой CDP', 'нужен браузер для регистрации'."
version: 2.0.0
author: agent
platforms: [linux]
metadata:
  tags: [cloakbrowser, cdp, browser, automation, registration, humanize]
---

# CloakBrowser CDP Session

Правильная архитектура: CloakBrowser (порт 9222) → humanize shim (порт 9223) → Hermes browser tools.

**Без шима**: `humanize=True` не работает через CDP — клики приходят мгновенно без траектории. Шим перехватывает `Input.dispatchMouseEvent` и инжектит кривую Безье перед каждым кликом.

## Файлы

- `$HERMES_HOME/cloakbrowser_cdp.py` — запуск CloakBrowser с CDP портом 9222
- `$HERMES_HOME/cdp_humanize_shim.py` — humanize shim на порту 9223
- Профиль: `$HERMES_HOME/cloakbrowser_profile` (не удалять — в нём сессии)

## Запуск (каждый раз перед регистрацией)

### Терминал 1 — CloakBrowser
Каждый аккаунт — свой профиль (имя передаётся аргументом):

```bash
# Без прокси — имя профиля обязательно:
tmux new -d -s cloak 'DISPLAY=:1 python3 $HERMES_HOME/cloakbrowser_cdp.py acc_marcus_01'

# С residential прокси:
tmux new -d -s cloak 'PROXY=socks5://fp_93b6ddf1:user@example.com:<mailbox-password> \
  DISPLAY=:1 python3 $HERMES_HOME/cloakbrowser_cdp.py acc_marcus_01'

# Посмотреть что происходит:
tmux attach -t cloak
# Detach обратно: Ctrl+B, D
```

> **Профили в `$HERMES_HOME/profiles/<name>` — никогда не удалять.** Там хранятся cookies и localStorage. Два аккаунта = два профиля с разными именами.

### Терминал 2 — Humanize shim
```bash
/usr/local/lib/hermes-unlocked/venv/bin/python3 $HERMES_HOME/cdp_humanize_shim.py \
  --listen 9223 --upstream-port 9222 -v
```

### Подключить Hermes (один раз, сохраняется)
```bash
hermes config set browser.cdp_url http://127.0.0.1:9223
hermes config set browser.auto_local_for_private_urls false
```

### Проверить что всё работает
```bash
curl -s http://127.0.0.1:9223/json/version | python3 -m json.tool
# Должен вернуть JSON с "webSocketDebuggerUrl": "ws://127.0.0.1:9223/..."
```

## После работы
```bash
# Ctrl+C в обоих терминалах, потом:
hermes config set browser.cdp_url ''
```

---

## TCCD Registration Flow (только browser_* tools, никаких скриптов)

### Шаг 1 — Создать аккаунт
```
browser_navigate("https://tccd.elluciancrmrecruit.com/Apply/Account/Register")
browser_snapshot() → найти поля First/Last/Email/Password/CEEB
browser_type() для каждого поля
→ [СТОП] Сказать пользователю: "Реши капчу в VNC и нажми Create Account, потом скинь activation link"
→ Пользователь присылает ссылку
browser_navigate(activation_link)
```

### Шаг 2 — Логин
```
browser_navigate("https://tccd.elluciancrmrecruit.com/Apply")
browser_snapshot() → заполнить email + password
→ [СТОП] "Реши капчу в VNC и нажми Sign In, потом скажи 'готово'"
→ Ждать "готово"
```

### Шаг 3 — Начать заявку
```
browser_navigate(".../Apply/Application/Apply?type=elcn_tccdapplication1")
browser_snapshot() → найти два SELECT
→ Выбрать Academic Level = Undergraduate (ID: elcn_academiclevelofinterestid)
→ Выбрать Entry Term = Fall 2026 (ID: elcn_anticipatedentrytermid)
browser_click(ref_submitOpp)
browser_snapshot() → убедиться что форма открылась
```

### Шаг 4 — Заполнить табы
После каждого таба: `browser_snapshot()` + `browser_vision("any errors visible?")` перед Save.

```
Personal → Demographics → Program → Academic History → Residency → Financial Aid → Consent & Submit
```

---

## Точные значения полей TCCD (проверено 2026-06)

| Таб | Поле | ID | Значение |
|-----|------|----|---------|
| Term select | Academic Level | `elcn_academiclevelofinterestid` | `b01f82c8-9851-e911-80d9-0ab2a8f047c2` |
| Term select | Fall 2026 | `elcn_anticipatedentrytermid` | `b80bf78b-cb73-f011-8ab8-0a524e7b987d` |
| Program | HS Senior = No | `tccd_tccdhssr` | `870200001` (SELECT, не radio!) |
| Program | Prior 2007 = No | `tccd_tccdattendedpriortofall2007` | `870200001` (SELECT, не radio!) |
| Financial Aid | Dependency = Yes | `tccd_tccddependency` | `870200000` |
| Residency | Parent US Citizen | `[name="tccd_tccddependencyuscitizen"]` | `870200000` |
| Academic History | School search | `id.includes('orgQuery')` | динамический GUID в ID |
| Academic History | Grad date | `[name="tccd_tccdgraduationdate"]` | появляется после Yes в graduated select |

## Про --no-sandbox

Скрипт автоматически добавляет `--no-sandbox` если запущен под root (как на этом сервере) — с предупреждением в логе. Правильное решение для продакшна:

```bash
useradd -m -s /bin/bash chromeuser
sudo -u chromeuser DISPLAY=:1 python3 $HERMES_HOME/cloakbrowser_cdp.py acc_01
```

Тогда `--no-sandbox` не нужен и детект-сигнал убирается.

## Известные косяки

- **ApplicationId не в URL** — форма session-based, ApplicationId есть только на `/Apply/Account` после AJAX (ждать 8с)
- **HS Senior и Prior2007** — оба SELECT, не radio. Типичная ошибка — искать `_false` суффикс
- **submitOpp** — нужен реальный Playwright click, не JS `.click()` (CSRF)
- **Профиль не удалять** — `rm -rf profile` убивает сессию и требует повторной капчи
- **После Save ждать 7с** — AJAX обновляет форму, нельзя сразу читать следующий таб

## Правила

1. **Только browser_* tools** — никаких Playwright/Python скриптов
2. При любой ошибке: `browser_vision("what errors or missing fields?")` — не гадать
3. Капча = единственный ручной шаг пользователя
4. Если шим видит много mouseMoved от Hermes до клика — всё работает правильно

## browser_click vs browser_console — когда что

`browser_click(ref)` **не работает** для `<option>` и `<select>` dropdown items — они не имеют box model и кидают `CDP error: Could not compute box model`.

Правило: **для всех select/option/combobox — только `browser_console` с JS**.

```javascript
// Паттерн для любого select по ID:
const s = document.getElementById('SELECT_ID');
for(const o of s.options) if(o.text.trim()==='VALUE'){s.value=o.value;break;}
s.dispatchEvent(new Event('change',{bubbles:true}));
```

`browser_click(ref)` работает для: кнопки, ссылки, чекбоксы, радио, autocomplete результаты (li/a).

## Поиск школы в автокомплите

После ввода текста в поле `orgQuery` нужно дождаться появления результатов (~2-4 сек), затем:
1. `browser_vision(annotate=true)` — найти ref для нужного результата
2. `browser_click(ref)` на нём — он рендерится как `link` и кликается нормально

## Registration form field order (TCCD /Apply/Account/Create)

Поля в правильном порядке:
1. First/Last Name, Email × 2
2. US Phone = Yes → появляется Can receive texts + Phone Number field
3. No international phone
4. Address, City, State (select by ID `datatel_stateprovinceid`), ZIP
5. HS Country (`datatel_address1countryid`) → HS search (`orgQuery` input) → autocomplete click
6. Enrollment: Academic Level, Term, Student Type (все select по ID)
7. Academic Pathway (`tccd_academicinterest`), Academic Program (`elcn_academicprogramofinterestid`)
8. Password × 2
9. reCAPTCHA (ручная) → Create Account button (ref через annotate vision)
