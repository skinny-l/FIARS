"""
load_kb_power_fault.py — Load the SA5212D6/SA5326D6 Power_Fault KB article.

Structured from the vendor KB article: each BMC log error pattern maps
to suspect components and (for memory faults) specific DIMM slot
locations. Content lives in kb_content/power_fault_article.json, which
is not tracked in version control (see kb_content/README.md).

    python -m scripts.load_kb_power_fault
"""

import sys
sys.path.insert(0, ".")

from fiars import db, kb_content
from fiars.config import load_config


def main():
    article = kb_content.load("power_fault_article")

    cfg = load_config()
    path = cfg["db_path"]
    db.init_db(path)

    con = db.connect(path)
    existing = con.execute(
        "SELECT kb_id FROM kb_articles WHERE title=?", (article["title"],)
    ).fetchone()
    con.close()
    if existing:
        print(f"KB article already loaded (kb_id={existing[0]}). Skipping.")
        return

    kb_id = db.save_kb_article(path, article)
    kbs = db.kb_stats(path)
    print(f"Loaded KB article: '{article['title']}' (kb_id={kb_id})")
    print(f"  {len(article['error_map'])} error patterns indexed")
    print(f"  DB totals: {kbs['kb_articles']} articles, {kbs['kb_patterns']} patterns")


if __name__ == "__main__":
    main()
