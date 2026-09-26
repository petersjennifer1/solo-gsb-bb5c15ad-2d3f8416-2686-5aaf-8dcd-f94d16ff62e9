import pytest

from app.balancer import (
    MultipleSolutionsError,
    UnbalanceableError,
    balance_reaction,
)


def test_simple_balance():
    result = balance_reaction(["Fe", "O2"], ["Fe3O4"])
    assert result["coefficients"] == {"reactants": [3, 2], "products": [1]}
    assert result["equation"] == "3Fe + 2O2 -> Fe3O4"
    assert result["atom_totals"]["reactants"] == {"Fe": 3, "O": 4}
    assert result["atom_totals"]["products"] == {"Fe": 3, "O": 4}
    # 中性反应保持兼容：两侧总电荷均为 0
    assert result["charge_totals"] == {"reactants": 0, "products": 0}


def test_order_is_preserved():
    result = balance_reaction(["O2", "Fe"], ["Fe3O4"])
    assert result["coefficients"] == {"reactants": [2, 3], "products": [1]}
    assert result["reactants"][0]["formula"] == "O2"
    assert result["reactants"][1]["formula"] == "Fe"


def test_water_electrolysis():
    result = balance_reaction(["H2O"], ["H2", "O2"])
    assert result["coefficients"] == {"reactants": [2], "products": [2, 1]}
    totals = result["atom_totals"]
    assert totals["reactants"] == totals["products"] == {"H": 4, "O": 2}


def test_coefficients_are_minimal_gcd_one():
    # KMnO4 + HCl -> KCl + MnCl2 + Cl2 + H2O 的经典配平
    result = balance_reaction(
        ["KMnO4", "HCl"],
        ["KCl", "MnCl2", "Cl2", "H2O"],
    )
    coeffs = (
        result["coefficients"]["reactants"]
        + result["coefficients"]["products"]
    )
    assert coeffs == [2, 16, 2, 2, 5, 8]
    from math import gcd
    from functools import reduce

    assert reduce(gcd, coeffs) == 1


def test_nested_parentheses_balance():
    # 黄血盐 + 高锰酸钾酸性体系（示例中使用的反应）
    result = balance_reaction(
        ["K4(Fe(CN)6)", "KMnO4", "H2SO4"],
        ["KHSO4", "Fe2(SO4)3", "MnSO4", "HNO3", "CO2", "H2O"],
    )
    left = result["atom_totals"]["reactants"]
    right = result["atom_totals"]["products"]
    assert left == right
    assert all(c > 0 for c in result["coefficients"]["reactants"])
    assert all(c > 0 for c in result["coefficients"]["products"])
    assert result["coefficients"]["reactants"][0] == 10
    assert result["coefficients"]["reactants"][1] == 122


def test_unbalanceable_full_rank_no_solution():
    # 产物多了一个反应物中不存在的元素，且约束满秩：零空间为空
    with pytest.raises(UnbalanceableError):
        balance_reaction(["H2", "O2"], ["HFeO2"])


def test_unbalanceable_zero_coefficient_distinguished():
    # H2 + O2 -> H2O + Fe：Fe 列被迫为 0，唯一解含零系数
    with pytest.raises(UnbalanceableError):
        balance_reaction(["H2", "O2"], ["H2O", "Fe"])


def test_multiple_solutions():
    # C + O2 + CO -> CO2：CO + 1/2 O2 -> CO2 与 C + O2 -> CO2 两个独立反应
    with pytest.raises(MultipleSolutionsError):
        balance_reaction(["C", "O2", "CO"], ["CO2"])


def test_zero_coefficient_solution_is_unbalanceable():
    # 体系中混入一个与反应无关的物质时，唯一解里它的系数可能是 0
    with pytest.raises(UnbalanceableError):
        balance_reaction(["H2", "O2", "N2"], ["H2O"])


def test_single_species_reaction():
    # 同素异形体：O3 -> O2
    result = balance_reaction(["O3"], ["O2"])
    assert result["coefficients"] == {"reactants": [2], "products": [3]}


