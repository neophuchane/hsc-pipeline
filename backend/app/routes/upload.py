"""
POST /api/upload — Accept multi-format file uploads into /tmp (ephemeral).
"""

import hashlib
import io
import logging
import os
import tarfile
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from app.models import UploadResponse, UploadedFile

router = APIRouter()
logger = logging.getLogger(__name__)

UPLOAD_DIR = Path(os.environ.get("UPLOAD_DIR", "/tmp/hsc_uploads"))
MAX_FILE_SIZE = int(os.environ.get("MAX_FILE_SIZE_MB", "2000")) * 1024 * 1024


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
        detail=f"Unsupported file: {filename}. Accepted: .csv, .csv.gz, .h5, .tar.gz (MTX dir)",
    )


def _file_id(content: bytes, filename: str) -> str:
    return hashlib.sha1(content[:4096] + filename.encode()).hexdigest()[:16]


@router.post("/upload", response_model=UploadResponse)
async def upload_files(
    files: list[UploadFile] = File(...),
    sample_names: Annotated[str, Form()] = "",
) -> UploadResponse:
    """
    Upload one or more count matrix files.

    Optional form field `sample_names`: comma-separated names matching file order.
    Files are stored in /tmp — ephemeral, cleared when the server restarts.
    """
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

    names_list = [s.strip() for s in sample_names.split(",") if s.strip()] if sample_names else []
    uploaded: list[UploadedFile] = []

    for i, upload in enumerate(files):
        fmt = _detect_format(upload.filename or "")
        sample_name = (
            names_list[i] if i < len(names_list)
            else Path(upload.filename or "file").stem.replace(".csv", "")
        )

        content = await upload.read()
        if len(content) > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=413,
                detail=f"{upload.filename} exceeds {MAX_FILE_SIZE // (1024**2)} MB limit",
            )

        file_id = _file_id(content, upload.filename or "")

        if fmt == "mtx":
            dest_dir = UPLOAD_DIR / file_id
            dest_dir.mkdir(exist_ok=True)
            with tarfile.open(fileobj=io.BytesIO(content), mode="r:gz") as tar:
                for member in tar.getmembers():
                    if ".." in member.name or member.name.startswith("/"):
                        raise HTTPException(400, "Unsafe archive path detected")
                tar.extractall(dest_dir)
        else:
            dest = UPLOAD_DIR / f"{file_id}_{upload.filename}"
            dest.write_bytes(content)

        uploaded.append(UploadedFile(
            file_id=file_id,
            filename=upload.filename or "",
            sample_name=sample_name,
            format=fmt,
            size_bytes=len(content),
        ))
        logger.info("Uploaded %s (fmt=%s, sample=%s)", upload.filename, fmt, sample_name)

    # On Modal: commit the volume so the pipeline worker can see the new files
    from app import modal_context
    if modal_context.volume_commit is not None:
        modal_context.volume_commit()

    return UploadResponse(files=uploaded)
