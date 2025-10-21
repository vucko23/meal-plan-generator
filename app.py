# app.py — Meal Plan Generator

import math
import streamlit as st
import json
import random
import datetime
import os
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime, date
import time

# ---------- Small helper for animated feedback ----------


def show_loading(msg="Processing...", wait=1.5):
    with st.spinner(msg):
        time.sleep(wait)
    st.toast("✅ Done!")


# ---------- Page config ----------
st.set_page_config(page_title="Meal Plan Generator",
                   page_icon="🥗", layout="wide")

# --- Session defaults (pre SVIH widgeta) ---
DEFAULTS = {
    "days": 7,
    "meals": 3,
    "base_kcal": 2000,
    "diet": "omnivore",
    "profile": "maintain",
    "lang": "EN",  # dosledno "EN"/"SR"
}
for k, v in DEFAULTS.items():
    st.session_state.setdefault(k, v)

# --- Primeni pending preset PRE instanciranja widgeta ---
_pending = st.session_state.pop("__PENDING_PRESET__", None)
if isinstance(_pending, dict):
    for k, v in _pending.items():
        st.session_state[k] = v

# ---- Meal slots & labels (single source of truth) ----
MEAL_SLOTS = ["breakfast", "lunch", "snack", "dinner"]
SLOT_LABELS = {
    "EN": {"breakfast": "Breakfast", "lunch": "Lunch", "snack": "Snack", "dinner": "Dinner"},
    "SR": {"breakfast": "Doručak", "lunch": "Ručak", "snack": "Užina", "dinner": "Večera"},
}
# raspodela dnevnih kcal (možeš menjati)
SLOT_DISTRIB = {"breakfast": 0.25,
                "lunch": 0.35, "snack": 0.10, "dinner": 0.30}

# cilj kcal po obroku (meki rasponi — kao guardrails)
SLOT_KCAL_RANGE = {
    "breakfast": (300, 600),
    "lunch":     (500, 850),
    "snack":     (120, 300),
    "dinner":    (500, 800),
}

# grupe koje važe kao "protein baza" za slane obroke
# prepared često sadrži proteine (npr. “wrap”, “bolognese”)
PROTEIN_GROUPS = {"meat", "fish", "plant_protein",
                  "legumes", "eggs", "prepared"}

# ---------- i18n ----------
if "LANG" not in st.session_state:
    st.session_state["LANG"] = "EN"

labels = {
    "EN": {
        "title": "Meal Plan Generator",
        "caption": "Generate a shareable multi-day meal plan with calories & macros.",
        "sidebar_prefs": "Preferences",
        "days": "Days",
        "kcal": "Daily calories (base)",
        "meals": "Meals per day",
        "diet": "Diet",
        "protein": "Protein %",
        "carbs": "Carbs %",
        "fat": "Fat %",
        "max_items": "Max items per meal",
        "allergens": "Exclude allergens (tags)",
        "groups": "Exclude food groups",
        "dislikes": "Dislikes (comma-separated names)",
        "lang": "Language",
        "profile": "Profile",
        "custom": "Custom",
        "cut": "Cut (-15% kcal, higher protein)",
        "maintain": "Maintain (balanced)",
        "bulk": "Bulk (+15% kcal, higher carbs)",
        "plan_header": "Plan — {days} days at {kcal} kcal/day (effective: {eff_kcal})",
        "download": "⬇️ Download as HTML",
        "tip": "Tip: Send the downloaded HTML via WhatsApp/Email, or host it on Netlify/GitHub Pages to share as a link.",
        "macros_error": "Protein % + Carbs % must be ≤ 100.",
        "about_header": "About this app",
        "about_lines": """🏋️‍♀️ Flexible meal plans with macro targets
🌱 Diets: omnivore, vegetarian, vegan, gluten-free
🧮 Profiles: Cut / Maintain / Bulk
💡 Created by <b>Jelena Vučetić</b>""",
        "day": "Day",
        "meal": "Meal",

        "generate_new": "🔄 Generate new plan",
        "lock": "Lock",
        "regenerate": "Regenerate",
        "shopping_list": "🛒 Shopping list",
        "download_shopping": "Download shopping list (CSV)",
        "locked_warn": "Meal is locked.",
        "no_items_yet": "No items yet — generate a plan first.",

        "presets": "Presets",
        "load_preset": "Load preset",
        "preset_name": "Preset name",
        "save": "Save",
        "delete": "Delete",
        "download_presets": "Download presets.json",
        "upload_presets": "Upload presets.json",
        "presets_imported": "Presets imported.",
        "invalid_file": "Invalid file format (expected JSON object).",
        "failed_to_import": "Failed to import",
        "filters_strict": "Filters are too strict; re-adding all foods temporarily.",
        "totals_header": "Totals for the whole plan",
        "daily_summary": "Daily summary",
        "print_pdf": "🖨️ Print / Save as PDF",
        "calc_estimator": "📊 Calories Estimator",
        "enter_preset_name": "Enter a preset name",
        "show_macro_charts": "Show macro charts"
    },
    "SR": {
        "title": "Generator jelovnika",
        "caption": "Napravi višednevni plan ishrane sa kalorijama i makroima — spreman za deljenje.",
        "sidebar_prefs": "Podešavanja",
        "days": "Dani",
        "kcal": "Dnevne kalorije (osnova)",
        "meals": "Obroka dnevno",
        "diet": "Dijeta",
        "protein": "Proteini %",
        "carbs": "UH %",
        "fat": "Masti %",
        "max_items": "Maks. stavki po obroku",
        "allergens": "Isključi alergene (tagovi)",
        "groups": "Isključi grupe namirnica",
        "dislikes": "Ne sviđa mi se (imenom, odvojeno zarezom)",
        "lang": "Jezik",
        "profile": "Profil",
        "custom": "Prilagođeno",
        "cut": "Deficit (-15% kcal, više proteina)",
        "maintain": "Održavanje (izbalansirano)",
        "bulk": "Suficit (+15% kcal, više UH)",
        "plan_header": "Plan — {days} dana @ {kcal} kcal/dan (efektivno: {eff_kcal})",
        "download": "⬇️ Preuzmi kao HTML",
        "tip": "Savjet: Pošalji HTML preko WhatsApp/E-mail ili hostuj na Netlify/GitHub Pages kao link.",
        "macros_error": "Zbir Proteini% + UH% mora biti ≤ 100.",
        "about_header": "O aplikaciji",
        "about_lines": """🏋️‍♀️ Fleksibilni jelovnici sa makro ciljevima
🌱 Dijete: omnivore, vegetarijanska, veganska, bez glutena
🧮 Profili: Deficit / Održavanje / Suficit
💡 Autor: <b>Jelena Vučetić</b>""",
        "day": "Dan",
        "meal": "Obrok",

        "generate_new": "🔄 Generiši novi plan",
        "lock": "Zaključaj",
        "regenerate": "Ponovo generiši",
        "shopping_list": "🛒 Lista za kupovinu",
        "download_shopping": "Preuzmi listu za kupovinu (CSV)",
        "locked_warn": "Obrok je zaključan.",
        "no_items_yet": "Nema stavki — prvo generiši plan.",

        "presets": "Preseti",
        "load_preset": "Učitaj preset",
        "preset_name": "Naziv preseta",
        "save": "Sačuvaj",
        "delete": "Obriši",
        "download_presets": "Preuzmi presets.json",
        "upload_presets": "Otpremi presets.json",
        "presets_imported": "Preset-i su uvezeni.",
        "invalid_file": "Neispravan format fajla (očekivan je JSON objekat).",
        "failed_to_import": "Neuspješan uvoz",
        "filters_strict": "Filteri su previše striktni; privremeno vraćam sve namirnice.",
        "totals_header": "Ukupno za ceo plan",
        "daily_summary": "Dnevni rezime",
        "print_pdf": "🖨️ Štampaj / Sačuvaj kao PDF",
        "calc_estimator": "📊 Procena kalorija",
        "enter_preset_name": "Unesite naziv preseta",
        "show_macro_charts": "Prikaži makro grafikone"
    },
}
def L(key): return labels[st.session_state.get("LANG", "EN")][key]

# ---------- THEME / CSS ----------


