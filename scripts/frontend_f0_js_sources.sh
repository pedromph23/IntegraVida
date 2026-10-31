#!/usr/bin/env bash
set -e
cd ~/proyectos/integravida
mkdir -p static/js/src static/js/dist

cat > static/js/src/main.js << 'EOF'
import './theme.js';
import './htmx-config.js';
import { initAlerts } from './alerts.js';
import { initModals } from './modals.js';
import { initForms } from './forms.js';
import { initAnimations } from './animations.js';
import './alpine-boot.js';

document.addEventListener('DOMContentLoaded', () => {
  initAlerts();
  initModals();
  initForms();
  initAnimations();

  document.body.addEventListener('htmx:afterSwap', () => {
    initAlerts();
    initModals();
    initForms();
  });
});
EOF

cat > static/js/src/theme.js << 'EOF'
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
EOF

cat > static/js/src/htmx-config.js << 'EOF'
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
EOF

cat > static/js/src/alerts.js << 'EOF'
export function initAlerts() {
  document.querySelectorAll('[data-alert-auto-dismiss]').forEach((alert) => {
    if (alert.dataset.alertPersistent === 'true') return;
    if (alert.dataset.dismissTimer) return;
    alert.dataset.dismissTimer = 'true';
    setTimeout(() => {
      alert.style.transition = 'opacity 0.3s ease, transform 0.3s ease';
      alert.style.opacity = '0';
      alert.style.transform = 'translateY(-8px)';
      setTimeout(() => alert.remove(), 300);
    }, 8000);
  });
}
EOF

cat > static/js/src/modals.js << 'EOF'
export function initModals() {
  document.querySelectorAll('[data-modal-open]').forEach((trigger) => {
    trigger.addEventListener('click', () => {
      const modal = document.getElementById(trigger.dataset.modalOpen);
      if (modal) openModal(modal);
    });
  });

  document.querySelectorAll('[data-modal-close]').forEach((btn) => {
    btn.addEventListener('click', () => {
      const modal = btn.closest('[role="dialog"]');
      if (modal) closeModal(modal);
    });
  });

  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
      document.querySelectorAll('[role="dialog"]:not([hidden])').forEach(closeModal);
    }
  });
}

function openModal(modal) {
  modal.hidden = false;
  modal.setAttribute('aria-hidden', 'false');
  document.body.style.overflow = 'hidden';
  const focusable = modal.querySelector('button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])');
  if (focusable) focusable.focus();
  modal._trapHandler = (e) => trapFocus(e, modal);
  modal.addEventListener('keydown', modal._trapHandler);
}

function closeModal(modal) {
  modal.hidden = true;
  modal.setAttribute('aria-hidden', 'true');
  document.body.style.overflow = '';
  if (modal._trapHandler) {
    modal.removeEventListener('keydown', modal._trapHandler);
    delete modal._trapHandler;
  }
}

function trapFocus(e, modal) {
  if (e.key !== 'Tab') return;
  const focusable = Array.from(modal.querySelectorAll(
    'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
  )).filter((el) => !el.disabled && el.offsetParent !== null);
  if (focusable.length === 0) return;
  const first = focusable[0];
  const last = focusable[focusable.length - 1];
  if (e.shiftKey && document.activeElement === first) {
    e.preventDefault(); last.focus();
  } else if (!e.shiftKey && document.activeElement === last) {
    e.preventDefault(); first.focus();
  }
}
EOF

cat > static/js/src/forms.js << 'EOF'
export function initForms() {
  document.querySelectorAll('form[data-validate]').forEach((form) => {
    if (form.dataset.validating === 'true') return;
    form.dataset.validating = 'true';
    form.addEventListener('submit', (e) => {
      const invalids = form.querySelectorAll(':invalid');
      if (invalids.length > 0) {
        e.preventDefault();
        form.classList.add('animate-shake');
        setTimeout(() => form.classList.remove('animate-shake'), 400);
        invalids[0].focus();
      }
    });
  });
}
EOF

cat > static/js/src/animations.js << 'EOF'
import { gsap } from 'gsap';
import { ScrollTrigger } from 'gsap/ScrollTrigger';

gsap.registerPlugin(ScrollTrigger);

const PREFERS_REDUCED = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

export function initAnimations() {
  if (PREFERS_REDUCED) return;

  document.querySelectorAll('[data-hero]').forEach((hero) => {
    if (hero.dataset.animated === 'true') return;
    hero.dataset.animated = 'true';
    const items = hero.querySelectorAll('[data-hero-item]');
    if (items.length === 0) return;
    gsap.from(items, {
      y: 24, opacity: 0, duration: 0.6, stagger: 0.08,
      ease: 'power3.out',
      scrollTrigger: { trigger: hero, start: 'top 80%', once: true },
    });
  });
}
EOF

cat > static/js/src/alpine-boot.js << 'EOF'
import Alpine from 'alpinejs';

window.Alpine = Alpine;

Alpine.store('theme', {
  current: (window.IntegraVidaTheme && window.IntegraVidaTheme.current) || 'system',
  set(val) {
    window.IntegraVidaTheme.set(val);
    this.current = val;
  },
  cycle() {
    const next = window.IntegraVidaTheme.cycle();
    this.current = next;
    return next;
  },
});

Alpine.store('menu', { open: false });

Alpine.start();
EOF

echo "OK: JS sources creados"
