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
