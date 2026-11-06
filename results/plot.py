"""Графики кампании по выгрузке results/campaign-<N>/: кривая поиска, родословная, private по стилям.

  uv run --no-project --with matplotlib==3.9.2 python results/plot.py results/campaign-1

Входы: journal.json и curve.json (команды арены export и curve), private/slices.md.
Выходы: curve.png, lineage.png, private-styles.png в том же каталоге.
"""
import json
import re
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

# цвета и чернила — референсная палитра (светлая поверхность): серия 1 синяя, база серая
SURFACE, INK, INK2, MUTED = "#fcfcfb", "#0b0b0b", "#52514e", "#898781"
GRID, AXIS = "#e1e0d9", "#c3c2b7"
BLUE, BLUE_LIGHT, BLUE_DARK = "#2a78d6", "#86b6ef", "#1c5cab"

plt.rcParams.update({
    "font.family": "DejaVu Sans", "font.size": 9, "text.color": INK, "axes.labelcolor": INK2,
    "axes.edgecolor": AXIS, "xtick.color": MUTED, "ytick.color": MUTED, "figure.facecolor": SURFACE,
    "axes.facecolor": SURFACE, "savefig.facecolor": SURFACE, "axes.spines.top": False,
    "axes.spines.right": False, "savefig.dpi": 160,
})

DIRECTIONS = {
    "r1": "R1 лексика", "r2": "R2 dense", "r3": "R3 кросс-энкодер", "r4": "R4 гибрид",
    "r5": "R5 центрирование", "r6": "R6 ансамбль", "r7": "R7 комбинация",
    "r8": "R8 ансамбль + лексика", "r9": "R9 граф, GBDT, вентиль", "r10": "R10 обучение на всём train",
}
FINALISTS = {"r10-01", "r9-02", "r6-01", "r4-01", "r5-02"}
WINNERS = {"r9-02", "r10-01"}
NOT_INDEPENDENT = {"r10-01", "r10-02", "r10-03"}  # train_curve входил в обучение


def curve_chart(curve: dict, out: Path) -> None:
    pts = curve["points"]
    fig, ax = plt.subplots(figsize=(8, 4.2))
    ax.grid(axis="y", color=GRID, linewidth=0.6)
    ax.set_axisbelow(True)
    horizon, stop = curve["horizon"], curve["actual_proposals"]
    ax.axvspan(stop, horizon, color=GRID, alpha=0.5, linewidth=0)
    ax.text((stop + horizon) / 2, 0.66, "не\nиспользовано", ha="center", va="center", color=MUTED, fontsize=7.5)
    ax.axhline(curve["baseline"], color=MUTED, linewidth=1, linestyle=(0, (4, 3)))
    ax.text(0.3, curve["baseline"] + 0.006, f"BM25 {curve['baseline']:.3f}", color=INK2, fontsize=8)
    meas = [p for p in pts if p.get("state") == "succeeded"]
    ax.scatter([p["proposals"] for p in meas], [p["score"] for p in meas], s=26, color=SURFACE,
               edgecolors=MUTED, linewidths=1, zorder=3, label="замер кандидата")
    ax.plot([p["proposals"] for p in pts], [p["quality"] for p in pts], drawstyle="steps-post",
            color=BLUE, linewidth=2, zorder=4, label="лучшее к этому моменту")
    best, labelled = curve["baseline"], {"r1-01", "r2-01", "r4-01", "r6-01", "r8-01", "r10-01"}
    for p in meas:
        if p["score"] > best:
            best = p["score"]
            ax.scatter([p["proposals"]], [p["score"]], s=34, color=BLUE, zorder=5)
            if p["candidate_id"] in labelled:
                star = "*" if p["candidate_id"] in NOT_INDEPENDENT else ""
                ax.annotate(f"{p['candidate_id']}{star} {p['score']:.3f}", (p["proposals"], p["score"]),
                            xytext=(-4, 7), textcoords="offset points", ha="right", fontsize=8, color=INK)
    ax.set_xlim(0, horizon)
    ax.set_ylim(0.45, 0.85)
    ax.set_xlabel("предложено решений к моменту окончания замера")
    ax.set_ylabel("score на train_curve (200)")
    ax.set_title(f"Кривая поиска c1: AUC {curve['auc']:.2f} до горизонта {horizon}, "
                 f"mean_quality {curve['mean_quality']:.3f}", loc="left", fontsize=10)
    ax.legend(loc="upper left", frameon=False, fontsize=8)
    fig.text(0.01, 0.01, "* r10: запросы train_curve входили в обучение, замер не независим. "
             "У r9-02 замера нет (сбой оценщика).", color=MUTED, fontsize=7)
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    fig.savefig(out)
    plt.close(fig)


