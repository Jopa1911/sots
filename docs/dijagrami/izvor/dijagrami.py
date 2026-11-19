"""Dijagrami za dnevnik (SVG): numerisani čvorovi bez teksta i legenda sa strane.

memorija_agenta (Slika 3 u dnevniku) i stanja_ljutnje (Slika 2); arhitektura_simulatora je u arhitektura.py.
"""
import html
import math
import sys

FONT = "Inter, 'DejaVu Sans', Arial, sans-serif"

ZONES = {
    "A": dict(fill="#9a6b3f", tint="#f8f2ea", border="#e3cfb5", text="#7a5230"),
    "B": dict(fill="#4f46e5", tint="#eef0ff", border="#c9ccfb", text="#3f37c9"),
    "C": dict(fill="#0e7ec4", tint="#e9f5fd", border="#b8def6", text="#0b6aa6"),
    "D": dict(fill="#475569", tint="#f2f4f7", border="#cfd6df", text="#334155"),
    "E": dict(fill="#d97706", tint="#fff6e5", border="#f5d49a", text="#b45309"),
    "F": dict(fill="#15803d", tint="#eaf8ef", border="#ade3bf", text="#166534"),
}

EDGE = {
    "tok": dict(color="#334155", width=2.2, dash=None),
    "upis": dict(color="#d97706", width=1.9, dash=None),
    "citanje": dict(color="#2563eb", width=1.9, dash="7 4"),
    "priprema": dict(color="#9a6b3f", width=2.0, dash="1.5 4.5"),
    "posle": dict(color="#15803d", width=2.0, dash=None),
}


def esc(s):
    return html.escape(str(s), quote=True)


class Fig:
    def __init__(self, w, h):
        self.w, self.h = w, h
        self.defs, self.markers = [], {}
        self.zones, self.edges, self.nodes, self.legend = [], [], [], []

    def marker(self, color):
        if color not in self.markers:
            mid = f"arrow{len(self.markers)}"
            self.defs.append(
                f'<marker id="{mid}" viewBox="0 0 10 10" refX="9" refY="5" markerUnits="userSpaceOnUse" '
                f'markerWidth="10" markerHeight="10" orient="auto"><path d="M0,0.8 L10,5 L0,9.2 z" fill="{color}"/></marker>'
            )
            self.markers[color] = mid
        return self.markers[color]

    def svg(self):
        parts = [
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{self.w}" height="{self.h}" viewBox="0 0 {self.w} {self.h}" font-family="{FONT}">',
            "<defs>" + "".join(self.defs) + "</defs>",
            f'<rect width="{self.w}" height="{self.h}" fill="#ffffff"/>',
        ]
        parts += self.zones + self.edges + self.nodes + self.legend
        parts.append("</svg>")
        return "\n".join(parts)


# ---------- geometrija ----------

def bdist(node, ux, uy):
    """Udaljenost od centra do ivice oblika u pravcu (ux, uy)."""
    if node is None or node.get("shape") == "point":
        return 0.0
    s, r = node["shape"], node["r"]
    if s == "circle":
        return r
    if s == "square":
        m = max(abs(ux), abs(uy))
        return r / m if m else r
    if s == "diamond":
        h = r * 1.3
        t = abs(ux) + abs(uy)
        return h / t if t else h
    return r


def unit(ax, ay, bx, by):
    dx, dy = bx - ax, by - ay
    d = math.hypot(dx, dy) or 1.0
    return dx / d, dy / d


def endpoint(node, toward, gap):
    x, y = node["x"], node["y"]
    ux, uy = unit(x, y, *toward)
    d = bdist(node, ux, uy) + gap
    return x + ux * d, y + uy * d


def rounded_poly(points, rr=14):
    d = f"M{points[0][0]:.1f},{points[0][1]:.1f}"
    for i in range(1, len(points) - 1):
        ax, ay = points[i - 1]
        cx, cy = points[i]
        bx, by = points[i + 1]
        u1 = unit(cx, cy, ax, ay)
        u2 = unit(cx, cy, bx, by)
        l1 = min(rr, math.hypot(ax - cx, ay - cy) / 2)
        l2 = min(rr, math.hypot(bx - cx, by - cy) / 2)
        p1 = (cx + u1[0] * l1, cy + u1[1] * l1)
        p2 = (cx + u2[0] * l2, cy + u2[1] * l2)
        d += f" L{p1[0]:.1f},{p1[1]:.1f} Q{cx:.1f},{cy:.1f} {p2[0]:.1f},{p2[1]:.1f}"
    d += f" L{points[-1][0]:.1f},{points[-1][1]:.1f}"
    return d


