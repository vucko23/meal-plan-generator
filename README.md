# JV Fit — Meal Plan Generator

Personalized nutrition plans by **Jelena Vučetić**.  
Generate shareable multi-day meal plans with calorie & macro targets.

[![Deployed on Streamlit Cloud](https://img.shields.io/badge/Deployed%20on-Streamlit%20Cloud-FF4B4B?logo=streamlit&logoColor=white)](https://meal-plan-generator23.streamlit.app)

---

## ✨ Features
- EN/SR language switch
- Profiles: **Cut / Maintain / Bulk** (auto-adjust kcal and macros)
- Allergens & dislikes filtering (by tags, groups, or names)
- 1–14 day plans, 2–6 meals/day
- Single-file **HTML export** (easy to share)
- Clean, pastel **JV Fit** branding

## 🧠 Tech Stack
**Python**, **Streamlit**, **JSON**, **HTML** export

## 🚀 Live Demo
Open the app here: **https://meal-plan-generator23.streamlit.app**

## 🖼️ Preview
Add a screenshot to `images/app_preview.png` and it will show here:

![JV Fit App Preview](images/app_preview.png)

## 🛠️ Run Locally
```bash
python3 -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```

## 📤 Deploy
- Push this folder to GitHub
- Go to https://share.streamlit.io → New app → pick your repo → `app.py`
- Streamlit builds automatically and gives you a public URL

## 🔗 Custom Subdomain
On Streamlit Cloud: **Manage app → Settings → Advanced → Custom subdomain**  
Example: `jvfit-mealplan` → https://jvfit-mealplan.streamlit.app

---

**Author:** Jelena Vučetić · [GitHub](https://github.com/vucko23)
