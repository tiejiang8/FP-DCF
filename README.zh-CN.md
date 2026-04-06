# FP-DCF

[English](./README.md) | [简体中文](./README.zh-CN.md)

面向 LLM Agent 和量化研究流程的第一性原理 DCF Skill 与估值引擎。

`FP-DCF` 专注做一件事：把公开财报与市场数据转成可审计的 `FCFF`、`WACC` 和内在价值估计，并尽量避免常见开源 DCF 工具里的税率混用、营运资本口径漂移和“把历史现金流直接当未来预测”的问题。

## 项目定位

这个仓库是一个可执行的 DCF skill / package 边界层，面向：

- OpenClaw 一类可执行 skill runtime
- 需要结构化 JSON 输入输出的 LLM 工具链
- 批量估值、研究自动化与原型验证

它不是完整的投研平台，因此不会试图覆盖：

- 组合优化
- 交易执行
- 回测框架
- 与估值无关的因子排序系统

## 为什么做 FP-DCF

很多开源 DCF 工具在 3 个位置最容易失真：

- 把 `FCFF` 和 `WACC` 统一套用一个税率
- 过度依赖脆弱、缺失或命名混乱的营运资本字段
- 直接把历史 `FCFF` 当成未来现金流折现，而不是先构造规范化现金流锚点

`FP-DCF` 的设计重点就是把这些路径显式化、可审计化。

## 核心原则

### 1. 税率口径分离

- `FCFF` 优先使用经营层面的有效税率
- `WACC` 的债务税盾使用边际税率
- 如果发生 fallback，必须在输出里写清来源

### 2. 稳健的 Delta NWC 处理

优先级目标为：

1. `OpNWC_delta`
2. `NWC_delta`
3. 由流动资产 / 流动负债反推的经营营运资本变化
4. 现金流量表中的营运资本变化字段

估值结果必须能说明最终用了哪条路径。

### 3. 规范化 FCFF 锚点

对于 steady-state single-stage DCF：

- 不把历史实现值直接当未来预测值
- 优先使用规范化 `FCFF` 锚点
- 当驱动项可用时，优先走 `NOPAT + reinvestment` 路径
- `assumptions.fcff_anchor_mode` 默认是 `latest`，同时支持 `manual`、`three_period_average`、`reconciled_average`
- Yahoo normalization 只暴露这些模式所需的最少量历史序列，并使用 `date:value` 字典输出

### 4. 市值口径的 WACC

`WACC` 路径强调：

- 无风险利率
- ERP
- Beta / Cost of Equity
- 税前债务成本
- 市值口径资本结构权重
- 债务税盾明确使用边际税率

## 当前能力

当前仓库已经包含：

- 可执行的 CLI 和脚本入口
- 面向 OpenClaw 的 [SKILL.md](./SKILL.md)
- 基于 Yahoo Finance 的 provider-backed normalization
- 默认开启的 provider snapshot 本地缓存
- 默认开启的 `WACC x Terminal Growth` 敏感性输出与自动热力图产物
- 单阶段 / 两阶段 DCF 引擎与结构化输出
- 对应的测试与示例输入输出

## 快速开始

安装运行时依赖：

```bash
python3 -m pip install .
```

用完整输入运行：

```bash
python3 scripts/run_dcf.py --input examples/sample_input.json --pretty
```

只给 ticker，让程序自动从 Yahoo 补齐主要输入：

```bash
cat > /tmp/fp_dcf_yahoo_input.json <<'JSON'
{
  "ticker": "AAPL",
  "market": "US",
  "provider": "yahoo",
  "statement_frequency": "A",
  "valuation_model": "steady_state_single_stage",
  "assumptions": {
    "terminal_growth_rate": 0.03
  }
}
JSON

python3 scripts/run_dcf.py --input /tmp/fp_dcf_yahoo_input.json --pretty
```

## 敏感性热力图

`FP-DCF` 现在会默认把精简版的 `WACC x Terminal Growth` 敏感性摘要附加到主估值输出 JSON 中，并在同一次执行里自动渲染 `svg/png` 图表。

命令行示例：

```bash
python3 scripts/run_dcf.py \
  --input /tmp/fp_dcf_yahoo_input.json \
  --output /tmp/aapl_output.json \
  --pretty
```

这一条命令会直接生成：

- `/tmp/aapl_output.json`
- JSON 里的精简 `sensitivity` 摘要
- 自动落盘的 `/tmp/aapl_output.sensitivity.svg`
- 自动落盘的 `/tmp/aapl_output.sensitivity.png`

