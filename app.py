
import streamlit as st
import json, random, math, datetime, os

# ----------------------- i18n -----------------------
LANG = st.session_state.get("LANG", "EN")
labels = {
    "EN": {
        "title": "🥗 Meal Plan Generator",
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
    },
    "SR": {
        "title": "🥗 Generator jelovnika",
        "caption": "Napravi višednevni plan ishrane sa kalorijama i makroima — spreman za deljenje.",
        "sidebar_prefs": "Podešavanja",
        "days": "Broj dana",
        "kcal": "Dnevne kalorije (osnovna vrednost)",
        "meals": "Obroka dnevno",
        "diet": "Dijeta",
        "protein": "Proteini %",
        "carbs": "Ugljeni hidrati %",
        "fat": "Masti %",
        "max_items": "Maks. namirnica po obroku",
        "allergens": "Isključi alergene (tagovi)",
        "groups": "Isključi grupe namirnica",
        "dislikes": "Ne volim (imena odvojena zarezom)",
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
    },
}

def L(key):
    return labels[st.session_state.get("LANG","EN")][key]

# ----------------------- Core logic -----------------------
def load_foods(path):
    with open(path, "r") as f:
        return json.load(f)

def filter_by_diet(foods, diet):
    if diet == "omnivore":
        return foods
    if diet == "vegetarian":
        return [x for x in foods if "vegan" in x.get("tags", []) or "vegetarian" in x.get("tags", []) or x["group"] in ["grains","fruit","vegetables","nuts","legumes","fat"]]
    if diet == "vegan":
        return [x for x in foods if "vegan" in x.get("tags", []) or x["group"] in ["grains","fruit","vegetables","nuts","legumes","fat"]]
    if diet == "gluten-free":
        return [x for x in foods if "gluten-free" in x.get("tags", []) or x["group"] in ["protein","fruit","vegetables","nuts","legumes","fat","dairy"]]
    return foods

def macro_targets(total_kcal, protein_pct, carbs_pct, fat_pct):
    protein_kcal = total_kcal * protein_pct
    carbs_kcal = total_kcal * carbs_pct
    fat_kcal = total_kcal * fat_pct
    return {"protein_g": protein_kcal/4.0, "carbs_g": carbs_kcal/4.0, "fat_g": fat_kcal/9.0}

def score_meal(meal, targets):
    kcal = sum(i["kcal"] for i in meal)
    protein = sum(i["protein"] for i in meal)
    carbs = sum(i["carbs"] for i in meal)
    fat = sum(i["fat"] for i in meal)
    kcal_diff = abs(kcal - targets["kcal_meal"])
    p_diff = abs(protein - (targets["protein_g"]/targets["meals"]))
    c_diff = abs(carbs - (targets["carbs_g"]/targets["meals"]))
    f_diff = abs(fat - (targets["fat_g"]/targets["meals"]))
    return kcal_diff + p_diff*2 + c_diff + f_diff*2

def build_day(foods, targets, meals=4, max_items_per_meal=3):
    best_day, best_score = None, 1e9
    for _ in range(500):
        day, total_score, used = [], 0, set()
        for _m in range(meals):
            candidates = [f for f in foods if f["name"] not in used or random.random() < 0.4]
            k = min(max_items_per_meal, max(2, int(random.gauss(2.5,0.6))))
            if len(candidates) < k:
                # if too filtered, fallback to any foods
                candidates = foods
            meal_items = random.sample(candidates, k=k)
            if random.random() < 0.35 and len(candidates) > 0:
                meal_items.append(random.choice(candidates))
            total_score += score_meal(meal_items, targets)
            for it in meal_items: used.add(it["name"])
            day.append(meal_items)
        if total_score < best_score:
            best_score, best_day = total_score, day
    return best_day

