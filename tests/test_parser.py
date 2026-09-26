import pytest

from app.parser import (
    ELECTRON_CHARGE,
    FormulaSyntaxError,
    ParsedFormula,
    parse_formula,
)


def test_simple_formulas():
    assert parse_formula("H2O") == ParsedFormula({"H": 2, "O": 1}, 0)
    assert parse_formula("H2") == ParsedFormula({"H": 2}, 0)
    assert parse_formula("He") == ParsedFormula({"He": 1}, 0)
    assert parse_formula("Fe3O4") == ParsedFormula({"Fe": 3, "O": 4}, 0)


def test_repeated_elements_accumulate():
    # COOH 中 O 出现两次
    assert parse_formula("COOH") == ParsedFormula({"C": 1, "O": 2, "H": 1}, 0)
    # 括号内外同名元素累加
    assert parse_formula("Mg2(OH)2") == ParsedFormula(
        {"Mg": 2, "O": 2, "H": 2}, 0
    )
    assert parse_formula("Ca3(PO4)2") == ParsedFormula(
        {"Ca": 3, "P": 2, "O": 8}, 0
    )
    assert parse_formula("K4(Fe(CN)6)") == ParsedFormula(
        {"K": 4, "Fe": 1, "C": 6, "N": 6}, 0
    )


def test_nested_parentheses_up_to_four_levels():
    # 四层：a(b(c(d)e)f)g 形式
    assert parse_formula("Mg2(Al(Si(BO4)2)3)2") == ParsedFormula(
        {"Mg": 2, "Al": 2, "Si": 6, "B": 12, "O": 48}, 0
    )


def test_five_levels_rejected():
    with pytest.raises(FormulaSyntaxError) as exc:
        parse_formula("(((((H)))))")
    assert exc.value.position == 4  # 第五个 '(' 的位置
    assert "4 层" in exc.value.message


def test_unknown_element():
    with pytest.raises(FormulaSyntaxError) as exc:
        parse_formula("X2O")
    assert exc.value.position == 0

    with pytest.raises(FormulaSyntaxError) as exc:
        parse_formula("Nx")
    assert exc.value.position == 0  # 'Nx' 不是任何元素

    # 按“最多一个小写字母”的文法，Nacl 在 c 处即判为大小写错误
    with pytest.raises(FormulaSyntaxError) as exc:
        parse_formula("Nacl")
    assert exc.value.position == 2


def test_invalid_subscript():
    with pytest.raises(FormulaSyntaxError) as exc:
        parse_formula("H0")
    assert exc.value.position == 1

    with pytest.raises(FormulaSyntaxError) as exc:
        parse_formula("H01")
    assert exc.value.position == 1

    with pytest.raises(FormulaSyntaxError) as exc:
        parse_formula("(H2)0")
    assert exc.value.position == 4


def test_unclosed_and_extra_parenthesis():
    with pytest.raises(FormulaSyntaxError) as exc:
        parse_formula("Ca(OH2")
    assert exc.value.position == 2
    assert "未闭合" in exc.value.message

    with pytest.raises(FormulaSyntaxError) as exc:
        parse_formula("H2O)")
    assert exc.value.position == 3
    assert "配对" in exc.value.message

    with pytest.raises(FormulaSyntaxError):
        parse_formula("()2")


def test_charge_suffix_simple_signs():
    assert parse_formula("Na^+") == ParsedFormula({"Na": 1}, 1)
    assert parse_formula("Cl^-") == ParsedFormula({"Cl": 1}, -1)
    assert parse_formula("H^+") == ParsedFormula({"H": 1}, 1)


def test_charge_suffix_numbered():
    assert parse_formula("Mg^2+") == ParsedFormula({"Mg": 1}, 2)
    assert parse_formula("SO4^2-") == ParsedFormula({"S": 1, "O": 4}, -2)
    assert parse_formula("Fe^3+") == ParsedFormula({"Fe": 1}, 3)
    assert parse_formula("Al^13+") == ParsedFormula({"Al": 1}, 13)
    # 电荷后缀不影响括号解析
    assert parse_formula("(OH)^-") == ParsedFormula({"O": 1, "H": 1}, -1)
    assert parse_formula("Fe(CN)6^3-") == ParsedFormula(
        {"Fe": 1, "C": 6, "N": 6}, -3
    )


