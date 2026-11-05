#!/usr/bin/env bash
# Проверка границы закрытых данных ИЗНУТРИ контейнера исследователя (common/isolation.md арены).
# Запуск оператором:
#   docker compose -p arena-ar04a -f <repo>/case/deploy/compose.campaign.yaml \
#     --env-file /etc/arena/campaign.env --profile research run --rm researcher \
#     bash /workspace/case/deploy/check_isolation.sh
# Каждая строка должна быть OK; вывод сохраняется в <campaign_dir>/preparation.md.
set -u
fail=0
ok()  { echo "OK    $*"; }
bad() { echo "FAIL  $*"; fail=1; }
absent() { if [ -e "$1" ]; then bad "доступно: $1"; else ok "нет доступа: $1"; fi; }

echo "uid=$(id -u) gid=$(id -g) groups=$(id -G)"
[ "$(id -u)" != 0 ] && ok "не root" || bad "работает от root"

# закрытые данные, состояние оценщиков, секреты и операторские каталоги не смонтированы
for p in /srv/arena /private /state /usage /search-control /run/secrets/model-api-key \
         /srv/arena/secrets /home/mikhart /etc/arena; do absent "$p"; done

# управление хостом: docker socket, docker CLI, sudo, выход в Windows (WSL interop)
absent /var/run/docker.sock
command -v docker >/dev/null && bad "есть docker CLI" || ok "нет docker CLI"
command -v sudo   >/dev/null && bad "есть sudo"       || ok "нет sudo"
command -v wsl.exe >/dev/null && bad "есть wsl.exe"   || ok "нет wsl.exe"
absent /mnt/c

# public/private-данные не лежат в рабочей копии (их хеши — в case/dataset/generation_report.md)
for name in public private; do
  hits=$(find /workspace /search /home/researcher -name "${name}.jsonl" -o -name "${name}.meta.jsonl" 2>/dev/null | wc -l)
  [ "$hits" = 0 ] && ok "нет ${name}.jsonl в рабочих каталогах" || bad "найден ${name}.jsonl"
done

# операторские переменные окружения не переданы
env | grep -qE '^ARENA_(DATASET_PATH|STATE_DIR|USAGE_DIR|MODEL_API_KEY_FILE|SUBMIT_TOKEN_FILE)=' \
  && bad "в окружении операторские ARENA_*" || ok "нет операторских ARENA_* в окружении"

# исследователю разрешено: train, журнал, submit-токены
[ -r /workspace/case/dataset/train.jsonl ] && ok "train доступен" || bad "train недоступен"
[ -w /search ] && ok "журнал /search доступен на запись" || bad "/search недоступен"
ls /run/secrets/arena/ >/dev/null 2>&1 && ok "submit-токены доступны: $(ls /run/secrets/arena | tr '\n' ' ')" \
  || bad "нет submit-токенов"

# материалы: каталог и модели, опубликованные результаты build — только чтение; staging — запись
for p in /assets /derived; do
  if [ ! -d "$p" ]; then bad "не смонтирован: $p"; elif [ -w "$p" ]; then bad "доступен на запись: $p"; else ok "только чтение: $p"; fi
done
[ -d /staging ] && [ -w /staging ] && ok "staging доступен на запись" || bad "staging не смонтирован или недоступен на запись"
for name in model-api-key; do absent "/run/secrets/arena/$name"; done
bad_tokens=$(ls /run/secrets/arena 2>/dev/null | grep -v -E '^(public|private|train)-submit-token$' | wc -l)
[ "$bad_tokens" = 0 ] && ok "в /run/secrets/arena только submit-токены" || bad "лишние файлы в /run/secrets/arena"

exit $fail
