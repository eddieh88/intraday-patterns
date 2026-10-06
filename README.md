# Do intraday chart patterns work?

YouTube and trading courses teach a common set of day-trading setups: buy the
breakout of the opening range, wait for price to break a level and come back to
"retest" it, trade "fair value gaps", watch for the "judas swing" at the open.
They're taught as if they work.

We turned each one into an exact rule and tested it on **1,435 trading days of
5-minute bars (2021–2026)**, using each day's 100 most-traded US stocks, chosen
from the previous 20 days' volume only — 439 different companies over the whole
period, including ones that were later delisted.

## The short version

- **The opening hour really is different.** Price moves **2.94×** as much per
  bar as at midday, and **35%** of the day's volume trades in 23% of the hours.
  That's the one claim that held up, and nobody disputes it.
- **The timing claims about the open failed.** The "false move" at the open
  reverses 50.5% of the time — a coin flip. Pre-market direction predicts the
  day 49.2% of the time. Also a coin flip.
- **The entry setups pick the right direction slightly more often than chance**
  — worth about **1–2 hundredths of a percent** per trade, before costs. Trading costs are
  3–6 hundredths. So none of it is profitable.
- **And that small edge isn't coming from the pattern.** A rule that ignores the
  chart and just asks "has price gone up or down over the last 30 minutes?"
  does exactly as well. The setups are a way of noticing momentum, not a source
  of it.
- **Futures and FX told the same story (September 2026).** Two NQ systems posted
  online failed on unseen data. Hourly FX does mean-revert, but by less than the
  spread on every pair we tested. Our own FX strategy, built on that reversion,
  made money before costs in every year from 2010 to 2026 and failed after
  costs on sealed 2010–2014 data.

## The story

### 1. Is the open special?

Every setup here is taught for the first hour or two of the trading day, so we
checked that first. It is: bars at the open are almost three times the size of
midday bars, and a third of the day's volume trades there. **Confirmed.**

### 2. The session-timing claims

A family of claims (much of it from "ICT" trading content) says the open follows
a script: an early false move that traps traders, then a reversal; the
pre-market range sets the day's direction; the opening range gets "swept" and
then reverses.

| claim | what happened |
|---|---|
| the early move is a fake-out that reverses | reverses 50.5% of the time — coin flip |
| the pre-market sets the day's direction | right 49.2% of the time — coin flip |
| the opening range gets swept, then reverses | the opposite: breaks tend to **continue** |
| opening gaps fill the same day | small gaps usually do (69%), big gaps usually don't (27%) |

### 3. Everything lost exactly the same amount — which was the clue

Next, the entry setups: break-and-retest of yesterday's high or low, and the
opening range breakout. We measure results in **R** — units of the amount
risked. Lose your stop and you're at −1R; hit a 3-to-1 target and you're at +3R.

Thirteen different strategies all came back between **−0.07R and −0.14R**.
Different setups, different exits, same answer. That's not what real
differences look like, so we went looking for the cause and found it in our own
setup. The stops were so tight that **trading costs alone** accounted for the
loss: the same 2bp cost is 0.135R on a very tight stop, and 0.034R on a normal
one. We had built the same penalty into every test.

We'd also been fooled by our own detector. **73% of the "retests" it found were
just the bar right after the breakout** — not price moving away and coming back.
Nobody would call that a retest, and nothing in the statistics showed it.
Plotting six real examples did.

### 4. A fair comparison is harder than it looks

With that fixed, the real question was: does entering on a setup beat entering
at a **random** moment? Getting a clean answer took several tries, because each
comparison turned out to be subtly unfair:

- Testing **long trades only** mostly measured whether the market went up in
  2021–2026. It did.
- On a day that trends up, the setups fire more long signals than short ones.
  Averaging all trades therefore leaned toward whichever side the day rewarded,
  which flattered the setups for reasons that had nothing to do with skill.
- Our random comparison trades were sometimes drawn from **before** the setup
  fired, so they caught the very move that created the setup.
- **The list of stocks was picked with hindsight.** "Most traded" was first
  measured over the whole five years, so a stock that only became popular in
  2024 was already on the 2021 list. On a typical day about one name in ten
  was wrong. Rebuilt using only each day's past volume, every result moved by
  less than 0.003R and every conclusion held.

The final design pairs each real trade with a random entry in the same stock,
same day, same direction, same risk, a few bars later. Entries are filled at the
**open of the next bar** — the first price you could actually trade at after
seeing the signal.

### 5. The answer: right direction, no timing, too small to pay