生成的 `output.json` 会同时包含：

- 主估值结果
- 精简版 `sensitivity` 摘要
- `artifacts.sensitivity_heatmap_path`，默认指向 PNG 图表路径
- `artifacts.sensitivity_heatmap_svg_path`，指向 SVG 图表路径

如果你确实要覆盖默认图表路径，也可以继续显式指定：

```bash
python3 scripts/run_dcf.py \
  --input /tmp/fp_dcf_yahoo_input.json \
  --output /tmp/aapl_output.json \
  --sensitivity-chart-output /tmp/aapl_sensitivity.svg \
  --pretty
```

也可以完全通过输入 JSON 来驱动这条覆盖逻辑：

```json
{
  "sensitivity": {
    "metric": "per_share_value",
    "chart_path": "/tmp/aapl_sensitivity.svg",
    "wacc_range_bps": 200,
    "wacc_step_bps": 100,
    "growth_range_bps": 100,
    "growth_step_bps": 50
  }
}
```

## Implied Growth 反推

主 CLI 现在也可以在不改变 `run_valuation()` 主流程行为的前提下，附加结构化的 implied growth 结果。

输入约定：

- 直接给 `payload.market_inputs.enterprise_value_market`，或
- 给 `payload.market_inputs.market_price`，再配合 `shares_out` 与 `net_debt` 推导 EV
- `payload.implied_growth.model` 支持 `one_stage` 和 `two_stage`

单阶段示例：

```json
{
  "market_inputs": {
    "market_price": 225.0
  },
  "implied_growth": {
    "model": "one_stage"
  }
}
```

两阶段示例：

```json
{
  "market_inputs": {
    "enterprise_value_market": 3500000000000.0
  },
  "implied_growth": {
    "model": "two_stage",
    "high_growth_years": 5,
    "stable_growth_rate": 0.03,
    "lower_bound": 0.0,
    "upper_bound": 0.25
  }
}
```

输出会新增两个顶层块：

- `market_inputs`：解析后的市场 EV / 股权市值 / 股价 / 股本 / 净债务及其来源
- `implied_growth`：结构化求解结果

其中：

- `one_stage` 使用 closed-form 直接反推 implied growth
- `two_stage` 在固定 stable growth 的前提下，用二分法反推出 implied high-growth rate
- 如果启用了 implied growth，但缺少必要的 market inputs，CLI 会跳过 `implied_growth` 输出，而不会让主估值报错

如果你需要把完整数值网格也放进 JSON，可以在 payload 里显式开启：

```json
{
  "sensitivity": {
    "detail": true
  }
}
```

如果你想在某次运行里关闭 sensitivity，可以用：

```bash
python3 scripts/run_dcf.py --input examples/sample_input.json --no-sensitivity --pretty
```

或者在输入 JSON 中写：

```json
{
  "sensitivity": {
    "enabled": false
  }
}
```

默认设置为：

- `metric=per_share_value`
- WACC 轴：基准值上下各 `200 bps`
- Terminal Growth 轴：基准值上下各 `100 bps`

当 terminal growth 大于等于 WACC 时，对应单元格会留空，并在 `diagnostics` 中写明。

如果因为缺少 `shares_out` 而无法生成 `per_share_value` 热力图，可以先加 `--refresh-provider`，或者把 metric 切换为 `equity_value` / `enterprise_value`。

为了兼容之前的用法，仓库里仍然保留了 `scripts/plot_sensitivity.py` 和 `fp-dcf-sensitivity` 入口，但现在推荐优先走主估值入口这一条一键路径。

## 缓存机制

Yahoo normalization 默认使用本地缓存，缓存目录默认是：

```bash
~/.cache/fp-dcf
```

如果你希望强制重新抓取 Yahoo 最新数据：

```bash
python3 scripts/run_dcf.py --input /tmp/fp_dcf_yahoo_input.json --pretty --refresh-provider
```

如果你希望把缓存写到指定目录：

```bash
python3 scripts/run_dcf.py --input /tmp/fp_dcf_yahoo_input.json --pretty --cache-dir /tmp/fp-dcf-cache
```

也可以在 JSON 输入里控制 normalization 行为：

```json
{
  "normalization": {
    "provider": "yahoo",
    "use_cache": true,
    "refresh": false,
    "cache_dir": "/tmp/fp-dcf-cache"
  }
}
```

