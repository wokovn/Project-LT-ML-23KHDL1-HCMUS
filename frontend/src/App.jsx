import { useEffect, useRef, useState } from 'react'
import SearchBox from './components/SearchBox'
import FilterBar from './components/FilterBar'
import NewsArticle from './components/NewsArticle'
import SummaryBox from './components/SummaryBox'
import HomeNewsGrid from './components/HomeNewsGrid'
import apiService from './services/api.service'
import './App.css'

const HISTORY_KEY = 'newsai-search-history'
const DAILY_SNAPSHOT_KEY = 'newsai-daily-snapshot'
const MAX_HISTORY_ITEMS = 6
const SUMMARY_TTS_STORAGE_KEY = 'newsai-summary-tts-jobs'
const ARTICLE_TTS_STORAGE_KEY = 'newsai-article-tts-jobs'
const ACTIVE_TTS_STATUSES = new Set(['queued', 'processing'])

const createIdleTtsState = () => ({
  key: '',
  status: 'idle',
  audioUrl: '',
  error: '',
  createdAt: '',
  updatedAt: '',
})

const normalizeTtsState = (value) => {
  if (!value || typeof value !== 'object') return createIdleTtsState()

  return {
    key: typeof value.key === 'string' ? value.key : '',
    status: typeof value.status === 'string' ? value.status : 'idle',
    audioUrl: typeof value.audioUrl === 'string' ? value.audioUrl : '',
    error: typeof value.error === 'string' ? value.error : '',
    createdAt: typeof value.createdAt === 'string' ? value.createdAt : '',
    updatedAt: typeof value.updatedAt === 'string' ? value.updatedAt : '',
  }
}

const normalizeTtsStateMap = (value) => {
  if (!value || typeof value !== 'object' || Array.isArray(value)) return {}

  return Object.entries(value).reduce((accumulator, [key, state]) => {
    if (!key || typeof key !== 'string') return accumulator
    accumulator[key] = normalizeTtsState(state)
    return accumulator
  }, {})
}

const loadTtsStateMapFromStorage = (storageKey) => {
  if (typeof window === 'undefined') return {}

  try {
    const raw = window.localStorage.getItem(storageKey)
    if (!raw) return {}
    const parsed = JSON.parse(raw)
    return normalizeTtsStateMap(parsed)
  } catch {
    return {}
  }
}

const saveTtsStateMapToStorage = (storageKey, value) => {
  if (typeof window === 'undefined') return

  try {
    window.localStorage.setItem(storageKey, JSON.stringify(value))
  } catch {
    // Ignore storage quota and browser privacy mode errors.
  }
}

const getSummarySignature = (text = '') => text.trim().toLowerCase().replace(/\s+/g, ' ').slice(0, 280)

const getArticleTtsSlot = (articleUrl, index) => {
  if (typeof articleUrl === 'string' && articleUrl.trim() && articleUrl !== '#') {
    return articleUrl
  }
  return `local-article-${index}`
}

const toTtsStateFromJob = (job, fallback = createIdleTtsState()) => {
  return {
    key: typeof job?.key === 'string' ? job.key : fallback.key,
    status: typeof job?.status === 'string' ? job.status : fallback.status,
    audioUrl: typeof job?.audioUrl === 'string' ? job.audioUrl : fallback.audioUrl,
    error: typeof job?.error === 'string' ? job.error : '',
    createdAt: typeof job?.createdAt === 'string' ? job.createdAt : fallback.createdAt,
    updatedAt: typeof job?.updatedAt === 'string' ? job.updatedAt : fallback.updatedAt,
  }
}

const isSameTtsState = (left, right) => {
  if (!left && !right) return true
  if (!left || !right) return false

  return (
    left.key === right.key &&
    left.status === right.status &&
    left.audioUrl === right.audioUrl &&
    left.error === right.error &&
    left.createdAt === right.createdAt &&
    left.updatedAt === right.updatedAt
  )
}

const getTtsErrorMessage = (error, fallbackMessage) => {
  return error?.response?.data?.error || error?.response?.data?.details || error?.message || fallbackMessage
}

const getLocalDayKey = (date = new Date()) => {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, '0');
  const day = String(date.getDate()).padStart(2, '0');
  return `${year}-${month}-${day}`;
};

const formatDateForQuery = (date = new Date()) => {
  const day = String(date.getDate()).padStart(2, '0');
  const month = String(date.getMonth() + 1).padStart(2, '0');
  const year = date.getFullYear();
  return `${day}/${month}/${year}`;
};

const getDailyAutoQuery = (date = new Date()) => `tin tức việt nam ${formatDateForQuery(date)}`;

const createHistoryId = () => {
  if (globalThis.crypto?.randomUUID) {
    return globalThis.crypto.randomUUID();
  }
  return `${Date.now()}-${Math.random().toString(16).slice(2)}`;
};

