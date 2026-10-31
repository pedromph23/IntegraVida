import './theme.js';
import './htmx-config.js';
import { initAlerts } from './alerts.js';
import { initModals } from './modals.js';
import { initForms } from './forms.js';
import { initAnimations } from './animations.js';
import './alpine-boot.js';

document.addEventListener('DOMContentLoaded', () => {
  // Carga lazy de mapas: solo si existe #map en la página (F2.e)
  if (document.getElementById('map')) {
    import('./maps.js').then((mod) => {
      mod.initMaps();
    }).catch((err) => console.warn('maps.js error', err));
  }
  
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
