#!/usr/bin/env bash
# Раскладка /srv/arena для кейса AR-04а по таблице «Данные и права» из deploy/README.md арены.
# Запускает оператор: sudo bash case/deploy/stage_srv.sh
# Повторный запуск безопасен: существующие токены и журнал не перезаписываются.
set -euo pipefail

REPO="$(cd "$(dirname "$0")/../.." && pwd)"
OPERATOR_HOME="$(getent passwd "${SUDO_USER:-$USER}" | cut -d: -f6)"
PRIVATE_SRC="${PRIVATE_SRC:-$OPERATOR_HOME/arena-private}"   # public/private от generate.py split
SRV=/srv/arena
UID_ARENA=10001   # пользователь контейнеров арены

[ "$(id -u)" -eq 0 ] || { echo "нужен sudo" >&2; exit 1; }

install -d -m 0755 "$SRV"

# закрытые разделы: только оператор (root) и evaluator (UID 10001)
for split in public private; do
  install -d -m 0700 -o "$UID_ARENA" -g "$UID_ARENA" "$SRV/$split" "$SRV/$split/state" "$SRV/$split/usage"
  install -m 0400 -o "$UID_ARENA" -g "$UID_ARENA" "$PRIVATE_SRC/$split.jsonl" "$SRV/$split/dataset.jsonl"
done

# секреты: отдельный submit-токен на каждый сервис; пустой ключ модели (решатель и метрика без LLM)
install -d -m 0700 -o "$UID_ARENA" -g "$UID_ARENA" "$SRV/secrets"
for name in public-submit-token private-submit-token train-submit-token; do
  [ -s "$SRV/secrets/$name" ] || (umask 077; head -c 32 /dev/urandom | base64 | tr -d '\n' > "$SRV/secrets/$name")
done
[ -e "$SRV/secrets/model-api-key" ] || : > "$SRV/secrets/model-api-key"
chown "$UID_ARENA:$UID_ARENA" "$SRV/secrets"/* && chmod 0400 "$SRV/secrets"/*

# токены, которые получает исследователь (submit-доступ, без операторских полномочий)
install -d -m 0500 -o "$UID_ARENA" -g "$UID_ARENA" "$SRV/researcher-tokens"
for name in public-submit-token private-submit-token train-submit-token; do
  install -m 0400 -o "$UID_ARENA" -g "$UID_ARENA" "$SRV/secrets/$name" "$SRV/researcher-tokens/$name"
done

# assets: каталог и закреплённые модели, только чтение для всех кандидатов
install -d -m 0755 "$SRV/assets"
install -m 0644 "$REPO/case/assets/catalog.jsonl" "$SRV/assets/catalog.jsonl"
rsync -a --delete --chmod=D0755,F0644 "$REPO/case/assets/models/" "$SRV/assets/models/"

# train-сервис: свой неизменяемый экземпляр train (не рабочая копия исследователя), состояние и учёт
install -d -m 0700 -o "$UID_ARENA" -g "$UID_ARENA" "$SRV/trainsvc" "$SRV/trainsvc/state" "$SRV/trainsvc/usage"
install -m 0400 -o "$UID_ARENA" -g "$UID_ARENA" "$REPO/case/dataset/train.jsonl" "$SRV/trainsvc/dataset.jsonl"

# квитанции build, опубликованные материалы, слоты исполнения: пишет только оценщик (UID 10001);
# staging пишет исследователь (материалы для evaluator.assets publish), оценщик читает
install -d -m 0700 -o "$UID_ARENA" -g "$UID_ARENA" "$SRV/builds" "$SRV/slots"
install -d -m 0755 -o "$UID_ARENA" -g "$UID_ARENA" "$SRV/derived" "$SRV/staging"

# журнал кампании и операторский каталог остановки
install -d -m 0700 -o "$UID_ARENA" -g "$UID_ARENA" "$SRV/search"
install -d -m 0700 "$SRV/search-control"

# HOME исследователя (логин Claude Code, транскрипты) — отдельно от HOME оператора
install -d -m 0700 -o "$UID_ARENA" -g "$UID_ARENA" "$SRV/researcher-home"

# чистая исследовательская копия: клон закоммиченного main (public/private в git нет).
# Перед тем как отдать историю исследователю — проверка утечек по всей истории main:
# данные читает root, скрипт работает под оператором.
(cd "$REPO" && cat "$PRIVATE_SRC/public.jsonl" "$PRIVATE_SRC/private.jsonl" \
  | sudo -u "${SUDO_USER:?запускайте через sudo}" python3 scripts/leak_check.py main) \
  || { echo "в истории main найден текст public/private — исследовательская копия не обновлена" >&2; exit 1; }
main_sha="$(git -c safe.directory='*' -C "$REPO" rev-parse main)"
if [ ! -d "$SRV/train/.git" ]; then
  # --no-local: в клон попадают только объекты, достижимые из main, а не весь .git/objects
  git -c safe.directory='*' clone --quiet --no-local --branch main "$REPO" "$SRV/train"
elif ! git -c safe.directory='*' -C "$SRV/train" merge-base --is-ancestor "$main_sha" HEAD 2>/dev/null; then
  # обновить до main; локальные коммиты исследователя не затираются (только fast-forward)
  git -c safe.directory='*' -C "$SRV/train" pull --quiet --ff-only origin main || {
    echo "история $SRV/train расходится с main (переписана?): удалите каталог и запустите снова" >&2; exit 1; }
fi
chown -R "$UID_ARENA:$UID_ARENA" "$SRV/train"

# замороженный пакет метрики кладёт оператор после подготовки:
#   cp -a <campaign_dir>/metric/. /srv/arena/metric/
install -d -m 0755 "$SRV/metric"

echo "готово: $SRV"
find "$SRV" -maxdepth 2 \( -path "$SRV/assets/models" -prune -o -print \) | sort | while read -r p; do
  stat -c '%A %u:%g %n' "$p"
done
