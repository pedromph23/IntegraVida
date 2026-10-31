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
