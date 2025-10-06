
# Meal Plan Mini App (Streamlit) — v2

Features:
- **Allergen/Dislikes filter** (exclude by tags, groups, or names).
- **SR/EN language toggle** in the UI.
- **Predefined profiles**: Cut (-15% kcal, higher protein), Maintain (balanced), Bulk (+15% kcal, higher carbs).
- Download **single-file HTML** (share via chat or host as a link).

## Run locally
```bash
python3 -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```

## Share as a link
- **Streamlit Community Cloud**: push to GitHub and deploy via https://share.streamlit.io (app file `app.py`).
- **Netlify static**: use the app's **Download as HTML**, then upload `meal_plan.html` to https://app.netlify.com/drop.
- **Google Drive**: upload the HTML and share the view link.

## Notes
- If filters are too strict and the pool gets tiny, the app will warn and relax filters to avoid failures.
- Not medical advice.
