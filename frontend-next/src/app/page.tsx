'use client';

import { useState, FormEvent, ChangeEvent, useRef } from 'react';
import axios from 'axios';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

interface SummaryResult {
  jobId: string;
  filename: string;
  pages: number;
  source: string;
  summary: string;
  status: 'processing' | 'done' | 'error';
  error?: string;
}

export default function Home() {
  const [file, setFile] = useState<File | null>(null);
  const [selectedFileName, setSelectedFileName] = useState<string>('');
  const [url, setUrl] = useState<string>('');
  const [results, setResults] = useState<SummaryResult[]>([]);
  const [isExpanded, setIsExpanded] = useState<boolean[]>([]);
  const [error, setError] = useState<string>('');
  const [navOpen, setNavOpen] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const API_BASE = 'http://localhost:8080';

  const scrollToMain = () => {
    document.getElementById('main')?.scrollIntoView({ behavior: 'smooth' });
    setNavOpen(false);
  };

  const handleSubmit = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setError('');

    try {
      let response;
      let filename = '';
      let source = '';
      if (file) {
        const formData = new FormData();
        formData.append('file', file);
        response = await axios.post(`${API_BASE}/upload-pdf`, formData, {
          headers: { 'Content-Type': 'multipart/form-data' },
        });
        filename = file.name;
        source = 'upload';
      } else if (url) {
        response = await axios.post(`${API_BASE}/upload-url`, { url });
        filename = new URL(url).pathname.split('/').pop() || 'unknown.pdf';
        source = 'url';
      } else {
        setError('Pilih file atau masukkan URL dulu!');
        return;
      }

      const { job_id } = response.data;
      const newIndex = results.length;
      setResults(prev => [...prev, {
        jobId: job_id,
        filename,
        pages: 0,
        source,
        summary: '',
        status: 'processing',
      }]);
      setIsExpanded(prev => [...prev, false]);
      pollStatus(job_id, newIndex);
    } catch (err: unknown) {
      const errorMsg = (err as any).response?.data?.error || 'Error submit!';
      setError(errorMsg);
    }
  };

  const handleFileButtonClick = () => {
    fileInputRef.current?.click();
  };

  const handleFileChange = (e: ChangeEvent<HTMLInputElement>) => {
    const newFile = e.target.files?.[0] || null;
    setFile(newFile);
    if (newFile) {
      setSelectedFileName(newFile.name);
      setUrl('');  // Clear URL (exclusive)
    } else {
      setSelectedFileName('');
    }
  };

  const handleUrlChange = (e: ChangeEvent<HTMLInputElement>) => {
    const newUrl = e.target.value;
    setUrl(newUrl);
    if (newUrl) {
      setFile(null);  // Clear file (exclusive)
      setSelectedFileName('');
    }
  };

  const clearFile = () => {
    setFile(null);
    setSelectedFileName('');
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  const pollStatus = (id: string, index: number) => {
    const interval = setInterval(async () => {
      try {
        const res = await axios.get(`${API_BASE}/status/${id}`);
        if (res.data.status === 'done') {
          const parsedResult = JSON.parse(res.data.result);
          setResults(prev => prev.map((r, i) => i === index 
            ? { ...r, ...parsedResult, status: 'done' } 
            : r
          ));
          clearInterval(interval);
        } else if (res.data.status === 'error') {
          setResults(prev => prev.map((r, i) => i === index 
            ? { ...r, status: 'error', error: res.data.detail || 'Error proses!' } 
            : r
          ));
          clearInterval(interval);
        }
      } catch (err: unknown) {
        setResults(prev => prev.map((r, i) => i === index 
          ? { ...r, status: 'error', error: 'Error poll status!' } 
          : r
        ));
        clearInterval(interval);
      }
    }, 2000);
  };

  const toggleExpanded = (index: number) => {
    setIsExpanded(prev => prev.map((expanded, i) => i === index ? !expanded : expanded));
  };

  const downloadSummary = (result: SummaryResult) => {
    const content = `# Summary PDF: ${result.filename}

**Pages:** ${result.pages}
**Source:** ${result.source}

**Summary:**
${result.summary}

Generated on ${new Date().toLocaleString('id-ID')}`;
    const blob = new Blob([content], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `summary-${result.filename.replace('.pdf', '')}.txt`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="min-h-screen bg-gray-100">
      {/* Header Fixed - Responsive */}
      <header className="fixed top-0 w-full bg-white shadow-md z-50">
        <nav className="max-w-6xl mx-auto px-4 py-4">
          <div className="flex justify-between items-center">
            <div className="text-2xl font-bold text-blue-900">PDF Summary</div>
            <button
              className="lg:hidden"
              onClick={() => setNavOpen(!navOpen)}
            >
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
              </svg>
            </button>
            <ul className={`lg:flex lg:space-x-6 absolute lg:static top-full left-0 w-full lg:w-auto bg-white lg:bg-transparent shadow-md lg:shadow-none ${navOpen ? 'block' : 'hidden'}`}>
              <li><a href="#hero" className="block px-4 py-2 text-blue-900 hover:text-blue-700 lg:inline-block" onClick={() => setNavOpen(false)}>Home</a></li>
              <li><a href="#main" className="block px-4 py-2 text-blue-900 hover:text-blue-700 lg:inline-block" onClick={() => setNavOpen(false)}>Upload</a></li>
            </ul>
          </div>
        </nav>
      </header>

      {/* Hero Section - Background White, Text Dark Blue */}
      <section id="hero" className="h-screen flex items-center justify-center bg-white text-blue-900 pt-16">
        <div className="text-center max-w-4xl mx-auto px-4">
          <h1 className="text-5xl md:text-6xl font-bold mb-4 text-blue-900">Summary PDF</h1>
          <p className="text-lg md:text-xl mb-8 text-blue-900">Tools untuk meringkas PDF dengan AI Gemini | Ada dua opsi: upload file PDF langsung atau masukkan url dengan akhiran .pdf | Ayo summary dan dapatkan insight cepat dan akurat.</p>
          <button
            onClick={scrollToMain}
            className="bg-blue-900 text-white px-8 py-4 rounded-full text-xl font-semibold hover:bg-blue-800 transition-colors shadow-lg"
          >
            Mulai
          </button>
        </div>
      </section>

      {/* Main Section - Background White */}
      <section id="main" className="py-20 bg-white pt-16">
        <div className="max-w-6xl mx-auto px-4">
          {/* Main Content - Form Selalu Tampil */}
          <div className="flex-1">
            <div className="bg-white rounded-lg shadow-md p-6 mb-6">
              <h2 className="text-2xl font-bold mb-4 text-blue-900">Mulai Summarize | Pilih PDF atau Link PDF</h2>
              <form onSubmit={handleSubmit} className="space-y-4">
                <div className="space-y-4">
                  <button
                    type="button"
                    onClick={handleFileButtonClick}
                    className="w-full bg-gray-50 text-gray-700 py-3 px-4 rounded border-2 border-dashed border-gray-300 hover:bg-gray-100 transition-colors flex items-center justify-center text-lg"
                  >
                    <svg className="w-6 h-6 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
                    </svg>
                    Upload PDF
                  </button>
                  <input
                    ref={fileInputRef}
                    type="file"
                    accept=".pdf"
                    onChange={handleFileChange}
                    className="hidden"
                  />
                  {selectedFileName && (
                    <div className="flex items-center justify-between text-sm text-gray-600 bg-gray-50 p-2 rounded">
                      <span>Terpilih: {selectedFileName}</span>
                      <button
                        type="button"
                        onClick={clearFile}
                        className="text-blue-500 hover:text-blue-700 text-xs"
                      >
                        Ubah
                      </button>
                    </div>
                  )}
                  <div className="text-center text-gray-500 text-sm">atau</div>
                  <input
                    type="url"
                    placeholder="https://example.com/document.pdf"
                    value={url}
                    onChange={handleUrlChange}
                    className="w-full p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                  />
                </div>
                <button
                  type="submit"
                  disabled={!file && !url}
                  className="w-full bg-blue-500 text-white py-3 rounded-lg hover:bg-blue-600 font-semibold transition-colors disabled:opacity-50"
                >
                  Submit & Summarize
                </button>
              </form>

              {error && (
                <div className="mt-2 p-2 bg-red-50 border border-red-200 rounded text-red-600 text-sm">
                  {error}
                </div>
              )}
            </div>

            {/* Results Cards */}
            <div className="space-y-4">
              {results.map((r, i) => (
                <div key={r.jobId} className="bg-white rounded-lg shadow-md p-6">
                  <div className="flex justify-between items-center mb-4">
                    <h3 className="text-xl font-bold text-blue-900">Job {i + 1}: {r.filename}</h3>
                    <span className={`px-3 py-1 rounded-full text-sm font-medium ${
                      r.status === 'done' ? 'bg-green-100 text-green-800' :
                      r.status === 'processing' ? 'bg-yellow-100 text-yellow-800' :
                      'bg-red-100 text-red-800'
                    }`}>
                      {r.status.toUpperCase()}
                    </span>
                  </div>

                  {r.status === 'processing' && (
                    <div className="w-full bg-gray-200 rounded-full h-2 mb-2">
                      <div className="bg-blue-600 h-2 rounded-full animate-pulse" style={{width: '60%'}}></div>
                    </div>
                  )}

                  {r.status === 'error' && (
                    <p className="text-red-600 mb-2">Error: {r.error}</p>
                  )}

                  {r.status === 'done' && (
                    <div className="space-y-2">
                      <p className="text-blue-900"><strong>Pages:</strong> {r.pages}</p>
                      <p className="text-blue-900"><strong>Source:</strong> {r.source}</p>
                      <div className="border-t pt-2">
                        <div className="flex justify-between items-start mb-2">
                          <strong className="text-blue-900">Summary:</strong>
                          <button
                            onClick={() => downloadSummary(r)}
                            className="ml-2 px-3 py-1 bg-green-500 text-white rounded hover:bg-green-600 text-sm font-medium transition-colors"
                          >
                            Download .txt
                          </button>
                        </div>
                        <div className="prose max-w-none prose-headings:text-blue-900 prose-strong:text-blue-900">
                          <ReactMarkdown remarkPlugins={[remarkGfm]}>
                            {r.summary.length > 200 && !isExpanded[i] ? `${r.summary.slice(0, 200)}...` : r.summary}
                          </ReactMarkdown>
                          {r.summary.length > 200 && (
                            <button
                              onClick={() => toggleExpanded(i)}
                              className="mt-2 text-blue-500 hover:underline text-sm"
                            >
                              {isExpanded[i] ? 'Sedikitnya' : 'Selengkapnya'}
                            </button>
                          )}
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              ))}
            </div>

            {results.length === 0 && (
              <div className="text-center text-gray-500 mt-8">
                <p>Belum ada summary. Silakan Upload PDF atau Masukkan Link PDF!</p>
              </div>
            )}
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="bg-gray-800 text-white py-6">
        <div className="max-w-6xl mx-auto px-4 text-center">
          <p>&copy; 2025 Made by NALM | Project PDF Summarizer Sarana.ai</p>
          <p className="text-sm opacity-75 mt-2">Built with Next.js, Golang, & LangChain</p>
        </div>
      </footer>
    </div>
  );
}

// Fungsi toggle expand per card
const toggleExpanded = (index: number, setIsExpanded: React.Dispatch<React.SetStateAction<boolean[]>>) => {
  setIsExpanded(prev => prev.map((expanded, i) => i === index ? !expanded : expanded));
};

// Fungsi download summary sebagai TXT
const downloadSummary = (result: SummaryResult) => {
  const content = `# Summary PDF: ${result.filename}

**Pages:** ${result.pages}
**Source:** ${result.source}

**Summary:**
${result.summary}

Generated on ${new Date().toLocaleString('id-ID')}`;
  const blob = new Blob([content], { type: 'text/plain' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `summary-${result.filename.replace('.pdf', '')}.txt`;
  a.click();
  URL.revokeObjectURL(url);
};