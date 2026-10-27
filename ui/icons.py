"""Ícones vectoriais (SVG, traço fino, cor herdada) — substituem os emojis na interface."""

_P = {
    "clinic": '<rect x="3" y="4" width="18" height="17" rx="2.5"/><path d="M12 8.5v8M8 12.5h8"/>',
    "radio": '<path d="M12 13v8"/><circle cx="12" cy="10" r="2"/><path d="M8 6.5a5 5 0 0 0 0 7M16 6.5a5 5 0 0 1 0 7"/>'
             '<path d="M5.2 4a9 9 0 0 0 0 12M18.8 4a9 9 0 0 1 0 12"/>',
    "water": '<path d="M12 3s-6 6.7-6 11.2a6 6 0 0 0 12 0C18 9.7 12 3 12 3z"/>',
    "house": '<path d="M3 11 12 4l9 7"/><path d="M5.5 9.5V20h13V9.5"/><path d="M10 20v-5h4v5"/>',
    "mill": '<path d="M3 21V11l5 3v-3l5 3v-3l5 3V6h3v15z"/>',
    "battery": '<rect x="2.5" y="7" width="17" height="10" rx="2"/><path d="M22 11v2"/>',
    "sun": '<circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2'
           'M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/>',
    "cloud": '<path d="M7 18a4.5 4.5 0 1 1 .9-8.9A6 6 0 0 1 19.5 11 3.5 3.5 0 0 1 18 18z"/>',
    "rain": '<path d="M7 15a4.5 4.5 0 1 1 .9-8.9A6 6 0 0 1 19.5 8 3.5 3.5 0 0 1 18 15z"/><path d="M8 18l-1 3M12 18l-1 3M16 18l-1 3"/>',
    "moon": '<path d="M20 14.5A8 8 0 1 1 9.5 4a6.5 6.5 0 0 0 10.5 10.5z"/>',
    "wind": '<path d="M3 8h11a3 3 0 1 0-3-3M3 12h16a3 3 0 1 1-3 3M3 16h8"/>',
    "thermo": '<path d="M14 14.8V5a2 2 0 0 0-4 0v9.8a4 4 0 1 0 4 0z"/>',
    "snow": '<path d="M12 2v20M4.9 7l14.2 10M4.9 17 19.1 7"/>',
    "alert": '<path d="M12 3 2 20h20z"/><path d="M12 10v4M12 17h.01"/>',
    "shield": '<path d="M12 3 4 6v6c0 5 3.5 8 8 9 4.5-1 8-4 8-9V6z"/><path d="m9 12 2 2 4-4"/>',
    "signal": '<path d="M4 20v-3M9 20v-7M14 20v-11M19 20V4"/>',
    "split": '<path d="M4 6h5l6 12h5M4 18h5l2-4M15 6h5"/><path d="m18 3 3 3-3 3M18 15l3 3-3 3"/>',
    "up": '<path d="M12 19V5M5 12l7-7 7 7"/>',
    "check":'<path d="m5 12 5 5 9-10"/>',
    "x": '<path d="M6 6l12 12M18 6 6 18"/>',
    "card": '<rect x="2.5" y="5" width="19" height="14" rx="2"/><path d="M2.5 10h19"/>',
    "tool": '<path d="M14.5 6.5a4 4 0 0 0-5.6 5.6L3 18l3 3 5.9-5.9a4 4 0 0 0 5.6-5.6l-2.5 2.5-2.5-.5-.5-2.5z"/>',
    "users": '<circle cx="9" cy="8" r="3.5"/><path d="M2.5 20a6.5 6.5 0 0 1 13 0"/><path d="M16 4.5a3.5 3.5 0 0 1 0 7M18 14.5a6 6 0 0 1 3.5 5.5"/>',
    "globe": '<circle cx="12" cy="12" r="9"/><path d="M3 12h18M12 3a14 14 0 0 1 0 18M12 3a14 14 0 0 0 0 18"/>',
    "ruler": '<rect x="2.5" y="8" width="19" height="8" rx="1.5"/><path d="M7 8v3M11 8v4M15 8v3M19 8v4"/>',
    "eyeoff": '<path d="M3 3l18 18"/><path d="M10.6 6.1A10 10 0 0 1 22 12a14 14 0 0 1-3 3.8M6.6 6.6A14 14 0 0 0 2 12s3.6 7 10 7a9.6 9.6 0 0 0 4.4-1"/>',
    "bulb": '<path d="M9 18h6M10 21h4"/><path d="M12 3a6 6 0 0 0-3.5 10.9c.6.5 1 1.2 1 2.1h5c0-.9.4-1.6 1-2.1A6 6 0 0 0 12 3z"/>',
    "vaccine": '<path d="m18 2 4 4M17 7l3-3M19 9 8.5 19.5 4.5 15.5 15 5zM6.5 17.5 3 21M10 11l3 3"/>',
    "fuel": '<path d="M4 21V5a2 2 0 0 1 2-2h7a2 2 0 0 1 2 2v16M3 21h13M15 9h2a2 2 0 0 1 2 2v6a1.5 1.5 0 0 0 3 0V8l-3-3"/><path d="M7 7h5v4H7z"/>',
}


def icon(name: str, size: int = 22, color: str = "currentColor", stroke: float = 1.8) -> str:
    return (f'<svg class="ic" width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="{color}" '
            f'stroke-width="{stroke}" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">{_P[name]}</svg>')
