# Zero-support activity audit

Date: 2026-07-14  
Decision: keep zero-support identities; reject only unobservable accounts.

## Question

Does `0 / 2,521` Network support mean an identity is useless or should leave
the Registry?

No. It means none of the 2,521 complete voting entities follows any X account
owned by that Registry identity in the frozen snapshot. It does not measure
AI relevance, posting activity, public followers, or the usefulness of that
person's outgoing-follow graph.

## Evidence

- The final entity-union analysis contained 38 zero-support Registry entities.
- 35 came from AI Engineer World's Fair 2026/2024; three were pre-existing AI
  researchers: Piotr Mirowski, Vlad Mnih, and Xuechen Li.
- A bounded fresh TwitterAPI.io timeline pass queried 35 accounts and retained
  every raw response in `data/raw/x/x-content.db`.
- 28 returned 254 public timeline items. Seven returned an empty public
  timeline page. Three additional conference profiles had a provider-reported
  lifetime `statusesCount` of zero.
- `@paulhenrytx`, the motivating example, returned two authored posts; its
  latest observed item is dated 2024-06-30. It is dormant, not empty.
- The timeline pass made 35 provider requests. At the documented maximum
  `$0.00015` per returned tweet, 254 returned items imply a conservative
  `$0.03810` upper bound; the provider exposed no billed cost.

Activity did not decide Registry state. A dormant but relevant expert can
still provide useful discovery evidence through their outgoing follows, while
a newly admitted curated speaker may be valuable precisely because the old
network has not already discovered them.

## Applied decision

Keep all 38 zero-support identities. Do not apply follower, support, timeline,
or posting-frequency cutoffs to Registry admission.

Reject only identities that are technically unobservable or invalid. The
frozen following snapshot independently marked these three accounts protected:

| Entity | X account | Reason |
| --- | --- | --- |
| Amit Navindgi | `@amitnavindgi` | Protected; no public posts or outgoing follows are observable. |
| Raymond Feng | `@raymondmfeng` | Protected; no public posts or outgoing follows are observable. |
| Idan Gazit | `@idangazit` | Protected; no public posts or outgoing follows are observable. |

All three now carry reversible `protected_x_unobservable` Registry rejections
with X evidence URLs. The three provisional `no_public_post_history`
rejections created during the audit were cleared before handoff.

## Result

- Registry: 2,630 total identities; 2,431 active people; 160 active
  organizations; 39 rejections.
- Frozen snapshot: unchanged at 2,558 complete, three missing, and three
  protected source accounts.
- Refreshed derived support: 2,521 voting entities and 2,524 active
  X-addressable Registry targets, including all 38 zero-support identities.
- No provider recollection was needed for the graph because protected sources
  already contributed zero outgoing votes.

Future cohort changes should be evaluated from unique useful evidence and
cited-insight yield. Activity and Network support are useful diagnostics, not
admission truth.
