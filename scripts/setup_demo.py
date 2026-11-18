"""Generate the reproducible sample dataset, build SQLite, and refresh SQL report.

Run from repository root: python -m scripts.setup_demo
This writes ONLY generated synthetic artifacts to data/ and reports/.
"""
from pathlib import Path

from src.database import load
from src.generate_data import generate
from scripts.evaluate_segments import evaluate


def main():
    csv_path = Path("data/bank_service_tickets.csv")
    db_path = Path("data/bankops.db")
    records = generate(csv_path, n=2600, seed=42)
    count = load(csv_path, db_path)
    if len(records) != count:
        raise RuntimeError("Generated CSV and imported SQLite row counts differ")
    evaluate()
    print("Demo dataset ready: {} synthetic tickets at {}".format(count, db_path))


if __name__ == "__main__":
    main()
