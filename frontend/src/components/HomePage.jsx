import { useMemo, useState } from 'react';

const TONE_BADGE_CLASS = {
  news: 'bg-black text-white',
  commerce: 'bg-emerald-100 text-emerald-700',
  culture: 'bg-indigo-100 text-indigo-700',
  discussion: 'bg-violet-100 text-violet-700',
  review: 'bg-pink-100 text-pink-700',
  video: 'bg-red-100 text-red-700',
  generic: 'bg-slate-100 text-slate-700',
};

function HomePage({ articles, loading, onSearch, onOpenWorkspace }) {
  const [query, setQuery] = useState('');

  const featuredArticle = articles?.[0] || null;
  const sideArticles = useMemo(() => articles.slice(1, 5), [articles]);

  const handleSubmit = (event) => {
    event.preventDefault();
    if (!query.trim() || !onSearch) return;
    onSearch(query.trim());
  };

  return (
    <div className="min-h-screen bg-[#f7f9fb] text-slate-900 selection:bg-black selection:text-white">
      <header className="sticky top-0 z-40 border-b border-black/5 bg-[#f7f9fb]/95 px-5 py-4 backdrop-blur md:px-8 lg:px-12">
        <div className="mx-auto flex w-full max-w-7xl items-center justify-between gap-4">
          <div className="flex items-center gap-8">
            <span className="text-2xl font-black tracking-tight text-black">NewsAI</span>
            <nav className="hidden items-center gap-6 md:flex">
              <button type="button" className="border-b-2 border-black pb-1 text-sm font-bold text-black">
                Discover
              </button>
              <button type="button" className="text-sm font-medium text-slate-500 transition-colors hover:text-black">
                Briefings
              </button>
              <button type="button" className="text-sm font-medium text-slate-500 transition-colors hover:text-black">
                Channels
              </button>
            </nav>
          </div>

          <button
            type="button"
            onClick={onOpenWorkspace}
            className="rounded-lg bg-black px-5 py-2 text-sm font-bold text-white transition-all hover:bg-slate-800"
          >
            Vào trang tìm kiếm
          </button>
        </div>
      </header>

      <main className="px-4 pb-16 pt-10 md:px-8 lg:px-12">
        <section className="mx-auto mb-14 w-full max-w-5xl text-center">
          <h1 className="mb-10 text-4xl font-black tracking-tight text-black md:text-5xl lg:text-6xl">
            Chào buổi sáng,
            <br />
            Khám phá tin tức AI hôm nay
          </h1>

          <form onSubmit={handleSubmit} className="relative mx-auto mb-8 w-full max-w-2xl">
            <span className="material-symbols-outlined pointer-events-none absolute left-5 top-1/2 -translate-y-1/2 text-slate-400">
              search
            </span>
            <input
              type="text"
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder="Tìm kiếm tin tức hoặc chủ đề AI..."
              className="h-16 w-full rounded-full border border-black/10 bg-white pl-14 pr-5 text-base font-medium text-black shadow-[0px_12px_32px_rgba(25,28,30,0.06)] outline-none transition-all focus:border-black/30"
            />
          </form>

          <div className="flex flex-wrap items-center justify-center gap-4">
            <button
              type="button"
              onClick={onOpenWorkspace}
              className="flex items-center gap-2 rounded-full border border-slate-200 bg-white px-6 py-2.5 text-sm font-semibold text-slate-700 transition-colors hover:bg-slate-50"
            >
              <span className="material-symbols-outlined text-lg">check_circle</span>
              Xem trang chi tiết
            </button>
            <button
              type="button"
              onClick={() => onSearch?.('tin tức AI hôm nay')}
              className="flex items-center gap-2 rounded-full bg-black px-8 py-2.5 text-sm font-bold text-white transition-all hover:scale-[1.02]"
            >
              <span className="material-symbols-outlined text-lg" style={{ fontVariationSettings: "'FILL' 1" }}>
                bolt
              </span>
              Tóm tắt ngay
            </button>
          </div>
        </section>

        <section className="mx-auto max-w-7xl">
          {loading && (
            <div className="grid grid-cols-1 gap-6 md:grid-cols-12">
              <div className="md:col-span-8 h-[320px] animate-pulse rounded-xl bg-slate-200" />
              <div className="md:col-span-4 h-[320px] animate-pulse rounded-xl bg-slate-200" />
              <div className="md:col-span-4 h-64 animate-pulse rounded-xl bg-slate-200" />
              <div className="md:col-span-4 h-64 animate-pulse rounded-xl bg-slate-200" />
              <div className="md:col-span-4 h-64 animate-pulse rounded-xl bg-slate-200" />
            </div>
          )}

          {!loading && featuredArticle && (
            <div className="grid grid-cols-1 gap-6 md:grid-cols-12">
              <article className="group relative overflow-hidden rounded-xl border border-transparent bg-white shadow-[0px_12px_32px_rgba(25,28,30,0.06)] transition-all hover:border-slate-100 hover:shadow-xl md:col-span-8">
                <div className="relative aspect-[16/9] w-full">
                  <img className="h-full w-full object-cover" src={featuredArticle.imageUrl} alt={featuredArticle.imageAlt} />
                  <div className="absolute inset-0 bg-gradient-to-t from-black/80 via-black/20 to-transparent" />
                  <div className="absolute left-6 right-6 top-6 flex items-center justify-between">
                    <span className="rounded-sm bg-black px-3 py-1 text-[10px] font-black uppercase tracking-[0.18em] text-white">
                      Featured
                    </span>
                    <span className="rounded-sm bg-white/90 px-3 py-1 text-[10px] font-black uppercase tracking-[0.12em] text-black">
                      {featuredArticle.source}
                    </span>
                  </div>
                  <div className="absolute bottom-6 left-6 right-6">
                    <h2 className="mb-3 text-2xl font-black leading-tight tracking-tight text-white md:text-3xl">
                      {featuredArticle.title}
                    </h2>
                    <p className="text-sm font-medium text-white/80">{featuredArticle.timeAgo || 'Hôm nay'} • {featuredArticle.category}</p>
                  </div>
                </div>
              </article>

              <article className="rounded-xl bg-white p-6 shadow-[0px_12px_32px_rgba(25,28,30,0.06)] md:col-span-4">
                {sideArticles[0] ? (
                  <>
                    <div className="mb-4 flex items-center justify-between">
                      <span
                        className={`rounded-sm px-3 py-1 text-[10px] font-black uppercase tracking-[0.14em] ${
                          TONE_BADGE_CLASS[sideArticles[0].categoryTone] || TONE_BADGE_CLASS.generic
                        }`}
                      >
                        {sideArticles[0].category}
                      </span>
                      <span className="text-xs font-semibold text-slate-500">{sideArticles[0].timeAgo || 'Hôm nay'}</span>
                    </div>
                    <div className="mb-4 aspect-video w-full overflow-hidden rounded-lg">
                      <img className="h-full w-full object-cover" src={sideArticles[0].imageUrl} alt={sideArticles[0].imageAlt} />
                    </div>
                    <h3 className="text-xl font-bold leading-snug tracking-tight text-black">{sideArticles[0].title}</h3>
                  </>
                ) : (
                  <div className="flex h-full min-h-64 flex-col items-center justify-center rounded-lg border border-dashed border-slate-200 text-center">
                    <span className="material-symbols-outlined text-4xl text-slate-300">newspaper</span>
                    <p className="mt-3 text-sm font-medium text-slate-500">Đang chuẩn bị tin tức đầu ngày...</p>
                  </div>
                )}
              </article>

              {sideArticles.slice(1).map((article) => (
                <article
                  key={article.articleUrl}
                  className="flex flex-col overflow-hidden rounded-xl border border-transparent bg-white transition-all hover:border-slate-200 md:col-span-4"
                >
                  <div className="h-48 w-full overflow-hidden">
                    <img className="h-full w-full object-cover" src={article.imageUrl} alt={article.imageAlt} />
                  </div>
                  <div className="flex flex-1 flex-col p-6">
                    <span
                      className={`mb-2 inline-flex w-fit rounded-sm px-2 py-1 text-[10px] font-black uppercase tracking-[0.14em] ${
                        TONE_BADGE_CLASS[article.categoryTone] || TONE_BADGE_CLASS.generic
                      }`}
                    >
                      {article.category}
                    </span>
                    <h3 className="mb-4 text-lg font-bold leading-tight tracking-tight text-black">{article.title}</h3>
                    <span className="mt-auto text-xs font-medium text-slate-500">{article.timeAgo || 'Hôm nay'}</span>
                  </div>
                </article>
              ))}
            </div>
          )}

          {!loading && !featuredArticle && (
            <div className="flex min-h-64 flex-col items-center justify-center rounded-xl border border-dashed border-black/20 bg-white text-center">
              <span className="material-symbols-outlined text-6xl text-black/20">search</span>
              <p className="mt-4 text-lg font-medium text-slate-500">
                Chưa có dữ liệu tin tức đầu ngày. Hãy thử tìm kiếm ngay.
              </p>
            </div>
          )}
        </section>
      </main>
    </div>
  );
}

export default HomePage;
