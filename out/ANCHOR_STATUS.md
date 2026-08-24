# §7 anchor status — what is actually proved, and what is not

As of 24 August 2026, 13:16 UTC. Specification hash
`f27b2cf9acb0af461d0817a98348ddae8f28175db609d4fc3af6626180d7fceb`, re-verified against
`GRIP2_REGISTRATION.md` at this commit and **unchanged** since the `v2.0.0-prereg` tag.

## What §7 item 4 committed to

> Third-party timestamping. The tag page is submitted to the Internet Archive, and the specification
> hash is posted publicly in a repository issue and archived independently. GitHub's own commit
> timestamps are controlled by the party being audited and are therefore not sufficient.

Three obligations: Internet Archive submission, a public issue carrying the hash, independent
archiving.

## Status of each

| Obligation | Status | Detail |
|---|---|---|
| Internet Archive submission | **UNMET** | `web.archive.org` returned `ERR_CONNECTION_RESET`; `archive.ph` returned HTTP 429 with a CAPTCHA. No snapshot exists. |
| Public issue with the hash | **UNMET** | Not posted. Awaiting a decision. |
| Independent archiving | **UNMET** | Depends on the above. |
| *(added)* Bitcoin timestamp | **PENDING → then MET** | Stamped via OpenTimestamps; four calendars attesting; awaiting block confirmation. |

## What the Bitcoin timestamp does and does not prove

`GRIP2_REGISTRATION.md` and `ANCHOR_MANIFEST.txt` were submitted to OpenTimestamps at 13:16 UTC on 24
August 2026. The receipt embeds the specification's sha256 and pending attestations from four
independent calendars: `btc.calendar.catallaxy.com`, `bob.btc.calendar.opentimestamps.org`,
`alice.btc.calendar.opentimestamps.org`, and `finney.calendar.eternitywall.com`.

**Proves:** that this exact byte sequence existed before a specific Bitcoin block. Nobody — including
me, Perplexity, or GitHub — can backdate the specification or alter it without breaking the hash. A
verifier needs only the file, the `.ots` receipt, and Bitcoin block headers. It does not depend on the
continued existence of any organisation, which is a property the Internet Archive does not have.

**Does not prove:** that the document was ever *published*. A timestamp is not visibility. §7's
Internet Archive and public-issue requirements existed so that a reader could confirm the
specification was openly available before results were computed, and a Bitcoin timestamp is silent on
that. Someone could hold a secretly-stamped document and reveal it only if convenient.

So the substitution is honest but partial:

- **anti-backdating purpose — met, and more strongly than §7 asked for.**
- **public-visibility purpose — still open.**

The specification is **not edited** to claim OpenTimestamps satisfies §7.4. It does not. The gap is
recorded here and stays recorded.

## Remaining weakness worth stating plainly

Publishing the hash in a public issue is the cheap part and it is the part still missing. Until that
exists, a reader has to take on trust that the timestamped document was the one being worked from,
rather than one of several stamped variants. Stamping is not exclusive: nothing stops a party from
timestamping several different specifications and later revealing whichever one matched the results.
Bitcoin fixes backdating; only public disclosure fixes selective revelation.

That is why the public issue matters more than it looks, and why it should not be quietly dropped now
that a cryptographic anchor exists.

## Verification

```
ots verify GRIP2_REGISTRATION.md.ots
ots verify ANCHOR_MANIFEST.txt.ots
sha256sum GRIP2_REGISTRATION.md   # must equal f27b2cf9...0f7dceb
```

`ots verify` uses a local Bitcoin node if one is present and otherwise queries public block explorers,
so a verifier who wants a fully trustless check should run it against their own node.

Confirmation into a block takes a few hours; a scheduled follow-up will run `ots upgrade` to embed the
block attestation and make the receipts self-contained and offline-verifiable.

---

## Confirmation — Bitcoin attestation complete (recorded 24 Aug 2026, 20:05 UTC)

`ots upgrade` returned "Success! Timestamp complete" for both receipts on 24 August 2026 at 20:01 UTC. Receipts grew from 805 to 3,878 bytes as the calendars' Merkle paths to the Bitcoin blockchain were filled in.

Both receipts now carry three independent Bitcoin block header attestations:

| Block height | Block time (UTC) | Block hash |
|---|---|---|
| **963861** | **2026-08-24 13:38:32** | `00000000000000000001fe1e5104369fc34608adc2d517459eec1f0c0df56f67` |
| 963864 | 2026-08-24 14:16:00 | `000000000000000000005452000c1e0ad02ba71e3dc976ade51bfccec888476b` |
| 963867 | 2026-08-24 14:30:16 | `0000000000000000000145639bbafb0e83205162935b3453366063290fbf5f2d` |

The binding attestation is the earliest, **block 963861 at 13:38:32 UTC**, 22 minutes after the 13:16 UTC stamp. The specification therefore provably existed in its current form before that block was mined.

Hashes committed in the receipts, re-verified at upgrade time:

- `GRIP2_REGISTRATION.md` — `f27b2cf9acb0af461d0817a98348ddae8f28175db609d4fc3af6626180d7fceb` (**unchanged**)
- `ANCHOR_MANIFEST.txt` — `c9fae3b50170586903cdaddf8305b61d1a7d3c814f52ae77c17e89ef2c95af1e`

Block heights and times were confirmed against an independent block explorer (https://blockstream.info/api/) because this environment has no Bitcoin node; `ots verify` requires one to check the block header locally. That is a limitation of the verifying environment, not of the receipt: any party with a Bitcoin node, or with the block headers alone, can verify these receipts offline and without contacting Geometryx or the OpenTimestamps calendars.

The four `PendingAttestation` records remain in the receipts alongside the confirmed ones. That is expected — a receipt retains its calendar commitments; `btc.calendar.catallaxy.com` had not yet published a path when the upgrade ran, and the other three succeeded. Three confirmed attestations are already redundant.

**Unchanged limitation.** This satisfies §7.4's anti-backdating purpose but still does not satisfy its public-visibility purpose, and selective revelation remains possible: stamping is not exclusive, so a party could stamp several variant specifications and reveal only the one that matched. The specification was not edited to claim compliance.
