from __future__ import annotations

import streamlit.components.v1 as components


def install_pwa_metadata() -> None:
    """Attach PWA metadata to Streamlit's parent document.

    Streamlit renders custom components in an iframe, so this tiny bootstrap
    script promotes the manifest/icon/theme metadata into the parent page.
    The app remains fully functional if the browser blocks PWA features.
    """
    components.html(
        r"""
<script>
(function () {
  try {
    const w = window.parent;
    const d = w.document;
    const head = d.head || d.getElementsByTagName('head')[0];

    function ensureLink(rel, href, attrs) {
      let el = head.querySelector('link[rel="' + rel + '"]');
      if (!el) {
        el = d.createElement('link');
        el.rel = rel;
        head.appendChild(el);
      }
      el.href = href;
      if (attrs) Object.entries(attrs).forEach(([k,v]) => el.setAttribute(k,v));
    }

    function ensureMeta(name, content, propertyMode) {
      const selector = propertyMode
        ? 'meta[property="' + name + '"]'
        : 'meta[name="' + name + '"]';
      let el = head.querySelector(selector);
      if (!el) {
        el = d.createElement('meta');
        el.setAttribute(propertyMode ? 'property' : 'name', name);
        head.appendChild(el);
      }
      el.setAttribute('content', content);
    }

    ensureLink('manifest', '/app/static/manifest.webmanifest');
    ensureLink('icon', '/app/static/vastuai-192.png', {type:'image/png', sizes:'192x192'});
    ensureLink('apple-touch-icon', '/app/static/vastuai-192.png', {sizes:'192x192'});
    ensureMeta('theme-color', '#78B58F');
    ensureMeta('mobile-web-app-capable', 'yes');
    ensureMeta('apple-mobile-web-app-capable', 'yes');
    ensureMeta('apple-mobile-web-app-status-bar-style', 'default');
    ensureMeta('apple-mobile-web-app-title', 'VastuAI');
    ensureMeta('application-name', 'VastuAI');
    ensureMeta('description', 'VastuAI Professional and Builder property intelligence.');

    // A service worker is registered for the static PWA asset area. The
    // Streamlit application itself remains network-first because it relies on
    // a live websocket session and should never show stale assessment data.
    if ('serviceWorker' in w.navigator && w.isSecureContext) {
      w.navigator.serviceWorker.register('/app/static/vastuai-sw.js', {scope:'/app/static/'})
        .catch(() => {});
    }

    // Give Android/desktop Chrome a consistent installed-app title.
    d.title = 'VastuAI';
  } catch (e) {
    // Progressive enhancement: never interfere with the Streamlit app.
  }
})();
</script>
        """,
        height=0,
        width=0,
    )