def inject_pro_theme():
    st.markdown("""
    <style>
    :root{
      --bg:#0c111b; --card:#0f172a; --muted:#94a3b8; --text:#e5e7eb; --line:#1e293b;
      --accent:#22d3ee; --accent2:#60a5fa; --chip:#0b1220; --chip-b:#1f2937;
      --radius:14px; --shadow:0 8px 26px rgba(0,0,0,.35);
    }

    /* uži glavni kontejner i centriran */
    .block-container{
      padding-top:1rem;
      max-width:1100px;
      margin:0 auto;
    }

    body{ background:var(--bg); color:var(--text); }

    /* BANNER — centriran i uži */
    .pro-banner{
      border:1px solid var(--line);
      border-radius:calc(var(--radius) + 6px);
      background:
        radial-gradient(1200px 800px at 10% -10%, rgba(34,211,238,.12), transparent 50%),
        radial-gradient(1200px 800px at 100% 10%, rgba(96,165,250,.12), transparent 50%),
        linear-gradient(180deg, #0b1220, #0b1220);
      padding:16px 18px;
      box-shadow:var(--shadow);
      margin:12px auto;
      max-width:980px;
      text-align:center;
    }
    .pro-banner h1{ margin:0 0 6px 0; font-size:20px; }
    .pro-banner .sub{ color:var(--muted); font-size:13px; }

    /* kartice i bar */
    .pro-card{
      background:var(--card);
      border:1px solid var(--line);
      border-radius:var(--radius);
      box-shadow:var(--shadow);
    }
    .bar{ height:9px; background:#0b1220; border:1px solid var(--line); border-radius:999px; overflow:hidden; }
    .fill{ height:100%; background:linear-gradient(90deg, var(--accent), var(--accent2)); }

    /* meal kartice */
    .meal-card{
      background:#111827;
      border:1px solid #242b38;
      border-radius:16px;
      padding:14px 14px;
      margin:16px 0;
    }
    .meal-card:hover {
      border-color:#3b82f6;
      box-shadow:0 0 8px rgba(59,130,246,0.25);
      transition:0.2s ease;
    }
    .meal-head{ display:flex; align-items:center; justify-content:space-between; gap:10px; margin-bottom:6px; }
    .meal-title{ font-weight:800; color:#e5e7eb; font-size:15px; letter-spacing:0.2px; }
    .meal-macros{ display:flex; gap:10px; font-size:12px; color:#cbd5e1; flex-wrap:wrap; }
    .meal-macros .pill{ background:#0f172a; padding:4px 10px; border-radius:999px; border:1px solid #1e293b; font-weight:500; }
    .meal-items{ margin:6px 0 0 0; padding-left:18px; color:#cbd5e1; font-size:14px; }
    .meal-actions{ display:flex; gap:8px; margin-top:8px; }
    .meal-chip{ display:inline-flex; align-items:center; gap:6px; font-size:12px; color:#9ca3af; background:#0b1220; border:1px solid #263044; padding:4px 8px; border-radius:999px; }

    /* +/- tiny buttons (samo naše kvantiti dugmiće) */
    div[data-testid="stButton"] > button.qty {
      width:36px; height:32px; padding:0;
      border-radius:10px; font-weight:700;
      color:#e5e7eb !important;
      background-color:#1f2937 !important;
      border:1px solid #374151 !important;
    }
    div[data-testid="stButton"] > button.qty span {
      color:#e5e7eb !important; font-size:16px !important; font-weight:800 !important; line-height:16px !important;
    }
    div[data-testid="stButton"] > button.qty:hover { background-color:#374151 !important; border-color:#4b5563 !important; }

    /* --- Charts: centriranje + safe širina --- */
    /* Matplotlib/Pyplot */
    div[data-testid="stPyplot"]{
      max-width:520px;   /* smanji ako želiš još uže: npr. 480 */
      margin:8px auto 18px;
    }
    div[data-testid="stPyplot"] figure,
    div[data-testid="stPyplot"] img,
    div[data-testid="stPyplot"] canvas{
      width:100% !important;
      height:auto !important;
    }

    /* Altair/Vega/Plotly */
    div[data-testid="stVegaLiteChart"],
    div[data-testid="stAltairChart"],
    div[data-testid="stPlotlyChart"]{
      max-width:620px;
      margin:8px auto 18px;
    }

    /* Tabele i expander spacing */
    div[data-testid="stDataFrame"]{ margin-top:6px; margin-bottom:18px; }
    div[data-testid="stExpander"]{ margin-bottom:14px; }
    </style>
    """, unsafe_allow_html=True)


def pro_banner(title: str, subtitle: str):
    st.markdown(f"""
    <div class="pro-banner">
      <h1>🥗 {title}</h1>
      <div class="sub">{subtitle}</div>
    </div>
    """, unsafe_allow_html=True)


# call the function to inject the theme
inject_pro_theme()

# ---------- SAFE accessors for old/new item formats ----------


def _kcal_of(x):
    m = x.get("macros")
    if isinstance(m, dict):
        return float(m.get("kcal", x.get("kcal", 0)) or 0)
    return float(x.get("kcal", 0) or 0)


def _p_of(x):
    m = x.get("macros")
    if isinstance(m, dict):
        return float(m.get("p", x.get("p", x.get("protein", 0))) or 0)
    return float(x.get("p", x.get("protein", 0)) or 0)


def _c_of(x):
    m = x.get("macros")
    if isinstance(m, dict):
        return float(m.get("c", x.get("c", x.get("carbs", 0))) or 0)
    return float(x.get("c", x.get("carbs", 0)) or 0)


def _f_of(x):
    m = x.get("macros")
    if isinstance(m, dict):
        return float(m.get("f", x.get("f", x.get("fat", 0))) or 0)
    return float(x.get("f", x.get("fat", 0)) or 0)

# ---------- Data IO ----------


@st.cache_data(show_spinner=False)
def load_foods(path):
    with open(path, "r") as f:
        return json.load(f)


foods_path = os.path.join("data", "foods.json")
try:
    foods = load_foods(foods_path)
except FileNotFoundError:
    st.error(
        f"❌ Missing foods file: `{foods_path}`. Create it or place your foods.json there.")
    st.stop()
except json.JSONDecodeError:
    st.error(f"❌ Invalid JSON in `{foods_path}`. Please fix formatting.")
    st.stop()

# ---------- Core helpers ----------


def filter_by_diet(foods, diet):
    if diet == "omnivore":
        return foods
    if diet == "vegetarian":
        return [x for x in foods if "vegan" in x.get("tags", []) or "vegetarian" in x.get("tags", []) or x["group"] in ["grains", "fruit", "vegetables", "nuts", "legumes", "fat"]]
    if diet == "vegan":
        return [x for x in foods if "vegan" in x.get("tags", []) or x["group"] in ["grains", "fruit", "vegetables", "nuts", "legumes", "fat"]]
    if diet == "gluten-free":
        return [x for x in foods if "gluten-free" in x.get("tags", []) or x["group"] in ["protein", "fruit", "vegetables", "nuts", "legumes", "fat", "dairy"]]
    return foods


def macro_targets(total_kcal, protein_pct, carbs_pct, fat_pct):
    protein_kcal = total_kcal * protein_pct
    carbs_kcal = total_kcal * carbs_pct
    fat_kcal = total_kcal * fat_pct

    protein_g = protein_kcal / 4.0
    carbs_g = carbs_kcal / 4.0
    fat_g = fat_kcal / 9.0

    targets = {
        "kcal": float(total_kcal),
        "p": protein_g,
        "c": carbs_g,
        "f": fat_g,
        "protein_g": protein_g,
        "carbs_g": carbs_g,
        "fat_g": fat_g,
    }
    # cache a copy for downstream lookups that expect a nested "target" mapping
    targets["target"] = {k: targets[k] for k in ("kcal", "p", "c", "f")}
    return targets


def score_meal(meal, targets):
    # Sum macros safely (supports old and new formats)
    kcal = sum(_kcal_of(i) for i in meal)
    p = sum(_p_of(i) for i in meal)
    c = sum(_c_of(i) for i in meal)
    f = sum(_f_of(i) for i in meal)

    tk = targets.get("kcal_meal", targets.get("kcal", 0.0))
    tp = targets.get("p_meal",    targets.get("p",    0.0))
    tc = targets.get("c_meal",    targets.get("c",    0.0))
    tf = targets.get("f_meal",    targets.get("f",    0.0))

    # Weighted absolute diffs
    return abs(kcal - tk) + 2.0*abs(p - tp) + 1.0*abs(c - tc) + 2.0*abs(f - tf)


