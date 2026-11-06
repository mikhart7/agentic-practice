"""Энкодер BERT на numpy: токенайзер `tokenizers` + веса safetensors, без torch и transformers.

Нужен, чтобы одноразовый контейнер solve не платил за импорт torch (секунды) ради кодирования одного короткого запроса.
Совпадение с sentence-transformers проверяет build (report.json).
v2: веса читаются последовательно (без page-fault по memmap), без импорта scipy (erf — полином Абрамовица-Стегана).
"""
import json
import math
import struct
from pathlib import Path

import numpy as np

_DT = {"F32": np.float32, "F16": np.float16}
_SKIP = ("pooler.", "position_ids")


def read_safetensors(path):
    """Читает safetensors без зависимостей: заголовок JSON + сырые байты, последовательное чтение нужных тензоров."""
    out = {}
    with open(path, "rb") as f:
        n = struct.unpack("<Q", f.read(8))[0]
        header = json.loads(f.read(n))
        base = 8 + n
        items = sorted(((k, v) for k, v in header.items() if k != "__metadata__" and v["dtype"] in _DT
                        and not any(s in k for s in _SKIP)), key=lambda kv: kv[1]["data_offsets"][0])
        for k, v in items:
            a, b = v["data_offsets"]
            f.seek(base + a)
            buf = np.frombuffer(f.read(b - a), dtype=_DT[v["dtype"]]).reshape(v["shape"])
            out[k] = buf.astype(np.float32, copy=False)
    return out


def _erf(x):
    # Abramowitz-Stegun 7.1.26, |ошибка| < 1.5e-7
    s = np.sign(x)
    a = np.abs(x)
    t = 1.0 / (1.0 + 0.3275911 * a)
    poly = ((((1.061405429 * t - 1.453152027) * t) + 1.421413741) * t - 0.284496736) * t + 0.254829592
    return s * (1.0 - poly * t * np.exp(-a * a))


def _gelu(x):
    return 0.5 * x * (1.0 + _erf(x * np.float32(1 / math.sqrt(2))))


def _ln(x, w, b, eps):
    mu = x.mean(-1, keepdims=True)
    var = ((x - mu) ** 2).mean(-1, keepdims=True)
    return (x - mu) / np.sqrt(var + eps) * w + b


class Encoder:
    def __init__(self, model_dir, pooling, max_len=512):
        from tokenizers import Tokenizer
        model_dir = Path(model_dir)
        cfg = json.loads((model_dir / "config.json").read_text())
        self.heads = cfg["num_attention_heads"]
        self.layers = cfg["num_hidden_layers"]
        self.eps = cfg.get("layer_norm_eps", 1e-12)
        self.pooling = pooling
        self.tok = Tokenizer.from_file(str(model_dir / "tokenizer.json"))
        self.tok.enable_truncation(max_length=max_len)
        self.tok.enable_padding(pad_id=self.tok.token_to_id("[PAD]") or 0, pad_token="[PAD]")
        self.w = read_safetensors(model_dir / "model.safetensors")

    def _layer(self, x, mask_bias, i):
        w, p = self.w, f"encoder.layer.{i}."
        B, T, H = x.shape
        d = H // self.heads

        def lin(name, h):
            return h @ w[p + name + ".weight"].T + w[p + name + ".bias"]

        def split(h):
            return h.reshape(B, T, self.heads, d).transpose(0, 2, 1, 3)

        q, k, v = split(lin("attention.self.query", x)), split(lin("attention.self.key", x)), split(lin("attention.self.value", x))
        att = q @ k.transpose(0, 1, 3, 2) / math.sqrt(d) + mask_bias
        att = np.exp(att - att.max(-1, keepdims=True))
        att /= att.sum(-1, keepdims=True)
        ctx = (att @ v).transpose(0, 2, 1, 3).reshape(B, T, H)
        x = _ln(lin("attention.output.dense", ctx) + x, w[p + "attention.output.LayerNorm.weight"], w[p + "attention.output.LayerNorm.bias"], self.eps)
        h = _gelu(lin("intermediate.dense", x))
        return _ln(lin("output.dense", h) + x, w[p + "output.LayerNorm.weight"], w[p + "output.LayerNorm.bias"], self.eps)

    def encode(self, texts, batch=16):
        out = []
        for s in range(0, len(texts), batch):
            encs = self.tok.encode_batch(texts[s: s + batch])
            ids = np.array([e.ids for e in encs], dtype=np.int64)
            mask = np.array([e.attention_mask for e in encs], dtype=np.float32)
            w = self.w
            x = w["embeddings.word_embeddings.weight"][ids] + w["embeddings.position_embeddings.weight"][: ids.shape[1]][None] \
                + w["embeddings.token_type_embeddings.weight"][0][None, None]
            x = _ln(x, w["embeddings.LayerNorm.weight"], w["embeddings.LayerNorm.bias"], self.eps).astype(np.float32)
            mask_bias = ((1.0 - mask) * -1e9)[:, None, None, :].astype(np.float32)
            for i in range(self.layers):
                x = self._layer(x, mask_bias, i)
            if self.pooling == "cls":
                e = x[:, 0]
            else:
                e = (x * mask[:, :, None]).sum(1) / np.maximum(mask.sum(1, keepdims=True), 1e-9)
            out.append(e / np.maximum(np.linalg.norm(e, axis=1, keepdims=True), 1e-12))
        return np.concatenate(out).astype(np.float32)
