"""
load_gpu_faults.py — GPU fault codes for SA5212D6/SA5326D6.
Content is sourced from vendor GPU troubleshooting documentation and
lives in kb_content/gpu_faults.json, which is not tracked in version
control (see kb_content/README.md).

    python -m scripts.load_gpu_faults
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from fiars import db, kb_content
from fiars.config import load_config


def main():
    entries = kb_content.load("gpu_faults")

    cfg = load_config()
    path = cfg["db_path"]
    db.init_db(path)
    con = db.connect(path)
    has = con.execute("SELECT 1 FROM knowledge WHERE error_code='GPU_Xid_79_Fallen_Off_Bus'").fetchone()
    con.close()
    if has:
        print("GPU fault codes already loaded. Skipping.")
        return
    for e in entries:
        db.add_knowledge(path, e)
    print(f"Loaded {len(entries)} GPU fault codes.")
    print(f"Total knowledge entries: {db.count_knowledge(path)}")


if __name__ == "__main__":
    main()
