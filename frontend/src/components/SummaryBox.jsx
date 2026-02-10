import { useEffect, useRef } from 'react';
import 'quill/dist/quill.snow.css';
import Quill from 'quill';

function SummaryBox({ summary, totalArticles, loading }) {
  const editorRef = useRef(null);
  const quillRef = useRef(null);

  useEffect(() => {
    if (!editorRef.current || loading) return;

    // Initialize Quill only once
    if (!quillRef.current) {
      quillRef.current = new Quill(editorRef.current, {
        theme: 'snow',
        readOnly: true,
        modules: {
          toolbar: false
        }
      });
    }

    // Set content (convert plain text to Quill format)
    if (summary) {
      // Convert plain text with line breaks to HTML
      const htmlContent = summary
        .split('\n')
        .map(line => {
          line = line.trim();
          if (!line) return '<br>';
          
          // Check for numbered list (1. 2. 3.)
          if (/^\d+\./.test(line)) {
            return `<p><strong>${line}</strong></p>`;
          }
          
          // Check for header-like lines (all caps or ending with :)
          if (line.endsWith(':') || line === line.toUpperCase()) {
            return `<h3>${line}</h3>`;
          }
          
          return `<p>${line}</p>`;
        })
        .join('');

      quillRef.current.root.innerHTML = htmlContent;
    }
  }, [summary, loading]);

  return (
    <div className="bg-gradient-to-br from-blue-50 to-indigo-50 rounded-lg border border-blue-100 shadow-soft p-6 mb-8">
      <div className="flex items-center gap-2 mb-4">
        <span className="material-symbols-outlined text-blue-600">summarize</span>
        <h2 className="text-xl font-bold text-slate-900">Bản tin tổng hợp</h2>
        {loading ? (
          <span className="ml-auto text-xs bg-yellow-100 text-yellow-700 px-2 py-1 rounded-full font-medium animate-pulse">
            Đang tóm tắt...
          </span>
        ) : totalArticles ? (
          <span className="ml-auto text-xs bg-blue-100 text-blue-700 px-2 py-1 rounded-full font-medium">
            {totalArticles} bài
          </span>
        ) : null}
      </div>
      
      {loading ? (
        <div className="bg-white rounded-md border border-gray-200 p-8 text-center">
          <span className="material-symbols-outlined text-4xl text-blue-500 animate-spin">progress_activity</span>
          <p className="text-slate-600 mt-4">AI đang phân tích và tóm tắt các bài báo...</p>
        </div>
      ) : (
        <>
          <div className="bg-white rounded-md border border-gray-200">
            <div 
              ref={editorRef} 
              className="prose prose-slate max-w-none"
              style={{ 
                minHeight: '200px',
                fontSize: '15px',
                lineHeight: '1.7'
              }}
            />
          </div>
          
          <div className="mt-4 flex items-center gap-4">
            <button className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-md text-sm font-medium transition-colors group shadow-sm">
              <span className="material-symbols-outlined text-lg">volume_up</span>
              Nghe bản tin
            </button>
            <button className="flex items-center gap-2 px-4 py-2 bg-white hover:bg-gray-50 text-slate-700 border border-gray-200 rounded-md text-sm font-medium transition-colors">
              <span className="material-symbols-outlined text-lg">content_copy</span>
              Sao chép
            </button>
          </div>
        </>
      )}
    </div>
  );
}

export default SummaryBox;