def to_html(plan, targets, title, prefs):
    def meal_stats(items):
        kcal = sum(i["kcal"] for i in items)
        protein = sum(i["protein"] for i in items)
        carbs = sum(i["carbs"] for i in items)
        fat = sum(i["fat"] for i in items)
        return kcal, protein, carbs, fat

    def day_stats(day):
        kcal = sum(sum(i["kcal"] for i in meal) for meal in day)
        protein = sum(sum(i["protein"] for i in meal) for meal in day)
        carbs = sum(sum(i["carbs"] for i in meal) for meal in day)
        fat = sum(sum(i["fat"] for i in meal) for meal in day)
        return kcal, protein, carbs, fat

    shopping = {}
    for day in plan:
        for meal in day:
            for it in meal:
                shopping[it["name"]] = shopping.get(it["name"], 0) + 1

    html = []
    html.append(f"""<!doctype html><html><head><meta charset='utf-8'><meta name="viewport" content="width=device-width, initial-scale=1">
    <title>{title}</title>
    <style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; margin: 24px; }}
    h1 {{ margin-bottom: 4px; }}
    .meta {{ color:#555; margin-bottom: 16px; }}
    .card {{ border:1px solid #eee; border-radius:12px; padding:16px; margin-bottom:16px; box-shadow: 0 1px 3px rgba(0,0,0,0.04);}}
    .meal {{ margin-bottom: 8px; }}
    .pill {{ background:#f4f6f8; padding:4px 8px; border-radius:999px; font-size:12px; margin-right:6px; }}
    table {{ border-collapse: collapse; width: 100%; }}
    th, td {{ border-bottom:1px solid #eee; padding:8px; text-align:left; font-size:14px; }}
    .small {{ font-size: 12px; color:#666; }}
    .footer {{ margin-top:24px; font-size:12px; color:#777; }}
    </style></head><body>""")
    html.append(f"<h1>{title}</h1>")
    html.append(f"<div class='meta'>Generated on {datetime.date.today().isoformat()} • Diet: <b>{prefs['diet']}</b> • Daily base target: <b>{prefs['kcal']} kcal</b> • Profile: <b>{prefs['profile']}</b> • Effective: <b>{int(prefs['effective_kcal'])} kcal</b> • Meals/day: <b>{prefs['meals']}</b></div>")
    html.append("<div class='card'><b>Macro targets</b><br>")
    html.append(f"<span class='pill'>Protein: {targets['protein_g']:.0f} g</span><span class='pill'>Carbs: {targets['carbs_g']:.0f} g</span><span class='pill'>Fat: {targets['fat_g']:.0f} g</span>")
    html.append("</div>")
    for d_idx, day in enumerate(plan, start=1):
        d_k, d_p, d_c, d_f = day_stats(day)
        html.append(f"<div class='card'><h3>Day {d_idx} — {int(d_k)} kcal</h3>")
        for m_idx, meal in enumerate(day, start=1):
            m_k, m_p, m_c, m_f = meal_stats(meal)
            html.append(f"<div class='meal'><b>Meal {m_idx}</b> — {int(m_k)} kcal • P {int(m_p)}g • C {int(m_c)}g • F {int(m_f)}g<ul>")
            for it in meal:
                html.append(f"<li>{it['name']} <span class='small'>(~{it['portion_g']} g)</span></li>")
            html.append("</ul></div>")
        html.append("</div>")
    html.append("<div class='card'><h3>Shopping list (by portions)</h3><table><tr><th>Item</th><th>Portions</th></tr>")
    for name, count in sorted(shopping.items(), key=lambda x: (-x[1], x[0])):
        html.append(f"<tr><td>{name}</td><td>{count}</td></tr>")
    html.append("</table></div>")
    html.append("<div class='footer'>Tip: Portions are approximate; adjust slightly to hit exact calories/macros. Data is illustrative and not medical advice.</div>")
    html.append("</body></html>")
    return "\n".join(html)

def generate_plan(foods, days, prefs):
    macros = macro_targets(prefs["effective_kcal"], prefs["protein_pct"], prefs["carbs_pct"], prefs["fat_pct"])
    macros["kcal_meal"] = prefs["effective_kcal"]/prefs["meals"]
    macros["meals"] = prefs["meals"]
    pool = filter_by_diet(foods, prefs["diet"])

    # Apply allergens/groups/dislikes filters
    if prefs["exclude_tags"]:
        pool = [f for f in pool if not any(tag in f.get("tags", []) for tag in prefs["exclude_tags"])]
    if prefs["exclude_groups"]:
        pool = [f for f in pool if f["group"] not in prefs["exclude_groups"]]
    if prefs["dislikes"]:
        lowers = [x.strip().lower() for x in prefs["dislikes"].split(",") if x.strip()]
        if lowers:
            pool = [f for f in pool if not any(tok in f["name"].lower() for tok in lowers)]
    if len(pool) < 5:
        st.warning("Filters are too strict; re-adding all foods temporarily.")
        pool = filter_by_diet(foods, prefs["diet"])

    plan = []
    for _ in range(days):
        day = build_day(pool, macros, meals=prefs["meals"], max_items_per_meal=prefs["max_items"])
        plan.append(day)
    return plan, macros

