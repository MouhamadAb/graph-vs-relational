# Graph vs. Relational

Vergleich von PostgreSQL (relational) und Neo4j (Graph) anhand realer
SNAP-Netzwerkdatensätze. Studentisches Miniprojekt, siehe [`docs/konzept.md`](docs/konzept.md)
für das vollständige Konzept und [`CLAUDE.md`](CLAUDE.md) für die
Zusammenarbeitsregeln.

## Setup

```bash
cp .env.example .env
docker compose up -d
python -m venv .venv && . .venv/Scripts/activate  # Windows
pip install -r requirements.txt
```

- PostgreSQL: `localhost:5432` (siehe `.env`)
- Neo4j Browser: http://localhost:7474 (siehe `.env`)

## Projektstruktur

```
├── docker-compose.yml       # PostgreSQL + Neo4j
├── postgres/                # Schema + SQL-Queries
├── neo4j/                   # Cypher-Queries
├── import/                  # Datensatz-Import
├── benchmark/                # Mess-Harness
├── results/                  # CSV-Messergebnisse
└── docs/konzept.md           # Projektkonzept
```

## Status

Workspace-Grundgerüst steht. Offene methodische Fragen (Fairness, siehe
"Offene Punkte" in `docs/konzept.md`) werden vor der Implementierung der
eigentlichen Benchmark-Queries (T1–T7) gemeinsam geklärt.
