// src/api/client.js
import axios from 'axios';

const api = axios.create({
  baseURL: '/api/v1',
  headers: { 'Content-Type': 'application/json' },
});

// Inyectar JWT automáticamente en cada request
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Manejar 401 globalmente
api.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err.response?.status === 401) {
      localStorage.removeItem('token');
      window.location.href = '/login';
    }
    return Promise.reject(err);
  }
);

// ── Auth ──────────────────────────────────────────────────────────
export const authAPI = {
  login: (email, password) => {
    const formData = new URLSearchParams();
    formData.append('username', email);
    formData.append('password', password);
    return api.post('/auth/login', formData, {
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    });
  },
  register: (data) => api.post('/auth/register', data),
  me: () => api.get('/auth/me'),
};

// ── Hojas de Vida ─────────────────────────────────────────────────
export const hojasAPI = {
  upload: (file) => {
    const form = new FormData();
    form.append('file', file);
    return api.post('/hojas-vida/upload', form, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
  },
  miHoja: () => api.get('/hojas-vida/mi-hoja'),
  datosIA: (hojaId) => api.get(`/hojas-vida/${hojaId}/datos-ia`),
  validar: (hojaId, datos) => api.post(`/hojas-vida/${hojaId}/validar`, datos),
  eliminar: (hojaId) => api.delete(`/hojas-vida/${hojaId}`),
};

// ── Evaluación ────────────────────────────────────────────────────
export const evaluacionAPI = {
  calcular: () => api.post('/evaluacion/calcular'),
  resultado: () => api.get('/evaluacion/resultado'),
};

// ── Admin ─────────────────────────────────────────────────────────
export const adminAPI = {
  getReglas: () => api.get('/admin/reglas'),
  updateRegla: (id, data) => api.patch(`/admin/reglas/${id}`, data),
  getRanking: (params = {}) => api.get('/admin/ranking', { params }),
  cambiarEstado: (aspiranteId, estado) =>
    api.patch(`/admin/aspirantes/${aspiranteId}/estado`, { estado }),
};

export default api;
