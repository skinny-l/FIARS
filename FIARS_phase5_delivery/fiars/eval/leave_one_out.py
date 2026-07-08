"""
leave_one_out.py — does the recommendation engine recover the correct root
cause for a case, when that case itself is hidden from the search index?

For every case_history row with a non-empty root_cause:
  1. Hide it (exclude_id) so it can't match against itself.
  2. Retrieve similar cases from the rest of the dataset.
  3. Run the same weighted aggregation recommend.py uses in production.
  4. Record the rank of the case's own (true) root cause in that ranking.

Run as a script for the headline numbers used in README.md:
    python -m fiars.eval.leave_one_out fiars.db
    python -m fiars.eval.leave_one_out fiars.db --mode lexical   # Phase 3 baseline
    python -m fiars.eval.leave_one_out fiars.db --mode hybrid    # needs build_index.py run first
"""
from __future__ import annotations

import argparse
import sys

from .. import db
from ..recommend import _aggregate
from ..retrieval import hybrid, lexical
from . import metrics


def _rank_of_true_label(ranked: list[dict], true_label: str) -> int | None:
    true_label = (true_label or "").strip()
    if not true_label:
        return None
    for i, bucket in enumerate(ranked):
        if bucket["label"] == true_label:
            return i + 1
    return None


def run(path: str, mode: str = "auto", k: int = 50, encoder=None) -> dict:
    """
    mode: "lexical" forces Phase-3-only retrieval; "hybrid" forces fused
    retrieval (raises if no embedding index has been built); "auto" uses
    hybrid when an index exists, else lexical — mirrors what diagnose() does
    for real users.

    encoder: only used for tests (injects a fake embedder). Real CLI usage
    never passes this — it uses whatever index scripts/build_index.py built.
    """
    if mode == "hybrid" and not hybrid.semantic.index_ready(path):
        raise RuntimeError(
            "No embedding index found. Run `python scripts/build_index.py "
            f"{path}` first, or use --mode lexical / --mode auto."
        )

    con = db.connect(path)
    rows = con.execute(
        "SELECT id, error_fault, root_cause FROM case_history "
        "WHERE root_cause IS NOT NULL AND TRIM(root_cause) != ''"
    ).fetchall()
    con.close()

    ranks: list[int | None] = []
    for r in rows:
        case_id, query, true_cause = r["id"], r["error_fault"], r["root_cause"]
        if not (query or "").strip():
            continue
        if mode == "lexical":
            cases = lexical.search(path, query, k=k, exclude_id=case_id)
        else:
            cases = hybrid.retrieve(path, query, k=k, exclude_id=case_id, encoder=encoder)
        ranked_causes, _mass, _found = _aggregate(cases, "root_cause_raw")
        ranks.append(_rank_of_true_label(ranked_causes, true_cause))

    result = metrics.score(ranks)
    result["mode"] = mode
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("db_path")
    parser.add_argument("--mode", choices=["auto", "lexical", "hybrid"], default="auto")
    parser.add_argument("--k", type=int, default=50)
    args = parser.parse_args(argv)

    result = run(args.db_path, mode=args.mode, k=args.k)
    print(f"mode={result['mode']}  n={result['n']}  "
          f"top-1={result['top_1']:.1%}  top-3={result['top_3']:.1%}  mrr={result['mrr']:.4f}")
    return result


if __name__ == "__main__":
    main(sys.argv[1:])
