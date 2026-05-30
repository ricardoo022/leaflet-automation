from leaflet_automation.core.models import Leaflet, LeafletPage
from leaflet_automation.retailers.lidl.api import parse_iso_date


def parse_leaflet(payload: dict) -> Leaflet:
    flyer = payload["flyer"]
    pages = [
        LeafletPage(
            leaflet_id=flyer["id"],
            page_number=page.get("number", 0),
            image_url=page.get("image"),
            zoom_url=page.get("zoom"),
            thumbnail_url=page.get("thumbnail"),
            alt_text=page.get("altText"),
            keywords=page.get("keyWords"),
        )
        for page in flyer.get("pages", [])
    ]

    return Leaflet(
        id=flyer["id"],
        retailer="lidl",
        name=flyer.get("name", ""),
        title=flyer.get("title", ""),
        category=flyer.get("category"),
        subcategory=flyer.get("subcategory"),
        status=flyer.get("status"),
        start_date=parse_iso_date(flyer.get("startDate")),
        end_date=parse_iso_date(flyer.get("endDate")),
        offer_start_date=parse_iso_date(flyer.get("offerStartDate")),
        offer_end_date=parse_iso_date(flyer.get("offerEndDate")),
        url=flyer.get("flyerUrlAbsolute", ""),
        pdf_url=flyer.get("pdfUrl"),
        high_res_pdf_url=flyer.get("hiResPdfUrl"),
        thumbnail_url=flyer.get("thumbnailUrl"),
        pages=pages,
    )
