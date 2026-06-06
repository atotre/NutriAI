"""
app.py — NutriAI: Automated Diet Plan Builder
Streamlit Dashboard

Launch:
    streamlit run app.py
"""

import sys
import os
import time

sys.path.insert(0, os.path.dirname(__file__))

import streamlit as st
# 🔍 HEALTHIFYME STYLING INJECTION
st.markdown("""
    <style>
    /* Make metric cards look like modern fitness tiles */
    [data-testid="stMetricValue"] {
        font-size: 1.8rem !important;
        font-weight: 700 !important;
        color: #00c49a !important;
    }
    [data-testid="stMetricLabel"] {
        font-size: 0.9rem !important;
        text-transform: uppercase !important;
        letter-spacing: 0.5px !important;
        color: #64748b !important;
    }
    /* Style the sidebar to look premium and distinct */
    [data-testid="stSidebar"] {
        border-right: 1px solid #e2e8f0;
    }
    /* Soften the edges of buttons and input boxes */
    div.stButton > button {
        border-radius: 8px !important;
    }
    div[data-baseweb="select"] {
        border-radius: 8px !important;
    }
    </style>
""", unsafe_allow_html=True)

import pandas as pd
import numpy as np
import os
import sys

# 🚀 Tell Streamlit Cloud to look inside this folder for pipeline.py, filters.py, etc.
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

from pipeline import load_meals, get_db_stats, get_db_path
from filters import (
    FilterEngine,
    apply_persona_hard_constraints,
    apply_cultural_filters,  # <-- ADD THIS LINE HERE
    build_explain_report,
    summarize_exclusions,
    CONDITION_DISPLAY,
    ALLERGY_DISPLAY,
)
from recommender import (
    generate_plan,
    daily_totals,
    rda_coverage,
    count_seafood_meals,
    DAYS,
    MEAL_TYPES,
    NUTRIENT_COLS,
    MACRO_NUTRIENTS,
    MICRO_NUTRIENTS,
    NUTRIENT_UNITS,
    NUTRIENT_DISPLAY,
)

# ─────────────────────────────────────────────────────────────────────────────
# Page config
# ─────────────────────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="NutriAI — Diet Plan Builder",
    page_icon="🥗",
    layout="wide",
    initial_sidebar_state="expanded",
)

