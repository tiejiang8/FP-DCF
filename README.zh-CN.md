# FP-DCF

[English](./README.md) | [简体中文](./README.zh-CN.md)

面向 LLM Agent 与量化研究流程的第一性原理 DCF 估值引擎。

FP-DCF 专注做一件事：把公开财报与市场数据转成可审计的 `FCFF`、`WACC`、估值结果、隐含增长率与敏感性分析输出，而不是把会计口径与估值假设混在一起做成一个黑盒数字。

> 仓库工作流说明：本项目提交到 GitHub 时不走单独功能分支工作流。除非维护者明确说明，否则请直接在指定分支上提交和同步。

代表性的市场隐含敏感性热力图：

| Apple 两阶段 | NVIDIA 三阶段 |
| --- | --- |
| ![Apple two-stage market-implied sensitivity heatmap](./examples/AAPL_two_stage_manual_fundamentals_market_implied.output.sensitivity.png) | ![NVIDIA three-stage market-implied sensitivity heatmap](./examples/NVDA_three_stage_manual_fundamentals_market_implied.output.sensitivity.png) |

## 快速开始

安装并直接跑 sample：

```bash
python3 -m pip install .
python3 scripts/run_dcf.py --input examples/sample_input.json --pretty
```

这会返回结构化 JSON，并默认自动渲染 `png/svg` 敏感性热力图。

## 适合谁

* 需要机器可读估值输出的 agent / tool workflow
* 量化与主观研究流程
* 在意 `FCFF -> WACC -> DCF` 可审计逻辑的用户
* 需要 diagnostics、warnings、source labels 的下游系统

## 不适合谁

* 组合优化
* 交易执行
* 回测平台
* 黑盒式“一键一个数字”的估值工具
* 与估值无关的因子排序系统

## 为什么是 FP-DCF

相比很多开源 DCF 脚本，FP-DCF 的重点是：

* 将 `FCFF` 的经营税率与 `WACC` 的边际税率明确分离
* 使用显式的 `Delta NWC` 层级，而不是硬编码一个噪声很大的字段
* 支持可追踪的 FCFF 路径选择（`EBIAT` vs `CFO`）
* 支持规范化 anchor 模式（`latest`、`manual`、`three_period_average`、`reconciled_average`）
* 输出结构化 diagnostics、warnings 与 source labels，而不是只给一个结论数

## 你会得到什么

* 支持 `steady_state_single_stage`、`two_stage`、`three_stage` 的结构化估值 JSON
* 统一的市场隐含增长能力 `market_implied_growth`
* `steady_state_single_stage` 反推市场隐含长期增长率；`two_stage` 和 `three_stage` 反推市场隐含 stage-1 增长率
* `WACC x Terminal Growth` 敏感性热力图
* provider-backed normalization，包含带本地缓存的 Yahoo 路径，以及面向 CN 的 AkShare + BaoStock fallback
* 适合下游工具消费的 machine-readable diagnostics
* 显式输出 `requested_valuation_model` / `effective_valuation_model`，unknown `valuation_model` 不再 silent fallback

## 输出形状示意

```json
{
  "valuation_model": "three_stage",
  "requested_valuation_model": "three_stage",
  "effective_valuation_model": "three_stage",
  "valuation": {
    "present_value_stage1": 514861452010.8,
    "present_value_stage2": 285871425709.47,
    "present_value_terminal": 1539144808713.01,
    "terminal_value": 3095373176764.22,
    "explicit_forecast_years": 8
  },
  "diagnostics": ["valuation_model_three_stage"],
  "warnings": []
}
```

参考：

