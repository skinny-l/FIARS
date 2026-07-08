"""
build_index.py — build/refresh the semantic embedding index used by
Phase 4 hybrid retrieval.

Requires the ML extra (not installed by default, so the base app stays
zero-dependency):
    pip install -r requirements-ml.txt

Usage:
    python scripts/build_index.py                  # uses config.json's db_path
    python scripts/build_index.py path/to/fiars.db

First run downloads the ~80MB all-MiniLM-L6-v2 model from Hugging Face
(needs internet, once). After that, everything is fully offline. Safe to
re-run any time — unchanged cases are skipped automatically.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fiars.config import load_config
from fiars.retrieval import semantic


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if argv:
        db_path = argv[0]
    else:
        db_path = load_config().get("db_path", "fiars.db")

    if not semantic.available():
        print(
            "sentence-transformers isn't installed.\n"
            "Run: pip install -r requirements-ml.txt\n"
            "(FIARS works fine without it — this just enables semantic/hybrid search "
            "instead of lexical-only.)",
            file=sys.stderr,
        )
        return 1

    print(f"Building embedding index for {db_path} ...")
    n = semantic.build_index(db_path)
    print(f"Done. Embedded/updated {n} case(s).")
    print("Hybrid retrieval is now active for new diagnose() calls.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
