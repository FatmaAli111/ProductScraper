"""Product variant value object."""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


@dataclass(slots=True)
class ProductVariant:
    """A purchasable product variant: an SKU tied to an option combination."""

    sku: str
    color: str = ""
    size: str = ""
    price: Decimal | None = None
    sale_price: Decimal | None = None
    quantity: int = 0
    available: bool = True

    @property
    def display_price(self) -> Decimal | None:
        """Effective price: sale price wins over the base price."""
        if self.sale_price is not None:
            return self.sale_price
        return self.price

    def as_dict(self) -> dict[str, object]:
        """JSON-serializable representation."""
        return {
            "sku": self.sku,
            "color": self.color,
            "size": self.size,
            "price": None if self.price is None else str(self.price),
            "sale_price": None if self.sale_price is None else str(self.sale_price),
            "quantity": self.quantity,
            "available": self.available,
        }

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> ProductVariant:
        """Rebuild a variant from its :meth:`as_dict` representation."""
        return cls(
            sku=str(data.get("sku", "")),
            color=str(data.get("color", "")),
            size=str(data.get("size", "")),
            price=_to_decimal(data.get("price")),
            sale_price=_to_decimal(data.get("sale_price")),
            quantity=int(data.get("quantity", 0)),
            available=bool(data.get("available", True)),
        )


def _to_decimal(value: object) -> Decimal | None:
    if value is None:
        return None
    return Decimal(str(value))
