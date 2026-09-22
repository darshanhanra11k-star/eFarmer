from decimal import Decimal

from app.capacity.engine import CapacityEngine, CapacityStatus


def test_capacity_engine_zero_total_capacity() -> None:
    engine = CapacityEngine()
    result = engine.calculate(
        total_capacity_kg=Decimal("0"),
        allocated_quantity_kg=Decimal("0"),
        active=True,
    )
    assert result.available_capacity_kg == Decimal("0")
    assert result.utilisation == Decimal("0")
    assert result.capacity_status == CapacityStatus.FULL


def test_capacity_engine_zero_allocation_available() -> None:
    engine = CapacityEngine()
    result = engine.calculate(
        total_capacity_kg=Decimal("1000"),
        allocated_quantity_kg=Decimal("0"),
        active=True,
    )
    assert result.available_capacity_kg == Decimal("1000")
    assert result.utilisation == Decimal("0")
    assert result.capacity_status == CapacityStatus.AVAILABLE


def test_capacity_engine_partial_allocation() -> None:
    engine = CapacityEngine()
    result = engine.calculate(
        total_capacity_kg=Decimal("1000"),
        allocated_quantity_kg=Decimal("350.50"),
        active=True,
    )
    assert result.available_capacity_kg == Decimal("649.50")
    assert result.utilisation == Decimal("0.3505")
    assert result.capacity_status == CapacityStatus.PARTIAL


def test_capacity_engine_full_allocation() -> None:
    engine = CapacityEngine()
    result = engine.calculate(
        total_capacity_kg=Decimal("500"),
        allocated_quantity_kg=Decimal("500"),
        active=True,
    )
    assert result.available_capacity_kg == Decimal("0")
    assert result.utilisation == Decimal("1")
    assert result.capacity_status == CapacityStatus.FULL


def test_capacity_engine_inactive_record() -> None:
    engine = CapacityEngine()
    result = engine.calculate(
        total_capacity_kg=Decimal("1000"),
        allocated_quantity_kg=Decimal("200"),
        active=False,
    )
    assert result.available_capacity_kg == Decimal("800")
    assert result.utilisation == Decimal("0.2")
    assert result.capacity_status == CapacityStatus.INACTIVE


def test_capacity_engine_never_negative_available() -> None:
    engine = CapacityEngine()
    result = engine.calculate(
        total_capacity_kg=Decimal("100"),
        allocated_quantity_kg=Decimal("150"),
        active=True,
    )
    assert result.available_capacity_kg == Decimal("0")
    assert result.capacity_status == CapacityStatus.FULL


def test_capacity_engine_exact_decimal_arithmetic() -> None:
    engine = CapacityEngine()
    result = engine.calculate(
        total_capacity_kg=Decimal("1234.5678"),
        allocated_quantity_kg=Decimal("500.1000"),
        active=True,
    )
    assert result.available_capacity_kg == Decimal("734.4678")
    assert result.capacity_status == CapacityStatus.PARTIAL
