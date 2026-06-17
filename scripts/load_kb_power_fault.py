"""
load_kb_power_fault.py — Load the SA5212D6/SA5326D6 Power_Fault KB article.

Structured from the vendor KB article. Each BMC log error pattern maps to
suspect components and (for memory faults) specific DIMM slot locations.

    python -m scripts.load_kb_power_fault
"""

import sys
sys.path.insert(0, ".")

from fiars import db
from fiars.config import load_config


ARTICLE = {
    "title": "SA5212D6/SA5326D6 Power_Fault Alarm Troubleshooting",
    "scope": "SA5212D6, SA5326D6",
    "problem": (
        "Machine crashes during operation. BMC log records Power_Fault alarm "
        "with corresponding voltage alarms. After crash, cannot power on online; "
        "must restart after AC power-off on site."
    ),
    "solution": (
        "1. Keep system in downtime, collect one-click logs, check error messages.\n"
        "2. Power on after cutting off AC power on site; if fault reproduces, "
        "perform minimal testing to locate faulty component.\n"
        "3. If machine returns to normal after power-off, replace component "
        "based on error indication table.\n"
        "Note: After abnormal power-off, CPLD controls motherboard power-off "
        "and sequence enters power fault state. This state cannot be cleared "
        "and can only be powered on again after cutting off AC power."
    ),
    "root_cause": (
        "After abnormal motherboard power-off (many potential causes), the CPLD "
        "controls power-off and the sequence enters power fault state. This state "
        "cannot be cleared; can only power on after cutting off AC power."
    ),
    "suggestions": (
        "Combine log analysis and minimal testing to identify fault point. "
        "Do NOT replace components blindly. If the specific DIMM slot can be "
        "seen in the log, replace only that specific DIMM — do NOT replace all "
        "DIMMs in the corresponding group."
    ),
    "source_url": "https://kb.surpech.com/spaceDetail/116129799/170066311",
    "error_map": [],
}

# ── CPU/Motherboard errors (no DIMM) ─────────────────────────────────────────
_CPU_MB = [
    ("PVCCIN_CPU0_Fault",      "PVCCIN_CPU0"),
    ("PVCCIN_CPU1_Fault",      "PVCCIN_CPU1"),
    ("PVCCSA_CPU0_Fault",      "PVCCSA_CPU0"),
    ("PVCCSA_CPU1_Fault",      "PVCCSA_CPU1"),
    ("PVCCIO_CPU0_Fault",      "PVCCIO_CPU0"),
    ("PVCCIO_CPU1_Fault",      "PVCCIO_CPU1"),
    ("PVCCANA_CPU0_Fault",     "PVCCANA_CPU0"),
    ("PVCCANA_CPU1_Fault",     "PVCCANA_CPU1"),
    ("P1V8_PCIE_CPU0_FAULT",   "P1V8_CPU0"),
    ("P1V8_PCIE_CPU1_FAULT",   "P1V8_CPU1"),
]
for pat, rail in _CPU_MB:
    ARTICLE["error_map"].append({
        "error_pattern": pat,
        "power_rail": rail,
        "suspect_components": ["Motherboard", "CPU"],
        "dimm_slots": [],
    })

