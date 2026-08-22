# kb_content/

This directory holds the actual text content for FIARS's built-in
knowledge base — troubleshooting entries and the Power_Fault article
that `scripts/load_*.py` insert into `fiars.db`.

**These JSON files are intentionally not tracked in git.** The content
is derived from vendor troubleshooting documentation, and this repo is
public, so it stays local to each installation instead of being
published.

## Files expected here

- `server_fault_kb.json` — list of entries (`scripts/load_server_fault_kb.py`)
- `gpu_faults.json` — list of entries (`scripts/load_gpu_faults.py`)
- `reference_data.json` — list of entries (`scripts/load_reference_data.py`)
- `sa5212d6_faults.json` — list of entries (`scripts/load_sa5212d6_faults.py`)
- `sel_smart_xid.json` — list of entries (`scripts/load_sel_smart_xid.py`)
- `confirmed_solutions.json` — list of entries (`scripts/load_confirmed_solutions.py`)
- `power_fault_article.json` — single article dict (`scripts/load_kb_power_fault.py`)

## Entry format

Each "list of entries" file is a JSON array of objects shaped like:

```json
{
  "category": "CPU",
  "error_code": "CPU_IERR",
  "fault_description": "...",
  "affected_parts": "...",
  "root_cause": "...",
  "solution": "...",
  "source": "..."
}
```

`power_fault_article.json` is a single object with `title`, `scope`,
`problem`, `solution`, `root_cause`, `suggestions`, `source_url`, and
`error_map` (a list of `{error_pattern, power_rail, suspect_components,
dimm_slots, remark?}` objects).

## Setup on a fresh clone / new machine

Copy your existing `kb_content/*.json` files here (they're not part of
the repo), then run each loader once:

```
python -m scripts.load_server_fault_kb
python -m scripts.load_gpu_faults
python -m scripts.load_reference_data
python -m scripts.load_sa5212d6_faults
python -m scripts.load_sel_smart_xid
python -m scripts.load_confirmed_solutions
python -m scripts.load_kb_power_fault
```

Each loader checks for existing entries first and skips if already
loaded, so re-running them is safe.
