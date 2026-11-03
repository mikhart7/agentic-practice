# Проверка изоляции исследователя — 2026-11-03

Контейнер `researcher` из `compose.yaml` арены (`a28eee3`) с [compose.override.yaml](../../case/deploy/compose.override.yaml), образ `ar04a-researcher:local` (Claude Code 2.1.280), `/srv/arena` разложен [stage_srv.sh](../../case/deploy/stage_srv.sh).

```bash
cd ~/arena && docker compose -f compose.yaml -f $REPO/case/deploy/compose.override.yaml \
  --env-file $REPO/case/deploy/private.env.example --profile train run --rm -T researcher \
  bash /workspace/case/deploy/check_isolation.sh
```

```
uid=10001 gid=10001 groups=10001
OK    не root
OK    нет доступа: /srv/arena
OK    нет доступа: /private
OK    нет доступа: /state
OK    нет доступа: /usage
OK    нет доступа: /search-control
OK    нет доступа: /run/secrets/model-api-key
OK    нет доступа: /srv/arena/secrets
OK    нет доступа: /home/mikhart
OK    нет доступа: /etc/arena
OK    нет доступа: /var/run/docker.sock
OK    нет docker CLI
OK    нет sudo
OK    нет wsl.exe
OK    нет доступа: /mnt/c
OK    нет public.jsonl в рабочих каталогах
OK    нет private.jsonl в рабочих каталогах
OK    нет операторских ARENA_* в окружении
OK    train доступен
OK    журнал /search доступен на запись
OK    submit-токены доступны: private-submit-token public-submit-token train-submit-token
```

Сеть из контейнера:
- `https://api.anthropic.com` достижим (HTTP 405 на GET);
- `host.docker.internal` разрешается.

Доступ к оценщикам (`:8090`, `:8080`, `:8070`) не проверен: они ещё не запущены. Проверить после шага 5 [case/deploy/README.md](../../case/deploy/README.md).
