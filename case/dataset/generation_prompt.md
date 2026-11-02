# Промпт генерации запросов

Открытых наборов «запрос пользователя → навык» для нашего каталога нет. Поэтому пул запросов сгенерировала LLM (Claude Opus 5.5, `claude-opus-5-5`, в сеансе Claude Code, 2026-11-02) по промпту ниже. Промпт записан **до** генерации, и генерация шла строго по нему. Модель видела каталог (`id`, `name`, `description`) и разметку кластеров из `catalog_meta.jsonl`.

Генерация в сеансе не воспроизводится командой. Поэтому сырой пул сохранён как артефакт, а в [generation_report.md](generation_report.md) записан его sha256. Всё дальнейшее детерминировано: [generate.py](generate.py) проверяет пул, строит записи и делит их на split по сиду.

---

## Промпт

> You are building an evaluation set for a skill router: given a user request and a fixed catalog of ~190 agent skills (MCP servers, each with a name and a ≤100-character description), the router must pick the right skill.
>
> For **every skill** in the catalog write **2 intents**: two different, realistic things a user might want that this skill is the best fit for. Prefer two different capabilities from the description (e.g. forecast vs. air quality). Each intent is one **family**. For each family write **4 user queries** that express the same intent, each in a **different style**.
>
> Styles (use 4 different ones per family; `indirect` is mandatory in every family):
> - `cmd`: short imperative or keyword-like command, 3–8 words ("merge these pdfs into one").
> - `verbose`: 1–2 sentences with situational context and incidental details.
> - `indirect`: describes the goal or situation **without the distinctive words** of the skill's name/description (no product names, no key nouns like "PDF", "Slack", "OCR" if they appear in the description); the user knows what they want, not what it is called.
> - `casual`: informal chat tone, slang or abbreviations.
> - `typo`: lowercase, 1–3 realistic typos or missing words.
> - `question`: phrased as a question ("is there a way to…", "how do I…").
>
> Rules:
> 1. English only. Queries are what a user types to an agent, not descriptions of tools. Never mention the skill id or "MCP".
> 2. The query must be answerable by the intended skill **as described** — do not invent capabilities the description does not support.
> 3. Hard negatives matter: when the skill has close neighbours in its cluster, include in at least 2 of the 4 queries the detail that distinguishes it (platform, region, read-only vs. write, local vs. hosted, etc.), and in the other queries keep it natural — ambiguity is allowed but must be reflected in `accept`.
> 4. `accept`: list other catalog skills that would **also fully satisfy** this intent as written in all 4 queries (be honest and conservative; a sibling that only partially fits is not acceptable). Empty if none.
> 5. Do not reuse the same query skeleton across families; vary vocabulary, length and entities (file names, cities, tickers, repo names).
>
> Output format (one block per family):
> ```
> @ <skill_id> | accept: <id>,<id> | intent: <short intent description>
> <style>: <query>
> <style>: <query>
> <style>: <query>
> <style>: <query>
> ```

---

## Почему так

- **2 намерения × 4 перефразы.** Семейство — единица деления на split. Перефразы одного намерения никогда не попадают в разные split, поэтому заучить формулировки из train не получится. Два намерения на навык дают для каждого навыка одно семейство в train и одно в public или private: см. [README.md](README.md).
- **Стили.** Это требование ТЗ к синтетике: разнообразный генератор, несколько шаблонов, шум (опечатки). Стиль `indirect` обязателен, потому что без него запросы лексически повторяют описания, и BM25 упрётся в потолок.
- **`accept`** — множество допустимых навыков (ADR о метрике). Оно делает честным acc@1 на неоднозначных запросах внутри кластера.
- **Известное ограничение.** Запросы и каталог видел один генератор. Возможен перекос в его стиле, а реальных запросов для сверки нет. Смягчение — ручная проверка выборки (см. [generation_report.md](generation_report.md)) и предложение дописать небольшой набор запросов вручную как внешнюю проверку.
