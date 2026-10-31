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
