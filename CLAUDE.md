# Backtesting

Backtests of the user's futures trading strategies on their own 1-minute data. Report results as point and dollar P&L per contract, not percent returns (see "Back-adjusted prices" below).

## Standing instructions from the user

- **Every test comes with its equity curves.** The standard report draws 3 SVGs per run and period in `<out>/equity/`: sizes, balance schemes, market schemes. Send the relevant charts to the user every time.
- **One standard test and report for every futures strategy (user, 2026-10-30 / 2026-10-31).** Run every test through `LucidSim/run_lucid.py`, or through a runner that calls its `evaluate()` and `write_outputs()`, as `Vaultbreak/scripts/vb_lucid.py` does.
  - Cover sizes 1–4 contracts plus the 8 standard sizing schemes, and each period: the whole window, 2016–2019, 2020–2023, 2024–2026.
  - The default account is LucidPro 50K with the daily loss limit off.
  - Every run writes `tables.md` and `datasheet.html` (`LucidSim/lucid_report.py`).
  - **Return the results as the tables in `tables.md`**: for each run and period, one row per sizing in three tables:
    - **A. Performance and risk:** net, return, CAGR, volatility, Sharpe, Sortino, Calmar, max drawdown $ and %, drawdown days, recovery.
    - **B. Trades:** count, win %, PF, average win and loss, payoff, expectancy, median, best and worst trade, gross profit and loss, longest win/loss runs, average bars held, average contracts.
    - **C. LucidPro 50K:** pass rate, pass within 30/45/60 days, mean and median days to pass, pass/fail/open, payout rates, payouts per pass, trader $ per pass and when paid, days to first payout, funded breach rate, funded days survived, expected payout per evaluation.
  - Also send `datasheet.html`: every field, all charts, the by-year table and exit reasons.
- **LucidPro has no consistency rule in the evaluation.** The 40% rule only applies to funded payouts. The user confirmed this.
- **The user's second engine was removed at their request (2026-10-30).** `Engine2/`, `.venv/` and the comparison runs are gone. Use only `BacktestEngine/`.
- **Tested PowerLanguage files** go are delivered to the user on request; they are not stored in the folder.

## Data

