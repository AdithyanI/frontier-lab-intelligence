# Registry Cleanup Checkpoint

Checkpoint date: 2026-07-11, before fresh outgoing-follow ingestion.

## Frozen State

- Git commit: `d9ffa37a103c73bbb5d0ec54081a34258daebf10`
- Database path: `data/fli.db`
- Database SHA-256:
  `047d3f109b9eb0b0a7b5c5ca79ca3046faa69dca21dd7b6b107f1afca5135352`
- Database size: `12,042,240` bytes
- The working database and the database blob stored at the checkpoint commit had
  the same SHA-256 when this checkpoint was recorded.
- The checkpoint commit was already present on `origin/main`.

The Git-tracked database blob is the byte-exact backup. A second 12 MB database
copy is intentionally not committed because it would duplicate the same bytes
without adding another recovery boundary.

## Reconciliation

| Measure | Value |
| --- | ---: |
| Entities | 2,213 |
| People | 2,123 |
| Organizations | 86 |
| Stored unsure entities | 4 |
| Protected-account rejections | 3 |
| Active unsure entities | 1 |
| Channels | 2,259 |
| X accounts | 2,235 |
| Graph edges | 0 |

`PRAGMA integrity_check` returned `ok`; `PRAGMA foreign_key_check` returned no
violations. Three rejected accounts retain an underlying `unsure` structural
kind, which explains the difference between four stored unsure entities and
one active unsure entity.

## Recovery

Extract the frozen database to a temporary path first:

```bash
git show d9ffa37a103c73bbb5d0ec54081a34258daebf10:data/fli.db \
  > tmp/registry-cleanup-2026-07-11.db
shasum -a 256 tmp/registry-cleanup-2026-07-11.db
sqlite3 tmp/registry-cleanup-2026-07-11.db 'PRAGMA integrity_check;'
```

The expected checksum is the SHA-256 above. Replacing the active database is a
separate deliberate recovery action; do not overwrite `data/fli.db` merely to
inspect the checkpoint.

## Final Cleanup Amendment

After this byte-exact checkpoint, Adi manually rejected the remaining unsure
`@linatawfik9` identity. The tracked database still has 2,235 X accounts, but
four reason-bearing rejected identities are excluded from graph collection.
The final active collection cohort is therefore 2,231 accounts with zero active
unsure entities. The original checkpoint remains the rollback boundary before
that single auditable curation change.

## Next Boundary

Collection breadth and trust are separate:

- fetch outgoing follows for the 2,231-account active cohort where accessible;
- preserve one attributable, resumable snapshot per source account;
- choose a smaller reviewed subset for personalized PageRank teleport weight;
- compare PageRank with the simple number of screened Registry accounts that
  follow each candidate;
- do not read the empty legacy `graph_edges` plane as a fallback.