* [sample_input.json](./examples/sample_input.json)
* [sample_output.json](./examples/sample_output.json)
* [sample_input_three_stage.json](./examples/sample_input_three_stage.json)
* [sample_output_three_stage.json](./examples/sample_output_three_stage.json)
* [sample_input_market_implied_growth_single_stage.json](./examples/sample_input_market_implied_growth_single_stage.json)
* [sample_output_market_implied_growth_single_stage.json](./examples/sample_output_market_implied_growth_single_stage.json)
* [sample_input_market_implied_growth_two_stage.json](./examples/sample_input_market_implied_growth_two_stage.json)
* [sample_output_market_implied_growth_two_stage.json](./examples/sample_output_market_implied_growth_two_stage.json)
* [sample_input_market_implied_growth_three_stage.json](./examples/sample_input_market_implied_growth_three_stage.json)
* [sample_output_market_implied_growth_three_stage.json](./examples/sample_output_market_implied_growth_three_stage.json)
* [cn_tencent_two_stage.json](./examples/cn_tencent_two_stage.json)
* [cn_tencent_two_stage.output.json](./examples/cn_tencent_two_stage.output.json)
* [cn_moutai_single_stage.json](./examples/cn_moutai_single_stage.json)
* [cn_moutai_single_stage.output.json](./examples/cn_moutai_single_stage.output.json)
* [AAPL_two_stage_manual_fundamentals_market_implied.json](./examples/AAPL_two_stage_manual_fundamentals_market_implied.json)
* [AAPL_two_stage_provider_market_implied.json](./examples/AAPL_two_stage_provider_market_implied.json)
* [NVDA_three_stage_manual_fundamentals_market_implied.json](./examples/NVDA_three_stage_manual_fundamentals_market_implied.json)
* [NVDA_three_stage_provider_market_implied.json](./examples/NVDA_three_stage_provider_market_implied.json)
* [方法论文档](./references/methodology.md)
* [English](./README.md)

## 区域样例

腾讯两阶段样例：

* 输入：[cn_tencent_two_stage.json](./examples/cn_tencent_two_stage.json)
* 输出：[cn_tencent_two_stage.output.json](./examples/cn_tencent_two_stage.output.json)
* 热力图 PNG：[cn_tencent_two_stage.output.sensitivity.png](./examples/cn_tencent_two_stage.output.sensitivity.png)

![Tencent two-stage sensitivity heatmap](./examples/cn_tencent_two_stage.output.sensitivity.png)

贵州茅台单阶段样例：

* 输入：[cn_moutai_single_stage.json](./examples/cn_moutai_single_stage.json)
* 输出：[cn_moutai_single_stage.output.json](./examples/cn_moutai_single_stage.output.json)
* 热力图 PNG：[cn_moutai_single_stage.output.sensitivity.png](./examples/cn_moutai_single_stage.output.sensitivity.png)

![Kweichow Moutai single-stage sensitivity heatmap](./examples/cn_moutai_single_stage.output.sensitivity.png)

AAPL / NVDA 市场隐含输入样例。上面的首图使用的是 `manual_fundamentals` 版本：

* Apple 两阶段，手工 fundamentals：[AAPL_two_stage_manual_fundamentals_market_implied.json](./examples/AAPL_two_stage_manual_fundamentals_market_implied.json)
* Apple 两阶段，provider fundamentals：[AAPL_two_stage_provider_market_implied.json](./examples/AAPL_two_stage_provider_market_implied.json)
* NVIDIA 三阶段，手工 fundamentals：[NVDA_three_stage_manual_fundamentals_market_implied.json](./examples/NVDA_three_stage_manual_fundamentals_market_implied.json)
* NVIDIA 三阶段，provider fundamentals：[NVDA_three_stage_provider_market_implied.json](./examples/NVDA_three_stage_provider_market_implied.json)

## 项目定位

这个仓库是更大 Yahoo / 市场数据 DCF 工作流的公开提炼层，边界刻意收窄，不是完整投研平台：

* 重点放在 valuation logic、input / output contract、以及 LLM-friendly packaging
* 不试图覆盖 portfolio optimizer、execution engine、backtesting system
* 更适合作为 downstream ranking、portfolio construction、agent orchestration 的上游模块

## 核心原则

### 1. 税率口径分离

* `FCFF` 应优先使用最合适的经营税率，通常是报表中的有效税率
* `WACC` 的债务税盾应使用边际税率
* 若发生 fallback，输出里必须明确来源

### 2. 稳健的 Delta NWC 处理

预期层级如下：

1. `delta_nwc`
2. `OpNWC_delta`
3. `NWC_delta`
4. 由流动资产 / 流动负债反推的经营营运资本变化
5. 现金流量表中的 `ChangeInWorkingCapital` 一类字段

最终选用的来源必须在输出中说明。

### 3. 规范化 FCFF 锚点

对于 steady-state single-stage DCF：

