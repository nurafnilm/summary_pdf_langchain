'use client';

import { useState, FormEvent, ChangeEvent } from 'react';
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
  const [option, setOption] = useState<'upload' | 'url'>('upload');
  const [file, setFile] = useState<File | null>(null);
  const [url, setUrl] = useState<string>('');
  const [results, setResults] = useState<SummaryResult[]>([]);
  const [isExpanded, setIsExpanded] = useState<boolean[]>([]);  // <-- Tambah state ini buat expand per card
  const [error, setError] = useState<string>('');

  const API_BASE = 'http://localhost:8080';

  const handleSubmit = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setError('');

    try {
      let response;
      if (option === 'upload') {
        if (!file) {
          setError('Pilih file PDF dulu!');
          return;
        }
        const formData = new FormData();
        formData.append('file', file);
        response = await axios.post(`${API_BASE}/upload-pdf`, formData, {
          headers: { 'Content-Type': 'multipart/form-data' },
        });
      } else {
        if (!url) {
          setError('Masukkan URL PDF dulu!');
          return;
        }
        response = await axios.post(`${API_BASE}/upload-url`, { url });
      }

      const { job_id } = response.data;
      // Tambah entry baru ke results (status processing dulu)
      setResults(prev => [...prev, {
        jobId: job_id,
        filename: option === 'upload' ? file!.name : new URL(url).pathname.split('/').pop() || 'unknown.pdf',
        pages: 0,
        source: option === 'upload' ? 'upload' : 'url',
        summary: '',
        status: 'processing',
      }]);
      // Update isExpanded buat card baru (default false)
      setIsExpanded(prev => [...prev, false]);
      pollStatus(job_id, results.length);  // Poll per entry baru
    } catch (err: unknown) {
      const errorMsg = (err as any).response?.data?.error || 'Error submit!';
      setError(errorMsg);
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

  // Fungsi toggle expand per card
  const toggleExpanded = (index: number) => {
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

  return (
    <div className="min-h-screen bg-gray-100 py-8">
      <div className="max-w-4xl mx-auto px-4">  {/* Lebarkan */}
        <div className="bg-white rounded-lg shadow-md p-6 mb-6">  {/* Form */}
          <h1 className="text-3xl font-bold text-center mb-6">PDF Summarizer</h1>
          
          <form onSubmit={handleSubmit} className="space-y-4">
            {/* Opsi Pilih */}
            <div className="flex space-x-6 justify-center">
              <label className="flex items-center space-x-2 cursor-pointer">
                <input
                  type="radio"
                  value="upload"
                  checked={option === 'upload'}
                  onChange={(e: ChangeEvent<HTMLInputElement>) => setOption(e.target.value as 'upload')}
                  className="form-radio text-blue-600"
                />
                <span className="text-lg">Upload File PDF</span>
              </label>
              <label className="flex items-center space-x-2 cursor-pointer">
                <input
                  type="radio"
                  value="url"
                  checked={option === 'url'}
                  onChange={(e: ChangeEvent<HTMLInputElement>) => setOption(e.target.value as 'url')}
                  className="form-radio text-blue-600"
                />
                <span className="text-lg">Input URL PDF</span>
              </label>
            </div>

            {/* Form Input */}
            {option === 'upload' ? (
              <input
                type="file"
                accept=".pdf"
                onChange={(e: ChangeEvent<HTMLInputElement>) => setFile(e.target.files?.[0] || null)}
                className="w-full p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                required
              />
            ) : (
              <input
                type="url"
                placeholder="https://example.com/document.pdf"
                value={url}
                onChange={(e: ChangeEvent<HTMLInputElement>) => setUrl(e.target.value)}
                className="w-full p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                required
              />
            )}

            <button
              type="submit"
              className="w-full bg-blue-500 text-white py-3 rounded-lg hover:bg-blue-600 font-semibold transition-colors"
            >
              Submit & Summarize
            </button>
          </form>

          {error && (
            <div className="mt-4 p-4 bg-red-50 border border-red-200 rounded-lg">
              <p className="text-red-600 font-medium">{error}</p>
            </div>
          )}
        </div>

        {/* History List Summary */}
        <div className="space-y-4">
          {results.map((r, i) => (
            <div key={r.jobId} className="bg-white rounded-lg shadow-md p-6">
              <div className="flex justify-between items-center mb-4">
                <h3 className="text-xl font-bold">Job {i + 1}: {r.filename}</h3>
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
                  <p><strong>Pages:</strong> {r.pages}</p>
                  <p><strong>Source:</strong> {r.source}</p>
                  <div className="border-t pt-2">
                    <div className="flex justify-between items-start mb-2">
                      <strong>Summary:</strong>
                      <button
                        onClick={() => downloadSummary(r)}
                        className="ml-2 px-3 py-1 bg-green-500 text-white rounded hover:bg-green-600 text-sm font-medium transition-colors"
                      >
                        Download TXT
                      </button>
                    </div>
                    <div className="prose max-w-none prose-headings:text-lg prose-strong:text-gray-800">
                      <ReactMarkdown remarkPlugins={[remarkGfm]}>
                        {r.summary.length > 200 && !isExpanded[i] ? `${r.summary.slice(0, 200)}...` : r.summary}
                      </ReactMarkdown>
                      {r.summary.length > 200 && (
                        <button
                          onClick={() => toggleExpanded(i)}
                          className="mt-2 text-blue-500 hover:underline text-sm"
                        >
                          {isExpanded[i] ? 'Tutup' : 'Selengkapnya'}
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
            <p>Belum ada summary. Coba submit PDF lo!</p>
          </div>
        )}
      </div>
    </div>
  );
}

// Fungsi toggle expand per card
const toggleExpanded = (index: number) => {
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