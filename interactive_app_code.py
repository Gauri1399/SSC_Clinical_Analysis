from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import streamlit as st

# ----------------------------------------------------------------------------
# Page config & theme constants
# ----------------------------------------------------------------------------
st.set_page_config(page_title="SSc Registry Explorer", layout="wide", page_icon="🩺")

TEAL = "#0E5C56"
TEAL_SOFT = "#DCEDEA"
AMBER = "#B5702B"
ROSE = "#9C3B3B"
ROSE_SOFT = "#F5E2E2"
INK_DIM = "#5A6B6E"

DATA_DIR = Path(__file__).parent / "cleaned_datasets"

st.markdown(
    f"""
    <style>
    .stApp {{ background-color: #EEF1F0; }}
    .pill {{
        display:inline-block; padding:2px 9px; border-radius:20px;
        font-size:11px; font-weight:600; margin-left:6px;
    }}
    .pill-lc {{ background:{TEAL_SOFT}; color:{TEAL}; }}
    .pill-dc {{ background:{ROSE_SOFT}; color:{ROSE}; }}
    .subhead {{ font-family: monospace; font-size:12.5px; color:{INK_DIM}; }}
    .empty {{ color:{INK_DIM}; font-style: italic; font-size: 13px; padding: 6px 0;}}
    </style>
    """,
    unsafe_allow_html=True,
)


# ----------------------------------------------------------------------------
# Data loading 
# ----------------------------------------------------------------------------
def load_csv(filename, date_cols):
    return pd.read_csv(DATA_DIR / filename, parse_dates=date_cols)


@st.cache_data
def load_data():
    demographics = load_csv("demographics.csv", ["birth_date"])
    ssc_subtype = load_csv("ssc_subtype.csv", ["raynaud_date", "nonraynaud_date", "diagnosis_date"])
    vitals = load_csv("vitals_wide.csv", ["date_recorded"])
    mrss = load_csv("mrss.csv", ["date_recorded"])
    pft = load_csv("pft_wide.csv", ["date_recorded"])
    antibodies = load_csv("antibodies.csv", ["date_recorded"])
    lab_reports = load_csv("lab_report_wide.csv", ["date_recorded"])
    medications = load_csv("medications.csv", ["date_recorded"])
    bal = load_csv("bal.csv", ["date_recorded"])
    skin_biopsies = load_csv("skin_biopsies.csv", ["date_recorded"])
    libraries = load_csv("libraries.csv", ["date_recorded", "date_of_rna_qc", "library_prep_date"])
    return {
        "demographics": demographics,
        "ssc_subtype": ssc_subtype,
        "vitals": vitals,
        "mrss": mrss,
        "pft": pft,
        "antibodies": antibodies,
        "lab_reports": lab_reports,
        "medication": medications,
        "bal": bal,
        "skin_biopsies": skin_biopsies,
        "libraries": libraries,
    }


DATA = load_data()

COMMON_DATE_COL = "date_recorded"

TRACK_COLOR = {
    "vitals": "#2E7D8A",
    "mrss": AMBER,
    "pft": "#5B7DB1",
    "antibodies": ROSE,
    "lab_reports": "#6E5A9C",
    "medication": "#3E8E5B",
    "bal": "#8A5A3B",
    "skin_biopsies": "#B15C8A",
}
TIMELINE_TRACKS = ["vitals", "mrss", "pft", "antibodies", "lab_reports", "medication", "bal", "skin_biopsies"]
ALL_TABLES = list(DATA.keys())

def rows_for(table, sid):
    return DATA[table][DATA[table]["reg_id"] == sid]

def fmt_date(d):
    if pd.isna(d):
        return "—"
    return pd.to_datetime(d).strftime("%Y-%m-%d")


@st.cache_data
def all_subject_ids():
    ids = set()

    for df in DATA.values():
        if "reg_id" in df.columns:
            ids.update(
                df["reg_id"].dropna().astype(str).unique().tolist())

    return sorted(ids, key=lambda s: (len(s), s))


IDS = all_subject_ids()


