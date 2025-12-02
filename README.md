# Summarize PDF dengan Langchain dan API dari GoogleAI Studio

Proyek buat summarize PDF pake Google Gemini via LangChain.

## A. Fokus di summary teks saja
Code Python ada di sum.py

### Setup
1. `uv add langchain langchain-google-genai langchain-core python-dotenv langchain-community pypdf`
2. `uv sync`
3. Buat `.env`: `GOOGLE_API_KEY=your_key`
4. `uv run sum.py`

### Files
- `sum.py`: Kode utama .
- `pdf/`: Sample files (laporan_cuaca.pdf, artikel_bunga.pdf).

### Hasil
Hasil summary pdf yang didapat ada di folder `hasil_summary` format `.txt`

`update`
### B. Ringkasan berbasis teks yang dibuat menggunakan LangChain, pemrosesan gambar melalui SDK Google Generative AI, serta integrasi backend dengan FastAPI.

### Setup
1. tambah `uv add fastapi uvicorn python-multipart requests`
2. tambah `uv pip google-generativeai` (soalnya uv add ga bisa)
3. `uv sync`
4. `uv run uvicorn main:app --reload`

### Files 
- `main.py`: Kode utama
- `pdf/`: Sample files (artikel_bunga.pdf, artikel_kucing_url.txt)

### Hasil
Hasil summary pdf ada di folder `hasil_summary`format `.json`

### Proses percobaan
Akses link `http://127.0.0.1:8000/docs`
<img width="1919" height="1012" alt="Screenshot 2025-12-02 113022" src="https://github.com/user-attachments/assets/aaa728ac-0603-45d0-9ed4-02b5fb3ba25a" />

#### Upload PDF
<img width="1919" height="1011" alt="Screenshot 2025-12-02 113235" src="https://github.com/user-attachments/assets/e220c1a1-8a6a-465b-b49d-edbba4b9c6a5" />
<img width="1919" height="1011" alt="Screenshot 2025-12-02 113257" src="https://github.com/user-attachments/assets/e4d2a8ae-7c7f-4ee8-8fa9-23fd757a9d4b" />

#### Upload URL
<img width="1919" height="1013" alt="Screenshot 2025-12-02 113422" src="https://github.com/user-attachments/assets/f21f19b0-ce5d-4af4-9efe-b442c2ad5435" />
<img width="1919" height="1015" alt="Screenshot 2025-12-02 113443" src="https://github.com/user-attachments/assets/cde6941b-f8b0-4266-b2fc-dc88172c9ac7" />