def build_meal(foods, targets, max_items_per_meal=3):
    if not foods:
        return []

    pool = list(foods)
    best_meal, best_score = None, 1e9

    for _ in range(200):
        if not pool:
            break

        spread = max(2, int(random.gauss(2.5, 0.6)))
        k = max(1, min(max_items_per_meal, spread, len(pool)))

        if k == 0:
            continue

        meal_items = random.sample(pool, k=k)
        if random.random() < 0.35 and pool and len(meal_items) < max_items_per_meal:
            meal_items.append(random.choice(pool))

        score = score_meal(meal_items, targets)
        if score < best_score:
            best_score, best_meal = score, meal_items

    return best_meal or []


def _norm_food(f):
    f = dict(f)
    f["macros"] = f.get("macros") or {
        "kcal": f.get("kcal", 0),
        "p": f.get("p", 0),
        "c": f.get("c", 0),
        "f": f.get("f", 0),
    }
    f["tags"] = f.get("tags", []) or []
    f["slots"] = f.get("slots") or MEAL_SLOTS
    f["portion"] = f.get("portion", 100)
    f["unit"] = f.get("unit", "g")
    f["group"] = f.get("group", "other")
    return f


def foods_for_slot(all_foods, slot):
    pool = []
    for f in all_foods:
        f = _norm_food(f)
        if slot in f["slots"]:
            pool.append(f)
    return pool or [_norm_food(f) for f in all_foods]


def scale_macros(total, frac):
    # total expects dict with keys kcal/p/c/f
    return {k: total[k] * frac for k in ("kcal", "p", "c", "f")}


def slot_targets(total_target):
    return {slot: scale_macros(total_target, SLOT_DISTRIB[slot]) for slot in MEAL_SLOTS}


def build_meal_for_slot(pool, slot_target, slot, max_items_per_meal=3):
    meal = build_meal(pool, slot_target, max_items_per_meal=max_items_per_meal)

    # ako je ručak/večera, mora imati proteine
    if slot in ("lunch", "dinner"):
        has_protein = any((_norm_food(x).get("group")
                          in PROTEIN_GROUPS) for x in meal)
        if not has_protein:
            candidates = [f for f in pool if f.get("group") in PROTEIN_GROUPS]
            if candidates:
                meal[-1] = random.choice(candidates)

    lo, hi = SLOT_KCAL_RANGE[slot]
    tries = 0
    while not (lo <= sum(_kcal_of(x) for x in meal) <= hi) and tries < 3:
        meal = build_meal(pool, slot_target,
                          max_items_per_meal=max_items_per_meal)
        tries += 1
    return meal

# ---------- HTML export (minimal, but robust) ----------


def to_html(plan, targets, title, prefs, mode="web"):
    """Return a minimal standalone HTML so downloads don't crash."""
    lang = prefs.get("lang", "EN")
    day_label = "Day" if lang == "EN" else "Dan"
    carbs_label = "Carbs" if lang == "EN" else "UH"
    fat_label = "Fat" if lang == "EN" else "Masti"

    def _meal_html(meal, idx):
        kcal = int(sum(_kcal_of(i) for i in meal))
        p = int(sum(_p_of(i) for i in meal))
        c = int(sum(_c_of(i) for i in meal))
        f = int(sum(_f_of(i) for i in meal))
        items = "".join(
            [f"<li>{it.get('name', '?')} (~{int(it.get('portion_g', it.get('portion', 0)))} g)</li>" for it in meal])
        return f"""
        <div style="border:1px solid #e5e7eb; border-radius:10px; padding:10px; margin:8px 0;">
          <div style="font-weight:700; margin-bottom:6px;">Meal {idx} • {kcal} kcal • P {p}g • {carbs_label} {c}g • {fat_label} {f}g</div>
          <ul style="margin:0 0 0 18px;">{items}</ul>
        </div>
        """

    days_html = []
    for d_idx, day in enumerate(plan or [], start=1):
        meals = []
        for m_idx, meal in enumerate(day, start=1):
            items = meal.get("items", []) if isinstance(meal, dict) else meal
            meals.append(_meal_html(items, m_idx))
        days_html.append(f"<h3>{day_label} {d_idx}</h3>" + "".join(meals))

    body = "".join(days_html) if days_html else "<p>No items yet.</p>"

    style = """
    <style>
      body{font-family:system-ui,-apple-system,Segoe UI,Roboto,Ubuntu,Cantarell,Inter,sans-serif; padding:18px;}
      h1{margin:0 0 12px 0; font-size:20px}
      h3{margin:18px 0 8px 0;}
    </style>
    """
    return f"<!doctype html><html><head><meta charset='utf-8'>{style}<title>{title}</title></head><body><h1>{title}</h1>{body}</body></html>"


# ---------- Header (lang picker + banner) ----------
col_lang, _ = st.columns([1, 4])
with col_lang:
    lang_choice = st.selectbox(
        "Language / Jezik", ["EN", "SR"],
        index=0 if st.session_state["LANG"] == "EN" else 1,
        key="lang_select"
    )
    st.session_state["LANG"] = lang_choice

pro_banner(L("title"), "Personalized nutrition plans by <b>Jelena Vučetić</b>")

st.caption(L("caption"))

# ---------- Presets helpers ----------
PROFILES_PATH = "profiles.json"


def _read_profiles(path=PROFILES_PATH):
    if not os.path.exists(path):
        return {}
    try:
        with open(path, "r") as f:
            data = json.load(f)
            return data if isinstance(data, dict) else {}
    except Exception as e:
        st.warning(f"⚠️ Failed to read presets from `{path}`: {e}")
        return {}


def _write_profiles(data: dict):
    with open(PROFILES_PATH, "w") as f:
        json.dump(data, f, indent=2)


