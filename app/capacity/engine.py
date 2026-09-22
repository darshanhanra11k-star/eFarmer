from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum


class CapacityStatus(StrEnum):
    INACTIVE = "INACTIVE"
    AVAILABLE = "AVAILABLE"
    PARTIAL = "PARTIAL"
    FULL = "FULL"


@dataclass(frozen=True)
class CapacityOutput:
    available_capacity_kg: Decimal
    utilisation: Decimal
    capacity_status: CapacityStatus


class CapacityEngine:
    def calculate(
        self,
        total_capacity_kg: Decimal,
        allocated_quantity_kg: Decimal,
        active: bool,
    ) -> CapacityOutput:
        if not active:
            available = max(Decimal("0"), total_capacity_kg - allocated_quantity_kg)
            utilisation = (
                (allocated_quantity_kg / total_capacity_kg)
                if total_capacity_kg > Decimal("0")
                else Decimal("0")
            )
            return CapacityOutput(
                available_capacity_kg=available,
                utilisation=utilisation,
                capacity_status=CapacityStatus.INACTIVE,
            )

        if total_capacity_kg == Decimal("0"):
            return CapacityOutput(
                available_capacity_kg=Decimal("0"),
                utilisation=Decimal("0"),
                capacity_status=CapacityStatus.FULL,
            )

        available = max(Decimal("0"), total_capacity_kg - allocated_quantity_kg)
        utilisation = allocated_quantity_kg / total_capacity_kg

        if available == Decimal("0"):
            status = CapacityStatus.FULL
        elif allocated_quantity_kg == Decimal("0"):
            status = CapacityStatus.AVAILABLE
        else:
            status = CapacityStatus.PARTIAL

        return CapacityOutput(
            available_capacity_kg=available,
            utilisation=utilisation,
            capacity_status=status,
        )
