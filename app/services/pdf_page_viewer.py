from __future__ import annotations

from pathlib import Path

import pypdfium2 as pdfium

from ..models import LearningUnit, Resource


PDF_PAGE_CACHE_DIRNAME = "pdf_pages"
PDF_RENDER_SCALE = 2.0


def get_resource_workspace(resource: Resource) -> Path:
    return Path(resource.stored_markdown_path).expanduser().resolve().parent


def get_original_pdf_path(resource: Resource) -> Path | None:
    workspace = get_resource_workspace(resource)
    cached_pdf_path = workspace / "original.pdf"
    if cached_pdf_path.exists():
        return cached_pdf_path

    if not resource.source_path_or_url:
        return None

    source_path = Path(resource.source_path_or_url).expanduser()
    if source_path.exists() and source_path.suffix.lower() == ".pdf":
        return source_path.resolve()
    return None


def get_resource_pdf_page_count(resource: Resource) -> int | None:
    pdf_path = get_original_pdf_path(resource)
    if pdf_path is None:
        return None

    with pdfium.PdfDocument(str(pdf_path)) as document:
        return len(document)


def get_unit_pdf_page_numbers(unit: LearningUnit) -> list[int]:
    if unit.page_start is None:
        return []

    start_page = max(1, int(unit.page_start))
    end_page = start_page
    if unit.page_end is not None and unit.page_end >= start_page:
        end_page = int(unit.page_end)

    return list(range(start_page, end_page + 1))


def get_available_unit_pdf_page_numbers(unit: LearningUnit) -> list[int]:
    page_numbers = get_unit_pdf_page_numbers(unit)
    if not page_numbers:
        return []

    page_count = get_resource_pdf_page_count(unit.resource)
    if page_count is None:
        return []

    return [page_number for page_number in page_numbers if page_number <= page_count]


def get_or_render_pdf_page(resource: Resource, page_number: int) -> Path:
    if page_number < 1:
        raise FileNotFoundError("Page numbers must be positive.")

    pdf_path = get_original_pdf_path(resource)
    if pdf_path is None:
        raise FileNotFoundError("Original PDF is not available for this resource.")

    cache_dir = get_resource_workspace(resource) / PDF_PAGE_CACHE_DIRNAME
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_path = cache_dir / f"page-{page_number:04d}.png"
    if cache_path.exists():
        return cache_path

    with pdfium.PdfDocument(str(pdf_path)) as document:
        if page_number > len(document):
            raise FileNotFoundError(f"Page {page_number} is outside the PDF page range.")

        page = document.get_page(page_number - 1)
        try:
            bitmap = page.render(scale=PDF_RENDER_SCALE)
            try:
                image = bitmap.to_pil()
                image.save(cache_path, format="PNG")
            finally:
                bitmap.close()
        finally:
            page.close()

    return cache_path
