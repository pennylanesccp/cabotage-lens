from __future__ import annotations

import pydeck as pdk
import streamlit.components.v1 as components

_DECK_HTML_STYLE = """
  <style>
    html, body {
      margin: 0;
      width: 100%;
      height: 100%;
      overflow: hidden;
      background: transparent;
    }
    canvas {
      outline: none !important;
      border-radius: 22px;
    }
  </style>
"""

_CTRL_WHEEL_ZOOM_SCRIPT = """
    (function enableModifierWheelZoom() {
      const map = deckInstance && typeof deckInstance.getMapboxMap === 'function'
        ? deckInstance.getMapboxMap()
        : null;
      if (!map || !map.scrollZoom) {
        return;
      }

      const mapContainer = map.getContainer ? map.getContainer() : container;
      let keyboardModifierPressed = false;
      const blocker = document.createElement('div');
      blocker.setAttribute('data-eco-freight-map-lock', 'true');
      blocker.innerHTML = '<div style="padding:0.5rem 0.8rem;border-radius:999px;background:rgba(15,23,42,0.78);color:#fff;font:600 12px/1.2 sans-serif;box-shadow:0 10px 24px rgba(15,23,42,0.18);">Hold Ctrl to interact with the map</div>';
      Object.assign(blocker.style, {
        position: 'absolute',
        inset: '0',
        zIndex: '20',
        display: 'flex',
        alignItems: 'flex-start',
        justifyContent: 'center',
        paddingTop: '14px',
        background: 'transparent',
        cursor: 'default'
      });
      if (mapContainer && getComputedStyle(mapContainer).position === 'static') {
        mapContainer.style.position = 'relative';
      }
      mapContainer.appendChild(blocker);

      const setInteractionsEnabled = (enabled) => {
        const toggle = (control, shouldEnable) => {
          if (!control || typeof control.enable !== 'function' || typeof control.disable !== 'function') {
            return;
          }
          if (shouldEnable) {
            control.enable();
          } else {
            control.disable();
          }
        };

        toggle(map.scrollZoom, enabled);
        toggle(map.dragPan, enabled);
        toggle(map.dragRotate, enabled);
        toggle(map.doubleClickZoom, enabled);
        toggle(map.touchZoomRotate, enabled);
        toggle(map.boxZoom, enabled);
        toggle(map.keyboard, enabled);
        blocker.style.display = enabled ? 'none' : 'flex';
      };

      const handleKeyState = (event) => {
        keyboardModifierPressed = Boolean(event.ctrlKey || event.metaKey);
        setInteractionsEnabled(keyboardModifierPressed);
      };

      blocker.addEventListener('wheel', (event) => {
        if (!(event.ctrlKey || event.metaKey || keyboardModifierPressed)) {
          event.preventDefault();
        }
      }, {capture: true, passive: false});
      setInteractionsEnabled(false);
      window.addEventListener('keydown', handleKeyState, true);
      window.addEventListener('keyup', handleKeyState, true);
      window.addEventListener('blur', () => {
        keyboardModifierPressed = false;
        setInteractionsEnabled(false);
      }, true);
    })();
"""


def inject_modifier_wheel_zoom(deck_html: str) -> str:
    html = deck_html.replace("<head>", f"<head>\n{_DECK_HTML_STYLE}", 1)
    html = html.replace(
        "const deckInstance = createDeck({",
        "const deckInstance = window.__ecoFreightDeck = createDeck({",
        1,
    )
    return html.replace(
        "\n\n  </script>\n</html>",
        f"\n{_CTRL_WHEEL_ZOOM_SCRIPT}\n  </script>\n</html>",
        1,
    )


def render_deck_chart(deck: pdk.Deck, *, height: int, require_ctrl_for_wheel_zoom: bool = False) -> None:
    deck_html = deck.to_html(
        as_string=True,
        notebook_display=False,
        iframe_width="100%",
        iframe_height=height,
    )
    if require_ctrl_for_wheel_zoom:
        deck_html = inject_modifier_wheel_zoom(deck_html)
    components.html(deck_html, height=height, scrolling=False)
