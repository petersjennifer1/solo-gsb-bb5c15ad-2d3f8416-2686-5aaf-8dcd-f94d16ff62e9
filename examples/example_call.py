"""配平 API 调用示例（仅依赖 Python 标准库）。

用法::

    # 先启动服务
    docker compose up --build

    # 再运行示例（默认 http://localhost:8000，可用环境变量 BASE_URL 覆盖）
    python examples/example_call.py
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request

BASE_URL = os.environ.get("BASE_URL", "http://localhost:8000")


def call_balance(reactants: list[str], products: list[str]) -> dict:
    payload = json.dumps(
        {"reactants": reactants, "products": products}
    ).encode("utf-8")
    request = urllib.request.Request(
        f"{BASE_URL}/balance",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        # 非法化学式返回 400，响应体仍是同样的 JSON 结构
        return json.loads(exc.read().decode("utf-8"))


def show(title: str, reactants: list[str], products: list[str]) -> None:
    print(f"=== {title} ===")
    print(f"请求: reactants={reactants}, products={products}")
    result = call_balance(reactants, products)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    print()


def main() -> None:
    # 1. 普通配平：Fe + O2 -> Fe3O4  =>  3Fe + 2O2 -> Fe3O4
    show("普通配平", ["Fe", "O2"], ["Fe3O4"])

    # 2. 酸性条件下的半反应：MnO4^- + 8H^+ + 5e^- -> Mn^2+ + 4H2O
    show("含电子的半反应", ["MnO4^-", "H^+", "e^-"], ["Mn^2+", "H2O"])

    # 3. 离子方程式：Zn + Cu^2+ -> Zn^2+ + Cu
    show("离子方程式", ["Zn", "Cu^2+"], ["Zn^2+", "Cu"])

    # 4. 四层括号 + 重复元素累计：K4(Fe(CN)6) 参与的反应
    show(
        "复杂括号",
        ["K4(Fe(CN)6)", "KMnO4", "H2SO4"],
        ["KHSO4", "Fe2(SO4)3", "MnSO4", "HNO3", "CO2", "H2O"],
    )

    # 5. 无法配平：H2 + O2 -> H2O + Fe
    show("无法配平", ["H2", "O2"], ["H2O", "Fe"])

    # 6. 电荷不守恒：Fe^2+ -> Fe^3+（缺少电子）
    show("电荷不守恒", ["Fe^2+"], ["Fe^3+"])

    # 7. 多组独立解：C + O2 + CO -> CO2
    show("多组独立解", ["C", "O2", "CO"], ["CO2"])

    # 8. 非法化学式（点号结晶水不支持；裸 +/- 电荷记号非法）
    show("非法化学式", ["CuSO4.5H2O"], ["CuSO4", "H2O"])
    show("非法电荷写法", ["Na^", "SO4^02-"], ["e^+"])


if __name__ == "__main__":
    main()
