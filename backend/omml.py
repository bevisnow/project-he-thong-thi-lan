"""Word Equation (OMML) -> LaTeX. Thành phần chưa hỗ trợ thì báo lỗi, không bỏ im lặng."""

from mathtype import SYM

M = "{http://schemas.openxmlformats.org/officeDocument/2006/math}"
W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
NARY = {"∑": "\\sum", "∏": "\\prod", "∫": "\\int", "∬": "\\iint", "∭": "\\iiint",
        "∮": "\\oint", "⋃": "\\bigcup", "⋂": "\\bigcap"}
ACC = {"\u0302": "\\hat", "\u0303": "\\tilde", "\u0307": "\\dot", "\u0308": "\\ddot",
       "\u0304": "\\overline", "\u20d7": "\\vec", "→": "\\vec"}
DELIM = {"{": "\\{", "}": "\\}", "⟨": "\\langle", "⟩": "\\rangle", "⌊": "\\lfloor",
         "⌋": "\\rfloor", "⌈": "\\lceil", "⌉": "\\rceil", "‖": "\\|", "": "."}
LIMFN = {"lim", "max", "min", "sup", "inf"}
BOX = {"e", "num", "den", "sub", "sup", "deg", "lim", "fName", "oMath", "box"}  # chỉ chứa nội dung


def conv(el):
    return "".join(node(c) for c in el)


def arg(el, name):
    c = el.find(M + name)
    return conv(c) if c is not None else ""


def prop(el, pr, name, default):
    p = el.find(M + pr)
    c = p.find(M + name) if p is not None else None
    return c.get(M + "val", default) if c is not None else default


def node(el):
    name = el.tag[len(M):] if el.tag.startswith(M) else el.tag
    if name.endswith("Pr") or el.tag == W + "rPr":
        return ""  # thuộc tính định dạng
    if name in BOX:
        return conv(el)
    if name == "r":
        raw = "".join(x.text or "" for x in el if x.tag in (M + "t", W + "t"))
        s = "".join(SYM.get(c, c) for c in raw)
        return "\\mathrm{%s}" % s if prop(el, "rPr", "sty", "") == "p" and raw.isalpha() else s
    if name == "f":
        kind = prop(el, "fPr", "type", "bar")
        fmt = {"noBar": "\\binom{%s}{%s}", "lin": "{%s}/{%s}"}.get(kind, "\\frac{%s}{%s}")
        return fmt % (arg(el, "num"), arg(el, "den"))
    if name == "rad":
        deg = arg(el, "deg")
        return "\\sqrt[%s]{%s}" % (deg, arg(el, "e")) if deg else "\\sqrt{%s}" % arg(el, "e")
    if name == "sSup":
        return "{%s}^{%s}" % (arg(el, "e"), arg(el, "sup"))
    if name == "sSub":
        return "{%s}_{%s}" % (arg(el, "e"), arg(el, "sub"))
    if name == "sSubSup":
        return "{%s}_{%s}^{%s}" % (arg(el, "e"), arg(el, "sub"), arg(el, "sup"))
    if name == "sPre":
        return "{}_{%s}^{%s}%s" % (arg(el, "sub"), arg(el, "sup"), arg(el, "e"))
    if name == "nary":
        chr_ = prop(el, "naryPr", "chr", "∫")
        if chr_ not in NARY:
            raise ValueError(f"ký hiệu '{chr_}' chưa hỗ trợ")
        hidden = lambda h: prop(el, "naryPr", h, "0") in ("1", "on", "true")
        sub = "" if hidden("subHide") else arg(el, "sub")
        sup = "" if hidden("supHide") else arg(el, "sup")
        return "%s%s%s {%s}" % (NARY[chr_], "_{%s}" % sub if sub else "",
                                "^{%s}" % sup if sup else "", arg(el, "e"))
    if name == "d":
        b, e, sep = (prop(el, "dPr", k, d) for k, d in (("begChr", "("), ("endChr", ")"), ("sepChr", "|")))
        body = (" %s " % DELIM.get(sep, sep)).join(conv(x) for x in el.findall(M + "e"))
        return "\\left%s %s \\right%s" % (DELIM.get(b, b), body, DELIM.get(e, e))
    if name == "eqArr":
        return "\\begin{array}{l}" + "\\\\ ".join(conv(x) for x in el.findall(M + "e")) + "\\end{array}"
    if name == "m":
        rows = (" & ".join(conv(c) for c in r.findall(M + "e")) for r in el.findall(M + "mr"))
        return "\\begin{matrix}" + "\\\\ ".join(rows) + "\\end{matrix}"
    if name == "func":
        f = arg(el, "fName")
        return ("\\mathrm{%s}" % f if f.isalpha() else f) + "\\, " + arg(el, "e")
    if name == "limLow":
        e, lim = arg(el, "e"), arg(el, "lim")
        base = e[len("\\mathrm{"):-1] if e.startswith("\\mathrm{") else e
        return "\\%s_{%s}" % (base, lim) if base in LIMFN else "\\underset{%s}{%s}" % (lim, e)
    if name == "limUpp":
        return "\\overset{%s}{%s}" % (arg(el, "lim"), arg(el, "e"))
    if name == "acc":
        c = prop(el, "accPr", "chr", "\u0302")
        if c not in ACC:
            raise ValueError(f"dấu '{c}' chưa hỗ trợ")
        return "%s{%s}" % (ACC[c], arg(el, "e"))
    if name == "bar":
        top = prop(el, "barPr", "pos", "bot") == "top"
        return ("\\overline{%s}" if top else "\\underline{%s}") % arg(el, "e")
    raise ValueError(f"thành phần '{name}' chưa hỗ trợ")


def to_latex(oMath):
    return conv(oMath).strip()
