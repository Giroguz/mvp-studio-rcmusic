from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
import uuid
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

ROOT = Path(__file__).resolve().parent
WORK = ROOT / "jobs"
WORK.mkdir(exist_ok=True)
MAX_BYTES = 500 * 1024 * 1024
ALLOWED = {".mp3", ".wav", ".flac", ".m4a", ".ogg"}

app = FastAPI(title="MVP Studio RCmusic API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def safe_name(name: str) -> str:
    suffix = Path(name or "audio.wav").suffix.lower()
    if suffix not in ALLOWED:
        raise HTTPException(400, "Formato no compatible. Usa MP3, WAV, FLAC, M4A u OGG.")
    return f"source{suffix}"


@app.get("/api/health")
def health():
    try:
        import demucs  # noqa: F401
        engine = "demucs"
    except Exception:
        engine = "not-installed"
    return {"ok": True, "app": "MVP Studio RCmusic", "engine": engine}


@app.post("/api/separate")
async def separate(file: UploadFile = File(...), mode: str = "stems"):
    """Separate an uploaded file with Demucs.

    `mode=karaoke` produces vocals/no-vocals. Other modes produce the
    standard four stems (drums, bass, other, vocals).
    """
    try:
        source_name = safe_name(file.filename or "audio.wav")
        job_id = uuid.uuid4().hex[:12]
        job = WORK / job_id
        job.mkdir(parents=True, exist_ok=True)
        source = job / source_name
        size = 0
        with source.open("wb") as out:
            while chunk := await file.read(1024 * 1024):
                size += len(chunk)
                if size > MAX_BYTES:
                    shutil.rmtree(job, ignore_errors=True)
                    raise HTTPException(413, "El archivo supera el límite de 500 MB.")
                out.write(chunk)

        model = os.getenv("RCMUSIC_DEMUCS_MODEL", "htdemucs")
        args = [sys.executable, "-m", "demucs.separate", "-n", model, "-o", str(job / "separated")]
        if mode == "karaoke":
            args += ["--two-stems=vocals"]
        args += [str(source)]
        env = os.environ.copy()
        try:
            import imageio_ffmpeg
            ffmpeg_bin = Path(imageio_ffmpeg.get_ffmpeg_exe())
            env["PATH"] = f"{ffmpeg_bin.parent}{os.pathsep}{env.get('PATH', '')}"
        except Exception:
            pass
        run = subprocess.run(args, capture_output=True, text=True, timeout=60 * 45, env=env)
        if run.returncode != 0:
            detail = (run.stderr or run.stdout or "No se pudo separar el audio")[-1600:]
            raise HTTPException(500, detail)

        outputs = []
        for p in sorted((job / "separated").rglob("*.wav")):
            outputs.append({"name": p.name, "url": f"/api/files/{job_id}/{p.relative_to(job).as_posix()}"})
        if not outputs:
            raise HTTPException(500, "El motor terminó sin generar pistas.")
        return {"ok": True, "job_id": job_id, "mode": mode, "stems": outputs}
    except HTTPException:
        raise
    except subprocess.TimeoutExpired:
        raise HTTPException(504, "El procesamiento tardó demasiado. Prueba con un archivo más corto.")
    except Exception as exc:
        raise HTTPException(500, f"No se pudo procesar el archivo: {exc}")


@app.get("/api/files/{job_id}/{file_path:path}")
def get_file(job_id: str, file_path: str):
    base = (WORK / job_id).resolve()
    target = (base / file_path).resolve()
    if base not in target.parents or not target.is_file():
        raise HTTPException(404, "Archivo no encontrado")
    return FileResponse(target)
