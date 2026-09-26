"""基于元素守恒与电荷守恒矩阵的反应配平。

把每种物质作为一列、每种元素以及电荷作为一行：

* 反应物列填入该物质中各元素的原子数与带符号电荷（正号）；
* 生成物列填入原子数与电荷的相反数（负号）。

配平系数向量 ``c`` 满足 ``A · c = 0``。用 SymPy 在整数/有理数域上求精确
零空间：零空间维数必须恰为 1，且该基向量可以整体取号为全部严格正整数，
再约去最大公约数得到最小正整数解。

电子 ``e^-`` 的原子计数为空、电荷为 -1，仅以电荷行参与矩阵，因此
离子反应与含电子的氧化还原半反应同样可以配平。
"""

from __future__ import annotations

from math import gcd

from sympy import Matrix, Rational

from .parser import FormulaSyntaxError, parse_formula


class BalanceError(Exception):
    """配平失败基类。"""


class UnbalanceableError(BalanceError):
    """零空间无解（无法满足元素/电荷守恒）。"""

    kind = "unbalanceable"


class MultipleSolutionsError(BalanceError):
    """零空间维数大于 1，存在多组独立配平。"""

    kind = "multiple_solutions"


def balance_reaction(
    reactants: list[str], products: list[str]
) -> dict:
    """配平一个化学反应（允许离子与电子 ``e^-``）。

    :returns: 成功时返回字典，字段见模块级说明；
    :raises UnbalanceableError: 无法配平；
    :raises MultipleSolutionsError: 存在多组独立解；
    :raises FormulaSyntaxError: 化学式非法。
    """
    species = [*reactants, *products]
    n_reactants = len(reactants)

    parsed = [parse_formula(formula) for formula in species]
    elements = sorted({el for p in parsed for el in p.counts})

    # 元素守恒行 + 电荷守恒行（电荷带符号：Na^+ 为 +1，e^- 为 -1）。
    rows = [
        [
            Rational(p.counts.get(el, 0)) * (1 if i < n_reactants else -1)
            for i, p in enumerate(parsed)
        ]
        for el in elements
    ]
    rows.append(
        [
            Rational(p.charge) * (1 if i < n_reactants else -1)
            for i, p in enumerate(parsed)
        ]
    )
    matrix = Matrix(rows)

    nullspace = matrix.nullspace()
    if not nullspace:
        raise UnbalanceableError("元素/电荷守恒方程无解，该反应无法配平")
    if len(nullspace) > 1:
        raise MultipleSolutionsError(
            f"零空间维数为 {len(nullspace)}（大于 1），存在多组独立的配平系数"
        )

    basis = nullspace[0]
    if any(component == 0 for component in basis):
        raise UnbalanceableError(
            "唯一解中存在系数为 0 的物质，无法在保留全部输入物质的情况下配平"
        )
    if not (all(v > 0 for v in basis) or all(v < 0 for v in basis)):
        raise UnbalanceableError(
            "唯一解的系数存在正负混合，无法通过整体取号得到全部为正的系数"
        )

    coefficients = _to_coprime_positive_ints(basis)

    reactant_coeffs = coefficients[:n_reactants]
    product_coeffs = coefficients[n_reactants:]
    left_atoms = _atom_totals(parsed[:n_reactants], reactant_coeffs)
    right_atoms = _atom_totals(parsed[n_reactants:], product_coeffs)
    left_charge = _charge_total(parsed[:n_reactants], reactant_coeffs)
    right_charge = _charge_total(parsed[n_reactants:], product_coeffs)

    # 最终核验：两侧各元素原子数与总电荷必须完全一致。
    if left_atoms != right_atoms:  # 理论上不会发生，留作防御
        raise UnbalanceableError("内部校验失败：两侧原子数不一致")
    if left_charge != right_charge:  # 理论上不会发生，留作防御
        raise UnbalanceableError("内部校验失败：两侧总电荷不一致")

    return {
        "balanced": True,
        "reactants": [
            {"formula": formula, "coefficient": coeff}
            for formula, coeff in zip(reactants, reactant_coeffs)
        ],
        "products": [
            {"formula": formula, "coefficient": coeff}
            for formula, coeff in zip(products, product_coeffs)
        ],
        "coefficients": {
            "reactants": reactant_coeffs,
            "products": product_coeffs,
        },
        "equation": _render_equation(
            reactants, reactant_coeffs, products, product_coeffs
        ),
        "atom_totals": {
            "reactants": left_atoms,
            "products": right_atoms,
        },
        "charge_totals": {
            "reactants": left_charge,
            "products": right_charge,
        },
    }


def _to_coprime_positive_ints(basis: Matrix) -> list[int]:
    """把有理零空间基向量取号为正并约成 gcd = 1 的最小正整数。"""
    rationals = [Rational(v) for v in basis]
    denominators = [rational.q for rational in rationals]

    common_denominator = 1
    for denominator in denominators:
        common_denominator = common_denominator * denominator // gcd(
            common_denominator, denominator
        )

    values = [int(rational * common_denominator) for rational in rationals]
    if all(v < 0 for v in values):
        values = [-v for v in values]

    common_divisor = 0
    for value in values:
        common_divisor = gcd(common_divisor, abs(value))
    if common_divisor > 1:
        values = [v // common_divisor for v in values]
    return values


def _atom_totals(
    parsed_side: list, coeffs: list[int]
) -> dict[str, int]:
    totals: dict[str, int] = {}
    for parsed, coeff in zip(parsed_side, coeffs):
        for element, amount in parsed.counts.items():
            totals[element] = totals.get(element, 0) + amount * coeff
    return dict(sorted(totals.items()))


def _charge_total(parsed_side: list, coeffs: list[int]) -> int:
    """该侧配平后的带符号总电荷。"""
    return sum(parsed.charge * coeff for parsed, coeff in zip(parsed_side, coeffs))


def _render_equation(
    reactants: list[str],
    reactant_coeffs: list[int],
    products: list[str],
    product_coeffs: list[int],
) -> str:
    def side(formulas: list[str], coeffs: list[int]) -> str:
        parts = []
        for formula, coeff in zip(formulas, coeffs):
            parts.append(formula if coeff == 1 else f"{coeff}{formula}")
        return " + ".join(parts)

    return f"{side(reactants, reactant_coeffs)} -> {side(products, product_coeffs)}"
