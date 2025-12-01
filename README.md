# Summarize PDF dengan Langchain dan API dari GoogleAI Studio

Proyek buat summarize PDF pake Google Gemini via LangChain. Ada dua pdf yang bisa digunakan di sini.

## Setup
1. `uv add langchain langchain-google-genai langchain-core python-dotenv langchain-community pypdf`
2. `uv sync`
3. Buat `.env`: `GOOGLE_API_KEY=your_key`
4. `uv run sum.py`

## Files
- `sum.py`: Kode utama (ekstrak teks PDF & summarize).
- `pdf/`: Sample files (laporan_cuaca.pdf, artikel_bunga.pdf).

## Hasil
hasil summary pdf yang didapat ada di foler `hasil_summary`
