import React from 'react';
import { MapPin, Globe, DollarSign, Calendar, ExternalLink, Trash2 } from 'lucide-react';

export default function JobCard({ job, onClick, onDelete }) {
  const handleDragStart = (e) => {
    e.dataTransfer.setData('jobId', job.id);
    e.target.classList.add('dragging');
  };

  const handleDragEnd = (e) => {
    e.target.classList.remove('dragging');
  };

  const handleApplyClick = (e) => {
    e.stopPropagation();
  };

  const handleDeleteClick = (e) => {
    e.stopPropagation();
    onDelete();
  };

  return (
    <div 
      className="job-card glass-panel"
      draggable="true"
      onDragStart={handleDragStart}
      onDragEnd={handleDragEnd}
      onClick={onClick}
    >
      <div className="card-header">
        <h4 className="job-title">{job.title}</h4>
        <button className="delete-btn" onClick={handleDeleteClick} title="Delete Job">
          <Trash2 size={14} />
        </button>
      </div>
      
      <div className="company-info">
        <span className="company-name">{job.company}</span>
        <span className={`source-badge ${job.source}`}>{job.source}</span>
      </div>

      <div className="job-meta">
        <div className="meta-item">
          <MapPin size={12} />
          <span>{job.location}</span>
        </div>
        {job.is_remote && (
          <div className="meta-item remote-badge">
            <Globe size={12} />
            <span>Remote</span>
          </div>
        )}
      </div>

      {(job.salary || job.experience_required) && (
        <div className="job-details">
          {job.salary && (
            <div className="detail-item">
              <DollarSign size={12} />
              <span>{job.salary}</span>
            </div>
          )}
          {job.experience_required && (
            <div className="detail-item exp-badge">
              <span>{job.experience_required}</span>
            </div>
          )}
        </div>
      )}

      <div className="card-footer">
        <div className="post-date">
          <Calendar size={12} />
          <span>{new Date(job.scraped_at).toLocaleDateString()}</span>
        </div>
        {job.apply_link && (
          <a 
            href={job.apply_link} 
            target="_blank" 
            rel="noopener noreferrer" 
            className="apply-btn"
            onClick={handleApplyClick}
          >
            Apply <ExternalLink size={12} />
          </a>
        )}
      </div>
    </div>
  );
}
