# 化学反应配平 API

用 **Python + FastAPI + SymPy** 实现的化学反应式自动配平服务，支持普通分子反应、
**离子反应**以及**含电子 `e^-` 的氧化还原半反应**。

按元素守恒与电荷守恒构建**精确整数矩阵**（SymPy 有理数运算，无浮点误差），仅当：

1. 矩阵零空间维数**恰为 1**，且
2. 该唯一解可以整体取号为**全部严格正整数**

时才返回配平结果；系数约成最大公约数为 1 的最小正整数，并返回反应两侧各元素的
原子总数与带符号的总电荷。

## 支持与不支持

**支持**

- 元素符号（1–118 号真实元素，首字母大写、最多一个小写字母）
- 正整数下标（如 `H2O`、`Fe2(SO4)3`），不允许前导 0
- **最多四层**圆括号嵌套，如 `K4(Fe(CN)6)`、`Mg2(Al(Si(BO4)2)3)2`
- 重复元素累计计数（括号内外同名元素相加）
- **电荷后缀**，写在整个化学式末尾：
  - `^+`、`^-`：1 个单位的正/负电荷，如 `Na^+`、`Cl^-`、`H^+`
  - `^n+`、`^n-`：n 为**无前导 0 的正整数**，如 `Mg^2+`、`SO4^2-`、`Fe(CN)6^3-`
  - 无后缀表示中性（电荷 0）
- **电子**只能写作 `e^-`：原子计数为空、电荷为 -1，例如
  `MnO4^- + 8H^+ + 5e^- -> Mn^2+ + 4H2O`

**不支持**（直接判为非法化学式并给出字符位置）

- 不带 `^` 的旧式电荷写法（`Na+`、`Cl-`、`e-`）——请改写为 `Na^+`、`Cl^-`、`e^-`
- 电荷数带前导 0（`Mg^02+`）、缺少正负号（`Na^2`）、电荷后缀不在末尾（`Na^+Cl`）
- 点号 / 中点结晶水（`CuSO4.5H2O`、`CuSO4·5H2O`）——请把 `CuSO4` 与 `5H2O` 拆成独立物质
- 方括号、花括号（请改写为圆括号）

## 一键启动（单条命令）

需要本机已安装 Docker 与 Docker Compose v2。在仓库根目录执行：

```bash
docker compose up --build
```

该命令在构建镜像时自动完成依赖安装（`pip install -r requirements.txt`）并启动服务，
无需任何手动安装或初始化步骤。前台运行，`Ctrl+C` 停止；如需后台运行可加 `-d`
（`docker compose up --build -d`），用 `docker compose down` 停止。

### 必要配置

| 配置项 | 位置 | 默认值 | 说明 |
| --- | --- | --- | --- |
| `BALANCER_PORT` | `docker-compose.yml` 环境变量 / `.env` | `8000` | 宿主机映射端口，如端口冲突可 `BALANCER_PORT=9000 docker compose up --build` |
| 容器内监听端口 | `Dockerfile` CMD | `8000` | 与 `EXPOSE` 保持一致，一般无需修改 |

### API 地址与端口

默认通过 **http://localhost:8000** 访问：

- 服务根地址：http://localhost:8000
- 配平接口：`POST http://localhost:8000/balance`
- 健康检查：`GET http://localhost:8000/health`
- Swagger 交互文档：http://localhost:8000/docs
- OpenAPI Schema：http://localhost:8000/openapi.json

## 本地开发（不用 Docker）

```bash
pip install -r requirements.txt
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
# 运行测试
pip install pytest && python -m pytest -q
```

## API 说明

### `POST /balance`

请求体：

```json
{
  "reactants": ["Fe", "O2"],
  "products": ["Fe3O4"]
}
```

- 两个数组均至少含 1 个、至多 50 个化学式；
- **数组顺序即返回系数顺序**，不做重排、不去重、不自动增删物种；
- 电荷与电子写法见上节；所有中性反应的写法与返回完全兼容旧版本。

#### 成功（HTTP 200，`balanced: true`）

普通分子反应：

```json
{
  "balanced": true,
  "reactants": [
    {"formula": "Fe", "coefficient": 3},
    {"formula": "O2", "coefficient": 2}
  ],
  "products": [
    {"formula": "Fe3O4", "coefficient": 1}
  ],
  "coefficients": {"reactants": [3, 2], "products": [1]},
  "equation": "3Fe + 2O2 -> Fe3O4",
  "atom_totals": {
    "reactants": {"Fe": 3, "O": 4},
    "products": {"Fe": 3, "O": 4}
  },
  "charge_totals": {
    "reactants": 0,
    "products": 0
  }
}
```

含电子的半反应
（请求：`{"reactants": ["MnO4^-", "H^+", "e^-"], "products": ["Mn^2+", "H2O"]}`）：

