import unicodedata

from leaflet_automation.retailers.lidl.keywords import CATEGORY_KEYWORDS


def normalize_text(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", text.lower())
    return "".join(char for char in normalized if not unicodedata.combining(char))


class ProductClassifier:
    def classify(self, text: str) -> str | None:
        normalized = normalize_text(text)
        for category, keywords in CATEGORY_KEYWORDS.items():
            if any(normalize_text(keyword) in normalized for keyword in keywords):
                return category
        return None
