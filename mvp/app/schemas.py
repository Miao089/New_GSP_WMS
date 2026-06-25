from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel, Field, field_validator


PartnerType = Literal["supplier", "customer", "both"]
TempZone = Literal["ambient", "cool", "refrigerated", "frozen", "ultra_low"]


class MaterialIn(BaseModel):
    code: str = Field(min_length=1, examples=["MD-6846-001"])
    name: str = Field(min_length=1, examples=["一次性植入器械"])
    category_code: str = Field(min_length=1, examples=["6846"])
    registration_no: str = Field(min_length=1, examples=["械注准20260001"])
    registration_valid_until: date
    sn_control: bool = False
    temp_zone: TempZone = "ambient"
    storage_rules: str = ""


class PartnerIn(BaseModel):
    code: str = Field(min_length=1, examples=["SUP-001"])
    name: str = Field(min_length=1)
    partner_type: PartnerType
    scope_codes: list[str] = Field(default_factory=list, examples=[["6846", "6815"]])
    license_valid_until: date

    @field_validator("scope_codes")
    @classmethod
    def scope_must_not_be_empty(cls, value: list[str]) -> list[str]:
        if not value:
            raise ValueError("scope_codes cannot be empty")
        return sorted(set(value))


class InboundReceiptIn(BaseModel):
    material_code: str
    supplier_code: str
    warehouse_code: str = "WH-001"
    location_code: str = "A-01-01"
    lot_no: str
    expires_at: date
    quantity: int = Field(gt=0)
    udi: str | None = None
    serial_numbers: list[str] = Field(default_factory=list)
    actor: str = "system"
    reason: str = "purchase receiving"


class OutboundOrderIn(BaseModel):
    material_code: str
    customer_code: str
    warehouse_code: str = "WH-001"
    quantity: int = Field(gt=0)
    actor: str = "system"
    reason: str = "sales outbound allocation"


class TemperatureAlertIn(BaseModel):
    warehouse_code: str = "WH-001"
    location_code: str
    observed_value: float
    threshold: str = "temperature out of range"
    actor: str = "sensor"
    reason: str = "temperature excursion"


class ApiResult(BaseModel):
    ok: bool
    data: dict | list | None = None
