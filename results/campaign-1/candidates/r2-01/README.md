# r2-01: dense bi-encoder (bge-base-en-v1.5), эмбеддинги каталога в build, быстрый solve на numpy

## Гипотеза
BM25 не находит навык, когда запрос не содержит слов описания (`indirect` ~0.11 acc@1). Bi-encoder сопоставляет смысл. bge-base-en-v1.5 — самая сильная из разрешённых bi-encoder моделей; взят как опорная точка семейства dense.
Вторая гипотеза (инженерная): время solve определяется импортом torch и загрузкой модели в одноразовом контейнере; для одного короткого запроса forward BERT на numpy (tokenizers + safetensors + numpy) даёт те же векторы без torch.

## Механизм
- `build.py`: кодирует `"{name}. {description}"` каждого навыка энкодером на numpy (`enc.py`), сверяет его с `sentence_transformers` (min cos документов и тестовых запросов, совпадение топ-5 на 4 тестовых запросах; пишет в `report.json`). Если cos < 0.999, в `emb.npy` кладутся эталонные векторы, а solve переключается на sentence-transformers (`numpy_encoder_ok=false`). Выход: `emb.npy`, `ids.json`, `config.json`, `report.json`.
- `solve.py`: читает `/assets/prepared`, кодирует только запрос (`enc.py`, модель из `/assets/models/bge-base-en-v1.5`), косинус, топ-3. При любой ошибке numpy-пути — резерв через sentence-transformers.
- `params.json`: модель, пулинг (cls), префиксы (пусто), шаблон документа.

## Изменения относительно baseline
BM25 заменён на dense; добавлены `build.py`, `enc.py`, `params.json`.

## Происхождение train-сведений
Нет: train в пакете и в build не используется, обучения нет. Только каталог и закреплённая модель.