# ----------------------- UI -----------------------
if "LANG" not in st.session_state:
    st.session_state["LANG"] = "EN"

col_lang, _ = st.columns([1,4])
with col_lang:
    lang_choice = st.selectbox("Language / Jezik", ["EN","SR"], index=0 if st.session_state["LANG"]=="EN" else 1)
st.session_state["LANG"] = lang_choice

st.title(L("title"))
st.caption(L("caption"))

with st.sidebar:
    st.header(L("sidebar_prefs"))
    days = st.slider(L("days"), 1, 14, 7)
    base_kcal = st.slider(L("kcal"), 1200, 3500, 2000, 50)
    meals = st.slider(L("meals"), 2, 6, 4)
    diet = st.selectbox(L("diet"), ["omnivore","vegetarian","vegan","gluten-free"])

    profile = st.selectbox(L("profile"), [L("custom"), L("cut"), L("maintain"), L("bulk")], index=1)
    # Defaults
    protein_pct, carbs_pct, fat_pct = 0.30, 0.40, 0.30
    effective_kcal = base_kcal
    if profile == L("cut"):
        effective_kcal = int(base_kcal * 0.85)
        protein_pct, carbs_pct, fat_pct = 0.35, 0.35, 0.30
    elif profile == L("maintain"):
        effective_kcal = base_kcal
        protein_pct, carbs_pct, fat_pct = 0.30, 0.40, 0.30
    elif profile == L("bulk"):
        effective_kcal = int(base_kcal * 1.15)
        protein_pct, carbs_pct, fat_pct = 0.25, 0.50, 0.25
    else:
        protein_pct = st.slider(L("protein"), 10, 50, 30) / 100.0
        carbs_pct = st.slider(L("carbs"), 20, 60, 40) / 100.0
        if protein_pct + carbs_pct > 1.0:
            st.error(L("macros_error"))
            st.stop()
        fat_pct = 1.0 - protein_pct - carbs_pct
        st.write(f"{L('fat')}: **{int(fat_pct*100)}**")

    max_items = st.slider(L("max_items"), 2, 5, 3)

    # Allergens & dislikes
    foods = load_foods(os.path.join("data", "foods.json"))
    all_tags = sorted({t for f in foods for t in f.get("tags", [])})
    all_groups = sorted({f["group"] for f in foods})
    exclude_tags = st.multiselect(L("allergens"), all_tags, default=[])
    exclude_groups = st.multiselect(L("groups"), all_groups, default=[])
    dislikes = st.text_input(L("dislikes"), value="eggs" if lang_choice=="EN" else "jaja")

prefs = {
    "kcal": base_kcal,
    "effective_kcal": effective_kcal,
    "meals": meals,
    "protein_pct": protein_pct,
    "carbs_pct": carbs_pct,
    "fat_pct": fat_pct,
    "diet": diet,
    "max_items": max_items,
    "exclude_tags": exclude_tags,
    "exclude_groups": exclude_groups,
    "dislikes": dislikes,
    "profile": profile,
}
plan, macros = generate_plan(foods, days, prefs)

# Render plan
st.subheader(L("plan_header").format(days=days, kcal=base_kcal, eff_kcal=effective_kcal))
for d_idx, day in enumerate(plan, start=1):
    with st.expander(f"Day {d_idx}" if lang_choice=="EN" else f"Dan {d_idx}"):
        for m_idx, meal in enumerate(day, start=1):
            kcal_m = int(sum(i["kcal"] for i in meal))
            p = int(sum(i["protein"] for i in meal))
            c = int(sum(i["carbs"] for i in meal))
            f = int(sum(i["fat"] for i in meal))
            st.markdown((f"**Meal {m_idx}** — {kcal_m} kcal • P {p}g • C {c}g • F {f}g") if lang_choice=="EN"
                        else (f"**Obrok {m_idx}** — {kcal_m} kcal • P {p}g • UH {c}g • M {f}g"))
            st.write(", ".join([f"{it['name']} (~{it['portion_g']} g)" for it in meal]))

# Download HTML
title = f"Meal Plan — {days} days — {int(effective_kcal)} kcal/day"
html = to_html(plan, macros, title, prefs)
st.download_button(L("download"), data=html.encode("utf-8"), file_name="meal_plan.html", mime="text/html")

st.info(L("tip"))