* 不把历史 `FCFF` 直接当未来显式预测期
* 优先使用规范化 steady-state anchor
* 当驱动项充分时，优先走 `NOPAT + ROIC + reinvestment`
* 当经营驱动路径不完整时，再回退到规范化历史 `FCFF`
* `assumptions.fcff_anchor_mode` 默认是 `latest`，同时支持 `manual`、`three_period_average`、`reconciled_average`
* provider-backed normalization 只暴露这些模式所需的最少量历史序列，并使用 `date:value` 字典表示

### 4. 市值口径的 WACC

目标 `WACC` 路径包括：

* 无风险利率
* 权益风险溢价
* Beta / Cost of Equity
* 税前债务成本
* 市值口径的股权与债务权重
* 使用边际税率的显式债务税盾

## 可执行入口

使用完整结构化输入运行：

```bash
python3 scripts/run_dcf.py --input examples/sample_input.json --pretty
```

安装后也可以使用打包 CLI：

```bash
fp-dcf --input examples/sample_input.json --pretty
```

如果你只有 ticker，希望程序自动从 Yahoo Finance 补齐主要估值输入，可以从下面开始：

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

对于中国 A 股，也可以显式走更适合国内网络环境的 provider：

```bash
cat > /tmp/fp_dcf_cn_input.json <<'JSON'
{
  "ticker": "600519.SH",
  "market": "CN",
  "provider": "akshare_baostock",
  "statement_frequency": "A",
  "valuation_model": "steady_state_single_stage",
  "assumptions": {
    "terminal_growth_rate": 0.025
  }
}
JSON

python3 scripts/run_dcf.py --input /tmp/fp_dcf_cn_input.json --pretty
```

当 `market="CN"` 且 Yahoo normalization 失败时，FP-DCF 现在会自动 fallback 到 `akshare_baostock`。这条路径里，AkShare 提供财务报表数据，BaoStock 提供价格历史和最新收盘价。

## 估值模型

FP-DCF `v0.4.0` 在主估值链中支持以下 `valuation_model`：

* `steady_state_single_stage`
* `two_stage`
* `three_stage`

其中 `three_stage` 是真正的三阶段估值：高增长期、收敛期、终值期。对未知 `valuation_model`，FP-DCF 现在会直接报错，并在错误信息中包含 `unsupported valuation_model`；不再静默回退到 `steady_state_single_stage`。

`market_implied_growth` 是唯一正式的市场隐含增长入口。它的含义由 `valuation_model` 决定：`steady_state_single_stage` 反推市场隐含长期增长率，`two_stage` 和 `three_stage` 反推市场隐含 stage-1 增长率。

三阶段输入示例：

```json
{
  "valuation_model": "three_stage",
  "assumptions": {
    "terminal_growth_rate": 0.03,
    "stage1_growth_rate": 0.08,
    "stage1_years": 5,
    "stage2_end_growth_rate": 0.045,
    "stage2_years": 3,
    "stage2_decay_mode": "linear"
  },
  "fundamentals": {
    "fcff_anchor": 106216000000.0,
    "net_debt": 46000000000.0,
    "shares_out": 15500000000.0
  }
}
```

三阶段输出片段：

```json
{
  "valuation_model": "three_stage",
  "requested_valuation_model": "three_stage",
  "effective_valuation_model": "three_stage",
  "valuation": {
    "present_value_stage1": 514861452010.79553,
    "present_value_stage2": 285871425709.4699,
    "present_value_terminal": 1539144808713.0115,
    "terminal_value": 3095373176764.218,
    "terminal_value_share": 0.6577885748631422,
    "explicit_forecast_years": 8,
    "stage1_years": 5,
    "stage2_years": 3,
    "stage2_decay_mode": "linear"
  }
}
```

## 敏感性热力图

FP-DCF 默认会把精简版 `WACC x Terminal Growth` 敏感性摘要附加到主估值 JSON 中，并在同一次运行里自动渲染图表产物。

CLI 示例：

```bash
python3 scripts/run_dcf.py \
  --input /tmp/fp_dcf_yahoo_input.json \
  --output /tmp/aapl_output.json \
  --pretty
```

这一条命令会：

* 把估值 JSON 写到 `/tmp/aapl_output.json`
* 在 JSON 中附加精简版 `sensitivity` 摘要
* 自动渲染 `/tmp/aapl_output.sensitivity.svg`
* 自动渲染 `/tmp/aapl_output.sensitivity.png`

