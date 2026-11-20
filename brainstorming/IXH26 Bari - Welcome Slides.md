# IXH26 Bari - Welcome Slides

20-21 Nov 2026 · University of Bari Aldo Moro
Organised with UBRI · De Cifris · University of Trento · University of Bari Aldo Moro

---

## Welcome to IXH26

Two days of cryptography, blockchain and building on the XRP Ledger.

### Welcome notes

- **Roberto La Scala**, University of Bari
- **Carlo Brunetta**, De Cifris
- **Vera Radeva**, XRPL Commons

---

## XRPL Commons: who we are

Our mission is to create the **conditions of success** for builders, entrepreneurs and developers to thrive in the XRPL ecosystem.

| # | Pillar | What it does |
|---|--------|--------------|
| 01 | Learn | Trainings and the XRPL Academy, for tech and business roles. |
| 02 | Build | Hackathons and developer trainings: a playground for invention. |
| 03 | Launch | The Aquarium Residency turns ideas into live products. |
| 04 | Adopt | Tailored support for corporates and institutions using XRPL. |
| 05 | Engage | Meetups, podcasts and our Community Magazine unite the ecosystem. |

**60+** universities worldwide focused on accelerating research & development.

---

## Agenda: two days in Bari

### Friday 20 Nov

Dept. of Mathematics · workshops in Informatics

| Time | Event | Type |
|------|-------|------|
| 10:00 | Registration and check-in | Check-in |
| 11:00 | Welcome and instructions | Talk |
| 12:00 | **Hacking starts** | Hack |
| 13:00 | Lunch | Food |
| 14:00 | Cryptography workshop | Workshop |
| 15:00 | XRPL workshop | Workshop |
| 17:00 | Hack the Mentor | Mentors |
| 18:00 | Dinner, then hack all night | Food |

### Saturday 21 Nov

Department of Informatics

| Time | Event | Type |
|------|-------|------|
| 09:00 | Breakfast | Food |
| 12:00 | **Final project submission** | Deadline |
| 12:30 | Project pitches | Pitch |
| 13:30 | Lunch | Food |
| 14:30 | Jury deliberation | Jury |
| 15:30 | Winners ceremony | Ceremony |
| 16:30 | Celebration and group photo | Social |
| 18:00 | End of the hackathon | Close |

---

## Tracks & prizes: three tracks, €12,000 in prizes

One project per team, in one track. Pick your track on-site. Teams of 3 to 8 people.

| | Track 01: Advanced Cryptography | Track 02: XRPL Applications | Track 03: Tokenisation on XRPL |
|---|---|---|---|
| Focus | Encryption, zero-knowledge proofs, digital signatures and other privacy tech for blockchain. | Integrations, apps, DeFi or smart contracts that use the XRP Ledger in a creative way. | Tokenise digital or real-world assets: issuance, ownership, management or compliance. |
| 1st place | €2,000 | €2,000 | €2,000 |
| 2nd place | €1,200 | €1,200 | €1,200 |
| 3rd place | €800 | €800 | €800 |

---

# Track 1: Advanced Cryptography for Blockchain

A track by **De Componendis Cifris**.

## The people behind the track

- **Carlo Brunetta**: Researcher, ShunyaXifra
- **Federico Pintore**: Assistant Professor, Department of Mathematics, University of Trento (IT)
- **Massimiliano Sala**: Full Professor, Department of Mathematics, University of Trento (IT); De Componendis Cifris, President

## Crypto track · ingredients

**Cryptography** + **Blockchain technology** + **Digital provenance**

## The problem: the synthetic reality dilemma

- Generative AI models produce photorealistic images, which are **indistinguishable from genuine camera captures**.
- **And** modern cameras already post-process every image.

→ **A possible solution:** cryptographic guarantees of physical origin.

## 01 · Example: Apple Reference Image (a non-blockchain example)

Something concrete and close to a solution, but **centralised**: no decentralisation, no distribution, so weak to a single point of failure.

### Main actors

Inside the mobile device (hardware bound):

1. **Photo sensor**: silicon chip signing raw pixels at light capture.
2. **Secure Enclave (SEP)**: isolated security chip holding keys and hardware attestation.

Outside the device:

3. **Private Cloud Compute (PCC)**: a privacy-preserving cloud, which executes verifiable operations on confidential data.
4. **Further Apple services**: centralized RFC 3161 timestamping and key revocation servers.

### Initialization & device manifest (factory provisioning)

1. **Photo-sensor keys**: generates an ECDSA key pair coupled with a certificate from **CA 1**.
2. **Secure-Enclave (SEP) keys**: produces its own key pair certified independently by **CA 2**.
3. **Signed device manifest**: keys and certificates are bundled into a device manifest signed by **CA 3**.

**Hardware binding:** this triple-certified device manifest permanently binds the specific camera sensor silicon to the device's Secure Enclave before leaving the factory.

### Phase 1: creating a secure digital negative (capture)

