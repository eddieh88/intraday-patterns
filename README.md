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
- **Index futures.** Almost all of these setups are taught on ES, NQ and SPY. We
  tested individual stocks. The futures data is downloaded; **no test has been
  run on it yet.**
- **Order flow.** We see 5-minute price bars only — not the order book or
  individual trades.
- **The level's real job.** If a support/resistance line is meant to tell you
  *where to put your stop* rather than *which way to trade*, we've been testing
  the wrong thing. That's untested.

## Where to go next

| | |
|---|---|
| **[FINDINGS.md](FINDINGS.md)** | The full record: every claim, method, correction and limitation |
| [experiments/](experiments/) | One script per claim, with an index mapping each to its result |
| [note/open-tests.html](note/) | The same story written for an experienced day trader, definitions first |
| [figures/](figures/) | Charts per experiment, and rendered examples of what the detector found |
| [prereg/](prereg/) | Rules written before the tests — one (inverse fair value gaps) not yet run |
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
pip install -r requirements.txt
python3 data/mp5_fetch.py              # download the 5-minute archive
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
