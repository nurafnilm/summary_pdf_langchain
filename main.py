# imports
from fastapi import FastAPI, UploadFile, File, Query, HTTPException, Body
from fastapi.responses import JSONResponse
import tempfile
import os
import shutil
from pathlib import Path
from dotenv import load_dotenv
import requests
import base64
import time
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_community.document_loaders import PyMuPDFLoader  # PyMuPDFLoader (support extract_images=True)
from langchain_core.messages import HumanMessage

# Load env
load_dotenv()
if "GOOGLE_API_KEY" not in os.environ:
    raise ValueError("Error: GOOGLE_API_KEY gak ditemukan di .env!")

# Prompt template
PROMPT_TEMPLATE = """Anda adalah seorang reviewer makalah akademik yang luar biasa. Anda melakukan ringkasan makalah pada teks makalah lengkap yang disajikan oleh pengguna. Deskripsikan gambar/diagram jika ada di pdf, dengan instruksi berikut:
INSTRUKSI REVIEW:
Ringkasan Pendekatan Teknis Makalah Akademik
1. Judul dan Penulis Makalah: Berikan judul dan penulis makalah.
2. Tujuan Utama dan Konsep Dasar: Mulailah dengan menyatakan secara jelas tujuan utama dari penelitian yang disajikan dalam makalah akademik. Gambarkan ide inti atau hipotesis yang mendasari studi tersebut dalam bahasa yang sederhana dan mudah diakses.
3. Pendekatan Teknis: Berikan penjelasan rinci tentang metodologi yang digunakan dalam penelitian. Fokus pada deskripsi bagaimana studi dilakukan, termasuk teknik, model, atau algoritma spesifik yang digunakan. Hindari membahas jargon rumit atau detail teknis yang sangat mendalam yang mungkin menyulitkan pemahaman.
4. Fitur Khas: Identifikasi dan jelaskan apa yang membedakan penelitian ini dari studi lain di bidang yang sama. Soroti teknik baru, aplikasi unik, atau metodologi inovatif yang berkontribusi pada keunikan penelitian ini.
5. Pengaturan Eksperimen dan Hasil: Gambarkan desain eksperimen dan proses pengumpulan data yang digunakan dalam studi. Ringkas hasil yang diperoleh atau temuan utama, dengan menekankan hasil atau penemuan signifikan apa pun.
6. Kelebihan dan Keterbatasan: Diskusikan secara ringkas kekuatan pendekatan yang diusulkan, termasuk manfaat apa pun yang ditawarkannya dibandingkan metode yang ada. Juga, bahas keterbatasannya atau potensi kekurangan, memberikan pandangan seimbang tentang efektivitas dan aplikabilitasnya.
7. Kesimpulan: Ringkas poin-poin utama tentang pendekatan teknis makalah, keunikannya, serta kelebihan dan keterbatasannya secara komparatif. Bidik kejelasan dan kekeringan dalam ringkasan Anda.
INSTRUKSI OUTPUT:
1. Header yang disediakan dalam instruksi di atas adalah opsi kedua, lebih fokus pada header sesuai isi makalah.
2. Format output Anda dalam Markdown yang jelas dan mudah dibaca oleh manusia.
3. Hanya output prompt tersebut, dan tidak ada yang lain, karena prompt tersebut mungkin dikirim langsung ke LLM.

berikut dokumen lengkapnya: {full_text}

Analisis juga seluruh gambar atau diagram yang disertakan sebagai bagian dari dokumen, taruh summarize terkait gambar sesuai dengan tempat konteks dokumennya."""

# FAST API
app = FastAPI(title="PDF Summarizer API", description="Summarize PDF dengan LangChain + PyMuPDFLoader (Teks + Gambar Multimodal)")

# Init LangChain model untuk multimodal
try:
    llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0.1)
except Exception as e:
    raise HTTPException(status_code=500, detail=f"Error init model: {e}")

def collect_images_from_docs(docs):
    """Collect all base64 images from document metadata."""
    all_images = []
    seen = set()  # Avoid duplicates
    for doc in docs:
        images = doc.metadata.get('images', [])
        for img_b64 in images:
            if img_b64 not in seen:
                all_images.append(img_b64)
                seen.add(img_b64)
    return all_images

def process_pdf(tmp_path: Path) -> dict:
    """Process PDF menggunakan PyMuPDFLoader (full teks + extract & encode gambar dari metadata)."""
    try:
        # Step 1: Load PDF dengan PyMuPDFLoader (ekstrak teks + images sebagai base64 di metadata)
        loader = PyMuPDFLoader(
            str(tmp_path),
            extract_images=True  # <-- Fixed: Hanya ini, images disimpan sebagai base64 di metadata['images']
        )
        docs = loader.load()
        full_text = "\n\n".join([doc.page_content for doc in docs])
        
        # Step 2: Collect all images from metadata
        all_images_b64 = collect_images_from_docs(docs)
        
        # Step 3: Siapkan multimodal message
        message_content = [
            {
                "type": "text",
                "text": PROMPT_TEMPLATE.format(full_text=full_text)
            }
        ]
        
        # Step 4: Tambah images sebagai base64 (PyMuPDF extract sebagai PNG)
        for img_b64 in all_images_b64:
            message_content.append({
                "type": "image_url",
                "image_url": {"url": f"data:image/png;base64,{img_b64}"}
            })
        
        # Step 5: Invoke LLM dengan multimodal content
        message = HumanMessage(content=message_content)
        response = llm.invoke([message])
        summary = response.content
        
        return {
            "summary": summary,
            "pages": len(docs),
            "text_length": len(full_text),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error process: {e}")
    finally:
        pass

def safe_unlink(path: Path, max_retries: int = 5):
    """Retry unlink with delay to handle Windows file locking."""
    for attempt in range(max_retries):
        try:
            path.unlink(missing_ok=True)
            return
        except PermissionError:
            if attempt < max_retries - 1:
                time.sleep(1)  # Wait 1 second before retry
            else:
                print(f"Warning: Could not delete {path} after {max_retries} attempts.")

@app.post("/summarize/upload")
async def summarize_upload(file: UploadFile = File(..., description="Upload PDF")):
    if not file.filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="File harus PDF!")
    
    # Simpan temp
    with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp:
        shutil.copyfileobj(file.file, tmp)
        tmp_path = Path(tmp.name)
    
    try:
        result = process_pdf(tmp_path)  # Shared function
        
        return JSONResponse(content={
            **result,
            "filename": file.filename
        })
    
    finally:
        safe_unlink(tmp_path)  # Fixed: Retry unlink

@app.post("/summarize/url")
async def summarize_url(data: dict = Body(..., example={"url": "https://example.com/file.pdf"})):
    url = data.get("url")
    if not url:
        raise HTTPException(status_code=400, detail="Harus ada 'url' di body JSON!")
    if not url.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="File harus PDF!")


    # Download dari URL
    try:
        r = requests.get(url, stream=True)
        r.raise_for_status()
        
        # Simpan temp
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp:
            shutil.copyfileobj(r.raw, tmp)
            tmp_path = Path(tmp.name)
        
        result = process_pdf(tmp_path)  # Shared function
        
        return JSONResponse(content={
            **result,
            "url": url
        })
    
    except requests.RequestException as e:
        raise HTTPException(status_code=400, detail=f"Error download URL: {e}")
    
    finally:
        safe_unlink(tmp_path)  # Fixed: Retry unlink

@app.get("/health")
async def health():
    return {"status": "OK"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)