0. **Lower-bound timestamp T₀**: signed timestamp tokens are regularly delivered to the device. The most recent one, T₀, is cached.
1. **Sensor reboot & pre-capture input**: the sensor reboots into a secure mode and accepts only one external input: the digest of T₀, Device Manifest and Secure Boot Manifest (the OS/firmware state was untampered at boot).
2. **Sensor raw capture & signature**: the photo sensor produces the raw frame and places the received digest into a slot of the frame's internal metadata. It produces an ECDSA signature σₛ on the raw frame and metadata.
3. **SEP binding**: the SEP signs a digest of σₛ combined with OS-captured metadata, producing σₑ.
4. **Upper-bound timestamp T₁**: the device sends SHA-256(σₑ) to Apple's timestamp service to obtain a signed T₁ receipt.
5. **DNG packaging**: raw frame, σₛ, σₑ, time window [T₀, T₁], metadata and manifests are bundled into a DNG file (digital negative).

### Phase 2: creation of the reference image (off-device attestation)

1. **Verification**: PCC verifies digests, signatures, CA chains and same-device SEP-sensor binding.
2. **JPEG generation**: PCC runs the verified raw frame through its image pipeline to produce the JPEG.
3. **Confidence score**: PCC computes an authenticity score of sensor and pipeline integrity.

- **Hybrid PQ signature:** the digest of the JPEG and its metadata is signed with a hybrid post-quantum signature (ML-DSA-87 + RSA-3072), embedded in the JPEG file.
- **Revocation alert:** verification relies on Apple's central Certificate Revocation Lists. If a sensor or CA key is revoked or the central server is unreachable, attestation fails.

### Who does what, and when

Rows are actors, time flows left to right.

| Actor | Factory | Phase 1 · Capture | Phase 2 · Attestation |
|-------|---------|-------------------|-----------------------|
| CAs (factory) | CA 1 · CA 2 · CA 3 issue certificates | | |
| Photo sensor | key · CA 1 | frame + σₛ | |
| Secure Enclave | key · CA 2 | sign → σₑ (over H(T₀, manifests) and σₛ) | |
| Device OS | manifest · CA 3 | cache T₀; SHA-256(σₑ); assemble DNG file | reference JPEG |
| Apple servers | | token T₀; receipt T₁ | CRL check |
| PCC (cloud) | | | verify · score; JPEG + PQ signature |

### Cons of a centralised system

- **Single point of failure:** Apple maintains central revocation lists. A compromised CA invalidates millions of devices.
- **Cross-platform lock-in:** non-Apple devices cannot natively verify claims without relying on Apple servers.
- **Retroactive censorship:** historic photos become unverifiable if central servers shut down or alter public keys.

## 02 · The hackathon challenge: Universal Photo-Origin Validation Protocol

**Architectural scope:** design a secure protocol that generalises to **any device** and guarantees **authentic photo origin** via **decentralised blockchains** technology.

## The rules: you can use

- **Anything you find on the Internet**, not subject to copyright limitation for non-profit use.
- **Any cryptographic primitive/protocol**, such as:
  - Standard public/symmetric keys
  - Functional/searchable encryption
  - (Fully) homomorphic encryption
  - Secure multiparty protocols
  - Any other advanced cryptosystem...

**Reference:** Apple Reference Image documentation: <https://security.apple.com/blog/apple-reference-image>

## You can use AI: allowed with full transparency

You are free to use any AI software (LLMs, code assistants, visual generators), but you **must explicitly declare** which tool was used, how, and where:

- **Solution design & code generation:** specify approaches, algorithms or smart contracts generated via AI.
- **Documentation:** declare assistance in writing specifications or slides.
- **Pitch preparation:** detail AI involvement in slide creation or speech drafting.

## Evaluation: how we rate your work

1. **Effectiveness:** solution quality, blockchain interaction and closeness to real-world deployment.
2. **Crypto vision:** novelty and soundness of crypto ideas vs feasibility.
3. **The pitch:** clarity of presentation, defense and vision.

Mentors and judges:

- PhD Andrea Gangemi (ShunyaXifra)
- Gabriele Radici (University of Trento)
- PhD Francesco Romeo (University of Cassino)
- Prof. Roberto La Scala (University of Bari)

## Good luck to all IXH26 teams!

For any doubt, ask the IXH mentors!
Organised by De Componendis Cifris · <https://www.decifris.it>

---

# Track 2: XRPL Application Track

**No fixed theme, the open track.** Build something that meaningfully leverages the XRP Ledger. Whether it's payments, tokenization, DeFi, identity, or something entirely new.

## You can use AI: allowed with full transparency

You are free to use any AI software (LLMs, code assistants, visual generators), but you **must explicitly declare** which tool was used, how, and where:

- **Solution design & code generation:** specify approaches, algorithms or token logic generated via AI.
- **Documentation:** declare assistance in writing specifications or slides.
- **Pitch preparation:** detail AI involvement in slide creation or speech drafting.

## Evaluation: how we rate your work

1. **Idea:** originality, creativity, and strength of the concept.
2. **Implementation:** code quality, functionality, and overall app experience.
3. **Demo quality:** clarity, storytelling, and impact of the pitch.
4. **Potential:** real-world impact, scalability, and room to grow.

