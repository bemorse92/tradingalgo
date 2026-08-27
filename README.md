# tradingalgo

Python trading algorithm project. Stack (backtesting framework, broker/data APIs) TBD.

## Setup

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
```

## Layout

- `strategies/` — trading strategy implementations
- `backtest/` — backtesting harness and results
- `data/` — market data (gitignored; not committed)
- `tests/` — unit tests