Files in `data\` in this folder (`C:\Backtesting\data\`), checked row by row on 2026-10-29. The originals in `C:\Users\Radu\Downloads\` are identical copies, but read from `data\`:

| File | Market | Bars | First bar → last bar |
|---|---|---|---|
| BTC.csv | CME Bitcoin futures | 1,879,956 | 2017-12-17 18:01 → 2026-09-02 19:58 |
| ES.csv | E-mini S&P 500 | 4,920,767 | 2010-06-06 18:01 → 2026-08-31 20:00 |
| NQ.csv | E-mini Nasdaq-100 | 4,811,160 | 2010-06-06 18:01 → 2026-09-02 20:00 |
| GC.csv | Gold | 5,610,270 | 2010-06-06 18:01 → 2026-09-02 20:00 |

Format: header `Date,Time,Open,High,Low,Close,Volume`. Date is `YYYYMMDD`, Time is `HHMMSS` (pad to 6 digits).

- **Bars:** 1-minute bars in US Eastern time, stamped with the bar's closing time. The session opens with the 18:01 bar. The 17:00→18:01 daily break is in the data, and so is the 16:15–16:30 ES/NQ halt that applied before 2021.
- **Back-adjusted prices:** these are continuous contracts with additive (Panama) back-adjustment. Early prices sit far above real history (ES in 2010 shows ≈1665 when the real price was ~1060), but every price is still on the tick grid. Point and dollar P&L is valid. Percent returns, and filters on fixed price levels, are wrong on older data.
- **Data quality:** no duplicate or out-of-order timestamps, no inconsistent OHLC, no zero volume, and no gaps longer than 4 days. A missing minute means nothing traded. BTC is sparse: only ~75% of its bars are 1 minute apart.
- **ES/NQ are incomplete before 2016, so their backtests start on 2016-01-01.**
  - 2010–2012 are missing most day sessions (only 30–105 full RTH days a year).
  - 2013–2015 miss about 40 days a year and have no bars after 15:00 CT.
  - Full sessions start in 2016.
  - GC is complete from 2010, with a few thin days a year.
- **Stray bars:** on some 2016–2020 days there are bars between 16:00 and 17:00 CT. Strategies built on the 17:00–16:00 CT template drop them (`eth_session` in `BacktestEngine/data.py`).

## Contract specs

| Symbol | Tick | Full size | Micro |
|---|---|---|---|
| ES | 0.25 | $50/pt ($12.50/tick) | MES $5/pt |
| NQ | 0.25 | $20/pt ($5/tick) | MNQ $2/pt |
| GC | 0.10 | $100/pt ($10/tick) | MGC $10/pt |
| BTC | 5 | $5/pt ($25/tick) | MBT $0.10/pt |

## Backtester

- `strategies/strategy_0N.pl`: the user's MultiCharts PowerLanguage originals, all written in CT for MNQ.
- `BacktestEngine/`: the Python port.
  - `data.py`: loads the CSVs into CT arrays, cached in `cache/`.
  - `engine.py`: MultiCharts-style order engine.
  - `strategies.py`: one function per strategy.
  - `run_all.py`: runs the full grid.
  - `report.py`: writes the CSVs.
- `results/`: `summary.json`, `summary.csv`, `by_year.csv`, and `trades/<strategy>_<market>_<tf>.csv`. Trade times are fill-bar close stamps in CT, as MultiCharts shows them.

```bash
python -I BacktestEngine/run_all.py --only S01,S04 --symbols NQ,ES --tfs 1,5,15,60
```

```bash
python -I BacktestEngine/report.py
```

Account stats and prop-firm sim (the user's report format):

- `BacktestEngine/metrics.py`: account stats from a 1-minute mark-to-market equity curve. Initial cash is $50k.
- `BacktestEngine/propsim.py`: LucidPro 50K with the DLL off. It runs 1,000 block-bootstrap paths: the evaluation gets up to 2 years, and the funded account runs for up to 1 year.
  - It reports the payout rate (of all evaluations and of passed ones) and the % passed within 30, 45 and 60 trading days.
  - `simulate(days, sizing=(base, scaled, balance))` models switching size at a balance, e.g. `(1, 2, 52500)` for 1 MNQ until $52,500, then 2. The day paths must be built at 1 contract.
- **Everything VaultBreak lives in `Vaultbreak/`**, as the user asked.
  - `vaultbreak.py`: the Python port (v1 + every option, v4 entries).
  - `code/`: PowerLanguage v1 original, v3 and v4.
  - `scripts/`: `opt.py`, `cmp.py`, `save_results.py`, `v4_grid.py` and `portfolio.py`. They add `BacktestEngine` and `Vaultbreak` to the import path themselves.
  - `results/v3/`: `summary_<n>ct.json`, `sizing.csv`, `comparison_by_period.txt`, the optimiser log and equity curves.
  - **Standard test:** `scripts/vb_lucid.py` runs VaultBreak through the standard report (`run_lucid.evaluate`/`write_outputs`).
    - Default variants: v1 (paper original) and v3. Add others with `--variant 'name={"cfg":...}'`.
    - Run ids are `VB_<variant>_NQ_<tf>`.
    - Output goes to `results/std/`. A run takes about 2 minutes.
    - `scripts/vb_improve.py` checks candidate changes against v3 in each of the 3 periods. It writes `results/std/improve.json`.
    - Rebuild the data sheet with the improvement grid using `python -I LucidSim/lucid_report.py Vaultbreak/results/std`.
    - Tested 2026-10-31; none beat v3 in all 3 periods:
      - slippage and fill checks;
      - funded account at 1 or 2 ct;
      - daily trade caps;
      - rolling ranges;
      - range-scaled stops and targets;
      - a 60-point stop.
    - The range average is expanding (all history loaded, from 2016 here), so live charts must load the same history.
  - `docs/`: the paper spec PDF.
- How the port works: it runs on RTH-only bars (`rth_bars`) with signal bars anchored at 09:30 ET, and always flattens on 1-minute bars.
- **The user's goal is passing LucidPro 50K in 45 trading days or fewer.** At 1→2 MNQ VaultBreak needs about 210 days; 3 MNQ needs about 37.
- What has been tested (2016–2019, 2020–2023 and 2024–2026 checked separately; always keep doing that):
  - Tuning on 2020–2023 alone overfit and collapsed on 2024–2026.
  - The v4 additions all failed to beat v3 on every period: ORB entries, an opening-range gate, continuation entries, and pairing it with Forecast-to-Fill.
  - The best remains v3 settings at 3 MNQ.
- v2 (EDIT) was dropped at the user's request.
- **Breakout (crypto prop firm) sim lives in `Breakout/`.**
  - `breakout_sim.py` runs S08 on BTC with positions sized as a % of a $50K account. It sizes from the real BTC price (`data/btc_usd_daily.json`: Yahoo BTC-USD daily closes), because the back-adjusted file sits far above real prices before 2025.
  - It simulates Breakout 1-Step Classic/Pro/Turbo 50K evaluations, starting one on every flat day, plus a 1-year funded phase.
  - Costs: 0.04% fee per side, 0.033% daily swap, `--slip-pct`.
  - Results go to `Breakout/<--out>/`. The user had them wiped; rerun to regenerate.
- `BacktestEngine/charts.py`: SVG equity and drawdown charts, plus an `index.html` gallery. No plotting library is needed; matplotlib is not installed.
- **`LucidSim/` holds the Lucid simulation backtester** (separate folder, user's request).
  - `propsim.py`: the LucidPro 50K sim. `sizing` may be a callable balance -> contracts.
  - `sizing.py`: fixed sizes and the standard schemes (balance ladders, trend, calm vol, vol target, equity curve, bench).
  - `run_lucid.py`: the standard runner (below). `metrics.analyze` takes a per-trade qty callable and `i_to`.
    - `evaluate(b, trades, meta, spec, periods, whole, out, ...)` produces the standard report for any engine's trade list.
    - `write_outputs()` writes the CSVs, `summary.json`, the gallery, `tables.md` and `datasheet.html`.
  - `lucid_report.py`: builds `tables.md` and `datasheet.html` from any report folder. It adds an improvement grid if the folder has `improve.json`.
  - Vaultbreak scripts and `s08_tests.py` add `LucidSim` to their path.
- `LucidSim/run_lucid.py`: runs every sizing for every period. It writes:
  - `tables.md` and `datasheet.html`;
  - `stats.csv`, `lucid.csv`, `by_year.csv` and `summary.json` (with exit-reason counts);
  - `runs/*.json`;
  - `equity/<run>_<period>_{sizes,balance_schemes,market_schemes}.svg`;
  - `daily/*.csv` (end-of-day equity) and `trades/*.csv` (with MAE/MFE and exit reason).
  - `--out` takes a name under `results/` or an absolute path.
  - Folders written before 2026-10-31 have no `tables.md`; rerun them to get it.
  - Costs can be changed with `--commission` and `--slip-ticks`.
  - `--param key=value` overrides a strategy parameter, e.g. `--param lucid_flat=1` for S08.
  - `tf` 0 means session daily bars for S08.
  - S08 is Forecast-to-Fill (the user's arXiv:2511.08571 code).
    - With `lucid_flat=1` it flattens at 15:40 CT and re-enters at 17:00, like strategies 01–07.
    - Best result: NQ 60m.
    - Improvement options (defaults = original): `entry_thr` / `exit_thr` (e.g. 0.6 / 0.4), `slope_norm=atr`, `rth_only`.
      - The ATR slope does nothing on its own at 0.5 thresholds, because only the slope's sign matters there.
    - `BacktestEngine/s08_tests.py` (2026-10-30) runs tests A (Lucid-flat), B (overnight, Lucid rule ignored), C (improved) plus ablations.
      - Coverage: all timeframes, sizes 1–4 MNQ and 12 sizing schemes, each period.
      - Output: `results/s08_three_tests/`.
      - Best for Lucid: A 1h at 1 MNQ (pass 40.5%, $450 per evaluation).
      - C lifts PF but cuts trades about 90%, which collapses Lucid pass rates.
  - `--limit-fill through` makes limit orders need a trade one tick through their price. The default is MultiCharts' touch fill.
  - Specs exist for NQ/ES/GC/BTC micros. Strategy 04 has no point stops set for GC or BTC. Strategies warm up on data from 2016, but only trades entered from `--from` onward count. Default output: `results/lucidpro50k_<year>/`.

```bash
python -I LucidSim/run_lucid.py --only S08 --symbols NQ --tfs 60,240,0 --param lucid_flat=1 --out s08_std
```

Conventions:

- **Execution:** always on 1-minute bars. Market orders fill at the next bar's open. Stops and limits use the O-H-L-C or O-L-H-C intrabar path (whichever extreme is nearer the open comes first) and fill at the open on a gap. Stop and limit prices are rounded to the tick, against the trader.
- **Signal timeframe:** `tf` replaces the strategy's own signal bars, which are clock-aligned in CT. Strategies 03 and 07 use RTH daily bars, so `tf` does not affect them.
- **Size and costs:** one micro contract (MNQ on NQ data, MES on ES data); results scale linearly with size. Costs are $0.75 commission per side, plus 1 tick of slippage per side on market and stop fills (none on limit fills).
- **Strategy 04 on ES:** uses a quarter of the NQ point stops and targets (20/10 long, 20/12.5 short). Its 0.10% momentum filter is distorted by the back-adjustment, which makes it stricter in early years.

## Environment

Python 3.12 is installed without pandas or pyarrow. A full-file scan with the standard library takes about 1 minute per file.
