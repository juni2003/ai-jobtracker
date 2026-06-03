import React from 'react';
import JobCard from './JobCard';
import './Kanban.css';

const COLUMN_COLORS = {
  inbox: '#9CA3AF',
  applied: '#3B82F6',
  interviewing: '#F59E0B',
  offer: '#10B981',
  rejected: '#EF4444',
  ghosted: '#6B7280'
};

const COLUMN_TITLES = {
  inbox: '📥 Inbox',
  applied: '📨 Applied',
  interviewing: '💬 Interviewing',
  offer: '🎉 Offer',
  rejected: '❌ Rejected',
  ghosted: '👻 Ghosted'
};

export default function KanbanColumn({ status, jobs, onDrop, onJobClick, onDelete }) {
  const handleDragOver = (e) => {
    e.preventDefault();
    e.currentTarget.classList.add('drag-over');
  };

  const handleDragLeave = (e) => {
    e.currentTarget.classList.remove('drag-over');
  };

  const handleDrop = (e) => {
    e.preventDefault();
    e.currentTarget.classList.remove('drag-over');
    const jobId = e.dataTransfer.getData('jobId');
    if (jobId) {
      onDrop(jobId, status);
    }
  };

  return (
    <div 
      className="kanban-column glass-panel animate-fade-in"
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
    >
      <div className="column-header">
        <h3 className="column-title">
          <span className="dot" style={{ backgroundColor: COLUMN_COLORS[status] }}></span>
          {COLUMN_TITLES[status]}
        </h3>
        <span className="job-count">{jobs.length}</span>
      </div>
      
      <div className="column-content">
        {jobs.map(job => (
          <JobCard 
            key={job.id} 
            job={job} 
            onClick={() => onJobClick(job)}
            onDelete={() => onDelete(job.id)}
          />
        ))}
        {jobs.length === 0 && (
          <div className="empty-state">No jobs</div>
        )}
      </div>
    </div>
  );
}