def edge(fig, kind, src, dst, via=None, curve=None, width=None, start_gap=2.0, end_gap=1.5):
    st = EDGE[kind]
    color = st["color"]
    w = width or st["width"]
    if curve:  # kubna kriva sa kontrolnim tačkama
        c1, c2 = curve
        p0 = endpoint(src, c1, start_gap)
        p3 = endpoint(dst, c2, end_gap)
        d = f"M{p0[0]:.1f},{p0[1]:.1f} C{c1[0]:.1f},{c1[1]:.1f} {c2[0]:.1f},{c2[1]:.1f} {p3[0]:.1f},{p3[1]:.1f}"
    else:
        pts = via or []
        first = pts[0] if pts else (dst["x"], dst["y"])
        last = pts[-1] if pts else (src["x"], src["y"])
        p0 = endpoint(src, first, start_gap)
        p3 = endpoint(dst, last, end_gap)
        d = rounded_poly([p0] + list(pts) + [p3])
    dash = f' stroke-dasharray="{st["dash"]}" stroke-linecap="round"' if st["dash"] else ""
    fig.edges.append(
        f'<path d="{d}" fill="none" stroke="{color}" stroke-width="{w}"{dash} '
        f'stroke-linejoin="round" marker-end="url(#{fig.marker(color)})"/>'
    )


def draw_shape(shape, x, y, r, fill, label=None, fs=13.5, stroke="#ffffff", sw=2.0):
    if shape == "circle":
        body = f'<circle cx="{x}" cy="{y}" r="{r}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"/>'
    elif shape == "square":
        body = (f'<rect x="{x - r}" y="{y - r}" width="{2 * r}" height="{2 * r}" rx="{r * 0.32:.1f}" '
                f'fill="{fill}" stroke="{stroke}" stroke-width="{sw}"/>')
    else:  # diamond
        h = r * 1.3
        body = (f'<path d="M{x},{y - h} L{x + h},{y} L{x},{y + h} L{x - h},{y} z" fill="{fill}" '
                f'stroke="{stroke}" stroke-width="{sw}" stroke-linejoin="round"/>')
    txt = ""
    if label is not None:
        txt = (f'<text x="{x}" y="{y}" dy="0.36em" text-anchor="middle" font-size="{fs}" '
               f'font-weight="700" fill="#ffffff">{esc(label)}</text>')
    return body + txt


def zone(fig, key, x, y, w, h):
    z = ZONES[key]
    fig.zones.append(
        f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="16" fill="{z["tint"]}" '
        f'stroke="{z["border"]}" stroke-width="1.6"/>'
    )
    # jezičak sa slovom zone na gornjoj ivici
    tx, ty = x + 16, y - 13
    fig.zones.append(
        f'<rect x="{tx}" y="{ty}" width="26" height="26" rx="7" fill="{z["fill"]}" stroke="#ffffff" stroke-width="2"/>'
        f'<text x="{tx + 13}" y="{ty + 13}" dy="0.36em" text-anchor="middle" font-size="14" '
        f'font-weight="700" fill="#ffffff">{key}</text>'
    )
    return dict(x=x, y=y, w=w, h=h)


# =====================================================================
# Memorija i tok obrade agenta (Slika 3 u dnevniku)
# =====================================================================

