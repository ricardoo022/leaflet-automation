from leaflet_automation.retailers.lidl.keywords import CATEGORY_KEYWORDS


class ProductClassifier:
    def classify(self, text: str) -> str | None:
        normalized = text.lower()
        for category, keywords in CATEGORY_KEYWORDS.items():
            if any(keyword in normalized for keyword in keywords):
                return category
        return None
