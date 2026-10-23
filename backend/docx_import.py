import re
import secrets
import unicodedata
import warnings
import zipfile
from io import BytesIO
from xml.etree import ElementTree as ET

import mathtype

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
O = "{urn:schemas-microsoft-com:office:office}"
V = "{urn:schemas-microsoft-com:vml}"
A = "{http://schemas.openxmlformats.org/drawingml/2006/main}"
RID = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"
IMG_EXT = {".png", ".jpg", ".jpeg", ".gif", ".webp"}
LEVEL = {"1": "NB", "2": "TH", "3": "VD", "4": "VDC"}
KIND = {
    "": "multiple_choice",
    "TN": "multiple_choice",
    "ĐS": "true_false",
    "DS": "true_false",
    "ĐT": "short_answer",
    "TLN": "short_answer",
}



def validate_package(data):
    try:
        with zipfile.ZipFile(BytesIO(data)) as archive:
            entries = archive.infolist()
            if len(entries) > 2048:
                raise ValueError("Tệp có quá nhiều thành phần")
            if sum(item.file_size for item in entries) > 50 * 1024 * 1024:
                raise ValueError("Nội dung giải nén vượt quá 50 MB")
            if any(item.file_size > 20 * 1024 * 1024 for item in entries):
                raise ValueError("Một thành phần trong tệp vượt quá 20 MB")
    except zipfile.BadZipFile as exc:
        raise ValueError("Tệp không phải gói Office ZIP hợp lệ") from exc


def valid_image(data, ext):
    signatures = {
        ".png": data.startswith(b"\x89PNG\r\n\x1a\n"),
        ".jpg": data.startswith(b"\xff\xd8\xff"),
        ".jpeg": data.startswith(b"\xff\xd8\xff"),
        ".gif": data.startswith((b"GIF87a", b"GIF89a")),
        ".webp": data.startswith(b"RIFF") and data[8:12] == b"WEBP",
    }
    return signatures.get(ext, False)


def sanitize_image(data, ext):
    if not valid_image(data, ext):
        raise ValueError("Nội dung ảnh không khớp với định dạng tệp")
    try:
        from PIL import Image, ImageSequence
    except ImportError as exc:
        raise RuntimeError("Cài dependency Pillow từ requirements.txt để xử lý ảnh") from exc

    expected = {".png": "PNG", ".jpg": "JPEG", ".jpeg": "JPEG", ".gif": "GIF", ".webp": "WEBP"}[ext]
    Image.MAX_IMAGE_PIXELS = 20_000_000
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(BytesIO(data)) as source:
                if source.format != expected or source.width * source.height > 20_000_000:
                    raise ValueError("Ảnh sai định dạng hoặc vượt quá 20 megapixel")
                if getattr(source, "n_frames", 1) > 100:
                    raise ValueError("Ảnh động có quá nhiều khung hình")
                frames, pixels = [], 0
                for frame in ImageSequence.Iterator(source):
                    pixels += frame.width * frame.height
                    if pixels > 20_000_000:
                        raise ValueError("Tổng ảnh vượt quá 20 megapixel")
                    mode = "RGB" if expected in ("JPEG", "GIF") else "RGBA"
                    frames.append(frame.convert(mode))
                if not frames:
                    raise ValueError("Ảnh không có dữ liệu")
                output = BytesIO()
                animated = expected in ("GIF", "WEBP") and len(frames) > 1
                frames[0].save(
                    output,
                    format=expected,
                    save_all=animated,
                    append_images=frames[1:] if animated else [],
                    duration=source.info.get("duration", 100),
                    loop=source.info.get("loop", 0),
                    quality=90,
                )
                cleaned = output.getvalue()
                if len(cleaned) > 5 * 1024 * 1024:
                    raise ValueError("Ảnh sau xử lý vượt quá 5MB")
                return cleaned
    except (Image.DecompressionBombError, Image.DecompressionBombWarning) as exc:
        raise ValueError("Ảnh vượt quá giới hạn xử lý an toàn") from exc
    except (OSError, SyntaxError) as exc:
        raise ValueError("Tệp ảnh bị hỏng hoặc không thể giải mã") from exc

def norm(s):
    return unicodedata.normalize("NFC", s or "").strip()


