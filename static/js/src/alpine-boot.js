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
