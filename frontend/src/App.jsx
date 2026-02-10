import { useState } from 'react'
import Navbar from './components/Navbar'
import Hero from './components/Hero'
import SearchBox from './components/SearchBox'
import FilterBar from './components/FilterBar'
import NewsArticle from './components/NewsArticle'
import SummaryBox from './components/SummaryBox'
import apiService from './services/api.service'
import './App.css'

function App() {
  const [loading, setLoading] = useState(false);
  const [summaryLoading, setSummaryLoading] = useState(false);
  const [error, setError] = useState('');
  const [articles, setArticles] = useState([]);
  const [summary, setSummary] = useState(null);
  const [totalArticles, setTotalArticles] = useState(0);
  
  // Filter states
  const [voice, setVoice] = useState('Bắc');
  const [time, setTime] = useState('pd');
  const [source, setSource] = useState('all');

  const mapBraveResultToArticle = (result, index) => {
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
      article: { name: "Tin tức", color: "bg-blue-50 text-blue-600" },
      news: { name: "Thời sự", color: "bg-blue-50 text-blue-600" },

      // Mua sắm / Sản phẩm
      product: { name: "Mua sắm", color: "bg-green-50 text-green-600" },
      
      // Ẩm thực / Công thức
      recipe: { name: "Ẩm thực", color: "bg-orange-50 text-orange-600" },
      
      // Hỏi đáp / Diễn đàn
      qa: { name: "Hỏi đáp", color: "bg-purple-50 text-purple-600" },
      discussion: { name: "Thảo luận", color: "bg-purple-50 text-purple-600" },
      
      // Đánh giá / Review
      review: { name: "Review", color: "bg-pink-50 text-pink-600" },
      
      // Video (Cái này thường nằm ở type 'video_result' nhưng map luôn cho chắc)
      video_result: { name: "Video", color: "bg-red-50 text-red-600" },
      
      // Phim ảnh
      movie: { name: "Phim ảnh", color: "bg-indigo-50 text-indigo-600" },
      
      // Mặc định (generic)
      generic: { name: "Kết quả", color: "bg-gray-50 text-gray-600" },
    };

    const getCategoryStyle = (subtype) => {
      const key = subtype?.toLowerCase() || 'generic';
      return SUBTYPE_MAPPING[key] || SUBTYPE_MAPPING.generic;
    };

    const style = getCategoryStyle(result.subtype);
    
    return {
      category: style.name,
      categoryColor: style.color,
      source: result.profile?.name || result.meta_url?.hostname || 'Unknown',
      timeAgo: result.age || "",
      title: stripHtml(result.title) || 'Không có tiêu đề',
      description: stripHtml(result.description) || '',
      imageUrl: result.thumbnail?.src || result.thumbnail?.original || 'https://placehold.co/400x300?text=No+Image',
      imageAlt: stripHtml(result.title) || 'News image',
      voiceType: ['Bắc', 'Nam', 'Trung'][index % 3],
      articleUrl: result.url || '#'
    };
  };

  const handleSearch = async (query) => {
    setLoading(true);
    setError('');
    setSummary(null);
    setTotalArticles(0);
    
    try {
      // Check if it's a URL or search query
      const isUrl = query.startsWith('http://') || query.startsWith('https://');
      
      if (isUrl) {
        // Scrape the URL and summarize
        const data = await apiService.scrape(query);
        console.log('Scraped data:', data);
        
        // Create article from scraped content
        const article = {
          category: "Tin tức",
          categoryColor: "bg-blue-50 text-blue-600",
          source: new URL(query).hostname,
          timeAgo: "Vừa xong",
          title: data.title || 'Không có tiêu đề',
          description: data.text?.substring(0, 200) + '...' || '',
          imageUrl: 'https://placehold.co/400x300?text=Scraped+Content',
          imageAlt: data.title || 'Scraped content',
          articleUrl: query
        };
        
        setArticles([article]);
        
        // Tóm tắt bài báo đơn lẻ
        try {
          const summaryData = await apiService.summarizeNews(data.text, data.title);
          setSummary(summaryData.summary);
          setTotalArticles(1);
        } catch (err) {
          console.error('Summarize error:', err);
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
        
        // Map Brave results to articles and show immediately
        let urls = [];
        if (searchData.news?.results && searchData.news.results.length > 0) {
          const mappedArticles = searchData.news.results
            .slice(0, 10)
            .map((result, index) => mapBraveResultToArticle(result, index));
          setArticles(mappedArticles);
          urls = searchData.news.results.slice(0, 10).map(r => r.url);
        } else if (searchData.web?.results && searchData.web.results.length > 0) {
          const mappedArticles = searchData.web.results
            .filter(result => result.type === 'search_result')
            .slice(0, 10)
            .map((result, index) => mapBraveResultToArticle(result, index));
          setArticles(mappedArticles);
          urls = searchData.web.results
            .filter(r => r.type === 'search_result')
            .slice(0, 10)
            .map(r => r.url);
        } else {
          setError('Không tìm thấy kết quả nào');
          setArticles([]);
          return;
        }
        
        // Now summarize in background
        setLoading(false); // End search loading
        setSummaryLoading(true); // Start summary loading
        
        try {
          console.log('Summarizing articles...');
          const data = await apiService.scrapeAndSummarize(urls);
          console.log('Summary results:', data);
          
          if (data.summary) {
            setSummary(data.summary);
            setTotalArticles(data.totalArticles || 0);
          }
        } catch (err) {
          console.error('Summarize error:', err);
          setError('Không thể tóm tắt: ' + (err.response?.data?.error || err.message));
        } finally {
          setSummaryLoading(false);
        }
      }
    } catch (err) {
      setError(err.response?.data?.error || 'Đã xảy ra lỗi khi xử lý yêu cầu');
      console.error('Error:', err);
    } finally {
      // Only set loading false if not a search term (URL case)
      if (query.startsWith('http://') || query.startsWith('https://')) {
        setLoading(false);
      }
    }
  };

  return (
    <div className="bg-background-light text-slate-800 font-display h-screen flex flex-col overflow-y-auto selection:bg-gray-200">
      <Navbar />
      <main className="flex-1 flex flex-col items-center w-full max-w-5xl mx-auto px-4 py-12 md:py-20">
        <Hero />
        <div className="w-full max-w-3xl space-y-4">
          <SearchBox onSearch={handleSearch} loading={loading} />
          <FilterBar 
            voice={voice}
            onVoiceChange={setVoice}
            time={time}
            onTimeChange={setTime}
            source={source}
            onSourceChange={setSource}
          />
          {error && (
            <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg text-sm">
              {error}
            </div>
          )}
        </div>
        <div className="w-full max-w-3xl mt-16 space-y-6">
          {(summary || summaryLoading) && <SummaryBox summary={summary} totalArticles={totalArticles} loading={summaryLoading} />}
          <h2 className="text-sm font-semibold text-gray-400 uppercase tracking-wider mb-4 pl-1">Kết quả tóm tắt mới nhất</h2>
          {loading && (
            <div className="text-center py-8">
              <span className="material-symbols-outlined text-4xl text-slate-400 animate-spin">progress_activity</span>
              <p className="text-slate-500 mt-2">Đang xử lý...</p>
            </div>
          )}
          {!loading && articles.length === 0 && (
            <div className="text-center py-12">
              <span className="material-symbols-outlined text-6xl text-slate-300">search</span>
              <p className="text-slate-400 mt-4 text-lg">Nhập từ khóa hoặc liên kết bài báo để bắt đầu tìm kiếm</p>
            </div>
          )}
          {!loading && articles.length > 0 && articles.map((article, index) => (
            <NewsArticle key={index} {...article} />
          ))}
        </div>
        <div className="mt-20 text-center px-4 w-full">
          <p className="text-xs text-slate-400">
            AI có thể mắc lỗi. Hãy kiểm tra lại thông tin quan trọng. Được xây dựng bởi <span className="font-semibold text-slate-500">HCMUS - Machine Learning - 23KHDL1 - Nhóm 4 </span>
          </p>
        </div>
      </main>
    </div>
  )
}

export default App
