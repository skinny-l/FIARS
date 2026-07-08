"""
dashboard/streamlit_app.py — read-only analytics UI over fiars.db.

Optional (Phase 5). Doesn't touch the database — pure reads via
fiars.analytics. Separate process from the Flask app (server.py); both can
run against the same fiars.db at once since this never writes.

    pip install -r requirements-dashboard.txt
    streamlit run dashboard/streamlit_app.py
    (or double-click start_dashboard.bat on Windows)
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st

from fiars.analytics import metrics, queries
from fiars.config import load_config

st.set_page_config(page_title="FIARS Analytics", layout="wide")

DB_PATH = load_config().get("db_path", "fiars.db")

if not os.path.exists(DB_PATH):
    st.error(f"No database found at `{DB_PATH}`. Start the FIARS Flask app at least once first.")
    st.stop()

PAGE = st.sidebar.radio(
    "Page",
    ["Overview", "Faults & Causes", "Trends", "Resolution Effectiveness",
     "Confidence Distribution", "Engineer Contribution"],
)
st.sidebar.caption(f"Reading: `{DB_PATH}` (read-only)")


def _bar(data: list[dict], label_key: str, value_key: str, title: str):
    if not data:
        st.info("Not enough data yet.")
        return
    st.bar_chart({d[label_key]: d[value_key] for d in data})
    st.caption(title)


# ── 1. Overview ───────────────────────────────────────────────────────────
if PAGE == "Overview":
    st.title("Overview")
    ov = metrics.overview(DB_PATH)
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total cases", ov["total_cases"])
    c2.metric("Cases this month", ov["cases_this_month"])
    c3.metric("MTTR (min)", ov["mttr_minutes"] if ov["mttr_minutes"] is not None else "—",
              help=f"based on {ov['mttr_n']} cases with a logged resolution time")
    c4.metric("Recurrence rate", f"{ov['recurrence_rate']:.1%}",
              help=f"based on {ov['recurrence_n']} cases")

# ── 2. Faults & Causes ────────────────────────────────────────────────────
elif PAGE == "Faults & Causes":
    st.title("Faults & Causes")
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Top root causes")
        _bar(queries.top_labels(DB_PATH, "root_cause", limit=10), "label", "n",
             "Count of confirmed cases per root cause")
    with col2:
        st.subheader("Most-replaced components")
        _bar(queries.top_labels(DB_PATH, "parts", limit=10), "label", "n",
             "Count of cases per affected part/component")

# ── 3. Trends ─────────────────────────────────────────────────────────────
elif PAGE == "Trends":
    st.title("Trends")
    st.caption("Bucketed by when each case was logged in FIARS (created_at), "
               "not the free-text ticket date field.")
    st.subheader("Monthly case volume")
    _bar(queries.monthly_volume(DB_PATH), "month", "n", "Cases logged per month")

    st.subheader("MTTR over time")
    _bar(queries.mttr_by_month(DB_PATH), "month", "mttr_minutes",
         "Average resolution time (minutes) per month")

    st.subheader("Recurrence rate over time")
    trend = queries.recurrence_trend_by_month(DB_PATH)
    if trend:
        st.line_chart({d["month"]: d["recurrence_rate"] for d in trend})
    else:
        st.info("Not enough data yet.")

# ── 4. Resolution Effectiveness ───────────────────────────────────────────
elif PAGE == "Resolution Effectiveness":
    st.title("Resolution Effectiveness")
    st.caption("Which fixes actually hold, vs. which come back as repeat faults. "
                "Resolutions with fewer than 2 recorded cases are hidden — too little "
                "evidence to call a rate meaningful.")
    data = queries.recurrence_by_resolution(DB_PATH, limit=15, min_n=2)
    if not data:
        st.info("Need at least 2 cases sharing the same resolution text to show this view.")
    else:
        for row in sorted(data, key=lambda r: r["recurrence_rate"]):
            success_rate = 1 - row["recurrence_rate"]
            st.progress(success_rate, text=f"{row['label']}  —  "
                        f"{success_rate:.0%} held (n={row['n']})")

# ── 5. Confidence Distribution ────────────────────────────────────────────
elif PAGE == "Confidence Distribution":
    st.title("Confidence Distribution")
    st.caption("Calibration check: for a sample of real cases, each is hidden from its "
               "own retrieval, then the recommendation engine's top confidence for the "
               "correct-answer slot is recorded. Computed live — may take a few seconds "
               "on large histories.")
    n_total = queries.total_cases(DB_PATH)
    sample_size = st.slider("Sample size", min_value=10,
                             max_value=max(10, min(n_total, 500)),
                             value=min(200, max(10, n_total)))
    if st.button("Run calibration check"):
        with st.spinner("Running leave-one-out sampling..."):
            result = metrics.confidence_distribution(DB_PATH, sample_size=sample_size)
        st.write(f"Sampled {result['n_sampled']} of {result['n_total']} cases.")
        if result["confidences"]:
            st.bar_chart(result["confidences"])
        else:
            st.info("No cases with fault text to sample.")

# ── 6. Engineer Contribution ──────────────────────────────────────────────
elif PAGE == "Engineer Contribution":
    st.title("Engineer Contribution")
    st.caption("Cases closed per engineer — for visibility and credit, not ranking.")
    _bar(queries.engineer_contribution(DB_PATH), "label", "n", "Cases closed")
