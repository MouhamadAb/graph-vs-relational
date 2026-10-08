"""Importiert denselben Datensatz nach PostgreSQL und Neo4j.

Hinweis: Schema (postgres/schema.sql) und dieses Import-Skript wurden auf
ausdruecklichen Wunsch des Teams komplett fertig geschrieben (bewusste
Ausnahme vom Lernmodus aus CLAUDE.md, siehe Memory
lernmodus-ausnahme-schema-import).

Kantenrichtung (siehe docs/konzept.md "Entscheidungen", Option A): jede Zeile
der Datei wird 1:1 als eine Zeile/Relationship uebernommen, nicht verdoppelt.

Skalierung / Teilmengen (Fairness-Punkt 6, entschieden): Teilmengen desselben
Graphen statt eines zweiten Datensatzes. Sampling-Methode (Fairness-Punkt 7):
Snowball-/BFS-Sampling mit festem Seed statt naivem ID-Cutoff - siehe
sample_subgraph(). Das erhaelt die lokale Graphstruktur (zusammenhaengend)
viel eher als rein zufaellige Knotenauswahl, bevorzugt aber dadurch tendenziell
dichter vernetzte Regionen um den Startknoten - diese Einschraenkung bitte im
Abschlussbericht erwaehnen.
"""

import argparse
import os
import random
from collections import defaultdict
from pathlib import Path
from typing import Optional

import psycopg2
import psycopg2.extras
from neo4j import GraphDatabase


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Importiert einen SNAP-Edge-List-Datensatz.")
    parser.add_argument("edgelist_path", help="Pfad zur Edge-List-Datei (z. B. facebook_combined.txt)")
    parser.add_argument(
        "--sample-nodes",
        type=int,
        default=None,
        help=(
            "Optional: nur eine Teilmenge von N Knoten importieren (Snowball-/"
            "BFS-Sampling ab einem zufaelligen, aber per --seed reproduzierbaren "
            "Startknoten). Fuer den Skalierungstest T7."
        ),
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Zufalls-Seed fuer --sample-nodes, damit die Teilmenge reproduzierbar ist.",
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Vor dem Import beide Datenbanken vollstaendig leeren (fuer wiederholte T7-Laeufe mit wechselnder Groesse).",
    )
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


def parse_edgelist(path: Path) -> list[tuple[int, int]]:
    edges: list[tuple[int, int]] = []
    with path.open() as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            a_str, b_str = line.split()
            edges.append((int(a_str), int(b_str)))
    return edges


def sample_subgraph(edges: list[tuple[int, int]], sample_size: int, seed: int) -> list[tuple[int, int]]:
    """Snowball-/BFS-Sampling: ab einem festen Startknoten (per Seed) so lange
    Nachbarn aufnehmen, bis sample_size Knoten erreicht ist. Danach werden alle
    Kanten behalten, deren beide Enden in der Stichprobe liegen (induzierter
    Teilgraph) - dadurch bleibt die Teilmenge zusammenhaengend, anders als bei
    rein zufaelliger Knotenauswahl."""
    rng = random.Random(seed)
    adjacency: dict[int, set[int]] = defaultdict(set)
    for a, b in edges:
        adjacency[a].add(b)
        adjacency[b].add(a)

    start = rng.choice(sorted(adjacency.keys()))
    visited = {start}
    frontier = [start]
    while frontier and len(visited) < sample_size:
        current = frontier.pop(0)
        neighbors = sorted(adjacency[current])
        rng.shuffle(neighbors)
        for n in neighbors:
            if n not in visited:
                visited.add(n)
                frontier.append(n)
                if len(visited) >= sample_size:
                    break

    return [(a, b) for a, b in edges if a in visited and b in visited]


def reset_postgres(conn) -> None:
    with conn.cursor() as cur:
        cur.execute("TRUNCATE TABLE friendship, person RESTART IDENTITY")
    conn.commit()


def reset_neo4j(driver) -> None:
    with driver.session() as session:
        session.run("MATCH (n) DETACH DELETE n")


def import_into_postgres(conn, edges: list[tuple[int, int]]) -> None:
    node_ids = sorted({n for edge in edges for n in edge})

    with conn.cursor() as cur:
        psycopg2.extras.execute_values(
            cur,
            "INSERT INTO person (id) VALUES %s ON CONFLICT DO NOTHING",
            [(n,) for n in node_ids],
        )
        psycopg2.extras.execute_values(
            cur,
            "INSERT INTO friendship (person_id, friend_id) VALUES %s ON CONFLICT DO NOTHING",
            edges,
        )
    conn.commit()


def import_into_neo4j(driver, edges: list[tuple[int, int]]) -> None:
    def _create_constraint(tx):
        # Ohne diesen Constraint (der intern einen Index anlegt) muesste jedes
        # MERGE unten alle bisherigen Person-Knoten durchsuchen - bei 88k
        # Kanten auf langsamerer Hardware spuerbar langsam.
        tx.run(
            "CREATE CONSTRAINT person_id_unique IF NOT EXISTS "
            "FOR (p:Person) REQUIRE p.id IS UNIQUE"
        )

    def _write(tx, rows):
        tx.run(
            """
            UNWIND $rows AS row
            MERGE (a:Person {id: row.a})
            MERGE (b:Person {id: row.b})
            MERGE (a)-[:KNOWS]->(b)
            """,
            rows=rows,
        )

    rows = [{"a": a, "b": b} for a, b in edges]
    with driver.session() as session:
        session.execute_write(_create_constraint)
        session.execute_write(_write, rows)


def validate(conn, driver, expected_edges: list[tuple[int, int]]) -> None:
    expected_nodes = {n for edge in expected_edges for n in edge}

    with conn.cursor() as cur:
        cur.execute("SELECT count(*) FROM person")
        pg_nodes = cur.fetchone()[0]
        cur.execute("SELECT count(*) FROM friendship")
        pg_edges = cur.fetchone()[0]

    with driver.session() as session:
        neo4j_nodes = session.run("MATCH (p:Person) RETURN count(p) AS c").single()["c"]
        neo4j_edges = session.run("MATCH ()-[r:KNOWS]->() RETURN count(r) AS c").single()["c"]

    print(f"Erwartet:  {len(expected_nodes)} Knoten, {len(expected_edges)} Kanten")
    print(f"Postgres:  {pg_nodes} Knoten, {pg_edges} Kanten")
    print(f"Neo4j:     {neo4j_nodes} Knoten, {neo4j_edges} Kanten")


def main() -> None:
    args = parse_args()
    edges = parse_edgelist(Path(args.edgelist_path))
    print(f"{len(edges)} Kanten aus {args.edgelist_path} gelesen.")

    if args.sample_nodes is not None:
        edges = sample_subgraph(edges, args.sample_nodes, args.seed)
        node_count = len({n for edge in edges for n in edge})
        print(f"Snowball-Sample (seed={args.seed}): {node_count} Knoten, {len(edges)} Kanten.")

    pg_conn = connect_postgres()
    neo4j_driver = connect_neo4j()
    try:
        if args.reset:
            reset_postgres(pg_conn)
            reset_neo4j(neo4j_driver)
            print("Beide Datenbanken wurden vor dem Import geleert.")

        import_into_postgres(pg_conn, edges)
        print("Import nach Postgres abgeschlossen.")
        import_into_neo4j(neo4j_driver, edges)
        print("Import nach Neo4j abgeschlossen.")
        validate(pg_conn, neo4j_driver, edges)
    finally:
        pg_conn.close()
        neo4j_driver.close()


if __name__ == "__main__":
    main()
