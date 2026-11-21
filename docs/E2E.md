# End-to-end check on XRPL Testnet

Last run: 21 Nov 2026, 01:44 to 01:50 CET, on the docker compose stack (api, worker, Postgres) built from `master` at T-013.

## What was run

1. A fresh stack (`docker compose down -v`, then `up --build`) with two accounts: `alice` (user) and `analyst` (analyst).
2. `make demo ARGS="--watch-user alice --auto-trace analyst"`. This is a real theft on Testnet: rekey, drain, split across three fresh mules, deposits at our exchange wallet under tag 777001.
3. `uv run --with playwright python scripts/e2e_browser.py --user alice:… --analyst analyst:…`. It signs in through the login form as each role, opens every page, flags a mule from the trace page as the analyst, and checks as alice that the flag shows up.

## Results

| Check | Result |
|---|---|
| Drain of 99.99997 XRP at ledger 22,485,782 | [9C004106…](https://testnet.xrpl.org/transactions/9C004106BB908901B1B328AD82272EA253D1EB2C116F1146553D1018A7EB4E) |
| Deposits at the exchange, tag 777001 | [4D847C23…](https://testnet.xrpl.org/transactions/4D847C23561D914AF102B963C31A30F24C293839C13CFFD42D0CDACC4F1900EC), [22A892C1…](https://testnet.xrpl.org/transactions/22A892C1F7A0971654D9AF81347D081E5413F3DF1614C552B3EA154363F1C8A0), [6BF03F43…](https://testnet.xrpl.org/transactions/6BF03F43C6EC73E88B0751AFC6EFACA90020A7C5BE4F63AD6F042677D370028C) |
| Trace edges against the ledger's own `tx` answer (sender, receiver, tag, `delivered_amount`) | 7 of 7 match |
| Amount attributed to the exchange | 95.59997 XRP, the exact sum of the three deposits (95.6% of the theft) |
| What's left on the attacker and mule accounts | 1.1 XRP each: the 1 XRP account reserve plus fee margin |
| Alice's notifications | key change, outgoing 99.99997 XRP, "Traced 95.59997 XRP … tag 777001" |
| Analyst findings | `possible_takeover` on the victim, `funds_funnel` on exchange:777001 |
| Flag set by the analyst, then looked up by alice | visible, with category and analyst name |
| Alice opening `/analyst/findings` | 403 |
| Browser console errors | none |

Screenshots: `artifacts/screenshots/` (`user-*` and `analyst-*`).

The victim's history also holds the earlier demo runs (each starts with a 100 XRP faucet top-up), which is why its balance chart shows several drains.

## How to repeat it

```bash
make setup                      # creates .env; set JWT_SECRET in it
docker compose up -d --build
docker compose exec api ixh26 create-user alice            # asks for a password
docker compose exec api ixh26 create-user analyst --role analyst
DATABASE_URL=postgresql+psycopg://ixh26:ixh26@localhost:5432/ixh26 \
  make demo ARGS="--watch-user alice --auto-trace analyst"
uv run --with playwright python scripts/e2e_browser.py --user alice:PASS --analyst analyst:PASS
```

On WSL machines where Python DNS lookups stall (IPv6), prefix the network commands with `RES_OPTIONS="timeout:1 attempts:1"`.
