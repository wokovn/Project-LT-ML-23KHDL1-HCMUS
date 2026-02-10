import Navbar from './components/Navbar'
import Hero from './components/Hero'
import SearchBox from './components/SearchBox'
import FilterBar from './components/FilterBar'
import NewsArticle from './components/NewsArticle'
import './App.css'

function App() {
  const articles = [
    {
      category: "Kinh tế",
      categoryColor: "bg-blue-50 text-blue-600",
      source: "VnExpress",
      timeAgo: "2 giờ trước",
      title: "Giá vàng SJC tiếp tục lập đỉnh mới, vượt mốc 80 triệu đồng/lượng",
      description: "Sáng nay, giá vàng SJC trong nước tiếp tục đà tăng mạnh, chính thức vượt qua mốc lịch sử 80 triệu đồng mỗi lượng. Các chuyên gia nhận định biến động này chịu ảnh hưởng lớn từ thị trường thế giới và nhu cầu tích trữ cuối năm tăng cao...",
      imageUrl: "https://lh3.googleusercontent.com/aida-public/AB6AXuAHQK_DJaRIYVpQqBaMCtZCwm0qJ2lIIAYE7BHijZwWo4YQGbUJWcmRrWwpzrLr7N0_w7b96S-dTcCT9QT2_hYX9e6Fn4iHCg5x4X6EhEzG8nDmPrcFEjsJFEz7lE55sy8KOyI4kMCpXEsuJoHUEhsMRrP1ZMFs5FjXnnA27RpA4EHJm4QOHmr75rlB6KkmQY1v1mxpQNj4-Zo4x8b4EuuXBIfhfYNN_L4HYMmtzSC-hnAdQCdGd5CjLC-r9Y4opNfJoYY1k9OkS1w",
      imageAlt: "Vàng SJC",
      voiceType: "Bắc",
      articleUrl: "#"
    },
    {
      category: "Công nghệ",
      categoryColor: "bg-green-50 text-green-600",
      source: "Tuổi Trẻ",
      timeAgo: "5 giờ trước",
      title: "Việt Nam đặt mục tiêu phổ cập 5G vào năm 2025",
      description: "Bộ Thông tin và Truyền thông vừa công bố lộ trình phổ cập mạng 5G trên toàn quốc. Theo đó, đến năm 2025, 100% dân số sẽ được tiếp cận với hạ tầng mạng di động thế hệ mới, mở đường cho phát triển kinh tế số...",
      imageUrl: "https://lh3.googleusercontent.com/aida-public/AB6AXuBrkQ2BBQBgsy-3HhjUw7R26kS3eKrNLBlhGWTid8HXuxX6X06qAwWsYThgHxKJxW-17cEo-28TZ0NUA3x2QQtl2PfWBmvgU8-CbbUj9R3bvyjNQPtEyH2GoCqqK73Py_sts5k24HWN5iO_OIwfdnIsa1sLHSsaqYGIrlzkuLOMyP2lfRQQnE7K4pFre3NTHZm0ZvJrwB_rzWi9AQDkT4CUPwOcCFSyLprwHNsHcQNiKI6ZbSVmXP7eljfX9JJubMcw93LZJjVMixg",
      imageAlt: "Công nghệ 5G",
      voiceType: "Nam",
      articleUrl: "#"
    },
    {
      category: "Giao thông",
      categoryColor: "bg-orange-50 text-orange-600",
      source: "Dân Trí",
      timeAgo: "8 giờ trước",
      title: "Hoàn thành cao tốc Bắc - Nam đoạn Diễn Châu - Bãi Vọt",
      description: "Dự án thành phần cao tốc Bắc - Nam phía Đông giai đoạn 1 đoạn Diễn Châu - Bãi Vọt đã chính thức thông xe kỹ thuật. Công trình giúp rút ngắn thời gian di chuyển từ Hà Nội về Nghệ An xuống còn hơn 3 giờ...",
      imageUrl: "https://lh3.googleusercontent.com/aida-public/AB6AXuBvOWzv5Wt7dypGPCUuBQcNXQN3dD8RbYO5n_BONKalLmqWjB2uTRDhCM9BN1LhATZLw0a--nzP5bveNszmigBUh0qVhE-eJbcIsBIC9kV3cMnRp3XyDVRgUDESXrI8HaZPDNkKVWfuxBhgzxdFkDf5E_V4XUK30oiYNRaUDa4Z80G58HWM_5SrO22qJvgzHDQkFfysg2HM8ETD-R5Z0hxcMdWHV8mvAWbBTle_FP-zK6BzbZc7_gU5BS057_N-C22BADd9g4OOBA8",
      imageAlt: "Cao tốc",
      voiceType: "Trung",
      articleUrl: "#"
    }
  ];

  return (
    <div className="bg-background-light text-slate-800 font-display h-screen flex flex-col overflow-y-auto selection:bg-gray-200">
      <Navbar />
      <main className="flex-1 flex flex-col items-center w-full max-w-5xl mx-auto px-4 py-12 md:py-20">
        <Hero />
        <div className="w-full max-w-3xl space-y-4">
          <SearchBox />
          <FilterBar />
        </div>
        <div className="w-full max-w-3xl mt-16 space-y-6">
          <h2 className="text-sm font-semibold text-gray-400 uppercase tracking-wider mb-4 pl-1">Kết quả tóm tắt mới nhất</h2>
          {articles.map((article, index) => (
            <NewsArticle key={index} {...article} />
          ))}
        </div>
        <div className="mt-20 text-center px-4 w-full">
          <p className="text-xs text-slate-400">
            AI có thể mắc lỗi. Hãy kiểm tra lại thông tin quan trọng. Được xây dựng bởi <span className="font-semibold text-slate-500">NewsAI Team</span>
          </p>
        </div>
      </main>
    </div>
  )
}

export default App
