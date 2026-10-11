"""Fairness-Gegenprobe (Konzept Abschnitt 3.7 / Meilenstein M9).

Misst T1 GEGEN NUR EIN SYSTEM, waehrend der jeweils andere Container
gestoppt ist - im Unterschied zu benchmark.py, das immer beide Systeme
gleichzeitig misst (und damit beide Container gleichzeitig um Host-
Ressourcen konkurrieren, trotz der festen Docker-Limits). Vergleicht man
diese isolierten Werte mit den bisherigen T1-Werten aus benchmark.py, zeigt
sich, ob die gleichzeitige Ausfuehrung selbst einen messbaren Einfluss hatte.

Nur fuer T1 (Baseline-Lookup) - ausreichend fuer die Gegenprobe, da hier der
groesste relative Protokoll-Overhead-Anteil gemessen wird und etwaige
Stoerungen durch Mitbenutzung des Host-Systems am ehesten sichtbar waeren.
"""

import argparse
import os
import random
import statistics
import time

import psycopg2
from neo4j import GraphDatabase

T1_SQL = "SELECT id FROM person WHERE id = %(id)s"
T1_CYPHER = "MATCH (p:Person {id: $id}) RETURN p"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Isolierte T1-Messung fuer die Fairness-Gegenprobe.")
    parser.add_argument("system", choices=["postgres", "neo4j"])
    parser.add_argument("--runs", type=int, default=50)
    parser.add_argument("--warmup", type=int, default=5)
    parser.add_argument("--seed", type=int, default=42)
    return parser.parse_args()


def measure_postgres(runs: int, warmup: int, rng: random.Random) -> list[float]:
    conn = psycopg2.connect(
        host=os.environ.get("POSTGRES_HOST", "localhost"),
        port=os.environ.get("POSTGRES_PORT", "5432"),
        dbname=os.environ.get("POSTGRES_DB", "graphbench"),
        user=os.environ.get("POSTGRES_USER", "benchmark"),
        password=os.environ.get("POSTGRES_PASSWORD", "benchmark"),
    )
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM person")
            ids = [row[0] for row in cur.fetchall()]

        durations = []
        for i in range(warmup + runs):
            pid = rng.choice(ids)
            start = time.perf_counter()
            with conn.cursor() as cur:
                cur.execute(T1_SQL, {"id": pid})
                cur.fetchall()
            dur = (time.perf_counter() - start) * 1000
            if i >= warmup:
                durations.append(dur)
        return durations
    finally:
        conn.close()


def measure_neo4j(runs: int, warmup: int, rng: random.Random) -> list[float]:
    uri = os.environ.get("NEO4J_URI", "bolt://localhost:7687")
    user = os.environ.get("NEO4J_USER", "neo4j")
    password = os.environ.get("NEO4J_PASSWORD", "benchmark123")
    driver = GraphDatabase.driver(uri, auth=(user, password))
    try:
        with driver.session() as session:
            ids = [record["id"] for record in session.run("MATCH (p:Person) RETURN p.id AS id")]

            durations = []
            for i in range(warmup + runs):
                pid = rng.choice(ids)
                start = time.perf_counter()
                result = session.run(T1_CYPHER, {"id": pid})
                list(result)
                dur = (time.perf_counter() - start) * 1000
                if i >= warmup:
                    durations.append(dur)
        return durations
    finally:
        driver.close()


def main() -> None:
    args = parse_args()
    rng = random.Random(args.seed)

    if args.system == "postgres":
        durations = measure_postgres(args.runs, args.warmup, rng)
    else:
        durations = measure_neo4j(args.runs, args.warmup, rng)

    print(
        f"T1 / {args.system} (ISOLIERT, anderer Container gestoppt): "
        f"min={min(durations):.3f}ms max={max(durations):.3f}ms "
        f"mean={statistics.mean(durations):.3f}ms median={statistics.median(durations):.3f}ms "
        f"stddev={statistics.stdev(durations):.3f}ms (n={len(durations)})"
    )


if __name__ == "__main__":
    main()
