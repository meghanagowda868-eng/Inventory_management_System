import api from './axiosInstance';

export const authApi = {
  register: (data) => api.post('/auth/register', data),
  login: (credentials) => api.post('/auth/login', credentials),
  logout: (refreshToken) => api.post('/auth/logout', { refresh_token: refreshToken }),
  getProfile: () => api.get('/auth/profile'),
  updateProfile: (data) => api.put('/auth/profile', data),
  changePassword: (data) => api.put('/auth/change-password', data),
  refreshToken: (token) => api.post('/auth/refresh', { refresh_token: token }),
  getUsers: () => api.get('/auth/users'),
  updateUserRole: (userId, data) => api.put(`/auth/users/${userId}/role`, data),
  createUser: (data) => api.post('/auth/users', data),
  updateUser: (userId, data) => api.put(`/auth/users/${userId}`, data),
  deleteUser: (userId) => api.delete(`/auth/users/${userId}/permanent`),
};
