function Navbar() {
    return (
        <nav className="w-full py-4 px-6 flex items-center justify-between border-b border-gray-100 bg-white sticky top-0 z-50">
            <div className="flex items-center gap-2">
                <span className="material-symbols-outlined text-2xl text-slate-900">auto_stories</span>
                <span className="text-lg font-semibold tracking-tight text-slate-900">NewsAI</span>
            </div>
            <div className="hidden md:flex items-center gap-6 text-sm font-medium text-slate-500">
                <a className="hover:text-slate-900 transition-colors" href="#">Giới thiệu</a>
                <a className="hover:text-slate-900 transition-colors" href="#">Tính năng</a>
                <a className="hover:text-slate-900 transition-colors" href="#">Bảng giá</a>
            </div>
        </nav>
    );
}

export default Navbar;
