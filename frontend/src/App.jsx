import { useState, useEffect, useMemo } from 'react';
import Header from './components/Header';
import FilterBar from './components/FilterBar';
import KanbanColumn from './components/KanbanColumn';
import JobDetailModal from './components/JobDetailModal';
import { ENDPOINTS } from './config';
import './index.css';

const COLUMNS = ['inbox', 'applied', 'interviewing', 'offer', 'rejected', 'ghosted'];

function App() {
  const [activeTab, setActiveTab] = useState('pakistan'); // 'pakistan' or 'remote'
  const [jobs, setJobs] = useState([]);
  const [stats, setStats] = useState(null);
  const [isScraping, setIsScraping] = useState(false);
  
  const [filter, setFilter] = useState({
    search: '',
    city: '',
    is_remote: ''
  });

  const [selectedJob, setSelectedJob] = useState(null);

  // Fetch Data
  const fetchData = async () => {
    try {
      // Fetch Jobs
      const url = new URL(ENDPOINTS[activeTab].jobs);
      
      if (filter.search) url.searchParams.append('search', filter.search);
      if (activeTab === 'pakistan' && filter.city) url.searchParams.append('city', filter.city);
      if (filter.is_remote) url.searchParams.append('is_remote', filter.is_remote);
      url.searchParams.append('limit', 500);

      const res = await fetch(url);
      if (res.ok) {
        const data = await res.json();
        setJobs(data);
      }

      // Fetch Stats
      const statsRes = await fetch(ENDPOINTS[activeTab].stats);
      if (statsRes.ok) {
        const statsData = await statsRes.json();
        setStats(statsData);
      }
    } catch (err) {
      console.error("Failed to fetch data:", err);
    }
  };

  useEffect(() => {
    fetchData();
  }, [activeTab, filter]);

  // Handle Scrape
  const handleScrape = async () => {
    setIsScraping(true);
    try {
      const res = await fetch(ENDPOINTS[activeTab].scrape, { method: 'POST' });
      if (res.ok) {
        const result = await res.json();
        alert(`Scrape complete! Inserted: ${result.inserted}, Skipped: ${result.skipped}`);
        fetchData(); // Refresh data
      }
    } catch (err) {
      console.error("Scrape failed:", err);
      alert("Scrape failed. Check console.");
    } finally {
      setIsScraping(false);
    }
  };

  // Handle Drag & Drop Status Update
  const handleDrop = async (jobId, newStatus) => {
    // Optimistic UI update
    setJobs(prev => prev.map(job => job.id === jobId ? { ...job, status: newStatus } : job));
    
    // API Call
    try {
      const res = await fetch(`${ENDPOINTS[activeTab].jobs}/${jobId}/status`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ status: newStatus })
      });
      if (!res.ok) {
        console.error("Status update failed");
        fetchData(); // Revert on failure
      } else {
        // Refresh stats silently
        const statsRes = await fetch(ENDPOINTS[activeTab].stats);
        if (statsRes.ok) setStats(await statsRes.json());
      }
    } catch (err) {
      console.error("Status update error:", err);
      fetchData();
    }
  };

  // Handle Delete
  const handleDelete = async (jobId) => {
    if (!window.confirm("Are you sure you want to delete this job?")) return;
    
    setJobs(prev => prev.filter(job => job.id !== jobId));
    try {
      await fetch(`${ENDPOINTS[activeTab].jobs}/${jobId}`, { method: 'DELETE' });
      const statsRes = await fetch(ENDPOINTS[activeTab].stats);
      if (statsRes.ok) setStats(await statsRes.json());
    } catch (err) {
      console.error("Delete error:", err);
      fetchData();
    }
  };

  // Group jobs by status
  const jobsByStatus = useMemo(() => {
    const grouped = { inbox: [], applied: [], interviewing: [], offer: [], rejected: [], ghosted: [] };
    jobs.forEach(job => {
      if (grouped[job.status]) {
        grouped[job.status].push(job);
      } else {
        grouped.inbox.push(job); // fallback
      }
    });
    return grouped;
  }, [jobs]);

  return (
    <div className="app-container">
      <Header 
        activeTab={activeTab} 
        setActiveTab={(tab) => {
          setActiveTab(tab);
          setFilter({ search: '', city: '', is_remote: '' }); // Reset filters on tab switch
        }}
        onScrape={handleScrape}
        isScraping={isScraping}
        stats={stats}
      />
      
      <main className="main-content">
        <FilterBar 
          activeTab={activeTab} 
          filter={filter} 
          setFilter={setFilter} 
        />
        
        <div className="kanban-container">
          {COLUMNS.map(col => (
            <KanbanColumn 
              key={col} 
              status={col} 
              jobs={jobsByStatus[col] || []} 
              onDrop={handleDrop}
              onJobClick={setSelectedJob}
              onDelete={handleDelete}
            />
          ))}
        </div>
      </main>

      <JobDetailModal 
        job={selectedJob} 
        onClose={() => setSelectedJob(null)} 
      />
    </div>
  );
}

export default App;
