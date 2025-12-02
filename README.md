# Summarize PDF dengan Langchain dan API dari GoogleAI Studio

Proyek buat summarize PDF pake Google Gemini via LangChain.

## Fokus di summary teks saja
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
### Ringkasan berbasis teks yang dibuat menggunakan LangChain, pemrosesan gambar melalui SDK Google Generative AI, serta integrasi backend dengan FastAPI.

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
#### Upload PDF
<img width="1920" height="1080" alt="Screenshot 2025-12-02 102620" src="https://github.com/user-attachments/assets/3f213a93-f370-4eba-858d-82d4a77ea735" />
<img width="1920" height="1080" alt="Screenshot 2025-12-02 103821" src="https://github.com/user-attachments/assets/de61968b-5ee9-48a8-bef4-ff065eb2e941" />
#### Upload Link
<img width="1920" height="1080" alt="Screenshot 2025-12-02 110008" src="https://github.com/user-attachments/assets/cbe71786-a2f5-42bc-815b-0c64ef322f62" />
<img width="1920" height="1080" alt="Screenshot 2025-12-02 110040" src="https://github.com/user-attachments/assets/03ef46fd-aee7-49e2-af28-ceff4714bf2c" />




