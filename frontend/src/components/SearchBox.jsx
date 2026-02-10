import { useEffect, useRef, useState } from 'react';

function SearchBox({ onSearch, loading }) {
    const textareaRef = useRef(null);
    const [value, setValue] = useState('');

    useEffect(() => {
        const textarea = textareaRef.current;
        if (textarea) {
            const OnInput = function() {
                this.style.height = 0;
                this.style.height = (this.scrollHeight) + "px";
            };
            
            textarea.setAttribute("style", "height:" + (textarea.scrollHeight) + "px;overflow-y:hidden;");
            textarea.addEventListener("input", OnInput, false);
            
            return () => {
                textarea.removeEventListener("input", OnInput, false);
            };
        }
    }, []);

    const handleSubmit = (e) => {
        e.preventDefault();
        if (value.trim() && onSearch) {
            onSearch(value.trim());
        }
    };

    return (
        <form onSubmit={handleSubmit}>
            <div className="relative group">
                <div className="absolute inset-0 bg-gray-200 rounded-lg blur opacity-20 group-hover:opacity-40 transition duration-500"></div>
                <div className="relative bg-white rounded-lg border border-gray-200 shadow-soft p-2 flex items-start gap-2 focus-within:ring-2 focus-within:ring-gray-100 focus-within:border-gray-300 transition-all">
                    <span className="material-symbols-outlined text-gray-400 p-2 mt-1">search</span>
                    <textarea 
                        ref={textareaRef}
                        value={value}
                        onChange={(e) => setValue(e.target.value)}
                        disabled={loading}
                        className="w-full bg-transparent border-0 text-slate-800 placeholder-gray-400 focus:ring-0 resize-none py-3 px-0 text-lg leading-relaxed min-h-[56px]" 
                        placeholder="Dán liên kết bài báo hoặc nhập từ khóa để tóm tắt..." 
                        rows="1" 
                        style={{ fieldSizing: 'content' }}
                    ></textarea>
                    <button 
                        type="submit"
                        disabled={loading || !value.trim()}
                        className="flex items-center justify-center h-12 w-12 mt-0.5 rounded-md bg-slate-900 hover:bg-black text-white transition-all disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                        <span className="material-symbols-outlined text-xl">
                            {loading ? 'progress_activity' : 'arrow_forward'}
                        </span>
                    </button>
                </div>
            </div>
        </form>
    );
}

export default SearchBox;
