# Frontend Architecture Plan

## Design System
- Dark glassmorphism theme (deep navy background)
- Pakistan tab: Teal/emerald accent (#00D4AA)
- Remote tab: Purple/violet accent (#7C3AED)
- Font: Inter (Google Fonts)
- Smooth micro-animations throughout

## Component Tree
```
App.jsx
├── Header.jsx          ← Logo + Pakistan/Remote tabs + Scrape button + stats
├── FilterBar.jsx       ← Search + City filter + Onsite/Remote toggle
└── KanbanBoard.jsx     ← Drag-and-drop board
    ├── KanbanColumn.jsx  (× 6 columns)
    │   └── JobCard.jsx   (× N cards per column)
    └── JobDetailModal.jsx ← Click card → full detail popup
```

## Kanban Columns
Inbox → Applied → Interviewing → Rejected → Ghosted → Offer

## Job Card Shows
- Job title (bold)
- Company name + source badge (adzuna / rozee / remotive)
- Location + 🏢 Onsite / 🌍 Remote badge
- Salary (if available)
- Experience required badge
- Posted date
- Apply button (opens link)

## Filters (Pakistan tab only)
- Search by title/company
- Filter by city (Karachi, Lahore, Islamabad, Rawalpindi, Other)
- Toggle: All / Onsite / Remote

## Stats Bar
- Total jobs | Inbox | Applied | Interviewing | Offers
