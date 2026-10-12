"""Cold-Start-Benchmark: misst T1-T7 je 3x nach einem vollstaendigen
Container-Neustart - genau EINE Abfrage pro Neustart, kein Warmup.

Ergaenzt die bisherige Entscheidung ("nur Warm-Runs") um echte
Cold-Start-Werte: Postgres und Neo4j werden vor jeder Messung komplett
gestoppt und neu gestartet, dann wird sofort (ohne Aufwaermen) eine einzelne
Abfrage ausgefuehrt und die Zeit gestoppt.

Dieselbe Test-ID (bzw. dasselbe ID-Paar) wird fuer alle 3 Wiederholungen
EINER Query verwendet (fester Seed, einmal vor dem Cold-Start-Zyklus
gezogen) - Unterschiede zwischen den 3 Wiederholungen kommen dadurch nur
vom Cold-Start selbst, nicht von unterschiedlich "schweren" IDs.

Einschraenkung: "Cold" bedeutet hier, dass der Datenbank-PROZESS neu
gestartet wird (In-Memory-Caches wie Postgres shared_buffers oder Neo4js
Page-Cache/JVM-Zustand sind weg). Der Betriebssystem-Festplatten-Cache der
Docker-VM kann trotzdem noch "warm" sein, da dieselben Volumes weiter
existieren - ein echtes Zuruecksetzen davon wuerde einen Neustart der
gesamten Docker-VM erfordern, was hier bewusst nicht gemacht wird.
"""

import argparse
import csv
import json
import random
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from benchmark import (  # noqa: E402
    QUERIES,
    connect_neo4j,
    connect_postgres,
    fetch_all_ids,
    make_params,
    time_neo4j,
    time_postgres,
)

ROOT = Path(__file__).resolve().parent.parent
RESULTS_DIR = ROOT / "results"
CSV_FIELDS = ["query", "system", "rep", "duration_ms", "params"]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Cold-Start-Benchmark fuer T1-T7.")
    parser.add_argument("--reps", type=int, default=3)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--queries", nargs="+", default=sorted(QUERIES.keys()))
    return parser.parse_args()


def docker(args: list[str]) -> subprocess.CompletedProcess:
    print("$ docker " + " ".join(args))
    return subprocess.run(["docker"] + args, cwd=ROOT, check=True, capture_output=True, text=True)


def wait_healthy(container: str, timeout: int = 90) -> None:
    start = time.time()
    while time.time() - start < timeout:
        result = subprocess.run(
            ["docker", "inspect", "--format={{.State.Health.Status}}", container],
            cwd=ROOT, capture_output=True, text=True,
        )
        status = result.stdout.strip()
        if status == "healthy":
            return
        time.sleep(2)
    raise TimeoutError(f"{container} wurde nicht innerhalb von {timeout}s healthy.")


def restart_databases() -> None:
    docker(["compose", "stop", "postgres", "neo4j"])
    docker(["compose", "start", "postgres", "neo4j"])
    wait_healthy("graph_vs_relational_postgres")
    wait_healthy("graph_vs_relational_neo4j")


def main() -> None:
    args = parse_args()

    # IDs einmalig VOR dem Cold-Start-Zyklus holen (eigene, kurze Verbindung -
    # die Container werden danach sofort neu gestartet, zaehlt also nicht als
    # Aufwaermen der eigentlichen Messungen).
    pg_conn = connect_postgres()
    ids = fetch_all_ids(pg_conn)
    pg_conn.close()

    rng = random.Random(args.seed)
    fixed_params = {qid: make_params(QUERIES[qid]["params"], ids, rng) for qid in args.queries}

    rows: list[dict] = []
    for qid in args.queries:
        query = QUERIES[qid]
        params = fixed_params[qid]
        print(f"\n########## {qid} (Params: {params}) ##########")

        for rep in range(1, args.reps + 1):
            print(f"\n--- Cold-Rep {rep}/{args.reps} ---")
            restart_databases()

            pg_conn = connect_postgres()
            pg_ms = time_postgres(pg_conn, query["sql"], params)
            pg_conn.close()
            rows.append({"query": qid, "system": "postgres", "rep": rep, "duration_ms": pg_ms, "params": json.dumps(params)})
            print(f"  postgres (cold): {pg_ms:.3f} ms")

            neo4j_driver = connect_neo4j()
            with neo4j_driver.session() as session:
                neo4j_ms = time_neo4j(session, query["cypher"], params)
            neo4j_driver.close()
            rows.append({"query": qid, "system": "neo4j", "rep": rep, "duration_ms": neo4j_ms, "params": json.dumps(params)})
            print(f"  neo4j (cold):    {neo4j_ms:.3f} ms")

    RESULTS_DIR.mkdir(exist_ok=True)
    out_path = RESULTS_DIR / "cold_start.csv"
    with out_path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    print(f"\nErgebnisse gespeichert: {out_path}")

    print("\n=== Finaler Neustart (Container danach wieder normal einsatzbereit) ===")
    restart_databases()


if __name__ == "__main__":
    main()
