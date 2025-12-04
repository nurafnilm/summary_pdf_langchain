# tasks.py - Fokus: Celery tasks + LangChain summarization
from celery import Celery
from fastapi import HTTPException
import json
import os
from pathlib import Path
from dotenv import load_dotenv
import tempfile
import shutil
import time
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_community.document_loaders import PyMuPDFLoader
from langchain_core.messages import HumanMessage

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

# Init Celery (sesuaikan broker/ backend)
celery = Celery('tasks', broker='redis://localhost:6379/0', backend='redis://localhost:6379/0')

# Init LangChain model (global, biar efisien)
try:
    llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0.1)
except Exception as e:
    raise HTTPException(status_code=500, detail=f"Error init model: {e}")

def collect_images_from_docs(docs):
    """Collect all base64 images from document metadata."""
    all_images = []
    seen = set()
    for doc in docs:
        images = doc.metadata.get('images', [])
        for img_b64 in images:
            if img_b64 not in seen:
                all_images.append(img_b64)
                seen.add(img_b64)
    return all_images

def process_pdf(tmp_path: Path) -> dict:
    """Process PDF menggunakan PyMuPDFLoader (full teks + extract & encode gambar)."""
    try:
        loader = PyMuPDFLoader(str(tmp_path), extract_images=True)
        docs = loader.load()
        full_text = "\n\n".join([doc.page_content for doc in docs])
        all_images_b64 = collect_images_from_docs(docs)
        
        message_content = [{"type": "text", "text": PROMPT_TEMPLATE.format(full_text=full_text)}]
        for img_b64 in all_images_b64:
            message_content.append({"type": "image_url", "image_url": {"url": f"data:image/png;base64,{img_b64}"}})
        
        message = HumanMessage(content=message_content)
        response = llm.invoke([message])
        summary = response.content
        
        return {"summary": summary, "pages": len(docs), "text_length": len(full_text)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error process: {e}")

def safe_unlink(path: Path, max_retries: int = 5):
    """Retry unlink with delay."""
    for attempt in range(max_retries):
        try:
            path.unlink(missing_ok=True)
            return
        except PermissionError:
            if attempt < max_retries - 1:
                time.sleep(1)
            else:
                print(f"Warning: Could not delete {path} after {max_retries} attempts.")

@celery.task(bind=True, max_retries=3)
def summarize_pdf_task(self, pdf_path: str, job_id: str, filename: str = None, is_url: bool = False):
    """Celery task untuk summarization - ini yang fokus LangChain."""
    tmp_path = Path(pdf_path)
    try:
        result = process_pdf(tmp_path)
        
        # Simpan result ke file JSON
        output_dir = Path("hasil_summary")
        output_dir.mkdir(exist_ok=True)
        output_file = output_dir / f"{job_id}.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump({
                **result,
                "filename": filename,
                "job_id": job_id,
                "source": "url" if is_url else "upload"
            }, f, ensure_ascii=False, indent=2)
        
        return {"status": "success", "job_id": job_id, "output_file": str(output_file)}
    except Exception as exc:
        # Retry logic Celery
        raise self.retry(exc=exc, countdown=60)
    finally:
        safe_unlink(tmp_path)