def test_neutral_formulas_have_zero_charge():
    assert parse_formula("H2O").charge == 0
    assert parse_formula("K4(Fe(CN)6)").charge == 0


def test_electron_special_form():
    parsed = parse_formula("e^-")
    assert parsed == ParsedFormula({}, ELECTRON_CHARGE)
    assert parsed.counts == {}
    assert parsed.charge == -1


def test_invalid_electron_spellings():
    # 旧式 e- / 大写 E 等：首字符小写 e 一律指向位置 0
    with pytest.raises(FormulaSyntaxError) as exc:
        parse_formula("e-")
    assert exc.value.position == 0
    assert "电子" in exc.value.message

    with pytest.raises(FormulaSyntaxError) as exc:
        parse_formula("e")
    assert exc.value.position == 0

    with pytest.raises(FormulaSyntaxError) as exc:
        parse_formula("e^2-")
    assert exc.value.position == 0

    with pytest.raises(FormulaSyntaxError) as exc:
        parse_formula("e^+")
    assert exc.value.position == 0


def test_invalid_charge_spellings():
    # 旧式不带 '^' 的 + / -，仍定位到原字符
    with pytest.raises(FormulaSyntaxError) as exc:
        parse_formula("Na+")
    assert exc.value.position == 2

    with pytest.raises(FormulaSyntaxError) as exc:
        parse_formula("OH-")
    assert exc.value.position == 2

    # 电荷数不允许前导 0
    with pytest.raises(FormulaSyntaxError) as exc:
        parse_formula("Mg^02+")
    assert exc.value.position == 3

    # 缺少正负号 / 电荷数
    with pytest.raises(FormulaSyntaxError) as exc:
        parse_formula("Na^")
    assert exc.value.position == 2

    with pytest.raises(FormulaSyntaxError) as exc:
        parse_formula("Na^2")
    assert exc.value.position == 4

    # '^' 后为非法字符
    with pytest.raises(FormulaSyntaxError) as exc:
        parse_formula("Na^*")
    assert exc.value.position == 3

    # 电荷后缀必须在整个化学式末尾（^ 只能位于最外层末尾）
    with pytest.raises(FormulaSyntaxError) as exc:
        parse_formula("H2^2-O")
    assert exc.value.position == 5

    with pytest.raises(FormulaSyntaxError) as exc:
        parse_formula("Na^+Cl")
    assert exc.value.position == 4

    with pytest.raises(FormulaSyntaxError) as exc:
        parse_formula("(Na^+)")
    assert exc.value.position == 3

    # '^' 不允许出现在中间或括号组内部
    with pytest.raises(FormulaSyntaxError) as exc:
        parse_formula("(Na^+)")
    assert exc.value.position == 3

    # 以 '^' 开头
    with pytest.raises(FormulaSyntaxError) as exc:
        parse_formula("^+")
    assert exc.value.position == 0


def test_unsupported_features_are_rejected_with_position():
    with pytest.raises(FormulaSyntaxError) as exc:
        parse_formula("CuSO4.5H2O")
    assert exc.value.position == 5

    with pytest.raises(FormulaSyntaxError) as exc:
        parse_formula("CuSO4·5H2O")
    assert exc.value.position == 5

    with pytest.raises(FormulaSyntaxError) as exc:
        parse_formula("[Cu(NH3)4]SO4")
    assert exc.value.position == 0

    with pytest.raises(FormulaSyntaxError) as exc:
        parse_formula("H2 O")
    assert exc.value.position == 2

    with pytest.raises(FormulaSyntaxError) as exc:
        parse_formula("Na ^+")
    assert exc.value.position == 2


def test_empty_and_leading_digit():
    with pytest.raises(FormulaSyntaxError) as exc:
        parse_formula("")
    assert exc.value.position == 0

    with pytest.raises(FormulaSyntaxError) as exc:
        parse_formula("2H")
    assert exc.value.position == 0

    with pytest.raises(FormulaSyntaxError) as exc:
        parse_formula("H2 3")
    assert exc.value.position == 2
