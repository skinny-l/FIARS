"""
load_reference_data.py — BMC SEL events, SMART thresholds, Xid errors,
CPU link faults. Content is sourced from SA5212D6/SA5326D6 vendor KB
extraction and lives in kb_content/reference_data.json, which is not
tracked in version control (see kb_content/README.md).

    python -m scripts.load_reference_data
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from fiars import db, kb_content
from fiars.config import load_config


def main():
    entries = kb_content.load("reference_data")

    cfg = load_config()
    path = cfg["db_path"]
    db.init_db(path)
    con = db.connect(path)
    has = con.execute("SELECT 1 FROM knowledge WHERE error_code='SEL_0x04'").fetchone()
    con.close()
    if has:
        print("Reference data already loaded. Skipping.")
        return
    for e in entries:
        db.add_knowledge(path, e)
    print(f"Loaded {len(entries)} reference entries (SEL, SMART, Xid, CPU).")
    print(f"Total knowledge entries: {db.count_knowledge(path)}")


if __name__ == "__main__":
    main()
