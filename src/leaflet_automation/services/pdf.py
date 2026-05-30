from pathlib import Path


class PdfService:
    def extract_pages(self, pdf_path: Path, output_dir: Path) -> list[Path]:
        raise NotImplementedError("Wire PyMuPDF or pdfplumber here during implementation.")