const normalizeHistoryEntry = (entry, index) => {
  if (typeof entry === 'string') {
    const query = entry.trim();
    if (!query) return null;

    return {
      id: `legacy-${index}-${query.toLowerCase().replace(/\s+/g, '-')}`,
      query,
      createdAt: new Date(0).toISOString(),
      dayKey: '',
      autoDaily: false,
      filters: {
        voice: 'Bắc',
        time: 'pd',
        source: 'all',
      },
      articles: [],
      summary: '',
      summaryReady: false,
      totalArticles: 0,
    };
  }

  if (!entry || typeof entry !== 'object') return null;

  const query = typeof entry.query === 'string' ? entry.query.trim() : '';
  if (!query) return null;

  return {
    id: typeof entry.id === 'string' && entry.id ? entry.id : createHistoryId(),
    query,
    createdAt: typeof entry.createdAt === 'string' ? entry.createdAt : new Date().toISOString(),
    dayKey: typeof entry.dayKey === 'string' ? entry.dayKey : '',
    autoDaily: Boolean(entry.autoDaily),
    filters: {
      voice: entry.filters?.voice || 'Bắc',
      time: entry.filters?.time || 'pd',
      source: entry.filters?.source || 'all',
    },
    articles: Array.isArray(entry.articles) ? entry.articles : [],
    summary: typeof entry.summary === 'string' ? entry.summary : '',
    summaryReady:
      typeof entry.summaryReady === 'boolean'
        ? entry.summaryReady
        : Boolean(typeof entry.summary === 'string' && entry.summary.trim().length > 0),
    totalArticles: Number.isFinite(entry.totalArticles) ? entry.totalArticles : 0,
  };
};

const loadHistoryFromStorage = () => {
  if (typeof window === 'undefined') return [];

  try {
    const rawHistory = window.localStorage.getItem(HISTORY_KEY);
    if (!rawHistory) return [];

    const parsedHistory = JSON.parse(rawHistory);
    if (!Array.isArray(parsedHistory)) return [];

    return parsedHistory
      .map((entry, index) => normalizeHistoryEntry(entry, index))
      .filter((entry) => entry && !entry.autoDaily)
      .slice(0, MAX_HISTORY_ITEMS);
  } catch {
    return [];
  }
};

const loadDailySnapshotFromStorage = () => {
  if (typeof window === 'undefined') return null;

  try {
    const rawSnapshot = window.localStorage.getItem(DAILY_SNAPSHOT_KEY);
    if (!rawSnapshot) return null;

    const parsedSnapshot = JSON.parse(rawSnapshot);
    const normalizedSnapshot = normalizeHistoryEntry(parsedSnapshot, 0);
    if (!normalizedSnapshot) return null;

    return {
      ...normalizedSnapshot,
      autoDaily: true,
    };
  } catch {
    return null;
  }
};

const saveDailySnapshotToStorage = (entry) => {
  if (typeof window === 'undefined') return;

  try {
    if (!entry) {
      window.localStorage.removeItem(DAILY_SNAPSHOT_KEY);
      return;
    }

    window.localStorage.setItem(DAILY_SNAPSHOT_KEY, JSON.stringify(entry));
  } catch {
    // Ignore storage quota and browser privacy mode errors.
  }
};

