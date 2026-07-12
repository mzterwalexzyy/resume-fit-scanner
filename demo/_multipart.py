"""
Minimal multipart/form-data parser shared by the demo tools (`cgi` module,
which used to do this, was removed in Python 3.13+).
"""


def parse_multipart(body: bytes, content_type: str):
    """Returns (text_fields: dict, files: dict[name -> (filename, bytes)])."""
    fields = {}
    files = {}
    if "boundary=" not in content_type:
        return fields, files
    boundary = content_type.split("boundary=", 1)[1].strip().strip('"').encode("ascii")

    for part in body.split(b"--" + boundary):
        part = part.strip(b"\r\n")
        if not part or part == b"--":
            continue
        header_blob, sep, content = part.partition(b"\r\n\r\n")
        if not sep:
            continue
        headers = header_blob.decode("utf-8", errors="replace")
        # Content-Disposition is one line among possibly several headers
        # (e.g. a following Content-Type: line for file parts) -- splitting
        # the whole blob on ";" would bleed those other lines into the
        # filename value, so isolate that one line first.
        disposition_line = next(
            (line for line in headers.split("\r\n") if line.lower().startswith("content-disposition:")),
            "",
        )
        name = None
        filename = None
        for piece in disposition_line.split(";"):
            piece = piece.strip()
            if piece.startswith("name="):
                name = piece.split("=", 1)[1].strip('"')
            elif piece.startswith("filename="):
                filename = piece.split("=", 1)[1].strip('"')
        if name is None:
            continue
        content = content[:-2] if content.endswith(b"\r\n") else content
        if filename is not None:
            files[name] = (filename, content)
        else:
            fields[name] = content.decode("utf-8", errors="replace")
    return fields, files