def test_repeated_formula_entries():
    # 同一物质出现两次：H2 + H2 -> H2O ... 无法配平（O 无来源）
    with pytest.raises(UnbalanceableError):
        balance_reaction(["H2", "H2"], ["H2O"])


def test_ionic_reaction_balances_with_charge_row():
    # Ag^+ + Cu -> Ag + Cu^2+  =>  2Ag^+ + Cu -> 2Ag + Cu^2+
    result = balance_reaction(["Ag^+", "Cu"], ["Ag", "Cu^2+"])
    assert result["coefficients"] == {"reactants": [2, 1], "products": [2, 1]}
    assert result["atom_totals"]["reactants"] == {"Ag": 2, "Cu": 1}
    assert result["atom_totals"]["products"] == {"Ag": 2, "Cu": 1}
    assert result["charge_totals"] == {"reactants": 2, "products": 2}
    assert result["equation"] == "2Ag^+ + Cu -> 2Ag + Cu^2+"


def test_ionic_precipitation_reaction():
    # Ag^+ + Cl^- -> AgCl，净离子反应，两侧总电荷为 0
    result = balance_reaction(["Ag^+", "Cl^-"], ["AgCl"])
    assert result["coefficients"] == {"reactants": [1, 1], "products": [1]}
    assert result["charge_totals"] == {"reactants": 0, "products": 0}


def test_half_reaction_with_electrons_reduction():
    # MnO4^- + H^+ + e^- -> Mn^2+ + H2O
    # => MnO4^- + 8H^+ + 5e^- -> Mn^2+ + 4H2O
    result = balance_reaction(
        ["MnO4^-", "H^+", "e^-"],
        ["Mn^2+", "H2O"],
    )
    assert result["coefficients"] == {
        "reactants": [1, 8, 5],
        "products": [1, 4],
    }
    assert result["atom_totals"]["reactants"] == {"Mn": 1, "O": 4, "H": 8}
    assert result["atom_totals"]["products"] == {"Mn": 1, "O": 4, "H": 8}
    # 左侧：-1 + 8 - 5 = +2，右侧：+2
    assert result["charge_totals"] == {"reactants": 2, "products": 2}


def test_half_reaction_with_electrons_oxidation():
    # Fe^2+ -> Fe^3+ + e^-
    result = balance_reaction(["Fe^2+"], ["Fe^3+", "e^-"])
    assert result["coefficients"] == {"reactants": [1], "products": [1, 1]}
    assert result["atom_totals"]["reactants"] == {"Fe": 1}
    assert result["charge_totals"] == {"reactants": 2, "products": 2}


def test_electron_appears_in_equation_string():
    result = balance_reaction(["Fe^2+"], ["Fe^3+", "e^-"])
    assert result["equation"] == "Fe^2+ -> Fe^3+ + e^-"


def test_charge_mismatch_is_unbalanceable():
    # 原子守恒但电荷不守恒：Na^+ -> Na （电子缺失），无解
    with pytest.raises(UnbalanceableError):
        balance_reaction(["Na^+"], ["Na"])

    # 两侧电荷不可调和：Na^+ -> Cl^-
    with pytest.raises(UnbalanceableError):
        balance_reaction(["Na^+"], ["Cl^-"])


def test_electron_only_rows_still_need_atom_balance():
    # e^- -> e^- 同物种列两侧：1 e^- -> 1 e^-
    result = balance_reaction(["e^-"], ["e^-"])
    assert result["coefficients"] == {"reactants": [1], "products": [1]}
    assert result["atom_totals"] == {"reactants": {}, "products": {}}
    assert result["charge_totals"] == {"reactants": -1, "products": -1}


def test_input_order_preserved_with_ions():
    result = balance_reaction(["e^-", "H^+", "MnO4^-"], ["H2O", "Mn^2+"])
    assert [item["formula"] for item in result["reactants"]] == [
        "e^-",
        "H^+",
        "MnO4^-",
    ]
    assert [item["formula"] for item in result["products"]] == ["H2O", "Mn^2+"]
    assert result["coefficients"]["reactants"] == [5, 8, 1]
    assert result["coefficients"]["products"] == [4, 1]
