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
- 可选的 `WACC x Terminal Growth` 敏感性热力图工作流
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
python3 scripts/run_dcf.py --input examples/sample_input_yahoo.json --pretty
```

## 敏感性热力图

`FP-DCF` 现在支持把 `WACC x Terminal Growth` 敏感性分析直接附加到主估值输出 JSON 中；如果安装了可选绘图依赖，还可以在同一次执行里额外渲染 `svg/png` 图表。

命令行示例：

```bash
python3 scripts/run_dcf.py \
  --input examples/sample_input_yahoo.json \
  --output /tmp/aapl_output.json \
  --sensitivity \
  --sensitivity-chart-output /tmp/aapl_sensitivity.svg \
  --pretty
```

生成的 `output.json` 会同时包含：

- 主估值结果
- 结构化 `sensitivity` 热力图网格
- 如果渲染了图表，则在 `artifacts.sensitivity_heatmap_path` 中列出图表路径

也可以完全通过输入 JSON 来驱动这条路径：

```json
{
  "sensitivity": {
    "enabled": true,
    "metric": "per_share_value",
    "chart_path": "/tmp/aapl_sensitivity.svg",
    "wacc_range_bps": 200,
    "wacc_step_bps": 100,
    "growth_range_bps": 100,
    "growth_step_bps": 50
  }
}
```

默认设置为：

- `metric=per_share_value`
- WACC 轴：基准值上下各 `200 bps`
- Terminal Growth 轴：基准值上下各 `100 bps`

当 terminal growth 大于等于 WACC 时，对应单元格会留空，并在 `diagnostics` 中写明。

如果因为缺少 `shares_out` 而无法生成 `per_share_value` 热力图，可以先加 `--refresh-provider`，或者把 metric 切换为 `equity_value` / `enterprise_value`。

为了兼容之前的用法，仓库里仍然保留了 `scripts/plot_sensitivity.py` 和 `fp-dcf-sensitivity` 入口，但现在推荐优先走主估值入口。

## 缓存机制

Yahoo normalization 默认使用本地缓存，缓存目录默认是：

```bash
~/.cache/fp-dcf
```

如果你希望强制重新抓取 Yahoo 最新数据：

```bash
python3 scripts/run_dcf.py --input examples/sample_input_yahoo.json --pretty --refresh-provider
```

如果你希望把缓存写到指定目录：

```bash
python3 scripts/run_dcf.py --input examples/sample_input_yahoo.json --pretty --cache-dir /tmp/fp-dcf-cache
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
- 企业价值、股权价值、每股价值
- diagnostics / warnings / degradation flags

参考文件：

- [sample_input.json](./examples/sample_input.json)
- [sample_input_yahoo.json](./examples/sample_input_yahoo.json)
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

如果你需要渲染热力图文件，再安装可选绘图库依赖：

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