function App() {
  const [loading, setLoading] = useState(false);
  const [summaryLoading, setSummaryLoading] = useState(false);
  const [error, setError] = useState('');
  const [articles, setArticles] = useState([]);
  const [summary, setSummary] = useState(null);
  const [totalArticles, setTotalArticles] = useState(0);
  
  // Individual article summaries
  const [articleSummaries, setArticleSummaries] = useState({});
  const [articleSummaryLoading, setArticleSummaryLoading] = useState({});
  
  // Filter states
  const [voice, setVoice] = useState('Bắc');
  const [time, setTime] = useState('pd');
  const [source, setSource] = useState('all');
  const [searchQuery, setSearchQuery] = useState('');
  const [searchHistory, setSearchHistory] = useState([]);
  const [historyReady, setHistoryReady] = useState(false);
  const [summaryTtsJobs, setSummaryTtsJobs] = useState(() => loadTtsStateMapFromStorage(SUMMARY_TTS_STORAGE_KEY));
  const [articleTtsJobs, setArticleTtsJobs] = useState(() => loadTtsStateMapFromStorage(ARTICLE_TTS_STORAGE_KEY));
  const [isMobileSummaryOpen, setIsMobileSummaryOpen] = useState(false);
  const [useDailyHomeLayout, setUseDailyHomeLayout] = useState(true);
  const hasBootstrappedRef = useRef(false);
  const handleSearchRef = useRef(() => {});

  const closeMobileSummaryPanel = () => {
    setIsMobileSummaryOpen(false);
  };

  const toggleMobileSummaryPanel = () => {
    setIsMobileSummaryOpen((previous) => !previous);
  };

  useEffect(() => {
    if (!historyReady || typeof window === 'undefined') return;

    try {
      const manualHistory = searchHistory.filter((entry) => !entry.autoDaily);
      window.localStorage.setItem(HISTORY_KEY, JSON.stringify(manualHistory));
    } catch {
      // Ignore storage quota and browser privacy mode errors.
    }
  }, [searchHistory, historyReady]);

  useEffect(() => {
    saveTtsStateMapToStorage(SUMMARY_TTS_STORAGE_KEY, summaryTtsJobs);
  }, [summaryTtsJobs]);

  useEffect(() => {
    saveTtsStateMapToStorage(ARTICLE_TTS_STORAGE_KEY, articleTtsJobs);
  }, [articleTtsJobs]);

  useEffect(() => {
    const pendingSummaryJobs = Object.entries(summaryTtsJobs).filter(
      ([, state]) => state.key && ACTIVE_TTS_STATUSES.has(state.status)
    );
    const pendingArticleJobs = Object.entries(articleTtsJobs).filter(
      ([, state]) => state.key && ACTIVE_TTS_STATUSES.has(state.status)
    );

    if (pendingSummaryJobs.length === 0 && pendingArticleJobs.length === 0) {
      return;
    }

    let canceled = false;
    let pollTimer = null;

    const fetchJobState = async (state) => {
      try {
        const job = await apiService.getTtsJob(state.key);
        return toTtsStateFromJob(job, state);
      } catch (error) {
        if (error?.response?.status === 404) {
          return {
            ...state,
            status: 'failed',
            error: 'Không tìm thấy tiến trình TTS trên server.',
          };
        }

        return state;
      }
    };

    const pollPendingJobs = async () => {
      const [summaryUpdates, articleUpdates] = await Promise.all([
        Promise.all(
          pendingSummaryJobs.map(async ([slot, state]) => {
            const nextState = await fetchJobState(state);
            return [slot, nextState];
          })
        ),
        Promise.all(
          pendingArticleJobs.map(async ([slot, state]) => {
            const nextState = await fetchJobState(state);
            return [slot, nextState];
          })
        ),
      ]);

      if (canceled) return;

      if (summaryUpdates.length > 0) {
        setSummaryTtsJobs((previous) => {
          let changed = false;
          const next = { ...previous };

          summaryUpdates.forEach(([slot, nextState]) => {
            const currentState = previous[slot];
            if (!currentState || isSameTtsState(currentState, nextState)) return;
            next[slot] = normalizeTtsState(nextState);
            changed = true;
          });

          return changed ? next : previous;
        });
      }

      if (articleUpdates.length > 0) {
        setArticleTtsJobs((previous) => {
          let changed = false;
          const next = { ...previous };

          articleUpdates.forEach(([slot, nextState]) => {
            const currentState = previous[slot];
            if (!currentState || isSameTtsState(currentState, nextState)) return;
            next[slot] = normalizeTtsState(nextState);
            changed = true;
          });

          return changed ? next : previous;
        });
      }

      pollTimer = window.setTimeout(pollPendingJobs, 2200);
    };

    pollPendingJobs();

    return () => {
      canceled = true;
      if (pollTimer) {
        window.clearTimeout(pollTimer);
      }
    };
  }, [summaryTtsJobs, articleTtsJobs]);

  const mapBraveResultToArticle = (result) => {
    // Helper function to strip HTML tags
    const stripHtml = (html) => {
      if (!html) return '';
      const tmp = document.createElement('DIV');
      tmp.innerHTML = html;
      return tmp.textContent || tmp.innerText || '';
    };

    // Determine category color based on content or default
    // Map từ Brave subtype sang UI style
    const SUBTYPE_MAPPING = {
      // Tin tức / Bài viết chung
      article: { name: 'Tin tức', tone: 'news' },
      news: { name: 'Thời sự', tone: 'news' },

      // Mua sắm / Sản phẩm
      product: { name: 'Mua sắm', tone: 'commerce' },
      
      // Ẩm thực / Công thức
      recipe: { name: 'Ẩm thực', tone: 'culture' },
      
      // Hỏi đáp / Diễn đàn
      qa: { name: 'Hỏi đáp', tone: 'discussion' },
      discussion: { name: 'Thảo luận', tone: 'discussion' },
      
      // Đánh giá / Review
      review: { name: 'Review', tone: 'review' },
      
      // Video (Cái này thường nằm ở type 'video_result' nhưng map luôn cho chắc)
      video_result: { name: 'Video', tone: 'video' },
      
      // Phim ảnh
      movie: { name: 'Phim ảnh', tone: 'culture' },
      
      // Mặc định (generic)
      generic: { name: 'Kết quả', tone: 'generic' },
    };

    const getCategoryStyle = (subtype) => {
      const key = subtype?.toLowerCase() || 'generic';
      return SUBTYPE_MAPPING[key] || SUBTYPE_MAPPING.generic;
    };

    const style = getCategoryStyle(result.subtype);
    
    return {
      category: style.name,
      categoryTone: style.tone,
      source: result.profile?.name || result.meta_url?.hostname || 'Unknown',
      timeAgo: result.age || "",
      title: stripHtml(result.title) || 'Không có tiêu đề',
      description: stripHtml(result.description) || '',
      imageUrl: result.thumbnail?.src || result.thumbnail?.original || 'https://placehold.co/400x300?text=No+Image',
      imageAlt: stripHtml(result.title) || 'News image',
      articleUrl: result.url || '#'
    };
  };

  const applyHistorySnapshot = (entry) => {
    setError('');
    setLoading(false);
    setSummaryLoading(false);
    setArticleSummaries({});
    setArticleSummaryLoading({});

    setArticles(Array.isArray(entry.articles) ? entry.articles : []);
    setSummary(entry.summary || null);
    setTotalArticles(entry.totalArticles || entry.articles?.length || 0);
  };

  const upsertHistoryEntry = ({ query, articles: nextArticles, summary: nextSummary, totalCount, autoDaily = false }) => {
    const normalizedQuery = query.trim();
    if (!normalizedQuery || !Array.isArray(nextArticles) || nextArticles.length === 0) return;

    const entry = {
      id: createHistoryId(),
      query: normalizedQuery,
      createdAt: new Date().toISOString(),
      dayKey: getLocalDayKey(),
      autoDaily,
      filters: {
        voice,
        time,
        source,
      },
      articles: nextArticles,
      summary: nextSummary || '',
      summaryReady: Boolean(nextSummary && nextSummary.trim().length > 0),
      totalArticles: totalCount || nextArticles.length,
    };

    if (autoDaily) {
      saveDailySnapshotToStorage(entry);
      return;
    }

    setSearchHistory((previous) => {
      return [entry, ...previous].slice(0, MAX_HISTORY_ITEMS);
    });
  };

  const handleHistorySelect = (entry) => {
    if (!entry) return;

    const selectedEntry = searchHistory.find((item) => item.id === entry.id) || entry;
    const hasSnapshot = (selectedEntry.articles?.length || 0) > 0 || Boolean(selectedEntry.summary);
    const shouldUseHomeLayout = Boolean(selectedEntry.autoDaily && selectedEntry.dayKey === getLocalDayKey());
    setUseDailyHomeLayout(shouldUseHomeLayout);

    setSearchQuery(selectedEntry.query || '');
    setVoice(selectedEntry.filters?.voice || 'Bắc');
    setTime(selectedEntry.filters?.time || 'pd');
    setSource(selectedEntry.filters?.source || 'all');
    closeMobileSummaryPanel();

    if (hasSnapshot) {
      applyHistorySnapshot(selectedEntry);

      setSearchHistory((previous) => {
        const filtered = previous.filter((item) => item.id !== selectedEntry.id);
        return [selectedEntry, ...filtered].slice(0, MAX_HISTORY_ITEMS);
      });
      return;
    }

    handleSearch(selectedEntry.query, { autoDaily: false });
  };

  const handleArticleSummarize = async (articleUrl, index) => {
    const currentSummary = articleSummaries[index];
    
    // If summary exists, toggle visibility
    if (currentSummary?.content) {
      setArticleSummaries(prev => ({
        ...prev,
        [index]: {
          ...prev[index],
          visible: !prev[index].visible
        }
      }));
      return;
    }

    // If no summary yet, fetch it
    setArticleSummaryLoading(prev => ({ ...prev, [index]: true }));
    const articleTtsSlot = getArticleTtsSlot(articleUrl, index);
    
    try {
      const data = await apiService.scrape(articleUrl);
      const summaryData = await apiService.summarizeNews(data.text, data.title);
      
      setArticleSummaries(prev => ({
        ...prev,
        [index]: {
          content: summaryData.summary,
          visible: true
        }
      }));

      setArticleTtsJobs((previous) => {
        if (!previous[articleTtsSlot]) return previous;
        const next = { ...previous };
        delete next[articleTtsSlot];
        return next;
      });
    } catch (err) {
      console.error('Article summarize error:', err);
      setArticleSummaries(prev => ({
        ...prev,
        [index]: {
          content: 'Không thể tóm tắt bài viết này: ' + (err.response?.data?.error || err.message),
          visible: true
        }
      }));
    } finally {
      setArticleSummaryLoading(prev => ({ ...prev, [index]: false }));
    }
  };

  const handleGenerateSummaryTts = async () => {
    const summaryText = typeof summary === 'string' ? summary.trim() : '';
    if (!summaryText) return;

    const signature = getSummarySignature(summaryText);
    if (!signature) return;

    const currentState = summaryTtsJobs[signature] || createIdleTtsState();
    if (ACTIVE_TTS_STATUSES.has(currentState.status)) return;

    setSummaryTtsJobs((previous) => ({
      ...previous,
      [signature]: {
        ...normalizeTtsState(previous[signature]),
        status: 'queued',
        audioUrl: '',
        error: '',
      },
    }));

    try {
      const createdJob = await apiService.createTtsJob(summaryText, { language: 'vi' });

      if (!createdJob?.key) {
        throw new Error('Không nhận được key TTS từ server.');
      }

      setSummaryTtsJobs((previous) => ({
        ...previous,
        [signature]: {
          ...normalizeTtsState(previous[signature]),
          key: createdJob.key,
          status: createdJob.status || 'queued',
          createdAt: createdJob.createdAt || previous[signature]?.createdAt || '',
          error: '',
        },
      }));
    } catch (err) {
      setSummaryTtsJobs((previous) => ({
        ...previous,
        [signature]: {
          ...normalizeTtsState(previous[signature]),
          status: 'failed',
          error: getTtsErrorMessage(err, 'Không thể tạo audio cho bản tóm tắt.'),
        },
      }));
    }
  };

  const handleGenerateArticleTts = async (articleUrl, index) => {
    const summaryText = articleSummaries[index]?.content?.trim();
    const slot = getArticleTtsSlot(articleUrl, index);

    if (!summaryText || summaryText.startsWith('Không thể tóm tắt')) {
      setArticleTtsJobs((previous) => ({
        ...previous,
        [slot]: {
          ...normalizeTtsState(previous[slot]),
          status: 'failed',
          error: 'Hãy tạo bản tóm tắt hợp lệ trước khi chuyển thành giọng nói.',
          audioUrl: '',
        },
      }));
      return;
    }

    const currentState = articleTtsJobs[slot] || createIdleTtsState();
    if (ACTIVE_TTS_STATUSES.has(currentState.status)) return;

    setArticleTtsJobs((previous) => ({
      ...previous,
      [slot]: {
        ...normalizeTtsState(previous[slot]),
        status: 'queued',
        audioUrl: '',
        error: '',
      },
    }));

    try {
      const createdJob = await apiService.createTtsJob(summaryText, { language: 'vi' });

      if (!createdJob?.key) {
        throw new Error('Không nhận được key TTS từ server.');
      }

      setArticleTtsJobs((previous) => ({
        ...previous,
        [slot]: {
          ...normalizeTtsState(previous[slot]),
          key: createdJob.key,
          status: createdJob.status || 'queued',
          createdAt: createdJob.createdAt || previous[slot]?.createdAt || '',
          error: '',
        },
      }));
    } catch (err) {
      setArticleTtsJobs((previous) => ({
        ...previous,
        [slot]: {
          ...normalizeTtsState(previous[slot]),
          status: 'failed',
          error: getTtsErrorMessage(err, 'Không thể tạo audio cho bài viết này.'),
        },
      }));
    }
  };

  const handleDailyCardSummarize = async (articleUrl) => {
    if (!articleUrl || articleUrl === '#') return;

    setError('');
    setSummaryLoading(true);

    try {
      const data = await apiService.scrape(articleUrl);
      const summaryData = await apiService.summarizeNews(data.text, data.title);
      setSummary(summaryData.summary || '');
      setTotalArticles(1);
      setIsMobileSummaryOpen(true);
    } catch (err) {
      setError('Không thể tóm tắt bài viết này: ' + (err.response?.data?.error || err.message));
    } finally {
      setSummaryLoading(false);
    }
  };

  const handleSearch = async (rawQuery = searchQuery, options = {}) => {
    const { autoDaily = false } = options;
    const query = rawQuery.trim();
    if (!query) return;

    closeMobileSummaryPanel();
    setUseDailyHomeLayout(Boolean(autoDaily));
    setSearchQuery(query);

    setLoading(true);
    setSummaryLoading(false);
    setError('');
    setSummary(null);
    setTotalArticles(0);
    setArticles([]);
    setArticleSummaries({});
    setArticleSummaryLoading({});
    const isUrl = /^https?:\/\//i.test(query);
    let nextArticles = [];
    let nextSummary = '';
    let nextTotalArticles = 0;
    
    try {
      if (isUrl) {
        // Scrape the URL and summarize
        const data = await apiService.scrape(query);
        console.log('Scraped data:', data);
        
        // Create article from scraped content
        const article = {
          category: "Tin tức",
          categoryTone: 'news',
          source: new URL(query).hostname,
          timeAgo: "Vừa xong",
          title: data.title || 'Không có tiêu đề',
          description: data.text?.substring(0, 200) + '...' || '',
          imageUrl: 'https://placehold.co/400x300?text=No+Image',
          imageAlt: data.title || 'Scraped content',
          articleUrl: query
        };

        nextArticles = [article];
        setArticles(nextArticles);
        setLoading(false);
        setSummaryLoading(true);
        
        // Tóm tắt bài báo đơn lẻ
        try {
          const summaryData = await apiService.summarizeNews(data.text, data.title);
          nextSummary = summaryData.summary || '';
          nextTotalArticles = 1;
          setSummary(nextSummary || null);
          setTotalArticles(1);
        } catch (err) {
          console.error('Summarize error:', err);
          setError('Không thể tóm tắt bài viết này.');
        } finally {
          setSummaryLoading(false);
        }
      } else {
        // Search first to show articles immediately
        const searchOptions = {
          freshness: time,
          language: source === 'all' ? 'vi' : source
        };
        
        console.log('Searching...');
        const searchData = await apiService.search(query, searchOptions);
        console.log('Search results:', searchData);
        
        // Check for family_friendly at the top level
        if (searchData.web?.family_friendly === false || searchData.news?.family_friendly === false) {
          setError('Kết quả tìm kiếm chứa nội dung không phù hợp. Vui lòng thử từ khóa khác.');
          setArticles([]);
          setLoading(false);
          return;
        }
        
        // Map Brave results to articles and show immediately
        let urls = [];
        let hasUnsafeContent = false;
        
        if (searchData.news?.results && searchData.news.results.length > 0) {
          // Check for unsafe content
          const unsafeResults = searchData.news.results.filter(r => r.family_friendly === false);
          if (unsafeResults.length > 0) {
            hasUnsafeContent = true;
          }
          
          const mappedArticles = searchData.news.results
            .filter(result => {
              // Loại bỏ nội dung không phù hợp
              if (result.family_friendly === false) {
                return false;
              }
              // Loại bỏ video và image results
              const isVideoType = result.type === 'video_result' || result.subtype === 'video';
              const hasVideo = result.video !== undefined;
              const isImage = result.type === 'image_result';
              const isVideoUrl = result.url?.includes('youtube.com') || 
                                  result.url?.includes('tiktok.com') || 
                                  result.url?.includes('youtu.be');
              return !isVideoType && !hasVideo && !isImage && !isVideoUrl;
            })
            .slice(0, 10)
            .map((result) => mapBraveResultToArticle(result));
          
          // Check if all results were filtered out
          if (mappedArticles.length === 0) {
            if (hasUnsafeContent) {
              setError('Kết quả tìm kiếm chứa nội dung không phù hợp. Vui lòng thử từ khóa khác.');
            } else {
              setError('Không tìm thấy kết quả nào');
            }
            setArticles([]);
            setLoading(false);
            return;
          }
          
          nextArticles = mappedArticles;
          setArticles(nextArticles);
          urls = searchData.news.results
            .filter(result => {
              if (result.family_friendly === false) {
                return false;
              }
              const isVideoType = result.type === 'video_result' || result.subtype === 'video';
              const hasVideo = result.video !== undefined;
              const isImage = result.type === 'image_result';
              const isVideoUrl = result.url?.includes('youtube.com') || 
                                  result.url?.includes('tiktok.com') || 
                                  result.url?.includes('youtu.be');
              return !isVideoType && !hasVideo && !isImage && !isVideoUrl;
            })
            .slice(0, 10)
            .map(r => r.url);
        } else if (searchData.web?.results && searchData.web.results.length > 0) {
          // Check for unsafe content
          const unsafeResults = searchData.web.results.filter(r => r.family_friendly === false);
          if (unsafeResults.length > 0) {
            hasUnsafeContent = true;
          }
          
          const mappedArticles = searchData.web.results
            .filter(result => {
              // Loại bỏ nội dung không phù hợp
              if (result.family_friendly === false) {
                return false;
              }
              // Chỉ lấy search_result thông thường, bỏ video/image
              const isSearchResult = result.type === 'search_result';
              const isVideoType = result.subtype === 'video';
              const hasVideo = result.video !== undefined;
              const isImage = result.type === 'image_result';
              const isVideoUrl = result.url?.includes('youtube.com') || 
                                  result.url?.includes('tiktok.com') || 
                                  result.url?.includes('youtu.be');
              return isSearchResult && !isVideoType && !hasVideo && !isImage && !isVideoUrl;
            })
            .slice(0, 10)
            .map((result) => mapBraveResultToArticle(result));
          
          // Check if all results were filtered out
          if (mappedArticles.length === 0) {
            if (hasUnsafeContent) {
              setError('Kết quả tìm kiếm chứa nội dung không phù hợp. Vui lòng thử từ khóa khác.');
            } else {
              setError('Không tìm thấy kết quả nào');
            }
            setArticles([]);
            setLoading(false);
            return;
          }
          
          nextArticles = mappedArticles;
          setArticles(nextArticles);
          urls = searchData.web.results
            .filter(result => {
              if (result.family_friendly === false) {
                return false;
              }
              const isSearchResult = result.type === 'search_result';
              const isVideoType = result.subtype === 'video';
              const hasVideo = result.video !== undefined;
              const isImage = result.type === 'image_result';
              const isVideoUrl = result.url?.includes('youtube.com') || 
                                  result.url?.includes('tiktok.com') || 
                                  result.url?.includes('youtu.be');
              return isSearchResult && !isVideoType && !hasVideo && !isImage && !isVideoUrl;
            })
            .slice(0, 10)
            .map(r => r.url);
        } else {
          setError('Không tìm thấy kết quả nào');
          setArticles([]);
          setLoading(false);
          return;
        }
        
        // Now summarize in background
        setLoading(false); // End search loading
        setSummaryLoading(true); // Start summary loading
        
        try {
          console.log('Summarizing articles...');
          const data = await apiService.scrapeAndSummarize(urls, query);
          console.log('Summary results:', data);
          
          if (data.summary) {
            nextSummary = data.summary;
            nextTotalArticles = data.totalArticles || nextArticles.length;
            setSummary(nextSummary);
            setTotalArticles(nextTotalArticles);
          }
        } catch (err) {
          console.error('Summarize error:', err);
          setError('Không thể tóm tắt: ' + (err.response?.data?.error || err.message));
        } finally {
          setSummaryLoading(false);
        }
      }

      if (nextArticles.length > 0) {
        upsertHistoryEntry({
          query,
          articles: nextArticles,
          summary: nextSummary,
          totalCount: nextTotalArticles || nextArticles.length,
          autoDaily,
        });
      }
    } catch (err) {
      setError(err.response?.data?.error || 'Đã xảy ra lỗi khi xử lý yêu cầu');
      console.error('Error:', err);
      setLoading(false);
      setSummaryLoading(false);
    } finally {
      // Ensure loading is stopped
      if (isUrl) {
        setLoading(false);
      }
    }
  };

  const handleDailyResummary = async () => {
    if (loading || summaryLoading) return;

    const urls = articles
      .map((article) => article.articleUrl)
      .filter((url) => typeof url === 'string' && /^https?:\/\//i.test(url));

    if (urls.length === 0) {
      setError('Không có bài viết hợp lệ để tóm tắt lại.');
      return;
    }

    const dailyQuery = getDailyAutoQuery();

    setError('');
    setSummaryLoading(true);

    try {
      const data = await apiService.scrapeAndSummarize(urls, dailyQuery);
      const nextSummary = data.summary || '';

      if (!nextSummary.trim()) {
        setError('Không nhận được bản tóm tắt mới. Vui lòng thử lại.');
        return;
      }

      const nextTotalArticles = data.totalArticles || urls.length;
      setSummary(nextSummary);
      setTotalArticles(nextTotalArticles);

      upsertHistoryEntry({
        query: dailyQuery,
        articles,
        summary: nextSummary,
        totalCount: nextTotalArticles,
        autoDaily: true,
      });
    } catch (err) {
      setError('Không thể tóm tắt lại: ' + (err.response?.data?.error || err.message));
    } finally {
      setSummaryLoading(false);
    }
  };

  handleSearchRef.current = handleSearch;

  const summarySignature = getSummarySignature(summary || '');
  const summaryTtsState = summarySignature
    ? normalizeTtsState(summaryTtsJobs[summarySignature])
    : createIdleTtsState();

  // Bootstrap cache on first render:
  // 1) Load manual search history for sidebar
  // 2) Load today's daily snapshot from dedicated storage
  // 3) Otherwise trigger daily auto-search once
  useEffect(() => {
    if (hasBootstrappedRef.current) return;
    hasBootstrappedRef.current = true;

    const persistedHistory = loadHistoryFromStorage();
    const persistedDailySnapshot = loadDailySnapshotFromStorage();
    setSearchHistory(persistedHistory);
    setHistoryReady(true);

    const todayKey = getLocalDayKey();
    const dailyAutoQuery = getDailyAutoQuery();
    const todayAutoEntry =
      persistedDailySnapshot &&
      persistedDailySnapshot.dayKey === todayKey &&
      persistedDailySnapshot.articles.length > 0 &&
      persistedDailySnapshot.summaryReady
        ? persistedDailySnapshot
        : null;

    if (todayAutoEntry) {
      setSearchQuery(dailyAutoQuery);
      setUseDailyHomeLayout(true);
      setVoice(todayAutoEntry.filters?.voice || 'Bắc');
      setTime(todayAutoEntry.filters?.time || 'pd');
      setSource(todayAutoEntry.filters?.source || 'all');
      applyHistorySnapshot(todayAutoEntry);
      return;
    }

    setSearchQuery(dailyAutoQuery);
    handleSearchRef.current(dailyAutoQuery, { autoDaily: true });
  }, []);

  return (
    <div className="min-h-screen bg-background text-on-background font-body selection:bg-black selection:text-white">
      <aside className="hidden lg:fixed lg:inset-y-0 lg:left-0 lg:z-40 lg:flex lg:w-72 lg:flex-col lg:border-r lg:border-black/10 lg:bg-white lg:px-8 lg:py-8">
        <div className="mb-10 flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center bg-black text-white">
            <span className="material-symbols-outlined text-2xl">neurology</span>
          </div>
          <div>
            <h1 className="text-xl font-black uppercase tracking-tight">NewsAI</h1>
            <p className="mt-1 text-[10px] font-extrabold uppercase tracking-[0.2em] text-slate-500">
              Digital Curator
            </p>
          </div>
        </div>

        <div className="flex-1">
          <h2 className="mb-5 flex items-center gap-2 text-[11px] font-black uppercase tracking-[0.15em] text-black">
            <span className="material-symbols-outlined text-lg">history</span>
            Lịch sử tìm kiếm
          </h2>

          {searchHistory.length > 0 ? (
            <div className="flex flex-col gap-1">
              {searchHistory.map((item) => (
                <button
                  key={item.id}
                  type="button"
                  onClick={() => handleHistorySelect(item)}
                  className="group flex items-center gap-3 rounded-lg px-4 py-3 text-left transition-all hover:bg-slate-50"
                >
                  <span className="material-symbols-outlined text-lg opacity-40 transition-all group-hover:text-black group-hover:opacity-100">
                    history
                  </span>
                  <span className="truncate text-sm font-medium text-slate-600 group-hover:text-black">
                    {item.query}
                  </span>
                </button>
              ))}
            </div>
          ) : (
            <p className="rounded-lg border border-dashed border-slate-200 p-4 text-sm text-slate-400">
              Chưa có lượt tìm kiếm nào.
            </p>
          )}
        </div>

        <button
          type="button"
          className="mt-auto flex items-center gap-3 rounded-lg px-4 py-3 text-slate-500 transition-all hover:bg-slate-50 hover:text-black"
        >
          <span className="material-symbols-outlined">settings</span>
          <span className="text-sm font-bold">Cài đặt</span>
        </button>
      </aside>

      <main className="relative w-full lg:pl-72">
        <div className="w-full px-2 pb-12 pt-4 md:px-4 lg:px-6 lg:pt-6">
        <section className="mb-8 rounded-xl border border-black/10 bg-white p-5 lg:hidden">
          <div className="mb-4 flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center bg-black text-white">
              <span className="material-symbols-outlined text-2xl">neurology</span>
            </div>
            <div>
              <h1 className="text-xl font-black uppercase tracking-tight">NewsAI</h1>
              <p className="text-[10px] font-extrabold uppercase tracking-[0.2em] text-slate-500">Digital Curator</p>
            </div>
          </div>

          <div className="flex items-center gap-2 overflow-x-auto pb-1">
            {searchHistory.length > 0 ? searchHistory.map((item) => (
              <button
                key={`mobile-${item.id}`}
                type="button"
                onClick={() => handleHistorySelect(item)}
                className="whitespace-nowrap rounded-full border border-black/20 px-3 py-1.5 text-xs font-bold text-slate-600 transition-all hover:border-black hover:text-black"
              >
                {item.query}
              </button>
            )) : (
              <p className="text-xs font-medium text-slate-400">Lịch sử tìm kiếm sẽ xuất hiện tại đây.</p>
            )}
          </div>
        </section>

        <header className="mb-8">
          <div className="w-full">
            <SearchBox
              value={searchQuery}
              onChange={setSearchQuery}
              onSearch={handleSearch}
              loading={loading}
            />
            <div className="mt-7">
              <FilterBar
                voice={voice}
                onVoiceChange={setVoice}
                time={time}
                onTimeChange={setTime}
                source={source}
                onSourceChange={setSource}
              />
            </div>
            {error && (
              <div className="mt-6 border border-red-300 bg-red-50 px-4 py-3 text-sm font-medium text-red-700">
                {error}
              </div>
            )}
          </div>
        </header>

        <div className="grid items-start gap-6 xl:grid-cols-2">
          <section>
            <div className="mb-10 flex items-center justify-between border-b border-black pb-4">
              <h2 className="text-2xl font-black uppercase tracking-tight">
                {useDailyHomeLayout ? 'Bản tin đầu ngày' : 'Kết quả tìm kiếm'}
              </h2>
              {!useDailyHomeLayout && (
                <div className="flex items-center gap-1 text-[10px] font-black uppercase tracking-[0.2em] text-black/70">
                  <span>Sắp xếp: Mới nhất</span>
                  <span className="material-symbols-outlined text-sm">swap_vert</span>
                </div>
              )}
            </div>

            {useDailyHomeLayout ? (
              <HomeNewsGrid
                articles={articles}
                loading={loading}
                onSummarizeArticle={handleDailyCardSummarize}
              />
            ) : (
              <>
                {loading && (
                  <div className="flex min-h-56 flex-col items-center justify-center rounded-xl border border-black/10 bg-white text-center">
                    <span className="material-symbols-outlined animate-spin text-4xl text-black/40">progress_activity</span>
                    <p className="mt-3 text-sm font-semibold text-slate-500">Đang phân tích và tìm bài viết...</p>
                  </div>
                )}

                {!loading && articles.length === 0 && (
                  <div className="flex min-h-56 flex-col items-center justify-center rounded-xl border border-dashed border-black/20 bg-white text-center">
                    <span className="material-symbols-outlined text-6xl text-black/20">search</span>
                    <p className="mt-4 text-lg font-medium text-slate-500">
                      Nhập từ khóa hoặc đường dẫn bài báo để bắt đầu.
                    </p>
                  </div>
                )}

                {!loading && articles.length > 0 && (
                  <div className="space-y-12">
                    {articles.map((article, index) => (
                      <NewsArticle
                        key={`${article.articleUrl}-${index}`}
                        {...article}
                        onSummarize={() => handleArticleSummarize(article.articleUrl, index)}
                        onGenerateTts={() => handleGenerateArticleTts(article.articleUrl, index)}
                        summary={articleSummaries[index]?.content}
                        summaryVisible={articleSummaries[index]?.visible}
                        summaryLoading={articleSummaryLoading[index]}
                        ttsStatus={articleTtsJobs[getArticleTtsSlot(article.articleUrl, index)]?.status || 'idle'}
                        ttsAudioUrl={articleTtsJobs[getArticleTtsSlot(article.articleUrl, index)]?.audioUrl || ''}
                        ttsError={articleTtsJobs[getArticleTtsSlot(article.articleUrl, index)]?.error || ''}
                      />
                    ))}
                  </div>
                )}
              </>
            )}
          </section>

          <aside className="hidden md:block xl:sticky xl:top-8">
            <SummaryBox
              summary={summary}
              totalArticles={totalArticles}
              loading={summaryLoading}
              onGenerateTts={handleGenerateSummaryTts}
              ttsStatus={summaryTtsState.status}
              ttsAudioUrl={summaryTtsState.audioUrl}
              ttsError={summaryTtsState.error}
              onResummarize={useDailyHomeLayout ? handleDailyResummary : undefined}
              resummarizeDisabled={loading || summaryLoading || articles.length === 0}
            />
          </aside>
        </div>

        <div className="fixed bottom-5 right-5 z-40 md:hidden">
          <button
            type="button"
            onClick={toggleMobileSummaryPanel}
            aria-expanded={isMobileSummaryOpen}
            className="flex items-center gap-2 rounded-full border border-black bg-black px-5 py-3 text-xs font-black uppercase tracking-[0.14em] text-white shadow-lg transition-all hover:bg-slate-800"
          >
            <span className={`material-symbols-outlined text-base ${summaryLoading ? 'animate-spin' : ''}`}>
              {summaryLoading ? 'progress_activity' : isMobileSummaryOpen ? 'close' : 'summarize'}
            </span>
            {summaryLoading ? 'Đang tóm tắt' : isMobileSummaryOpen ? 'Đóng tóm tắt' : 'Mở tóm tắt'}
          </button>
        </div>

        <div
          className={`fixed inset-0 z-50 md:hidden ${isMobileSummaryOpen ? 'pointer-events-auto' : 'pointer-events-none'}`}
          aria-hidden={!isMobileSummaryOpen}
          onClick={closeMobileSummaryPanel}
        >
          <div
            className={`absolute inset-0 bg-black/45 transition-opacity duration-300 ${isMobileSummaryOpen ? 'opacity-100' : 'opacity-0'}`}
          />

          <section
            onClick={(event) => event.stopPropagation()}
            className={`absolute bottom-0 left-0 right-0 max-h-[88vh] overflow-y-auto rounded-t-2xl border-t-2 border-black bg-white p-4 transition-transform duration-300 ${isMobileSummaryOpen ? 'translate-y-0' : 'translate-y-full'}`}
          >
            <div className="mb-3 flex items-center justify-between">
              <h3 className="text-sm font-black uppercase tracking-[0.15em] text-black">Tóm tắt thông minh</h3>
              <button
                type="button"
                onClick={(event) => {
                  event.preventDefault();
                  event.stopPropagation();
                  closeMobileSummaryPanel();
                }}
                className="rounded-full border border-black/20 p-2 text-black transition-all hover:bg-slate-100"
                aria-label="Đóng"
              >
                <span className="material-symbols-outlined">close</span>
              </button>
            </div>

            <SummaryBox
              summary={summary}
              totalArticles={totalArticles}
              loading={summaryLoading}
              onGenerateTts={handleGenerateSummaryTts}
              ttsStatus={summaryTtsState.status}
              ttsAudioUrl={summaryTtsState.audioUrl}
              ttsError={summaryTtsState.error}
              onResummarize={useDailyHomeLayout ? handleDailyResummary : undefined}
              resummarizeDisabled={loading || summaryLoading || articles.length === 0}
            />
          </section>
        </div>

        <footer className="mt-16 border-t border-black/10 pt-8 text-center">
          <p className="text-xs leading-relaxed text-slate-500">
            AI có thể mắc lỗi. Hãy kiểm tra lại thông tin quan trọng.
            <br />
            Được xây dựng bởi <span className="font-bold text-black/70">HCMUS - Machine Learning - 23KHDL1 - Nhóm 4</span>
          </p>
        </footer>
        </div>
      </main>
    </div>
  )
}

export default App
