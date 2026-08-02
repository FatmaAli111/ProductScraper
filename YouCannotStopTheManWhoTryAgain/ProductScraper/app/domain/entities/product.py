"""Product aggregate root."""
from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal

from app.domain.entities.variant import ProductVariant


@dataclass(slots=True)
class Product:
    """A single scraped product with all data needed for a Salla import."""

    name: str
    sku: str
    url: str
    description: str = ""
    price: Decimal | None = None
    sale_price: Decimal | None = None
    category: str = ""
    brand: str = ""
    tags: list[str] = field(default_factory=list)
    colors: list[str] = field(default_factory=list)
    sizes: list[str] = field(default_factory=list)
    availability: bool = True
    weight: str = ""
    dimensions: str = ""
    image_urls: list[str] = field(default_factory=list)
    images: list[str] = field(default_factory=list)
    variants: list[ProductVariant] = field(default_factory=list)

    @property
    def display_price(self) -> Decimal | None:
        """Effective price: sale price wins over the base price."""
        if self.sale_price is not None:
            return self.sale_price
        return self.price

    @property
    def is_available(self) -> bool:
        return self.availability

    def as_dict(self) -> dict[str, object]:
        """JSON-serializable representation."""
        return {
            "name": self.name,
            "sku": self.sku,
            "url": self.url,
            "description": self.description,
            "price": None if self.price is None else str(self.price),
            "sale_price": None if self.sale_price is None else str(self.sale_price),
            "category": self.category,
            "brand": self.brand,
            "tags": self.tags,
            "colors": self.colors,
            "sizes": self.sizes,
            "availability": self.availability,
            "weight": self.weight,
            "dimensions": self.dimensions,
            "image_urls": self.image_urls,
            "images": self.images,
            "variants": [variant.as_dict() for variant in self.variants],
        }

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> Product:
        """Rebuild a product from its :meth:`as_dict` representation."""
        return cls(
            name=str(data.get("name", "")),
            sku=str(data.get("sku", "")),
            url=str(data.get("url", "")),
            description=str(data.get("description", "")),
            price=_to_decimal(data.get("price")),
            sale_price=_to_decimal(data.get("sale_price")),
            category=str(data.get("category", "")),
            brand=str(data.get("brand", "")),
            tags=_as_string_list(data.get("tags")),
            colors=_as_string_list(data.get("colors")),
            sizes=_as_string_list(data.get("sizes")),
            availability=bool(data.get("availability", True)),
            weight=str(data.get("weight", "")),
            dimensions=str(data.get("dimensions", "")),
            image_urls=_as_string_list(data.get("image_urls")),
            images=_as_string_list(data.get("images")),
            variants=[ProductVariant.from_dict(item) for item in _as_dict_list(data.get("variants"))],
        )


def _to_decimal(value: object) -> Decimal | None:
    if value is None:
        return None
    return Decimal(str(value))


def _as_string_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value]


def _as_dict_list(value: object) -> list[dict[str, object]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]