With a fair comparison, the setups do pick the right **direction** a little more
often than chance — worth **0.7 to 2.1 hundredths of a percent**. After
correcting for testing four setups at once, only one (the pullback) is
convincingly above zero.

But the **timing** adds nothing. Entering at the setup is no better than
entering a few bars later in the same direction. And realistic trading costs
are 3–6 hundredths of a percent, well above the edge.

### 6. It's just momentum

If the setup picks direction but not timing, maybe it's only telling you which
way price has already been moving. So we compared each setup against a rule
that ignores the chart entirely — same entry bar, same stop, same target, but go
long if price is up over the last 30 minutes and short if it's down. Both are
measured on exactly the same trades.

| setup | setup's result | momentum rule | difference |
|---|---|---|---|
| pullback after a run | +0.0249R | +0.0189R | +0.0060 (not significant) |
| opening range breakout | +0.0188R | +0.0188R | **exactly 0** |
| VWAP reclaim | +0.0210R | +0.0207R | +0.0003 (not significant) |
| break and retest of a level | +0.0129R | +0.0077R | +0.0052 (not significant) |

**No setup beats the momentum rule.** The opening range breakout is exactly
equal on every single trade, because an upward break of the opening range *is*
price going up — the two rules always pick the same side. **The opening range
breakout is a momentum rule with a line drawn on the chart.**

### 7. Can anything at 09:45 pick the good mornings?

If direction is just momentum, the useful question is *when* momentum pays. So
we took the plainest possible trade — at 09:45, go with the first fifteen
minutes; exit by 11:00 — and asked whether about 25 things visible at 09:45
(the gap, pre-market and opening volume, whether SPY and the sector agree, room
to the next level, volatility regime, FOMC and other calendar days) could pick
out the mornings where it works.

It was registered in advance, tested only on months the model had never seen,
and a hidden final period was sealed in code.

**They can't.** Out of sample the predictions ranked mornings no better than a
coin — a rank correlation of 0.003. A more flexible model (LightGBM) did no
better; it chose to stop after one to nine trees, having found nothing to learn.
The best-rated fifth of mornings lost money after costs under both models.
Details in [selection/RESULTS.md](selection/RESULTS.md).

### 8. Do levels hold on the retest?

A common version of the support/resistance claim: price hits a level, moves
away, and when it comes back — from either side — it bounces. We tested it on
prior-day, two-days-back and pre-market highs and lows, against a **fake level**
at the same distance from the open run through identical code.

Before touching real data, the detector ran on simulated random walks, where
levels mean nothing. That caught a flaw: measuring from the level price
manufactured a pass-through, and even made a fake result look significant. The
outcome was changed before any real data was read.

**They don't.** Across 187,000 retests, real levels held 50.2% of the time and
fake ones 50.3%. The difference is +0.24bp over the next hour, with a 95%
interval of −0.35 to +0.84bp. No level type, and neither support nor
resistance, stands out. Details in [retest/RESULTS.md](retest/RESULTS.md).

### 9. Beyond stocks: NQ futures and FX

The same approach, applied to strategies that traders posted on X, and to our own.

| what | result | where |
|---|---|---|
| A long-only NQ dip-buying system, as posted | Loses on unseen data. Before costs it makes exactly zero; its 57% win rate comes from the bracket's geometry, not from an edge | [explore_nq/](explore_nq/NOTES.md), [prereg](prereg/nq_mean_reversion.md) |
| The same author's NQ "Lunch Box" range fade | Fails: price reaching the edge of a quiet range usually breaks through | [prereg](prereg/nq_lunch_box.md) |
| Reverse-engineering a one-rule FX strategy from its author's chart and Darwinex statistics | The rule's shape was established: trades in groups on the hourly bar, a fixed close at 17:00 New York, a ~30-pip stop, mostly scratches. The exact rule was not | [explore_fx/](explore_fx/NOTES.md), [prereg](prereg/fx_distance_fade.md), [prereg](prereg/fx_night_scalper.md) |
| A StrategyQuant-style generator: 86,400 rules on 8 spot FX pairs, at real bid/ask, against shuffled data | Before costs, hourly FX mean reversion is real: persistence beats shuffled data. It is smaller than the spread on every pair | [explore_own/](explore_own/NOTES.md) |
| Our own FX strategy: fade a 0.4% dollar move after the 17:00 New York open, on EURUSD, AUDUSD and NZDUSD | **Fails** on sealed 2010–2014 data: −30 bp/yr net. Gross it is +237 bp/yr, positive in every year from 2010 to 2026. It lives on a few big reversals a year | [prereg](prereg/own_fx_basket.md) |

