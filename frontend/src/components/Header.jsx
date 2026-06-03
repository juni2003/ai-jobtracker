import React from 'react';
import { Briefcase, Globe, RefreshCw, BarChart2 } from 'lucide-react';
import './Header.css';

export default function Header({ activeTab, setActiveTab, onScrape, isScraping, stats }) {
  const isPak = activeTab === 'pakistan';

  return (
    <header className="app-header glass-panel">
      <div className="header-left">
        <div className="logo-container">
          <Briefcase className="logo-icon" size={28} color={isPak ? "var(--accent-teal)" : "var(--accent-violet)"} />
          <h1 className="logo-text">AI JobTracker</h1>
        </div>

        <div className="tab-switcher">
          <button 
            className={`tab-btn ${isPak ? 'active pak' : ''}`}
            onClick={() => setActiveTab('pakistan')}
          >
            🇵🇰 Pakistan
          </button>
          <button 
            className={`tab-btn ${!isPak ? 'active remote' : ''}`}
            onClick={() => setActiveTab('remote')}
          >
            🌍 Remote
          </button>
        </div>
      </div>

      <div className="header-right">
        <div className="stats-mini">
          <BarChart2 size={16} />
          <span>Total: <strong>{stats?.total || 0}</strong></span>
          <span className="divider">|</span>
          <span>Applied: <strong>{stats?.by_status?.applied || 0}</strong></span>
        </div>
        
        <button 
          className={`scrape-btn ${isScraping ? 'scraping' : ''}`} 
          onClick={onScrape}
          disabled={isScraping}
          style={{ '--btn-color': isPak ? 'var(--accent-teal)' : 'var(--accent-violet)' }}
        >
          <RefreshCw size={16} className={isScraping ? 'spin' : ''} />
          {isScraping ? 'Scraping...' : 'Scrape Now'}
        </button>
      </div>
    </header>
  );
}
