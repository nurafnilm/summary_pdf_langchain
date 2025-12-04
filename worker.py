# worker.py - Full Redis Consumer untuk PDF Summarization dengan LangChain + Gemini
import json
import os
import time
from pathlib import Path
from dotenv import load_dotenv
import redis
import psycopg2  # Tambah buat DB
from typing import Dict, Any
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_community.document_loaders import PyMuPDFLoader
from langchain_core.messages import HumanMessage
import base64  # Buat handle images kalau ada

load_dotenv()
if "GOOGLE_API_KEY" not in os.environ:
    raise ValueError("Error: GOOGLE_API_KEY gak ditemukan di .env!")

# Prompt template (copy dari repo asli)
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

# Init Redis client
r = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True, health_check_interval=30)

# Init LangChain model (global, biar efisien)
try:
    llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0.1)  # Ganti model kalau perlu
except Exception as e:
    raise ValueError(f"Error init Gemini model: {e}")

# Global DB connection
conn = psycopg2.connect("host=localhost dbname=pdf_summary user=postgres password=pass123 port=5432")

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

def process_pdf(tmp_path: Path) -> Dict[str, Any]:
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
        raise ValueError(f"Error process PDF: {e}")

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

def process_job():
    """Proses satu job dari Redis queue."""
    job_json = r.rpop('pdf_jobs')
    if job_json is None:
        return None  # Kosong, skip
    
    try:
        job_data = json.loads(job_json)
        job_id = job_data['job_id']
        pdf_path = job_data['pdf_path']
        filename = job_data.get('filename', 'unknown.pdf')
        
        # Fix: Normalisasi & absolute path
        pdf_path = os.path.normpath(pdf_path)  # Fix backslash
        pdf_path = os.path.abspath(pdf_path)   # Buat full absolute
        print(f"Original path: {job_data['pdf_path']}")  # Debug
        print(f"Normalized path: {pdf_path}")  # Debug - harus full D:\...
        
        # Cek file ada gak
        if not os.path.exists(pdf_path):
            raise ValueError(f"File not found at {pdf_path}")
        
        print(f"Processing job {job_id}: {filename} from {pdf_path}")
        
        result = process_pdf(Path(pdf_path))
        
        # Simpan result ke file JSON (tetep, buat backup)
        output_dir = Path("hasil_summary")
        output_dir.mkdir(exist_ok=True)
        output_file = output_dir / f"{job_id}.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump({
                **result,
                "filename": filename,
                "job_id": job_id,
                "source": "url" if job_data.get("is_url", False) else "upload",
                "processed_at": time.strftime("%Y-%m-%d %H:%M:%S")
            }, f, ensure_ascii=False, indent=2)
        
        # Update DB dengan result
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE summaries 
                SET pages = %s, summary = %s 
                WHERE job_id = %s
            """, (result["pages"], json.dumps({
                "summary": result["summary"],
                "pages": result["pages"],
                "text_length": result["text_length"],
                "filename": filename,
                "job_id": job_id,
                "source": "url" if job_data.get("is_url", False) else "upload"
            }), job_id))
            cur.execute("SELECT 1 FROM summaries WHERE job_id = %s", (job_id,))  # Test if updated
            if cur.fetchone():
                print(f"DB updated successfully for job {job_id}")
            else:
                print(f"DB update failed for job {job_id} - no row found")
        conn.commit()
        
        print(f"Summary done for {job_id}: Saved to {output_file.absolute()}")
        return True
    except json.JSONDecodeError as e:
        print(f"Error decoding job JSON: {e}")
        return False
    except Exception as e:
        print(f"Error processing job: {e}")
        return False
    finally:
        if 'pdf_path' in locals():
            safe_unlink(Path(pdf_path))

def main():
    """Main loop: Consume queue terus-menerus."""
    print('Worker started: Waiting for jobs from Redis queue "pdf_jobs"...')
    print(f'Gemini model: {llm.model}')
    
    # Test Redis connect
    try:
        r.ping()
        print("Redis connected OK.")
    except Exception as e:
        raise ValueError(f"Redis connection failed: {e}")
    
    try:
        while True:
            try:
                success = process_job()
                if success is None:  # Queue kosong
                    time.sleep(1)  # Poll interval
            except KeyboardInterrupt:
                print("\nWorker stopped by user.")
                break
            except Exception as e:
                print(f"Unexpected error in loop: {e}")
                time.sleep(5)  # Backoff kalau crash
    finally:
        conn.close()  # Tutup DB connection

if __name__ == '__main__':
    main()