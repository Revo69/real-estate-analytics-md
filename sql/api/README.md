# Public API SQL provenance and reconciliation

This directory now belongs to the pipeline producer. The nine `.sql` files were
copied byte-for-byte from `Imobil-Index/sql` on 2026-09-08 before any downstream
deletion. Their original SHA-256 values are recorded below.

These files describe the chronological production rollout. They are not yet a
single clean-install migration: several later scripts replace or patch
`refresh_gold_estate()`. Do not re-run the complete directory alphabetically.
The canonical ordered schema will be defined by `pipeline/gold/schema.sql` in
Task 2 Step 4.

## Historical execution order

The order below is derived from the dashboard repository history, not filename
sorting.

1. `public_api_layer.sql`
2. `revoke_internal_public_access.sql`
3. `refresh_gold_updates_api_layer.sql`
4. `check_public_api_layer.sql` — verification only
5. `add_estate_segments_api_layer.sql`
6. `add_estate_segments_daily_api_layer.sql`
7. `add_estate_housing_type_api_layer.sql`
8. `add_estate_condition_api_layer.sql`
9. `add_estate_floor_position_api_layer.sql`
10. `check_public_api_layer.sql` — run again after the additions

## Producer-owned corrective scripts

The files below were created in this repository after the historical dashboard
copy. They are not included in the copy hashes above and must be reviewed and
applied separately.

1. `harden_public_boundary.sql` — revoke redundant public privileges from
   internal relations and refresh functions, then make new postgres-owned
   objects private by default.
2. `check_public_api_layer.sql` — run after hardening; its access sections must
   return only `OK` before Step 6 is complete.

## Copy verification

| File | SHA-256 |
|---|---|
| `add_estate_condition_api_layer.sql` | `1D8FF282077BA4981466A16325F3A563D409619A0BA5AF687A2EDFB327AF71EE` |
| `add_estate_floor_position_api_layer.sql` | `B9246FC5739B32DAC293DD9B812B98B3E4269F55F56465A9A96C20CE4260473B` |
| `add_estate_housing_type_api_layer.sql` | `688EDD9B9A7B83726356DC488D39A4F4337AD4EA7D743A3C43A5E3C3A7E68F91` |
| `add_estate_segments_api_layer.sql` | `B021039A0C6CDCA4945EF5E3F93D0FB064F1BD7BAFD6066E46460B9A87B99D54` |
| `add_estate_segments_daily_api_layer.sql` | `BC1157225636C11A48C8C9C5E9D69D039F35B29DCF1F07F10BE8B5488CB86EDD` |
| `check_public_api_layer.sql` | `C4BAB3B8713E7D653A589DE8AE49B4492EC46BD4251AA747ECD84D18B9B1F372` |
| `public_api_layer.sql` | `8E05F7A0339D89B6874D70337A5CAF7143E56B28E0FCE7C4678101A6B819567F` |
| `refresh_gold_updates_api_layer.sql` | `34A5E5820B2F591E717E76E2BE0EB3995A88DA389AC4BB8C04DE92D67D7212A1` |
| `revoke_internal_public_access.sql` | `5AA38449377BF2E5FE31CF1023C638539B8819D107F78B159546CF1131725EF0` |

## Production reconciliation — 2026-09-08

The comparison source is the read-only production snapshot in
`docs/production_database_inventory_2026-09-08.md`.

| Script | Production relationship | Decision |
|---|---|---|
| `public_api_layer.sql` | The original five tables, keys, RLS read policies, public `SELECT`, public-write revokes, base indexes, and comments are present. Production also contains later API tables and additional, partly duplicated indexes. | Preserve as rollout history; do not treat it as the complete current schema. |
| `revoke_internal_public_access.sql` | Public `SELECT` is absent from the listed internal objects. Legacy non-SELECT grants remain on most internal tables/views, and `pipeline_runs` is not listed. | Replace later with a complete least-privilege producer boundary; do not apply this partial script as the final hardening change. |
| `refresh_gold_updates_api_layer.sql` | The live rent refresh still follows this structure. The live estate refresh has been superseded by all later profile additions. Both live functions use explicit `DELETE ... WHERE TRUE`, unlike these historical bodies. | Preserve history; build one current canonical function definition later. |
| `add_estate_segments_api_layer.sql` | Current table, policy, grants, indexes, comments, aggregation filters, and `count(*) >= 5` threshold are present. Its function body was superseded by later scripts. | Preserve history. |
| `add_estate_segments_daily_api_layer.sql` | Current history table and upsert behavior are present. Its function body was superseded by later scripts. | Preserve history. |
| `add_estate_housing_type_api_layer.sql` | Current table and profile block are present. Its function body was superseded by condition and floor additions. | Preserve history. |
| `add_estate_condition_api_layer.sql` | Current constrained table and normalized condition block are present. This is the base of the latest function before the floor patch. | Preserve history; retain the normalized category contract. |
| `add_estate_floor_position_api_layer.sql` | Current constrained table and floor-position block are present. The script edits the existing function text dynamically, so it depends on the exact preceding body. | Preserve history, but replace the dynamic patch with an explicit complete function in canonical SQL. |
| `check_public_api_layer.sql` | The original copied version covered all ten API tables, public read/write expectations, fixed search paths, and refresh markers. The producer-owned version was extended on 2026-09-10 to cover internal non-SELECT privileges, `pipeline_runs`, function execution/security mode, and postgres-owned default privileges. | Use the extended producer copy as the canonical verification query. |

## Security and reproducibility status

- `harden_public_boundary.sql` was applied manually and verified on 2026-09-10.
  Internal public grants, refresh-function execution, and postgres-owned
  defaults now pass the canonical access checks.
- Complete canonical function bodies must use fixed `search_path`, remain
  `SECURITY INVOKER`, and use `DELETE ... WHERE TRUE` only for intentional
  full-table replacement.
- Duplicate-index removal is a separate performance migration. It is not mixed
  into the ownership move.
- No copied script was applied to production during this reconciliation.
