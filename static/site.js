// Progressive enhancement: ordinary navigation works without JavaScript.
(() => {
  const button = document.querySelector('.menu-toggle');
  const navigation = document.querySelector('#main-navigation');
  const masthead = document.querySelector('.masthead');

  if (button && navigation) {
    const mobile = window.matchMedia('(max-width: 799px), (pointer: coarse) and (max-width: 1024px)');
    const isOpen = () => button.getAttribute('aria-expanded') === 'true';
    const setMenu = open => {
      button.setAttribute('aria-expanded', String(open));
      button.setAttribute('aria-label', open ? 'Close navigation' : 'Open navigation');
      navigation.classList.toggle('is-open', open);
    };

    button.addEventListener('click', () => setMenu(!isOpen()));
    document.addEventListener('keydown', event => {
      if (event.key === 'Escape' && isOpen()) {
        setMenu(false);
        button.focus();
      }
    });
    navigation.addEventListener('click', event => {
      if (event.target.closest('a')) setMenu(false);
    });
    mobile.addEventListener('change', () => {
      if (!mobile.matches) setMenu(false);
    });
    window.addEventListener('pageshow', () => setMenu(false));
    document.documentElement.classList.add('js');
  }

  if (masthead) {
    let pending = false;
    let compact = null;
    const updateHeader = () => {
      pending = false;
      const next = window.scrollY > 40;
      // Avoid querying and touching the DOM on every scroll event.
      if (next !== compact) {
        masthead.classList.toggle('is-scrolled', next);
        compact = next;
      }
    };
    window.addEventListener('scroll', () => {
      if (!pending) {
        pending = true;
        window.requestAnimationFrame(updateHeader);
      }
    }, {passive: true});
    window.addEventListener('pageshow', updateHeader);
    updateHeader();
  }
})();
