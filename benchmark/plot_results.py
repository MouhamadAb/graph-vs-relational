"""Erzeugt Diagramme aus den results/-CSV-Dateien.

Liest, was an Ergebnissen vorhanden ist - fehlende Dateien werden einfach
uebersprungen (kein Fehler), damit das Skript auch mit einem Teil-Datensatz
an Messungen laeuft.

Bewusst OHNE logarithmische Achsen: fuer ein Laien-Publikum ist eine
Log-Skala schwer zu lesen (gleicher Abstand = "mal 10", nicht "plus 10").
Stattdessen werden Werte mit sehr unterschiedlicher Groessenordnung (vor
allem T5, das alle anderen Werte um das > 1000-fache uebersteigt) in
eigene Diagramme ausgelagert, und jeder Balken bekommt seine Zahl direkt
als Beschriftung - so bleibt alles in normalen Millisekunden/Sekunden
ablesbar, auch wenn ein Balken auf der Achse winzig erscheint.
"""

import csv
import re
import statistics
from pathlib import Path

import matplotlib.pyplot as plt

RESULTS_DIR = Path(__file__).resolve().parent.parent / "results"
PLOTS_DIR = RESULTS_DIR / "plots"

PG_COLOR = "#336791"
NEO_COLOR = "#E8720C"


def read_csv(path: Path) -> list[dict]:
    with path.open() as f:
        return list(csv.DictReader(f))


def mean_by_system(rows: list[dict]) -> dict[str, float]:
    out = {}
    for system in ("postgres", "neo4j"):
        values = [float(r["duration_ms"]) for r in rows if r["system"] == system]
        if values:
            out[system] = statistics.mean(values)
    return out


def label_bars(ax, bars, fmt: str) -> None:
    """Schreibt den Wert jedes Balkens als Zahl direkt darueber."""
    for bar in bars:
        height = bar.get_height()
        ax.annotate(
            fmt.format(height),
            xy=(bar.get_x() + bar.get_width() / 2, height),
            xytext=(0, 3),
            textcoords="offset points",
            ha="center",
            va="bottom",
            fontsize=9,
        )


def grouped_bar_chart(labels, pg_values, neo_values, *, ylabel, title, unit_fmt="{:.0f} ms") -> plt.Figure:
    x = range(len(labels))
    width = 0.35
    fig, ax = plt.subplots(figsize=(7.5, 5))
    bars_pg = ax.bar([i - width / 2 for i in x], pg_values, width, label="PostgreSQL", color=PG_COLOR)
    bars_neo = ax.bar([i + width / 2 for i in x], neo_values, width, label="Neo4j", color=NEO_COLOR)
    ax.set_xticks(list(x))
    ax.set_xticklabels(labels)
    ax.set_ylabel(ylabel)
    ax.set_title(title)
    ax.legend()
    ax.margins(y=0.15)  # Platz fuer die Zahlen-Beschriftung ueber den Balken
    label_bars(ax, bars_pg, unit_fmt)
    label_bars(ax, bars_neo, unit_fmt)
    fig.tight_layout()
    return fig


def save(fig: plt.Figure, filename: str) -> None:
    PLOTS_DIR.mkdir(exist_ok=True)
    out_path = PLOTS_DIR / filename
    fig.savefig(out_path)
    plt.close(fig)
    print(f"Gespeichert: {out_path}")


def collect_query_means(query_ids: list[str]) -> tuple[list[str], list[float], list[float]]:
    labels, pg_means, neo_means = [], [], []
    for qid in query_ids:
        path = RESULTS_DIR / f"{qid}.csv"
        if not path.exists():
            continue
        means = mean_by_system(read_csv(path))
        if not means:
            continue
        labels.append(qid)
        pg_means.append(means.get("postgres", 0))
        neo_means.append(means.get("neo4j", 0))
    return labels, pg_means, neo_means


def plot_queries_simple() -> None:
    """T1/T2: einfache Abfragen, normale ms-Skala."""
    labels, pg_means, neo_means = collect_query_means(["T1", "T2"])
    if not labels:
        print("Keine T1/T2-Ergebnisse gefunden - Diagramm wird ausgelassen.")
        return
    fig = grouped_bar_chart(
        labels, pg_means, neo_means,
        ylabel="Mittlere Laufzeit (ms)",
        title="Einfache Abfragen (T1, T2)",
        unit_fmt="{:.1f} ms",
    )
    save(fig, "queries_einfach.png")


