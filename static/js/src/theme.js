const STORAGE_KEY = 'iv-theme';

function getStoredTheme() { return localStorage.getItem(STORAGE_KEY); }
function getSystemTheme() {
  return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
}
function applyTheme(theme) {
  const effective = theme === 'system' ? getSystemTheme() : theme;
  document.documentElement.setAttribute('data-theme', effective);
  document.cookie = `iv-theme=${theme}; path=/; max-age=31536000; SameSite=Lax`;
}

const stored = getStoredTheme();
applyTheme(stored || 'system');

const mq = window.matchMedia('(prefers-color-scheme: dark)');
mq.addEventListener('change', () => {
  if ((getStoredTheme() || 'system') === 'system') applyTheme('system');
});

window.IntegraVidaTheme = {
  get current() { return getStoredTheme() || 'system'; },
  set(theme) {
    localStorage.setItem(STORAGE_KEY, theme);
    applyTheme(theme);
    window.dispatchEvent(new CustomEvent('theme-changed', { detail: theme }));
  },
  cycle() {
    const order = ['light', 'dark', 'system'];
    const current = getStoredTheme() || 'system';
    const next = order[(order.indexOf(current) + 1) % order.length];
    this.set(next);
    return next;
  },
};
