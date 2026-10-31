#!/usr/bin/env bash
set -e
cd ~/proyectos/integravida
mkdir -p static/css/src static/css/dist

cat > static/css/src/main.css << 'EOF'
@import './themes.css';
@import './components.css';
@import './animations.css';

@tailwind base;
@tailwind components;
@tailwind utilities;
EOF

cat > static/css/src/themes.css << 'EOF'
:root {
  --color-primary: #7A1F2B;
  --color-primary-strong: #A8323F;
  --color-secondary: #1F7A5A;
  --color-accent: #D98C1F;
  --color-danger: #B3261E;
  --color-surface: #FFFFFF;
  --color-surface-raised: #F7F5F2;
  --color-surface-overlay: #FFFFFF;
  --color-text: #1A1A1A;
  --color-text-muted: #5A5A5A;
  --gradient-hero: linear-gradient(135deg, #7A1F2B 0%, #A8323F 50%, #D98C1F 100%);
  --gradient-calm: linear-gradient(135deg, #1F7A5A 0%, #2FA37A 100%);
  --gradient-emergency: linear-gradient(135deg, #B3261E 0%, #E5484D 100%);
  --gradient-surface: linear-gradient(135deg, #F7F5F2 0%, #FFFFFF 100%);
}

[data-theme="dark"] {
  --color-primary: #C14A57;
  --color-primary-strong: #E56B75;
  --color-secondary: #3FBF8F;
  --color-accent: #F2B544;
  --color-danger: #E5484D;
  --color-surface: #121212;
  --color-surface-raised: #1E1E1E;
  --color-surface-overlay: #2A2A2A;
  --color-text: #F5F5F5;
  --color-text-muted: #B0B0B0;
  --gradient-hero: linear-gradient(135deg, #4A1219 0%, #7A1F2B 50%, #A06A14 100%);
  --gradient-calm: linear-gradient(135deg, #145C43 0%, #1F7A5A 100%);
  --gradient-emergency: linear-gradient(135deg, #6A1410 0%, #B3261E 100%);
  --gradient-surface: linear-gradient(135deg, #1E1E1E 0%, #121212 100%);
}

html { color-scheme: light dark; }

body {
  background-color: var(--color-surface);
  color: var(--color-text);
  font-family: 'Inter', system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  line-height: 1.6;
  transition: background-color 200ms ease, color 200ms ease;
}

@media (prefers-reduced-motion: reduce) {
  body { transition: none; }
}
EOF

cat > static/css/src/components.css << 'EOF'
@layer components {
  .btn {
    @apply inline-flex items-center justify-center gap-2 px-4 py-2 rounded-lg font-medium;
    transition: transform 150ms ease, box-shadow 150ms ease, background-color 150ms ease;
  }
  .btn:focus-visible {
    @apply outline-none ring-2 ring-offset-2 ring-accent ring-offset-surface;
  }
  .btn-primary {
    @apply text-white shadow-sm;
    background: var(--gradient-hero);
  }
  .btn-primary:hover { @apply shadow-md -translate-y-0.5; }
  .btn-secondary {
    @apply text-white shadow-sm;
    background: var(--gradient-calm);
  }
  .btn-secondary:hover { @apply shadow-md -translate-y-0.5; }
  .btn-danger {
    @apply text-white shadow-sm;
    background: var(--gradient-emergency);
  }
  .btn-danger:hover { @apply shadow-md -translate-y-0.5; }
  .btn-ghost {
    @apply bg-transparent;
    color: var(--color-text);
  }
  .btn-ghost:hover { background-color: var(--color-surface-raised); }

  .card {
    @apply rounded-xl shadow-sm;
    background-color: var(--color-surface-raised);
    border: 1px solid color-mix(in srgb, var(--color-text) 10%, transparent);
  }
  .card-hover { transition: transform 150ms ease, box-shadow 150ms ease; }
  .card-hover:hover { @apply -translate-y-0.5 shadow-md; }

  .input {
    @apply w-full rounded-lg px-3 py-2;
    background-color: var(--color-surface);
    color: var(--color-text);
    border: 1px solid color-mix(in srgb, var(--color-text) 20%, transparent);
  }
  .input::placeholder { color: var(--color-text-muted); }
  .input:focus { @apply outline-none ring-2 ring-accent; border-color: transparent; }

  .badge {
    @apply inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium;
  }
  .badge-success { @apply bg-secondary-500/10 text-secondary-600; }
  .badge-warning { @apply bg-accent-500/10 text-accent-600; }
  .badge-danger { @apply bg-danger-500/10 text-danger-600; }
  .badge-info { @apply bg-primary-500/10 text-primary-600; }
}

@media (prefers-reduced-motion: reduce) {
  .btn-primary:hover, .btn-secondary:hover, .btn-danger:hover,
  .card-hover:hover { @apply translate-y-0; }
}
EOF

cat > static/css/src/animations.css << 'EOF'
@keyframes shimmer {
  0% { background-position: -1000px 0; }
  100% { background-position: 1000px 0; }
}

.skeleton {
  background: linear-gradient(90deg,
    var(--color-surface-raised) 0%,
    color-mix(in srgb, var(--color-surface-raised) 70%, white) 50%,
    var(--color-surface-raised) 100%);
  background-size: 1000px 100%;
  animation: shimmer 1.6s linear infinite;
  border-radius: 0.5rem;
}

@keyframes shake {
  0%, 100% { transform: translateX(0); }
  25% { transform: translateX(-4px); }
  75% { transform: translateX(4px); }
}
.animate-shake { animation: shake 0.4s ease-in-out; }

@keyframes slide-in-right {
  from { transform: translateX(100%); opacity: 0; }
  to { transform: translateX(0); opacity: 1; }
}
.animate-slide-in-right { animation: slide-in-right 0.25s cubic-bezier(0.16, 1, 0.3, 1); }

@keyframes check-pop {
  0% { transform: scale(0); opacity: 0; }
  50% { transform: scale(1.2); opacity: 1; }
  100% { transform: scale(1); opacity: 1; }
}
.animate-check-pop { animation: check-pop 0.3s ease-out; }

@media (prefers-reduced-motion: reduce) {
  .skeleton, .animate-shake, .animate-slide-in-right, .animate-check-pop {
    animation: none;
  }
}
EOF

echo "OK: CSS sources creados"