@st.cache_data
def cohort_table():
    demo = DATA["demographics"].copy()
    sub = DATA["ssc_subtype"].copy()
    cohort = demo.merge(sub, on="reg_id", how="left")

    today = pd.Timestamp.now()
    cohort["age"] = ((today - cohort["birth_date"]).dt.days / 365.25).round(1)

    # comorbidity flags (e.g. "ILD; GERD")
    cohort["comorbidities"] = cohort["other_dx"].fillna("").apply(
        lambda s: [c.strip() for c in s.split(";") if c.strip()]
    )

    n_events = {t: DATA[t]["reg_id"].value_counts() for t in ALL_TABLES if "reg_id" in DATA[t].columns}
    cohort["events_on_file"] = cohort["reg_id"].apply(
        lambda rid: sum(1 for t, counts in n_events.items() if rid in counts.index)
    )
    return cohort


COHORT = cohort_table()
ALL_COMORBIDITIES = sorted({c for row in COHORT["comorbidities"] for c in row})

# ----------------------------------------------------------------------------
# Session state
# ----------------------------------------------------------------------------
if "current_sid" not in st.session_state:
    st.session_state.current_sid = "subject_2005" if "subject_2005" in IDS else (IDS[0] if IDS else None)

if "exclude_incomplete" not in st.session_state:
    st.session_state.exclude_incomplete = False


def _sync_exclude_incomplete():
    st.session_state.exclude_incomplete = st.session_state.exclude_incomplete_widget


NAV_SEARCH = "Search & Browse"
NAV_INSIGHTS = "Cohort Insights"
NAV_PATIENT = "Patient Details"

if "nav_page" not in st.session_state:
    st.session_state.nav_page = NAV_SEARCH

# ---------------------------------------------------------------------------
# Cohort-level navigation
# ----------------------------------------------------------------------------
st.markdown(
    "<div style='font-family:monospace;font-size:11px;letter-spacing:.08em;"
    f"color:{TEAL};text-transform:uppercase;margin-bottom:8px;'>SSc Research Registry</div>",
    unsafe_allow_html=True,
)
nav_page = st.radio(
    "View",
    [NAV_SEARCH, NAV_INSIGHTS, NAV_PATIENT],
    horizontal=True,
    label_visibility="collapsed",
    key="nav_page",
)
st.markdown("---")

def empty_note(msg):
    st.markdown(f"<div class='empty'>{msg}</div>", unsafe_allow_html=True)


def render_table(df, cols, headers, date_col, ascending=False):
    if df.empty:
        return None
    d = df.copy()
    if date_col in d.columns:
        d = d.sort_values(date_col, ascending=ascending)
        d[date_col] = d[date_col].apply(fmt_date)
    d = d[cols].rename(columns=dict(zip(cols, headers)))
    return d


def sorted_wide_table(df, date_col, display_cols, headers):
   
    if df.empty:
        return None
    d = df.copy()
    d = d.sort_values(date_col, ascending=False, na_position="last")
    d[date_col] = d[date_col].apply(fmt_date)
    d = d[[date_col] + display_cols].rename(columns=dict(zip([date_col] + display_cols, headers)))
    return d