class Doc:
    def __init__(self, data, media_dir=None):
        validate_package(data)
        self.z = zipfile.ZipFile(BytesIO(data))
        rels = ET.fromstring(self.z.read("word/_rels/document.xml.rels"))
        self.rel = {r.get("Id"): r.get("Target") for r in rels}
        self.media_dir = media_dir  
        self.pending_images = {}
        self.root = ET.fromstring(self.z.read("word/document.xml"))

    def part(self, rid):
        return self.z.read("word/" + self.rel[rid].lstrip("/").removeprefix("word/"))

    def image(self, rid):
        name = self.rel.get(rid, "")
        ext = "." + name.rsplit(".", 1)[-1].lower()
        if ext not in IMG_EXT:
            raise ValueError(
                f"Ảnh định dạng {ext} chưa hỗ trợ, hãy chèn lại bằng png/jpg"
            )
        image_data = sanitize_image(self.part(rid), ext)
        out = secrets.token_hex(8) + ext
        if self.media_dir:
            self.pending_images[out] = image_data
        return f"![](/media/{out})"

    def save_images(self):
        if self.media_dir:
            for name, data in self.pending_images.items():
                (self.media_dir / name).write_bytes(data)
            self.pending_images.clear()

    def text(self, el):
        out = []
        for ch in el:
            t = ch.tag
            if t == W + "t":
                out.append(ch.text or "")
            elif t == W + "tab":
                out.append("\t")
            elif t == W + "br":
                out.append("\n")
            elif t == W + "object":
                ole = ch.find(O + "OLEObject")
                if ole is None:
                    out.append(self.text(ch))
                    continue
                try:
                    data = mathtype.read_stream(
                        self.part(ole.get(RID + "id")), "Equation Native"
                    )
                    out.append("$" + mathtype.to_latex(data) + "$")
                except (
                    Exception
                ) as e:  # công thức lạ: báo lỗi chứ không lặng lẽ làm mất
                    raise ValueError(
                        f"Không đọc được một công thức MathType ({type(e).__name__}: {e}). Hãy gõ lại bằng Word Equation hoặc báo admin"
                    )
            elif t in (W + "drawing", W + "pict"):
                for b in ch.iter(A + "blip"):
                    out.append(self.image(b.get(RID + "embed")))
                for b in ch.iter(V + "imagedata"):
                    out.append(self.image(b.get(RID + "id")))
            else:
                out.append(self.text(ch))
        return "".join(out)

    def rows(self):
        """Mỗi dòng bảng (trừ tiêu đề) -> dict; lỗi đọc công thức/ảnh đi kèm trong khoá 'error'."""
        tbl = next(self.root.iter(W + "tbl"), None)
        if tbl is None:
            raise ValueError("Không thấy bảng câu hỏi trong file")
        if len(tbl.findall(W + "tr")) > 5001:
            raise ValueError("Mỗi lần import tối đa 5.000 câu hỏi")
        out = []
        for n, tr in enumerate(tbl.findall(W + "tr"), start=1):
            cells = []
            for tc in tr.findall(W + "tc"):
                try:
                    cells.append(
                        "\n".join(
                            self.text(p).rstrip() for p in tc.findall(W + "p")
                        ).strip()
                    )
                except ValueError as e:
                    cells.append(e)
            if n == 1 and norm(str(cells[0])).upper() == "STT":
                continue
            cells += [""] * (6 - len(cells))
            err = next((c for c in cells if isinstance(c, Exception)), None)
            if err:
                out.append(
                    {"row": n, "code": str(cells[1]), "text": "", "error": str(err)}
                )
                continue
            out.append(
                {
                    "row": n,
                    "code": cells[1],
                    "text": cells[2],
                    "answer": norm(cells[3]),
                    "kind": norm(cells[4]).upper(),
                    "level": norm(cells[5]).upper(),
                    "error": None,
                }
            )
        return out


def split_marks(text, pattern, n):
    """Tách 'đề\\nA. ..\\nB. ..' thành (đề, [n phần]); các nhãn phải đủ và đúng thứ tự."""
    pos = []
    start = 0
    for lab in range(n):
        m = re.compile(pattern(lab)).search(text, start)
        if not m:
            raise ValueError(
                "Không tách được đủ %d phương án/ý, kiểm tra nhãn %s"
                % (n, pattern.__doc__)
            )
        pos.append((m.start(), m.end()))
        start = m.end()
    stem = text[: pos[0][0]].strip()
    parts = [
        text[e : (pos[i + 1][0] if i + 1 < n else len(text))].strip()
        for i, (_, e) in enumerate(pos)
    ]
    return stem, parts


def tn_pattern(i):
    """A. B. C. D."""
    return r"(?:^|(?<=[\n\t]))[ \t]*%s\.[ \t]*" % "ABCD"[i]


def ds_pattern(i):
    """a) b) c) d)"""
    return r"(?:^|(?<=[\n\t]))[ \t]*%s\)[ \t]*" % "abcd"[i]


