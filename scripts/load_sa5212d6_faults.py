"""
load_sa5212d6_faults.py — SA5212D6/SA5326D6 specific fault codes.
SMART errors, BMC-specific issues, GPU/PCIe/BIOS faults. Deduplicates
against existing knowledge entries. Content lives in
kb_content/sa5212d6_faults.json, which is not tracked in version control
(see kb_content/README.md).

    python -m scripts.load_sa5212d6_faults
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from fiars import db, kb_content
from fiars.config import load_config


def main():
    entries = kb_content.load("sa5212d6_faults")

    cfg = load_config()
    path = cfg["db_path"]
    db.init_db(path)

    con = db.connect(path)
    has = con.execute("SELECT 1 FROM knowledge WHERE error_code='SMART_197'").fetchone()
    con.close()
    if has:
        print("SA5212D6 fault codes already loaded. Skipping.")
        return

    for e in entries:
        db.add_knowledge(path, e)
    print(f"Loaded {len(entries)} SA5212D6-specific fault codes.")
    print(f"Total knowledge entries: {db.count_knowledge(path)}")


if __name__ == "__main__":
    main()