# ---- Search & Browse -----------------------------------------------------
if nav_page == NAV_SEARCH:
    st.markdown("##### SEARCH THE COHORT")
    st.caption(
        f"{len(COHORT)} subjects with a demographics + subtype record on file "
        f"(the {len(IDS) - len(COHORT)} 'SSC_NORM_*' ids seen in the clinical-event tables "
        "are healthy controls and have no demographics/subtype record by design)."
    )

    f1, f2, f3 = st.columns(3)
    with f1:
        subtype_sel = st.multiselect("SSc subtype", sorted(COHORT["ssc_subtype"].dropna().unique()))
        gender_sel = st.multiselect("Gender", sorted(COHORT["gender"].dropna().unique()))
    with f2:
        ethnicity_sel = st.multiselect("Ethnicity", sorted(COHORT["ethnicity"].dropna().unique()))
        race_sel = st.multiselect("Race", sorted(COHORT["races"].dropna().unique()))
    with f3:
        state_sel = st.multiselect("State", sorted(COHORT["state"].dropna().unique()))
        comorbid_sel = st.multiselect("Comorbidity (from other_dx)", ALL_COMORBIDITIES)

    age_min, age_max = int(COHORT["age"].min()), int(COHORT["age"].max())
    age_range = st.slider("Age range", age_min, age_max, (age_min, age_max))
    name_search = st.text_input(
        "Search by subject ID or name",
        placeholder="e.g. subject_2005 or Taylor...",
    )
    st.checkbox(
        "Exclude NA data",
        value=st.session_state.exclude_incomplete,
        key="exclude_incomplete_widget",
        on_change=_sync_exclude_incomplete,
        help="Excludes any subject missing a value in any displayed column, including "
             "Comorbidities -- so a subject with no recorded comorbidity also gets excluded, "
             "since that field is blank for them too.",
    )

    mask = pd.Series(True, index=COHORT.index)
    if subtype_sel:
        mask &= COHORT["ssc_subtype"].isin(subtype_sel)
    if gender_sel:
        mask &= COHORT["gender"].isin(gender_sel)
    if ethnicity_sel:
        mask &= COHORT["ethnicity"].isin(ethnicity_sel)
    if race_sel:
        mask &= COHORT["races"].isin(race_sel)
    if state_sel:
        mask &= COHORT["state"].isin(state_sel)
    if comorbid_sel:
        mask &= COHORT["comorbidities"].apply(lambda cs: any(c in cs for c in comorbid_sel))
    mask &= COHORT["age"].between(*age_range)
    if name_search.strip():
        q = name_search.strip().lower()
        mask &= (
            COHORT["reg_id"].str.lower().str.contains(q)
            | COHORT["first_name"].str.lower().str.contains(q, na=False)
            | COHORT["last_name"].str.lower().str.contains(q, na=False)
        )
    if st.session_state.exclude_incomplete:
        check_cols = [
            "reg_id", "first_name", "last_name", "gender", "ethnicity", "races",
            "state", "ssc_subtype", "age", "other_dx",
        ]
        is_missing = COHORT[check_cols].isna() | (COHORT[check_cols].astype(str).apply(lambda s: s.str.strip()) == "")
        mask &= ~is_missing.any(axis=1)

    results = COHORT[mask]
    st.markdown(f"**{len(results)} of {len(COHORT)} subjects match**")

    display_cols = [
        "reg_id", "first_name", "last_name", "age", "gender", "ethnicity", "races",
        "state", "ssc_subtype", "other_dx", "events_on_file",
    ]
    display_df = results[display_cols].rename(columns={
        "reg_id": "Subject ID", "first_name": "First", "last_name": "Last", "age": "Age",
        "gender": "Gender", "ethnicity": "Ethnicity", "races": "Race", "state": "State",
        "ssc_subtype": "Subtype", "other_dx": "Comorbidities", "events_on_file": "Data sources on file",
    }).sort_values("Subject ID")

    st.dataframe(display_df, use_container_width=True, hide_index=True)


