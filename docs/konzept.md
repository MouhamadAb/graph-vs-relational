# Miniprojekt: Graphdatenbank vs. relationale Datenbank

Konzept für einen messbaren Vergleich von Neo4j und PostgreSQL

Kernidee: Derselbe reale Datensatz wird einmal relational in PostgreSQL und einmal als Graph in Neo4j modelliert. Anschließend werden fachlich identische Abfragen ausgeführt und hinsichtlich Laufzeit, Query-Komplexität, Datenmodell, Skalierbarkeit, Lesbarkeit/Wartbarkeit und optional Speicherbedarf verglichen.

## 1. Ziel und Forschungsfrage

Forschungsfrage: Wie unterscheiden sich eine relationale Datenbank und eine Graphdatenbank hinsichtlich Abfragegeschwindigkeit, Abfragekomplexität, Datenmodellierung und Skalierbarkeit bei zunehmend komplexen Beziehungsabfragen?

Das Projekt soll nicht beweisen, dass eine Graphdatenbank grundsätzlich schneller ist. Stattdessen wird untersucht, bei welchen Arten von Abfragen und bei welcher Beziehungstiefe sich Unterschiede zeigen.

## 2. Empfohlener Anwendungsfall

Ein soziales Netzwerk eignet sich besonders gut, weil die Daten stark über Beziehungen geprägt sind. Personen werden als Knoten bzw. Datensätze modelliert; Beziehungen wie „kennt" oder „vertraut" bilden die Verbindungen.

- Beispiel 1: Welche direkten Kontakte hat Person X?
- Beispiel 2: Welche Personen sind Freunde zweiten Grades?
- Beispiel 3: Welche Personen sind innerhalb von maximal vier Beziehungsschritten erreichbar?
- Beispiel 4: Was ist der kürzeste Verbindungspfad zwischen zwei Personen?
- Beispiel 5: Welche gemeinsamen Kontakte haben zwei Personen?

## 3. Technischer Vergleich

### 3.1 Datenmodell

- PostgreSQL: z. B. Tabelle `person(id, …)` plus `friendship(person_id, friend_id)`.
- Neo4j: z. B. `(:Person)-[:KNOWS]->(:Person)`.

### 3.2 Abfragegeschwindigkeit

Für jede fachlich identische Abfrage wird die Ausführungszeit in beiden Systemen gemessen. Statt einer Einzelmessung sollten mehrere Wiederholungen durchgeführt werden, z. B. 50 Läufe pro Query und Datenmenge.

- Minimum und Maximum
- arithmetischer Mittelwert
- Median
- Standardabweichung
- optional: getrennte Betrachtung von Cold Run und Warm Run

### 3.3 Abfragekomplexität

Die fachlich gleiche Fragestellung wird in SQL und Cypher implementiert. Neben der Laufzeit kann die strukturelle Komplexität der Queries verglichen werden.

- Anzahl der Query-Zeilen
- Anzahl der JOINs bzw. rekursiven CTEs in SQL
- Anzahl bzw. Tiefe der Pfadmuster in Cypher
- Lesbarkeit und Verständlichkeit der Query
- Aufwand, wenn die Beziehungstiefe von 2 auf 4 oder 5 Ebenen erhöht wird

### 3.4 Skalierbarkeit

Die gleichen Tests werden mit unterschiedlich großen Teilmengen desselben öffentlichen Datensatzes durchgeführt. Damit ist kein künstlicher Datengenerator nötig.

- kleine Datenmenge, z. B. einige Tausend Knoten
- mittlere Datenmenge, z. B. Zehntausende Knoten
- größere Datenmenge bzw. deutlich mehr Beziehungen

Wichtig: Die Teilmengen sollten reproduzierbar erzeugt werden, z. B. anhand einer festen Auswahl der ersten N Knoten oder eines dokumentierten Sampling-Verfahrens.

### 3.5 Lesbarkeit und Wartbarkeit

Hier wird qualitativ betrachtet, wie verständlich die Abfragen und das Datenmodell sind und wie stark sich eine Änderung der fachlichen Frage auf den Query-Aufbau auswirkt.

