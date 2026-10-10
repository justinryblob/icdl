(function () {
  var root = document.documentElement;

  /* ---------- Theme toggle ---------- */
  function effectiveTheme() {
    var t = root.getAttribute('data-theme');
    if (t === 'light' || t === 'dark') return t;
    return window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
  }
  function syncLabel() {
    var b = document.getElementById('theme-toggle');
    if (!b) return;
    var dark = effectiveTheme() === 'dark';
    b.setAttribute('aria-label', dark ? 'Switch to light mode' : 'Switch to dark mode');
    b.setAttribute('title', dark ? 'Switch to light mode' : 'Switch to dark mode');
  }
  var themeBtn = document.getElementById('theme-toggle');
  if (themeBtn) {
    themeBtn.addEventListener('click', function () {
      var next = effectiveTheme() === 'dark' ? 'light' : 'dark';
      root.setAttribute('data-theme', next);
      try { localStorage.setItem('icdl-theme', next); } catch (e) {}
      syncLabel();
    });
    syncLabel();
  }

  /* ---------- Mobile sidebar ---------- */
  var navBtn = document.getElementById('nav-toggle');
  function setNav(open) {
    document.body.classList.toggle('nav-open', open);
    if (navBtn) navBtn.setAttribute('aria-expanded', open ? 'true' : 'false');
  }
  if (navBtn) {
    navBtn.addEventListener('click', function () {
      setNav(!document.body.classList.contains('nav-open'));
    });
    var scrim = document.querySelector('.scrim');
    if (scrim) scrim.addEventListener('click', function () { setNav(false); });
  }

  /* Keep the current page visible in the sidebar */
  var current = document.querySelector('.sidebar a[aria-current="page"]');
  if (current && current.scrollIntoView) {
    var side = document.querySelector('.sidebar');
    if (side) {
      var r = current.getBoundingClientRect();
      if (r.top < 80 || r.bottom > window.innerHeight - 40) {
        side.scrollTop += r.top - window.innerHeight / 3;
      }
    }
  }

  /* ---------- Click-to-zoom figures ---------- */
  var box = null;
  function closeBox() { if (box) box.classList.remove('open'); }
  function openBox(src, alt) {
    if (!box) {
      box = document.createElement('div');
      box.className = 'lightbox';
      box.setAttribute('role', 'dialog');
      box.setAttribute('aria-modal', 'true');
      box.setAttribute('aria-label', 'Enlarged figure');
      box.innerHTML = '<img alt="">';
      box.addEventListener('click', closeBox);
      document.body.appendChild(box);
    }
    var im = box.querySelector('img');
    im.src = src; im.alt = alt || '';
    box.classList.add('open');
  }
  document.addEventListener('click', function (e) {
    var t = e.target;
    if (t && t.tagName === 'IMG' && t.closest && t.closest('figure.fig')) {
      openBox(t.currentSrc || t.src, t.alt);
    }
  });
  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape') { closeBox(); setNav(false); }
  });
})();
