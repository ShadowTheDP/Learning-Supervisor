"""Run a local Docling conversion using EasyOCR and prefetched artifacts."""

from __future__ import annotations

import argparse
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Verify local Docling + EasyOCR conversion on a PDF."
    )
    parser.add_argument("source", help="Path to the source PDF file.")
    parser.add_argument(
        "--artifacts-dir",
        default="data/state/docling_artifacts",
        help="Directory containing Docling and EasyOCR artifacts.",
    )
    parser.add_argument(
        "--output-md",
        help="Optional path for the generated Markdown output.",
    )
    parser.add_argument(
        "--languages",
        default="en",
        help="Comma-separated EasyOCR language codes. Default: en",
    )
    parser.add_argument(
        "--gpu",
        action="store_true",
        help="Enable GPU for EasyOCR. CPU is the default for safer local verification.",
    )
    parser.add_argument(
        "--disable-ocr",
        action="store_true",
        help="Skip OCR entirely for born-digital PDFs that already contain selectable text.",
    )
    parser.add_argument(
        "--force-full-page-ocr",
        action="store_true",
        help="Force OCR on the entire page instead of only bitmap regions.",
    )
    parser.add_argument(
        "--enable-formula-enrichment",
        action="store_true",
        help="Enable Docling formula enrichment. Disabled by default for a lighter local smoke test.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    try:
        from docling.datamodel.base_models import InputFormat
        from docling.datamodel.pipeline_options import EasyOcrOptions, PdfPipelineOptions
        from docling.document_converter import DocumentConverter, PdfFormatOption
    except ImportError as exc:
        raise SystemExit(
            "Docling is not available in the current environment. "
            "Install project dependencies first."
        ) from exc

    source = Path(args.source).resolve()
    artifacts_dir = Path(args.artifacts_dir).resolve()
    easyocr_dir = artifacts_dir / "EasyOcr"
    output_md = Path(args.output_md).resolve() if args.output_md else source.with_suffix(".docling.md")
    languages = [part.strip() for part in args.languages.split(",") if part.strip()]

    pipeline_options = PdfPipelineOptions(
        artifacts_path=str(artifacts_dir),
        do_ocr=not args.disable_ocr,
        do_table_structure=True,
        do_formula_enrichment=args.enable_formula_enrichment,
    )

    if not args.disable_ocr:
        pipeline_options.ocr_options = EasyOcrOptions(
            lang=languages,
            model_storage_directory=str(easyocr_dir),
            download_enabled=False,
            use_gpu=args.gpu,
            force_full_page_ocr=args.force_full_page_ocr,
        )

    converter = DocumentConverter(
        format_options={
            InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options),
        }
    )

    result = converter.convert(str(source))
    markdown = result.document.export_to_markdown()
    output_md.write_text(markdown, encoding="utf-8")

    print(f"Converted: {source}")
    print(f"Markdown:  {output_md}")
    print(f"Artifacts: {artifacts_dir}")
    print(f"EasyOCR:   {easyocr_dir}")
    print(f"Languages: {', '.join(languages) if languages else 'en'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
