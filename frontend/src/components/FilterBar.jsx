function FilterBar({ voice, onVoiceChange, time, onTimeChange, source, onSourceChange }) {
    return (
        <div className="flex flex-wrap items-center gap-3">
            <div className="relative inline-block text-left">
                <div className="flex items-center gap-2 bg-surface-light border border-gray-200 rounded-md px-3 py-2 text-sm font-medium text-slate-700 hover:bg-gray-50 cursor-pointer transition-colors">
                    <span className="material-symbols-outlined text-gray-500 text-lg">record_voice_over</span>
                    <span>Giọng đọc:</span>
                    <select 
                        value={voice}
                        onChange={(e) => onVoiceChange(e.target.value)}
                        className="bg-transparent border-none p-0 pr-6 text-slate-900 font-semibold focus:ring-0 cursor-pointer text-sm"
                    >
                        <option value="Bắc">Bắc (Hà Nội)</option>
                        <option value="Trung">Trung (Huế)</option>
                        <option value="Nam">Nam (Sài Gòn)</option>
                    </select>
                </div>
            </div>
            <div className="relative inline-block text-left">
                <div className="flex items-center gap-2 bg-surface-light border border-gray-200 rounded-md px-3 py-2 text-sm font-medium text-slate-700 hover:bg-gray-50 cursor-pointer transition-colors">
                    <span className="material-symbols-outlined text-gray-500 text-lg">schedule</span>
                    <span>Thời gian:</span>
                    <select 
                        value={time}
                        onChange={(e) => onTimeChange(e.target.value)}
                        className="bg-transparent border-none p-0 pr-6 text-slate-900 font-semibold focus:ring-0 cursor-pointer text-sm"
                    >
                        <option value="pd">24 giờ qua</option>
                        <option value="pw">7 ngày qua</option>
                        <option value="pm">Tháng này</option>
                        <option value="py">Năm nay</option>
                    </select>
                </div>
            </div>
            <div className="relative inline-block text-left">
                <div className="flex items-center gap-2 bg-surface-light border border-gray-200 rounded-md px-3 py-2 text-sm font-medium text-slate-700 hover:bg-gray-50 cursor-pointer transition-colors">
                    <span className="material-symbols-outlined text-gray-500 text-lg">public</span>
                    <span>Nguồn:</span>
                    <select 
                        value={source}
                        onChange={(e) => onSourceChange(e.target.value)}
                        className="bg-transparent border-none p-0 pr-6 text-slate-900 font-semibold focus:ring-0 cursor-pointer text-sm"
                    >
                        <option value="all">Tất cả</option>
                        <option value="en">Quốc tế</option>
                        <option value="vi">Trong nước</option>
                    </select>
                </div>
            </div>
        </div>
    );
}

export default FilterBar;
