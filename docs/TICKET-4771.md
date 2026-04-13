# TICKET-4471 — Suspected Host Tampering / Anomalous File Modifications

**Priority:** P1
**Reported by:** Marcus Webb (mwebb@helix.internal)
**Filed:** 2026-04-13 07:43 UTC
**Assigned to:** On-call Engineer
**Status:** OPEN — pending investigation

---

## Description

Something modified files on my workstation overnight. I noticed it when I came in
this morning. I don't know if any of these things are related, but listing everything
I found:

**1. Unknown SSH key in my authorized_keys**

There's a second public key in `~/.ssh/authorized_keys` that I didn't add.
It's labelled `deploy-key-temp`. I don't have any deploy keys configured
and I didn't put it there.

**2. Crontab looks different**

`/etc/crontab` has changed since yesterday. Something got added but it doesn't
look obviously malicious at first glance — I almost missed it. I noticed it because
the file's modification timestamp was from 03:17 UTC, which is when nobody would
be touching system files.

**3. Docker.raw integrity check failing**

The nightly backup job (runs at 22:00 UTC) writes a SHA-256 checksum to
`checksums.txt` alongside `Docker.raw`. This morning the hashes don't match.
The file is larger than it was at the snapshot time.

**4. The ai-gateway was doing something weird around 03:00–04:00 UTC**

I can see in the Docker logs that the gateway was active during that window
but I don't fully understand what it was doing. It wasn't serving any of my
normal traffic — I was asleep.

---

## What I Need

Someone to look at the running stack, figure out what happened and how,
identify what was compromised, and tell me how to fix it.

The full stack is in this repo. Spin it up and dig in.

---

*— Marcus*
