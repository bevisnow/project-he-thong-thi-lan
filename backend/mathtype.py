import struct


def read_stream(data: bytes, want: str) -> bytes | None:
    """Đọc 1 stream trong file OLE (Compound File v3/v4). Chỉ đủ dùng cho object công thức nhỏ."""
    if data[:8] != b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1":
        return None
    sh, msh = struct.unpack_from("<HH", data, 30)
    ss, mss = 1 << sh, 1 << msh
    (first_dir,) = struct.unpack_from("<I", data, 48)
    cutoff, first_mfat = struct.unpack_from("<II", data, 56)
    first_difat, n_difat = struct.unpack_from("<II", data, 68)
    sec = lambda i: data[(i + 1) * ss : (i + 2) * ss]
    difat = list(struct.unpack_from("<109I", data, 76))
    while first_difat < 0xFFFFFFFA and n_difat: 
        s = struct.unpack("<%dI" % (ss // 4), sec(first_difat))
        difat += s[:-1]
        first_difat, n_difat = s[-1], n_difat - 1
    fat = []
    for i in difat:
        if i < 0xFFFFFFFA:
            fat += struct.unpack("<%dI" % (ss // 4), sec(i))

    def chain(start, table):
        out, seen = [], set()
        while start < 0xFFFFFFFA and start not in seen and start < len(table):
            seen.add(start)
            out.append(start)
            start = table[start]
        return out

    dirs = b"".join(sec(i) for i in chain(first_dir, fat))
    entries = []
    for o in range(0, len(dirs), 128):
        e = dirs[o : o + 128]
        n = struct.unpack_from("<H", e, 64)[0]
        entries.append(
            (
                e[: max(n - 2, 0)].decode("utf-16-le", "replace"),
                e[66],
                struct.unpack_from("<I", e, 116)[0],
                struct.unpack_from("<I", e, 120)[0],
            )
        )
    root = entries[0]
    for name, typ, start, size in entries:
        if typ == 2 and name == want:
            if size < cutoff:
                mini = b"".join(sec(i) for i in chain(root[2], fat))
                mfat = []
                for i in chain(first_mfat, fat):
                    mfat += struct.unpack("<%dI" % (ss // 4), sec(i))
                return b"".join(
                    mini[i * mss : (i + 1) * mss] for i in chain(start, mfat)
                )[:size]
            return b"".join(sec(i) for i in chain(start, fat))[:size]
    return None


GREEK = {
    c: "\\" + n
    for c, n in zip(
        "αβγδεζηθικλμνξοπρστυφχψω",
        "alpha beta gamma delta epsilon zeta eta theta iota kappa lambda mu nu xi o pi rho sigma tau upsilon phi chi psi omega".split(),
    )
    if n != "o"
}
GREEK.update(
    {
        "ε": "\\varepsilon",
        "φ": "\\varphi",
        "ϕ": "\\phi",
        "ϑ": "\\vartheta",
        "ς": "\\varsigma",
        "Γ": "\\Gamma",
        "Δ": "\\Delta",
        "Θ": "\\Theta",
        "Λ": "\\Lambda",
        "Ξ": "\\Xi",
        "Π": "\\Pi",
        "Σ": "\\Sigma",
        "Φ": "\\Phi",
        "Ψ": "\\Psi",
        "Ω": "\\Omega",
    }
)
SYM = {
    "−": "-",
    "×": "\\times ",
    "·": "\\cdot ",
    "⋅": "\\cdot ",
    "÷": "\\div ",
    "±": "\\pm ",
    "∓": "\\mp ",
    "≤": "\\le ",
    "≥": "\\ge ",
    "≠": "\\ne ",
    "≈": "\\approx ",
    "≡": "\\equiv ",
    "∞": "\\infty ",
    "→": "\\to ",
    "←": "\\leftarrow ",
    "⇒": "\\Rightarrow ",
    "⇔": "\\Leftrightarrow ",
    "⇐": "\\Leftarrow ",
    "↔": "\\leftrightarrow ",
    "∈": "\\in ",
    "∉": "\\notin ",
    "⊂": "\\subset ",
    "⊃": "\\supset ",
    "⊆": "\\subseteq ",
    "⊇": "\\supseteq ",
    "∪": "\\cup ",
    "∩": "\\cap ",
    "∅": "\\emptyset ",
    "∀": "\\forall ",
    "∃": "\\exists ",
    "∠": "\\angle ",
    "°": "^{\\circ}",
    "′": "'",
    "″": "''",
    "∥": "\\parallel ",
    "⊥": "\\perp ",
    "∼": "\\sim ",
    "∝": "\\propto ",
    "∂": "\\partial ",
    "∇": "\\nabla ",
    "…": "\\ldots ",
    "⋯": "\\cdots ",
    "∴": "\\therefore ",
    "∵": "\\because ",
    "∘": "\\circ ",
    "∆": "\\Delta ",
    "∑": "\\sum ",
    "∏": "\\prod ",
    "∫": "\\int ",
    "√": "\\surd ",
    "⟨": "\\langle ",
    "⟩": "\\rangle ",
    "ℝ": "\\mathbb{R}",
    "ℕ": "\\mathbb{N}",
    "ℤ": "\\mathbb{Z}",
    "ℚ": "\\mathbb{Q}",
    "ℂ": "\\mathbb{C}",
    " ": " ",
    " ": " ",
    " ": "\\ ",
    " ": "\\ ",
    "{": "\\{",
    "}": "\\}",
    "#": "\\#",
    "$": "\\$",
    "%": "\\%",
    "&": "\\&",
    "_": "\\_",
    "~": "\\sim ",
    "\\": "\\backslash ",
    "^": "\\wedge ",
}
SYM.update(GREEK)
FENCE = {
    0: ("\\langle", "\\rangle"),
    1: ("(", ")"),
    2: ("\\{", "\\}"),
    3: ("[", "]"),
    4: ("|", "|"),
    5: ("\\|", "\\|"),
    6: ("\\lfloor", "\\rfloor"),
    7: ("\\lceil", "\\rceil"),
    8: ("[", ")"),
}
BIGOP = {16: "\\sum", 17: "\\prod", 18: "\\coprod", 19: "\\bigcup", 20: "\\bigcap"}
ACCENT = {31: "\\vec", 32: "\\tilde", 33: "\\hat", 12: "\\underline", 13: "\\overline"}
EMBELL = {
    2: "\\dot",
    3: "\\ddot",
    4: "\\dddot",
    8: "\\tilde",
    9: "\\hat",
    11: "\\vec",
    16: "\\underline",
    17: "\\overline",
    18: "\\widehat",
}


class Bad(Exception):
    pass


class R:
    def __init__(s, b):
        s.b, s.i = b, 0

    def u8(s):
        v = s.b[s.i]
        s.i += 1
        return v

    def u16(s):
        v = struct.unpack_from("<H", s.b, s.i)[0]
        s.i += 2
        return v

    def cstr(s):
        j = s.b.index(0, s.i)
        v = s.b[s.i : j]
        s.i = j + 1
        return v


def nudge(r, attrs):
    if attrs & 0x08:
        if r.u8() == 128 and r.u8() == 128:
            r.u16()
            r.u16()


def objects(r):
    """Đọc danh sách đối tượng tới END. Trả về list (loại, giá trị)."""
    out = []
    while True:
        tag = r.u8()
        if tag == 0:
            return out
        if tag in (10, 11, 12, 13, 14):
            continue  # đổi cỡ chữ
        if tag == 9:  # SIZE
            if r.u8() == 101:
                r.u16()
            else:
                r.u8()
        elif tag == 15:  # COLOR
            r.u16() if False else r.u8()
        elif tag == 16:  # COLOR_DEF
            a = r.u8()
            r.i += 8 if a & 1 else 6
            if a & 4:
                r.cstr()
        elif tag == 1:
            a = r.u8()
            nudge(r, a)
            if a & 4:
                r.u16()
            if a & 2:  # ruler
                n = r.u8()
                r.i += 3 * n
            out.append(("line", None if a & 1 else objects(r)))
        elif tag == 2:
            a = r.u8()
            nudge(r, a)
            face = r.u8()
            code = None if a & 0x20 else r.u16()
            c8 = r.u8() if a & 4 else None
            if a & 0x10:
                code = r.u16()
            emb = []
            if a & 1:
                for t, v in objects(r):
                    emb.append(v)
            if code is None:
                code = c8 or 63
            out.append(("char", (face & 0x7F, chr(code), emb)))
        elif tag == 3:
            a = r.u8()
            nudge(r, a)
            sel = r.u8()
            var = r.u8()
            if var & 0x80:
                var = ((var & 0x7F) << 8) | r.u8()
            r.u8()  # tuỳ chọn riêng của template
            out.append(("tmpl", (sel, var, objects(r))))
        elif tag == 4:
            a = r.u8()
            nudge(r, a)
            r.u8()
            r.u8()
            out.append(("pile", objects(r)))
        elif tag == 5:
            a = r.u8()
            nudge(r, a)
            r.u8()
            r.u8()
            r.u8()
            rows, cols = r.u8(), r.u8()
            r.i += ((rows + 1) * 2 + 7) // 8 + ((cols + 1) * 2 + 7) // 8
            out.append(("matrix", (rows, cols, objects(r))))
        elif tag == 6:  
            a = r.u8()
            nudge(r, a)
            out.append(("embell", r.u8()))
        elif tag == 7:  
            n = r.u8()
            r.i += 3 * n
        elif tag == 8:  
            r.i += 2
        elif (
            tag >= 100
        ):  
            r.i += r.u8()
        else:
            raise Bad(f"tag {tag}")


def header(r):
    """Bỏ qua header MTEF + các định nghĩa font/ưu tiên, dừng ở đối tượng đầu tiên của công thức."""
    if r.u8() != 5:
        raise Bad("không phải MTEF v5")
    r.i += 4
    r.cstr()
    r.u8()
    while True:
        tag = r.b[r.i]
        if tag == 19:
            r.i += 1
            r.cstr()
        elif tag == 17:
            r.i += 2
            r.cstr()
        elif tag == 8:
            r.i += 3
        elif tag >= 100:
            r.i += 1
            r.i += r.u8()
        elif tag == 0: 
            r.i += 1
        elif tag == 18:
            r.i += 1
            r.u8()
            for _ in range(
                2
            ):  
                n, nib = r.u8(), []
                need = n
                while need:
                    b = r.u8()
                    nib += [b >> 4, b & 15]
                    need = n - nib.count(15)
            n = r.u8()
            for _ in range(n):
                if r.u8():
                    r.u8()
        else:
            return


def render_char(face, ch, emb):
    s = SYM.get(ch, ch)
    for e in emb:
        if e in (5, 6, 7):
            s += "'" * (e - 4 if e < 7 else 1)
        elif e in EMBELL:
            s = f"{EMBELL[e]}{{{s}}}"
    return s


def lines(objs):
    return [o for o in objs if o[0] in ("line", "pile", "matrix")]


def txt(objs):
    out, fn = (
        [],
        "",
    )  
    for kind, v in objs:
        if kind == "char" and v[0] in (1, 2) and v[1].isalpha() and not v[2]:
            fn += v[1]
            continue
        if fn:
            out.append(("t", "\\mathrm{%s}" % fn))
            fn = ""
        if kind == "char":
            out.append(("t", render_char(*v)))
        elif kind == "line":
            out.append(("t", txt(v) if v else ""))
        elif kind == "tmpl":
            out.append((v[0], tmpl(*v)))
        elif kind == "pile":
            out.append(
                (
                    "t",
                    "\\begin{array}{l}"
                    + "\\\\ ".join(txt([l]) for l in v if l[0] == "line")
                    + "\\end{array}",
                )
            )
        elif kind == "matrix":
            rows, cols, cells = v
            c = [txt([x]) for x in cells if x[0] == "line"]
            out.append(
                (
                    "t",
                    "\\begin{matrix}"
                    + "\\\\ ".join(
                        " & ".join(c[r * cols : (r + 1) * cols]) for r in range(rows)
                    )
                    + "\\end{matrix}",
                )
            )
    if fn:
        out.append(("t", "\\mathrm{%s}" % fn))
    res = []
    for sel, p in out:
        if sel == 28 and res and res[-1][0] == 28:
            res[-1] = (28, res[-1][1][:-1] + p[2:])
        else:
            res.append((sel, p))
    return "".join(p for _, p in res)


def tmpl(sel, var, objs):
    sl = [txt([o]) if o[1] is not None else "" for o in lines(objs)]
    g = lambda i: sl[i] if i < len(sl) else ""
    if sel in FENCE:
        l, r = FENCE[sel]
        return f"\\left{l if var & 1 else '.'} {g(0)} \\right{r if var & 2 else '.'}"
    if sel == 9: 
        c = [SYM.get(v[1], v[1]) for k, v in objs if k == "char"] + ["."] * 2
        return f"\\left{c[0]} {g(0)} \\right{c[1]}"
    if sel == 10:
        return f"\\sqrt[{g(1)}]{{{g(0)}}}" if var == 1 else f"\\sqrt{{{g(0)}}}"
    if sel == 11:
        return f"\\frac{{{g(0)}}}{{{g(1)}}}"
    if sel in (12, 13, 31, 32, 33):
        return f"{ACCENT[sel]}{{{g(0)}}}"
    if sel == 15:
        return f"\\int{'_{%s}' % g(1) if g(1) else ''}{'^{%s}' % g(2) if g(2) else ''} {g(0)}"
    if sel in BIGOP:
        return f"{BIGOP[sel]}{'_{%s}' % g(1) if g(1) else ''}{'^{%s}' % g(2) if g(2) else ''} {g(0)}"
    if sel == 23:
        return f"{g(0)}{'_{%s}' % g(1) if g(1) else ''}"
    if sel == 27:
        return f"_{{{g(0)}}}"
    if sel == 28:
        e = sl[-1] if sl else ""
        return (
            "^{\\circ}" if e == "\\mathrm{o}" else f"^{{{e}}}"
        )  
    if sel == 29:
        return f"_{{{g(0)}}}^{{{g(1)}}}"
    raise Bad(f"template {sel}")


def to_latex(ole_stream: bytes) -> str:
    r = R(
        ole_stream[ole_stream[0] | ole_stream[1] << 8 :]
    )  
    header(r)
    return txt(objects(r)).strip()
