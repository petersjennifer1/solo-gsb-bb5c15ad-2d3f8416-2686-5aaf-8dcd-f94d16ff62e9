"""请求/响应模型。"""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, Field

FormulaList = Annotated[
    list[str],
    Field(
        min_length=1,
        max_length=50,
        description="化学式数组，保持数组顺序作为返回系数顺序",
    ),
]


class BalanceRequest(BaseModel):
    reactants: FormulaList
    products: FormulaList


class SpeciesCoefficient(BaseModel):
    formula: str
    coefficient: int


class CoefficientPair(BaseModel):
    reactants: list[int]
    products: list[int]


class AtomTotals(BaseModel):
    reactants: dict[str, int]
    products: dict[str, int]


class ChargeTotals(BaseModel):
    reactants: int = Field(description="反应物侧带符号总电荷")
    products: int = Field(description="生成物侧带符号总电荷")


class BalanceSuccessResponse(BaseModel):
    balanced: Literal[True] = True
    reactants: list[SpeciesCoefficient]
    products: list[SpeciesCoefficient]
    coefficients: CoefficientPair
    equation: str
    atom_totals: AtomTotals
    charge_totals: ChargeTotals


class FormulaErrorDetail(BaseModel):
    side: Literal["reactants", "products"]
    index: int = Field(description="该侧数组中的下标（从 0 开始）")
    formula: str
    position: int = Field(description="化学式中的非法字符位置（从 0 开始）")
    message: str


class BalanceFailureResponse(BaseModel):
    balanced: Literal[False] = False
    reason: Literal["invalid_formula", "unbalanceable", "multiple_solutions"]
    message: str
    errors: list[FormulaErrorDetail] | None = None
