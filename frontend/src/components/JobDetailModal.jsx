import React from 'react';
import { X, ExternalLink, MapPin, Globe, DollarSign, Calendar, Briefcase, Mail } from 'lucide-react';
import './JobDetailModal.css';

export default function JobDetailModal({ job, onClose }) {
  if (!job) return null;

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content glass-panel" onClick={e => e.stopPropagation()}>
        <button className="close-btn" onClick={onClose}>
          <X size={24} />
        </button>

        <div className="modal-header">
          <h2 className="modal-title">{job.title}</h2>
          <div className="modal-company">
            <span className="company-name">{job.company}</span>
            <span className={`source-badge ${job.source}`}>{job.source}</span>
          </div>
        </div>

        <div className="modal-meta">
          <div className="meta-row">
            <div className="meta-item">
              <MapPin size={16} />
              <span>{job.location}</span>
            </div>
            {job.is_remote && (
              <div className="meta-item remote-badge">
                <Globe size={16} />
                <span>Remote</span>
              </div>
            )}
            {job.salary && (
              <div className="meta-item detail-item">
                <DollarSign size={16} />
                <span>{job.salary}</span>
              </div>
            )}
          </div>
          <div className="meta-row">
            <div className="meta-item">
              <Calendar size={16} />
              <span>Posted: {job.post_date || new Date(job.scraped_at).toLocaleDateString()}</span>
            </div>
            {job.experience_required && (
              <div className="meta-item detail-item exp-badge">
                <Briefcase size={16} />
                <span>{job.experience_required}</span>
              </div>
            )}
          </div>
        </div>

        <div className="modal-body">
          <h3>Job Description</h3>
          <p className="description-text">
            {job.description_snippet || "No description provided."}
          </p>
          
          {job.contact_email && (
            <div className="contact-info">
              <Mail size={16} />
              <span>Contact: {job.contact_email}</span>
            </div>
          )}
        </div>

        <div className="modal-footer">
          {job.apply_link ? (
            <a href={job.apply_link} target="_blank" rel="noopener noreferrer" className="apply-btn-large">
              Apply Now <ExternalLink size={18} />
            </a>
          ) : (
            <button className="apply-btn-large disabled" disabled>
              No Apply Link
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