# ── Memory/DIMM errors (PVDDQ, PVPP, PVTT) ──────────────────────────────────
_DIMM_GROUPS = {
    "CPU0_GROUP0": {
        "slots": ["P0_C1_D0","P0_C1_D1","P0_C0_D0","P0_C0_D1",
                   "P0_C3_D0","P0_C3_D1","P0_C2_D0","P0_C2_D1"],
        "rail_suffix": "ABCD_CPU0",
    },
    "CPU0_GROUP1": {
        "slots": ["P0_C6_D0","P0_C6_D1","P0_C7_D0","P0_C7_D1",
                   "P0_C4_D0","P0_C4_D1","P0_C5_D0","P0_C5_D1"],
        "rail_suffix": "EFGH_CPU0",
    },
    "CPU1_GROUP0": {
        "slots": ["P1_C1_D0","P1_C1_D1","P1_C0_D0","P1_C0_D1",
                   "P1_C3_D0","P1_C3_D1","P1_C2_D0","P1_C2_D1"],
        "rail_suffix": "ABCD_CPU1",
    },
    "CPU1_GROUP1": {
        "slots": ["P1_C6_D0","P1_C6_D1","P1_C7_D0","P1_C7_D1",
                   "P1_C4_D0","P1_C4_D1","P1_C5_D0","P1_C5_D1"],
        "rail_suffix": "EFGH_CPU1",
    },
}
for prefix in ("PVDDQ", "PVPP", "PVTT"):
    for group_key, group in _DIMM_GROUPS.items():
        pat = f"{prefix}_{group_key}_FAULT"
        rail = f"{prefix}_{group['rail_suffix']}"
        if prefix == "PVDDQ":
            suspects = ["Memory/DIMM", "Motherboard", "CPU"]
        else:
            suspects = ["Memory/DIMM", "Motherboard"]
        ARTICLE["error_map"].append({
            "error_pattern": pat,
            "power_rail": rail,
            "suspect_components": suspects,
            "dimm_slots": group["slots"],
            "remark": f"DIMM locations: {', '.join(group['slots'])}",
        })

# ── Board/power errors ───────────────────────────────────────────────────────
_BOARD = [
    ("PVNN_PCH_AUX_FAULT",   "PVNN_STBY",   ["Motherboard"]),
    ("P1V05_PCH_AUX_FAULT",  "P1V05_STBY",  ["Motherboard"]),
    ("P12V_FAULT",            "P12V",         ["Motherboard"]),
    ("P12V_STBY_FAULT",       "P12V_STBY",   ["Motherboard"]),
    ("P12V_NVME_FAULT",       "P12V_NVME",   ["Motherboard", "Hard drive backplane"]),
    ("P3V3_FAULT",            "P3V3",         ["Motherboard"]),
    ("P5V_AUX_FAULT",         "P5V_STBY",    ["Motherboard"]),
    ("P3V3_AUX_FAULT",        "P3V3_STBY",   ["Motherboard", "Other small cards"]),
    ("P5V_FAULT",             "P5V",          ["Right ear board", "Motherboard"]),
    ("P12V_FAN_FAULT",        "P12V_FAN0-5", ["Fan", "Motherboard"]),
    ("P1V2_AUX_FAULT",        "P1V2_STBY",   ["Motherboard"]),
    ("P1V15_AUX_FAULT",       "P1V15_STBY",  ["Motherboard"]),
    ("P1V8_AUX_FAULT",        "P1V8_STBY",   ["Motherboard"]),
    ("P2V5_AUX_FAULT",        "P2V5_STBY",   ["Motherboard"]),
]
for pat, rail, suspects in _BOARD:
    ARTICLE["error_map"].append({
        "error_pattern": pat,
        "power_rail": rail,
        "suspect_components": suspects,
        "dimm_slots": [],
    })


def main():
    cfg = load_config()
    path = cfg["db_path"]
    db.init_db(path)

    # Check if already loaded
    con = db.connect(path)
    existing = con.execute(
        "SELECT kb_id FROM kb_articles WHERE title=?", (ARTICLE["title"],)
    ).fetchone()
    con.close()
    if existing:
        print(f"KB article already loaded (kb_id={existing[0]}). Skipping.")
        return

    kb_id = db.save_kb_article(path, ARTICLE)
    kbs = db.kb_stats(path)
    print(f"Loaded KB article: '{ARTICLE['title']}' (kb_id={kb_id})")
    print(f"  {len(ARTICLE['error_map'])} error patterns indexed")
    print(f"  DB totals: {kbs['kb_articles']} articles, {kbs['kb_patterns']} patterns")


if __name__ == "__main__":
    main()
