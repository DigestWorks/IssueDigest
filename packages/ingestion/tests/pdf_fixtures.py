"""Small real PDFs built without a second PDF dependency."""

from hashlib import sha256
from pathlib import Path


def synthetic_pdf(pages: list[str]) -> bytes:
    # Every character is a two-byte CID, mapped to its exact UTF-16BE sequence.
    chars = dict.fromkeys("".join(pages))
    codes = {char: index for index, char in enumerate(chars, 1)}
    mappings = "\n".join(
        f"<{code:04X}> <{char.encode('utf-16-be').hex().upper()}>" for char, code in codes.items()
    )
    cmap = (
        "/CIDInit /ProcSet findresource begin\n12 dict begin\nbegincmap\n"
        "/CIDSystemInfo << /Registry (Adobe) /Ordering (UCS) /Supplement 0 >> def\n"
        "/CMapName /Synthetic def\n/CMapType 2 def\n"
        "1 begincodespacerange\n<0000> <FFFF>\nendcodespacerange\n"
        f"{len(codes)} beginbfchar\n{mappings}\nendbfchar\n"
        "endcmap\nCMapName currentdict /CMap defineresource pop\nend\nend"
    ).encode("ascii")

    def stream(data: bytes) -> bytes:
        return f"<< /Length {len(data)} >>\nstream\n".encode() + data + b"\nendstream"

    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        (
            "<< /Type /Pages /Count "
            + str(len(pages))
            + " /Kids ["
            + " ".join(f"{7 + index * 2} 0 R" for index in range(len(pages)))
            + "] >>"
        ).encode(),
        b"<< /Type /Font /Subtype /Type0 /BaseFont /Synthetic /Encoding /Identity-H "
        b"/DescendantFonts [4 0 R] /ToUnicode 6 0 R >>",
        b"<< /Type /Font /Subtype /CIDFontType2 /BaseFont /Synthetic "
        b"/CIDSystemInfo << /Registry (Adobe) /Ordering (Identity) /Supplement 0 >> "
        b"/FontDescriptor 5 0 R /DW 1000 >>",
        b"<< /Type /FontDescriptor /FontName /Synthetic /Flags 4 /FontBBox [0 0 1000 1000] "
        b"/ItalicAngle 0 /Ascent 1000 /Descent 0 /CapHeight 1000 /StemV 80 >>",
        stream(cmap),
    ]
    for index, text in enumerate(pages):
        content = (
            "BT /F1 12 Tf 20 100 Td <" + "".join(f"{codes[char]:04X}" for char in text) + "> Tj ET"
        ).encode()
        objects += [
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 600 800] "
            f"/Resources << /Font << /F1 3 0 R >> >> /Contents {8 + index * 2} 0 R >>".encode(),
            stream(content),
        ]
    data = b"%PDF-1.7\n"
    offsets = [0]
    for index, obj in enumerate(objects, 1):
        offsets.append(len(data))
        data += f"{index} 0 obj\n".encode() + obj + b"\nendobj\n"
    xref = len(data)
    data += f"xref\n0 {len(offsets)}\n0000000000 65535 f \n".encode()
    data += b"".join(f"{offset:010} 00000 n \n".encode() for offset in offsets[1:])
    data += (
        f"trailer\n<< /Size {len(offsets)} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n"
    ).encode()
    return data


def source(tmp_path: Path, pages: list[str]) -> tuple[Path, Path, str]:
    root = tmp_path / "source"
    (root / "pdfs").mkdir(parents=True)
    file = root / "pdfs" / "PRIVATE.pdf"
    data = synthetic_pdf(pages)
    file.write_bytes(data)
    return root, file, sha256(data).hexdigest()
