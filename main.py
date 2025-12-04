# main.py - Fokus: FastAPI API + Enqueue ke queue
from fastapi import FastAPI, UploadFile, File, Body, HTTPException
from fastapi.responses import JSONResponse
import tempfile
import os
import shutil
import uuid
from pathlib import Path
import json
from tasks import celery, summarize_pdf_task  # Import dari tasks.py

app = FastAPI(title="PDF Summarizer API (Async)")

@app.post("/summarize/upload")
async def summarize_upload(file: UploadFile = File(...)):
    if not file.filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="File harus PDF!")
    
    job_id = str(uuid.uuid4())
    # Simpan temp file
    with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp:
        shutil.copyfileobj(file.file, tmp)
        temp_path = tmp.name
    
    # Enqueue task (non-blocking)
    task = summarize_pdf_task.delay(temp_path, job_id, file.filename, is_url=False)
    return JSONResponse(content={"job_id": job_id, "status": "queued", "task_id": task.id})

@app.post("/summarize/url")
async def summarize_url(data: dict = Body(...)):
    url = data.get("url")
    if not url or not url.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Harus ada 'url' PDF di body!")
    
    job_id = str(uuid.uuid4())
    # Download dan simpan temp (sama seperti asli)
    import requests
    try:
        r = requests.get(url, stream=True)
        r.raise_for_status()
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp:
            shutil.copyfileobj(r.raw, tmp)
            temp_path = tmp.name
    except requests.RequestException as e:
        raise HTTPException(status_code=400, detail=f"Error download: {e}")
    
    # Enqueue
    task = summarize_pdf_task.delay(temp_path, job_id, None, is_url=True)
    return JSONResponse(content={"job_id": job_id, "status": "queued", "task_id": task.id})

@app.get("/status/{job_id}")
async def get_status(job_id: str):
    # Poll dari Celery atau file (contoh pakai file seperti repo asli)
    task = celery.AsyncResult(job_id)  # Atau pakai task_id jika beda
    output_file = Path("hasil_summary") / f"{job_id}.json"
    
    if task.state == 'PENDING':
        return {"status": "processing", "job_id": job_id}
    elif task.state == 'SUCCESS':
        if output_file.exists():
            with open(output_file, 'r', encoding='utf-8') as f:
                result = json.load(f)
            return {"status": "done", **result}
        else:
            return {"status": "done", "message": "Result ready, check file"}
    elif task.state == 'FAILURE':
        return {"status": "error", "detail": str(task.info)}
    else:
        raise HTTPException(status_code=500, detail="Unknown status")

@app.get("/health")
async def health():
    return {"status": "OK"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)