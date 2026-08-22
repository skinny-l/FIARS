"""
load_server_fault_kb.py — Server Fault Knowledge Base (29 entries).
Content is sourced from vendor server fault troubleshooting
documentation and lives in kb_content/server_fault_kb.json, which is not
tracked in version control (see kb_content/README.md).

    python -m scripts.load_server_fault_kb
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from fiars import db, kb_content
from fiars.config import load_config


def main():
    entries = kb_content.load("server_fault_kb")

    cfg = load_config()
    path = cfg["db_path"]
    db.init_db(path)

    con = db.connect(path)
    has = con.execute("SELECT 1 FROM knowledge WHERE error_code='CPU_IERR'").fetchone()
    con.close()
    if has:
        print("Server Fault KB already loaded. Skipping.")
        return

    for e in entries:
        db.add_knowledge(path, e)
    print(f"Loaded {len(entries)} server fault KB entries.")
    print(f"Total knowledge entries: {db.count_knowledge(path)}")


if __name__ == "__main__":
    main()
