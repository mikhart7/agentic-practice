"""R1 (лексика): BM25 по name + description с нормализацией текста.

Контракт runner арены: stdin {"input", "assets_dir"} -> stdout {"answer": "<JSON-массив до 3 id>"}.
Только стандартная библиотека; источник знаний — только каталог `<assets_dir>/catalog.jsonl`.

Изменения относительно baseline (см. README.md кандидата):
  1. список служебных слов (стоп-слова) убирается из запроса и из документов;
  2. собственный стеммер Портера (без внешних пакетов) на обеих сторонах;
  3. k1 = 1.2 (было 1.5).
"""
import json
import math
import re
import sys
from collections import Counter
from pathlib import Path

K1, B, TOP = 1.2, 0.75, 3

STOP = frozenset(
    "a an and are as at be but by can could do does for from had has have how i if in into is it its just me my "
    "of on or our so some than that the their them then there these they this to up us was we were what when "
    "where which who why will with would you your pls please plz need want like get let help also any all about "
    "out over using use via".split()
)


class Porter:
    """Стеммер Портера (1980), собственная реализация; кэш по слову."""

    def __init__(self):
        self.cache = {}

    @staticmethod
    def _cons(w, i):
        c = w[i]
        if c in "aeiou":
            return False
        if c == "y":
            return i == 0 or not Porter._cons(w, i - 1)
        return True

    @classmethod
    def _m(cls, w):
        n, i, size = 0, 0, len(w)
        while i < size and cls._cons(w, i):
            i += 1
        while i < size:
            while i < size and not cls._cons(w, i):
                i += 1
            if i >= size:
                break
            n += 1
            while i < size and cls._cons(w, i):
                i += 1
        return n

    @classmethod
    def _vowel(cls, w):
        return any(not cls._cons(w, i) for i in range(len(w)))

    @classmethod
    def _dc(cls, w):
        return len(w) >= 2 and w[-1] == w[-2] and cls._cons(w, len(w) - 1)

    @classmethod
    def _cvc(cls, w):
        size = len(w)
        return (size >= 3 and cls._cons(w, size - 1) and not cls._cons(w, size - 2)
                and cls._cons(w, size - 3) and w[-1] not in "wxy")

    def stem(self, w):
        r = self.cache.get(w)
        if r is None:
            r = self.cache[w] = self._stem(w)
        return r

    S2 = [("ational", "ate"), ("tional", "tion"), ("enci", "ence"), ("anci", "ance"), ("izer", "ize"),
          ("abli", "able"), ("alli", "al"), ("entli", "ent"), ("eli", "e"), ("ousli", "ous"),
          ("ization", "ize"), ("ation", "ate"), ("ator", "ate"), ("alism", "al"), ("iveness", "ive"),
          ("fulness", "ful"), ("ousness", "ous"), ("aliti", "al"), ("iviti", "ive"), ("biliti", "ble")]
    S3 = [("icate", "ic"), ("ative", ""), ("alize", "al"), ("iciti", "ic"), ("ical", "ic"), ("ful", ""), ("ness", "")]
    S4 = sorted(["al", "ance", "ence", "er", "ic", "able", "ible", "ant", "ement", "ment", "ent", "ion", "ou",
                 "ism", "ate", "iti", "ous", "ive", "ize"], key=len, reverse=True)

    def _stem(self, w):
        if len(w) <= 2 or not w.isalpha():
            return w
        m, V, dc, cvc = self._m, self._vowel, self._dc, self._cvc
        if w.endswith("sses"):
            w = w[:-2]
        elif w.endswith("ies"):
            w = w[:-2]
        elif w.endswith("ss"):
            pass
        elif w.endswith("s"):
            w = w[:-1]
        flag = False
        if w.endswith("eed"):
            if m(w[:-3]) > 0:
                w = w[:-1]
        elif w.endswith("ed") and V(w[:-2]):
            w, flag = w[:-2], True
        elif w.endswith("ing") and V(w[:-3]):
            w, flag = w[:-3], True
        if flag:
            if w.endswith(("at", "bl", "iz")):
                w += "e"
            elif dc(w) and w[-1] not in "lsz":
                w = w[:-1]
            elif m(w) == 1 and cvc(w):
                w += "e"
        if w.endswith("y") and V(w[:-1]):
            w = w[:-1] + "i"
        for a, b in self.S2:
            if w.endswith(a):
                if m(w[:-len(a)]) > 0:
                    w = w[:-len(a)] + b
                break
        for a, b in self.S3:
            if w.endswith(a):
                if m(w[:-len(a)]) > 0:
                    w = w[:-len(a)] + b
                break
        for a in self.S4:
            if w.endswith(a):
                st = w[:-len(a)]
                if m(st) > 1 and (a != "ion" or (st and st[-1] in "st")):
                    w = st
                break
        if w.endswith("e"):
            st = w[:-1]
            if m(st) > 1 or (m(st) == 1 and not cvc(st)):
                w = st
        if m(w) > 1 and dc(w) and w.endswith("l"):
            w = w[:-1]
        return w


PORTER = Porter()


def words(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", text.lower())


def tokenize(text: str) -> list[str]:
    ws = words(text)
    kept = [t for t in ws if t not in STOP]
    return [PORTER.stem(t) for t in (kept or ws)]


class BM25:
    def __init__(self, docs: list[list[str]]):
        self.tfs = [Counter(d) for d in docs]
        self.lens = [len(d) for d in docs]
        self.avg = sum(self.lens) / len(docs)
        df = Counter(t for d in docs for t in set(d))
        n = len(docs)
        self.idf = {t: math.log(1 + (n - f + 0.5) / (f + 0.5)) for t, f in df.items()}

    def scores(self, query: list[str]) -> list[float]:
        out = []
        for tf, length in zip(self.tfs, self.lens):
            s = 0.0
            for t in query:
                if t in tf:
                    s += self.idf[t] * tf[t] * (K1 + 1) / (tf[t] + K1 * (1 - B + B * length / self.avg))
            out.append(s)
        return out


def solve(task: dict) -> str:
    catalog = [json.loads(line) for line in (Path(task["assets_dir"]) / "catalog.jsonl").open(encoding="utf-8")]
    index = BM25([tokenize(c["name"] + " " + c["description"]) for c in catalog])
    scores = index.scores(tokenize(task["input"]))
    # при равенстве — порядок каталога, чтобы ответ был детерминированным
    ranked = sorted(range(len(catalog)), key=lambda i: (-scores[i], i))
    return json.dumps([catalog[i]["id"] for i in ranked[:TOP]])


if __name__ == "__main__":
    print(json.dumps({"answer": solve(json.load(sys.stdin))}))
