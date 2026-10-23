import { reactive } from 'vue';
import api from './apiClient';

export const auth = reactive({ user: null, ready: false, error: '' });
export const can = (capability, user = auth.user) => {
  if (!user || user.must_change_password) return false;
  if (user.is_superuser) return true;
  const matrix = { administer: ['ADMIN'], infrastructure: ['ADMIN'], register: ['ADMIN', 'OPERATOR'],
    validate: ['ADMIN', 'REVIEWER'], segment: ['ADMIN', 'OPERATOR', 'REVIEWER'] };
  return (matrix[capability] || []).includes(user.role);
};
let bootstrap;
function accept(data) {
  const oldKey = sessionStorage.getItem('sicam.auth.context');
  const key = data.user ? `${data.user.id}:${data.user.institution?.id ?? 'platform'}` : '';
  if (oldKey !== key) sessionStorage.removeItem('sicam.uiContext.v1');
  sessionStorage.setItem('sicam.auth.context', key);
  auth.user = data.user;
  if (data.csrf_token) api.defaults.headers.common['X-CSRFToken'] = data.csrf_token;
  auth.ready = true;
}
export async function refreshSession() {
  const { data } = await api.get('/api/auth/me/'); accept(data); return data.user;
}
export function initializeSession() {
  bootstrap ||= refreshSession().catch(() => { auth.error = 'No se pudo comprobar la sesión. Recargue para reintentar.'; auth.ready = true; });
  return bootstrap;
}
export async function login(username, password) {
  // Bootstrap establishes the CSRF cookie before anonymous login.
  await refreshSession();
  const { data } = await api.post('/api/auth/login/', { username, password }); accept(data);
}
export async function logout() {
  const { data } = await api.post('/api/auth/logout/'); accept(data);
}
export async function changePassword(current_password, new_password, confirmation) {
  const { data } = await api.post('/api/auth/password/', { current_password, new_password, confirmation }); accept(data);
}
let checkingSession = false;
api.interceptors.response.use(response => response, async error => {
  if ([401, 403].includes(error.response?.status) && !error.config?.url?.includes('/auth/') && !checkingSession) {
    checkingSession = true;
    try { await refreshSession(); } finally { checkingSession = false; }
  }
  return Promise.reject(error);
});
