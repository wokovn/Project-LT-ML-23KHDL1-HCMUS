function NewsArticle({ category, categoryColor, source, timeAgo, title, description, imageUrl, imageAlt, voiceType, articleUrl, onSummarize, summary, summaryVisible, summaryLoading }) {
    const hasSummary = !!summary;
    const showSummary = hasSummary && summaryVisible;
    
    return (
        <article className="bg-white rounded-lg border border-gray-100 shadow-soft hover:shadow-md transition-shadow duration-200 p-6 flex flex-col gap-6">
            <div className="flex flex-col md:flex-row gap-6">
                <div className="w-full md:w-48 h-48 md:h-auto flex-shrink-0 relative overflow-hidden rounded-md bg-gray-100">
                    <img 
                        alt={imageAlt} 
                        className="w-full h-full object-cover transform hover:scale-105 transition-transform duration-500" 
                        src={imageUrl}
                    />
                </div>
                <div className="flex-1 space-y-3 flex flex-col justify-between">
                    <div>
                        <div className="flex items-center gap-2 mb-2">
                            <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${categoryColor} uppercase tracking-wide`}>{category}</span>
                            <span className="text-xs text-gray-400">• {source} • {timeAgo}</span>
                        </div>
                        <h3 className="text-xl font-semibold text-slate-900 leading-snug">{title}</h3>
                        <p className="text-slate-600 text-sm leading-relaxed line-clamp-3 mt-2">
                            {description}
                        </p>
                    </div>
                    <div className="flex items-center gap-4 pt-2">
                        <button 
                            onClick={onSummarize}
                            disabled={summaryLoading}
                            className="flex items-center gap-2 px-4 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-md text-sm font-medium transition-colors group disabled:opacity-50 disabled:cursor-not-allowed">
                            <span className="material-symbols-outlined text-lg group-hover:text-blue-600">
                                {summaryLoading ? 'progress_activity' : showSummary ? 'expand_less' : 'play_circle'}
                            </span>
                            {summaryLoading ? 'Đang tóm tắt...' : showSummary ? 'Thu gọn' : hasSummary ? 'Xem lại' : 'Nghe tóm tắt'}
                        </button>
                        <a 
                            className="text-sm text-gray-500 hover:text-slate-900 underline decoration-gray-300 underline-offset-4" 
                            href={articleUrl}
                            target="_blank"
                            rel="noopener noreferrer"
                        >
                            Đọc bài gốc
                        </a>
                    </div>
                </div>
            </div>
            
            {/* Summary section */}
            {(summaryLoading || showSummary) && (
                <div className="border-t border-gray-100 pt-4 mt-2">
                    {summaryLoading ? (
                        <div className="bg-blue-50 rounded-md border border-blue-100 p-6 text-center">
                            <span className="material-symbols-outlined text-3xl text-blue-500 animate-spin">progress_activity</span>
                            <p className="text-slate-600 mt-3 text-sm">Đang tóm tắt bài viết...</p>
                        </div>
                    ) : summary && (
                        <div className="bg-gradient-to-br from-blue-50 to-indigo-50 rounded-md border border-blue-100 p-5">
                            <div className="flex items-center gap-2 mb-3">
                                <span className="material-symbols-outlined text-blue-600 text-sm">summarize</span>
                                <h4 className="text-sm font-semibold text-slate-900">Tóm tắt</h4>
                            </div>
                            <div className="bg-white rounded p-4 text-slate-700 text-sm leading-relaxed whitespace-pre-wrap">
                                {summary}
                            </div>
                        </div>
                    )}
                </div>
            )}
        </article>
    );
}

export default NewsArticle;
