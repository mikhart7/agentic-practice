"""Лексический модуль (код r1-03, поведение не менялось): BM25 + триграммный косинус.

Контракт runner арены: stdin {"input", "assets_dir"} -> stdout {"answer": "<JSON-массив до 3 id>"}.
Только стандартная библиотека; источник знаний — только каталог `<assets_dir>/catalog.jsonl`.

Изменения относительно baseline (см. README.md кандидата):
  1. список служебных слов (стоп-слова) убирается из запроса и из документов;
  2. собственный стеммер Портера (без внешних пакетов) на обеих сторонах;
  3. k1 = 1.2 (было 1.5);
  4. слова запроса вне словаря каталога заменяются ближайшим словом каталога (одна правка Дамерау-Левенштейна,
     длина слова от 6) с весом 0.7 — защита от опечаток;
  5. к BM25 (нормированному на максимум по запросу) добавляется 0.6 * косинус tf-idf по символьным триграммам слов.
"""
import json
import math
import re
import sys
from collections import Counter
from pathlib import Path

K1, B, TOP = 1.2, 0.75, 3
FUZZY, FUZZY_MIN = 0.7, 6  # вес слова, исправленного по словарю каталога; минимальная длина слова
NGRAM = 0.6                # вес косинуса tf-idf по символьным триграммам (0 — выключено)

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


def near(a: str, b: str) -> bool:
    """Расстояние Дамерау-Левенштейна не больше 1 (замена, вставка, удаление, перестановка соседних)."""
    if a == b:
        return True
    la, lb = len(a), len(b)
    if abs(la - lb) > 1:
        return False
    if la == lb:
        diff = [i for i in range(la) if a[i] != b[i]]
        if len(diff) == 1:
            return True
        return len(diff) == 2 and diff[1] == diff[0] + 1 and a[diff[0]] == b[diff[1]] and a[diff[1]] == b[diff[0]]
    if la > lb:
        a, b = b, a
    i = 0
    while i < len(a) and a[i] == b[i]:
        i += 1
    return a[i:] == b[i + 1:]


def trigrams(word: str) -> list[str]:
    w = f"^{word}$"
    return [w[i:i + 3] for i in range(len(w) - 2)]


class Catalog:
    """Лексический словарь каталога: нужен для исправления опечаток и символьных триграмм."""

    def __init__(self, catalog: list[dict]):
        self.freq = Counter()
        gram_docs = []
        for c in catalog:
            grams = Counter()
            for w in words(c["name"] + " " + c["description"]):
                self.freq[w] += 1
                if w not in STOP:
                    grams.update(trigrams(w))
            gram_docs.append(grams)
        self.vocab = [w for w in self.freq if len(w) >= 4 and w not in STOP]
        df = Counter(g for d in gram_docs for g in d)
        n = len(catalog)
        self.gidf = {g: math.log(1 + n / f) for g, f in df.items()}
        self.gvec = []
        for d in gram_docs:
            v = {g: (1 + math.log(c)) * self.gidf[g] for g, c in d.items()}
            norm = math.sqrt(sum(x * x for x in v.values())) or 1.0
            self.gvec.append({g: x / norm for g, x in v.items()})

    def correct(self, w: str) -> str | None:
        """Ближайшее по написанию слово каталога (одна правка), чаще встречающееся выигрывает."""
        if len(w) < FUZZY_MIN or not w.isalpha():
            return None
        near_words = [v for v in self.vocab if near(w, v)]
        same_first = [v for v in near_words if v[0] == w[0]]
        cands = same_first or near_words
        return max(cands, key=lambda v: self.freq[v]) if cands else None

    def cosine(self, query: str) -> list[float]:
        grams = Counter()
        for w in words(query):
            if w not in STOP:
                grams.update(trigrams(w))
        v = {g: (1 + math.log(c)) * self.gidf.get(g, 0.0) for g, c in grams.items()}
        norm = math.sqrt(sum(x * x for x in v.values())) or 1.0
        return [sum(x * d.get(g, 0.0) for g, x in v.items()) / norm for d in self.gvec]


class BM25:
    def __init__(self, docs: list[list[str]]):
        self.tfs = [Counter(d) for d in docs]
        self.lens = [len(d) for d in docs]
        self.avg = sum(self.lens) / len(docs)
        df = Counter(t for d in docs for t in set(d))
        n = len(docs)
        self.idf = {t: math.log(1 + (n - f + 0.5) / (f + 0.5)) for t, f in df.items()}

    def scores(self, query: list[str], weight: dict[str, float]) -> list[float]:
        out = []
        for tf, length in zip(self.tfs, self.lens):
            s = 0.0
            for t in query:
                if t in tf:
                    s += weight[t] * self.idf[t] * tf[t] * (K1 + 1) / (tf[t] + K1 * (1 - B + B * length / self.avg))
            out.append(s)
        return out


def query_terms(query: str, index: BM25, cat: Catalog) -> tuple[list[str], dict[str, float]]:
    """Токены запроса; слово вне словаря каталога заменяется ближайшим словом каталога с весом FUZZY."""
    ws = words(query)
    ws = [t for t in ws if t not in STOP] or ws
    out, weight = [], {}
    for w in ws:
        st = PORTER.stem(w)
        if st in index.idf:
            out.append(st)
            weight[st] = 1.0
        elif FUZZY:
            fixed = cat.correct(w)
            st2 = PORTER.stem(fixed) if fixed else None
            if st2 in index.idf:
                out.append(st2)
                weight[st2] = max(weight.get(st2, 0.0), FUZZY)
        else:
            out.append(st)
            weight[st] = 1.0
    return out, weight



class Lexical:
    """Лексические признаки запроса по каталогу: сырой BM25 и косинус триграмм (r1-03 = bm25/max + 0.6 * tri)."""

    def __init__(self, catalog: list[dict]):
        self.index = BM25([tokenize(c["name"] + " " + c["description"]) for c in catalog])
        self.cat = Catalog(catalog)

    def features(self, query: str) -> tuple[list[float], list[float]]:
        qt, weight = query_terms(query, self.index, self.cat)
        return self.index.scores(qt, weight), self.cat.cosine(query)


def r103_score(bm: list[float], tri: list[float]) -> list[float]:
    top = max(bm) or 1.0
    return [s / top + NGRAM * c for s, c in zip(bm, tri)]