### 3.6 Speicherbedarf (optional)

Zusätzlich kann die belegte Datenbankgröße nach dem Import verglichen werden. Das sollte jedoch als ergänzende Kennzahl behandelt werden, weil Speicherformate, Indizes und interne Strukturen der Systeme unterschiedlich sind.

### 3.7 Grenzen des Graphansatzes

Zur Fairness sollten auch einfache Lookup-Abfragen getestet werden. So lässt sich zeigen, dass eine Graphdatenbank nicht automatisch bei jeder Operation im Vorteil ist.

## 4. Benchmark-Katalog

| Test | Fragestellung | Zweck |
|------|---------------|-------|
| T1 | Person anhand ID suchen | Baseline / einfacher Lookup |
| T2 | Direkte Kontakte einer Person | 1-Hop-Beziehung |
| T3 | Kontakte zweiten Grades | 2-Hop-Traversierung |
| T4 | Alle Personen bis Tiefe 4 | mehrstufige Traversierung |
| T5 | Kürzester Pfad zwischen zwei Personen | Pfadsuche |
| T6 | Gemeinsame Kontakte zweier Personen | Nachbarschaftsvergleich |
| T7 | Erreichbare Personen bei wachsender Datenmenge | Skalierung |

Für einen fairen Vergleich sollten beide Datenbanken auf demselben Rechner laufen, identische fachliche Ergebnisse liefern und sinnvoll indexiert sein. Außerdem sollten Datenbankversionen, Hardware, Anzahl der Wiederholungen und Cache-Zustand dokumentiert werden.

## 5. Beispiel für dieselbe fachliche Abfrage

Fragestellung: Welche Personen sind innerhalb von maximal vier Beziehungen mit Person X verbunden?

**PostgreSQL / SQL**

In einer relationalen Datenbank wird dafür typischerweise mit mehreren Self-Joins oder einer rekursiven CTE gearbeitet. Die genaue Implementierung sollte so gewählt werden, dass die Semantik exakt der Neo4j-Abfrage entspricht.

**Neo4j / Cypher**

```cypher
MATCH (p:Person {id: $id})-[:KNOWS*1..4]-(other)
RETURN DISTINCT other
```

## 6. Docker-Aufbau

Beide Datenbanken können parallel über Docker Compose gestartet werden. Ein separates Import- bzw. Benchmark-Skript lädt denselben Datensatz in beide Systeme und misst die Queries.

```
graph-vs-relational/
├── docker-compose.yml
├── postgres/
│   ├── schema.sql
│   └── queries.sql
├── neo4j/
│   └── queries.cypher
├── import/
│   └── import_dataset.py
├── benchmark/
│   └── benchmark.py
└── results/
```

Vorgesehene Systeme: PostgreSQL als relationale Datenbank und Neo4j als Graphdatenbank.

## 7. Öffentliche Datensätze – kein eigener Datengenerator nötig

Für das Projekt eignen sich reale Netzwerkdatensätze besonders gut. Die folgenden Datensätze sind öffentlich verfügbar und lassen sich sowohl als Kantenliste in Neo4j als auch relational in PostgreSQL importieren.

| Datensatz | Knoten | Kanten / Beziehungen | Eignung | Quelle |
|-----------|--------|-----------------------|---------|--------|
| SNAP Facebook Social Circles | 4.039 | 88.234 | Undirektionales soziales Netzwerk; sehr guter Einstieg und schnell importierbar. | https://snap.stanford.edu/data/ego-Facebook.html |
| SNAP Wikipedia Vote | 7.115 | 103.689 | Gerichtete Nutzerbeziehungen; gut für gerichtete Pfade und Traversierungen. | https://snap.stanford.edu/data/wiki-Vote.html |
| SNAP Enron Email Network | 36.692 | 183.831 | Reales Kommunikationsnetzwerk; gute mittlere Größe für aussagekräftige Benchmarks. | https://snap.stanford.edu/data/email-Enron.html |
| SNAP Epinions | 75.879 | 508.837 | Who-trusts-whom-Netzwerk; deutlich größer und gut für Skalierungs- und Traversierungstests. | https://snap.stanford.edu/data/soc-Epinions1.html |
| MovieLens 1M | ca. 6.000 Nutzer + 4.000 Filme | 1 Mio. Ratings | Alternative mit zwei Knotentypen (User, Movie) und RATED-Beziehungen; gut für Empfehlungsabfragen. | https://grouplens.org/datasets/movielens/1m/ |

