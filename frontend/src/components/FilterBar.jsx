function FilterBar({ voice, onVoiceChange, time, onTimeChange, source, onSourceChange }) {
    return (
        <div className="flex flex-wrap items-center justify-center gap-3 md:gap-4">
            <label className="relative flex items-center gap-2 rounded-full border border-black/20 bg-white px-4 py-2.5 text-xs font-black uppercase tracking-[0.1em] text-black transition-all hover:border-black">
                <span className="material-symbols-outlined text-base">record_voice_over</span>
                <span>Giọng đọc</span>
                <select
                    value={voice}
                    onChange={(event) => onVoiceChange(event.target.value)}
                    className="cursor-pointer border-0 bg-transparent py-0 pl-0 pr-6 text-[11px] font-black uppercase tracking-[0.12em] text-slate-600 focus:ring-0"
                >
                    <option value="Bắc">Nam (Bắc)</option>
                    <option value="Nam">Nam (Nam)</option>
                    <option value="Trung">Nam (Trung)</option>
                </select>
            </label>

            <label className="relative flex items-center gap-2 rounded-full border border-black/20 bg-white px-4 py-2.5 text-xs font-black uppercase tracking-[0.1em] text-black transition-all hover:border-black">
                <span className="material-symbols-outlined text-base">schedule</span>
                <span>Thời gian</span>
                <select
                    value={time}
                    onChange={(event) => onTimeChange(event.target.value)}
                    className="cursor-pointer border-0 bg-transparent py-0 pl-0 pr-6 text-[11px] font-black uppercase tracking-[0.12em] text-slate-600 focus:ring-0"
                >
                    <option value="pd">24h qua</option>
                    <option value="pw">7 ngày</option>
                    <option value="pm">Tháng này</option>
                    <option value="py">Năm nay</option>
                </select>
            </label>

            <label className="relative flex items-center gap-2 rounded-full border border-black/20 bg-white px-4 py-2.5 text-xs font-black uppercase tracking-[0.1em] text-black transition-all hover:border-black">
                <span className="material-symbols-outlined text-base">public</span>
                <span>Nguồn tin</span>
                <select
                    value={source}
                    onChange={(event) => onSourceChange(event.target.value)}
                    className="cursor-pointer border-0 bg-transparent py-0 pl-0 pr-6 text-[11px] font-black uppercase tracking-[0.12em] text-slate-600 focus:ring-0"
                >
                    <option value="all">Tất cả</option>
                    <option value="vi">Trong nước</option>
                    <option value="en">Quốc tế</option>
                </select>
            </label>

            <button
                type="button"
                className="rounded-full border border-black/20 p-2.5 text-black transition-all hover:border-black hover:bg-black hover:text-white"
            >
                <span className="material-symbols-outlined text-lg">tune</span>
            </button>
        </div>
    );
}

export default FilterBar;