provider 路径会在输出 `diagnostics` 中标记缓存状态，例如：

- `provider_cache_miss:yahoo`
- `provider_cache_hit:yahoo`
- `provider_cache_refresh:yahoo`

## 输出方向

这个仓库首先面向“机器可消费”的结构化输出。典型结果会包含：

- 估值模型类型
- 税率口径与来源
- `WACC` 输入项及来源
- `FCFF` 锚点与锚点方法
- FCFF 路径选择、anchor mode、reconciliation 信息
- 企业价值、股权价值、每股价值
- 可选的 `market_inputs` 与 `implied_growth`
- diagnostics / warnings / degradation flags

一个典型结果形状如下：

```json
{
  "ticker": "AAPL",
  "market": "US",
  "valuation_model": "steady_state_single_stage",
  "tax": {
    "effective_tax_rate": 0.187,
    "marginal_tax_rate": 0.21
  },
  "wacc_inputs": {
    "risk_free_rate": 0.043,
    "equity_risk_premium": 0.05,
    "beta": 1.08,
    "pre_tax_cost_of_debt": 0.032,
    "wacc": 0.0912624
  },
  "capital_structure": {
    "equity_weight": 0.92,
    "debt_weight": 0.08,
    "source": "yahoo:market_value_using_total_debt"
  },
  "fcff": {
    "anchor": 106216000000.0,
    "anchor_method": "ebiat_plus_da_minus_capex_minus_delta_nwc",
    "selected_path": "ebiat",
    "anchor_ebiat_path": 106216000000.0,
    "anchor_cfo_path": null,
    "ebiat_path_available": true,
    "cfo_path_available": false,
    "after_tax_interest": null,
    "after_tax_interest_source": null,
    "reconciliation_gap": null,
    "reconciliation_gap_pct": null,
    "anchor_mode": "latest",
    "anchor_observation_count": 1,
    "delta_nwc_source": "OpNWC_delta"
  },
  "valuation": {
    "enterprise_value": 1785801405103.2935,
    "equity_value": 1739801405103.2935,
    "per_share_value": 112.24525194214796
  },
  "market_inputs": {
    "enterprise_value_market": 3533500000000.0,
    "enterprise_value_market_source": "derived_from_market_price_shares_out_and_net_debt",
    "equity_value_market": 3487500000000.0,
    "market_price": 225.0,
    "shares_out": 15500000000.0,
    "net_debt": 46000000000.0
  },
  "implied_growth": {
    "enabled": true,
    "model": "one_stage",
    "solver": "closed_form",
    "success": true,
    "enterprise_value_market": 3533500000000.0,
    "fcff_anchor": 106216000000.0,
    "wacc": 0.0912624,
    "one_stage": {
      "growth_rate": 0.05941663866081859
    },
    "two_stage": null
  },
  "diagnostics": [
    "tax_rate_paths_are_separated",
    "fcff_path_selector_only_ebiat_available",
    "fcff_path_selected:ebiat",
    "valuation_model_steady_state_single_stage"
  ]
}
```

参考文件：

- [sample_input.json](./examples/sample_input.json)
- [sample_output.json](./examples/sample_output.json)

## 仓库结构

```text
FP-DCF/
├── README.md
├── README.zh-CN.md
├── SKILL.md
├── examples/
├── references/
├── scripts/
├── fp_dcf/
└── tests/
```

## 开发与测试

开发环境建议：

```bash
python3 -m pip install --upgrade pip
pip install -e .[dev]
```

当前基础运行时依赖包括：

- `numpy`
- `pandas`
- `yfinance`
- `matplotlib`

之所以把 `matplotlib` 放到基础依赖里，是因为主 CLI 默认会同时渲染 `png/svg` 敏感性图表。

旧的 `.[viz]` 安装方式仍然可以继续使用，作为兼容别名：

```bash
python3 -m pip install .[viz]
```

运行测试：

```bash
pytest -q
```

运行可选的 Yahoo 实时集成测试：

```bash
FP_DCF_RUN_YAHOO_TESTS=1 pytest -q tests/test_yahoo_integration.py
```

## 当前限制

- Yahoo provider 的字段质量和可用性并不完全稳定
- 目前缓存还没有 TTL / stale policy
- 金融行业公司还没有单独的估值处理路径
- 当前只实现了 Yahoo 这一条 live normalization provider

## 贡献

开发规范、检查方式和 PR 约定见 [CONTRIBUTING.md](./CONTRIBUTING.md)。
