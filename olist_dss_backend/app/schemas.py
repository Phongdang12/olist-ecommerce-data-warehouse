from pydantic import BaseModel, Field

class WhatIfRequest(BaseModel):
    order_growth_pct: float = Field(0, ge=-90, le=300)
    order_value_change_pct: float = Field(0, ge=-90, le=300)
    late_rate_reduction_pct: float = Field(0, ge=0, le=100)
    freight_change_pct: float = Field(0, ge=-100, le=300)
