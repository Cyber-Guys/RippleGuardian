# Context: what we are building and how we got here

Read this first if you are joining the repo, whether you are a teammate or an agent. It explains the idea, which parts of the first plan we dropped and why, and the words we use. The rules for working in the repo are in [CLAUDE.md](../CLAUDE.md); the decisions with dates are in [DECISIONS.md](DECISIONS.md).

## The problem

When someone steals an XRPL wallet's seed, the theft usually follows the same pattern. The thief adds a signing key of their own (`SetRegularKey` or `SignerListSet`), empties the wallet in one payment, splits the money across a few new accounts, and deposits it at an exchange. On XRPL the deposit carries a destination tag, which is how the exchange knows which customer account to credit. Whoever holds that tag is the person the exchange can identify.

Tracing tools exist, but they are sold to exchanges and law enforcement. The person who lost the money usually finds out late and has nothing to hand to anyone.

## The idea, as first proposed

The team's starting idea (Friday evening) had these parts:

1. A program listens to new ledger transactions and flags suspicious transactions and accounts.
2. Owners get a notification when something happens to their wallet, through a web app that maps wallets to email addresses.
3. Two explorers: a simple one for normal users, and one for forensic analysts.
4. Analysts use the haircut taint method to follow stolen funds, and can flag wallets and transactions.
5. Users see only their own wallets (analysis, statement, notification settings) and the accounts analysts flagged. The detection algorithms stay on the analyst side.

## What changed, and why

An outside review on Friday night was blunt: as described, the project was a block explorer with labels and an email service. It used XRPL only as a data source, the two explorers were one app with two permission levels, flags from anonymous analysts had no accountability, and a notification after the money is gone does not help much.

The team decided to keep the detector idea and change the rest:

| First plan | Now | Why |
|---|---|---|
| Two explorers | One web app with a `user` and an `analyst` role | One thing to build and demo. The split is a permission check, not a second product. |
| Email notifications, wallet-to-email map | In-app notifications only, accounts are a username and a password | No personal data to store or protect. |
| Notifications about "other wallets doing exchanges" | Notifications on (a) a key change, (b) an outgoing payment above the owner's threshold, (c) any contact with a flagged account, and (d) stolen funds traced to a known exchange | The original wording was ambiguous; these are the four cases an owner can act on. |
| Flags from analysts | Flags carry the analyst's username, a category and a reason, can be revoked, and are public to every user | Accountability: a wrong flag is visible and attributable. |
| Detection on every transaction of the ledger | Detection on the history of watched wallets and of the accounts a trace visits | The public Testnet node keeps about two hours of history and we have one night. |
| Owners only see what happened | Owners get a status in plain words and a numbered list of what to do now | The goal is that someone who was just robbed knows their next step. |

The review also suggested using XRPL's own tools to get money back: an issuer can freeze a trust line or claw back its tokens, and our trace is exactly the evidence an issuer needs. The team chose not to build that during the hackathon. It is the first item on the roadmap.

## What exists now

- A worker that subscribes to watched wallets over WebSocket, catches up with `account_tx` polling, stores every transfer and key change, sends alerts, runs the detectors, and runs trace jobs.
- A haircut taint tracer that follows stolen XRP hop by hop, takes each account's clean balance into account, and stops at labelled entities such as exchanges, reporting the destination tag.
- Four detectors (T-006). Two of them, possible takeover and funds funnel, fire on live data. The other two need DEX and AMM data we don't read yet.
- A web app. Users see a status for each wallet, a balance chart, history, notifications, per-wallet alert settings and a page to check any address against the flags. A robbed owner gets a four-step recovery screen, can request a trace and downloads a PDF incident report. Analysts see an overview with counts, the findings queue, traces drawn as an animated hop graph (hovering an account highlights its money path), and the flags page.
- A Testnet demo that performs a real theft and launders it through two relays and five mules into two exchanges, and an end-to-end check that compares the app's numbers with the ledger ([E2E.md](E2E.md)).

## Glossary

Drops
: XRP's smallest unit; 1 XRP is 1,000,000 drops. The code stores XRP in drops as `Decimal`, never as float.

delivered_amount
: What a payment actually delivered, from the transaction metadata. A "partial payment" can ask for 1,000 XRP and deliver 0.01, so we never read the requested `Amount`.

Destination tag
: A number attached to a payment that tells the receiver, usually an exchange, which customer account to credit.

Regular key
: A second key pair that can sign for an account. Adding one is the quickest way for a thief to keep control, so `SetRegularKey` is an alert.

Haircut taint
: When an account holds some stolen and some clean funds, every payment out of it carries stolen funds in the same proportion. We follow those proportions hop by hop.

Sink
: Where a trace ends: an account that kept the stolen funds, or a labelled entity such as an exchange, split by destination tag.

Finding
: A detector's signal, with the transactions behind it. Only analysts see findings, and a finding is a lead to review, not a verdict.

Flag
: An analyst's public statement that an account or a transaction is suspicious, with a category and a reason. Every user can see flags.

Cursor
: The last ledger the worker has fully read for a wallet. The sidebar's live indicator shows the highest one.

SIMULATED
: Anything that isn't real ledger data. It is marked in the code with `# SIMULATED:` and shown as such in the app.

## Where to start in the code

- `src/ixh26/contracts.py` holds the types every module shares (`Transfer`, `SecurityEvent`, `Alert`, `TraceResult`). Change them only through a contract task.
- `make smoke` runs the whole path offline in a few seconds. `flows/smoke.py` is the shortest readable version of the product.
- Tasks live in `tasks/`. Claim one on `master` before you start, as described in CLAUDE.md section 2.
