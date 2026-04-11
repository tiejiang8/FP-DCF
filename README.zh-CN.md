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
* `one_stage` / `two_stage` implied growth；现有 `implied_growth` block 仍不支持 `three_stage`
* 支持 `two_stage` / `three_stage` 的独立 `market_implied_stage1_growth` 反推块
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
* [sample_input_market_implied_stage1_growth_two_stage.json](./examples/sample_input_market_implied_stage1_growth_two_stage.json)
* [sample_output_market_implied_stage1_growth_two_stage.json](./examples/sample_output_market_implied_stage1_growth_two_stage.json)
* [sample_input_market_implied_stage1_growth_three_stage.json](./examples/sample_input_market_implied_stage1_growth_three_stage.json)
* [sample_output_market_implied_stage1_growth_three_stage.json](./examples/sample_output_market_implied_stage1_growth_three_stage.json)
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

`v0.4.0` 的 `three_stage` 现在既支持主估值，也支持独立的 `market_implied_stage1_growth` 反推；现有 `implied_growth` 求解器仍只支持 `one_stage` 与 `two_stage`。

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

## 隐含增长率反推

主 CLI 可以在不改变 `run_valuation()` 主逻辑的前提下，追加结构化 implied-growth 输出。

输入约定：

* 直接提供 `payload.market_inputs.enterprise_value_market`，或
* 提供 `payload.market_inputs.market_price`，再结合 `shares_out` 与 `net_debt` 推导 EV
* `payload.implied_growth.model` 支持 `one_stage` 与 `two_stage`

`v0.4.0` 中，现有隐含增长求解器仍不支持 `three_stage`。

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

输出会追加：

* `market_inputs`：解析后的 market EV / equity value / price / shares / net debt 及其来源
* `implied_growth`：结构化求解结果

其中：

* `one_stage` 使用 closed-form 直接反推 implied growth
* `two_stage` 在固定 stable growth 的前提下，使用二分法反推 implied high-growth rate
* 如果启用了 implied growth，但 market inputs 不完整，CLI 会跳过 implied-growth 输出，而不会让主估值失败

single-stage 的市场隐含增长仍应走 `payload.implied_growth.model=one_stage`，不要把 `steady_state_single_stage` 强行塞进 `market_implied_stage1_growth`。

## 市场隐含 stage1 增长率

`market_implied_stage1_growth` 是一个独立于 `implied_growth` 的输出块。

它只回答一个问题：

* 在 base-case 的 `FCFF` anchor、`WACC`、terminal growth、阶段年数、capital structure、`shares_out`、`net_debt` 都不变时
* 市场价格或市场 EV 等价于多高的 `stage1_growth_rate`

这是单变量解释层，不会自动改写 payload assumptions，也不是多参数联动校准。

支持范围：

* `valuation_model=two_stage`
* `valuation_model=three_stage`

不支持：

* `valuation_model=steady_state_single_stage`

如果在 `steady_state_single_stage` 上启用它，FP-DCF 会直接报错：

* `market_implied_stage1_growth requires valuation_model in {two_stage, three_stage}`

两阶段最小输入：

```json
{
  "valuation_model": "two_stage",
  "market_inputs": {
    "market_price": 582.5849079694428
  },
  "market_implied_stage1_growth": {
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

三阶段最小输入：

```json
{
  "valuation_model": "three_stage",
  "market_inputs": {
    "market_price": 491.243930259804
  },
  "market_implied_stage1_growth": {
    "enabled": true
  },
  "assumptions": {
    "terminal_growth_rate": 0.03,
    "stage1_growth_rate": 0.12,
    "stage1_years": 3,
    "stage2_end_growth_rate": 0.06,
    "stage2_years": 2,
    "stage2_decay_mode": "linear"
  },
  "fundamentals": {
    "fcff_anchor": 100.0,
    "shares_out": 10.0,
    "net_debt": 0.0
  }
}
```

输出片段：

```json
{
  "market_implied_stage1_growth": {
    "enabled": true,
    "success": true,
    "valuation_model": "two_stage",
    "solver": "bisection",
    "target_metric": "per_share_value",
    "market_price": 582.5849079694428,
    "enterprise_value_market": 5845.849079694428,
    "base_case_value": 506.5955721473416,
    "base_input_value": 0.1,
    "solved_value": 0.14021034240722655,
    "absolute_offset": 0.04021034240722654,
    "relative_offset_pct": 40.21034240722654,
    "lower_bound": 0.0,
    "upper_bound": 0.4,
    "iterations": 20,
    "residual": 0.00035705652669548726,
    "interpretation": "The market is pricing a stronger explicit-growth phase than the base case."
  }
}
```

示例：

* [sample_input_market_implied_stage1_growth_two_stage.json](./examples/sample_input_market_implied_stage1_growth_two_stage.json)
* [sample_output_market_implied_stage1_growth_two_stage.json](./examples/sample_output_market_implied_stage1_growth_two_stage.json)
* [sample_input_market_implied_stage1_growth_three_stage.json](./examples/sample_input_market_implied_stage1_growth_three_stage.json)
* [sample_output_market_implied_stage1_growth_three_stage.json](./examples/sample_output_market_implied_stage1_growth_three_stage.json)

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