如果你想覆盖默认图表路径，也可以继续显式指定：

```bash
python3 scripts/run_dcf.py \
  --input /tmp/fp_dcf_yahoo_input.json \
  --output /tmp/aapl_output.json \
  --sensitivity-chart-output /tmp/aapl_sensitivity.svg \
  --pretty
```

也可以通过输入 JSON 驱动：

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

如果你需要把完整数值网格也放进 JSON，可以显式开启：

```json
{
  "sensitivity": {
    "detail": true
  }
}
```

如果想在某次运行里关闭 sensitivity，可以用：

```bash
python3 scripts/run_dcf.py --input examples/sample_input.json --no-sensitivity --pretty
```

或者在 payload 中写：

```json
{
  "sensitivity": {
    "enabled": false
  }
}
```

默认热力图设置为：

* `metric=per_share_value`
* WACC 轴：基准值上下各 `200 bps`
* Terminal Growth 轴：基准值上下各 `100 bps`

当 terminal growth 大于等于 WACC 时，对应单元格会留空，并在 diagnostics 中说明。

## 市场隐含增长

主 CLI 可以在不改变 `run_valuation()` 主逻辑的前提下，追加结构化 `market_implied_growth` 输出。

输入约定：

* 直接提供 `payload.market_inputs.enterprise_value_market`，或
* 提供 `payload.market_inputs.market_price`，再结合 `shares_out` 与 `net_debt` 推导 EV
* `payload.market_implied_growth.enabled = true`
* 可选项包括 `lower_bound`、`upper_bound`、`solver`、`tolerance`、`max_iterations`

按 `valuation_model` 的解释方式：

* `steady_state_single_stage` 反推 `growth_rate`，即市场隐含长期增长率
* `two_stage` 和 `three_stage` 反推 `stage1_growth_rate`，即市场隐含 stage-1 增长率

输出块也叫 `market_implied_growth`，并且始终包含：

* `enabled`
* `success`
* `valuation_model`
* `solved_field`
* `solved_value`
* `solver_used`
* `lower_bound`
* `upper_bound`
* `iterations`
* `residual`

还可能包含：

* `market_price`
* `market_enterprise_value`
* `base_case_per_share_value`
* `base_case_enterprise_value`
* `message`

旧的市场隐含增长键会直接报错，不再兼容。

单阶段最小示例：

```json
{
  "valuation_model": "steady_state_single_stage",
  "market_inputs": {
    "market_price": 225.0
  },
  "market_implied_growth": {
    "enabled": true
  }
}
```

两阶段最小示例：

```json
{
  "valuation_model": "two_stage",
  "market_inputs": {
    "market_price": 582.5849079694428
  },
  "market_implied_growth": {
    "enabled": true,
    "lower_bound": 0.0,
    "upper_bound": 0.4
  },
  "assumptions": {
    "terminal_growth_rate": 0.03,
    "stage1_growth_rate": 0.1,
    "stage1_years": 4
  },
  "fundamentals": {
    "fcff_anchor": 100.0,
    "shares_out": 10.0,
    "net_debt": 20.0
  }
}
```

输出片段：

```json
{
  "market_implied_growth": {
    "enabled": true,
    "success": true,
    "valuation_model": "two_stage",
    "solved_field": "stage1_growth_rate",
    "solved_value": 0.14021034240722655,
    "solver_used": "bisection",
    "lower_bound": 0.0,
    "upper_bound": 0.4,
    "iterations": 20,
    "residual": 0.00035705652669548726,
    "market_price": 582.5849079694428,
    "market_enterprise_value": 5845.849079694428,
    "base_case_per_share_value": 506.5955721473416,
    "base_case_enterprise_value": 5085.955721473416,
    "message": "Market-implied growth solved successfully."
  }
}
```

示例：

* [sample_input_market_implied_growth_single_stage.json](./examples/sample_input_market_implied_growth_single_stage.json)
* [sample_output_market_implied_growth_single_stage.json](./examples/sample_output_market_implied_growth_single_stage.json)
* [sample_input_market_implied_growth_two_stage.json](./examples/sample_input_market_implied_growth_two_stage.json)
* [sample_output_market_implied_growth_two_stage.json](./examples/sample_output_market_implied_growth_two_stage.json)
* [sample_input_market_implied_growth_three_stage.json](./examples/sample_input_market_implied_growth_three_stage.json)
* [sample_output_market_implied_growth_three_stage.json](./examples/sample_output_market_implied_growth_three_stage.json)

