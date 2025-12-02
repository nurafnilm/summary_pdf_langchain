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
### B. Ringkasan PDF (keseluruhan termasuk gambar) berbasis teks yang dibuat menggunakan LangChain, serta integrasi dengan FastAPI.

### Setup
1. tambah `uv add fastapi uvicorn requests`
2. `uv sync`
3. `uv run uvicorn main:app --reload`

### Files 
- `main.py`: Kode utama
- `pdf/`: Sample files (artikel_bunga.pdf, artikel_pohon_gambar_url.txt)

### Hasil
Hasil summary pdf ada di folder `hasil_summary` format `.json`

### Proses percobaan
Akses link `http://127.0.0.1:8000/docs`
<img width="1919" height="1011" alt="Screenshot 2025-12-02 163341" src="https://github.com/user-attachments/assets/5f052b5f-1771-42f4-a5d9-8ba1cf5d2651" />

#### Upload PDF
<img width="1919" height="1012" alt="Screenshot 2025-12-02 161024" src="https://github.com/user-attachments/assets/2d9720fe-1947-4321-a634-d4c9dcf794af" />
<img width="1919" height="1017" alt="Screenshot 2025-12-02 161049" src="https://github.com/user-attachments/assets/83a18b5e-8445-4b32-8395-2d284447699e" />

#### Upload URL
<img width="1919" height="1010" alt="Screenshot 2025-12-02 160912" src="https://github.com/user-attachments/assets/27a61681-27b3-41b5-9de8-d1e56218ebd0" />
<img width="1919" height="1016" alt="Screenshot 2025-12-02 160959" src="https://github.com/user-attachments/assets/4fd008d9-f14a-4a61-8ad1-de627a4903e0" />