def memorija_agenta():
    OX, OY = 22, 26
    W, H = 1870, 1010
    fig = Fig(W, H)

    raw = {
        # A — izvori podataka i priprema
        1: ("A", "circle", 370, 62), 2: ("A", "circle", 470, 62), 3: ("A", "circle", 570, 62),
        4: ("A", "circle", 670, 62), 5: ("A", "square", 520, 148),
        # B — stalna memorija: pravila i sadržaj
        6: ("B", "circle", 425, 252), 7: ("B", "circle", 490, 252), 8: ("B", "circle", 620, 252),
        9: ("B", "circle", 685, 252), 10: ("B", "circle", 750, 252), 11: ("B", "circle", 830, 252),
        # C — stalna memorija: persona i scenario
        12: ("C", "circle", 200, 742), 13: ("C", "circle", 320, 742), 14: ("C", "circle", 580, 742),
        15: ("C", "circle", 700, 742), 16: ("C", "circle", 200, 822), 17: ("C", "circle", 320, 822),
        18: ("C", "circle", 450, 822), 19: ("C", "circle", 580, 822), 20: ("C", "circle", 700, 822),
        # D — obrada jednog poteza (kružni tok)
        21: ("D", "circle", 110, 382), 22: ("D", "square", 225, 382), 23: ("D", "square", 340, 382),
        24: ("D", "square", 455, 382), 25: ("D", "square", 570, 382), 26: ("D", "square", 685, 382),
        27: ("D", "diamond", 878, 516), 28: ("D", "square", 790, 642), 29: ("D", "square", 620, 642),
        30: ("D", "diamond", 450, 642), 31: ("D", "square", 280, 642), 32: ("D", "circle", 110, 642),
        # E — radna memorija
        33: ("E", "circle", 340, 462), 34: ("E", "circle", 455, 462), 35: ("E", "circle", 545, 462),
        36: ("E", "circle", 605, 462), 37: ("E", "circle", 692, 462),
        38: ("E", "circle", 280, 562), 39: ("E", "circle", 450, 562), 40: ("E", "circle", 545, 562),
        41: ("E", "circle", 628, 562), 42: ("E", "circle", 706, 562),
        # F — trajni zapis
        43: ("F", "circle", 870, 752), 44: ("F", "circle", 945, 752), 45: ("F", "circle", 1020, 752),
        46: ("F", "circle", 870, 832), 47: ("F", "circle", 945, 832), 48: ("F", "square", 1020, 832),
        49: ("F", "circle", 1020, 907),
    }
    N = {}
    for k, (z, shape, x, y) in raw.items():
        N[k] = dict(z=z, shape=shape, x=x + OX, y=y + OY, r=17 if shape != "square" else 16.5)

    def P(x, y):
        return (x + OX, y + OY)

    def pt(x, y):
        return dict(shape="point", x=x + OX, y=y + OY)

    # zone (D se crta pre E jer je E unutar D)
    zone(fig, "A", 320 + OX, 22 + OY, 400, 160)
    zone(fig, "B", 385 + OX, 207 + OY, 490, 92)
    zone(fig, "D", 62 + OX, 338 + OY, 862, 346)
    zone(fig, "E", 240 + OX, 426 + OY, 492, 170)
    zone(fig, "C", 150 + OX, 700 + OY, 655, 160)
    zone(fig, "F", 828 + OX, 700 + OY, 236, 240)

    # --- A: priprema sadržaja ---
    for s in (1, 2, 3, 4):
        edge(fig, "priprema", N[s], N[5])
    for t in (6, 7, 8):
        edge(fig, "priprema", N[5], N[t])
    # A -> C levim kanalom (do čvorova 18 i 19)
    for t in (18, 19):
        edge(fig, "priprema", N[5], N[t],
             via=[P(400, 148), P(40, 148), P(40, 892), P(N[t]["x"] - OX, 892)])

    # --- B -> D čitanje ---
    for s in (6, 7):
        edge(fig, "citanje", N[s], N[24])
    for s in (8, 9, 10):
        edge(fig, "citanje", N[s], N[26])
    # cilj vežbe -> povratna informacija (desnim kanalom)
    edge(fig, "citanje", N[11], N[48], via=[P(1102, 252), P(1102, 832)])

    # --- D: tok obrade ---
    order = [21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 21]
    for a, b in zip(order, order[1:]):
        edge(fig, "tok", N[a], N[b])

    # --- D -> E upis ---
    for a, b in [(23, 33), (24, 34), (25, 35), (25, 36), (26, 37), (30, 39), (27, 42)]:
        edge(fig, "upis", N[a], N[b])
    # izvođenje unutar radne memorije
    for a, b in [(33, 38), (39, 38), (35, 40), (37, 40), (37, 41)]:
        edge(fig, "upis", N[a], N[b])

    # --- čitanje iz memorije u obradu ---
    edge(fig, "citanje", N[37], N[27])                        # ljutnja -> kraj razgovora
    edge(fig, "citanje", N[18], N[30])                        # obrazac razgovora (nivoi) -> provera replike
    edge(fig, "citanje", pt(730, 596), N[28], width=3.0)      # cela zona E -> izbor poteza i smernice
    edge(fig, "citanje", pt(790, 700), N[28], width=3.0)      # cela zona C -> izbor poteza i smernice

    # --- posle razgovora ---
    edge(fig, "posle", N[27], pt(925, 700), width=3.0, curve=(P(905, 590), P(925, 650)))
    for a, b in [(43, 46), (44, 47), (44, 48), (45, 48), (48, 49)]:
        edge(fig, "posle", N[a], N[b])

    # čvorovi
    for k, n in N.items():
        fig.nodes.append(draw_shape(n["shape"], n["x"], n["y"], n["r"], ZONES[n["z"]]["fill"], str(k)))

    # ---------------- legenda ----------------
    LX, LY, LW = 1172, 18, 680
    fig.legend.append(f'<rect x="{LX}" y="{LY}" width="{LW}" height="{H - 36}" rx="16" fill="#fbfbfd" stroke="#e5e7eb" stroke-width="1.4"/>')
    fig.legend.append(f'<text x="{LX + 24}" y="{LY + 38}" font-size="19" font-weight="700" fill="#111827">Legenda</text>')

    groups = {
        "A": ("Izvori podataka i priprema", [
            "ESConv (strategije S1–S8, redosled)", "ParaDetox (uvredljivo – neutralno)",
            "APPDIA (uvredljivo – neutralno)", "Naši školski parovi vanila → grubo",
            "Obrtanje, filtriranje, kalibracija"]),
        "B": ("Stalna memorija: pravila i sadržaj", [
            "Kartice strategija (8 iz ESConv)", "Eskalirajuća ponašanja (A1–A3)",
            "Tabela Δ ljutnje po strategiji", "Početni nivo ljutnje",
            "Osetljivost (brzina smirivanja)", "Cilj vežbe (aktivna kartica)"]),
        "C": ("Stalna memorija: persona i scenario", [
            "Scenario poziva", "Činjenice o detetu i oceni", "Uloga agenta: ljuti roditelj",
            "Uloga korisnika: nastavnik", "Temperament roditelja", "Skrivena potreba roditelja",
            "Obrazac razgovora: potezi i nivoi", "Parovi vanila → grubo (primeri)", "Pravila uloge i teme"]),
        "D": ("Obrada jednog poteza", [
            "Govor ili tekst nastavnika", "Detekcija kraja govora (VAD)", "Govor u tekst (STT)",
            "Strategije (S1–S8, A1–A3) i fokus", "Pritužbe, predlog, ljutnja nastavnika",
            "Ažuriranje ljutnje roditelja (Δ)", "Kraj razgovora? (dogovor/prekid/vreme)",
            "Izbor poteza i grube smernice", "Vanila rečenica → gruba rečenica",
            "Provera: nivo ljutnje, fokus, bezbednost", "Tekst u govor (TTS)", "Odgovor roditelja"]),
        "E": ("Radna memorija (svaki potez)", [
            "Poslednje replike nastavnika", "Strategije nastavnika po potezima",
            "Pritužbe i njihov status", "Ljutnja nastavnika po replikama", "Trenutni nivo ljutnje",
            "Istorija razgovora za jezički model", "Poslednje replike roditelja", "Faza i otkrivene činjenice",
            "Istorija ljutnje", "Broj poteza i proteklo vreme"]),
        "F": ("Trajni zapis (posle razgovora)", [
            "Kompletan transkript", "Kriva ljutnje roditelja i nastavnika", "Ishod razgovora",
            "Anonimizovani podaci za pilot-studiju", "Podaci za kalibraciju Δ i merača",
            "Izveštaj evaluatora (0–100)", "Preporučene kartice za ponavljanje"]),
    }
    shape_of = {k: n["shape"] for k, n in N.items()}
    ROW, HEAD = 22.5, 36

    def group_block(key, x, y, start_no):
        title, items = groups[key]
        z = ZONES[key]
        fig.legend.append(
            f'<rect x="{x}" y="{y - 13}" width="24" height="24" rx="6" fill="{z["fill"]}"/>'
            f'<text x="{x + 12}" y="{y - 1}" dy="0.36em" text-anchor="middle" font-size="13" font-weight="700" fill="#fff">{key}</text>'
            f'<text x="{x + 33}" y="{y - 1}" dy="0.36em" font-size="14.5" font-weight="700" fill="{z["text"]}">{esc(title)}</text>'
        )
        y += HEAD - 6
        no = start_no
        for it in items:
            fig.legend.append(draw_shape(shape_of[no], x + 12, y, 10.5, z["fill"], str(no), fs=10, sw=0))
            fig.legend.append(f'<text x="{x + 33}" y="{y}" dy="0.36em" font-size="14" fill="#1f2937">{esc(it)}</text>')
            y += ROW
            no += 1
        return y + 14, no

    c1x, c2x, y0 = LX + 24, LX + 352, LY + 82
    y, no = y0, 1
    for key in "ABC":
        y, no = group_block(key, c1x, y, no)

    # ključ oblika i veza (dno prve kolone)
    y += 2
    fig.legend.append(f'<text x="{c1x}" y="{y}" dy="0.36em" font-size="14.5" font-weight="700" fill="#111827">Oblici</text>')
    y += HEAD - 6
    sx = c1x
    for shape, label, wdt in [("circle", "Podatak", 98), ("square", "Obrada", 92), ("diamond", "Provera", 0)]:
        fig.legend.append(draw_shape(shape, sx + 12, y, 10.5, "#6b7280", None, sw=0))
        fig.legend.append(f'<text x="{sx + 31}" y="{y}" dy="0.36em" font-size="14" fill="#1f2937">{label}</text>')
        sx += wdt
    y += ROW + 14
    fig.legend.append(f'<text x="{c1x}" y="{y}" dy="0.36em" font-size="14.5" font-weight="700" fill="#111827">Veze</text>')
    y += HEAD - 6
    for kind, label in [("tok", "Tok obrade poteza"), ("upis", "Upis u radnu memoriju"),
                        ("citanje", "Čitanje iz memorije"), ("priprema", "Priprema sadržaja iz dataseta"),
                        ("posle", "Obrada posle razgovora")]:
        st = EDGE[kind]
        dash = f' stroke-dasharray="{st["dash"]}" stroke-linecap="round"' if st["dash"] else ""
        fig.legend.append(
            f'<path d="M{c1x},{y} L{c1x + 24},{y}" stroke="{st["color"]}" stroke-width="{st["width"]}"{dash} '
            f'marker-end="url(#{fig.marker(st["color"])})"/>'
            f'<text x="{c1x + 33}" y="{y}" dy="0.36em" font-size="14" fill="#1f2937">{label}</text>'
        )
        y += ROW
    y += 6
    for line in ["Deblja strelica koja polazi od zone ili", "ulazi u zonu odnosi se na celu zonu."]:
        fig.legend.append(f'<text x="{c1x}" y="{y}" dy="0.36em" font-size="13" fill="#6b7280">{line}</text>')
        y += 18
    col1_end = y

    y, no2 = y0, 21
    for key in "DEF":
        y, no2 = group_block(key, c2x, y, no2)
    col2_end = y
    return fig, col1_end, col2_end


