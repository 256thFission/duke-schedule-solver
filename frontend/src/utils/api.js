/**
 * API client for Duke Schedule Solver backend.
 *
 * Provides functions to interact with the FastAPI backend endpoints.
 */

import axios from 'axios';

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export const api = {
  /**
   * Upload transcript PDF and extract courses.
   * @param {File} file - PDF file object
   * @returns {Promise<Object>} Transcript response with matched courses
   */
  parseTranscript: async (file, matriculationYear = 'pre2025') => {
    const formData = new FormData();
    formData.append('file', file);

    const params = new URLSearchParams({
      matriculation_year: matriculationYear,
    });

    // Don't manually set Content-Type — axios auto-sets it with the
    // correct multipart boundary when given a FormData object
    const { data } = await axios.post(
      `${API_BASE}/parse-transcript?${params}`,
      formData
    );

    return data;
  },

  /**
   * Search for courses by query string.
   * @param {string} query - Search query
   * @param {string[]} exclude - Course IDs to exclude
   * @returns {Promise<Object>} Search response with matching courses
   */
  searchCourses: async (query, exclude = []) => {
    const params = new URLSearchParams({ query });
    exclude.forEach(id => params.append('exclude', id));

    const { data } = await axios.get(`${API_BASE}/search-courses`, { params });
    return data;
  },

  /**
   * Solve for optimal schedules.
   * @param {Object} config - Complete solver configuration
   * @returns {Promise<Object>} Schedule response with solutions
   */
  solve: async (config) => {
    const { data } = await axios.post(`${API_BASE}/solve`, config);
    return data;
  },

  /**
   * Log the reason a user removed a course (fire-and-forget).
   * @param {string} courseId
   * @param {string} reason - not_interested | cannot_take | not_helpful | other
   * @param {string} reasonText - free text when reason === 'other'
   */
  trackRemoval: (courseId, reason, reasonText = '') => {
    axios.post(`${API_BASE}/track-removal`, {
      course_id: courseId,
      reason,
      reason_text: reasonText,
    }).catch(() => {/* silently ignore */});
  },
};