Empfehlung für den Projektstart: Zuerst den Facebook-Datensatz verwenden. Er ist klein genug für schnelle Iterationen, besitzt aber bereits 88.234 Beziehungen. Danach denselben Benchmark mit Enron oder Epinions wiederholen, um die Skalierung zu untersuchen.

Alternative, wenn du einen fachlich reicheren Anwendungsfall möchtest: MovieLens 1M. Dabei werden Nutzer und Filme als unterschiedliche Entitäten modelliert. Mögliche Fragen wären z. B. „Welche Filme wurden von Nutzern bewertet, die ähnliche Filme wie Nutzer X mögen?" Für einen klaren Graph-vs.-SQL-Vergleich ist das soziale Netzwerk jedoch einfacher.

## 8. Konkreter Projektablauf

1. Öffentlichen Datensatz herunterladen und Format dokumentieren.
2. Docker Compose mit PostgreSQL und Neo4j starten.
3. Relationales Schema und Graphmodell definieren.
4. Denselben Datensatz in beide Datenbanken importieren.
5. Sinnvolle Indizes in beiden Systemen anlegen.
6. T1 bis T7 fachlich identisch in SQL und Cypher implementieren.
7. Warm-up durchführen und anschließend z. B. 50 Messungen pro Query ausführen.
8. Messwerte automatisch als CSV speichern.
9. Mittelwert, Median, Minimum, Maximum und Standardabweichung berechnen.
10. Query-Komplexität, Datenmodell, Lesbarkeit/Wartbarkeit und optional Speicherbedarf ergänzend bewerten.
11. Ergebnisse als Tabellen und Diagramme darstellen und Grenzen des Benchmarks diskutieren.

## 9. Beispiel für die spätere Ergebnisdarstellung

| Abfrage | PostgreSQL | Neo4j | Interpretation |
|---------|-----------|-------|-----------------|
| T1 – Lookup nach ID | Messwert | Messwert | Baseline; keine pauschale Erwartung |
| T3 – 2-Hop | Messwert | Messwert | Beziehungstraversierung |
| T4 – Tiefe 4 | Messwert | Messwert | Effekt zunehmender Pfadtiefe |
| T5 – kürzester Pfad | Messwert | Messwert | Graph-/Pfadoperation |

Die Schlussfolgerung sollte erst aus den Messungen entstehen. Eine sinnvolle Erwartung ist lediglich, dass sich die Systeme bei einfachen Lookup-Abfragen und bei tiefen Beziehungsabfragen unterschiedlich verhalten können.

## 10. Quellen zu den Datensätzen

- Stanford SNAP – Facebook Social Circles: https://snap.stanford.edu/data/ego-Facebook.html
- Stanford SNAP – Wikipedia Vote Network: https://snap.stanford.edu/data/wiki-Vote.html
- Stanford SNAP – Enron Email Network: https://snap.stanford.edu/data/email-Enron.html
- Stanford SNAP – Epinions Social Network: https://snap.stanford.edu/data/soc-Epinions1.html
- GroupLens – MovieLens 1M: https://grouplens.org/datasets/movielens/1m/

## Offene Punkte (noch zu entscheiden)

Beim ersten Review wurden 10 unklare bzw. potenziell unfaire Stellen in diesem Konzept identifiziert (Kantenrichtung, Index-Strategie, Ressourcen-Parität der Container, Cold/Warm-Protokoll, widersprüchliche Skalierungsmethode in 3.4 vs. 7, Sampling-Verzerrung, Formatierungsabhängigkeit der Komplexitätsmetriken, Treiber-Overhead, Zeitpunkt der Speichermessung). Diese Diskussion wurde bewusst zurückgestellt, bis Workspace und Prototyp stehen — siehe Team-Besprechung, bevor die eigentlichen T1–T7-Queries implementiert werden.
