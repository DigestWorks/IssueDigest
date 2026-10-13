"""Private script entrypoint: apply process limits before importing a PDF parser."""

import hashlib
import json
import logging
import os
import resource
import sys
import warnings


def main() -> int:
    input_fd, output_fd, max_pages, max_text, cpu, address_space, max_output = map(
        int, sys.argv[1:]
    )
    resource.setrlimit(resource.RLIMIT_CPU, (cpu, cpu))
    resource.setrlimit(resource.RLIMIT_AS, (address_space, address_space))
    resource.setrlimit(resource.RLIMIT_FSIZE, (max_output, max_output))
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    logging.disable(logging.CRITICAL)
    warnings.simplefilter("ignore")
    # This script is launched by filename, avoiding the package __init__ imports.
    from pypdf import PdfReader, __version__

    class EncryptedPdf(Exception):
        pass

    class UnencryptedReader(PdfReader):
        def _handle_encryption(self, password: str | bytes | None) -> None:
            # The pinned reader normally tries an empty password in __init__.
            raise EncryptedPdf

    result: dict[str, object]
    try:
        with os.fdopen(input_fd, "rb") as stream:
            reader = UnencryptedReader(stream, strict=True)
            if reader.is_encrypted:
                result = {"status": "failed", "error": "pdf_encrypted"}
            elif len(reader.pages) > max_pages:
                result = {"status": "failed", "error": "pdf_page_limit_exceeded"}
            else:
                texts: list[str] = []
                pages: list[dict[str, int]] = []
                empty: list[int] = []
                offset = 0
                for number, page in enumerate(reader.pages, 1):
                    if number > 1:
                        offset += 3
                    text = page.extract_text(extraction_mode="plain")
                    text.encode("utf-8")
                    end = offset + len(text)
                    if end > max_text:
                        result = {"status": "failed", "error": "pdf_text_limit_exceeded"}
                        break
                    if text.strip():
                        pages.append({"page_number": number, "start": offset, "end": end})
                    else:
                        empty.append(number)
                    texts.append(text)
                    offset = end
                else:
                    if not pages:
                        result = {"status": "failed", "error": "no_extractable_text"}
                    else:
                        combined = "\n\f\n".join(texts)
                        result = {
                            "status": "completed",
                            "text": combined,
                            "page_texts": texts,
                            "pages": pages,
                            "empty_pages": empty,
                            "page_count": len(texts),
                            "text_sha256": hashlib.sha256(combined.encode("utf-8")).hexdigest(),
                            "parser_name": "pypdf",
                            "parser_version": __version__,
                            "normalization_profile": "pypdf-plain-v1",
                        }
    except EncryptedPdf:
        result = {"status": "failed", "error": "pdf_encrypted"}
    except UnicodeError:
        result = {"status": "failed", "error": "pdf_invalid_unicode"}
    except Exception:
        result = {"status": "failed", "error": "pdf_parse_failed"}
    payload = json.dumps(result, ensure_ascii=True, separators=(",", ":")).encode("ascii")
    if len(payload) > max_output:
        return 3
    with os.fdopen(output_fd, "wb") as output:
        output.write(payload)
        output.flush()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
