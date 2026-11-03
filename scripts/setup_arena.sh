#!/usr/bin/env bash
# Арена из GitLab на закреплённом коммите + подключение нашего кейса как cases/ar04a-skill-select.
#   bash scripts/setup_arena.sh [каталог арены, по умолчанию ~/arena]
# Код арены не копируется в репозиторий и не изменяется: кейс подключается символической ссылкой,
# поэтому всё, что агент подготовки пишет в cases/ar04a-skill-select/campaigns/, попадает в наш git.
set -euo pipefail

ARENA_URL=https://gitlab.deeppavlov.ai/deeppavlov/arena.git
ARENA_COMMIT=a28eee3abd72d5af3445e718b0253ff7147b8d45
CASE_ID=ar04a-skill-select
REPO="$(cd "$(dirname "$0")/.." && pwd)"
ARENA_DIR="${1:-$HOME/arena}"

if [ ! -d "$ARENA_DIR/.git" ]; then
  git clone --quiet "$ARENA_URL" "$ARENA_DIR"
fi
# в сеть — только если закреплённого коммита ещё нет локально
git -C "$ARENA_DIR" cat-file -e "$ARENA_COMMIT^{commit}" 2>/dev/null || git -C "$ARENA_DIR" fetch --quiet origin
git -C "$ARENA_DIR" checkout --quiet --detach "$ARENA_COMMIT"
if [ -n "$(git -C "$ARENA_DIR" status --porcelain --untracked-files=no)" ]; then
  echo "в $ARENA_DIR изменены файлы арены — откатите их, мы используем арену без изменений" >&2
  exit 1
fi

link="$ARENA_DIR/cases/$CASE_ID"
if [ -L "$link" ]; then
  ln -sfn "$REPO/case" "$link"
elif [ -e "$link" ]; then
  echo "$link существует и не является ссылкой — разберитесь вручную" >&2
  exit 1
else
  ln -s "$REPO/case" "$link"
fi
# ссылка — наша локальная настройка, не часть арены
grep -qxF "/cases/$CASE_ID" "$ARENA_DIR/.git/info/exclude" || echo "/cases/$CASE_ID" >> "$ARENA_DIR/.git/info/exclude"

(cd "$ARENA_DIR" && uv sync --frozen --quiet)
echo "арена: $(git -C "$ARENA_DIR" log --oneline -1)"
echo "кейс:  $link -> $(readlink "$link")"
