function getCsrf() {
  const meta = document.querySelector('meta[name="csrf-token"]');
  if (meta && meta.content) return meta.content;
  const match = document.cookie.match(/csrftoken=([^;]+)/);
  return match ? match[1] : null;
}

document.addEventListener('htmx:configRequest', (evt) => {
  const token = getCsrf();
  if (token) evt.detail.headers['X-CSRFToken'] = token;
});
