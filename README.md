# HSC Pipeline — Developmental Stage Classification

Interactive web app for classifying HSCs across developmental stages using scRNA-seq gene signature scorecards.

Upload → run → explore dot plot & UMAP. No data is saved — all results are in-memory and gone on refresh.

## Architecture

```
Vercel — frontend  (Vite static build, CDN-served)
Modal  — backend   (FastAPI web endpoint + pipeline worker)
```

The frontend calls the Modal web endpoint via `VITE_API_URL`.

---

## Deployment

### Step 1 — Deploy backend to Modal

Modal is already installed on your machine. In PowerShell:

```powershell
cd C:\Users\nphuc\Coding\hsc-pipeline
pip install modal          # if not already installed
modal setup                # authenticate (opens browser)
modal deploy modal_app.py  # deploy — takes ~5 min first time (builds image)
```

After deploy, Modal prints your web endpoint URL:
```
✓ Created web endpoint: https://neophuchane--hsc-pipeline-web.modal.run
```
Copy that URL.

To test before deploying permanently:
```powershell
modal serve modal_app.py   # temporary URL, live reloads on file save
```

---

### Step 2 — Deploy frontend to Vercel

1. Go to [vercel.com](https://vercel.com) → **New Project** → import `neophuchane/hsc-pipeline`
2. Set **Root Directory** → `frontend`
3. Under **Environment Variables** add:
   ```
   VITE_API_URL = https://neophuchane--hsc-pipeline-web.modal.run
   ```
   (use your actual Modal URL from Step 1)
4. Click **Deploy**

---

### Step 3 — Lock down CORS (optional)

In `railway.toml` or as a Modal secret, set:
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
