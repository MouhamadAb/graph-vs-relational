"""Erzeugt Diagramme aus den results/-CSV-Dateien.

Liest, was an Ergebnissen vorhanden ist - fehlende Dateien werden einfach
uebersprungen (kein Fehler), damit das Skript auch mit einem Teil-Datensatz
an Messungen laeuft.
"""

import csv
import re
import statistics
from pathlib import Path

import matplotlib.pyplot as plt

RESULTS_DIR = Path(__file__).resolve().parent.parent / "results"
PLOTS_DIR = RESULTS_DIR / "plots"


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


def plot_single_queries() -> None:
    labels, pg_means, neo_means = [], [], []
    for i in range(1, 7):
        path = RESULTS_DIR / f"T{i}.csv"
        if not path.exists():
            continue
        means = mean_by_system(read_csv(path))
        if not means:
            continue
        labels.append(f"T{i}")
        pg_means.append(means.get("postgres", 0))
        neo_means.append(means.get("neo4j", 0))

    if not labels:
        print("Keine T1-T6 Ergebnisse gefunden - Diagramm wird ausgelassen.")
        return

    x = range(len(labels))
    width = 0.35
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.bar([i - width / 2 for i in x], pg_means, width, label="Postgres")
    ax.bar([i + width / 2 for i in x], neo_means, width, label="Neo4j")
    ax.set_xticks(list(x))
    ax.set_xticklabels(labels)
    ax.set_ylabel("Mittlere Laufzeit (ms, logarithmische Skala)")
    # Log-Skala, weil T5 (Sekunden) und T1 (Millisekunden) sonst auf derselben
    # linearen Achse nicht gleichzeitig lesbar waeren.
    ax.set_yscale("log")
    ax.set_title("Laufzeitvergleich pro Query (Mittelwert ueber alle Laeufe)")
    ax.legend()
    fig.tight_layout()

    PLOTS_DIR.mkdir(exist_ok=True)
    out_path = PLOTS_DIR / "queries_vergleich.png"
    fig.savefig(out_path)
    plt.close(fig)
    print(f"Gespeichert: {out_path}")


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
    ax.plot(sizes, pg_means, marker="o", label="Postgres")
    ax.plot(sizes, neo_means, marker="o", label="Neo4j")
    ax.set_xlabel("Anzahl Knoten in der Teilmenge")
    ax.set_ylabel("Mittlere Laufzeit T7 (ms)")
    ax.set_title("Skalierung: T7-Laufzeit vs. Datenmenge")
    ax.legend()
    fig.tight_layout()

    PLOTS_DIR.mkdir(exist_ok=True)
    out_path = PLOTS_DIR / "skalierung_t7.png"
    fig.savefig(out_path)
    plt.close(fig)
    print(f"Gespeichert: {out_path}")


def plot_cold_vs_warm() -> None:
    cold_path = RESULTS_DIR / "cold_start.csv"
    if not cold_path.exists():
        print("Keine cold_start.csv gefunden - Cold-vs-Warm-Diagramm wird ausgelassen.")
        return
    cold_rows = read_csv(cold_path)

    # Warm-Referenz: T1-T6 aus T{n}.csv, T7 aus der vollen Skalierungsgroesse
    # (T7_n4039.csv) - das ist dieselbe Datenmenge, die auch fuer die
    # Cold-Messungen aktiv war.
    labels, pg_cold, pg_warm, neo_cold, neo_warm = [], [], [], [], []
    for i in range(1, 8):
        qid = f"T{i}"
        warm_path = RESULTS_DIR / (f"{qid}.csv" if i < 7 else "T7_n4039.csv")
        if not warm_path.exists():
            continue
        warm_means = mean_by_system(read_csv(warm_path))
        cold_means = mean_by_system([r for r in cold_rows if r["query"] == qid])
        if not warm_means or not cold_means:
            continue
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

    axes[0].bar([i - width / 2 for i in x], pg_warm, width, label="Warm (Ø 50 Läufe)", color="#336791")
    axes[0].bar([i + width / 2 for i in x], pg_cold, width, label="Cold (Ø 3 Neustarts)", color="#9fb8cc")
    axes[0].set_title("PostgreSQL: Cold- vs. Warm-Start")
    axes[0].set_xticks(list(x))
    axes[0].set_xticklabels(labels)
    axes[0].set_ylabel("Mittlere Laufzeit (ms, logarithmische Skala)")
    axes[0].set_yscale("log")
    axes[0].legend()

    axes[1].bar([i - width / 2 for i in x], neo_warm, width, label="Warm (Ø 50 Läufe)", color="#E8720C")
    axes[1].bar([i + width / 2 for i in x], neo_cold, width, label="Cold (Ø 3 Neustarts)", color="#f4bd8a")
    axes[1].set_title("Neo4j: Cold- vs. Warm-Start")
    axes[1].set_xticks(list(x))
    axes[1].set_xticklabels(labels)
    axes[1].set_yscale("log")
    axes[1].legend()

    fig.suptitle("Fairness-Gegenprobe: Auswirkung eines Container-Neustarts")
    fig.tight_layout()

    PLOTS_DIR.mkdir(exist_ok=True)
    out_path = PLOTS_DIR / "cold_vs_warm.png"
    fig.savefig(out_path)
    plt.close(fig)
    print(f"Gespeichert: {out_path}")


def main() -> None:
    plot_single_queries()
    plot_scaling()
    plot_cold_vs_warm()


if __name__ == "__main__":
    main()