## Provider 缓存

Provider-backed normalization 默认启用本地缓存，避免重复抓取相同请求形状下的 provider snapshot。

默认缓存目录：

```bash
~/.cache/fp-dcf
```

如果希望强制刷新 provider 数据并覆盖缓存：

```bash
python3 scripts/run_dcf.py --input /tmp/fp_dcf_yahoo_input.json --pretty --refresh-provider
```

如果希望改用指定缓存目录：

```bash
python3 scripts/run_dcf.py --input /tmp/fp_dcf_yahoo_input.json --pretty --cache-dir /tmp/fp-dcf-cache
```

也可以在 JSON 输入中控制 normalization 行为：

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

provider-backed run 还会在 diagnostics 中输出缓存状态，例如：

* `provider_cache_miss:yahoo`
* `provider_cache_hit:yahoo`
* `provider_cache_refresh:yahoo`
* `provider_cache_miss:akshare_baostock`
* `provider_cache_hit:akshare_baostock`
* `provider_cache_refresh:akshare_baostock`
* `provider_fallback:yahoo->akshare_baostock`

## Structured output 方向

这个仓库首先面向机器可消费的结构化输出。典型返回结果形状如下：

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
  "market_implied_growth": {
    "enabled": true,
    "success": true,
    "valuation_model": "steady_state_single_stage",
    "solved_field": "growth_rate",
    "solved_value": 0.05941663866081859,
    "solver_used": "closed_form",
    "lower_bound": -0.5,
    "upper_bound": 0.5,
    "iterations": 0,
    "residual": 0.0,
    "market_price": 225.0,
    "market_enterprise_value": 3533500000000.0,
    "base_case_per_share_value": 112.24525194214796,
    "base_case_enterprise_value": 1785801405103.2935,
    "message": "Market-implied growth solved successfully."
  },
  "diagnostics": [
    "tax_rate_paths_are_separated",
    "fcff_path_selector_only_ebiat_available",
    "fcff_path_selected:ebiat",
    "valuation_model_steady_state_single_stage"
  ]
}
```

更完整的例子见：

* [sample_input.json](./examples/sample_input.json)
* [sample_output.json](./examples/sample_output.json)

## 仓库结构

```text
FP-DCF/
├── README.md
├── README.zh-CN.md
├── SKILL.md
├── pyproject.toml
├── .gitignore
├── examples/
│   ├── sample_input.json
│   ├── sample_output.json
│   └── sample_output.sensitivity.png
├── scripts/
│   ├── plot_sensitivity.py
│   └── run_dcf.py
├── references/
│   └── methodology.md
├── tests/
└── fp_dcf/
```

## 安装

```bash
python3 -m pip install .
```

当前基础依赖包括：

* `akshare`
* `baostock`
* `numpy`
* `pandas`
* `yfinance`
* `matplotlib`

之所以把 `matplotlib` 作为基础依赖，是因为主 CLI 默认会渲染 `png/svg` 敏感性图表。

旧的 `.[viz]` 方式仍然可用，作为兼容别名：

```bash
python3 -m pip install .[viz]
```

本地开发与测试建议：

```bash
python3 -m pip install --upgrade pip
pip install -e .[dev]
```

运行可选的 Yahoo 实时集成测试：

```bash
FP_DCF_RUN_YAHOO_TESTS=1 pytest -q tests/test_yahoo_integration.py
```

## 当前限制

* Yahoo-backed normalization 仍依赖 provider 字段质量与可用性
* `akshare_baostock` 目前只覆盖 `market=CN`，不会替代 US/HK ticker 的 Yahoo 路径
* 缓存目前还没有 TTL 或 staleness policy
* 金融行业公司尚未有单独估值路径
* live normalization provider 现在包括 Yahoo，以及面向 CN 的 `akshare_baostock` fallback 路径

## 贡献

开发环境、检查方式与本仓库“不额外创建分支”的 GitHub 提交流程见 [CONTRIBUTING.md](./CONTRIBUTING.md)。