The FX data is HistData spot tick quotes (bid/ask), reduced to one-minute bars. Its
timestamps are New York local time with daylight saving, not EST as documented. Within
this repo, 2010–2014 was sealed until the one test above.

### 10. A YouTube strategy, rebuilt from its creator's own live trade

The "silent flip": on 15-minute candles, a strong opening candle runs into yesterday's
high or low (or the next swing beyond), the next candle turns against it, and you fade
the move toward the other side of yesterday's range. The video shows one live trade.

We found that trade's date in the data. His chart's timestamp and Yahoo's prices match
to the cent: **3 September 2026**. Rules rebuilt from that morning reproduce his calls
exactly: they short UBER at 77.78 with the stop at 78.48 (his 78.50) and the target at
75.36, and they skip the four stocks he skipped.

| | result |
|---|---|
| The rules as first written (877 trades, 2021–25) | −0.037R after costs, zero before. Levels taken from a random other day do as well |
| Rebuilt from his trade (1,388 trades) | −0.036R after costs, zero before. Fake levels again do as well |
| 11 ways of moving the stop, including trailing it as he did | All negative (−0.016R to −0.041R). None beats the same exits on fake levels |
| Waiting for the third candle to confirm | Worse (−0.11R): the move happens before the confirmation can be seen |
| Only the cleanest form, a push from inside yesterday's range into the level | Breaks even after costs (−0.007R), no better than fake levels |

Before any real data was read, a random-walk check of each version caught two problems
in our own controls, recorded as amendments: error bars that were too narrow, and a
random-entry control that could see the future. The holdout stays sealed, because nothing
passed. Details: [prereg/silent_flip.md](prereg/silent_flip.md),
[prereg/silent_flip_v2.md](prereg/silent_flip_v2.md), [flip/figures/](flip/figures/).

### 11. Can a model find what drives the hour after the opening range?

LightGBM was asked to rank each day's top 100 stocks by their 10:00–11:00 return, using
50 features known at 10:00:
- the opening half hour, the overnight gap, and the same hour on earlier days
- recent days' returns, distance to yesterday's levels, volatility and size
- macro moves: ES, NQ, Russell, rates, the dollar, the yen, oil, gold, VIX and bitcoin
- each stock's sensitivity to those moves, and its sector

Walk-forward over seven half-year blocks from 2022 to 2025, with a leak test that fails
the build if any feature sees 10:00.

| | IC | before costs | after 6 bp a day |
|---|---|---|---|
| LightGBM, settings fixed in advance | +0.011 (t 1.1) | +4.3 bp/day | −1.7 |
| LightGBM, tuned properly over 162 settings | +0.009 | +0.6 bp/day | −5.4 |
| one feature, the stock's volatility (long the calmest fifth, short the most volatile) | +0.026 (t 1.9) | +6.6 bp/day | +0.6 |

- **The model had nothing durable to learn.** Its training fit rose to 0.40 while the
  out-of-sample IC stayed near 0.01, and tuning made it no better.
- **The only stable driver is volatility:** the most volatile stocks lag in that hour.
  It is the top feature in every block. It has faded from −12 bp for the most volatile
  tenth in 2021 to about zero in 2024, and it is about the size of trading costs.
- **The other apparent drivers are the same effect.** The macro context adjusts how
  much volatility matters, and yesterday's extreme movers are the volatile stocks.
  Neither adds anything to a simple OLS once volatility is in it.
- **No driver changes measurably across years or regimes:** volatility, market trend
  or rates.

Nothing passed, so the holdout stays sealed. Before costs these effects have Sharpe
ratios of about 0.6–0.75, like slow futures trend rules. But a book traded every day
pays roughly 15% a year in costs, and three years cannot prove an edge that size.
Details: [prereg/opening_ml.md](prereg/opening_ml.md).

## One pattern claim did check out

**Fair value gaps fill at roughly the rates people say they do.**

| | we measured | published |
|---|---|---|
| price comes back to touch the gap | 78.7% | 74.6% |
| fills it halfway | 68.4% | 61.2% |
| fills it completely | 46.1% | 48.7% |

The geometry is real. Trading it (break of structure → gap → entry on
the tap) did no better than a random entry: −0.109R against −0.121R. Both
numbers were measured before the cost fix in part 3, so both carry the same
artificial penalty — the comparison between them is what counts.

## What this test can't see

