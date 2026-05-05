"""Frontend 'sade' payload -> Turkcell provider JSON payload mappers.

Bu modül **sadece dönüştürücü**: herhangi bir IO yapmaz, DB'ye yazmaz.
Unit test'lerde saf mapper olarak kolayca doğrulanabilir.
"""

from __future__ import annotations

import uuid
from datetime import datetime, date
from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Dict, List, Optional


def _q(value: Any, places: int = 2) -> float:
    """Quantize a numeric value to `places` decimals using HALF_UP."""
    if value is None:
        return 0.0
    try:
        d = Decimal(str(value))
    except Exception:
        d = Decimal("0")
    quant = Decimal("1." + "0" * places)
    return float(d.quantize(quant, rounding=ROUND_HALF_UP))


def _as_date_str(value: Any) -> str:
    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, str) and value:
        # kabul: YYYY-MM-DD veya dd/MM/yyyy
        if "/" in value and len(value) == 10:
            d, m, y = value.split("/")
            return f"{y}-{m}-{d}"
        return value
    return date.today().isoformat()


def _default(value: Any, default: Any) -> Any:
    return value if value not in (None, "") else default


def map_efatura_create_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Map frontend sade payload -> Turkcell /v1/outboxinvoice/create JSON.

    Minimum required:
        receiver.vkn, receiver.name, invoice.issue_date, lines[*]
    """
    receiver = payload.get("receiver") or {}
    invoice = payload.get("invoice") or {}
    lines_in: List[Dict[str, Any]] = payload.get("lines") or []

    ettn = invoice.get("ettn") or str(uuid.uuid4())

    mapped_lines = []
    for line in lines_in:
        quantity = _q(line.get("quantity"), 3)
        unit_price = _q(line.get("unit_price"), 4)
        vat_rate = _q(line.get("vat_rate"), 2)
        line_ext = _q(quantity * unit_price, 2)
        vat_amount = _q(line_ext * vat_rate / 100.0, 2)

        mapped_lines.append(
            {
                "inventoryCard": line.get("name") or "Ürün",
                "amount": quantity,
                "unitCode": line.get("unit_code") or "NIU",
                "unitPrice": unit_price,
                "description": line.get("description") or line.get("name") or "Ürün",
                "vatRate": vat_rate,
                "vatAmount": vat_amount,
                "lineExtensionAmount": line_ext,
                "taxes": [
                    {
                        "taxName": "KDV",
                        "taxTypeCode": "0015",
                        "taxRate": vat_rate,
                        "taxAmount": vat_amount,
                    }
                ],
            }
        )

    mapped: Dict[str, Any] = {
        "recordType": 1,
        "status": int(_default(invoice.get("status"), 0)),
        "localReferenceId": invoice.get("local_reference_id") or str(uuid.uuid4()),
        "note": invoice.get("note") or "",
        "addressBook": {
            "name": receiver.get("name") or "",
            "identificationNumber": receiver.get("vkn") or receiver.get("tckn") or "",
            "alias": receiver.get("alias") or "",
            "receiverDistrict": receiver.get("district") or "",
            "receiverCity": receiver.get("city") or "",
            "receiverCountry": receiver.get("country") or "Türkiye",
            "receiverStreet": receiver.get("street") or "",
            "receiverZipCode": receiver.get("zip_code") or "",
            "receiverTaxOffice": receiver.get("tax_office") or "",
        },
        "generalInfoModel": {
            "ettn": ettn,
            "invoiceProfileType": int(_default(invoice.get("profile_type"), 0)),
            "type": int(_default(invoice.get("type"), 1)),
            "issueDate": _as_date_str(invoice.get("issue_date")),
            "prefix": invoice.get("prefix") or "EPA",
            "currencyCode": invoice.get("currency") or "TRY",
            "exchangeRate": float(_default(invoice.get("exchange_rate"), 1)),
        },
        "invoiceLines": mapped_lines,
    }
    return mapped


def map_eirsaliye_create_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Map frontend sade payload -> Turkcell e-İrsaliye /v1/outboxdespatch/create JSON.

    Not:
        Gerçek Turkcell e-İrsaliye JSON payload key isimleri Postman koleksiyonuna
        göre doğrulanır. Aşağıdaki yapı Turkcell e-Fatura konvansiyonu ile uyumlu,
        sevkiyat/teslim alanları e-Despatch Postman örneklerine göre düzenlenmiştir.
    """
    receiver = payload.get("receiver") or {}
    despatch = payload.get("despatch") or {}
    delivery = payload.get("delivery") or {}
    shipment = payload.get("shipment") or {}
    lines_in: List[Dict[str, Any]] = payload.get("lines") or []

    ettn = despatch.get("ettn") or str(uuid.uuid4())

    despatch_lines = []
    for line in lines_in:
        quantity = _q(line.get("quantity"), 3)
        unit_price = _q(line.get("unit_price"), 4)
        line_ext = _q(quantity * unit_price, 2)

        despatch_lines.append(
            {
                "inventoryCard": line.get("product_name") or line.get("name") or "Ürün",
                "amount": quantity,
                "unitCode": line.get("unit_code") or "C62",
                "unitPrice": unit_price,
                "description": line.get("description") or line.get("product_name") or "Ürün",
                "lineExtensionAmount": line_ext,
            }
        )

    mapped: Dict[str, Any] = {
        "recordType": 1,
        "status": int(_default(despatch.get("status"), 0)),
        "localReferenceId": despatch.get("local_reference_id") or str(uuid.uuid4()),
        "note": despatch.get("note") or "",
        "addressBook": {
            "name": receiver.get("name") or "",
            "identificationNumber": receiver.get("vkn") or receiver.get("tckn") or "",
            "alias": receiver.get("alias") or "",
            "receiverDistrict": receiver.get("district") or "",
            "receiverCity": receiver.get("city") or "",
            "receiverCountry": receiver.get("country") or "Türkiye",
            "receiverStreet": receiver.get("street") or "",
            "receiverZipCode": receiver.get("zip_code") or "",
            "receiverTaxOffice": receiver.get("tax_office") or "",
        },
        "generalInfoModel": {
            "ettn": ettn,
            "despatchProfileType": int(_default(despatch.get("profile_type"), 0)),
            "type": int(_default(despatch.get("type"), 1)),
            "issueDate": _as_date_str(despatch.get("issue_date")),
            "prefix": despatch.get("prefix") or "EIR",
            "currencyCode": despatch.get("currency") or "TRY",
            "exchangeRate": float(_default(despatch.get("exchange_rate"), 1)),
        },
        "deliveryAddressInfo": {
            "receiverStreet": delivery.get("street") or receiver.get("street") or "",
            "receiverDistrict": delivery.get("district") or receiver.get("district") or "",
            "receiverCity": delivery.get("city") or receiver.get("city") or "",
            "receiverCountry": delivery.get("country") or receiver.get("country") or "Türkiye",
            "receiverZipCode": delivery.get("zip_code") or receiver.get("zip_code") or "",
        },
        "despatchShipmentInfo": {
            "plateNumber": shipment.get("plate_number") or "",
            "driverName": shipment.get("driver_name") or "",
            "driverSurname": shipment.get("driver_surname") or "",
            "driverIdentificationNumber": shipment.get("driver_tckn") or "",
        },
        "despatchLines": despatch_lines,
    }
    return mapped