def plot_queries_traversal() -> None:
    """T3/T4/T6: Traversierungs-Abfragen, normale ms-Skala."""
    labels, pg_means, neo_means = collect_query_means(["T3", "T4", "T6"])
    if not labels:
        print("Keine T3/T4/T6-Ergebnisse gefunden - Diagramm wird ausgelassen.")
        return
    fig = grouped_bar_chart(
        labels, pg_means, neo_means,
        ylabel="Mittlere Laufzeit (ms)",
        title="Traversierungs-Abfragen (T3, T4, T6)",
        unit_fmt="{:.0f} ms",
    )
    save(fig, "queries_traversierung.png")


def plot_t5_special() -> None:
    """T5 (kuerzester Pfad) sprengt jede gemeinsame ms-Skala - eigenes
    Diagramm, in Sekunden statt Millisekunden (verstaendlicher: "28 s" statt
    "27940 ms")."""
    path = RESULTS_DIR / "T5.csv"
    if not path.exists():
        print("Keine T5-Ergebnisse gefunden - Diagramm wird ausgelassen.")
        return
    means = mean_by_system(read_csv(path))
    if not means:
        return
    labels = ["PostgreSQL", "Neo4j"]
    values_s = [means.get("postgres", 0) / 1000, means.get("neo4j", 0) / 1000]

    fig, ax = plt.subplots(figsize=(6, 5))
    bars = ax.bar(labels, values_s, color=[PG_COLOR, NEO_COLOR])
    ax.set_ylabel("Mittlere Laufzeit (Sekunden)")
    ax.set_title("Sonderfall T5 - kürzester Pfad")
    ax.margins(y=0.15)
    label_bars(ax, bars, "{:.3f} s")
    fig.tight_layout()
    save(fig, "t5_sonderfall.png")


def plot_scaling() -> None:
    pattern = re.compile(r"T7_n(\d+)\.csv$")
    points: list[tuple[int, dict[str, float]]] = []
    for path in RESULTS_DIR.glob("T7_n*.csv"):
        match = pattern.search(path.name)
        if not match:
            continue
        means = mean_by_system(read_csv(path))
        if means:
            points.append((int(match.group(1)), means))

    if len(points) < 2:
        print("Zu wenige T7-Groessen gefunden - Skalierungsdiagramm wird ausgelassen.")
        return

    points.sort(key=lambda p: p[0])
    sizes = [p[0] for p in points]
    pg_means = [p[1].get("postgres", 0) for p in points]
    neo_means = [p[1].get("neo4j", 0) for p in points]

    fig, ax = plt.subplots(figsize=(8, 5))
    ax.plot(sizes, pg_means, marker="o", label="PostgreSQL", color=PG_COLOR)
    ax.plot(sizes, neo_means, marker="o", label="Neo4j", color=NEO_COLOR)
    ax.set_xlabel("Anzahl Knoten in der Teilmenge")
    ax.set_ylabel("Mittlere Laufzeit T7 (ms)")
    ax.set_title("Skalierung: T7-Laufzeit vs. Datenmenge")
    ax.legend()
    fig.tight_layout()

    save(fig, "skalierung_t7.png")


def _cold_warm_means(query_id: str, cold_rows: list[dict]) -> tuple[dict, dict] | None:
    warm_path = RESULTS_DIR / (f"{query_id}.csv" if query_id != "T7" else "T7_n4039.csv")
    if not warm_path.exists():
        return None
    warm_means = mean_by_system(read_csv(warm_path))
    cold_means = mean_by_system([r for r in cold_rows if r["query"] == query_id])
    if not warm_means or not cold_means:
        return None
    return warm_means, cold_means