- **News.** One strategy we tested says: never trade on news days, only after.
  We have no news calendar, so we couldn't test that version.
- **Index futures, partly.** The stock tests above don't cover ES, NQ or SPY,
  where most of these setups are taught. Two NQ systems were tested later
  ([part 9](#9-beyond-stocks-nq-futures-and-fx)); the setups from parts 1–8 were
  not rerun on futures.
- **Order flow.** We see 5-minute price bars only — not the order book or
  individual trades.
- **The level's real job, now tested.** If a support/resistance line tells you
  *where to put your stop* rather than *which way to trade*, a stop at the level
  should beat one of the same width placed anywhere. It did, by about a hundredth
  of an R in development, but the one setup that cleared the pre-registered bar
  (VWAP) was zero in the holdout, and no setup pays after costs with its
  structural stop. See [prereg/structure_stops.md](prereg/structure_stops.md).

## Where to go next

| | |
|---|---|
| **[FINDINGS.md](FINDINGS.md)** | The full record: every claim, method, correction and limitation |
| [experiments/](experiments/) | One script per claim, with an index mapping each to its result |
| [note/open-tests.html](note/) | The same story written for an experienced day trader, definitions first |
| [note/setups.html](note/setups.html) | Every setup drawn as a candlestick example, with the rule as coded and the verdict |
| [figures/](figures/) | Charts per experiment, and rendered examples of what the detector found |
| [selection/](selection/) | The 09:45 selection study: features, leak audit, results |
| [retest/](retest/) | Do levels hold on the retest: detector, random-walk check, results |
| [prereg/](prereg/) | Rules written before the tests — one (inverse fair value gaps) not yet run |
| [explore_nq/](explore_nq/NOTES.md) | NQ futures: the posted dip-buying system, taken apart, and the Lunch Box |
| [explore_fx/](explore_fx/NOTES.md) | FX: reverse-engineering a posted one-rule strategy, the forensics, the searches |
| [explore_own/](explore_own/NOTES.md) | Our own FX strategy work: spreads, the generator, what the edge is |
| [flip/](flip/) | The silent flip: simulator, random-walk checks, exit sweep, sample sheets and figures |
| [ml/](ml/) | The opening-hour ML study: feature builder with a leak test, walk-forward, driver and regime analysis, tuning, OLS |
| [lib/](lib/), [data/](data/), [render/](render/), [diagnostics/](diagnostics/) | Shared code, data download, chart rendering, one-off checks — each with its own README |

## Words used here

| term | meaning |
|---|---|
| **R** | Profit in units of what you risked. −1R is a full stop-out; +3R is a 3-to-1 winner. |
| **bp** | Basis point: one hundredth of a percent. |
| **opening range breakout (ORB)** | Trade in the direction price breaks the 9:30–10:00 high or low. |
| **break and retest** | Price closes through yesterday's high/low, moves away, comes back to touch it, then continues. |
| **VWAP reclaim** | Price closes back above the day's volume-weighted average price after being below it. |
| **pullback** | After a run of more than 0.5% from the open, enter on the first bar against the run. |
| **fair value gap** | A three-candle pattern where the first and third candles don't overlap, leaving a gap. |
| **ICT** | "Inner Circle Trader", a popular trading-education brand whose session-timing ideas we tested in part 2. |

## Running it

Run from the repository root:

```bash
pip install -r requirements.txt       # dependencies + the shared modules in lib/
git config core.hooksPath hooks        # once: secret scan and tests before each commit
python3 -m pytest -q                   # unit tests (no data needed)
python3 data/mp_fetch.py stock_5min    # download the 5-minute archive
python3 data/build_daily.py            # build the shared daily table and the universe
python3 data/universe_check.py         # fails if the universe ever uses future data
python3 experiments/e18_momentum.py    # the momentum comparison
```

A MarketParquet key is expected at `~/.market_parquest/api_key.txt`, never in
the repo; the pre-commit hook in `hooks/` scans for it. The archive is ~24 GB —
if you already have it, `ln -s /path/to/cache cache` instead.

## Related repositories

| repository | question | answer |
|---|---|---|
| [**statarb-replication**](https://github.com/eddieh88/statarb-replication) | Does deep-learning stat arb replicate, and does it still work? | Replicates. Does not survive past 2016. |
| [**characteristic-factors**](https://github.com/eddieh88/characteristic-factors) | If prices alone stopped working, do models built on company fundamentals do better? | No. What they found was market exposure. |
| **this one** | Do the chart setups taught in trading education work? | No. Every edge they have is plain momentum. |
