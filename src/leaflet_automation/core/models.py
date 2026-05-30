from datetime import date, datetime
from pathlib import Path

from pydantic import BaseModel, Field

from leaflet_automation.core.enums import ProgramType, RunStatus


class LeafletPage(BaseModel):
    leaflet_id: str
    page_number: int
    image_url: str | None = None
    zoom_url: str | None = None
    thumbnail_url: str | None = None
    local_image_path: Path | None = None
    alt_text: str | None = None
    keywords: str | None = None


class Leaflet(BaseModel):
    id: str
    retailer: str
    name: str
    title: str
    category: str | None = None
    subcategory: str | None = None
    status: str | None = None
    program_type: ProgramType = ProgramType.UNKNOWN
    start_date: date | None = None
    end_date: date | None = None
    offer_start_date: date | None = None
    offer_end_date: date | None = None
    url: str
    pdf_url: str | None = None
    high_res_pdf_url: str | None = None
    thumbnail_url: str | None = None
    pages: list[LeafletPage] = Field(default_factory=list)


class ExtractedProduct(BaseModel):
    retailer: str
    leaflet_id: str
    page_number: int
    program_type: ProgramType
    category: str
    name: str
    price_text: str | None = None
    price_value: float | None = None
    promo_start: date | None = None
    promo_end: date | None = None
    screenshot_path: Path | None = None
    raw_text: str = ""
    confidence: float | None = None


class RunRecord(BaseModel):
    id: str
    retailer: str
    status: RunStatus = RunStatus.PENDING
    started_at: datetime | None = None
    finished_at: datetime | None = None
    message: str | None = None
