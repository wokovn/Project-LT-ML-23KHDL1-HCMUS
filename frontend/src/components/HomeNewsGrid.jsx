import { useState } from 'react';

const TONE_BADGE_CLASS = {
  news: 'bg-black text-white',
  commerce: 'bg-emerald-100 text-emerald-700',
  culture: 'bg-indigo-100 text-indigo-700',
  discussion: 'bg-violet-100 text-violet-700',
  review: 'bg-pink-100 text-pink-700',
  video: 'bg-red-100 text-red-700',
  generic: 'bg-slate-100 text-slate-700',
};

function HomeNewsGrid({ articles, loading, onSummarizeArticle }) {
  const [copiedUrl, setCopiedUrl] = useState('');
  const featuredArticle = articles?.[0] || null;
  const sideArticles = articles?.slice(1, 5) || [];

  const handleCopyLink = async (articleUrl) => {
    if (!articleUrl || articleUrl === '#') return;

    try {
      await navigator.clipboard.writeText(articleUrl);
      setCopiedUrl(articleUrl);
      window.setTimeout(() => setCopiedUrl(''), 1800);
    } catch {
      setCopiedUrl('');
    }
  };

  if (loading) {
    return (
      <div className="grid grid-cols-1 gap-5 lg:grid-cols-12">
        <div className="h-[330px] animate-pulse rounded-xl bg-slate-200 lg:col-span-8" />
        <div className="h-[330px] animate-pulse rounded-xl bg-slate-200 lg:col-span-4" />
        <div className="h-64 animate-pulse rounded-xl bg-slate-200 lg:col-span-4" />
        <div className="h-64 animate-pulse rounded-xl bg-slate-200 lg:col-span-4" />
        <div className="h-64 animate-pulse rounded-xl bg-slate-200 lg:col-span-4" />
      </div>
    );
  }

  if (!featuredArticle) {
    return (
      <div className="flex min-h-64 flex-col items-center justify-center rounded-xl border border-dashed border-black/20 bg-white text-center">
        <span className="material-symbols-outlined text-6xl text-black/20">search</span>
        <p className="mt-4 text-lg font-medium text-slate-500">
          Chưa có dữ liệu tin tức đầu ngày.
        </p>
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 gap-5 lg:grid-cols-12">
      <article className="group relative overflow-hidden rounded-xl border border-transparent bg-white shadow-[0px_12px_32px_rgba(25,28,30,0.06)] transition-all hover:border-slate-100 hover:shadow-xl lg:col-span-8">
        <div className="relative aspect-[16/9] w-full">
          <img className="h-full w-full object-cover" src={featuredArticle.imageUrl} alt={featuredArticle.imageAlt} />
          <div className="absolute inset-0 bg-gradient-to-t from-black/80 via-black/20 to-transparent" />
          <div className="absolute left-5 right-5 top-5 flex items-center justify-between">
            <span className="rounded-sm bg-black px-3 py-1 text-[10px] font-black uppercase tracking-[0.16em] text-white">
              Featured
            </span>
            <span className="rounded-sm bg-white/90 px-3 py-1 text-[10px] font-black uppercase tracking-[0.12em] text-black">
              {featuredArticle.source}
            </span>
          </div>
          <div className="absolute bottom-5 left-5 right-5">
            <h2 className="mb-2 text-2xl font-black leading-tight tracking-tight text-white md:text-3xl">
              {featuredArticle.title}
            </h2>
            <div className="flex items-center justify-between gap-3">
              <p className="text-sm font-medium text-white/80">
                {featuredArticle.timeAgo || 'Hôm nay'} • {featuredArticle.category}
              </p>

              <div className="flex items-center gap-2">
                <a
                  href={featuredArticle.articleUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  title="Đọc bài gốc"
                  className="inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-white/90 text-black transition-all hover:bg-white"
                >
                  <span className="material-symbols-outlined text-base leading-none">article</span>
                </a>
                <button
                  type="button"
                  title="Tóm tắt bài"
                  onClick={() => onSummarizeArticle?.(featuredArticle.articleUrl)}
                  className="inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-white/20 text-white transition-all hover:bg-white/30"
                >
                  <span className="material-symbols-outlined text-base leading-none">auto_awesome</span>
                </button>
                <button
                  type="button"
                  title="Sao chép link"
                  onClick={() => handleCopyLink(featuredArticle.articleUrl)}
                  className="inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-white/20 text-white transition-all hover:bg-white/30"
                >
                  <span className="material-symbols-outlined text-base leading-none">
                    {copiedUrl === featuredArticle.articleUrl ? 'check' : 'share'}
                  </span>
                </button>
              </div>
            </div>
            {copiedUrl === featuredArticle.articleUrl && (
              <p className="mt-2 text-xs font-bold text-emerald-300">Đã copy link bài viết</p>
            )}
          </div>
        </div>
      </article>

      <article className="rounded-xl bg-white p-5 shadow-[0px_12px_32px_rgba(25,28,30,0.06)] lg:col-span-4">
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
            <h3 className="text-lg font-bold leading-snug tracking-tight text-black">{sideArticles[0].title}</h3>
            <div className="mt-5 flex items-center justify-between gap-3">
              <span className="text-xs font-semibold text-slate-500">{sideArticles[0].timeAgo || 'Hôm nay'}</span>
              <div className="flex items-center gap-2">
                <a
                  href={sideArticles[0].articleUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  title="Đọc bài gốc"
                  className="inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-full text-slate-500 transition-all hover:bg-slate-100 hover:text-black"
                >
                  <span className="material-symbols-outlined text-base leading-none">article</span>
                </a>
                <button
                  type="button"
                  title="Tóm tắt bài"
                  onClick={() => onSummarizeArticle?.(sideArticles[0].articleUrl)}
                  className="inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-full text-slate-500 transition-all hover:bg-slate-100 hover:text-black"
                >
                  <span className="material-symbols-outlined text-base leading-none">auto_awesome</span>
                </button>
                <button
                  type="button"
                  title="Sao chép link"
                  onClick={() => handleCopyLink(sideArticles[0].articleUrl)}
                  className="inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-full text-slate-500 transition-all hover:bg-slate-100 hover:text-black"
                >
                  <span className="material-symbols-outlined text-base leading-none">
                    {copiedUrl === sideArticles[0].articleUrl ? 'check' : 'share'}
                  </span>
                </button>
              </div>
            </div>
            {copiedUrl === sideArticles[0].articleUrl && (
              <p className="mt-2 text-[11px] font-bold text-emerald-600">Đã copy link bài viết</p>
            )}
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
          className="flex flex-col overflow-hidden rounded-xl border border-transparent bg-white transition-all hover:border-slate-200 lg:col-span-4"
        >
          <div className="h-48 w-full overflow-hidden">
            <img className="h-full w-full object-cover" src={article.imageUrl} alt={article.imageAlt} />
          </div>
          <div className="flex flex-1 flex-col p-5">
            <span
              className={`mb-2 inline-flex w-fit rounded-sm px-2 py-1 text-[10px] font-black uppercase tracking-[0.14em] ${
                TONE_BADGE_CLASS[article.categoryTone] || TONE_BADGE_CLASS.generic
              }`}
            >
              {article.category}
            </span>
            <h3 className="mb-4 text-lg font-bold leading-tight tracking-tight text-black">{article.title}</h3>
            <div className="mt-auto flex items-center justify-between gap-3">
              <span className="text-xs font-medium text-slate-500">{article.timeAgo || 'Hôm nay'}</span>
              <div className="flex items-center gap-2">
                <a
                  href={article.articleUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  title="Đọc bài gốc"
                  className="inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-full text-slate-500 transition-all hover:bg-slate-100 hover:text-black"
                >
                  <span className="material-symbols-outlined text-base leading-none">article</span>
                </a>
                <button
                  type="button"
                  title="Tóm tắt bài"
                  onClick={() => onSummarizeArticle?.(article.articleUrl)}
                  className="inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-full text-slate-500 transition-all hover:bg-slate-100 hover:text-black"
                >
                  <span className="material-symbols-outlined text-base leading-none">auto_awesome</span>
                </button>
                <button
                  type="button"
                  title="Sao chép link"
                  onClick={() => handleCopyLink(article.articleUrl)}
                  className="inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-full text-slate-500 transition-all hover:bg-slate-100 hover:text-black"
                >
                  <span className="material-symbols-outlined text-base leading-none">
                    {copiedUrl === article.articleUrl ? 'check' : 'share'}
                  </span>
                </button>
              </div>
            </div>
            {copiedUrl === article.articleUrl && (
              <p className="mt-2 text-[11px] font-bold text-emerald-600">Đã copy link bài viết</p>
            )}
          </div>
        </article>
      ))}
    </div>
  );
}

export default HomeNewsGrid;
