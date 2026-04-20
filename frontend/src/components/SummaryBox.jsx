import { useState } from 'react';

function SummaryBox({
  summary,
  totalArticles,
  loading,
  onResummarize,
  resummarizeDisabled = false,
  onGenerateTts,
  ttsStatus = 'idle',
  ttsAudioUrl = '',
  ttsError = '',
}) {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    if (!summary) return;
    try {
      await navigator.clipboard.writeText(summary);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 2000);
    } catch {
      setCopied(false);
    }
  };

  const renderedSummary = summary
    ?.split('\n')
    .map((line) => line.trim())
    .filter(Boolean);

  const hasSummary = renderedSummary?.length > 0;
  const isGeneratingAudio = ttsStatus === 'queued' || ttsStatus === 'processing';

  return (
    <div className="summary-panel overflow-hidden border-2 border-black bg-white p-6 shadow-[10px_10px_0px_0px_rgba(0,0,0,0.04)] md:p-7">
      <div className="mb-6 flex items-center gap-3">
        <span className="h-[2px] w-8 bg-black" />
        <h2 className="text-xs font-black uppercase tracking-[0.22em] text-black">Bản tóm tắt AI</h2>
        {loading ? (
          <span className="ml-auto rounded-full border border-black/20 bg-white px-3 py-1 text-[10px] font-black uppercase tracking-[0.12em] text-black animate-pulse">
            Đang tóm tắt...
          </span>
        ) : totalArticles ? (
          <span className="ml-auto rounded-full border border-black/20 bg-white px-3 py-1 text-[10px] font-black uppercase tracking-[0.12em] text-black">
            {totalArticles} bài
          </span>
        ) : null}
      </div>

      {onResummarize ? (
        <div className="mb-6 flex justify-end">
          <button
            type="button"
            onClick={onResummarize}
            disabled={resummarizeDisabled}
            className="flex items-center gap-2 rounded-full border border-black bg-white px-4 py-2 text-[10px] font-black uppercase tracking-[0.14em] text-black transition-all hover:bg-black hover:text-white disabled:cursor-not-allowed disabled:opacity-60"
          >
            <span className={`material-symbols-outlined text-sm ${loading ? 'animate-spin' : ''}`}>
              {loading ? 'progress_activity' : 'autorenew'}
            </span>
            Re-summary hôm nay
          </button>
        </div>
      ) : null}
      
      {loading ? (
        <div className="space-y-4 rounded-lg border border-black/10 bg-slate-50 p-5">
          <div className="flex items-center gap-3 text-slate-600">
            <span className="material-symbols-outlined summary-spin text-2xl">progress_activity</span>
            <p className="text-sm font-semibold">Đang tạo bản tóm tắt thông minh...</p>
          </div>
          <div className="summary-shimmer h-3 rounded" />
          <div className="summary-shimmer h-3 w-[88%] rounded" />
          <div className="summary-shimmer h-3 w-[76%] rounded" />
          <div className="summary-shimmer h-3 w-[82%] rounded" />
        </div>
      ) : !hasSummary ? (
        <div className="rounded-lg border border-dashed border-black/20 bg-slate-50 p-5 text-center">
          <span className="material-symbols-outlined text-4xl text-black/25">auto_awesome</span>
          <p className="mt-3 text-sm font-medium text-slate-500">
            Chọn hoặc tìm kiếm tin tức để tạo bản tóm tắt.
          </p>
        </div>
      ) : (
        <div>
          <div className="max-h-[48vh] space-y-3 overflow-y-auto pr-1 text-[15px] font-medium leading-relaxed text-slate-600 md:text-base">
            {renderedSummary?.map((line, index) => (
              <p key={`${index}-${line}`} className={/^\d+\./.test(line) ? 'font-semibold text-black' : ''}>
                {line}
              </p>
            ))}
          </div>

          <div className="mt-8 flex flex-wrap items-center gap-4">
            <button
              type="button"
              onClick={onGenerateTts}
              disabled={!hasSummary || isGeneratingAudio}
              className="flex items-center gap-3 bg-black px-8 py-4 text-xs font-black uppercase tracking-[0.15em] text-white transition-all hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-60"
            >
              <span className={`material-symbols-outlined text-lg ${isGeneratingAudio ? 'animate-spin' : ''}`}>
                {isGeneratingAudio ? 'progress_activity' : 'play_arrow'}
              </span>
              {isGeneratingAudio ? 'Đang tạo audio...' : ttsAudioUrl ? 'Tạo lại bản audio' : 'Nghe bản tin'}
            </button>
            <button
              type="button"
              onClick={handleCopy}
              className="flex items-center gap-3 border-2 border-black bg-white px-8 py-4 text-xs font-black uppercase tracking-[0.15em] text-black transition-all hover:bg-slate-50"
            >
              <span className="material-symbols-outlined text-lg">content_copy</span>
              {copied ? 'Đã sao chép' : 'Sao chép tóm tắt'}
            </button>
          </div>

          {ttsError ? (
            <p className="mt-4 text-xs font-semibold text-red-600">{ttsError}</p>
          ) : null}

          {ttsAudioUrl ? (
            <div className="mt-4">
              <audio controls className="w-full" src={ttsAudioUrl} preload="none" />
            </div>
          ) : null}
        </div>
      )}
    </div>
  );
}

export default SummaryBox;
