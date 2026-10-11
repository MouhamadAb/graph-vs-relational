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


def main() -> None:
    plot_single_queries()
    plot_scaling()


if __name__ == "__main__":
    main()
