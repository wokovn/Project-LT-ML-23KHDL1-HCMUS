import { useState } from 'react';

const TONE_CLASSNAMES = {
    news: 'bg-black text-white border-black',
    commerce: 'bg-emerald-50 text-emerald-700 border-emerald-200',
    culture: 'bg-indigo-50 text-indigo-700 border-indigo-200',
    discussion: 'bg-violet-50 text-violet-700 border-violet-200',
    review: 'bg-pink-50 text-pink-700 border-pink-200',
    video: 'bg-red-50 text-red-700 border-red-200',
    generic: 'bg-slate-50 text-slate-700 border-slate-200',
};

function NewsArticle({
    category,
    categoryTone,
    source,
    timeAgo,
    title,
    description,
    imageUrl,
    imageAlt,
    articleUrl,
    onSummarize,
    onGenerateTts,
    summary,
    summaryVisible,
    summaryLoading,
    ttsStatus = 'idle',
    ttsAudioUrl = '',
    ttsError = '',
}) {
    const [copied, setCopied] = useState(false);
    const hasSummary = !!summary;
    const showSummary = hasSummary && summaryVisible;
    const isGeneratingAudio = ttsStatus === 'queued' || ttsStatus === 'processing';
    const categoryClasses = TONE_CLASSNAMES[categoryTone] || TONE_CLASSNAMES.generic;

    const handleShare = async () => {
        if (!articleUrl || articleUrl === '#') return;

        try {
            await navigator.clipboard.writeText(articleUrl);
            setCopied(true);
            window.setTimeout(() => setCopied(false), 1800);
        } catch {
            setCopied(false);
        }
    };

    return (
        <article className="group flex flex-col gap-6">
            <div className="flex flex-col gap-6 md:flex-row md:gap-10">
                <div className="h-44 w-full shrink-0 overflow-hidden border border-black bg-slate-100 md:w-60">
                    <img
                        alt={imageAlt}
                        className="h-full w-full object-cover transition-all duration-700 group-hover:scale-105"
                        src={imageUrl}
                    />
                </div>

                <div className="flex flex-1 flex-col">
                    <div className="mb-4 flex flex-wrap items-center gap-3">
                        <span className={`border px-2 py-0.5 text-[10px] font-black uppercase tracking-[0.12em] ${categoryClasses}`}>
                            {category}
                        </span>
                        <span className="text-xs font-bold text-black">{source}</span>
                        <span className="h-1 w-1 rounded-full bg-black" />
                        <span className="text-xs font-bold text-slate-400">{timeAgo || 'Vừa xong'}</span>
                    </div>

                    <h3 className="text-2xl font-black leading-tight tracking-tight text-black transition-all group-hover:underline group-hover:decoration-2 group-hover:underline-offset-4">
                        {title}
                    </h3>

                    <p className="mt-3 line-clamp-2 text-sm font-medium leading-relaxed text-slate-500">
                        {description}
                    </p>

                    <div className="mt-6 flex flex-wrap items-center justify-between gap-4">
                        <div className="flex flex-wrap items-center gap-6">
                            <a
                                className="flex items-center gap-2 text-[11px] font-black uppercase tracking-[0.13em] text-black transition-all hover:opacity-60"
                                href={articleUrl}
                                target="_blank"
                                rel="noopener noreferrer"
                            >
                                <span className="material-symbols-outlined text-lg">article</span>
                                Đọc bài gốc
                            </a>

                            <button
                                type="button"
                                onClick={onSummarize}
                                disabled={summaryLoading}
                                className="flex items-center gap-2 text-[11px] font-black uppercase tracking-[0.13em] text-slate-400 transition-all hover:text-black disabled:cursor-not-allowed disabled:opacity-70"
                            >
                                <span className={`material-symbols-outlined text-lg ${summaryLoading ? 'animate-spin' : ''}`}>
                                    {summaryLoading ? 'progress_activity' : showSummary ? 'expand_less' : 'summarize'}
                                </span>
                                {summaryLoading ? 'Đang tóm tắt...' : showSummary ? 'Thu gọn tóm tắt' : hasSummary ? 'Xem lại tóm tắt' : 'Tóm tắt bài viết'}
                            </button>

                            <button
                                type="button"
                                onClick={onGenerateTts}
                                disabled={!hasSummary || summaryLoading || isGeneratingAudio}
                                className="flex items-center gap-2 text-[11px] font-black uppercase tracking-[0.13em] text-slate-400 transition-all hover:text-black disabled:cursor-not-allowed disabled:opacity-70"
                            >
                                <span className={`material-symbols-outlined text-lg ${isGeneratingAudio ? 'animate-spin' : ''}`}>
                                    {isGeneratingAudio ? 'progress_activity' : 'play_arrow'}
                                </span>
                                {isGeneratingAudio ? 'Đang tạo audio...' : ttsAudioUrl ? 'Tạo lại audio' : 'Nghe audio'}
                            </button>
                        </div>

                        <div className="flex items-center gap-2">
                            {copied && (
                                <span className="text-[10px] font-black uppercase tracking-[0.12em] text-emerald-600">
                                    Đã copy
                                </span>
                            )}
                            <button
                                type="button"
                                onClick={handleShare}
                                className="inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-full text-black transition-all hover:bg-slate-100"
                                title="Sao chép link bài viết"
                            >
                                <span className="material-symbols-outlined text-base leading-none">{copied ? 'check' : 'share'}</span>
                            </button>
                        </div>
                    </div>
                </div>
            </div>

            {(summaryLoading || showSummary) && (
                <div className="border-l-2 border-black bg-slate-50 px-5 py-4">
                    {summaryLoading ? (
                        <div className="flex items-center gap-3 text-sm font-medium text-slate-600">
                            <span className="material-symbols-outlined animate-spin text-lg">progress_activity</span>
                            Đang tóm tắt bài viết...
                        </div>
                    ) : (
                        <div>
                            <div className="mb-2 flex items-center gap-2">
                                <span className="material-symbols-outlined text-base text-black">summarize</span>
                                <h4 className="text-xs font-black uppercase tracking-[0.14em] text-black">Tóm tắt nhanh</h4>
                            </div>
                            <p className="whitespace-pre-wrap text-sm leading-relaxed text-slate-700">{summary}</p>

                            {ttsError ? (
                                <p className="mt-3 text-xs font-semibold text-red-600">{ttsError}</p>
                            ) : null}

                            {ttsAudioUrl ? (
                                <div className="mt-4">
                                    <audio controls className="w-full" src={ttsAudioUrl} preload="none" />
                                </div>
                            ) : null}
                        </div>
                    )}
                </div>
            )}
        </article>
    );
}

export default NewsArticle;
