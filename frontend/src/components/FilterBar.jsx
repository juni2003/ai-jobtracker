import React from 'react';
import { Search, MapPin, Monitor } from 'lucide-react';
import './FilterBar.css';

export default function FilterBar({ activeTab, filter, setFilter }) {
  const isPak = activeTab === 'pakistan';

  return (
    <div className="filter-bar glass-panel animate-fade-in">
      <div className="filter-group search-group">
        <Search size={18} className="filter-icon" />
        <input 
          type="text" 
          placeholder="Search title or company..." 
          value={filter.search}
          onChange={(e) => setFilter(prev => ({...prev, search: e.target.value}))}
        />
      </div>

      {isPak && (
        <div className="filter-group">
          <MapPin size={18} className="filter-icon" />
          <select 
            value={filter.city}
            onChange={(e) => setFilter(prev => ({...prev, city: e.target.value}))}
          >
            <option value="">All Cities</option>
            <option value="Karachi">Karachi</option>
            <option value="Lahore">Lahore</option>
            <option value="Islamabad">Islamabad</option>
            <option value="Rawalpindi">Rawalpindi</option>
            <option value="Peshawar">Peshawar</option>
          </select>
        </div>
      )}

      <div className="filter-group">
        <Monitor size={18} className="filter-icon" />
        <select 
          value={filter.is_remote}
          onChange={(e) => setFilter(prev => ({...prev, is_remote: e.target.value}))}
        >
          <option value="">All Modes</option>
          <option value="true">Remote Only</option>
          <option value="false">Onsite Only</option>
        </select>
      </div>
    </div>
  );
}