def validation_errors_for_efatura(payload: Dict[str, Any]) -> List[str]:
    errors: List[str] = []
    receiver = payload.get("receiver") or {}
    invoice = payload.get("invoice") or {}
    lines = payload.get("lines") or []

    if not (receiver.get("vkn") or receiver.get("tckn")):
        errors.append("receiver.vkn (veya tckn) zorunlu")
    if not receiver.get("name"):
        errors.append("receiver.name zorunlu")
    if not invoice.get("issue_date"):
        errors.append("invoice.issue_date zorunlu")
    if not lines:
        errors.append("lines boş olamaz (en az 1 satır)")
    for idx, line in enumerate(lines):
        if not line.get("name"):
            errors.append(f"lines[{idx}].name zorunlu")
        if line.get("quantity") in (None, ""):
            errors.append(f"lines[{idx}].quantity zorunlu")
        if line.get("unit_price") in (None, ""):
            errors.append(f"lines[{idx}].unit_price zorunlu")
    return errors


def validation_errors_for_eirsaliye(payload: Dict[str, Any]) -> List[str]:
    errors: List[str] = []
    receiver = payload.get("receiver") or {}
    despatch = payload.get("despatch") or {}
    lines = payload.get("lines") or []

    if not (receiver.get("vkn") or receiver.get("tckn")):
        errors.append("receiver.vkn (veya tckn) zorunlu")
    if not receiver.get("name"):
        errors.append("receiver.name zorunlu")
    if not despatch.get("issue_date"):
        errors.append("despatch.issue_date zorunlu")
    if not lines:
        errors.append("lines boş olamaz (en az 1 satır)")
    for idx, line in enumerate(lines):
        if not (line.get("product_name") or line.get("name")):
            errors.append(f"lines[{idx}].product_name zorunlu")
        if line.get("quantity") in (None, ""):
            errors.append(f"lines[{idx}].quantity zorunlu")
    return errors
