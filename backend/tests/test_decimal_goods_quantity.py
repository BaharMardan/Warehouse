from decimal import Decimal
import pytest
from pydantic import ValidationError
from app.crud.registry import TaliDetailInput, GhabzDetailInput
from app.services.ghabz_allotment import GhabzLineInput


@pytest.mark.parametrize('model,parent',[(TaliDetailInput,{'id_headers_tali':1}),(GhabzDetailInput,{'id_ghabz_anbar_headar':1})])
def test_goods_quantity_accepts_decimals(model,parent):
    row=model(**parent,number_kala='12.5')
    assert Decimal(str(row.number_kala))==Decimal('12.5')
    assert model(**parent,number_kala=2).number_kala==2


@pytest.mark.parametrize('value',[-1,'NaN','Infinity'])
@pytest.mark.parametrize('model,parent',[(TaliDetailInput,{'id_headers_tali':1}),(GhabzDetailInput,{'id_ghabz_anbar_headar':1})])
def test_invalid_quantities_are_rejected(model,parent,value):
    with pytest.raises(ValidationError): model(**parent,number_kala=value)


def test_receipt_draw_already_keeps_decimal_quantity():
    assert GhabzLineInput(hscode='A',number_kala=12.5).number_kala==12.5


def test_pallet_count_remains_integer():
    with pytest.raises(ValidationError): TaliDetailInput(id_headers_tali=1,number_pallet=1.5)
