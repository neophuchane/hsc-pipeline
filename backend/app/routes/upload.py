"""
POST /api/upload         — small files (<25 MB) direct upload
POST /api/upload/chunk   — one chunk of a large file
POST /api/upload/finalize — reassemble chunks into a complete upload
"""

import hashlib
import io
import json
import logging
import os
import shutil
import tarfile
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from app.models import UploadResponse, UploadedFile

router = APIRouter()
logger = logging.getLogger(__name__)

UPLOAD_DIR = Path(os.environ.get("UPLOAD_DIR", "/tmp/hsc_uploads"))
MAX_FILE_SIZE = int(os.environ.get("MAX_FILE_SIZE_MB", "2000")) * 1024 * 1024
STAGING_DIR = UPLOAD_DIR / "_staging"


def _detect_format(filename: str) -> str:
    name = filename.lower()
    if name.endswith(".csv") or name.endswith(".csv.gz"):
        return "csv"
    if name.endswith(".h5"):
        return "h5"
    if name.endswith(".tar.gz") or name.endswith(".tgz"):
        return "mtx"
    raise HTTPException(
        status_code=400,
        detail=f"Unsupported file: {filename}. Accepted: .csv, .csv.gz, .h5, .tar.gz",
    )


def _file_id(content: bytes, filename: str) -> str:
    return hashlib.sha1(content[:4096] + filename.encode()).hexdigest()[:16]


def _sample_name_from(filename: str) -> str:
    """Strip extensions to get a clean sample name."""
    stem = Path(filename).stem          # removes last extension (.gz → .tar)
    if stem.endswith(".tar"):
        stem = stem[:-4]                # strip .tar
    if stem.endswith(".csv"):
        stem = stem[:-4]
    return stem


def _save_upload(content: bytes, filename: str) -> tuple[str, str, str]:
    """
    Persist uploaded bytes and return (file_id, fmt, path_for_pipeline).
    For tar.gz archives: extracts to a directory and returns the dir path.
    For everything else: writes the raw file and returns the file path.
    """
    fmt = _detect_format(filename)
    file_id = _file_id(content, filename)

    if fmt == "mtx":
        dest_dir = UPLOAD_DIR / file_id
        dest_dir.mkdir(exist_ok=True)
        with tarfile.open(fileobj=io.BytesIO(content), mode="r:gz") as tar:
            for member in tar.getmembers():
                if ".." in member.name or member.name.startswith("/"):
                    raise HTTPException(400, "Unsafe archive path detected")
            tar.extractall(dest_dir)
        path = str(dest_dir)
    else:
        dest = UPLOAD_DIR / f"{file_id}_{filename}"
        dest.write_bytes(content)
        path = str(dest)

    return file_id, fmt, path


# ---------------------------------------------------------------------------
# Direct upload (small files)
# ---------------------------------------------------------------------------

@router.post("/upload", response_model=UploadResponse)
async def upload_files(
    files: list[UploadFile] = File(...),
    sample_names: Annotated[str, Form()] = "",
) -> UploadResponse:
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

    names_list = [s.strip() for s in sample_names.split(",") if s.strip()] if sample_names else []
    uploaded: list[UploadedFile] = []

    for i, upload in enumerate(files):
        sample_name = names_list[i] if i < len(names_list) else _sample_name_from(upload.filename or "file")

        content = await upload.read()
        if len(content) > MAX_FILE_SIZE:
            raise HTTPException(413, f"{upload.filename} exceeds {MAX_FILE_SIZE // (1024**2)} MB limit")

        file_id, fmt, _ = _save_upload(content, upload.filename or "")

        uploaded.append(UploadedFile(
            file_id=file_id,
            filename=upload.filename or "",
            sample_name=sample_name,
            format=fmt,
            size_bytes=len(content),
        ))
        logger.info("Uploaded %s (fmt=%s, sample=%s)", upload.filename, fmt, sample_name)

    from app import modal_context
    if modal_context.volume_commit is not None:
        modal_context.volume_commit()

    return UploadResponse(files=uploaded)


# ---------------------------------------------------------------------------
# Chunked upload — one chunk at a time
# ---------------------------------------------------------------------------

@router.post("/upload/chunk")
async def upload_chunk(
    file: UploadFile = File(...),
    upload_id: str = Form(...),
    chunk_index: int = Form(...),
    total_chunks: int = Form(...),
    filename: str = Form(...),
) -> dict:
    """Receive one chunk of a large file. Commit to volume after each chunk."""
    STAGING_DIR.mkdir(parents=True, exist_ok=True)
    session_dir = STAGING_DIR / upload_id
    session_dir.mkdir(exist_ok=True)

    content = await file.read()
    (session_dir / f"chunk_{chunk_index:04d}").write_bytes(content)

    # Persist metadata on the first chunk
    if chunk_index == 0:
        (session_dir / "meta.json").write_text(
            json.dumps({"filename": filename, "total_chunks": total_chunks})
        )

    logger.info("Chunk %d/%d received for upload_id=%s", chunk_index + 1, total_chunks, upload_id)

    # Commit so other containers can see this chunk
    from app import modal_context
    if modal_context.volume_commit is not None:
        modal_context.volume_commit()

    return {"received": chunk_index, "total": total_chunks}


# ---------------------------------------------------------------------------
# Finalize — reassemble chunks and process like a normal upload
# ---------------------------------------------------------------------------

@router.post("/upload/finalize", response_model=UploadResponse)
async def finalize_upload(
    upload_id: str = Form(...),
    sample_name: str = Form(""),
) -> UploadResponse:
    """Reassemble all chunks for upload_id and process into the pipeline-ready format."""
    from app import modal_context

    # Reload volume so we see chunks written by other containers
    if modal_context.volume_reload is not None:
        modal_context.volume_reload()

    session_dir = STAGING_DIR / upload_id
    meta_path = session_dir / "meta.json"
    if not meta_path.exists():
        raise HTTPException(400, f"No upload session found: {upload_id}")

    meta = json.loads(meta_path.read_text())
    filename: str = meta["filename"]
    total_chunks: int = meta["total_chunks"]

    chunks = [session_dir / f"chunk_{i:04d}" for i in range(total_chunks)]
    missing = [i for i, c in enumerate(chunks) if not c.exists()]
    if missing:
        raise HTTPException(400, f"Missing chunks {missing} for upload_id={upload_id}")

    logger.info("Reassembling %d chunks for %s", total_chunks, filename)
    content = b"".join(c.read_bytes() for c in chunks)

    # Clean up staging
    shutil.rmtree(session_dir, ignore_errors=True)

    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    file_id, fmt, _ = _save_upload(content, filename)

    if not sample_name:
        sample_name = _sample_name_from(filename)

    logger.info("Finalized %s (fmt=%s, sample=%s, size=%d B)", filename, fmt, sample_name, len(content))

    if modal_context.volume_commit is not None:
        modal_context.volume_commit()

    return UploadResponse(files=[UploadedFile(
        file_id=file_id,
        filename=filename,
        sample_name=sample_name,
        format=fmt,
        size_bytes=len(content),
    )])
