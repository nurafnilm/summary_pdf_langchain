from fastapi import FastAPI, UploadFile, File, Query, HTTPException, Body
from fastapi.responses import JSONResponse
import tempfile
import os
import shutil
from pathlib import Path
from dotenv import load_dotenv
import google.generativeai as genai  # SDK untuk multimodal gambar
import requests

# Load env
load_dotenv()
if "GOOGLE_API_KEY" not in os.environ:
    raise ValueError("Error: GOOGLE_API_KEY gak ditemukan di .env!")

# LangChain imports untuk teks
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_community.document_loaders import PyPDFLoader
from langchain_core.messages import HumanMessage

# Prompt template (plain string dengan placeholder, gak f-string)
PROMPT_TEMPLATE = """Anda adalah seorang reviewer makalah akademik yang luar biasa. Anda melakukan ringkasan makalah pada teks makalah lengkap yang disediakan oleh pengguna, Deskripsikan gambar/diagram jika ada di pdf, dengan instruksi berikut:
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

berikut dokumen lengkapnya: {full_text}"""

# Init SDK untuk gambar
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
model_sdk = genai.GenerativeModel("gemini-2.5-flash")

app = FastAPI(title="PDF Summarizer API", description="Summarize PDF dengan Gemini – Teks (LangChain) + Gambar (SDK Multimodal)")

# Init LangChain model untuk teks
try:
    llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0.1)
except Exception as e:
    raise HTTPException(status_code=500, detail=f"Error init model: {e}")

def generate_image_descriptions(tmp_path: Path) -> str:
    """Generate deskripsi gambar via SDK multimodal."""
    try:
        pdf_part = genai.upload_file(path=str(tmp_path), mime_type="application/pdf")
        image_prompt = f"""Deskripsikan seluruh gambar/diagram di PDF ini secara akurat & singkat sesuai dengan isi konteks dokumen.
                        Output hanya deskripsi, markdown."""
        response = model_sdk.generate_content([image_prompt, pdf_part])
        genai.delete_file(pdf_part.name)  # Cleanup
        return response.text
    except Exception as e:
        return f"Fallback: Error deskripsi gambar - {e}. Gunakan teks-only."

def process_pdf(tmp_path: Path) -> dict:
    """Function shared untuk process PDF (teks + gambar)."""
    try:
        # Step 1: Teks via LangChain
        loader = PyPDFLoader(str(tmp_path))
        docs = loader.load()
        full_text = "\n\n".join([doc.page_content for doc in docs])
        
        prompt = PROMPT_TEMPLATE.format(full_text=full_text)
        
        message = HumanMessage(content=prompt)
        text_response = llm.invoke([message])
        text_summary = text_response.content
        
        # Step 2: Gambar via SDK
        image_descriptions = generate_image_descriptions(tmp_path)
        
        # Gabung
        combined_summary = f"**Teks Summary:** {text_summary}\n\n**Gambar Descriptions:** {image_descriptions}"
        
        return {
            "combined_summary": combined_summary,
            "pages": len(docs),
            "text_length": len(full_text)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error process: {e}")

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
        tmp_path.unlink(missing_ok=True)

@app.post("/summarize/url")
async def summarize_url(data: dict = Body(..., example={"url": "https://example.com/file.pdf"})):
    url = data.get("url")
    if not url:
        raise HTTPException(status_code=400, detail="Harus ada 'url' di body JSON!")
    if not url.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="URL harus PDF!")
    
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
        if 'tmp_path' in locals():
            tmp_path.unlink(missing_ok=True)

@app.get("/health")
async def health():
    return {"status": "OK"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)