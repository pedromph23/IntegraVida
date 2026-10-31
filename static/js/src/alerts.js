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
