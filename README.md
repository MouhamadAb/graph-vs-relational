# Graph vs. Relational

Vergleich von PostgreSQL (relational) und Neo4j (Graph) anhand realer
SNAP-Netzwerkdatensätze. Studentisches Miniprojekt. Ausführliche Schritt-für-Schritt-Anleitung inkl.
Troubleshooting: [`docs/setup.md`](docs/setup.md).

## Setup

```bash
cp .env.example .env
docker compose up -d
python -m venv .venv && . .venv/Scripts/activate  # Windows
pip install -r requirements.txt
```

Datensatz (nicht im Repo, siehe `.gitignore`): `facebook_combined.txt` von
https://snap.stanford.edu/data/ego-Facebook.html herunterladen, entpacken und
im Projektroot ablegen.

- PostgreSQL: `localhost:5432` (siehe `.env`)
- Adminer (Postgres-Web-UI): http://localhost:8080 — System "PostgreSQL", Server `postgres`, Benutzer/Passwort/DB aus `.env`
- Neo4j Browser: http://localhost:7474 (siehe `.env`)

## Projektstruktur

```
├── docker-compose.yml       # PostgreSQL + Neo4j
├── postgres/                # Schema + SQL-Queries
├── neo4j/                   # Cypher-Queries
├── import/                  # Datensatz-Import
├── benchmark/                # Mess-Harness
├── results/                  # CSV-Messergebnisse
└── docs/setup.md             # Setup-Anleitung
```

## Benchmark & Skalierung

```bash
python benchmark/benchmark.py T1 --runs 50          # einzelne Query messen
python benchmark/scaling_benchmark.py                # T7 ueber mehrere Groessen (automatisiert)
python benchmark/plot_results.py                     # Diagramme aus results/*.csv erzeugen -> results/plots/
```

Details zum Skalierungs-Workflow: siehe `docs/setup.md`.

## Ergebnisse

Messwerte liegen als CSV in `results/*.csv`, Diagramme in `results/plots/`.

## Contributors

- Mouhamad Abdallah
- Christian Schönfeld
