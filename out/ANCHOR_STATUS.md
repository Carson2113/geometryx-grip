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
