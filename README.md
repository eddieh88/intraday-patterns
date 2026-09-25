# Do intraday chart patterns work?

Eighteen mechanical tests of the setups taught in retail trading education —
opening range breakouts, break-and-retest of prior-day support and resistance,
fair value gaps, break of structure, ICT-style session logic — on **1,425
sessions of 5-minute bars, 2021–2026, 200 names selected point-in-time.**

## The answer

**One claim survived. It is the one nobody disputes.**

> The opening hour really is different: its bar range is **2.94× midday**, and
> **35% of the day's volume trades in 23% of its hours.**

**Every directional claim failed, and the last test explains why.**

Four entry rules each carry a small positive directional edge — they pick the
right side slightly more often than chance, worth **+0.7 to +1.9 bp of price,
gross.** Realistic all-in cost is 3–6 bp, so none of it is payable. But the
size was never the interesting part:

```
side from the pattern   vs   side from the sign of the last k bars
(same entry bar, same stop, same 3R target, same costs)

entry      pattern   mom k=6   pattern - mom6       t
pullback   +0.0210   +0.0183          +0.0057   +0.90
ORB        +0.0198   +0.0198          +0.0000     n/a
VWAP       +0.0148   +0.0215          -0.0029   -0.59
level      +0.0086   +0.0084          +0.0040   +0.33
```

**No pattern beats a rule that ignores the chart and looks only at whether
price has gone up or down for thirty minutes.** The edge is generic opening
continuation. The patterns are ways of noticing it, not sources of it.

**ORB's zero is exact, and it is the sharpest result here.** Its t is undefined
because the difference is identically zero on *every* trade: an upward
opening-range break *is* a positive sign of the recent move, so the momentum
rule picks the same side every time. ORB is a momentum rule with a level drawn
on top of it.

Timing adds nothing either: entering at the signal is indistinguishable from
entering a few bars later, on all four entries.

## Where to read the findings

| | |
|---|---|
| **[INTRADAY_LOG.md](INTRADAY_LOG.md)** | **Start here.** Every claim, how it was measured, every correction, all limitations. |
| [FINDINGS_intraday.md](FINDINGS_intraday.md) | The earlier pre-registered intraday tests (A and B). |
| [figures/](figures/) | One chart per experiment, plus rendered detections used to check the detector by eye. |
| [PREREG_orb.md](PREREG_orb.md), [PREREG_bos_fvg.md](PREREG_bos_fvg.md), [PREREG_ifvg.md](PREREG_ifvg.md), [PREREG_intraday.md](PREREG_intraday.md) | Pre-registrations, written before the runs. `PREREG_ifvg.md` is written and **not yet run.** |
| [LITERATURE.md](LITERATURE.md) | What the academic record already says. |

## The scoreboard

| # | Claim | Result | Verdict |
|---|---|---|---|
| E1 | The open differs from the rest of the day | 2.94× midday range; 35% of volume in 23% of hours | **Confirmed** |
| E2 | Opening gaps fill | 69% for gaps <0.2%, 27% for gaps >2% | Size-dependent |
| E3 | The opening move is a false move (PO3 / judas) | 50.5% reversal vs 50.0% coin flip | Null |
| E4 | The opening range is swept, then reverses | breaks continue; fading loses 5.7 bp | Refuted |
| E5 | Pre-market sets the day's direction | 49.2% same-direction; the high-sweep rule inverts | Refuted |
| E6 | Prior-day S/R break, then retest | −0.073R across two stop definitions | Negative |
| E7 | ORB on high relative-volume names | +0.009R; prereg needed +0.05 | Exploratory |
| E8 | The exit rule is what decides it | 7 policies within 0.04R, all negative | Refuted |
| E9 | *Descriptive:* what trades actually do | losers peak bar 1–7, winners bar 40 | — |
| E10–E10f | Structured entries beat a random bar | direction +0.7 to +1.9 bp gross; timing nothing | Real, unpayable |
| E12 | FVGs fill at the published rates | 78.7 / 68.4 / 46.1% vs 74.6 / 61.2 / 48.7% | **Replicates** |
| E13 | Break of structure → FVG → tap entry | −0.109R; random entry −0.121R | Negative |
| E15–E17 | Direction and timing, matched placebo | direction positive, timing zero | See log |
| **E18** | **The pattern beats naive momentum** | **it does not, on any entry** | **Refuted** |

## Ten errors, and what caught each

The corrections are the most reusable thing in this repo, and
[INTRADAY_LOG.md](INTRADAY_LOG.md) records all of them. The pattern in *how*
they were caught matters more than any single result: **five of ten were
spotted because a number was far larger than its mechanism could explain.**

A few worth naming:

- **73% of "retests" were the next bar.** The detector took the first bar whose
  low touched the level — usually the bar right after the breakout. Caught by
  rendering six real detections and looking at them.
- **Stops so tight that friction looked like failure.** Thirteen strategies all
  returned −0.07 to −0.14R. That convergence was the tell: the same 2 bp round
  trip costs −0.135R on a half-bar stop and −0.034R on a two-bar stop.
- **A look-ahead in the placebo arm.** Placebos drawn *before* their signal
  enter ahead of the breakout and capture the move that defines it — they earn
  +0.67R against the signal's −0.08R.
- **Two numbers that were never the same statistic.** Two ORB figures disagreed
  in sign (−0.0700 vs +0.0198). The first explanation was wrong; the real cause
  was that one traded long breaks only, net of costs, on a tenth of the sample.
  With both sides in, ORB's clustered standard error is *larger than the gap
  being argued over* — it was never significant in either direction.

## What this test cannot see

- **No news calendar.** One tested strategy says explicitly: never trade during
  news, only after. We cannot filter on that at all.
- **Single stocks, not indices.** 199 of 200 names are individual stocks; these
  setups are overwhelmingly taught on ES, NQ and SPY. Futures data is
  downloaded and **not one test has been run on it.**
- **No tape.** 5-minute OHLCV only — no order flow, no depth, no prints.
- **The entry rule may be the wrong object.** If the level's job is to set the
  *risk unit* rather than the direction, every test here aims at the wrong
  target. Untested.

## Running it

```bash
pip install -r requirements.txt
python3 data/mp5_fetch.py          # MarketParquet 5-minute archive -> cache/mp5min/
python3 intraday_build.py          # one daily summary table -> cache/intraday_daily.parquet
python3 e18_momentum.py            # the decisive test
```

Scripts read `cache/` relative to the repo root and expect a MarketParquet key
at `~/.market_parquest/api_key.txt`, **never in the repo** — the pre-commit
hook in `hooks/` scans for it. Enable with `git config core.hooksPath hooks`.

No market data is redistributed here; `cache/` is gitignored.
