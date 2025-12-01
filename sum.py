#key api
from dotenv import load_dotenv
import os

load_dotenv()

if "GOOGLE_API_KEY" not in os.environ:
    raise ValueError("Error: GOOGLE_API_KEY gak ditemukan di .env! Cek file-nya.")
print("API Key loaded from .env!")

#langchain gen ai summarize pdf
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_community.document_loaders import PyPDFLoader
from langchain_core.messages import HumanMessage
import pathlib

try:
    llm = ChatGoogleGenerativeAI( 
        model="gemini-2.5-flash",
        temperature=0.1  
    )
    print("Model berhasil diinisialisasi!")
except Exception as e:
    print(f"Error init model: {e}")
    exit(1)

filepath = pathlib.Path("D:\\maganghub\\summarize_pdf\\pdf\\artikel_bunga.pdf")
if not filepath.exists():
    print(f"Error: File {filepath} tidak ditemukan! Cek path-nya.")
    exit(1)
print(f"File PDF ditemukan: {filepath}")

# Ekstrak teks dari PDF
try:
    loader = PyPDFLoader(str(filepath))
    docs = loader.load()
    print(f"PDF punya {len(docs)} halaman.")

    # Concat semua teks (atau ambil ringkasan per halaman kalau terlalu panjang)
    full_text = "\n\n".join([doc.page_content for doc in docs])
    print(f"Panjang teks: {len(full_text)} karakter.")
except Exception as e:
    print(f"Error load PDF: {e}")
    exit(1)

prompt= (f"Kamu adalah AI pintar yang rajin membaca buku dan paham isi bacaannya, kamu suka merangkum informasi penting yang benar-benar ada di dokumen, kamu tidak mengarang bebas dan tidak berbohong, kamu jujur merangkum apa yang benar-benar ada di dokumen, berikut dokumen lengkapnya: {full_text}")

message = HumanMessage(content=prompt)

# Generate response
try:
    response = llm.invoke([message])
    print("Summary:\n", response.content)
except Exception as e:
    print("Error generate response: {e}")