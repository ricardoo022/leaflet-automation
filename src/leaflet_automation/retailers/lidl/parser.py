import re

from leaflet_automation.core.models import Leaflet, LeafletPage
from leaflet_automation.retailers.lidl.api import parse_iso_date

ALT_TEXT_MARKERS = (
    "com descontos em",
    "com destaque para",
    "destacando",
    "incluindo",
    "como",
)
TRAILING_NAME_STOP_WORDS = {
    "disponivel",
    "disponível",
    "familiar",
    "kg",
    "loja",
    "lidl",
    "nacional",
    "pack",
    "plus",
    "preco",
    "preço",
    "produtos",
    "promocao",
    "promoção",
    "stock",
    "vendido",
    "xxl",
}
KEYWORD_NOISE_WORDS = {
    "acumulaveis",
    "acumuláveis",
    "aderecos",
    "adereços",
    "adquirir",
    "artigos",
    "comparado",
    "disponiveis",
    "disponíveis",
    "erro",
    "face",
    "feira",
    "fotos",
    "limitado",
    "lidl",
    "loja",
    "lojas",
    "normal",
    "plus",
    "poderao",
    "poderão",
    "poupanca",
    "poupança",
    "preco",
    "precos",
    "preço",
    "preços",
    "produto",
    "produtos",
    "promocao",
    "promoção",
    "reserva",
    "salvo",
    "stock",
    "sugestao",
    "sugestão",
    "validos",
    "válidos",
    "vendido",
}


def _normalize_spaces(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _clean_product_name(text: str) -> str:
    cleaned = _normalize_spaces(text.strip(" ,.;:-"))
    cleaned = re.sub(
        r"^(?:descontos? em|ofertas? de|produtos? como|destacando|incluindo|com destaque para)\s+",
        "",
        cleaned,
        flags=re.IGNORECASE,
    )
    tokens = cleaned.split()
    while tokens and tokens[-1].lower() in TRAILING_NAME_STOP_WORDS:
        tokens.pop()
    return " ".join(tokens).strip(" ,.;:-")


def _unique_names(names: list[str]) -> list[str]:
    seen: set[str] = set()
    unique: list[str] = []
    for name in names:
        normalized = name.casefold()
        if not name or normalized in seen:
            continue
        seen.add(normalized)
        unique.append(name)
    return unique


def extract_product_names_from_alt_text(text: str | None) -> list[str]:
    if not text:
        return []

    snippet = text
    normalized = text.casefold()
    for marker in ALT_TEXT_MARKERS:
        marker_index = normalized.find(marker)
        if marker_index >= 0:
            snippet = text[marker_index + len(marker) :]
            break

    parts = re.split(r",|\se\s", snippet)
    return _unique_names([_clean_product_name(part) for part in parts if _clean_product_name(part)])


def extract_product_names_from_keywords(text: str | None) -> list[str]:
    if not text:
        return []

    names: list[str] = []
    for match in re.finditer(r"N[ºo][0-9A-Za-z-]+", text):
        window = text[max(0, match.start() - 80) : match.start()]
        tokens = [token.strip(" ,.;:-") for token in window.split()]
        filtered = [
            token
            for token in tokens
            if token
            and not any(character.isdigit() for character in token)
            and token.casefold() not in KEYWORD_NOISE_WORDS
            and not token.startswith("-")
        ]
        if not filtered:
            continue
        candidate = _clean_product_name(" ".join(filtered[-4:]))
        if candidate:
            names.append(candidate)

    return _unique_names(names)


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
