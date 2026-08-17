import pytest
from pydantic import ValidationError

from app.crud.registry import TaliHeaderInput


@pytest.mark.parametrize("value", ["واردات", "صادرات", "حمل یکسره", None])
def test_tally_header_accepts_supported_customs_procedures(value):
    item = TaliHeaderInput(
        customs_procedure=value,
        tracking_number="۱۲۳-ABC",
    )

    assert item.customs_procedure == value
    assert item.tracking_number == "۱۲۳-ABC"


def test_tally_header_rejects_unknown_customs_procedure():
    with pytest.raises(ValidationError):
        TaliHeaderInput(customs_procedure="ترانزیت خارجی")
