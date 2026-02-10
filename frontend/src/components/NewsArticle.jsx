function NewsArticle({ category, categoryColor, source, timeAgo, title, description, imageUrl, imageAlt, voiceType, articleUrl }) {
    return (
        <article className="bg-white rounded-lg border border-gray-100 shadow-soft hover:shadow-md transition-shadow duration-200 p-6 flex flex-col md:flex-row gap-6">
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
                    <button className="flex items-center gap-2 px-4 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-md text-sm font-medium transition-colors group">
                        <span className="material-symbols-outlined text-lg group-hover:text-blue-600">play_circle</span>
                        Nghe tóm tắt
                    </button>
                    <a className="text-sm text-gray-500 hover:text-slate-900 underline decoration-gray-300 underline-offset-4" href={articleUrl}>Đọc bài gốc</a>
                </div>
            </div>
        </article>
    );
}

export default NewsArticle;