# =====================================================================
# Stanja ljutnje (Slika 2 u dnevniku)
# =====================================================================

def stanja_ljutnje():
    W, H = 1530, 660
    fig = Fig(W, H)
    cy = 322
    xs = [175, 335, 495, 655, 815]
    colors = ["#16a34a", "#ca8a04", "#ea580c", "#dc2626", "#7f1d1d"]
    R = 28
    S = [dict(shape="circle", x=x, y=cy, r=R) for x in xs]

    calm, esc_c, dark = "#16a34a", "#dc2626", "#334155"
    mk = {c: fig.marker(c) for c in (calm, esc_c, dark, "#7f1d1d")}

    def badge(x, y, letter, color):
        fig.nodes.append(
            f'<circle cx="{x:.1f}" cy="{y:.1f}" r="11.5" fill="#ffffff" stroke="{color}" stroke-width="2"/>'
            f'<text x="{x:.1f}" y="{y:.1f}" dy="0.36em" text-anchor="middle" font-size="12.5" font-weight="700" fill="{color}">{letter}</text>'
        )

    def arc(i, j, up, color, letter):
        a, b = S[i], S[j]
        sgn = -1 if up else 1
        ang = math.radians(42)
        dirx = 1 if b["x"] > a["x"] else -1
        p0 = (a["x"] + dirx * R * math.sin(ang), a["y"] + sgn * R * math.cos(ang))
        p3 = (b["x"] - dirx * R * math.sin(ang), b["y"] + sgn * R * math.cos(ang))
        lift = 92
        c1 = (p0[0] + dirx * 34, p0[1] + sgn * lift)
        c2 = (p3[0] - dirx * 34, p3[1] + sgn * lift)
        # skrati kraj zbog vrha strelice
        ux, uy = unit(c2[0], c2[1], p3[0], p3[1])
        p3s = (p3[0] - ux * 2, p3[1] - uy * 2)
        fig.edges.append(
            f'<path d="M{p0[0]:.1f},{p0[1]:.1f} C{c1[0]:.1f},{c1[1]:.1f} {c2[0]:.1f},{c2[1]:.1f} {p3s[0]:.1f},{p3s[1]:.1f}" '
            f'fill="none" stroke="{color}" stroke-width="2.4" marker-end="url(#{mk[color]})"/>'
        )
        mx = (p0[0] + 3 * c1[0] + 3 * c2[0] + p3[0]) / 8
        my = (p0[1] + 3 * c1[1] + 3 * c2[1] + p3[1]) / 8
        badge(mx, my, letter, color)

    # eskalacija (gore) i smirivanje (dole)
    for i, letter in zip(range(4), "fghi"):
        arc(i, i + 1, True, esc_c, letter)
    for i, letter in zip(range(4, 0, -1), "bcde"):
        arc(i, i - 1, False, calm, letter)

    # početak
    sx, sy = xs[2], 112
    fig.nodes.append(f'<circle cx="{sx}" cy="{sy}" r="8" fill="{dark}"/>')
    fig.edges.append(
        f'<path d="M{sx},{sy + 10} L{sx},{cy - R - 3}" stroke="{dark}" stroke-width="2.2" stroke-dasharray="7 4" '
        f'marker-end="url(#{mk[dark]})"/>'
    )
    badge(sx, (sy + cy - R) / 2 - 6, "a", dark)

    # krajevi
    def end(x, color, glyph):
        fig.nodes.append(
            f'<circle cx="{x}" cy="{cy}" r="17" fill="#ffffff" stroke="{color}" stroke-width="3"/>'
            f'<circle cx="{x}" cy="{cy}" r="10.5" fill="{color}"/>'
            f'<text x="{x}" y="{cy}" dy="0.36em" text-anchor="middle" font-size="12" font-weight="700" fill="#fff">{glyph}</text>'
        )
    e1x, e2x = 52, 940
    end(e1x, calm, "✓")
    end(e2x, "#7f1d1d", "✕")
    fig.edges.append(f'<path d="M{xs[0] - R - 2},{cy} L{e1x + 20},{cy}" stroke="{calm}" stroke-width="2.4" marker-end="url(#{mk[calm]})"/>')
    fig.edges.append(f'<path d="M{xs[4] + R + 2},{cy} L{e2x - 20},{cy}" stroke="#7f1d1d" stroke-width="2.4" marker-end="url(#{mk["#7f1d1d"]})"/>')

    for i, (x, c) in enumerate(zip(xs, colors)):
        fig.nodes.append(draw_shape("circle", x, cy, R, c, str(i + 1), fs=17, sw=2.5))

    # legenda
    LX, LY, LW = 1000, 18, 510
    fig.legend.append(f'<rect x="{LX}" y="{LY}" width="{LW}" height="{H - 36}" rx="16" fill="#fbfbfd" stroke="#e5e7eb" stroke-width="1.4"/>')
    fig.legend.append(f'<text x="{LX + 24}" y="{LY + 38}" font-size="19" font-weight="700" fill="#111827">Legenda</text>')
    x, y = LX + 24, LY + 78
    ROW = 22.5

    def head(t):
        nonlocal y
        fig.legend.append(f'<text x="{x}" y="{y}" dy="0.36em" font-size="14.5" font-weight="700" fill="#111827">{esc(t)}</text>')
        y += 28

    head("Stanja (nivo ljutnje 0–10)")
    states = ["Smiren (0–2): sarađuje, prihvata predloge", "Nezadovoljan (3–4): kratko i skeptično",
              "Ljut (5–6): ponavlja pritužbu", "Jako ljut (7–8): prekida, generalizuje",
              "Pred prekidom (9–10): preti žalbom"]
    for i, t in enumerate(states):
        fig.legend.append(draw_shape("circle", x + 12, y, 10.5, colors[i], str(i + 1), fs=10.5, sw=0))
        fig.legend.append(f'<text x="{x + 33}" y="{y}" dy="0.36em" font-size="14" fill="#1f2937">{esc(t)}</text>')
        y += ROW
    y += 12
    head("Prelazi")
    trans = [("a", dark, "Početak razgovora (početni nivo se podešava)"),
             ("b", calm, "Imenovanje emocije (Reflection of feelings)"),
             ("c", calm, "Parafraza i otvorena pitanja"),
             ("d", calm, "Potvrda brige roditelja"),
             ("e", calm, "Predlog rešenja kad je ljutnja ≤ 5"),
             ("f", esc_c, "Ljutnja u tonu nastavnika, skretanje sa teme"),
             ("g", esc_c, "Pozivanje na pravila"),
             ("h", esc_c, "Minimizovanje, prerano nuđenje rešenja"),
             ("i", esc_c, "Pretnja autoritetom, okrivljavanje")]
    for letter, col, t in trans:
        fig.legend.append(
            f'<circle cx="{x + 12}" cy="{y}" r="10" fill="#fff" stroke="{col}" stroke-width="2"/>'
            f'<text x="{x + 12}" y="{y}" dy="0.36em" text-anchor="middle" font-size="11.5" font-weight="700" fill="{col}">{letter}</text>'
            f'<text x="{x + 33}" y="{y}" dy="0.36em" font-size="14" fill="#1f2937">{esc(t)}</text>'
        )
        y += ROW
    y += 12
    head("Kraj razgovora")
    for col, _glyph, t in [(calm, "✓", "Rešeno: ljutnja ≤ 3 i pritužbe rešene"),
                          ("#7f1d1d", "✕", "Prekid: ljutnja ≥ 9 dva poteza zaredom")]:
        fig.legend.append(
            f'<circle cx="{x + 12}" cy="{y}" r="10" fill="#fff" stroke="{col}" stroke-width="2.4"/>'
            f'<circle cx="{x + 12}" cy="{y}" r="6" fill="{col}"/>'
            f'<text x="{x + 33}" y="{y}" dy="0.36em" font-size="14" fill="#1f2937">{esc(t)}</text>'
        )
        y += ROW
    y += 8
    for line in ["Zelene strelice: smirivanje (Δ < 0), crvene: eskalacija (Δ > 0).",
                 "U jednom potezu ljutnja se menja najviše za ±2.",
                 "Razgovor se završava i kada istekne vreme (oko 8 minuta)."]:
        fig.legend.append(f'<text x="{x}" y="{y}" dy="0.36em" font-size="13" fill="#6b7280">{esc(line)}</text>')
        y += 18
    return fig, y


if __name__ == "__main__":
    out = sys.argv[1]
    f1, a, b = memorija_agenta()
    open(f"{out}/memorija_agenta.svg", "w", encoding="utf-8").write(f1.svg())
    f2, c = stanja_ljutnje()
    open(f"{out}/stanja_ljutnje.svg", "w", encoding="utf-8").write(f2.svg())
    print("legend ends:", round(a), round(b), "| fig2 legend end:", round(c))