```json
{
  "balanced": true,
  "reactants": [
    {"formula": "MnO4^-", "coefficient": 1},
    {"formula": "H^+", "coefficient": 8},
    {"formula": "e^-", "coefficient": 5}
  ],
  "products": [
    {"formula": "Mn^2+", "coefficient": 1},
    {"formula": "H2O", "coefficient": 4}
  ],
  "coefficients": {"reactants": [1, 8, 5], "products": [1, 4]},
  "equation": "MnO4^- + 8H^+ + 5e^- -> Mn^2+ + 4H2O",
  "atom_totals": {
    "reactants": {"H": 8, "Mn": 1, "O": 4},
    "products": {"H": 8, "Mn": 1, "O": 4}
  },
  "charge_totals": {
    "reactants": 2,
    "products": 2
  }
}
```

- `atom_totals` 给出配平后两侧**各元素的原子总数**（两侧必然相等）；
- `charge_totals` 给出两侧**带符号的总电荷**（两侧必然相等；中性反应为 0）。

#### 无法配平（HTTP 200，`balanced: false`）

零空间为空（含原子守恒或**电荷守恒**无法满足），或唯一解含零/正负混合系数：

```json
{
  "balanced": false,
  "reason": "unbalanceable",
  "message": "元素/电荷守恒方程无解，该反应无法配平"
}
```

例如 `Na^+ -> Na`（缺少电子，电荷不守恒）归入此类，服务**不会**自动补入 `e^-`。

#### 多组独立解（HTTP 200，`balanced: false`）

零空间维数大于 1，通常因为输入混入了两个以上独立反应：

```json
{
  "balanced": false,
  "reason": "multiple_solutions",
  "message": "零空间维数为 2（大于 1），存在多组独立的配平系数"
}
```

> 「无法配平」与「存在多组独立解」通过 `reason` 字段明确区分，
> 不会返回任意一组解来冒充唯一答案。

#### 非法化学式（HTTP 400，`balanced: false`）

一次性返回两侧**全部**非法化学式，`position` 为化学式中首个非法字符的
**0 起始下标**（未闭合的 `(` 指向该括号本身；旧式 `Na+` 指向 `+`；
非法电子写法指向首字符）：

```json
{
  "balanced": false,
  "reason": "invalid_formula",
  "message": "存在非法化学式，错误位置见 errors",
  "errors": [
    {
      "side": "reactants",
      "index": 0,
      "formula": "CuSO4.5H2O",
      "position": 5,
      "message": "不支持点号结晶水，请将其拆成反应物/生成物中的独立物质"
    }
  ]
}
```

## 可调用示例

### curl

```bash
curl -s -X POST http://localhost:8000/balance \
  -H 'Content-Type: application/json' \
  -d '{"reactants": ["MnO4^-", "H^+", "e^-"],
       "products": ["Mn^2+", "H2O"]}'
```

### Python（仅标准库）

`examples/example_call.py` 演示普通配平、复杂括号、离子半反应、无法配平、
多组解、非法化学式六类场景：

```bash
python examples/example_call.py
# 服务地址不同时：BASE_URL=http://localhost:9000 python examples/example_call.py
```

### Python（requests）

```python
import requests

resp = requests.post(
    "http://localhost:8000/balance",
    json={"reactants": ["MnO4^-", "H^+", "e^-"],
          "products": ["Mn^2+", "H2O"]},
)
print(resp.json())
# MnO4^- + 8H^+ + 5e^- -> Mn^2+ + 4H2O
```

## 算法与判定规则

1. 用递归下降解析器校验并解析每个化学式，得到 `{元素: 原子数}` 与带符号电荷
   （`e^-` 为空计数、电荷 -1；无后缀电荷为 0）；
2. 以物质为列、元素为行构建矩阵 `A`：反应物列取正、生成物列取负；
   再追加一行带符号的**电荷守恒行**；
3. `sympy.Matrix(...).nullspace()` 在精确有理数域上求零空间：
   - 零空间维数 0 → `unbalanceable`；
   - 维数 > 1 → `multiple_solutions`；
4. 唯一基向量含零分量或正负混合 → `unbalanceable`（不存在全部严格正系数）；
5. 整体取号为正，按分母公倍数转整数，再除以全部系数的最大公约数，
   得到 gcd = 1 的最小正整数解；
6. 校验两侧原子数与总电荷一致后，返回系数、两侧原子总数 `atom_totals`
   与两侧带符号总电荷 `charge_totals`。

## 项目结构

```
.
├── app/
│   ├── main.py       # FastAPI 入口（/balance、/health）
│   ├── schemas.py    # Pydantic 请求/响应模型
│   ├── balancer.py   # 元素+电荷守恒矩阵与零空间配平
│   └── parser.py     # 化学式递归下降解析（电荷后缀/e^-/四层括号/位置报错）
├── examples/
│   └── example_call.py
├── tests/            # pytest 测试（45 个用例）
├── Dockerfile
├── docker-compose.yml
└── requirements.txt
```