def lineage_chart(journal: dict, out: Path) -> None:
    cands = journal["candidates"]
    curve_score = {}
    for m in journal["measurements"]:
        if m["measurement_id"].endswith("-curve") and m["state"] == "succeeded":
            curve_score[m["candidate_id"]] = m["score"]
    lanes = list(DIRECTIONS)
    pos = {c["candidate_id"]: (c["proposal"], lanes.index(c["candidate_id"].split("-")[0])) for c in cands}
    fig, ax = plt.subplots(figsize=(13, 5.8))
    for y in range(len(lanes)):
        ax.axhline(y, color=GRID, linewidth=0.6, zorder=0)
    for c in cands:
        x1, y1 = pos[c["candidate_id"]]
        for parent in c["parents"]:
            x0, y0 = pos[parent]
            ax.annotate("", (x1, y1), (x0, y0), zorder=1, arrowprops=dict(
                arrowstyle="-|>", color=AXIS, linewidth=1, shrinkA=7, shrinkB=7, mutation_scale=8,
                connectionstyle="arc3,rad=0.15" if y0 != y1 else "arc3,rad=0"))
    styles = {"winner": (BLUE, BLUE_DARK), "finalist": (BLUE_LIGHT, BLUE), "other": (SURFACE, MUTED)}
    for c in cands:
        cid = c["candidate_id"]
        x, y = pos[cid]
        kind = "winner" if cid in WINNERS else "finalist" if cid in FINALISTS else "other"
        face, edge = styles[kind]
        ax.scatter([x], [y], s=120, color=face, edgecolors=edge, linewidths=1.5, zorder=3)
        ax.text(x, y - 0.3, cid, ha="center", va="bottom", fontsize=6.5, color=INK,
                fontweight="bold" if kind == "winner" else "normal")
        s = curve_score.get(cid)
        txt = "—" if s is None else f"{s:.3f}" + ("*" if cid in NOT_INDEPENDENT else "")
        ax.text(x, y + 0.3, txt, ha="center", va="top", fontsize=6.5, color=MUTED)
    for kind, label in [("winner", "выбран на private (N = 2)"), ("finalist", "финалист (K = 5)"),
                        ("other", "кандидат")]:
        face, edge = styles[kind]
        ax.scatter([], [], s=80, color=face, edgecolors=edge, linewidths=1.5, label=label)
    ax.set_yticks(range(len(lanes)), [DIRECTIONS[d] for d in lanes])
    ax.invert_yaxis()
    ax.set_xticks(range(1, len(cands) + 1))
    ax.set_xlim(0.3, len(cands) + 0.7)
    ax.set_ylim(len(lanes) - 0.4, -0.7)
    ax.tick_params(axis="y", length=0, labelcolor=INK2)
    ax.spines["left"].set_visible(False)
    ax.set_xlabel("номер предложенного решения")
    ax.set_title("Родословная кандидатов c1: стрелка от родителя к потомку; под узлом — score на train_curve",
                 loc="left", fontsize=10)
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.11), ncol=3, frameon=False, fontsize=8)
    fig.text(0.01, 0.01, "* r10: train_curve входил в обучение. «—»: замера на train_curve нет "
             "(r5-03 и r8-02 эквивалентны родителю, у r9-02 сбой оценщика).", color=MUTED, fontsize=7)
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    fig.savefig(out)
    plt.close(fig)


def private_chart(slices_md: Path, out: Path) -> None:
    rows = [[c.strip() for c in line.strip().strip("|").split("|")]
            for line in slices_md.read_text(encoding="utf-8").splitlines() if line.startswith("|")]
    header, body = rows[0], [r for r in rows[2:]]
    col = {name: i for i, name in enumerate(header)}
    bm25, best = col["BM25"], next(i for i, h in enumerate(header) if h.startswith("r9-02"))

    def num(cell: str) -> float:
        return float(re.sub(r"[^0-9.]", "", cell))

    data = {r[0]: (int(r[1]), num(r[bm25]), num(r[best])) for r in body if r[0] != "не hard"}
    order = ["все", "hard"] + sorted((k for k in data if k.startswith("style=")), key=lambda k: -data[k][1])
    fig, ax = plt.subplots(figsize=(7.5, 3.8))
    for y, key in enumerate(order):
        n, a, b = data[key]
        ax.plot([a, b], [y, y], color=AXIS, linewidth=2, zorder=1, solid_capstyle="round")
        ax.scatter([a], [y], s=60, color=MUTED, edgecolors=SURFACE, linewidths=2, zorder=2)
        ax.scatter([b], [y], s=60, color=BLUE, edgecolors=SURFACE, linewidths=2, zorder=3)
        ax.text(a - 0.015, y, f"{a:.3f}", ha="right", va="center", fontsize=7.5, color=INK2)
        ax.text(b + 0.015, y, f"{b:.3f}  (+{b - a:.2f})", ha="left", va="center", fontsize=7.5, color=INK)
    ax.scatter([], [], s=60, color=MUTED, label="BM25 (baseline)")
    ax.scatter([], [], s=60, color=BLUE, label="r9-02 (1-е место)")
    labels = [f"{k.removeprefix('style=')} ({data[k][0]})" for k in order]
    ax.set_yticks(range(len(order)), labels)
    ax.invert_yaxis()
    ax.set_xlim(0, 1.12)
    ax.set_xticks([0, 0.2, 0.4, 0.6, 0.8, 1.0])
    ax.grid(axis="x", color=GRID, linewidth=0.6)
    ax.set_axisbelow(True)
    ax.tick_params(axis="y", length=0, labelcolor=INK2)
    ax.spines["left"].set_visible(False)
    ax.set_xlabel("score на private, 0.7·acc@1 + 0.3·nP@3")
    ax.set_title("Private по срезам: где выращенное решение обгоняет BM25", loc="left", fontsize=10)
    ax.legend(loc="upper left", frameon=False, fontsize=8)
    fig.tight_layout()
    fig.savefig(out)
    plt.close(fig)


def main() -> None:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else "results/campaign-1")
    journal = json.loads((root / "journal.json").read_text(encoding="utf-8"))
    curve = json.loads((root / "curve.json").read_text(encoding="utf-8"))
    curve_chart(curve, root / "curve.png")
    lineage_chart(journal, root / "lineage.png")
    private_chart(root / "private/slices.md", root / "private-styles.png")
    print("written:", ", ".join(str(root / n) for n in ("curve.png", "lineage.png", "private-styles.png")))


if __name__ == "__main__":
    main()
