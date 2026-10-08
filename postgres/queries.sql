-- SQL-Implementierung der Benchmark-Queries T1-T7.
-- Siehe docs/konzept.md Abschnitt 4 fuer die Fragestellungen.
--
-- Kernlogik: eigentlich bewusst vom Team zu schreiben (Lernmodus, siehe
-- CLAUDE.md). T1-T7 wurden auf ausdruecklichen, wiederholt bestaetigten
-- Wunsch des Teams komplett fertig geschrieben (siehe Memory
-- lernmodus-ausnahme-schema-import).
-- Wichtig: Jede Query muss fachlich identische Ergebnisse liefern wie die
-- entsprechende Cypher-Query in neo4j/queries.cypher.

-- T1: Person anhand ID suchen (Baseline / einfacher Lookup)
-- Parametrisiert (%(id)s), nicht als String zusammengebaut -> keine SQL-Injection.
SELECT id
FROM person
WHERE id = %(id)s;

-- T2: Direkte Kontakte einer Person (1-Hop)
-- Wegen Options-A-Entscheidung (eine Zeile pro Paar) steht die gesuchte ID
-- mal in person_id, mal in friend_id -> OR auf beide Spalten, und CASE waehlt
-- jeweils die ANDERE Spalte als Ergebnis (den Kontakt, nicht die Person X selbst).
SELECT CASE
           WHEN person_id = %(id)s THEN friend_id
           ELSE person_id
       END AS contact_id
FROM friendship
WHERE person_id = %(id)s OR friend_id = %(id)s;

-- T3: Kontakte zweiten Grades (2-Hop)
-- Begriffsklaerung (Annahme): "Freunde zweiten Grades" = ueber genau 2 Hops
-- erreichbar, OHNE Person X selbst und OHNE deren direkte (1-Hop-)Kontakte.
-- Sonst waeren gemeinsame Freunde faelschlich als "zweiten Grades" dabei,
-- obwohl sie schon direkte Kontakte sind. Dieselbe Annahme gilt in der
-- Cypher-Variante.
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
  AND c2.b NOT IN (SELECT b FROM contacts WHERE a = %(id)s);

-- T4: Alle Personen bis Tiefe 4 (rekursive CTE)
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
SELECT DISTINCT contact_id
FROM reachable
WHERE contact_id <> %(id)s;

-- T5: Kuerzester Pfad zwischen zwei Personen
-- Einschraenkung / Fairness-Punkt 2 (siehe docs/konzept.md): Cyphers
-- shortestPath() bricht ab, sobald der Pfad gefunden ist. Diese CTE berechnet
-- stattdessen schichtweise (Breitensuche) ALLE Distanzen bis max. Tiefe 8
-- (SNAP nennt 8 als Durchmesser des Facebook-Graphen) und liest danach die
-- gesuchte Distanz heraus - mehr Rechenaufwand als Cyphers fruehzeitiger
-- Abbruch. Geliefert wird nur die Distanz (Anzahl Hops), nicht die konkrete
-- Knotenfolge des Pfads - das waere in SQL deutlich aufwendiger zu
-- rekonstruieren und ist hier bewusst ausgespart.
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
SELECT min(depth) AS distance
FROM bfs
WHERE contact_id = %(id2)s;

-- T6: Gemeinsame Kontakte zweier Personen
WITH contacts AS (
    SELECT person_id AS a, friend_id AS b FROM friendship
    UNION ALL
    SELECT friend_id AS a, person_id AS b FROM friendship
)
SELECT DISTINCT c1.b AS contact_id
FROM contacts c1
JOIN contacts c2 ON c1.b = c2.b
WHERE c1.a = %(id1)s AND c2.a = %(id2)s;

-- T7: Skalierung (Fairness-Punkt 6, entschieden: Teilmengen desselben Graphen)
-- Keine eigene Query - T7 ist T4, wiederholt auf unterschiedlich grossen
-- Teilmengen (Snowball-/BFS-Sampling mit festem Seed, siehe
-- import_dataset.py --sample-nodes/--seed und docs/konzept.md
-- "Entscheidungen"). benchmark.py fuehrt T7 deshalb identisch zu T4 aus.
