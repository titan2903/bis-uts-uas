"""D4 — enam test kualitas data pada seed T2/k8.

Jalankan: python tests/run_tests.py [--topic t2 --slice k8] [--json]
Exit 1 berarti ada blocking FAIL, error, atau hasil tidak sesuai expected.
Expected mencatat cacat seed, bukan izin melewatkan blocking FAIL.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

import duckdb
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from pipeline import config  # noqa: E402

DIMENSIONS = {"completeness", "uniqueness", "validity", "consistency", "timeliness", "accuracy"}
SEVERITIES = {"blocking", "warning"}


def load_definitions(path: str, topic: str, slice_id: str) -> list[dict]:
    with open(path, encoding="utf-8") as handle:
        document = yaml.safe_load(handle)
    if not isinstance(document, dict) or not isinstance(document.get("tests"), list):
        raise ValueError("YAML harus berisi daftar tests.")
    if not all(isinstance(test, dict) for test in document["tests"]):
        raise ValueError("Setiap test harus berupa mapping.")
    tests = [t for t in document["tests"]
             if t.get("topic") == topic and t.get("slice") == slice_id]
    if len(tests) != 6 or {t.get("dimension") for t in tests} != DIMENSIONS:
        raise ValueError(f"Topik/slice {topic}/{slice_id} perlu tepat enam test, satu per dimensi.")
    if len({t.get("name") for t in tests}) != 6:
        raise ValueError("Nama enam test harus unik.")
    for test in tests:
        if (not isinstance(test.get("sql"), str) or not test["sql"].strip()
                or not isinstance(test.get("name"), str)
                or test.get("severity") not in SEVERITIES
                or test.get("expected") not in {"pass", "fail"}
                or not isinstance(test.get("justifikasi"), str)
                or not test["justifikasi"].strip() or "\n" in test["justifikasi"]):
            raise ValueError(f"Definisi test tidak lengkap: {test.get('name')}")
    return tests


def prepare(con: duckdb.DuckDBPyConnection, ctx: dict) -> tuple[list[str], bool]:
    """Baca CSV sebagai view tanpa mengubah grain sumber."""
    views = []
    for filename in sorted(ctx["cfg"]["files"]):
        path = os.path.join(ctx["dir"], filename).replace("'", "''")
        name = "raw_" + Path(filename).stem
        con.execute(f"CREATE OR REPLACE TEMP VIEW {name} AS "
                    f"SELECT * FROM read_csv_auto('{path}', all_varchar=true)")
        views.append(name)
    db = os.path.join(config.WAREHOUSE, f"{ctx['topic']}_{ctx['slice']}.duckdb")
    has_warehouse = os.path.exists(db)
    if has_warehouse:
        safe = db.replace("'", "''")
        con.execute(f"ATTACH '{safe}' AS wh (READ_ONLY)")
    return views, has_warehouse


def evaluate(con: duckdb.DuckDBPyConnection, tests: list[dict]) -> list[dict]:
    results = []
    for test in tests:
        result = {**test, "expected": test["expected"]}
        try:
            rows = con.execute(test["sql"]).fetchall()
            if (len(rows) != 1 or len(rows[0]) != 1
                    or not isinstance(rows[0][0], int) or isinstance(rows[0][0], bool)
                    or rows[0][0] < 0):
                raise ValueError("SQL harus menghasilkan satu bilangan bulat nonnegatif")
            count = rows[0][0]
            actual = "fail" if count else "pass"
            result.update(pelanggaran=count, hasil=actual.upper(),
                          sesuai_harapan=(actual == result["expected"]))
        except Exception as exc:
            result.update(hasil="ERROR", catatan=str(exc).split("\n")[0][:160])
        results.append(result)
    return results


def display(results: list[dict]) -> None:
    for result in results:
        mark = {"PASS": "✓", "FAIL": "✗"}.get(result["hasil"], "•")
        count = result.get("pelanggaran")
        number = f"{count:,}" if isinstance(count, int) else "-"
        matches = {True: "sesuai harapan", False: "TIDAK sesuai harapan"}.get(
            result.get("sesuai_harapan"), "")
        print(f"{mark} [{result['severity']:<8}] {result['name']:<40} "
              f"pelanggaran={number:<8} expected={result['expected']:<5} {matches}")
        if result.get("catatan"):
            print("      catatan: " + result["catatan"])
    failed = sum(r["hasil"] == "FAIL" for r in results)
    blocking = sum(r.get("severity") == "blocking" and r["hasil"] == "FAIL" for r in results)
    unexpected = sum(r["hasil"] == "ERROR" or r.get("sesuai_harapan") is False for r in results)
    print(f"\n{failed} test menangkap masalah · {blocking} blocking FAIL (load ditahan) · "
          f"{unexpected} hasil/error tidak sesuai harapan")

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--topic", default="t2", choices=sorted(config.TOPICS))
    parser.add_argument("--slice", default=None)
    parser.add_argument("--file", default=str(Path(config.ROOT) / "tests/test_definitions.yml"))
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    args.slice = args.slice or sorted(config.TOPICS[args.topic]["slices"])[0]
    if args.slice not in config.TOPICS[args.topic]["slices"]:
        parser.error(f"Slice {args.slice} tidak dikenal untuk {args.topic}.")
    try:
        ctx = config.resolve(args.topic, args.slice)
        tests = load_definitions(args.file, args.topic, args.slice)
        with duckdb.connect() as con:
            views, has_warehouse = prepare(con, ctx)
            if any(t.get("scope") == "warehouse" for t in tests) and not has_warehouse:
                raise ValueError("Test membutuhkan warehouse; jalankan pipeline.load dulu.")
            results = evaluate(con, tests)
    except (ValueError, OSError, duckdb.Error, yaml.YAMLError) as exc:
        raise SystemExit(f"ERROR: {exc}") from exc
    if args.json:
        print(json.dumps(results, indent=2, ensure_ascii=False))
    else:
        print(f"# Test kualitas — {ctx['cfg']['label']} / {args.slice}")
        print(f"# {len(tests)} test · view: {', '.join(views)}\n")
        display(results)
    blocked = any(r["hasil"] == "ERROR" or r.get("sesuai_harapan") is False
                  or (r["severity"] == "blocking" and r["hasil"] == "FAIL")
                  for r in results)
    sys.exit(1 if blocked else 0)


if __name__ == "__main__":
    main()
