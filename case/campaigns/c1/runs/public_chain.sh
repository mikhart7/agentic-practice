#!/bin/bash
# последовательные public-проверки (по одной), лог на каждую
cd /workspace/case/campaigns/c1
for c in "$@"; do
  python tools/public.py --candidate "$c" > "runs/$c-public.log" 2>&1
  echo "$c exit=$?" >> runs/public_chain.log
done