# ---------- SIDEBAR (Preferences + Presets + About) ----------
with st.sidebar:
    st.header(L("sidebar_prefs"))

    # === 📊 Calories Estimator (Mifflin–St Jeor) ===
    with st.expander(L("calc_estimator"), expanded=True):
        _lang = st.session_state.get("LANG", "EN")
        LBL = {
            "sex": "Sex" if _lang == "EN" else "Pol",
            "female": "Female" if _lang == "EN" else "Žensko",
            "male": "Male" if _lang == "EN" else "Muško",
            "weight": "Weight (kg)" if _lang == "EN" else "Težina (kg)",
            "height": "Height (cm)" if _lang == "EN" else "Visina (cm)",
            "age": "Age" if _lang == "EN" else "Godine",
            "activity": "Activity level" if _lang == "EN" else "Nivo aktivnosti",
            "sed": "Sedentary (little/no exercise)" if _lang == "EN" else "Sedeći (malo/nimalo vežbe)",
            "light": "Light (1–3x/wk)" if _lang == "EN" else "Laki (1–3x/ned)",
            "mod": "Moderate (3–5x/wk)" if _lang == "EN" else "Umereni (3–5x/ned)",
            "act": "Active (6–7x/wk)" if _lang == "EN" else "Aktivan (6–7x/ned)",
            "very": "Very active (physical job + training)" if _lang == "EN" else "Veoma aktivan (fizički posao + trening)",
            "goal": "Goal" if _lang == "EN" else "Cilj",
            "cut": "Cut (deficit)" if _lang == "EN" else "Deficit",
            "maintain": "Maintain" if _lang == "EN" else "Održavanje",
            "bulk": "Bulk (surplus)" if _lang == "EN" else "Suficit",
            "use": "Use this value ↑" if _lang == "EN" else "Iskoristi ovu vrednost ↑",
            "reco": "Recommended base kcal" if _lang == "EN" else "Preporučene bazne kcal",
        }

        sex = st.radio(LBL["sex"], [LBL["female"], LBL["male"]],
                       key="calc_sex", horizontal=True)
        weight = st.number_input(
            LBL["weight"], min_value=30, max_value=250, value=70, step=1, key="calc_weight")
        height = st.number_input(
            LBL["height"], min_value=130, max_value=220, value=170, step=1, key="calc_height")
        age = st.number_input(LBL["age"], min_value=14,
                              max_value=90, value=30, step=1, key="calc_age")

        act_labels = [LBL["sed"], LBL["light"],
                      LBL["mod"], LBL["act"], LBL["very"]]
        act_factors = {act_labels[0]: 1.2, act_labels[1]: 1.375,
                       act_labels[2]: 1.55, act_labels[3]: 1.725, act_labels[4]: 1.9}
        act = st.selectbox(LBL["activity"], act_labels,
                           index=2, key="calc_activity")

        goal_labels = [LBL["cut"], LBL["maintain"], LBL["bulk"]]
        goal_mults = {goal_labels[0]: 0.85,
                      goal_labels[1]: 1.00, goal_labels[2]: 1.15}
        goal = st.selectbox(LBL["goal"], goal_labels, index=1, key="calc_goal")

        s = 5 if sex == LBL["male"] else -161
        bmr = 10 * float(weight) + 6.25 * float(height) - 5 * float(age) + s
        tdee = bmr * act_factors[act]
        rec_kcal = int(round((tdee * goal_mults[goal]) / 50.0) * 50)

        st.metric(LBL["reco"], f"{rec_kcal} kcal")
        if st.button(LBL["use"], key="btn_use_calc_kcal", width="stretch"):
            st.session_state["base_kcal"] = rec_kcal
            st.success(f"{LBL['reco']}: {rec_kcal}")
            st.rerun()

    # --- Preferences ---
    days = st.slider(L("days"), 1, 14,
                     st.session_state.get("days", 7), key="days")
    base_kcal = st.slider(L("kcal"), 1200, 3500, st.session_state.get(
        "base_kcal", 2000), 50, key="base_kcal")

    # --- Fine-tune calories (±300) ---
    st.markdown("### Fine-tune calories")
    adj = st.slider("Adjust kcal", -300, 300,
                    st.session_state.get("adj", 0), 50, key="adj")
    effective_kcal = base_kcal + adj
    st.caption(f"Effective target: **{effective_kcal} kcal/day**")
    st.session_state["effective_kcal"] = effective_kcal

    meals = st.slider(L("meals"), 2, 6, st.session_state.get(
        "meals", 4), key="meals")

    diet_options = ["omnivore", "vegetarian", "vegan", "gluten-free"]
    diet = st.selectbox(L("diet"), diet_options,
                        index=diet_options.index(
                            st.session_state.get("diet", "omnivore")),
                        key="diet")

    profile_options = [L("custom"), L("cut"), L("maintain"), L("bulk")]
    current_profile = st.session_state.get("profile", L("maintain"))
    if current_profile not in profile_options:
        current_profile = L("maintain")
    profile = st.selectbox(L("profile"), profile_options,
                           index=profile_options.index(current_profile),
                           key="profile")

    if profile == L("custom"):
        protein_pct = st.slider(L("protein"), 0.10, 0.50, float(
            st.session_state.get("protein_pct", 0.30)), 0.01, key="protein_pct")
        carbs_pct = st.slider(L("carbs"),   0.20, 0.60, float(
            st.session_state.get("carbs_pct",   0.40)), 0.01, key="carbs_pct")
        if protein_pct + carbs_pct > 1.0:
            st.error(L("macros_error"))
            st.stop()
        fat_pct = 1.0 - protein_pct - carbs_pct
        effective_kcal = base_kcal
        st.write(f"{L('fat')}: **{int(fat_pct*100)}**")
    else:
        if profile == L("cut"):
            protein_pct, carbs_pct, fat_pct = 0.35, 0.35, 0.30
            effective_kcal = int(base_kcal * 0.85)
        elif profile == L("bulk"):
            protein_pct, carbs_pct, fat_pct = 0.25, 0.50, 0.25
            effective_kcal = int(base_kcal * 1.15)
        else:
            protein_pct, carbs_pct, fat_pct = 0.30, 0.40, 0.30
            effective_kcal = base_kcal
        st.session_state["protein_pct"] = protein_pct
        st.session_state["carbs_pct"] = carbs_pct

    max_items = st.slider(L("max_items"), 2, 5, st.session_state.get(
        "max_items", 3), key="max_items")

    all_tags = sorted({t for f in foods for t in f.get("tags", [])})
    all_groups = sorted({f["group"] for f in foods})
    exclude_tags = st.multiselect(L("allergens"), all_tags, default=st.session_state.get(
        "exclude_tags", []), key="exclude_tags")
    exclude_groups = st.multiselect(L("groups"),   all_groups, default=st.session_state.get(
        "exclude_groups", []), key="exclude_groups")
    dislikes = st.text_input(L("dislikes"),
                             value=st.session_state.get("dislikes", "eggs" if st.session_state.get(
                                 "LANG", "EN") == "EN" else "jaja"),
                             key="dislikes")

    st.markdown("---")

    # --- Presets ---
    st.subheader(L("presets"))

    profiles = _read_profiles() or {}
    names = ["—"] + sorted(profiles.keys())
    sel_name = st.selectbox(L("load_preset"), names, key="load_preset")

    if st.button("Load", key="btn_load_preset", width="stretch"):
        if sel_name != "—" and isinstance(profiles.get(sel_name), dict):
            st.session_state["__PENDING_PRESET__"] = profiles[sel_name]
            st.rerun()
        else:
            st.warning("Preset not found or invalid.")

    preset_name = st.text_input(L("preset_name"), value=st.session_state.get(
        "preset_name", ""), key="preset_name_input")

    sc1, sc2 = st.columns(2)
    missing_name = False
    with sc1:
        if st.button(L("save"), key="btn_save_preset", width="stretch"):
            name = (preset_name or "").strip()
            if name:
                profiles[name] = {
                    "days": days, "base_kcal": base_kcal, "meals": meals, "diet": diet, "profile": profile,
                    "protein_pct": protein_pct, "carbs_pct": carbs_pct, "max_items": max_items,
                    "exclude_tags": exclude_tags, "exclude_groups": exclude_groups, "dislikes": dislikes,
                }
                _write_profiles(profiles)
                st.session_state["preset_name"] = name
                st.toast(
                    "✅ " + ("Sačuvano" if st.session_state.get("LANG", "EN") == "SR" else "Saved"))
            else:
                missing_name = True
    with sc2:
        if st.button(L("delete"), key="btn_delete_preset", width="stretch"):
            if sel_name != "—" and sel_name in profiles:
                del profiles[sel_name]
                _write_profiles(profiles)
                st.success(("Obrisano: " if st.session_state.get(
                    "LANG", "EN") == "SR" else "Deleted: ") + sel_name)
                st.rerun()

    if missing_name:
        st.warning(L("enter_preset_name"))

    st.markdown("**Import / Export**")
    st.download_button(L("download_presets"), data=json.dumps(profiles, indent=2),
                       file_name="profiles.json", mime="application/json",
                       key="download_presets_btn", width="stretch")
    up = st.file_uploader(L("upload_presets"), type=[
                          "json"], key="upload_presets_json")
    if up is not None:
        try:
            imported = json.load(up)
            if isinstance(imported, dict):
                _write_profiles(imported)
                st.success(L("presets_imported"))
                st.rerun()
            else:
                st.error(L("invalid_file"))
        except Exception as e:
            st.error(f"{L('failed_to_import')}: {e}")

    st.markdown("---")
    st.markdown(f"**{L('about_header')}**")
    st.markdown(labels[st.session_state['LANG']]
                ["about_lines"], unsafe_allow_html=True)
    st.markdown("[🌐 GitHub](https://github.com/vucko23)")

# ---------- Prepare prefs ----------
prefs = {
    "days": days,
    "kcal": base_kcal,
    "effective_kcal": effective_kcal,
    "meals": meals,
    "protein_pct": protein_pct,
    "carbs_pct": carbs_pct,
    "fat_pct": 1.0 - protein_pct - carbs_pct if profile == L("custom") else fat_pct,
    "diet": diet,
    "max_items": max_items,
    "exclude_tags": exclude_tags,
    "exclude_groups": exclude_groups,
    "dislikes": dislikes,
    "profile": profile,
    "lang": lang_choice,
}
prefs["effective_kcal"] = st.session_state.get(
    "effective_kcal", effective_kcal)

# --- Save/Load user prefs (auto-persist) ---


