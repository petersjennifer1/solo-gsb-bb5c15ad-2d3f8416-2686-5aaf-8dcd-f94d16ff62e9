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


def test_empty_list_rejected_by_schema():
    response = client.post(
        "/balance",
        json={"reactants": [], "products": ["H2O"]},
    )
    assert response.status_code == 422


def test_missing_field_rejected_by_schema():
    response = client.post("/balance", json={"reactants": ["H2"]})
    assert response.status_code == 422


def test_balance_ionic_half_reaction_success():
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
    assert data["coefficients"] == {"reactants": [1, 8, 5], "products": [1, 4]}
    assert data["charge_totals"] == {"reactants": 2, "products": 2}
    assert data["atom_totals"]["reactants"] == {"H": 8, "Mn": 1, "O": 4}


def test_neutral_reaction_charge_totals_zero():
    response = client.post(
        "/balance",
        json={"reactants": ["Fe", "O2"], "products": ["Fe3O4"]},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["balanced"] is True
    assert data["charge_totals"] == {"reactants": 0, "products": 0}


def test_charge_not_conserved_is_unbalanceable():
    response = client.post(
        "/balance",
        json={"reactants": ["Fe^2+"], "products": ["Fe^3+"]},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["balanced"] is False
    assert data["reason"] == "unbalanceable"


def test_invalid_charge_syntax_all_reported():
    response = client.post(
        "/balance",
        json={"reactants": ["Na^", "SO4^02-"], "products": ["e^+", "H2O"]},
    )
    assert response.status_code == 400
    data = response.json()
    assert data["balanced"] is False
    assert data["reason"] == "invalid_formula"
    errors = data["errors"]
    assert {(e["side"], e["index"], e["position"]) for e in errors} == {
        ("reactants", 0, 3),
        ("reactants", 1, 4),
        ("products", 0, 2),
    }
