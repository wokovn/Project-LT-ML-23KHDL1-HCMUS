function SearchBox({ value, onChange, onSearch, loading }) {
    const handleSubmit = (event) => {
        event.preventDefault();
        if (!value?.trim() || !onSearch) return;
        onSearch(value.trim());
    };

    return (
        <form onSubmit={handleSubmit} className="mx-auto w-full max-w-[860px]">
            <div className="group relative">
                <div className="pointer-events-none absolute inset-0 rounded-full border-2 border-black/10 transition-all group-focus-within:border-black/40" />
                <div className="relative flex items-center gap-4 rounded-full border-2 border-black bg-white px-6 py-4 shadow-[8px_8px_0px_0px_rgba(0,0,0,0.05)] transition-all group-hover:shadow-[10px_10px_0px_0px_rgba(0,0,0,0.08)] md:px-9 md:py-5">
                    <span className="material-symbols-outlined shrink-0 text-black">search</span>
                    <input
                        type="text"
                        value={value}
                        onChange={(event) => onChange?.(event.target.value)}
                        disabled={loading}
                        placeholder="Nhập từ khóa hoặc dán URL của tin tức..."
                        className="w-full border-0 bg-transparent text-base font-medium text-black placeholder:text-slate-400 focus:ring-0 md:text-lg"
                    />
                    <button
                        type="submit"
                        disabled={loading || !value?.trim()}
                        className="flex shrink-0 items-center gap-2 rounded-full bg-black px-5 py-2.5 text-xs font-black uppercase tracking-[0.15em] text-white transition-all hover:bg-slate-800 disabled:cursor-not-allowed disabled:bg-slate-400 md:px-8"
                    >
                        <span className="material-symbols-outlined text-base">
                            {loading ? 'progress_activity' : 'arrow_forward'}
                        </span>
                        <span className="hidden sm:inline">Tìm kiếm</span>
                    </button>
                </div>
            </div>
        </form>
    );
}

export default SearchBox;
