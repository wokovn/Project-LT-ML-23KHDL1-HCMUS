import { useState } from 'react'
import axios from 'axios'
import './App.css'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:5000'

function App() {
  const [activeTab, setActiveTab] = useState('search')
  const [loading, setLoading] = useState(false)
  
  // Search state
  const [searchQuery, setSearchQuery] = useState('')
  const [searchResults, setSearchResults] = useState(null)
  
  // Scrape state
  const [scrapeUrl, setScrapeUrl] = useState('')
  const [scrapeResults, setScrapeResults] = useState(null)
  
  // Gemini state
  const [geminiPrompt, setGeminiPrompt] = useState('')
  const [geminiResults, setGeminiResults] = useState(null)
  
  const [error, setError] = useState('')

  const handleSearch = async (e) => {
    e.preventDefault()
    setLoading(true)
    setError('')
    try {
      const response = await axios.post(`${API_URL}/api/search`, {
        query: searchQuery
      })
      setSearchResults(response.data)
    } catch (err) {
      setError(err.response?.data?.error || 'Failed to perform search')
    } finally {
      setLoading(false)
    }
  }

  const handleScrape = async (e) => {
    e.preventDefault()
    setLoading(true)
    setError('')
    try {
      const response = await axios.post(`${API_URL}/api/scrape`, {
        url: scrapeUrl
      })
      setScrapeResults(response.data)
    } catch (err) {
      setError(err.response?.data?.error || 'Failed to scrape URL')
    } finally {
      setLoading(false)
    }
  }

  const handleGemini = async (e) => {
    e.preventDefault()
    setLoading(true)
    setError('')
    try {
      const response = await axios.post(`${API_URL}/api/gemini`, {
        prompt: geminiPrompt
      })
      setGeminiResults(response.data)
    } catch (err) {
      setError(err.response?.data?.error || 'Failed to generate content')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="app">
      <header className="header">
        <h1>API Integration Demo</h1>
        <p>React + Express + Brave Search + Puppeteer + Gemini AI</p>
      </header>

      <div className="tabs">
        <button 
          className={activeTab === 'search' ? 'tab active' : 'tab'}
          onClick={() => setActiveTab('search')}
        >
          Brave Search
        </button>
        <button 
          className={activeTab === 'scrape' ? 'tab active' : 'tab'}
          onClick={() => setActiveTab('scrape')}
        >
          Puppeteer Scraper
        </button>
        <button 
          className={activeTab === 'gemini' ? 'tab active' : 'tab'}
          onClick={() => setActiveTab('gemini')}
        >
          Gemini AI
        </button>
      </div>

      <div className="content">
        {error && <div className="error">{error}</div>}

        {activeTab === 'search' && (
          <div className="tab-content">
            <h2>Brave Search API</h2>
            <form onSubmit={handleSearch}>
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Enter search query..."
                disabled={loading}
              />
              <button type="submit" disabled={loading}>
                {loading ? 'Searching...' : 'Search'}
              </button>
            </form>
            {searchResults && (
              <div className="results">
                <h3>Search Results</h3>
                <pre>{JSON.stringify(searchResults, null, 2)}</pre>
              </div>
            )}
          </div>
        )}

        {activeTab === 'scrape' && (
          <div className="tab-content">
            <h2>Puppeteer Web Scraper</h2>
            <form onSubmit={handleScrape}>
              <input
                type="url"
                value={scrapeUrl}
                onChange={(e) => setScrapeUrl(e.target.value)}
                placeholder="Enter URL to scrape..."
                disabled={loading}
              />
              <button type="submit" disabled={loading}>
                {loading ? 'Scraping...' : 'Scrape'}
              </button>
            </form>
            {scrapeResults && (
              <div className="results">
                <h3>Scraped Data</h3>
                <div className="scrape-results">
                  <p><strong>Title:</strong> {scrapeResults.title}</p>
                  <p><strong>URL:</strong> {scrapeResults.url}</p>
                  <p><strong>Text Preview:</strong></p>
                  <pre>{scrapeResults.text}</pre>
                </div>
              </div>
            )}
          </div>
        )}

        {activeTab === 'gemini' && (
          <div className="tab-content">
            <h2>Google Gemini AI</h2>
            <form onSubmit={handleGemini}>
              <textarea
                value={geminiPrompt}
                onChange={(e) => setGeminiPrompt(e.target.value)}
                placeholder="Enter your prompt..."
                rows="4"
                disabled={loading}
              />
              <button type="submit" disabled={loading}>
                {loading ? 'Generating...' : 'Generate'}
              </button>
            </form>
            {geminiResults && (
              <div className="results">
                <h3>Generated Content</h3>
                <div className="gemini-results">
                  {geminiResults.text}
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}

export default App
