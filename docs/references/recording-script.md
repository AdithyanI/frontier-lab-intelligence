# Submission video — recording script

Working script for the section-by-section screen recording, 20 July 2026.
Adi dictates from this; the agent updates it as sections get re-recorded.
Spoken style on purpose: short sentences, numbers written out where helpful.

Status per section: `draft` → `recorded` → `final`.

---

## Section 1 · Intro — land on the site — `draft`

Screen: https://frontier-lab-intelligence.adithyan.io/ (lands on Insights), then navigate to /how.

> Hi, my name is Adi, and this is Frontier Lab Intelligence.
>
> Everything I'm about to show you is live. When you open the site, you land
> here: the final insights, for any date. This is the end product, and we'll
> come back to it.
>
> But first I want to show you how the system works. So let's go to the How
> page.
>
> The core challenge is signal to noise. Frontier labs and their researchers
> publish thousands of things every day, and almost all of it is noise. This
> whole system is one funnel: wide at the top, and at the narrow end come out
> a handful of cited insights per day. That's what I'll walk you through,
> stage by stage.

---

## Section 2 · The funnel — `draft`

Screen: https://frontier-lab-intelligence.adithyan.io/how — scroll the sticky funnel with arrow keys.

> I have limited attention, so the way I designed the system is a funnel. The
> funnel decides what to pay attention to. As we go down, every stage raises
> the signal-to-noise ratio. Think of the blue dots as signal and the gray
> ones as noise: as we go down, we keep the blue and drop the gray.
>
> It starts from a universe of over five hundred fifty thousand accounts on X.
> That gets screened down to a Registry of about twenty six hundred trusted
> identities: frontier lab researchers and the labs themselves.
>
> On a typical day the Registry produces around four and a half thousand
> posts. Those resolve into about thirteen hundred exact Events. A transparent
> attention score picks the top one hundred for judging. Two independent
> judges route them per audience. And an editorial agent keeps three to six
> insights per audience, declining everything else in writing.
>
> So at the end, one single data source becomes two cited briefs. And nothing
> is dropped silently, at any stage.

---

## Section 3 · The Registry, ranked by trust — `draft`

Screen: /how, scroll to the network rank figure (or /network/ranking live).

> The key design call is here. Accounts are ranked by who inside the screened
> set follows them, never by raw follower count. A million followers measures
> reach, not trust.
>
> The thesis held up. Across the briefed days, events by authors in the top
> half of this ranking became kept insights at about twelve percent. The
> bottom half, about seven percent. And the judges never see the rank.

---

## Section 4 · One insight, fully traceable — `draft`

Screen: pick one insight → open its event → show citations and the declined list.

> Here is what "cited" actually means. Every claim in an insight quotes its
> source, and the quote is checked verbatim against a frozen snapshot before
> the brief ships. A quote that can't be matched does not ship. That is the
> hallucination control.
>
> And transparency goes the other way too. Under the brief you can expand
> every candidate the editor declined, each with its written reason.

---

## Section 5 · Costs and limitations — `draft`

Screen: /how "For the reviewer" section, or architecture page.

> A full day costs well under a dollar in routing, with the editorial run on
> top. Every model call is logged with its cost.
>
> The limits are stated, not hidden: single-source events can't be
> independently verified, and the top one hundred gate has unmeasured recall.
> The system tells you what it doesn't know.
>
> Everything you saw is live and inspectable. Thanks for watching.

---

## Working notes

- Stale on /how: "13 briefed days" → corpus is now 15 briefed days (Jul 5–19).
- 17 July is the worked example day throughout /how (4,537 posts → 1,287
  events → 56 candidates → 84 decisions → 10 insights).
- Rework queue (page edits requested during recording): —
