(() => {
    const navbar = document.querySelector('.navbar');
    const toggle = navbar?.querySelector('.nav-toggle');
    const menu = navbar?.querySelector('.nav-menu');
    if (!toggle || !menu) return;

    const setOpen = (open) => {
        toggle.setAttribute('aria-expanded', String(open));
        toggle.setAttribute('aria-label', open ? 'Close navigation' : 'Open navigation');
        menu.classList.toggle('is-open', open);
    };

    toggle.hidden = false;
    navbar.classList.add('nav-ready');
    toggle.addEventListener('click', () => setOpen(toggle.getAttribute('aria-expanded') !== 'true'));
    navbar.addEventListener('keydown', (event) => {
        if (event.key === 'Escape' && toggle.getAttribute('aria-expanded') === 'true') {
            setOpen(false);
            toggle.focus();
        }
    });
    document.addEventListener('click', (event) => {
        if (!navbar.contains(event.target)) setOpen(false);
    });
    menu.addEventListener('click', (event) => {
        if (event.target.closest('a')) setOpen(false);
    });
    window.matchMedia('(max-width: 820px)').addEventListener('change', () => setOpen(false));
})();
