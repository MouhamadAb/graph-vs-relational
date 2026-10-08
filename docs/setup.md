# Setup-Anleitung: Workspace + Datensatz-Import

Schritt-für-Schritt-Anleitung für einen frischen Rechner (z. B. Teampartner),
inklusive der Stolpersteine, auf die wir selbst schon gestoßen sind.

## 1. Repo klonen und Python-Umgebung einrichten

```bash
git clone https://github.com/MouhamadAb/graph-vs-relational.git
cd graph-vs-relational
python -m venv .venv
.venv\Scripts\activate          # Windows
pip install -r requirements.txt
```

**Wichtig:** `import/import_dataset.py` braucht **Python 3.9 oder neuer**
(wegen `list[tuple[int, int]]`-Typangaben). Mit `python --version` prüfen.
Falls `pip install` durchläuft, aber das Skript sofort mit einem `TypeError`
oder `SyntaxError` abbricht, ist das meist ein zu altes Python.

## 2. `.env` anlegen

```bash
cp .env.example .env
```

Die Werte darin sind Lern-/Testdaten (keine echten Zugangsdaten), die
Default-Credentials im Code passen dazu — `.env` muss nicht verändert werden.

## 3. Datensatz herunterladen

1. https://snap.stanford.edu/data/ego-Facebook.html öffnen
2. `facebook_combined.txt.gz` herunterladen
3. Entpacken, sodass die Datei **direkt im Projekt-Root** liegt:
   `graph-vs-relational/facebook_combined.txt`
   (Nicht in einem Unterordner — der Importbefehl in Schritt 5 geht von
   diesem Pfad aus. `.gitignore` sorgt dafür, dass die Datei nicht ins Repo
   committet wird.)

## 4. Docker-Container starten

```bash
docker compose up -d
docker compose ps
```

Beide Zeilen (`postgres`, `neo4j`, `adminer`) sollten `Up`/`healthy` zeigen.

**Stolperstein, den wir selbst hatten:** Das Schema in `postgres/schema.sql`
wird nur beim **allerersten** Start eines neuen Postgres-Datenverzeichnisses
automatisch angelegt. Wenn der Container vorher schon mal lief (z. B. weil
jemand Adminer getestet hat, bevor das Schema fertig war), bleibt die
Datenbank leer, auch nach einem Neustart. Prüfen mit:

```bash
docker compose exec -T postgres psql -U benchmark -d graphbench -c "\dt"
```

Zeigt das **keine** Tabellen `person`/`friendship`, einmalig manuell
nachziehen. Der Befehl unterscheidet sich je nach Shell:

**PowerShell** (Standard-Terminal unter Windows):
```powershell
docker compose cp postgres/schema.sql postgres:/tmp/schema.sql
docker compose exec -T postgres psql -U benchmark -d graphbench -f /tmp/schema.sql
```

**Git Bash / WSL:**
```bash
MSYS_NO_PATHCONV=1 docker compose cp postgres/schema.sql postgres:/tmp/schema.sql
MSYS_NO_PATHCONV=1 docker compose exec -T postgres psql -U benchmark -d graphbench -f /tmp/schema.sql
```

**Warum nicht einfach `psql ... < schema.sql`?** Das `<` fuer Datei-Umleitung
gibt es in der PowerShell nicht (Fehler "the '<' operator is reserved for
future use"), und in Git Bash wird der Pfad `/tmp/schema.sql` ohne
`MSYS_NO_PATHCONV=1` faelschlich in einen Windows-Pfad umgewandelt, den der
Linux-Container nicht kennt ("No such file or directory"). Der `docker
compose cp` + `-f`-Weg funktioniert in allen drei Faellen gleich.

Bei einem wirklich frischen `docker compose up -d` (noch nie vorher
gestartet) passiert das automatisch — der manuelle Schritt ist nur das
Nachholen, falls der Container schon mal ohne fertiges Schema lief.

## 5. Datensatz importieren

Im Projekt-Root (gleiche Ebene wie `facebook_combined.txt`):

```bash
python import/import_dataset.py facebook_combined.txt
```

Erwartete Ausgabe:

```
88234 Kanten aus facebook_combined.txt gelesen.
Import nach Postgres abgeschlossen.
Import nach Neo4j abgeschlossen.
Erwartet:  4039 Knoten, 88234 Kanten
Postgres:  4039 Knoten, 88234 Kanten
Neo4j:     4039 Knoten, 88234 Kanten
```

## 6. Benchmark ausführen

```bash
python benchmark/benchmark.py T1 --runs 50
```

Ergebnis landet als CSV in `results/<query_id>.csv` plus einer
Zusammenfassung (Min/Max/Mittelwert/Median/Stddev) auf der Konsole.

## 7. Skalierungstest (T7)

T7 ist keine eigene Query, sondern T4 wiederholt auf unterschiedlich großen
Teilmengen desselben Graphen (Snowball-/BFS-Sampling, siehe
`docs/konzept.md` "Entscheidungen"). Workflow pro Größe:

```bash
python import/import_dataset.py facebook_combined.txt --reset --sample-nodes 1000 --seed 42
python benchmark/benchmark.py T7 --runs 50
cp results/T7.csv results/T7_n1000.csv   # sichern, bevor die naechste Groesse laeuft
```

Danach mit einer anderen `--sample-nodes`-Größe wiederholen. Am Ende, um
wieder mit dem vollen Datensatz zu arbeiten:

```bash
python import/import_dataset.py facebook_combined.txt --reset
```

**Achtung:** `benchmark.py` überschreibt `results/T7.csv` bei jedem Lauf —
die Datei nach jeder Größe wie oben sichern, sonst gehen frühere Messungen
verloren.

## Häufige Fehlerquellen

| Fehlermeldung (sinngemäß) | Ursache | Lösung |
|---|---|---|
| `FileNotFoundError` / `No such file` | `facebook_combined.txt` liegt nicht im aktuellen Verzeichnis oder falscher Dateiname | Pfad/Dateiname prüfen, Befehl aus Projekt-Root ausführen |
| `psycopg2.OperationalError: could not connect to server` | Docker-Container laufen nicht oder sind noch nicht "healthy" | `docker compose ps` prüfen, ggf. `docker compose up -d` erneut, kurz warten |
| `psycopg2.errors.UndefinedTable: relation "person" does not exist` | Schema wurde nicht angelegt (siehe Schritt 4, Stolperstein) | Schema manuell nachziehen (Befehl oben) |
| `neo4j.exceptions.ServiceUnavailable` | Neo4j noch nicht hochgefahren (braucht beim ersten Start etwas länger) | Kurz warten, `docker compose ps` auf "healthy" prüfen |
| `TypeError` direkt beim Start des Skripts | Python-Version zu alt (< 3.9) | `python --version` prüfen, ggf. neuere Python-Version installieren |