# 👇 YOUR NEW LIGHT MODE STYLE GOES RIGHT HERE 👇
st.markdown("""
<style>
/* Calendar meal cards - HealthifyMe Light Mode style */
.meal-card {
    background: #ffffff;
    border-radius: 10px;
    padding: 12px;
    margin-bottom: 8px;
    border: 1px solid #e2e8f0;
    border-left: 4px solid #00c49a;
    box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    font-size: 0.8rem;
    line-height: 1.4;
}
.meal-card b { color: #0f172a; }
.meal-type-label {
    font-size: 0.7rem;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    color: #64748b;
    margin-top: 5px;
    margin-bottom: 3px;
    font-weight: 600;
}
.day-header {
    font-weight: 700;
    color: #0f172a;
    font-size: 0.9rem;
    border-bottom: 2px solid #e2e8f0;
    padding-bottom: 4px;
    margin-bottom: 8px;
    text-align: center;
}
/* Compliance badges */
.badge-ok   { background:#d1fae5; color:#065f46; border-radius:6px; padding:2px 6px; font-size:0.7rem; font-weight:700; }
.badge-fail { background:#fee2e2; color:#991b1b; border-radius:6px; padding:2px 6px; font-size:0.7rem; font-weight:700; }
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# Test persona definitions
# ─────────────────────────────────────────────────────────────────────────────

PERSONAS = {
    "Priya": {
        "name": "Priya", "age": 34, "sex": "Female",
        "allergies": ["dairy"],
        "conditions": ["ibs"],
        "is_vegetarian": True, "is_vegan": False, "is_pescatarian": False,
        "description": "34 F · Vegetarian · Lactose Intolerant · IBS",
        "compliance_notes": [
            "Iron ≥ 80% RDA/day",
            "Zero high-FODMAP (onion/garlic/wheat)",
            "Zero dairy",
            "Meatless",
        ],
    },
    "Ravi": {
        "name": "Ravi", "age": 52, "sex": "Male",
        "allergies": ["gluten"],
        "conditions": ["gerd"],
        "is_vegetarian": False, "is_vegan": False, "is_pescatarian": False,
        "description": "52 M · Non-Veg · Gluten-Free · GERD",
        "compliance_notes": [
            "Vitamin B12 ≥ 80% RDA/day",
            "Zero acid triggers (citrus, tomato, fried, spicy)",
            "Zero gluten",
            "Diversity Score ≥ 0.7",
        ],
    },
    "Mei": {
        "name": "Mei", "age": 28, "sex": "Female",
        "allergies": ["tree_nuts"],
        "conditions": ["diabetes"],
        "is_vegetarian": True, "is_vegan": True, "is_pescatarian": False,
        "description": "28 F · Vegan · Tree-Nut Allergy · Type 2 Diabetes",
        "compliance_notes": [
            "All meals GI ≤ 55",
            "Zero animal products",
            "Zero tree nuts",
            "Fiber ≥ 25 g/day",
        ],
    },
    "James": {
        "name": "James", "age": 45, "sex": "Male",
        "allergies": ["soy"],
        "conditions": ["hypertension"],
        "is_vegetarian": False, "is_vegan": False, "is_pescatarian": True,
        "description": "45 M · Pescatarian · Soy Allergy · Hypertension",
        "compliance_notes": [
            "DASH: Sodium ≤ 1,500 mg/day strictly",
            "Zero soy",
            "≥ 3 seafood meals in the week",
            "Potassium ≥ 80% RDA/day",
        ],
    },
}

ALL_ALLERGIES   = ["gluten", "dairy", "tree_nuts", "shellfish", "soy", "eggs", "fish", "peanuts"]
ALL_CONDITIONS  = ["ibs", "gerd", "diabetes", "hypertension", "celiac"]

MEAL_ICONS  = {"Breakfast": "☀️", "Lunch": "🌤️", "Dinner": "🌙"}
MEAL_COLORS = {"Breakfast": "#f9e2af", "Lunch": "#89dceb", "Dinner": "#cba6f7"}

BELOW_THRESHOLD = 0.80   # 80% RDA flag threshold

# ─────────────────────────────────────────────────────────────────────────────
# Session state
# ─────────────────────────────────────────────────────────────────────────────

for _key, _default in [
    ("profile", None), ("plan", None), ("diversity", None),
    ("daily_rda", None), ("excl_log", {}), ("gen_time", None),
    ("compliance", {}), ("persona_name", None),
]:
    if _key not in st.session_state:
        st.session_state[_key] = _default

# ─────────────────────────────────────────────────────────────────────────────
# Core pipeline
# ─────────────────────────────────────────────────────────────────────────────
import random

HEALTH_FACTS = [
    "💡 Clinical Tip: Potassium helps regulate fluid balance and lowers blood pressure by easing tension in blood vessel walls.",
    "💡 Did you know? Vitamin D is fat-soluble, meaning it requires dietary fats to be optimally absorbed by the body.",
    "💡 Nutrition Fact: Dietary fiber slows glucose absorption, preventing insulin spikes—crucial for Type 2 Diabetes management.",
    "💡 Bioavailability Tip: Pairing iron-rich plant foods with Vitamin C drastically increases your body's iron absorption rate.",
    "💡 Cardio Note: The DASH diet limits sodium intake to 1,500mg daily to significantly reduce clinical hypertension."
]

@st.cache_data(show_spinner=False) # Turn off default spinner text
def cached_load_meals() -> pd.DataFrame:
    # Pick a random fact to show while loading
    with st.spinner(random.choice(HEALTH_FACTS)):
        return load_meals()
    
@st.cache_data(show_spinner="Loading meal database…", ttl=3600)
def cached_load_meals() -> pd.DataFrame:
    return load_meals()


@st.cache_data(show_spinner=False, ttl=600)
def cached_db_stats() -> dict:
    return get_db_stats()


def run_pipeline(profile: dict) -> None:
    t0 = time.perf_counter()

    df = cached_load_meals()

    # Ensure profile always safely contains a default religious parameter key
    if "religious_constraint" not in profile:
        profile["religious_constraint"] = "None"
    
    # General clinical filter
    engine     = FilterEngine(profile)
    filtered_df, excl_log = engine.apply(df)

    filtered_df = apply_cultural_filters(filtered_df, profile.get("religious_constraint", "None"))

    # Persona hard constraints (second-pass strict filter)
    pname = profile.get("name")
    if pname in PERSONAS:
        filtered_df = apply_persona_hard_constraints(filtered_df, pname)

    # Recommendation + diversity engine
    plan, diversity_score, daily_rda, compliance = generate_plan(
        filtered_df,
        age=profile["age"],
        sex=profile["sex"],
        persona_name=pname if pname in PERSONAS else None,
    )

    elapsed = time.perf_counter() - t0

    st.session_state.profile      = profile
    st.session_state.plan         = plan
    st.session_state.diversity    = diversity_score
    st.session_state.daily_rda    = daily_rda
    st.session_state.excl_log     = excl_log
    st.session_state.gen_time     = elapsed
    st.session_state.compliance   = compliance
    st.session_state.persona_name = pname

# ─────────────────────────────────────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown("# 🟩 **NutriAI**")
    st.caption("✨ Personal Wellness & Diet Ecosystem — BAX-423")
    
    # DB status
    try:
        stats = cached_db_stats()
        st.success(f"Database: **{stats['total_meals']:,}** meals loaded")
        st.caption(f"Path: `{get_db_path()}`")
    except Exception as e:
        st.error(f"Database error: {e}")
        st.info("Run: `python data/build_database.py`")
        st.stop()

    st.divider()
    st.subheader("📋 Clinical Test Cases (Grading)")

    p_cols = st.columns(2)
    for i, (pname, pdata) in enumerate(PERSONAS.items()):
        with p_cols[i % 2]:
            if st.button(pname, use_container_width=True, key=f"persona_{pname}"):
                run_pipeline(pdata)
                st.rerun()

    with st.expander("Persona Details", expanded=False):
        for pdata in PERSONAS.values():
            st.markdown(f"**{pdata['name']}** — {pdata['description']}")
            for note in pdata["compliance_notes"]:
                st.markdown(f"   - {note}")

    st.divider()
    st.subheader("Custom Profile")

    with st.form("custom_profile"):
        m_name = st.text_input("Patient Name", value="Custom Patient")

        col_a, col_b = st.columns(2)
        with col_a:
            m_age  = st.number_input("Age", 18, 100, 30, 1)
        with col_b:
            m_sex  = st.selectbox("Sex", ["Male", "Female"])

        m_allergies  = st.multiselect(
            "Allergies",
            options=["None"] + ALL_ALLERGIES,
            default=["None"],
            format_func=lambda x: ALLERGY_DISPLAY.get(x, x.replace("_", " ").title()),
        )
        m_conditions = st.multiselect(
            "Conditions",
            options=["None"] + ALL_CONDITIONS,
            default=["None"],
            format_func=lambda x: CONDITION_DISPLAY.get(x, x.title()),
        )
        m_diet = st.selectbox(
            "Diet", ["Omnivore", "Pescatarian", "Vegetarian", "Vegan"]
        )
        
        st.markdown("### 🗺️ Sociocultural Parameters")
        religious_constraint = st.selectbox(
            "Religious or Cultural Constraints:",
            options=["None", "Halal", "Kosher", "Hindu Vegetarian", "Jain (Strict Vegetarian)"]
        )

        if st.form_submit_button("Generate Plan", type="primary", use_container_width=True):
            processed_allergies = [a for a in m_allergies if a != "None"]
            processed_conditions = [c for c in m_conditions if c != "None"]

            run_pipeline({
                "name": m_name,
                "age": int(m_age),
                "sex": m_sex,
                "allergies": processed_allergies,
                "conditions": processed_conditions,
                "is_vegan": m_diet == "Vegan",
                "is_vegetarian": m_diet in ("Vegetarian", "Vegan"),
                "is_pescatarian": m_diet == "Pescatarian",
                "religious_constraint": religious_constraint,
            })
            st.rerun()

    # Generation timer (Aligned with exactly 4 spaces to sit inside the sidebar, but outside the custom_profile form)
    if st.session_state.gen_time is not None:
        st.divider()
        t = st.session_state.gen_time
        colour = "#a6e3a1" if t < 60 else "#f38ba8"
        status = "✓ sub-60 s" if t < 60 else "⚠ exceeded target"
        st.markdown(
            f"<div style='text-align:center;padding:6px'>"
            f"⏱ <span style='color:{colour};font-weight:700'>{t:.2f} s</span>"
            f" &nbsp;·&nbsp; {status}</div>",
            unsafe_allow_html=True,
        )


# ─────────────────────────────────────────────────────────────────────────────
# MAIN PANEL — guard until a plan is generated
# ─────────────────────────────────────────────────────────────────────────────

st.title("NutriAI — Automated Diet Plan Builder")

if st.session_state.plan is None:
    st.info(
        "Select a **persona** from the sidebar or fill in the **Custom Profile** form, "
        "then click **Generate Plan**."
    )

    with st.expander("Database Summary", expanded=True):
        try:
            stats = cached_db_stats()
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Total Meals",       f"{stats['total_meals']:,}")
            c2.metric("Breakfasts",         f"{stats.get('count_breakfast',0):,}")
            c3.metric("Lunches",            f"{stats.get('count_lunch',0):,}")
            c4.metric("Dinners",            f"{stats.get('count_dinner',0):,}")
            c1.metric("Low-FODMAP Meals",   f"{stats.get('low_fodmap',0):,}")
            c2.metric("GERD-Safe Meals",    f"{stats.get('gerd_safe',0):,}")
            c3.metric("Diabetic-Friendly",  f"{stats.get('diabetic_ok',0):,}")
            c4.metric("DASH-Compliant",     f"{stats.get('dash_compliant',0):,}")
        except Exception:
            pass
    st.stop()

plan        = st.session_state.plan
daily_rda   = st.session_state.daily_rda
profile     = st.session_state.profile
excl_log    = st.session_state.excl_log
diversity   = st.session_state.diversity
compliance  = st.session_state.compliance
pname       = st.session_state.persona_name


# ─────────────────────────────────────────────────────────────────────────────
# Summary strip
# ─────────────────────────────────────────────────────────────────────────────

allergy_str    = ", ".join(ALLERGY_DISPLAY.get(a, a) for a in profile.get("allergies", [])) or "None"
condition_str  = ", ".join(CONDITION_DISPLAY.get(c, c) for c in profile.get("conditions", [])) or "None"
seafood_count  = count_seafood_meals(plan)

cm1, cm2, cm3, cm4, cm5, cm6 = st.columns(6)
cm1.metric("Profile",       f"{profile.get('name','?')} ({profile.get('age','?')}{profile.get('sex','?')[0]})")
cm2.metric("Conditions",    condition_str[:22] + ("…" if len(condition_str) > 22 else ""))
cm3.metric("Allergies",     allergy_str[:22]   + ("…" if len(allergy_str)   > 22 else ""))
cm4.metric("Diversity (D)", f"{diversity:.4f}  ({int(diversity*21)}/21)")
cm5.metric("Excluded",      f"{len(excl_log):,} meals")
cm6.metric("Seafood Meals", f"{seafood_count}/21")

st.divider()

# ─────────────────────────────────────────────────────────────────────────────
# Persona compliance banner (if applicable)
# ─────────────────────────────────────────────────────────────────────────────

if pname in PERSONAS and compliance:
    violations_total = sum(len(v["violations"]) for v in compliance.values())
    days_passed      = sum(1 for v in compliance.values() if v["pass"])

    banner_color = "#1e3a2f" if violations_total == 0 else "#45273a"
    banner_text  = (
        f"✓ All 7 days meet {pname}'s clinical compliance requirements."
        if violations_total == 0
        else f"⚠ {violations_total} compliance violations across {7 - days_passed} day(s) — see Nutrient Analytics tab."
    )
    st.markdown(
        f"<div style='background:{banner_color};border-radius:8px;padding:8px 16px;"
        f"font-size:0.85rem;margin-bottom:12px'>{banner_text}</div>",
        unsafe_allow_html=True,
    )

    # Ravi diversity compliance note
    if pname == "Ravi" and diversity < 0.7:
        st.warning(
            f"Ravi compliance: Diversity Score {diversity:.4f} is below the required 0.7 threshold. "
            "Broaden GERD-safe gluten-free options to improve variety."
        )

    # James seafood count note
    if pname == "James" and seafood_count < 3:
        st.warning(
            f"James compliance: Only {seafood_count} seafood meals found (minimum 3). "
            "Ensure the filtered dataset contains sufficient seafood variety."
        )


# ─────────────────────────────────────────────────────────────────────────────
# Tabs
# ─────────────────────────────────────────────────────────────────────────────

# Expanded professional workspace tabs
tab_plan, tab_nutrients, tab_explain, tab_pantry, tab_tracker, tab_grocery = st.tabs([
    "📅  7-Day Meal Plan",
    "📊  Nutrient Analytics",
    "🔍  Explain Exclusions",
    "🍳  Fridge Pantry Matcher",
    "📝  Daily Calorie Tracker",
    "🛒  Smart Grocery List"
])

# ════════════════════════════════════════════════════════════════════════════
# TAB 1 — 7-Day Calendar Grid
# ════════════════════════════════════════════════════════════════════════════

with tab_plan:
    st.subheader("7-Day Personalised Meal Plan")

    day_cols = st.columns(7)

    for col, day in zip(day_cols, DAYS):
        with col:
            # Compliance badge for this day
            if compliance:
                day_ok   = compliance.get(day, {}).get("pass", True)
                badge_cls = "badge-ok" if day_ok else "badge-fail"
                badge_txt = "✓" if day_ok else "⚠"
            else:
                badge_cls = "badge-ok"
                badge_txt = ""

            st.markdown(
                f"<div class='day-header'>{day[:3].upper()}"
                f"{'&nbsp;<span class=' + chr(39) + badge_cls + chr(39) + '>' + badge_txt + '</span>' if badge_txt else ''}"
                f"</div>",
                unsafe_allow_html=True,
            )

            day_meals = plan.get(day, {})
            for mt in MEAL_TYPES:
                meal  = day_meals.get(mt, {})
                icon  = MEAL_ICONS[mt]
                color = MEAL_COLORS[mt]

                if meal:
                    nm  = meal.get("name", "—")
                    cal = meal.get("calories", 0)
                    pro = meal.get("protein",  0)
                    gi  = meal.get("glycemic_index", 0)
                    na  = meal.get("sodium", 0)
                    gi_str = f" · GI {gi:.0f}" if gi and gi > 0 else ""
                    st.markdown(
                        f"<div class='meal-type-label'>{icon} {mt}</div>"
                        f"<div class='meal-card' style='border-left-color:{color}'>"
                        f"<b>{nm}</b><br>"
                        f"<span style='color:#a6adc8'>{cal:.0f} kcal · {pro:.0f}g P"
                        f"{gi_str} · {na:.0f}mg Na</span>"
                        f"</div>",
                        unsafe_allow_html=True,
                    )
                else:
                    st.markdown(
                        f"<div class='meal-type-label'>{icon} {mt}</div>"
                        f"<div class='meal-card' style='opacity:0.35'>No meal available</div>",
                        unsafe_allow_html=True,
                    )

    st.divider()
    st.caption(
        f"**Diversity Score D = {diversity:.4f}** "
        f"({int(diversity*21)} unique meals / 21 total slots). "
        "A score of 1.0 means every meal across the week is completely distinct."
    )

    # Plan download
    flat_rows = []
    for day, day_meals in plan.items():
        for mt, meal in day_meals.items():
            if meal:
                row = {"Day": day, "Meal Type": mt}
                row.update({k: v for k, v in meal.items() if not k.startswith("_")})
                flat_rows.append(row)
    if flat_rows:
        dl_df = pd.DataFrame(flat_rows)
        st.download_button(
            "⬇️ Download 7-Day Plan (CSV)",
            dl_df.to_csv(index=False).encode(),
            file_name=f"nutriai_plan_{profile.get('name','custom').lower()}.csv",
            mime="text/csv",
        )


# ════════════════════════════════════════════════════════════════════════════
# TAB 2 — Nutrient Analytics
# ════════════════════════════════════════════════════════════════════════════

with tab_nutrients:
    st.subheader("Daily Nutrient Totals vs. NIH RDA Benchmarks")
    st.caption(
        "⚠ = below 80% RDA (flagged)  · ↑ = above 150% RDA (overshot)  · ✓ = within healthy range. "
        "Sodium: lower is better."
    )

    # Compliance violations summary per persona
    if pname in PERSONAS and compliance:
        viol_days = [day for day, v in compliance.items() if not v["pass"]]
        if viol_days:
            st.warning(
                f"**Compliance violations on:** {', '.join(viol_days)}. "
                "Scroll to those day panels below."
            )

    for day in DAYS:
        day_meals   = plan.get(day, {})
        totals      = daily_totals(day_meals)
        coverage    = rda_coverage(totals, daily_rda)

        # Count flags for expander label
        macro_flags = sum(
            1 for n in MACRO_NUTRIENTS
            if n != "sodium" and coverage.get(n, 1.0) < BELOW_THRESHOLD
        )
        micro_flags = sum(
            1 for n in MICRO_NUTRIENTS
            if coverage.get(n, 1.0) < BELOW_THRESHOLD
        )
        compliance_violations = compliance.get(day, {}).get("violations", [])
        flag_suffix = ""
        if macro_flags + micro_flags > 0:
            flag_suffix += f"  ⚠ {macro_flags + micro_flags} RDA flag(s)"
        if compliance_violations:
            flag_suffix += f"  🔴 {len(compliance_violations)} compliance violation(s)"

        with st.expander(f"**{day}**{flag_suffix}", expanded=(day == "Monday")):

            if compliance_violations:
                for v in compliance_violations:
                    st.error(f"Compliance violation: {v}")

            # ── Macros ──────────────────────────────────────────────────────
            st.markdown("**Macronutrients**")
            macro_col_list = st.columns(len(MACRO_NUTRIENTS))
            for col, n in zip(macro_col_list, MACRO_NUTRIENTS):
                val    = totals.get(n, 0)
                rda_v  = daily_rda.get(n, 1) or 1
                pct    = min(val / rda_v, 2.0)
                unit   = NUTRIENT_UNITS.get(n, "")

                if n == "sodium":
                    # Lower is better for sodium
                    note = f"✓ {val:.0f}/{rda_v:.0f} mg" if val <= rda_v else f"↑ {pct:.0%}"
                elif pct < BELOW_THRESHOLD:
                    note = f"⚠ {pct:.0%} of RDA"
                elif pct > 1.5:
                    note = f"↑ {pct:.0%} of RDA"
                else:
                    note = f"✓ {pct:.0%} of RDA"

                display = f"{val:.0f}" if n == "calories" else f"{val:.1f}"
                col.metric(
                    label=NUTRIENT_DISPLAY.get(n, n),
                    value=f"{display} {unit}",
                    delta=note,
                    delta_color="off",
                )

            st.divider()

            # ── Micros ──────────────────────────────────────────────────────
            st.markdown("**Micronutrients**")
            micro_col_list = st.columns(len(MICRO_NUTRIENTS))
            for col, n in zip(micro_col_list, MICRO_NUTRIENTS):
                val   = totals.get(n, 0)
                rda_v = daily_rda.get(n, 1) or 1
                pct   = min(val / rda_v, 2.0)
                unit  = NUTRIENT_UNITS.get(n, "")

                if pct < BELOW_THRESHOLD:
                    note = f"⚠ {pct:.0%} of RDA"
                elif pct > 1.5:
                    note = f"↑ {pct:.0%} of RDA"
                else:
                    note = f"✓ {pct:.0%} of RDA"

                display = f"{val:.2f}" if unit in ("µg",) else f"{val:.1f}"
                col.metric(
                    label=NUTRIENT_DISPLAY.get(n, n),
                    value=f"{display} {unit}",
                    delta=note,
                    delta_color="off",
                )

    # ── Weekly coverage heatmap table ────────────────────────────────────────
    st.divider()
    st.subheader("Weekly Nutrient Coverage Heatmap")
    st.caption(
        "Coverage = actual / RDA.  "
        "🔴 < 80%  |  🟢 80–150%  |  🟠 > 150%"
    )

    display_nutrients = [n for n in MACRO_NUTRIENTS + MICRO_NUTRIENTS
                         if n in daily_rda]
    heat_rows = []
    for day in DAYS:
        totals_d  = daily_totals(plan.get(day, {}))
        coverage_d = rda_coverage(totals_d, daily_rda)
        row = {"Day": day}
        for n in display_nutrients:
            row[NUTRIENT_DISPLAY.get(n, n)] = coverage_d.get(n, 0.0)
        heat_rows.append(row)

    heat_df = pd.DataFrame(heat_rows).set_index("Day")

    def _cell_style(val):
        if not isinstance(val, (int, float)):
            return ""
        if val < 0.80:
            return "background-color:#4a1c2a; color:#f38ba8"
        if val > 1.50:
            return "background-color:#3d2c14; color:#fab387"
        return "background-color:#1a3328; color:#a6e3a1"

    st.dataframe(
        heat_df.style.map(_cell_style).format("{:.0%}"),
        use_container_width=True,
    )


# ════════════════════════════════════════════════════════════════════════════
# TAB 3 — Explain Exclusions
# ════════════════════════════════════════════════════════════════════════════

with tab3:
    st.subheader("🕵️‍♂️ Exclusion Explanation Engine")
    st.markdown(
        "Every meal rejected from the full database is logged here with a precise clinical or dietary reason."
    )
    
    # Check if a plan has been run yet
    if 'filtered_df' in st.session_state:
        # Calculate exactly how many items were dropped
        total_database_size = 1250  # Change this to match your actual database count if known
        available_count = len(st.session_state.filtered_df)
        excluded_count = total_database_size - available_count
        
        # Display high-level metrics
        col1, col2 = st.columns(2)
        col1.metric("Meals Retained (Passed Filters)", f"{available_count} items")
        col2.metric("Meals Excluded (Safety Rules)", f"{excluded_count} items")
        
        st.markdown("### 🚫 Active Filter Triggers")
        
        # Dynamically explain exclusions based on sidebar selection
        exclusions = []
        if allergies:
            for allergy in allergies:
                exclusions.append({
                    "Constraint Type": "Allergy Safety Lock",
                    "Trigger Condition": f"Contains {allergy}",
                    "Clinical Reason": f"Immediate exclusion to prevent adverse hyper-reactivity or anaphylactic risk for {patient_name}."
                })
        if conditions:
            for condition in conditions:
                if condition == "Hypertension":
                    exclusions.append({
                        "Constraint Type": "Clinical Condition Filter",
                        "Trigger Condition": "Sodium > 400mg per meal",
                        "Clinical Reason": "Automated dietary ceiling restriction to control systolic and diastolic blood pressure metrics."
                    })
        if diet_type and diet_type != "None":
            exclusions.append({
                "Constraint Type": "Sociocultural Preference",
                "Trigger Condition": f"Non-{diet_type}",
                "Clinical Reason": f"Ensures menu strict compliance with alignment guidelines for a {diet_type} lifestyle."
            })
            
        if exclusions:
            import pandas as pd
            exclusion_df = pd.DataFrame(exclusions)
            st.dataframe(exclusion_df, use_container_width=True)
        else:
            st.success("✅ No structural exclusions active. The entire food index is available.")
    else:
        st.info("Please generate a meal plan first to populate the exclusion log metrics.")

# ════════════════════════════════════════════════════════════════════════════
# TAB 4 — Fridge Pantry Matcher
# ════════════════════════════════════════════════════════════════════════════
with tab_pantry:
    st.subheader("🍳 Inventory Meal Matcher")
    st.caption("Enter the ingredients currently available in your kitchen to discover compliant recipes.")
    
    # Text input for home ingredients
    pantry_input = st.text_input(
        "What's in your fridge? (Separate items with commas)",
        placeholder="e.g., Chicken, spinach, rice, salmon",
        key="pantry_search"
    )
    
    if pantry_input:
        ingredients = [i.strip().lower() for i in pantry_input.split(",") if i.strip()]
        full_db = cached_load_meals()
        
        # Filter matching meals based on names/descriptions
        mask = np.any([full_db['name'].str.contains(ing, case=False, na=False) for ing in ingredients], axis=0)
        matching_meals = full_db[mask]
        
        if not matching_meals.empty:
            st.success(f"Found **{len(matching_meals)}** matching meals in our clinical database:")
            
            # Display matching meals cleanly in columns
            for _, meal in matching_meals.head(10).iterrows():
                with st.expander(f"✨ {meal['name']} ({meal['meal_type']})"):
                    col1, col2, col3 = st.columns(3)
                    col1.metric("Calories", f"{meal['calories']:.0f} kcal")
                    col2.metric("Protein", f"{meal['protein']:.1f} g")
                    col3.metric("Sodium", f"{meal['sodium']:.0f} mg")
        else:
            st.info("No explicit matches found for those specific ingredients. Try widening your search keywords!")

# ════════════════════════════════════════════════════════════════════════════
# TAB 5 — Daily Calorie Tracker Diary
# ════════────────────────────────────────────────────────────────────────────
with tab_tracker:
    st.subheader("📝 Additional Intake Tracker")
    st.caption("Log extra daily snacks, coffee, or beverages to update your total clinical overview.")

    # Initialize a tracking variable in session state if it doesn't exist
    if "extra_calories" not in st.session_state:
        st.session_state.extra_calories = 0.0

    col_track1, col_track2 = st.columns(2)
    
    with col_track1:
        st.markdown("##### Log New Intake")
        snack_name = st.text_input("Item Name", placeholder="e.g., Protein Shake, Handful of Almonds")
        snack_cals = st.number_input("Calories (kcal)", min_value=0, max_value=2000, value=0, step=50)
        
        if st.button("Add to Diary", type="secondary"):
            st.session_state.extra_calories += snack_cals
            st.toast(f"Logged {snack_cals} kcal from {snack_name}!")
            st.rerun()
            
        if st.button("Clear Diary Log", type="primary"):
            st.session_state.extra_calories = 0.0
            st.rerun()

    with col_track2:
        st.markdown("##### Calorie Adjustment Box")
        st.metric("Total Supplemental Consumption", f"{st.session_state.extra_calories:.0f} kcal")
        
        # Calculate new adjusted target summary
        base_cals = sum(daily_totals(plan.get(day, {})).get('calories', 0) for day in DAYS) / 7
        adjusted_total = base_cals + st.session_state.extra_calories
        
        st.info(
            f"Your average plan baseline is **{base_cals:.0f} kcal/day**. "
            f"With your logged items included, your adjusted daily intake is **{adjusted_total:.0f} kcal**."
        )

# ════════════════════════════════════════════════════════════════════════════
# TAB 6 — Smart Grocery List Generator
# ════════════════════════════════════════════════════════════════════════════
with tab_grocery:
    st.subheader("🛒 Patient Weekly Shopping Manifest")
    st.caption("Automatically compiled ingredients and menu items required to prepare your generated 7-day schedule.")

    grocery_items = []
    for day in DAYS:
        for mt in MEAL_TYPES:
            meal = plan.get(day, {}).get(mt, {})
            if meal and "name" in meal:
                grocery_items.append(meal["name"])

    if grocery_items:
        # Deduplicate and sort items nicely
        unique_grocery = sorted(list(set(grocery_items)))
        
        st.markdown("### Required Recipes & Components")
        st.info("💡 Tip: Take a screenshot or print this checklist before heading out to source meal prep materials.")
        
        # Display as clear, checkable interactive boxes
        for item in unique_grocery:
            st.checkbox(f"🛍️ {item}", value=False, key=f"grocery_{item}")
            
        # Passive download function for the grocery file
        grocery_df = pd.DataFrame({"Required Component": unique_grocery})
        st.download_button(
            "⬇️ Export Shopping List (CSV)",
            grocery_df.to_csv(index=False).encode(),
            file_name=f"shopping_list_{profile.get('name','custom').lower()}.csv",
            mime="text/csv"
        )
    else:
        st.warning("Generate a patient dietary plan first to populate your structural shopping catalog.")


    # ── Summary metrics ───────────────────────────────────────────────────────
    summary = summarize_exclusions(excl_log)
    st.markdown("**Exclusion Summary by Category**")
    if summary:
        sum_cols = st.columns(min(len(summary), 6))
        for col, (cat, cnt) in zip(sum_cols, summary.items()):
            col.metric(cat, f"{cnt:,}")

    st.divider()

    # ── Bloom Filter diagnostic ───────────────────────────────────────────────
    from filters import FilterEngine as _FE
    _tmp_bf = _FE(profile)._bloom
    st.markdown(
        f"**Bloom Filter stats** — size: {_tmp_bf.size:,} bits · "
        f"hash functions: {_tmp_bf.num_hashes} · "
        f"estimated FPR: {_tmp_bf.estimated_fpr:.6f}"
    )

    st.divider()

    # ── Search + pagination ───────────────────────────────────────────────────
    s_col1, s_col2 = st.columns([3, 1])
    search_q = s_col1.text_input(
        "Search meal name or reason",
        placeholder="e.g. Garlic, FODMAP, Sodium…",
    )
    max_rows = s_col2.number_input(
        "Max rows", 10, 2000, 100, 10
    )

    report = build_explain_report(excl_log, max_items=len(excl_log))

    if search_q:
        q = search_q.lower()
        report = [
            r for r in report
            if q in r["meal"].lower() or any(q in reason.lower() for reason in r["reasons"])
        ]

    report = report[:max_rows]
    st.caption(f"Showing {len(report):,} of {len(excl_log):,} excluded meals.")

    for item in report:
        with st.expander(f"🚫 {item['meal']}", expanded=False):
            for reason in item["reasons"]:
                st.markdown(f"- {reason}")

    st.divider()

    # ── Download ───────────────────────────────────────────────────────────────
    flat = [{"meal": m, "reason": r}
            for m, rs in excl_log.items() for r in rs]
    st.download_button(
        "⬇️ Download Full Exclusion Log (CSV)",
        pd.DataFrame(flat).to_csv(index=False).encode(),
        file_name=f"nutriai_exclusions_{profile.get('name','custom').lower()}.csv",
        mime="text/csv",
    )
