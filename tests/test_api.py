from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_balance_success():
    response = client.post(
        "/balance",
        json={"reactants": ["Fe", "O2"], "products": ["Fe3O4"]},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["balanced"] is True
    assert data["coefficients"] == {"reactants": [3, 2], "products": [1]}
    assert data["atom_totals"]["reactants"] == {"Fe": 3, "O": 4}
    # 中性反应仍返回 charge_totals，两侧均为 0
    assert data["charge_totals"] == {"reactants": 0, "products": 0}


def test_balance_ionic_half_reaction():
    response = client.post(
        "/balance",
        json={
            "reactants": ["MnO4^-", "H^+", "e^-"],
            "products": ["Mn^2+", "H2O"],
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["balanced"] is True
    assert data["coefficients"] == {
        "reactants": [1, 8, 5],
        "products": [1, 4],
    }
    assert data["charge_totals"] == {"reactants": 2, "products": 2}
    assert data["equation"] == "MnO4^- + 8H^+ + 5e^- -> Mn^2+ + 4H2O"


def test_unbalanceable_response():
    response = client.post(
        "/balance",
        json={"reactants": ["H2", "O2"], "products": ["HFeO2"]},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["balanced"] is False
    assert data["reason"] == "unbalanceable"


def test_multiple_solutions_response():
    response = client.post(
        "/balance",
        json={"reactants": ["C", "O2", "CO"], "products": ["CO2"]},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["balanced"] is False
    assert data["reason"] == "multiple_solutions"


def test_invalid_formula_returns_position():
    response = client.post(
        "/balance",
        json={"reactants": ["CuSO4.5H2O"], "products": ["CuSO4", "H2O"]},
    )
    assert response.status_code == 400
    data = response.json()
    assert data["balanced"] is False
    assert data["reason"] == "invalid_formula"
    error = data["errors"][0]
    assert error["side"] == "reactants"
    assert error["index"] == 0
    assert error["position"] == 5
    assert "点号" in error["message"]


def test_multiple_invalid_formulas_all_reported():
    response = client.post(
        "/balance",
        json={"reactants": ["Na+", "X2"], "products": ["H2O", "e-"]},
    )
    assert response.status_code == 400
    errors = response.json()["errors"]
    assert {(e["side"], e["index"], e["position"]) for e in errors} == {
        ("reactants", 0, 2),
        ("reactants", 1, 0),
        ("products", 1, 0),
    }


def test_invalid_charge_spellings_reported_by_original_position():
    response = client.post(
        "/balance",
        json={
            "reactants": ["Mg^02+", "SO4^2"],
            "products": ["e^2-", "H2O"],
        },
    )
    assert response.status_code == 400
    data = response.json()
    assert data["reason"] == "invalid_formula"
    errors = data["errors"]
    # 全部非法写法一次汇总，位置均按原字符串定位
    assert {(e["side"], e["index"], e["position"]) for e in errors} == {
        ("reactants", 0, 3),  # Mg^02+ 电荷数前导 0
        ("reactants", 1, 5),  # SO4^2 缺少正负号
        ("products", 0, 0),   # e^2- 不是合法电子写法
    }
    # 合法物质不出现在 errors 中
    assert all(e["formula"] != "H2O" for e in errors)


def test_old_style_charge_still_invalid():
    response = client.post(
        "/balance",
        json={"reactants": ["Na+", "Cl-"], "products": ["NaCl"]},
    )
    assert response.status_code == 400
    errors = response.json()["errors"]
    assert {(e["side"], e["index"], e["position"]) for e in errors} == {
        ("reactants", 0, 2),
        ("reactants", 1, 2),
    }


def test_empty_list_rejected_by_schema():
    response = client.post(
        "/balance",
        json={"reactants": [], "products": ["H2O"]},
    )
    assert response.status_code == 422


def test_missing_field_rejected_by_schema():
    response = client.post("/balance", json={"reactants": ["H2"]})
    assert response.status_code == 422
