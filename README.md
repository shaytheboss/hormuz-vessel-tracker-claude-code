# hormuz-vessel-tracker-claude-code

# 🚢 Hormuz Vessel Tracker

מערכת אוטומטית לניטור תנועת ספינות במצרי הורמוז, מבוססת על נתוני AIS בזמן אמת.

## איך זה עובד

```
AISstream.io ──► collector.py ──► hormuz_ships.db ──► Streamlit App
                 (GitHub Action)    (ענף data)         (חינמי)
```

- פעמיים ביום, GitHub Actions מריץ את `collector.py` למשך 5 דקות
- הקולקטור מתחבר ל-AIS ואוסף מיקומי ספינות ממצרי הורמוז
- הנתונים נשמרים ב-SQLite בענף `data` של הריפו
- אפליקציית Streamlit קוראת את הקובץ ומציגה דשבורד אינטראקטיבי

**עלות: $0** — משתמש בחינמיות של GitHub Actions (300–420 דקות/חודש מתוך 2,000)

---

## הקמה מאפס

### 1. דרישות מוקדמות

- חשבון GitHub
- חשבון [AISstream.io](https://aisstream.io) (חינמי) — לקבלת API Token
- חשבון [Streamlit Community Cloud](https://streamlit.io/cloud) (חינמי)

### 2. יצירת ענף data

בדף הריפו ב-GitHub:
1. לחץ על הדרופדאון של הענפים (כתוב `main`)
2. הקלד `data` בשדה החיפוש
3. לחץ **"Create branch: data from main"**

### 3. הוספת ה-API Token ב-GitHub

ריפו → **Settings** → **Secrets and variables** → **Actions** → **New repository secret**

| שם | ערך |
|----|-----|
| `AIS_TOKEN` | הטוקן שלך מ-AISstream.io |

### 4. פריסה ב-Streamlit Cloud

1. היכנס ל-[share.streamlit.io](https://share.streamlit.io)
2. לחץ **"New app"**
3. בחר את הריפו הזה, ענף `main`, קובץ `app.py`
4. ב-**Advanced settings** → **Secrets**, הוסף:
   ```toml
   # לא נדרש לאפליקציה — הטוקן רק ל-collector
   ```
5. לחץ **Deploy**

### 5. הרצה ראשונה ידנית

ריפו → **Actions** → **Collect AIS Data** → **Run workflow**

לאחר שה-Action יסתיים (כ-7 דקות), הנתונים יופיעו באפליקציה.

---

## מבנה הפרויקט

```
hormuz-vessel-tracker/
├── app.py                          # אפליקציית Streamlit
├── collector.py                    # קולקטור AIS
├── requirements.txt                # תלויות Python
└── .github/
    └── workflows/
        └── collect.yml             # GitHub Action — פועל פעמיים ביום
```

**ענף `data`** (נפרד):
```
data/
└── hormuz_ships.db                 # מסד הנתונים המצטבר
```

---

## לוח הזמנים של האיסוף

ה-Action רץ אוטומטית:
- **06:00 UTC** (9:00 בישראל)
- **18:00 UTC** (21:00 בישראל)

ניתן גם להריץ ידנית דרך Actions → Run workflow.

---

## requirements.txt

```
streamlit
pandas
websocket-client
```

---

## שאלות נפוצות

**ה-Action נכשל — מה לעשות?**
בדוק שה-`AIS_TOKEN` הוגדר ב-Secrets, ושענף `data` קיים.

**האפליקציה לא מציגה נתונים?**
וודא שה-Action רץ לפחות פעם אחת בהצלחה (סימן ✅ ירוק ב-Actions).

**כמה דקות Actions אני צורך?**
כ-7 דקות לריצה × 2 ריצות ביום × 30 ימים = **~420 דקות/חודש** מתוך 2,000 החינמיות.
