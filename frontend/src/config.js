export const API_BASE_URL = "http://127.0.0.1:8000/api";

export const ENDPOINTS = {
  pakistan: {
    jobs: `${API_BASE_URL}/pakistan/jobs`,
    stats: `${API_BASE_URL}/pakistan/stats`,
    scrape: `${API_BASE_URL}/pakistan/scrape`,
  },
  remote: {
    jobs: `${API_BASE_URL}/remote/jobs`,
    stats: `${API_BASE_URL}/remote/stats`,
    scrape: `${API_BASE_URL}/remote/scrape`,
  }
};
