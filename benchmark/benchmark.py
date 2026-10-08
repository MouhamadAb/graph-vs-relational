"""Fuehrt eine Benchmark-Query mehrfach gegen Postgres UND Neo4j aus und
schreibt die Messwerte als CSV.

Komplett implementiert auf ausdruecklichen Wunsch des Teams (siehe Memory
lernmodus-ausnahme-schema-import) - die Lernmodus-Ausnahme aus CLAUDE.md gilt
jetzt auch fuer diese Mess-Logik.

Bekannte, bewusst nicht geloeste Einschraenkungen (siehe docs/konzept.md):
- Fairness-Punkt 5 (Cold/Warm-Protokoll): hier nur ein einfaches
  Warmup+Messphasen-Schema, kein Container-Neustart zwischen Laeufen.
- Fairness-Punkt 9 (Treiber-Overhead): gemessen wird Ausfuehrung + Abholen
  der Ergebnisse ueber eine bereits offene Verbindung, nicht der
  Verbindungsaufbau selbst.

T7 (Skalierung) ist keine eigene Query, sondern T4 wiederholt gegen
unterschiedlich grosse, mit import_dataset.py --sample-nodes importierte
Teilmengen - siehe docs/setup.md fuer den kompletten Skalierungs-Workflow.
"""

import argparse
import csv
import json
import os
import random
import statistics
import time
from pathlib import Path

import psycopg2
from neo4j import GraphDatabase

RESULTS_DIR = Path(__file__).resolve().parent.parent / "results"
CSV_FIELDS = ["query", "system", "run", "duration_ms", "params"]

# Query-Texte identisch zu postgres/queries.sql bzw. neo4j/queries.cypher.
# "params" legt fest, wie viele (und welche) IDs die Query braucht.
QUERIES = {
    "T1": {
        "params": ("id",),
        "sql": "SELECT id FROM person WHERE id = %(id)s",
        "cypher": "MATCH (p:Person {id: $id}) RETURN p",
    },
    "T2": {
        "params": ("id",),
        "sql": """
            SELECT CASE WHEN person_id = %(id)s THEN friend_id ELSE person_id END AS contact_id
            FROM friendship
            WHERE person_id = %(id)s OR friend_id = %(id)s
        """,
        "cypher": "MATCH (x:Person {id: $id})-[:KNOWS]-(other) RETURN DISTINCT other",
    },
    "T3": {
        "params": ("id",),
        "sql": """
            WITH contacts AS (
                SELECT person_id AS a, friend_id AS b FROM friendship
                UNION ALL
                SELECT friend_id AS a, person_id AS b FROM friendship
            )
            SELECT DISTINCT c2.b AS contact_id
            FROM contacts c1
            JOIN contacts c2 ON c1.b = c2.a
            WHERE c1.a = %(id)s
              AND c2.b <> %(id)s
              AND c2.b NOT IN (SELECT b FROM contacts WHERE a = %(id)s)
        """,
        "cypher": """
            MATCH (x:Person {id: $id})-[:KNOWS*2]-(other)
            WHERE other.id <> $id AND NOT (x)-[:KNOWS]-(other)
            RETURN DISTINCT other
        """,
    },
    "T4": {
        "params": ("id",),
        "sql": """
            WITH RECURSIVE contacts AS (
                SELECT person_id AS a, friend_id AS b FROM friendship
                UNION ALL
                SELECT friend_id AS a, person_id AS b FROM friendship
            ),
            reachable(contact_id, depth) AS (
                SELECT b, 1 FROM contacts WHERE a = %(id)s
                UNION
                SELECT c.b, r.depth + 1
                FROM reachable r
                JOIN contacts c ON c.a = r.contact_id
                WHERE r.depth < 4
            )
            SELECT DISTINCT contact_id FROM reachable WHERE contact_id <> %(id)s
        """,
        "cypher": """
            MATCH (p:Person {id: $id})-[:KNOWS*1..4]-(other)
            WHERE other.id <> $id
            RETURN DISTINCT other
        """,
    },
    "T5": {
        "params": ("id1", "id2"),
        "sql": """
            WITH RECURSIVE contacts AS (
                SELECT person_id AS a, friend_id AS b FROM friendship
                UNION ALL
                SELECT friend_id AS a, person_id AS b FROM friendship
            ),
            bfs(contact_id, depth) AS (
                SELECT %(id1)s::int, 0
                UNION
                SELECT c.b, bfs.depth + 1
                FROM bfs
                JOIN contacts c ON c.a = bfs.contact_id
                WHERE bfs.depth < 8
            )
            SELECT min(depth) AS distance FROM bfs WHERE contact_id = %(id2)s
        """,
        "cypher": """
            MATCH p = shortestPath((a:Person {id: $id1})-[:KNOWS*..8]-(b:Person {id: $id2}))
            RETURN length(p) AS distance
        """,
    },
    "T6": {
        "params": ("id1", "id2"),
        "sql": """
            WITH contacts AS (
                SELECT person_id AS a, friend_id AS b FROM friendship
                UNION ALL
                SELECT friend_id AS a, person_id AS b FROM friendship
            )
            SELECT DISTINCT c1.b AS contact_id
            FROM contacts c1
            JOIN contacts c2 ON c1.b = c2.b
            WHERE c1.a = %(id1)s AND c2.a = %(id2)s
        """,
        "cypher": """
            MATCH (a:Person {id: $id1})-[:KNOWS]-(common)-[:KNOWS]-(b:Person {id: $id2})
            WHERE a <> b
            RETURN DISTINCT common
        """,
    },
}
QUERIES["T7"] = QUERIES["T4"]  # T7 = T4, wiederholt auf unterschiedlich grossen Teilmengen


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Misst eine Benchmark-Query mehrfach gegen Postgres und Neo4j.")
    parser.add_argument("query_id", choices=sorted(QUERIES.keys()), help="z. B. T1, T2, ...")
    parser.add_argument("--runs", type=int, default=50, help="Anzahl Messwiederholungen")
    parser.add_argument("--warmup", type=int, default=5, help="Anzahl Warm-up-Laeufe vor der Messung")
    parser.add_argument("--seed", type=int, default=42, help="Zufalls-Seed fuer die Auswahl der Test-IDs")
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


