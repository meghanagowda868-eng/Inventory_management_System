import api from './axiosInstance';

export const aiApi = {
  getInsights: () => api.get('/ai/insights'),
  predictDemand: (data) => api.post('/ai/predict-demand', data),
  reorderSuggestion: (data) => api.post('/ai/reorder-suggestion', data),
  nlQuery: (query) => api.post('/ai/query', { query }),
};
