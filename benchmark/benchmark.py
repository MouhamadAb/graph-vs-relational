"""Fuehrt eine Benchmark-Query mehrfach aus und schreibt die Messwerte als CSV.

Boilerplate (CLI, CSV-Schema, DB-Verbindungen) ist vorgegeben. Die eigentliche
Mess-/Timing-Logik ist bewusst als TODO offen - siehe CLAUDE.md Lernmodus.
"""

import argparse
import csv
import os
from pathlib import Path

import psycopg2
from neo4j import GraphDatabase

RESULTS_DIR = Path(__file__).resolve().parent.parent / "results"
CSV_FIELDS = ["query", "system", "run", "duration_ms"]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Misst eine Benchmark-Query mehrfach.")
    parser.add_argument("query_id", help="z. B. T1, T2, ...")
    parser.add_argument("--runs", type=int, default=50, help="Anzahl Messwiederholungen")
    parser.add_argument("--warmup", type=int, default=5, help="Anzahl Warm-up-Laeufe vor der Messung")
    return parser.parse_args()


def connect_postgres():
    return psycopg2.connect(
        host=os.environ.get("POSTGRES_HOST", "localhost"),
        port=os.environ.get("POSTGRES_PORT", "5432"),
        dbname=os.environ.get("POSTGRES_DB", "graphbench"),
        user=os.environ.get("POSTGRES_USER", "benchmark"),
        password=os.environ.get("POSTGRES_PASSWORD", "benchmark"),
    )


def connect_neo4j():
    uri = os.environ.get("NEO4J_URI", "bolt://localhost:7687")
    user = os.environ.get("NEO4J_USER", "neo4j")
    password = os.environ.get("NEO4J_PASSWORD", "benchmark123")
    return GraphDatabase.driver(uri, auth=(user, password))


def run_postgres_query(conn, query_id: str) -> float:
    # TODO (Team): Query aus postgres/queries.sql ausfuehren und die reine
    # Ausfuehrungszeit in Millisekunden zurueckgeben.
    raise NotImplementedError


def run_neo4j_query(driver, query_id: str) -> float:
    # TODO (Team): Query aus neo4j/queries.cypher ausfuehren und die reine
    # Ausfuehrungszeit in Millisekunden zurueckgeben.
    raise NotImplementedError


def write_csv(rows: list[dict]) -> Path:
    RESULTS_DIR.mkdir(exist_ok=True)
    out_path = RESULTS_DIR / f"{rows[0]['query']}.csv"
    with out_path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    return out_path


def main() -> None:
    args = parse_args()
    pg_conn = connect_postgres()
    neo4j_driver = connect_neo4j()

    rows: list[dict] = []
    try:
        # TODO (Team): Warm-up-Laeufe (args.warmup) ausfuehren, dann
        # args.runs Messungen fuer beide Systeme und in `rows` sammeln.
        pass
    finally:
        pg_conn.close()
        neo4j_driver.close()

    if rows:
        out_path = write_csv(rows)
        print(f"Ergebnisse gespeichert: {out_path}")


if __name__ == "__main__":
    main()