def plot_cold_vs_warm() -> None:
    """T1,T2,T3,T4,T6,T7: Cold- vs. Warm-Start, normale ms-Skala. T5 wird
    bewusst ausgeklammert (eigenes Diagramm, siehe plot_t5_cold_vs_warm)."""
    cold_path = RESULTS_DIR / "cold_start.csv"
    if not cold_path.exists():
        print("Keine cold_start.csv gefunden - Cold-vs-Warm-Diagramm wird ausgelassen.")
        return
    cold_rows = read_csv(cold_path)

    labels, pg_cold, pg_warm, neo_cold, neo_warm = [], [], [], [], []
    for qid in ("T1", "T2", "T3", "T4", "T6", "T7"):
        result = _cold_warm_means(qid, cold_rows)
        if result is None:
            continue
        warm_means, cold_means = result
        labels.append(qid)
        pg_warm.append(warm_means.get("postgres", 0))
        pg_cold.append(cold_means.get("postgres", 0))
        neo_warm.append(warm_means.get("neo4j", 0))
        neo_cold.append(cold_means.get("neo4j", 0))

    if not labels:
        print("Keine passenden Warm-Referenzwerte gefunden - Cold-vs-Warm-Diagramm wird ausgelassen.")
        return

    fig, axes = plt.subplots(1, 2, figsize=(13, 5.5), sharey=True)
    x = range(len(labels))
    width = 0.35

    bars_pg_warm = axes[0].bar([i - width / 2 for i in x], pg_warm, width, label="Warm (Ø 50 Läufe)", color=PG_COLOR)
    bars_pg_cold = axes[0].bar([i + width / 2 for i in x], pg_cold, width, label="Cold (Ø 3 Neustarts)", color="#9fb8cc")
    axes[0].set_title("PostgreSQL: Cold- vs. Warm-Start")
    axes[0].set_xticks(list(x))
    axes[0].set_xticklabels(labels)
    axes[0].set_ylabel("Mittlere Laufzeit (ms)")
    max_value = max(pg_warm + pg_cold + neo_warm + neo_cold)
    axes[0].set_ylim(0, max_value * 1.18)
    axes[0].legend()
    label_bars(axes[0], bars_pg_warm, "{:.0f}")
    label_bars(axes[0], bars_pg_cold, "{:.0f}")

    bars_neo_warm = axes[1].bar([i - width / 2 for i in x], neo_warm, width, label="Warm (Ø 50 Läufe)", color=NEO_COLOR)
    bars_neo_cold = axes[1].bar([i + width / 2 for i in x], neo_cold, width, label="Cold (Ø 3 Neustarts)", color="#f4bd8a")
    axes[1].set_title("Neo4j: Cold- vs. Warm-Start")
    axes[1].set_xticks(list(x))
    axes[1].set_xticklabels(labels)
    axes[1].legend()
    label_bars(axes[1], bars_neo_warm, "{:.0f}")
    label_bars(axes[1], bars_neo_cold, "{:.0f}")

    fig.suptitle("Fairness-Gegenprobe: Auswirkung eines Container-Neustarts (ohne T5, siehe t5_cold_vs_warm.png)")
    fig.tight_layout()

    save(fig, "cold_vs_warm.png")


def plot_t5_cold_vs_warm() -> None:
    """T5 cold vs. warm separat, in Sekunden statt Millisekunden."""
    cold_path = RESULTS_DIR / "cold_start.csv"
    if not cold_path.exists():
        return
    cold_rows = read_csv(cold_path)
    result = _cold_warm_means("T5", cold_rows)
    if result is None:
        print("Keine T5-Cold/Warm-Daten gefunden - Diagramm wird ausgelassen.")
        return
    warm_means, cold_means = result

    labels = ["PostgreSQL", "Neo4j"]
    warm_s = [warm_means.get("postgres", 0) / 1000, warm_means.get("neo4j", 0) / 1000]
    cold_s = [cold_means.get("postgres", 0) / 1000, cold_means.get("neo4j", 0) / 1000]

    x = range(len(labels))
    width = 0.35
    fig, ax = plt.subplots(figsize=(6, 5))
    # Hier EINE Farbe pro Balkengruppe (warm/cold), nicht pro System - sonst
    # zeigt die Legende nur die erste Farbe einer Gruppe an und der zweite
    # Balken (z.B. Neo4j in Orange) taucht scheinbar "ohne Legende" auf. Die
    # Systeme werden stattdessen schon ueber die X-Achsen-Beschriftung
    # unterschieden.
    bars_warm = ax.bar([i - width / 2 for i in x], warm_s, width, label="Warm (Ø 50 Läufe)", color=PG_COLOR)
    bars_cold = ax.bar([i + width / 2 for i in x], cold_s, width, label="Cold (Ø 3 Neustarts)", color="#9fb8cc")
    ax.set_xticks(list(x))
    ax.set_xticklabels(labels)
    ax.set_ylabel("Mittlere Laufzeit (Sekunden)")
    ax.set_title("Sonderfall T5: Cold- vs. Warm-Start")
    ax.margins(y=0.15)
    ax.legend()
    label_bars(ax, bars_warm, "{:.3f} s")
    label_bars(ax, bars_cold, "{:.3f} s")
    fig.tight_layout()

    save(fig, "t5_cold_vs_warm.png")


def main() -> None:
    plot_queries_simple()
    plot_queries_traversal()
    plot_t5_special()
    plot_scaling()
    plot_cold_vs_warm()
    plot_t5_cold_vs_warm()


if __name__ == "__main__":
    main()
