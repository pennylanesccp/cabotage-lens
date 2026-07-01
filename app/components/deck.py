from __future__ import annotations

import base64

import pydeck as pdk
import streamlit as st

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
      let disableTimer = null;

      const syncScrollZoom = (modifierActive = keyboardModifierPressed) => {
        if (modifierActive) {
          map.scrollZoom.enable();
        } else {
          map.scrollZoom.disable();
        }
      };

      const handleKeyState = (event) => {
        keyboardModifierPressed = Boolean(event.ctrlKey || event.metaKey);
        syncScrollZoom();
      };

      const handleWheel = (event) => {
        const modifierActive = Boolean(event.ctrlKey || event.metaKey || keyboardModifierPressed);
        syncScrollZoom(modifierActive);
        window.clearTimeout(disableTimer);
        disableTimer = window.setTimeout(() => {
          if (!keyboardModifierPressed) {
            map.scrollZoom.disable();
          }
        }, 180);
      };

      syncScrollZoom();
      window.addEventListener('keydown', handleKeyState, true);
      window.addEventListener('keyup', handleKeyState, true);
      window.addEventListener('blur', () => {
        keyboardModifierPressed = false;
        syncScrollZoom();
      }, true);
      mapContainer.addEventListener('wheel', handleWheel, {capture: true, passive: true});
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


def _html_to_data_url(html: str) -> str:
    payload = base64.b64encode(html.encode("utf-8")).decode("ascii")
    return f"data:text/html;charset=utf-8;base64,{payload}"


def render_deck_chart(deck: pdk.Deck, *, height: int, require_ctrl_for_wheel_zoom: bool = False) -> None:
    deck_html = deck.to_html(
        as_string=True,
        notebook_display=False,
        iframe_width="100%",
        iframe_height=height,
    )
    if require_ctrl_for_wheel_zoom:
        deck_html = inject_modifier_wheel_zoom(deck_html)
    st.iframe(_html_to_data_url(deck_html), height=height)