def save_prefs(prefs: dict) -> None:
    try:
        with open("user_prefs.json", "w", encoding="utf-8") as f:
            json.dump(prefs, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def load_prefs() -> dict:
    try:
        if os.path.exists("user_prefs.json"):
            with open("user_prefs.json", "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        return {}
    return {}


_saved = load_prefs()
if _saved:
    prefs.update(_saved)

# ---------- Generate + render (ALWAYS runs) ----------


def generate_plan(foods, days, prefs):
    macros = macro_targets(
        prefs["effective_kcal"], prefs["protein_pct"], prefs["carbs_pct"], prefs["fat_pct"])
    meals_count = max(1, prefs["meals"])
    macros["kcal_meal"] = prefs["effective_kcal"] / meals_count
    macros["p_meal"] = macros["p"] / meals_count
    macros["c_meal"] = macros["c"] / meals_count
    macros["f_meal"] = macros["f"] / meals_count
    macros["meals"] = meals_count

    pool = filter_by_diet(foods, prefs["diet"])

    if prefs["exclude_tags"]:
        pool = [f for f in pool if not any(tag in f.get(
            "tags", []) for tag in prefs["exclude_tags"])]
    if prefs["exclude_groups"]:
        pool = [f for f in pool if f["group"] not in prefs["exclude_groups"]]
    if prefs["dislikes"]:
        lowers = [x.strip().lower()
                  for x in prefs["dislikes"].split(",") if x.strip()]
        if lowers:
            pool = [f for f in pool if not any(
                tok in f["name"].lower() for tok in lowers)]
    if len(pool) < 5:
        st.warning(L("filters_strict"))
        pool = filter_by_diet(foods, prefs["diet"])

    # build a day using older approach (uniform meals)
    def build_day(foods, targets, meals=4, max_items_per_meal=3):
        best_day, best_score = None, 1e9
        foods_list = list(foods)

        for _ in range(400):
            day, total_score, used = [], 0, set()
            success = True

            for _m in range(meals):
                candidates = [
                    f for f in foods_list if f["name"] not in used or random.random() < 0.4
                ]
                if not candidates:
                    candidates = list(foods_list)

                if not candidates:
                    success = False
                    break

                spread = max(2, int(random.gauss(2.5, 0.6)))
                k = max(1, min(max_items_per_meal, spread, len(candidates)))
                if k == 0:
                    success = False
                    break

                meal_items = random.sample(candidates, k=k)
                if random.random() < 0.35 and candidates and len(meal_items) < max_items_per_meal:
                    meal_items.append(random.choice(candidates))

                total_score += score_meal(meal_items, targets)
                for it in meal_items:
                    used.add(it["name"])
                day.append(meal_items)

            if not success or len(day) != meals:
                continue

            if total_score < best_score:
                best_score, best_day = total_score, day

        return best_day or []

    plan = []
    for _ in range(prefs["days"]):
        day = build_day(
            pool, macros, meals=prefs["meals"], max_items_per_meal=prefs["max_items"])
        plan.append(day)
    return plan, macros


# Compute pool & macros for reuse
_macros_for_pool = macro_targets(
    prefs["effective_kcal"], prefs["protein_pct"], prefs["carbs_pct"], prefs["fat_pct"])
_meals_count = max(1, prefs["meals"])
_macros_for_pool["kcal_meal"] = prefs["effective_kcal"]/_meals_count
_macros_for_pool["p_meal"] = _macros_for_pool["p"] / _meals_count
_macros_for_pool["c_meal"] = _macros_for_pool["c"] / _meals_count
_macros_for_pool["f_meal"] = _macros_for_pool["f"] / _meals_count
_macros_for_pool["meals"] = _meals_count

_pool = filter_by_diet(foods, prefs["diet"])
if prefs["exclude_tags"]:
    _pool = [f for f in _pool if not any(tag in f.get(
        "tags", []) for tag in prefs["exclude_tags"])]
if prefs["exclude_groups"]:
    _pool = [f for f in _pool if f["group"] not in prefs["exclude_groups"]]
if prefs["dislikes"]:
    _lowers = [x.strip().lower()
               for x in prefs["dislikes"].split(",") if x.strip()]
    if _lowers:
        _pool = [f for f in _pool if not any(
            tok in f["name"].lower() for tok in _lowers)]
if len(_pool) < 5:
    _pool = filter_by_diet(foods, prefs["diet"])

# Keep pool/macros in session for callbacks
st.session_state["_POOL"] = _pool
st.session_state["_MACROS"] = _macros_for_pool

if "active_plan" not in st.session_state:
    plan, macros = generate_plan(foods, prefs["days"], prefs)
    st.session_state["active_plan"] = plan
    st.session_state["plan_macros"] = macros
else:
    plan = st.session_state["active_plan"]
    macros = st.session_state.get("plan_macros", _macros_for_pool)


def _get_qty(d_idx, m_idx, i_idx, default=1.0, NS="plan_tab"):
    key = f"{NS}_qty_{d_idx}_{m_idx}_{i_idx}"
    return float(st.session_state.get(key, default))

# ---------- Render helpers ----------


def render_meal_card(meal, m_idx, lang="EN", d_idx=None):
    kcal_m = int(sum((_kcal_of(i) * (_get_qty(d_idx, m_idx, j)
                 if d_idx else 1.0)) for j, i in enumerate(meal)))
    p = int(sum((_p_of(i) * (_get_qty(d_idx, m_idx, j) if d_idx else 1.0))
            for j, i in enumerate(meal)))
    c = int(sum((_c_of(i) * (_get_qty(d_idx, m_idx, j) if d_idx else 1.0))
            for j, i in enumerate(meal)))
    f = int(sum((_f_of(i) * (_get_qty(d_idx, m_idx, j) if d_idx else 1.0))
            for j, i in enumerate(meal)))

    meal_label = "Meal" if lang == "EN" else "Obrok"
    carbs_label = "Carbs" if lang == "EN" else "UH"
    fat_label = "Fat" if lang == "EN" else "Masti"

    items_html = "".join([
        f"<li>{it.get('name', '?')} <span style='color:#94a3b8;font-size:12px'>(~{int(it.get('portion_g', it.get('portion', 0)))} g)</span></li>"
        for it in meal
    ])
    card = f"""
    <div class="meal-card">
      <div class="meal-head">
        <div class="meal-title">{meal_label} {m_idx}</div>
        <div class="meal-macros">
          <span class="pill">{kcal_m} kcal</span>
          <span class="pill">P {p} g</span>
          <span class="pill">{carbs_label} {c} g</span>
          <span class="pill">{fat_label} {f} g</span>
        </div>
      </div>
      <ul class="meal-items">{items_html}</ul>
      <div class="meal-actions">
        <span class="meal-chip">⏱️ quick</span>
        <span class="meal-chip">🥣 simple</span>
      </div>
    </div>
    """
    return card

# ---------- Smart substitutions helpers ----------


def _food_vec(food):
    group = (food.get("group") or "").strip().lower()
    tags = [(t or "").strip().lower() for t in food.get("tags", [])]
    return set([f"g::{group}"] + [f"t::{t}" for t in tags])


def _sim(a: set, b: set) -> float:
    if not a and not b:
        return 1.0
    u = len(a | b)
    return (len(a & b) / u) if u else 0.0


def _macro_close(a, b, tol=0.15):
    for k in ("protein", "carbs", "fat"):
        av = max(1e-6, float(a.get(k, 0)))
        bv = max(1e-6, float(b.get(k, 0)))
        if abs(bv - av) / av > tol:
            return False
    return True


def suggest_swaps(item, pool, topk=5, tol=0.30):
    pool = pool or []

    def _get_kcal(x):
        if isinstance(x, dict):
            m = x.get("macros")
            if isinstance(m, dict):
                return float(m.get("kcal", x.get("kcal", 0) or 0))
        return float(x.get("kcal", 0) or 0)
    base_vec = _food_vec(item)
    base_name = (item.get("name") or "").strip().lower()
    cands = []
    for f in pool:
        if (f.get("name") or "").strip().lower() == base_name:
            continue
        if not _macro_close(item, f, tol=tol):
            continue
        sim = _sim(base_vec, _food_vec(f))
        kcal_gap = abs(_get_kcal(f) - _get_kcal(item))
        score = sim - (kcal_gap / 800.0)
        cands.append((score, f))
    cands.sort(key=lambda x: x[0], reverse=True)
    return [f for _, f in cands[:topk]]

# ---------- Macro math ----------


def macros_of_day(day, d_idx=None):
    P = C = F = 0
    for m_idx, meal in enumerate(day, start=1):
        items = meal.get("items", []) if isinstance(meal, dict) else meal
        for i_idx, it in enumerate(items):
            qty_key = f"plan_tab_qty_{d_idx}_{m_idx}_{i_idx}" if d_idx else None
            qty = float(st.session_state.get(qty_key, 1.0)) if qty_key else 1.0
            P += _p_of(it) * qty
            C += _c_of(it) * qty
            F += _f_of(it) * qty
    return P, C, F


def render_summary(kcal: float, P: float, C: float, F: float,
                   title="Daily summary", lang="EN", show_donut=False):
    """Dark summary: card + 3 progress bars + (optional) donut chart + smart tip (EN/SR)."""
    total_macros = max(P + C + F, 1e-6)
    rp, rc, rf = P / total_macros, C / total_macros, F / total_macros

    if lang == "EN":
        lbl_total = "Total kcal"
        lbl_p = "Protein"
        lbl_c = "Carbs"
        lbl_f = "Fat"
        lbl_tip = "Smart tip"
        tip_balanced = "Perfect balance today! 👌 40% carbs / 35% protein / 25% fat."
        tip_low_p = "Protein share seems low — add a bit more protein."
        tip_high_f = "Fat is a bit high — try lighter cooking methods."
        tip_ok = "Looks good 👍"
        lbls = ["Protein", "Carbs", "Fat"]
        center_label = "Total kcal"
    else:
        lbl_total = "Ukupno kcal"
        lbl_p = "Proteini"
        lbl_c = "Ugljeni hidrati"
        lbl_f = "Masti"
        lbl_tip = "Pametan savet"
        tip_balanced = "Savršen balans! 👌 40% UH / 35% proteini / 25% masti."
        tip_low_p = "Udeo proteina je nizak — ubaci malo više proteina."
        tip_high_f = "Masti su malo visoke — probaj lakše metode pripreme."
        tip_ok = "Izgleda dobro 👍"
        lbls = ["Proteini", "UH", "Masti"]
        center_label = "Ukupno kcal"

    st.markdown(f"### {title}")

    # layout: kartica + (opciono) donut
    left, right = (st.columns([2, 1])
                   if show_donut else (st.container(), None))

    # kartica
    card_html = f"""
    <div style="background:#1f2937;border:1px solid #374151;border-radius:12px;padding:14px;margin:8px 0;color:#e5e7eb;line-height:1.7;">
      <div><b>🔥 {lbl_total}:</b> {int(kcal)}</div>
      <div><b>💪 {lbl_p}:</b> {int(P)} g</div>
      <div><b>🍞 {lbl_c}:</b> {int(C)} g</div>
      <div><b>🥑 {lbl_f}:</b> {int(F)} g</div>
    </div>
    """
    if show_donut:
        with left:
            st.markdown(card_html, unsafe_allow_html=True)
    else:
        st.markdown(card_html, unsafe_allow_html=True)

    # progress barovi
    def _bars():
        st.write(lbl_p)
        st.progress(min(max(rp, 0.0), 1.0))
        st.write(lbl_c)
        st.progress(min(max(rc, 0.0), 1.0))
        st.write(lbl_f)
        st.progress(min(max(rf, 0.0), 1.0))
    (left if show_donut else st).container()  # no-op da zadržimo stil
    if show_donut:
        with left:
            _bars()
    else:
        _bars()

    # donut (opciono)
    if show_donut and right is not None:
        with right:
            fig, ax = plt.subplots(figsize=(2.6, 2.6))

            # 🎨 prilagođene boje (blago pastelne, tamne teme)
            colors = ["#60a5fa", "#facc15", "#34d399"]  # plava / žuta / zelena

            wedges, texts, autotexts = ax.pie(
                [P, C, F],
                labels=lbls,
                colors=colors,
                autopct="%1.0f%%",
                startangle=90,
                pctdistance=0.76,
                labeldistance=1.10,
                wedgeprops=dict(
                    width=0.40, edgecolor="#111827", linewidth=1.0),
            )

            for t in autotexts:
                t.set_color("#111827")
                t.set_fontsize(9)
                t.set_weight("bold")

            for t in texts:
                t.set_fontsize(9)
                t.set_color("#9ca3af")

            ax.axis("equal")

            # tekst u centru: label + kcal vrednost
            ax.text(0, 0.08, center_label, ha="center",
                    va="center", fontsize=9, color="#9ca3af")
            ax.text(0, -0.08, f"{int(kcal)}", ha="center",
                    va="center", fontsize=14, color="#e5e7eb", weight="bold")

            st.pyplot(fig, bbox_inches="tight")
            plt.close(fig)

    # smart tip
    if abs(rp - 0.35) < 0.05 and abs(rc - 0.40) < 0.05 and abs(rf - 0.25) < 0.05:
        tip = tip_balanced
    elif rp < 0.25:
        tip = tip_low_p
    elif rf > 0.35:
        tip = tip_high_f
    else:
        tip = tip_ok

    st.markdown(f"""
    <div style="background:linear-gradient(135deg,#111827,#1f2937);
    border:1px solid #272e3a;border-radius:10px;padding:12px;margin-top:10px;
    color:#e5e7eb;box-shadow:0 0 6px rgba(0,0,0,0.4);transition:0.3s;">
    💡 <b>{lbl_tip}:</b> {tip}
    </div>
    """, unsafe_allow_html=True)


def day_totals(day, d_idx=None):
    kcal = P = C = F = 0
    for m_idx, meal in enumerate(day, start=1):
        items = meal.get("items", []) if isinstance(meal, dict) else meal
        for i_idx, it in enumerate(items):
            qty = _get_qty(d_idx, m_idx, i_idx) if d_idx else 1.0
            kcal += _kcal_of(it) * qty
            P += _p_of(it) * qty
            C += _c_of(it) * qty
            F += _f_of(it) * qty
    return int(kcal), int(P), int(C), int(F)


# ---------- Header & Command bar ----------
st.subheader(L("plan_header").format(
    days=prefs["days"], kcal=prefs["kcal"], eff_kcal=prefs["effective_kcal"]))

title = f"Meal Plan — {prefs['days']} days • {int(prefs['kcal'])} kcal"
c1, c2, c3 = st.columns([1, 1, 1])
with c1:
    if st.button(L("generate_new"), key="cmd_generate", width="stretch"
                 ):
        plan, macros = generate_plan(foods, prefs["days"], prefs)
        st.session_state["active_plan"] = plan
        st.session_state["plan_macros"] = macros
        st.rerun()

with c2:
    web_html = to_html(st.session_state.get(
        "active_plan", []), macros, title, prefs, mode="web")
    st.download_button(label=L("download"),
                       data=(web_html or "").encode("utf-8"),
                       file_name=f"meal_plan_{datetime.now().strftime('%Y%m%d_%H%M')}.html",
                       mime="text/html",
                       key="cmd_dl_web",
                       width="stretch",
                       disabled=not bool(plan))

with c3:
    print_html = to_html(st.session_state.get(
        "active_plan", []), macros, title, prefs, mode="print")
    st.download_button(label=L("print_pdf"),
                       data=(print_html or "").encode("utf-8"),
                       file_name=f"meal_plan_print_{datetime.now().strftime('%Y%m%d_%H%M')}.html",
                       mime="text/html",
                       key="cmd_dl_print",
                       width="stretch",
                       disabled=not bool(plan))

# --- Quick filters (inline) ---
q1, q2, q3 = st.columns(3)
with q1:
    st.checkbox("🥛 No dairy", value=False, key="quick_no_dairy",
                help="Exclude foods tagged dairy/milk")
with q2:
    st.checkbox("🐖 No pork", value=False, key="quick_no_pork",
                help="Exclude pork products")
with q3:
    st.checkbox("🌿 Vegetarian", value=False,
                key="quick_veg", help="No meat/fish/seafood")

# Re-derive filtered pool for quick filters (non-destructive)
_pool_quick = list(_pool)
try:
    if st.session_state.get("quick_no_dairy"):
        _pool_quick = [f for f in _pool_quick if "dairy" not in set(
            f.get("tags", [])) and "milk" not in set(f.get("tags", []))]
    if st.session_state.get("quick_no_pork"):
        _pool_quick = [
            f for f in _pool_quick if "pork" not in set(f.get("tags", []))]
    if st.session_state.get("quick_veg"):
        _pool_quick = [f for f in _pool_quick if f.get("group", "").lower(
        ) not in {"meat", "fish", "seafood"} and "meat" not in set(f.get("tags", []))]
except Exception:
    pass
if len(_pool_quick) < 5:
    _pool_quick = list(_pool)

# --- Tabs: Plan / Summary / Analytics / Presets ---
tab_plan, tab_summary, tab_analytics, tab_presets = st.tabs([
    "🍽 Plan",
    "📊 " + L("daily_summary"),
    "📈 Analytics",
    "🗂 " + L("presets")
])

with tab_summary:
    if plan:
        rows = []
        for d_idx, day in enumerate(plan, start=1):
            kcal, P, C, F = day_totals(day, d_idx)
            rows.append({"Day" if lang_choice == "EN" else "Dan": d_idx,
                        "kcal": kcal, "P": P, "C": C, "F": F})
        df_days = pd.DataFrame(rows)
        st.dataframe(df_days, width="stretch"
                     )
        csv_bytes = df_days.to_csv(index=False).encode("utf-8")
        csv_name = f"daily_summary_{datetime.now().strftime('%Y%m%d_%H%M')}.csv"
        st.download_button("⬇️ CSV", data=csv_bytes, file_name=csv_name,
                           mime="text/csv", width="stretch"
                           )

        # Mini kcal trend
        fig, ax = plt.subplots(figsize=(5, 2.2))
        ax.plot(range(1, len(rows)+1), [r["kcal"]
                for r in rows], marker="o", linewidth=2)
        ax.axhline(prefs.get("effective_kcal", 2000),
                   linestyle="--", linewidth=1, alpha=0.7)
        ax.set_xlabel('Day' if lang_choice == "EN" else 'Dan')
        ax.set_ylabel('kcal')
        ax.set_title('Kcal trend' if lang_choice == "EN" else 'Trend kcal')
        st.pyplot(fig, bbox_inches="tight")
        plt.close(fig)
    else:
        st.caption(L("no_items_yet"))

with tab_analytics:
    st.subheader("Macro & Calorie Overview")
    if plan:
        kcal_list, protein_list, carbs_list, fat_list = [], [], [], []
        for d_idx, day in enumerate(plan, start=1):
            kcal, P, C, F = day_totals(day, d_idx)
            kcal_list.append(kcal)
            protein_list.append(P)
            carbs_list.append(C)
            fat_list.append(F)

        fig, ax = plt.subplots()
        ax.bar(range(1, len(kcal_list)+1), kcal_list)
        ax.set_title("Calories per day")
        ax.set_xlabel("Day")
        ax.set_ylabel("kcal")
        st.pyplot(fig)
        plt.close(fig)

        avg_P = sum(protein_list)/len(protein_list)
        avg_C = sum(carbs_list)/len(carbs_list)
        avg_F = sum(fat_list)/len(fat_list)

        fig2, ax2 = plt.subplots(figsize=(2.2, 2.2))
        ax2.pie([avg_P, avg_C, avg_F], labels=["Protein", "Carbs", "Fat"],
                autopct="%1.0f%%", startangle=90, pctdistance=0.78)
        ax2.axis("equal")
        st.pyplot(fig2, bbox_inches="tight")
        plt.close(fig2)
    else:
        st.caption(L("no_items_yet"))

with tab_presets:
    st.caption(
        "Presets su u sidebaru (levo) — tu možeš da sačuvaš, učitaš i uvezeš fajl.")
    st.subheader("📤 Export / 📥 Import Presets")

    profiles_path = "data/profiles.json"
    if os.path.exists(profiles_path):
        with open(profiles_path, "r") as f:
            profiles2 = json.load(f)
    else:
        profiles2 = {}

    if profiles2:
        export_json = json.dumps(profiles2, indent=2)
        st.download_button(label="💾 Export all presets (JSON)", data=export_json,
                           file_name="meal_presets.json", mime="application/json",
                           key="btn_export_presets", width="stretch"
                           )
    else:
        st.info("No presets available yet.")

    uploaded = st.file_uploader("📥 Import presets (.json)", type=[
                                "json"], key="upload_presets")
    if uploaded:
        new_profiles = json.load(uploaded)
        profiles2.update(new_profiles)
        with open(profiles_path, "w") as f:
            json.dump(profiles2, f, indent=2)
        st.success("✅ Presets imported successfully.")
        st.rerun()

with tab_plan:
    if not plan:
        st.markdown(f"""
        <div class="meal-card" style="text-align:center; padding:20px;">
            <div class="meal-title">Nothing here yet</div>
            <p style="color:#9ca3af; margin-top:6px;">{L("no_items_yet")}</p>
        </div>
        """, unsafe_allow_html=True)
        if st.button(L("generate_new"), key="btn_generate_from_empty", width="stretch"
                     ):
            plan, macros = generate_plan(foods, prefs["days"], prefs)
            st.session_state["active_plan"] = plan
            st.session_state["plan_macros"] = macros
            st.rerun()
    else:
        show_charts = st.checkbox(
            L("show_macro_charts"), value=True, key="show_charts")
        NS = "plan_tab"

        # 🔄 Regenerate ALL unlocked meals (slot-aware)
        if st.button("🔄 Regenerate all unlocked meals", key=f"{NS}_regen_all",
                     help="Rebuild every meal that isn't locked (respecting Breakfast/Lunch/Snack/Dinner)",
                     width="stretch"
                     ):
            show_loading("🔄 Regenerating full plan...", wait=1.2)
            plan_cur = st.session_state.get("active_plan", [])

            eff = prefs.get("effective_kcal", 2000)
            pp = prefs.get("protein_pct", 0.30)
            cp = prefs.get("carbs_pct", 0.40)
            fp = prefs.get("fat_pct", 0.30)
            total_target = {"kcal": float(eff),
                            "p": float(eff * pp / 4.0),
                            "c": float(eff * cp / 4.0),
                            "f": float(eff * fp / 9.0)}
            slot_tgts = slot_targets(total_target)

            for d_idx, day in enumerate(plan_cur, start=1):
                for m_idx, meal in enumerate(day, start=1):
                    if st.session_state.get(f"{NS}_lock_{d_idx}_{m_idx}", False):
                        continue
                    if isinstance(meal, dict):
                        slot = meal.get(
                            "slot", MEAL_SLOTS[(m_idx - 1) % len(MEAL_SLOTS)])
                        items_now = meal.get("items", [])
                    else:
                        slot = MEAL_SLOTS[(m_idx - 1) % len(MEAL_SLOTS)]
                        items_now = meal
                    pool = foods_for_slot(_pool_quick, slot)
                    new_items = build_meal_for_slot(pool=pool, slot_target=slot_tgts[slot],
                                                    slot=slot, max_items_per_meal=prefs.get("max_items", 3))
                    if isinstance(meal, dict):
                        plan_cur[d_idx - 1][m_idx -
                                            1] = {"slot": slot, "items": new_items}
                    else:
                        plan_cur[d_idx - 1][m_idx - 1] = new_items

            st.session_state["active_plan"] = plan_cur
            st.toast("🔄 Plan regenerated (unlocked meals).")
            st.rerun()

        # === Day by day render ===
        NS = "plan_tab"  # namespace za qty/lock ključeve

        for d_idx, day in enumerate(plan, start=1):
            with st.expander(f"{labels[lang_choice]['day']} {d_idx}"):

                # ---------- TOOLBAR (Regenerate / Reset) ----------
                with st.container():
                    c_reg, c_rst = st.columns(
                        [1, 1], vertical_alignment="bottom")

                    with c_reg:
                        if st.button("🔁 Regenerate this day", key=f"regen_day_{d_idx}", width="stretch"
                                     ):
                            show_loading(
                                "🔄 Regenerating this day...", wait=1.0)
                            eff = prefs.get("effective_kcal", 2000)
                            pp = prefs.get("protein_pct", 0.30)
                            cp = prefs.get("carbs_pct", 0.40)
                            fp = prefs.get("fat_pct", 0.30)
                            total_target = {"kcal": float(eff),
                                            "p": float(eff * pp / 4.0),
                                            "c": float(eff * cp / 4.0),
                                            "f": float(eff * fp / 9.0)}
                            targets = slot_targets(total_target)
                            pool_all = st.session_state.get("_POOL", [])
                            new_day = []
                            for slot in MEAL_SLOTS:
                                pool = foods_for_slot(pool_all, slot)
                                items = build_meal_for_slot(
                                    pool, targets[slot], slot, max_items_per_meal=prefs["max_items"])
                                new_day.append({"slot": slot, "items": items})
                            st.session_state["active_plan"][d_idx - 1] = new_day
                            st.rerun()

                    with c_rst:
                        if st.button("🧹 Reset quantities", key=f"reset_qty_day_{d_idx}", width="stretch"
                                     ):
                            for m_idx, meal in enumerate(day, start=1):
                                items = meal.get("items", []) if isinstance(
                                    meal, dict) else meal
                                for i_idx, _ in enumerate(items):
                                    st.session_state.pop(
                                        f"{NS}_qty_{d_idx}_{m_idx}_{i_idx}", None)
                            st.rerun()

                # ---------- Meals for the day ----------
                for m_idx, meal in enumerate(day, start=1):
                    if isinstance(meal, dict):
                        slot = meal.get(
                            "slot", MEAL_SLOTS[(m_idx - 1) % len(MEAL_SLOTS)])
                        items = meal.get("items", [])
                    else:
                        slot = MEAL_SLOTS[(m_idx - 1) % len(MEAL_SLOTS)]
                        items = meal

                    LBL = SLOT_LABELS[st.session_state.get("LANG", "EN")]
                    st.markdown(f"**{LBL.get(slot, slot.title())}**")

                    st.markdown(
                        render_meal_card(
                            items, m_idx, lang=lang_choice, d_idx=d_idx),
                        unsafe_allow_html=True
                    )

                    for i_idx, item in enumerate(items):
                        qkey = f"{NS}_qty_{d_idx}_{m_idx}_{i_idx}"
                        current = float(st.session_state.get(qkey, 1.0))

                        c1, c2, c3 = st.columns(
                            [1, 1, 6], vertical_alignment="center")

                        with c1:
                            if st.button("\u2212", key=f"{NS}_btn_dec_{d_idx}_{m_idx}_{i_idx}", type="secondary"):
                                st.session_state[qkey] = max(
                                    0.5, current - 0.5)
                                st.rerun()

                        with c2:
                            if st.button("\uFF0B", key=f"{NS}_btn_plus_{d_idx}_{m_idx}_{i_idx}", type="secondary"):
                                st.session_state[qkey] = current + 0.5
                                st.rerun()

                        with c3:
                            pool_all = st.session_state.get("_POOL", [])
                            slot_pool = foods_for_slot(pool_all, slot)
                            sugs = suggest_swaps(item, slot_pool) or []

                            st.caption(
                                f"{item.get('name', '?')} × {st.session_state.get(qkey, 1.0)}")

                            if sugs:
                                sel_label = "Suggest swap" if lang_choice == "EN" else "Predlog zamene"
                                alt_names = ["—"] + \
                                    [a.get("name", "") for a in sugs]
                                sel_alt = st.selectbox(
                                    sel_label, alt_names, key=f"suggest_{d_idx}_{m_idx}_{i_idx}")

                                if sel_alt != "—":
                                    new_item = next(a for a in sugs if a.get(
                                        "name", "") == sel_alt)
                                    qty_now = float(
                                        st.session_state.get(qkey, 1.0))

                                    base_item = _norm_food(new_item)
                                    replacement = dict(base_item)
                                    replacement["macros"] = dict(
                                        base_item.get("macros", {}))
                                    replacement["tags"] = list(
                                        base_item.get("tags", []))
                                    replacement["group"] = base_item.get(
                                        "group", item.get("group", ""))
                                    replacement["portion"] = base_item.get(
                                        "portion", item.get("portion", 0))
                                    replacement["unit"] = base_item.get(
                                        "unit", item.get("unit", ""))
                                    replacement["portion_g"] = new_item.get(
                                        "portion_g",
                                        item.get(
                                            "portion_g",
                                            item.get("portion", replacement.get("portion", 0))
                                        )
                                    )

                                    if isinstance(st.session_state["active_plan"][d_idx-1][m_idx-1], dict):
                                        st.session_state["active_plan"][d_idx-1][m_idx-1]["items"][i_idx] = replacement
                                    else:
                                        st.session_state["active_plan"][d_idx-1][m_idx-1][i_idx] = replacement

                                    st.session_state[qkey] = qty_now
                                    st.toast("✨ Swapped" if lang_choice ==
                                             "EN" else "✨ Zamenjeno")
                                    st.rerun()

                    # kontrole za jedan obrok (lock / regenerate)
                    ctrl_cols = st.columns([1, 1, 2])
                    lock_key = f"{NS}_lock_{d_idx}_{m_idx}"
                    regen_key = f"{NS}_regen_{d_idx}_{m_idx}"

                    with ctrl_cols[0]:
                        st.checkbox(L("lock"), key=lock_key,
                                    value=st.session_state.get(lock_key, False))

                    with ctrl_cols[1]:
                        if st.button(L("regenerate"), key=regen_key):
                            if not st.session_state.get(lock_key, False):
                                pool_all = st.session_state.get("_POOL", [])
                                slot_pool = foods_for_slot(pool_all, slot)

                                total_target = st.session_state.get("_MACROS", {}).get("target", {
                                    "kcal": float(prefs.get("effective_kcal", 2000)),
                                    "p": float(prefs.get("effective_kcal", 2000) * prefs.get("protein_pct", 0.30) / 4.0),
                                    "c": float(prefs.get("effective_kcal", 2000) * prefs.get("carbs_pct", 0.40) / 4.0),
                                    "f": float(prefs.get("effective_kcal", 2000) * prefs.get("fat_pct", 0.30) / 9.0),
                                })
                                tgt = scale_macros(
                                    total_target, SLOT_DISTRIB.get(slot, 0.25))

                                new_meal = build_meal_for_slot(
                                    slot_pool, tgt, slot, max_items_per_meal=prefs.get(
                                        "max_items", 3)
                                )

                                if new_meal:
                                    if isinstance(st.session_state["active_plan"][d_idx-1][m_idx-1], dict):
                                        st.session_state["active_plan"][d_idx-1][m_idx-1] = {
                                            "slot": slot, "items": new_meal}
                                    else:
                                        st.session_state["active_plan"][d_idx -
                                                                        1][m_idx-1] = new_meal

                                    st.toast(
                                        "🔁 Meal regenerated" if lang_choice == "EN" else "🔁 Obrok regenerisan")
                                    st.rerun()
                            else:
                                st.warning(L("locked_warn"))

                # === Day summary (posle svih obroka; 1× po danu) ===
                if show_charts:
                    kcal_d, P_d, C_d, F_d = day_totals(day, d_idx=d_idx)
                    title_pc = ("Day {0} summary".format(
                        d_idx) if lang_choice == "EN" else f"Dan {d_idx} — sažetak")
                    render_summary(kcal_d, P_d, C_d, F_d, title=title_pc,
                                   lang=lang_choice, show_donut=True)

        # === Whole plan summary (jednom, posle svih dana) ===
        if show_charts:
            plan_kcal = plan_P = plan_C = plan_F = 0
            for d_i, dday in enumerate(plan, start=1):
                k, p, c, f = day_totals(dday, d_idx=d_i)
                plan_kcal += k
                plan_P += p
                plan_C += c
                plan_F += f

            ttl_title = ("Whole plan summary" if lang_choice ==
                         "EN" else "Sažetak celog plana")
            render_summary(plan_kcal, plan_P, plan_C, plan_F,
                           title=ttl_title, lang=lang_choice, show_donut=True)


# === Shopping List (aggregated) ===
with st.expander(L("shopping_list"), expanded=False):
    plan_now = st.session_state.get("active_plan", [])
    if plan_now:
        rows = []
        NS = "plan_tab"
        for d_idx, day in enumerate(plan_now, start=1):
            for m_idx, meal in enumerate(day, start=1):
                items = meal.get("items", []) if isinstance(
                    meal, dict) else meal
                for i_idx, it in enumerate(items):
                    qkey = f"{NS}_qty_{d_idx}_{m_idx}_{i_idx}"
                    q = float(st.session_state.get(qkey, 1.0))
                    pg = float(
                        it.get("portion_g", it.get("portion", 0)) or 0.0)
                    rows.append({"name": it.get("name", "Item"),
                                "qty": q, "grams": pg * q})
        if rows:
            df = pd.DataFrame(rows).groupby("name", as_index=False).agg(
                {"qty": "sum", "grams": "sum"})
            df["qty"] = df["qty"].round(2)
            df["grams"] = df["grams"].round(0).astype(int)
            df["kg"] = (df["grams"] / 1000.0).round(2)
            df = df.sort_values("name")

            _lang = st.session_state.get("LANG", "EN")
            df_disp = df.rename(columns={
                "name": "Item" if _lang == "EN" else "Namirnica",
                "qty":  "Qty" if _lang == "EN" else "Količina",
                "grams": "Grams" if _lang == "EN" else "Grami",
                "kg":   "Kg" if _lang == "EN" else "Kg"
            })
            st.dataframe(df_disp, width="stretch"
                         )

            csv = df_disp.to_csv(index=False).encode("utf-8")
            st.download_button(label=L("download_shopping"),
                               data=csv, file_name="shopping_list.csv",
                               mime="text/csv", key="dl_shop_csv",
                               width="stretch"
                               )

            total_items = len(df_disp)
            total_kg = float(df["kg"].sum())
            st.caption((f"Total items: {total_items} • Approx. weight: {total_kg:.2f} kg")
                       if _lang == "EN" else f"Ukupno stavki: {total_items} • Približno: {total_kg:.2f} kg")
        else:
            st.caption(L("no_items_yet"))
    else:
        st.caption(L("no_items_yet"))

st.info(L("tip"))

# --- Auto-save current preferences ---
prefs["effective_kcal"] = st.session_state.get(
    "effective_kcal", prefs.get("effective_kcal", prefs.get("kcal", base_kcal)))
try:
    save_prefs(prefs)
except Exception:
    pass