# ---- Cohort Insights ------------------------------------------------------
elif nav_page == NAV_INSIGHTS:
    st.markdown("##### COHORT INSIGHTS")
    st.caption(f"Across all {len(COHORT)} subjects with a demographics + subtype record on file.")

    g1, g2 = st.columns(2)
    with g1:
        race_counts = COHORT["races"].value_counts().reset_index()
        race_counts.columns = ["Race", "Count"]
        fig = px.bar(race_counts, x="Race", y="Count", title="Race distribution")
        fig.update_traces(marker_color=TEAL)
        fig.update_layout(
            height=340, plot_bgcolor="white", margin=dict(l=10, r=10, t=40, b=10),
            xaxis=dict(title=""), yaxis=dict(gridcolor="#E4E9E7", title=""),
        )
        st.plotly_chart(fig, use_container_width=True)

    with g2:
        fig = px.histogram(COHORT, x="age", nbins=15, title="Age distribution")
        fig.update_traces(marker_color="#5B7DB1")
        fig.update_layout(
            height=340, plot_bgcolor="white", margin=dict(l=10, r=10, t=40, b=10),
            xaxis=dict(title="Age (years)"), yaxis=dict(gridcolor="#E4E9E7", title=""),
        )
        st.plotly_chart(fig, use_container_width=True)

    g3, g4 = st.columns(2)
    with g3:
        gender_pct = (
            COHORT.dropna(subset=["ssc_subtype", "gender"])
            .groupby(["ssc_subtype", "gender"])
            .size()
            .reset_index(name="count")
        )
        gender_pct["pct"] = gender_pct.groupby("ssc_subtype")["count"].transform(lambda x: x / x.sum() * 100)
        fig = px.bar(
            gender_pct, x="ssc_subtype", y="pct", color="gender", barmode="group",
            title="Gender distribution within subtype", text=gender_pct["pct"].round(1).astype(str) + "%",
            color_discrete_map={"Female": TEAL, "Male": AMBER},
        )
        fig.update_layout(
            height=340, plot_bgcolor="white", margin=dict(l=10, r=10, t=40, b=10),
            xaxis=dict(title=""), yaxis=dict(gridcolor="#E4E9E7", title="% of patients", range=[0, 100]),
            legend_title="",
        )
        st.plotly_chart(fig, use_container_width=True)

    with g4:
        corr_cols = [c for c in ["fev1", "fvc", "dlco_sb"] if c in DATA["pft"].columns]
        corr_data = DATA["pft"][corr_cols].dropna()
        if len(corr_data) < 3:
            empty_note("Not enough PFT visits on file to compute a correlation.")
        else:
            corr = corr_data.corr().round(2)
            fig = px.imshow(
                corr, text_auto=True, color_continuous_scale=[[0, ROSE], [0.5, "#FFFFFF"], [1, TEAL]],
                zmin=-1, zmax=1, title="PFT measure correlation",
            )
            fig.update_layout(height=340, margin=dict(l=10, r=10, t=40, b=10))
            st.plotly_chart(fig, use_container_width=True)