def parse_row(r):
    """dict thô -> (question_type, difficulty, stem, options[(key,text,correct)], accepted[str])"""
    if r["error"]:
        raise ValueError(r["error"])
    qtype = KIND.get(r["kind"])
    if not qtype:
        raise ValueError(
            f"Loại câu '{r['kind']}' không hợp lệ (để trống = trắc nghiệm, ĐS, ĐT)"
        )
    diff = LEVEL.get(r["level"], r["level"] if r["level"] in LEVEL.values() else None)
    if not diff:
        raise ValueError("Mức độ phải là 1-4 (hoặc NB/TH/VD/VDC)")
    text, ans = r["text"], r["answer"]
    if not text:
        raise ValueError("Thiếu nội dung câu hỏi")
    if qtype == "short_answer":
        if not ans:
            raise ValueError("Thiếu đáp án")
        alts = [ans] + (
            [ans.replace(".", ",")]
            if "." in ans
            else [ans.replace(",", ".")] if "," in ans else []
        )
        return qtype, diff, text, [], list(dict.fromkeys(alts))
    if qtype == "multiple_choice":
        stem, parts = split_marks(text, tn_pattern, 4)
        key = ans.upper()
        if key not in ("A", "B", "C", "D"):
            raise ValueError("Đáp án trắc nghiệm phải là A, B, C hoặc D")
        return qtype, diff, stem, [(k, p, k == key) for k, p in zip("ABCD", parts)], []
    stem, parts = split_marks(text, ds_pattern, 4)
    flags = [c for c in ans.upper().replace("Đ", "D") if c in "DS"]
    if len(flags) != 4:
        raise ValueError("Đáp án đúng/sai phải gồm 4 ký tự Đ/S, ví dụ ĐSĐS")
    return (
        qtype,
        diff,
        stem,
        [(k, p, f == "D") for k, p, f in zip("ABCD", parts, flags)],
        [],
    )


def table_rows(data):
    """Đọc các ô của bảng đầu tiên trong một file DOCX."""
    doc = Doc(data)
    table = next(doc.root.iter(W + "tbl"), None)
    if table is None:
        raise ValueError("Không thấy bảng trong file Word")
    if len(table.findall(W + "tr")) > 1001:
        raise ValueError("Danh sách tối đa 1.000 học sinh")
    return [
        [
            "\n".join(doc.text(p).rstrip() for p in tc.findall(W + "p")).strip()
            for tc in tr.findall(W + "tc")
        ]
        for tr in table.findall(W + "tr")
    ]


def paragraphs_docx(blocks):
    """Tạo DOCX từ danh sách đoạn. Mỗi phần tử là chuỗi hoặc {text, align, bold, size}."""
    ET.register_namespace("w", W[1:-1])
    q = lambda name: W + name
    document = ET.Element(q("document"))
    body = ET.SubElement(document, q("body"))
    for block in blocks:
        item = (
            {"text": block, "align": "left", "bold": False, "size": 24}
            if isinstance(block, str)
            else {
                "text": block.get("text", ""),
                "align": block.get("align", "left"),
                "bold": bool(block.get("bold")),
                "size": int(block.get("size") or 24),
            }
        )
        para = ET.SubElement(body, q("p"))
        props = ET.SubElement(para, q("pPr"))
        ET.SubElement(props, q("jc"), {q("val"): item["align"]})
        ET.SubElement(props, q("spacing"), {q("after"): "160"})
        run = ET.SubElement(para, q("r"))
        rpr = ET.SubElement(run, q("rPr"))
        ET.SubElement(rpr, q("sz"), {q("val"): str(item["size"])})
        ET.SubElement(rpr, q("szCs"), {q("val"): str(item["size"])})
        if item["bold"]:
            ET.SubElement(rpr, q("b"))
        ET.SubElement(
            run, q("t"), {"{http://www.w3.org/XML/1998/namespace}space": "preserve"}
        ).text = str(item["text"])
    ET.SubElement(body, q("sectPr"))
    return pack_docx(document)


def pack_docx(document):
    content_types = b"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/></Types>"""
    package_rels = b"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/></Relationships>"""
    doc_rels = b"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"/>"""
    out = BytesIO()
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", content_types)
        z.writestr("_rels/.rels", package_rels)
        z.writestr("word/_rels/document.xml.rels", doc_rels)
        z.writestr(
            "word/document.xml",
            ET.tostring(document, encoding="utf-8", xml_declaration=True),
        )
    return out.getvalue()


def table_docx(headers, sample):
    """Tạo DOCX đơn giản có một bảng tiêu đề và một dòng mẫu."""
    ET.register_namespace("w", W[1:-1])
    q = lambda name: W + name
    document = ET.Element(q("document"))
    body = ET.SubElement(document, q("body"))
    table = ET.SubElement(body, q("tbl"))
    props = ET.SubElement(table, q("tblPr"))
    borders = ET.SubElement(props, q("tblBorders"))
    for edge in ("top", "left", "bottom", "right", "insideH", "insideV"):
        ET.SubElement(
            borders, q(edge), {q("val"): "single", q("sz"): "4", q("color"): "B7C1D1"}
        )
    grid = ET.SubElement(table, q("tblGrid"))
    for _ in headers:
        ET.SubElement(grid, q("gridCol"), {q("w"): "2200"})
    for values in (headers, sample):
        tr = ET.SubElement(table, q("tr"))
        for value in values:
            tc = ET.SubElement(tr, q("tc"))
            para = ET.SubElement(tc, q("p"))
            run = ET.SubElement(para, q("r"))
            ET.SubElement(
                run, q("t"), {"{http://www.w3.org/XML/1998/namespace}space": "preserve"}
            ).text = str(value)
    ET.SubElement(body, q("sectPr"))
    return pack_docx(document)
