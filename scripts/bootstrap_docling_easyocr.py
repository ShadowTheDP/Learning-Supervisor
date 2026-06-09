"""Bootstrap local Docling artifacts with EasyOCR, without RapidOCR downloads.

This script downloads:
1. Docling core/model artifacts from Hugging Face.
2. EasyOCR detector/recognition weights from EasyOCR's official GitHub releases.

It intentionally avoids Docling's generic `download_models()` path because that can
pull RapidOCR and trigger downloads from modelscope.cn, which is failing in this
environment due to certificate verification.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import shutil
import ssl
import sys
import tempfile
import zipfile
from pathlib import Path
from typing import Iterable

import httpx
import requests
from huggingface_hub import set_client_factory, snapshot_download
from requests import exceptions as requests_exceptions


DEFAULT_REPOS = (
    "docling-project/docling-layout-heron",
    "docling-project/docling-models",
    "docling-project/DocumentFigureClassifier-v2.5",
    "docling-project/CodeFormulaV2",
)

EASYOCR_MODELS = {
    "craft_mlt_25k.pth": {
        "url": "https://github.com/JaidedAI/EasyOCR/releases/download/pre-v1.1.6/craft_mlt_25k.zip",
        "md5": "2f8227d2def4037cdb3b34389dcf9ec1",
    },
    "english_g2.pth": {
        "url": "https://github.com/JaidedAI/EasyOCR/releases/download/v1.3/english_g2.zip",
        "md5": "5864788e1821be9e454ec108d61b887d",
    },
    "latin_g2.pth": {
        "url": "https://github.com/JaidedAI/EasyOCR/releases/download/v1.3/latin_g2.zip",
        "md5": "469869130aad1a34e8f9086f4262bc59",
    },
    "zh_sim_g2.pth": {
        "url": "https://github.com/JaidedAI/EasyOCR/releases/download/v1.3/zh_sim_g2.zip",
        "md5": "b601ce7143293387d3ec4f41a66edc07",
    },
}

LATIN_FAMILY = {
    "af",
    "az",
    "bs",
    "cs",
    "cy",
    "da",
    "de",
    "es",
    "et",
    "fr",
    "ga",
    "hr",
    "hu",
    "id",
    "is",
    "it",
    "ku",
    "la",
    "lt",
    "lv",
    "mi",
    "ms",
    "mt",
    "nl",
    "no",
    "oc",
    "pi",
    "pl",
    "pt",
    "ro",
    "rs_latin",
    "sk",
    "sl",
    "sq",
    "sv",
    "sw",
    "tl",
    "tr",
    "uz",
    "vi",
}

SIMPLIFIED_CHINESE = {
    "ch_sim",
    "zh",
    "zh-cn",
    "zh_cn",
    "zh-hans",
    "zh_hans",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Bootstrap Docling local artifacts using the EasyOCR route."
    )
    parser.add_argument(
        "--output-dir",
        default="data/state/docling_artifacts",
        help="Base directory for downloaded artifacts.",
    )
    parser.add_argument(
        "--repo",
        action="append",
        dest="repos",
        help="Override or extend Hugging Face repos to prefetch. Repeatable.",
    )
    parser.add_argument(
        "--languages",
        default="en",
        help="Comma-separated EasyOCR language codes to prefetch. Default: en",
    )
    parser.add_argument(
        "--skip-hf",
        action="store_true",
        help="Skip Hugging Face Docling artifact downloads.",
    )
    parser.add_argument(
        "--skip-easyocr",
        action="store_true",
        help="Skip EasyOCR model downloads.",
    )
    parser.add_argument(
        "--allow-insecure-fallback",
        action="store_true",
        help="Retry once with SSL verification disabled when certificate validation fails.",
    )
    parser.add_argument(
        "--timeout-seconds",
        type=float,
        default=120.0,
        help="Per-request timeout for HTTP downloads.",
    )
    return parser.parse_args()


def md5_of_file(path: Path) -> str:
    digest = hashlib.md5()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def is_ssl_error(exc: BaseException) -> bool:
    current: BaseException | None = exc
    while current is not None:
        if isinstance(current, (ssl.SSLError, requests_exceptions.SSLError, httpx.ConnectError)):
            return True
        current = current.__cause__ or current.__context__
    return False


def repo_local_dir(base_dir: Path, repo_id: str) -> Path:
    return base_dir / repo_id.replace("/", "--")


def download_hf_repo(
    repo_id: str,
    base_dir: Path,
    *,
    allow_insecure_fallback: bool,
    timeout_seconds: float,
) -> None:
    target_dir = repo_local_dir(base_dir, repo_id)
    target_dir.parent.mkdir(parents=True, exist_ok=True)

    def run_snapshot(verify: bool) -> None:
        set_client_factory(
            lambda: httpx.Client(
                verify=verify,
                follow_redirects=True,
                timeout=timeout_seconds,
            )
        )
        snapshot_download(
            repo_id=repo_id,
            repo_type="model",
            local_dir=target_dir,
            local_dir_use_symlinks=False,
        )

    try:
        print(f"[hf] Syncing {repo_id} -> {target_dir}")
        run_snapshot(True)
    except Exception as exc:
        if not allow_insecure_fallback or not is_ssl_error(exc):
            raise
        print(f"[hf] SSL verification failed for {repo_id}. Retrying with verify=False...")
        run_snapshot(False)


def requested_easyocr_files(languages: Iterable[str]) -> list[str]:
    requested = {"craft_mlt_25k.pth", "english_g2.pth"}
    normalized = {lang.strip().lower() for lang in languages if lang.strip()}

    if normalized & LATIN_FAMILY:
        requested.add("latin_g2.pth")
    if normalized & SIMPLIFIED_CHINESE:
        requested.add("zh_sim_g2.pth")

    return sorted(requested)


def download_binary(
    url: str,
    *,
    timeout_seconds: float,
    allow_insecure_fallback: bool,
) -> bytes:
    def run(verify: bool) -> bytes:
        with requests.get(url, timeout=timeout_seconds, stream=True, verify=verify) as response:
            response.raise_for_status()
            buffer = io.BytesIO()
            for chunk in response.iter_content(chunk_size=1024 * 1024):
                if chunk:
                    buffer.write(chunk)
            return buffer.getvalue()

    try:
        return run(True)
    except Exception as exc:
        if not allow_insecure_fallback or not is_ssl_error(exc):
            raise
        print(f"[easyocr] SSL verification failed for {url}. Retrying with verify=False...")
        return run(False)


def ensure_easyocr_model(
    output_dir: Path,
    filename: str,
    *,
    timeout_seconds: float,
    allow_insecure_fallback: bool,
) -> None:
    spec = EASYOCR_MODELS[filename]
    output_dir.mkdir(parents=True, exist_ok=True)
    final_path = output_dir / filename

    if final_path.exists() and md5_of_file(final_path) == spec["md5"]:
        print(f"[easyocr] Reusing {final_path}")
        return

    print(f"[easyocr] Downloading {filename}")
    payload = download_binary(
        spec["url"],
        timeout_seconds=timeout_seconds,
        allow_insecure_fallback=allow_insecure_fallback,
    )

    with tempfile.TemporaryDirectory() as temp_dir_name:
        temp_dir = Path(temp_dir_name)
        archive_path = temp_dir / f"{filename}.zip"
        archive_path.write_bytes(payload)

        with zipfile.ZipFile(archive_path) as archive:
            archive.extractall(temp_dir)

        extracted = temp_dir / filename
        if not extracted.exists():
            raise FileNotFoundError(
                f"Expected {filename} inside archive from {spec['url']}, but it was not found."
            )

        shutil.copy2(extracted, final_path)

    actual_md5 = md5_of_file(final_path)
    if actual_md5 != spec["md5"]:
        final_path.unlink(missing_ok=True)
        raise ValueError(
            f"MD5 mismatch for {filename}: expected {spec['md5']}, got {actual_md5}"
        )


def main() -> int:
    args = parse_args()
    output_dir = Path(args.output_dir).resolve()
    easyocr_dir = output_dir / "EasyOcr"
    repos = tuple(args.repos) if args.repos else DEFAULT_REPOS
    languages = [part.strip() for part in args.languages.split(",") if part.strip()]

    if not args.skip_hf:
        for repo_id in repos:
            download_hf_repo(
                repo_id,
                output_dir,
                allow_insecure_fallback=args.allow_insecure_fallback,
                timeout_seconds=args.timeout_seconds,
            )

    if not args.skip_easyocr:
        for filename in requested_easyocr_files(languages):
            ensure_easyocr_model(
                easyocr_dir,
                filename,
                timeout_seconds=args.timeout_seconds,
                allow_insecure_fallback=args.allow_insecure_fallback,
            )

    print("")
    print("Bootstrap complete.")
    print(f"Artifacts path: {output_dir}")
    print(f"EasyOCR path:  {easyocr_dir}")
    print("Recommended runtime languages:", ",".join(languages) or "en")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