elif nav_page == NAV_PATIENT:
    with st.sidebar:
        st.markdown(
            "<div style='font-family:monospace;font-size:11px;letter-spacing:.08em;"
            f"color:{TEAL};text-transform:uppercase;'>SSc Research Registry</div>"
            "<h2 style='margin:4px 0 14px;'>Patient Explorer</h2>",
            unsafe_allow_html=True,
        )
        search = st.text_input("Filter subject_id...", label_visibility="collapsed", placeholder="Filter subject_id...")
        filtered_ids = [i for i in IDS if search.strip().lower() in i.lower()] if search else IDS

        st.caption(f"{len(filtered_ids)} of {len(IDS)} subjects match")

        default_idx = filtered_ids.index(st.session_state.current_sid) if st.session_state.current_sid in filtered_ids else 0
        if filtered_ids:
            chosen = st.selectbox(
                "Subject",
                filtered_ids,
                index=default_idx,
                label_visibility="collapsed",
            )
            st.session_state.current_sid = chosen
        else:
            st.warning("No subjects match that filter.")

        if st.session_state.current_sid:
            present = [t for t in ALL_TABLES if not rows_for(t, st.session_state.current_sid).empty]
            st.markdown("**Data sources on file:**")
            for t in ALL_TABLES:
                has = t in present
                dot = "🟢" if has else "🟠"
                st.caption(f"{dot} {t.replace('_', ' ')}")

        st.markdown("---")

    sid = st.session_state.current_sid

    if sid is None:
        st.warning("No subjects found in the data.")
        st.stop()

    # ----------------------------------------------------------------------------
    # Header
    # ----------------------------------------------------------------------------
    demo_df = rows_for("demographics", sid)
    demo = demo_df.iloc[0].to_dict() if not demo_df.empty else None
    n_sources = sum(1 for t in ALL_TABLES if not rows_for(t, sid).empty)


    if demo is None:
        st.warning(
            "⚠ No demographics / subtype record for this subject_id. IDs prefixed `SSC_NORM_*` "
            "are healthy controls and are expected to have clinical-event data (vitals, PFT, labs, "
            "etc.) but no demographics/subtype record — that's by design, not a linkage error. "
            "If this ID is prefixed `subject_*` instead, that would indicate a genuine registry gap."
        )


    TABS = ["Overview", "Vitals", "MRSS", "Clinical History", "Labs", "BAL", "Skin Biopsies"]
    tab_overview, tab_vitals, tab_mrss, tab_treatment, tab_labs, tab_bal, tab_biopsy = st.tabs(TABS)

    # ---- Overview -----------------------------------------------------------
    with tab_overview:

        subtype_df = rows_for("ssc_subtype", sid)
        subtype = subtype_df.iloc[0].to_dict() if not subtype_df.empty else None

        c1, c2 = st.columns(2)

        # Demographics

        with c1:
            st.markdown("##### DEMOGRAPHICS")

            if demo:
                demographic_info = {
                    "Name": f"{demo.get('first_name', '')} {demo.get('last_name', '')}",
                    "DOB": fmt_date(demo.get("birth_date")),
                    "Gender": demo.get("gender", "—"),
                    "Race / Eth.": f"{demo.get('races', '—')} · {demo.get('ethnicity', '—')}",
                    "State": demo.get("state", "—"),
                    "Height / Wt": f"{demo.get('height', '—')} in · {demo.get('weight', '—')} lb",
                    "Diagnosis": demo.get("diagnosis", "—"),
                }

                demographic_df = pd.DataFrame(
                    demographic_info.items(),
                    columns=["Feature", "Value"]
                )

                st.dataframe(
                    demographic_df,
                    hide_index=True,
                    use_container_width=True
                )

            else:
                empty_note("No demographic record linked to this subject_id.")


        # Disease Course
        with c2:
            st.markdown("##### DISEASE COURSE")

            if subtype:

                disease_info = {
                    "Subtype": subtype.get("ssc_subtype", "—"),
                    "Other Dx": subtype.get("other_dx") or "—",
                    "Raynaud's onset": fmt_date(subtype.get("raynaud_date")),
                    "First non-Raynaud sx": (
                        f"{fmt_date(subtype.get('nonraynaud_date'))} "
                        f"({subtype.get('nonraynaud_sx') or '—'})"
                    ),
                    "SSc diagnosis": fmt_date(subtype.get("diagnosis_date")),
                }

                disease_df = pd.DataFrame(
                    disease_info.items(),
                    columns=["Feature", "Value"]
                )

                st.dataframe(
                    disease_df,
                    hide_index=True,
                    use_container_width=True
                )

            else:
                empty_note("No subtype record linked to this subject_id.")

        st.markdown("##### COMBINED EVENT TIMELINE")
        timeline_rows = []
        for t in TIMELINE_TRACKS:
            df = rows_for(t, sid)
            dc = COMMON_DATE_COL
            for d in df[dc].dropna():
                timeline_rows.append({"track": t.replace("_", " "), "date": d})

        if not timeline_rows:
            empty_note("No dated clinical events for this subject.")
            for t in TIMELINE_TRACKS:
                df = rows_for(t, sid)
                note = "No records on file" if df.empty else "No dated events on file"
                st.caption(f"**{t.replace('_', ' ')}**: {note}")
        else:
            tdf = pd.DataFrame(timeline_rows)
            fig = go.Figure()
            for t in TIMELINE_TRACKS:
                sub = tdf[tdf["track"] == t.replace("_", " ")]
                if sub.empty:
                    continue
                fig.add_trace(
                    go.Scatter(
                        x=sub["date"],
                        y=sub["track"],
                        mode="markers",
                        marker=dict(size=10, color=TRACK_COLOR[t]),
                        name=t.replace("_", " "),
                        hovertemplate="%{y} · %{x|%Y-%m-%d}<extra></extra>",
                    )
                )
            fig.update_layout(
                height=340,
                showlegend=False,
                margin=dict(l=10, r=10, t=10, b=10),
                plot_bgcolor="white",
                yaxis=dict(categoryorder="array", categoryarray=[t.replace("_", " ") for t in TIMELINE_TRACKS][::-1]),
                xaxis=dict(gridcolor="#E4E9E7"),
            )
            st.plotly_chart(fig, use_container_width=True)

    # ---- Vitals (already wide: bmi, bp_diastolic, bp_systolic, pulse, weight_in_pound) ----
    with tab_vitals:
        st.markdown("##### VITALS")
        vdf = rows_for("vitals", sid)
        table = sorted_wide_table(
            vdf, "date_recorded",
            ["bmi", "bp_systolic", "bp_diastolic", "pulse", "weight_in_pound"],
            ["Date", "BMI", "BP Systolic", "BP Diastolic", "Pulse", "Weight (lb)"],
        )
        if table is None:
            empty_note("No vitals recorded.")
        else:
            st.dataframe(table, use_container_width=True, hide_index=True)

    # ---- MRSS -------------------------------------------------------------
    with tab_mrss:
        st.markdown("##### MODIFIED RODNAN SKIN SCORE TREND")
        mdf_all = rows_for("mrss", sid).sort_values("date_recorded", na_position="last")
        mdf_dated = mdf_all.dropna(subset=["date_recorded"])
        if mdf_all.empty:
            empty_note("No MRSS recorded.")
        else:
            if mdf_dated.empty:
                empty_note("No dated MRSS assessments to plot (all records below are missing a date).")
            else:
                fig = px.line(
                    mdf_dated, x="date_recorded", y=mdf_dated["mrss_score"].astype(float),
                    markers=True, labels={"y": "score (0–51)", "date_recorded": ""},
                )
                fig.update_traces(line_color=AMBER, marker=dict(color=AMBER, size=8))
                fig.update_layout(height=300, plot_bgcolor="white", margin=dict(l=10, r=10, t=10, b=10),
                                   xaxis=dict(gridcolor="#E4E9E7"), yaxis=dict(gridcolor="#E4E9E7", title="score (0–51)"))
                st.plotly_chart(fig, use_container_width=True)

            table = render_table(mdf_all, ["date_recorded", "mrss_score", "entry_user_name"], ["Date", "MRSS", "Assessor"], "date_recorded")
            st.dataframe(table, use_container_width=True, hide_index=True)

    # ---- Clinical Events (Treatment) ------------------------------------------
    with tab_treatment:
        st.markdown("##### PULMONARY FUNCTION")
        pft_df = rows_for("pft", sid)
        table = sorted_wide_table(
            pft_df, "date_recorded", ["fvc", "fev1", "dlco_sb"], ["Date", "FVC", "FEV1", "DLCO_SB"],
        )
        if table is None:
            empty_note("No PFT recorded.")
        else:
            st.dataframe(table, use_container_width=True, hide_index=True)

        c1, c2 = st.columns(2)
        with c1:
            st.markdown("##### MEDICATIONS ON FILE")
            med_df = rows_for("medication", sid)
            table = render_table(med_df, ["date_recorded", "medication", "dose"], ["Date", "Medication", "Dose"], "date_recorded")
            if table is None:
                empty_note("No medications recorded.")
            else:
                st.dataframe(table, use_container_width=True, hide_index=True)

        with c2:
            st.markdown("##### ANTIBODY RESULTS")
            ab_df = rows_for("antibodies", sid)
            if ab_df.empty:
                empty_note("No antibody results recorded.")
            else:
                d = ab_df.sort_values("date_recorded", ascending=False).copy()
                d["date_recorded"] = d["date_recorded"].apply(fmt_date)

                def style_val(v):
                    color = ROSE if v == "positive" else (AMBER if v == "borderline" else INK_DIM)
                    return f"color: {color}; font-weight: 600;"

                styled = d[["date_recorded", "test", "value"]].rename(
                    columns={"date_recorded": "Date", "test": "Test", "value": "Result"}
                )
                st.dataframe(
                    styled.style.map(style_val, subset=["Result"]),
                    use_container_width=True,
                    hide_index=True,
                )

    # ---- Labs ----
    with tab_labs:
        lab_df = rows_for("lab_reports", sid)
        if lab_df.empty:
            empty_note("No labs recorded.")
        else:
            component_cols = [c for c in lab_df.columns if c not in ("reg_id", "date_recorded")]

            st.markdown("##### LAB TREND")
            component = st.selectbox("Measurement:", component_cols, key="lab_component")
            rs = lab_df.dropna(subset=["date_recorded", component]).sort_values("date_recorded")
            if rs.empty:
                empty_note(f"No recorded values for {component}.")
            else:
                fig = px.line(rs, x="date_recorded", y=component, markers=True, labels={component: component, "date_recorded": ""})
                fig.update_traces(line_color="#6E5A9C", marker=dict(color="#6E5A9C", size=8))
                fig.update_layout(height=300, plot_bgcolor="white", margin=dict(l=10, r=10, t=10, b=10),
                                   xaxis=dict(gridcolor="#E4E9E7"), yaxis=dict(gridcolor="#E4E9E7", title=component))
                st.plotly_chart(fig, use_container_width=True)

            st.markdown("##### FULL PANEL BY DATE")
            dates = sorted(lab_df["date_recorded"].dropna().unique().tolist(), reverse=True)
            if dates:
                date_labels = {fmt_date(d): d for d in dates}
                chosen_label = st.selectbox("Draw date:", list(date_labels.keys()), key="lab_date")
                chosen_date = date_labels[chosen_label]
                row = lab_df[lab_df["date_recorded"] == chosen_date][component_cols].iloc[0]
                panel = row.dropna().reset_index()
                panel.columns = ["Component", "Value"]
                st.dataframe(panel, use_container_width=True, hide_index=True)
            else:
                empty_note("No dated lab draws recorded.")

    # ---- BAL ----------------------------------------------------------------
    with tab_bal:
        st.markdown("##### BRONCHOALVEOLAR LAVAGE PROCEDURES")
        bal_df = rows_for("bal", sid).sort_values("date_recorded")
        if bal_df.empty:
            empty_note("No BAL procedures recorded.")
        else:
            d = bal_df.copy()
            d["date_recorded"] = d["date_recorded"].apply(fmt_date)
            d["Recovery %"] = (d["volume_recovered_ml"] / d["volume_instilled_ml"] * 100).round(0)
            d["Recovery %"] = d["Recovery %"].apply(lambda x: f"{x:.0f}%" if pd.notna(x) else "—")
            d["bal_comment"] = d["bal_comment"].fillna("—")
            table = d[
                ["date_recorded", "procedure_site", "volume_instilled_ml", "volume_recovered_ml", "Recovery %", "bal_comment"]
            ].rename(
                columns={
                    "date_recorded": "Date",
                    "procedure_site": "Site",
                    "volume_instilled_ml": "Instilled (mL)",
                    "volume_recovered_ml": "Recovered (mL)",
                    "bal_comment": "Comment",
                }
            )
            st.dataframe(table, use_container_width=True, hide_index=True)

    # ---- Skin Biopsies ----------------------------------------------------
    with tab_biopsy:
        st.markdown("##### SKIN BIOPSIES")
        bx_df = rows_for("skin_biopsies", sid).sort_values("date_recorded", ascending=False)
        if bx_df.empty:
            empty_note("No skin biopsies recorded.")
        else:
            d = bx_df.copy()
            d["date_recorded"] = d["date_recorded"].apply(fmt_date)
            table = d[
                ["date_recorded", "biopsy_site", "clinical_indication", "entry_user_name", "specimen_accession", "image_file_path"]
            ].rename(
                columns={
                    "date_recorded": "Date",
                    "biopsy_site": "Site",
                    "clinical_indication": "Clinical Indication",
                    "entry_user_name": "Performed By",
                    "specimen_accession": "Specimen ID",
                    "image_file_path": "Image File",
                }
            )
            st.dataframe(table, use_container_width=True, hide_index=True)
