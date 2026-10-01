"""Importiert denselben Datensatz nach PostgreSQL und Neo4j.

Boilerplate (CLI, DB-Verbindungen) ist vorgegeben. Die eigentliche
Mapping-Logik (wie eine Kante aus der Edge-List in beide Systeme
geschrieben wird) ist bewusst als TODO offen - siehe CLAUDE.md Lernmodus
und docs/konzept.md "Offene Punkte" (Kantenrichtung!).
"""

import argparse
import os

import psycopg2
from neo4j import GraphDatabase


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Importiert einen SNAP-Edge-List-Datensatz.")
    parser.add_argument("edgelist_path", help="Pfad zur Edge-List-Datei (z. B. facebook_combined.txt)")
    parser.add_argument("--limit-nodes", type=int, default=None, help="Optional: nur die ersten N Knoten importieren")
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


def import_into_postgres(conn, edges) -> None:
    # TODO (Team): Knoten + Kanten gemaess postgres/schema.sql einfuegen.
    raise NotImplementedError


def import_into_neo4j(driver, edges) -> None:
    # TODO (Team): Knoten + Kanten als (:Person)-[:KNOWS]->(:Person) anlegen.
    raise NotImplementedError


def main() -> None:
    args = parse_args()

    # TODO (Team): Edge-List-Datei einlesen (Format dokumentieren, siehe
    # docs/konzept.md Abschnitt 8, Schritt 1).
    edges = []

    pg_conn = connect_postgres()
    neo4j_driver = connect_neo4j()
    try:
        import_into_postgres(pg_conn, edges)
        import_into_neo4j(neo4j_driver, edges)
    finally:
        pg_conn.close()
        neo4j_driver.close()


if __name__ == "__main__":
    main()
