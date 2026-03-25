# HSC Pipeline — Developmental Stage Classification

Interactive web app for classifying HSCs across developmental stages using scRNA-seq gene signature scorecards.

Upload → run → explore dot plot & UMAP. No data is saved — all results are in-memory and gone on refresh.

## Architecture

```
Vercel  — frontend (Vite static build, CDN-served)
Railway — backend  (FastAPI Docker container, persistent process)
```

The frontend calls the Railway backend via `VITE_API_URL`.

---

## Deployment

### Step 1 — Push to GitHub

```powershell
cd C:\Users\nphuc\Coding\hsc-pipeline
git init
git add .
git commit -m "initial commit"
gh repo create hsc-pipeline --public --push --source=.
```

---

### Step 2 — Deploy backend to Railway

1. Go to [railway.app](https://railway.app) → **New Project** → **Deploy from GitHub repo**
2. Select your `hsc-pipeline` repo
3. Railway detects the root `Dockerfile` automatically — hit **Deploy**
4. Wait for the build (~10 min first time; scanpy is large)
5. Go to **Settings → Networking → Generate Domain**
6. Copy the URL — it looks like `https://hsc-pipeline-production.up.railway.app`

---

### Step 3 — Deploy frontend to Vercel

1. Go to [vercel.com](https://vercel.com) → **New Project** → import `hsc-pipeline`
2. In the **Configure Project** screen set:
   - **Root Directory** → `frontend`
   - Framework Preset → Vite (auto-detected)
3. Under **Environment Variables** add:
   ```
   VITE_API_URL = https://hsc-pipeline-production.up.railway.app
   ```
   (use your actual Railway URL from Step 2)
4. Click **Deploy**

The frontend is now live at `https://hsc-pipeline.vercel.app` (or similar).

---

### Step 4 — Lock down CORS (optional but recommended)

In Railway → your service → **Variables**, set:
```
ALLOWED_ORIGINS = https://hsc-pipeline.vercel.app
```

---

## Local development

```powershell
# Terminal 1 — backend
cd backend
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# Terminal 2 — frontend (proxies /api → localhost:8000)
cd frontend
npm install
npm run dev
# open http://localhost:5173
```

No `VITE_API_URL` needed locally — the Vite proxy handles it.

---

## Supported input formats

| Format | Extension |
|---|---|
| CSV count matrix | `.csv`, `.csv.gz` |
| 10X HDF5 | `.h5` |
| 10X MTX directory | `.tar.gz` of dir |

CSV layout: genes × cells (rows = genes). Transposed automatically.

---

## Gene signatures

- **Nascent HSC** (42 genes) — Calvanese et al. *Nature* 2022 + Sommarin et al. *Blood Advances* 2023
- **HSC Maturation** (50 genes) — Zheng et al. *Cell Stem Cell* 2022

Developmental order: AGM (4–5 wk) → Fetal Liver (CS16–CS22) → Bone Marrow (PCW10–14) → Spleen (12–14 wk)