def fetch_all_ids(pg_conn) -> list[int]:
    with pg_conn.cursor() as cur:
        cur.execute("SELECT id FROM person")
        return [row[0] for row in cur.fetchall()]


def make_params(param_names: tuple[str, ...], ids: list[int], rng: random.Random) -> dict:
    # Pro Lauf eine (reproduzierbar) zufaellige ID bzw. ein zufaelliges Paar
    # auswaehlen, statt immer dieselbe ID zu testen - sonst wuerde eine einzelne,
    # evtl. untypische ID (Hub oder Randknoten) das Ergebnis verzerren.
    if len(param_names) == 1:
        values = [rng.choice(ids)]
    else:
        values = rng.sample(ids, k=len(param_names))
    return dict(zip(param_names, values))


def time_postgres(conn, sql: str, params: dict) -> float:
    start = time.perf_counter()
    with conn.cursor() as cur:
        cur.execute(sql, params)
        cur.fetchall()
    return (time.perf_counter() - start) * 1000


def time_neo4j(session, cypher: str, params: dict) -> float:
    start = time.perf_counter()
    result = session.run(cypher, params)
    list(result)  # erzwingt das vollstaendige Abholen aller Datensaetze
    return (time.perf_counter() - start) * 1000


def write_csv(rows: list[dict]) -> Path:
    RESULTS_DIR.mkdir(exist_ok=True)
    out_path = RESULTS_DIR / f"{rows[0]['query']}.csv"
    with out_path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    return out_path


def print_summary(query_id: str, rows: list[dict]) -> None:
    for system in ("postgres", "neo4j"):
        durations = [r["duration_ms"] for r in rows if r["system"] == system]
        print(
            f"{query_id} / {system}: "
            f"min={min(durations):.3f}ms max={max(durations):.3f}ms "
            f"mean={statistics.mean(durations):.3f}ms median={statistics.median(durations):.3f}ms "
            f"stddev={statistics.stdev(durations):.3f}ms (n={len(durations)})"
        )


def main() -> None:
    args = parse_args()
    query = QUERIES[args.query_id]
    rng = random.Random(args.seed)

    pg_conn = connect_postgres()
    neo4j_driver = connect_neo4j()
    rows: list[dict] = []
    try:
        ids = fetch_all_ids(pg_conn)
        with neo4j_driver.session() as session:
            for _ in range(args.warmup):
                params = make_params(query["params"], ids, rng)
                time_postgres(pg_conn, query["sql"], params)
                time_neo4j(session, query["cypher"], params)

            for run in range(1, args.runs + 1):
                params = make_params(query["params"], ids, rng)
                params_json = json.dumps(params)

                pg_ms = time_postgres(pg_conn, query["sql"], params)
                rows.append({"query": args.query_id, "system": "postgres", "run": run, "duration_ms": pg_ms, "params": params_json})

                neo4j_ms = time_neo4j(session, query["cypher"], params)
                rows.append({"query": args.query_id, "system": "neo4j", "run": run, "duration_ms": neo4j_ms, "params": params_json})
    finally:
        pg_conn.close()
        neo4j_driver.close()

    out_path = write_csv(rows)
    print(f"Ergebnisse gespeichert: {out_path}")
    print_summary(args.query_id, rows)


if __name__ == "__main__":
    main()
