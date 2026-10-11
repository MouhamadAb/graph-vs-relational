"""Orchestriert den T7-Skalierungstest ueber mehrere Datengroessen.

Boilerplate (ruft nur import_dataset.py und benchmark.py per Subprocess auf,
keine eigene Mess-/Kernlogik) - loest das bisher manuelle Problem, dass
benchmark.py results/T7.csv bei jedem Lauf ueberschreibt: dieses Skript
sichert nach jeder Groesse automatisch unter results/T7_n<Groesse>.csv und
importiert am Ende wieder den vollen Datensatz, damit die DB nicht in einem
Teilmengen-Zustand haengen bleibt.
"""

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RESULTS_DIR = ROOT / "results"


def run(cmd: list[str]) -> None:
    print("$ " + " ".join(cmd))
    subprocess.run(cmd, check=True, cwd=ROOT)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="T7-Skalierungstest ueber mehrere Groessen.")
    parser.add_argument("--sizes", type=int, nargs="+", default=[500, 1000, 2000, 3000, 4039])
    parser.add_argument("--runs", type=int, default=50)
    parser.add_argument("--warmup", type=int, default=5)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--edgelist", default="facebook_combined.txt")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    python = sys.executable

    for size in args.sizes:
        print(f"\n=== Groesse {size} ===")
        import_cmd = [python, "import/import_dataset.py", args.edgelist, "--reset", "--seed", str(args.seed)]
        if size < 4039:
            import_cmd += ["--sample-nodes", str(size)]
        run(import_cmd)

        run([python, "benchmark/benchmark.py", "T7", "--runs", str(args.runs), "--warmup", str(args.warmup), "--seed", str(args.seed)])

        src = RESULTS_DIR / "T7.csv"
        dst = RESULTS_DIR / f"T7_n{size}.csv"
        shutil.copy(src, dst)
        print(f"Gesichert: {dst}")

    print("\n=== Voller Datensatz wird wiederhergestellt ===")
    run([python, "import/import_dataset.py", args.edgelist, "--reset"])
    print("\nFertig.")


if __name__ == "__main__":
    main()