Judges: Thomas Hussenet, Roman Thepaut, Emma Nasseri, Marco Jean Aboav.

---

# Track 3: Tokenization Challenge

Turn real value into tokens people can trust. A joint track by De Componendis Cifris × XRPL Commons.

## Tokenization track · ingredients

**Real-world value** + **Cryptography** + **Tokens on the ledger**

## The idea: a token is worth its data

- A token can represent a share of **any real asset**, but on the ledger it is **just a number**.
- **And** its value depends on off-chain facts nobody on-chain can see.

→ **The key:** cryptographic proofs that bind the token to real value.

## Example: tokenized energy

### From a real asset to an investment

1. **Fund:** tokens are issued to finance a new energy plant. Investors buy them.
2. **Produce:** the plant generates energy, which is sold and earns revenue.
3. **Verify:** meters sign production data. Proofs are anchored on the ledger.
4. **Return:** revenue flows back to token holders, pro rata.

**The point:** the token *is* the investment, and its yield is only as credible as step 3.

### Where cryptography adds value

Flow: Investors (buy tokens) → *money ≠ tokens* → Token issuer (issues tokens) → *builds & runs* → Energy asset (plant + smart meters) → *signed data* → Ledger (tokens + proofs). Yield flows back from the ledger to token holders, pro rata.

- **Signed measurements:** device keys and attestation prove who produced the data.
- **Commitments:** hashes and Merkle trees anchor data for cheap audits.
- **Private proofs:** zero-knowledge proofs reveal the yield, not the raw data.

## The hackathon challenge: Tokenize real value (open track, free theme)

**The scope:** build **any application** where **tokenization** is the **central feature**, and **cryptography** makes the token **trustworthy**.

## For whom: two ways in

- **Cryptographers:** you master the tools. Turn them into a **business idea** people would invest in.
- **Practitioners:** you have the use case. **Experiment with cryptographic tools** to validate, store and communicate data on-chain.

**Any asset:** energy, real estate, art, carbon credits, invoices, data... as long as **the token is the heart** of the project.

## The rules: you can use

- **Anything you find on the Internet**, not subject to copyright limitation for non-profit use.
- **Any cryptographic primitive/protocol**, such as:
  - Signatures & device attestation
  - Commitments & Merkle trees
  - Zero-knowledge proofs
  - Threshold & multiparty protocols
  - Any other advanced cryptosystem...

**Reference:** XRP Ledger documentation: <https://xrpl.org/docs>

## You can use AI: allowed with full transparency

Same policy as above: declare which tool was used, how, and where, for solution design & code generation (approaches, algorithms or token logic), documentation, and pitch preparation.

## Evaluation: how we rate your work

1. **Effectiveness:** tokenization at the core, use of the ledger and closeness to real deployment.
2. **Crypto vision:** how cryptography gives verifiable value to the token: novelty vs feasibility.
3. **The pitch:** clarity, business vision and defense.

Mentors and judges:

- Francesco Pierangeli (LUM University)
- Vera Radeva (XRPL Commons)
- Tushar Pardhe (XRPL Commons)
- Carlo Brunetta (ShunyaXifra)

## Good luck to all IXH26 teams!

IXH26 · Tokenization track. For any doubt, ask the IXH mentors! De Componendis Cifris × XRPL Commons.

---

## Mentors & judges: who's here to help

| Name | Affiliation |
|------|-------------|
| Vera Radeva | XRPL Commons |
| Elisa Bailly | XRPL Commons |
| Thomas Hussenet | XRPL Commons |
| Romain Thépaut | XRPL Commons |
| Tushar Pardhe | XRPL Commons |
| Emma Nasseri | UBRI, Ripple |
| Carlo Brunetta | De Cifris |
| Roberto La Scala | University of Bari |
| Francesco Romeo | Cryptography mentor |
| Andrea Gangemi | Cryptography mentor |
| Gabriele Radici | Cryptography mentor |
| Francesco Pierangeli | LUM University |
| Marco Jean Aboav | Cross Asset Strategie |

**Hack the Mentor:** 17:00 today, office hours.

**Safe help**

- **Share:** your code, public address, transaction hash and result code.
- **Never share:** a seed, a private key or a signed transaction blob.

---

## Judging: how projects are evaluated

1. **Innovation:** how original is the idea? Does it bring new insights or solutions?
2. **Execution:** how well is it built? Does it show technical depth and solid engineering?
3. **Impact:** does it add real value to a community, scenario or industry?
4. **Pitch:** is the project clearly communicated, with a convincing demo?

| | |
|---|---|
| Submit by | Sat 21 Nov, 12:00 |
| Pitch format | 3 min + 2 min Q&A |
| Winners | Top 3 per track |
| Where to submit | The Hackathon app |

---

## Resources and links

| | |
|---|---|
| Hackathon app | hackathons.xrpl-commons.org |
| XRPL Academy | academy.xrpl-commons.org |
| Developer docs | xrpl.org |
| Dev linktree | linktr.ee/rippledevrel |
| Questions | education@xrpl-commons.org |

Scan the QR code to register, join a team and submit your project.
