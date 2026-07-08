"""
fiars.analytics — Phase 5 read-only analytics over case_history.

queries.py  — raw SQL pulls (stdlib sqlite3 only, no pandas dependency)
metrics.py  — derived/formatted metrics built on top of queries.py,
              including a real (not simulated) confidence-calibration check
              that reuses recommend.diagnose() via leave-one-out sampling.

Nothing here writes to the database. Consumed by dashboard/streamlit_app.py,
but every function is plain stdlib and independently unit-testable without
installing Streamlit.
"""
