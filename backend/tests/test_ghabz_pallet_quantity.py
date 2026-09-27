import pytest
from fastapi import HTTPException
from pydantic import ValidationError
from app.routers.ghabz import GhabzExtrasInput, validate_pallet_quantity


@pytest.mark.parametrize("quantity", [1, 30, 100])
@pytest.mark.parametrize("cargo", ["volumetric", "yes"])
def test_valid_partial_or_full_pallet_quantity(quantity, cargo):
    validate_pallet_quantity(quantity, "no", cargo, 100)


@pytest.mark.parametrize("master,cargo,total,quantity", [
    ("yes", "volumetric", 100, 30),
    ("no", "weight", 100, 30),
    ("no", "container", 100, 30),
    ("no", None, 100, 30),
    ("no", "volumetric", None, 30),
    ("no", "volumetric", 0, 1),
    ("no", "volumetric", 100, 101),
])
def test_invalid_receipt_or_tally_limit(master, cargo, total, quantity):
    with pytest.raises(HTTPException) as exc:
        validate_pallet_quantity(quantity, master, cargo, total)
    assert exc.value.status_code == 422


@pytest.mark.parametrize("quantity", [0, -1, 1.5, True, "30"])
def test_api_requires_a_positive_integer(quantity):
    with pytest.raises(ValidationError):
        GhabzExtrasInput(pallet_quantity=quantity)


def test_field_optional_and_can_be_cleared():
    assert "pallet_quantity" not in GhabzExtrasInput(description="test").model_dump(exclude_unset=True)
    assert GhabzExtrasInput(pallet_quantity=None).model_dump(exclude_unset=True) == {"pallet_quantity": None}
    validate_pallet_quantity(None, "yes", "weight", None)


def test_other_receipts_reserve_pallets_before_finalization():
    validate_pallet_quantity(10, "no", "volumetric", 15, allocated_other=5)
    with pytest.raises(HTTPException) as exc:
        validate_pallet_quantity(11, "no", "volumetric", 15, allocated_other=5)
    assert exc.value.status_code == 422


@pytest.mark.parametrize("allocated", [15, 20])
def test_no_pallets_available_when_other_receipts_exhaust_total(allocated):
    with pytest.raises(HTTPException):
        validate_pallet_quantity(1, "no", "volumetric", 15, allocated_other=allocated)
    validate_pallet_quantity(None, "no", "volumetric", 15, allocated_other=allocated)


def test_current_receipt_can_keep_or_reduce_its_allocation():
    validate_pallet_quantity(5, "no", "volumetric", 15, allocated_other=10)
    validate_pallet_quantity(3, "no", "volumetric", 15, allocated_other=10)
