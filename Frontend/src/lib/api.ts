// ── Future: Axios instance for real Express backend ───────────
// This file is a stub. When the backend is ready:
// 1. npm install axios
// 2. Uncomment the implementation below
// 3. Set VITE_USE_MOCK=false in .env.production

// import axios from 'axios';
//
// export const api = axios.create({
//   baseURL: import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:4000/api',
//   timeout: 10000,
//   headers: { 'Content-Type': 'application/json' },
// });
//
// api.interceptors.request.use((config) => {
//   const token = localStorage.getItem('invebro_token');
//   if (token) config.headers.Authorization = `Bearer ${token}`;
//   return config;
// });
//
// api.interceptors.response.use(
//   (response) => response,
//   (error) => {
//     if (error.response?.status === 401) {
//       localStorage.removeItem('invebro_token');
//       window.location.href = '/login';
//     }
//     return Promise.reject(error);
//   }
// );

export {};  // Stub — prevents "no exports" TS error
