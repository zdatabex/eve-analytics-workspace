# DATA-005 validation assumptions

These assumptions are the ones the generated-data suite uses. They are not extra rejection rules. A row that meets the merged source contract and the generation rules restated in `specs/DATA-005-validate-generated-data.md` stays in the dataset.

- The row key is `observation_key`. An observation entity may repeat its source identifier. `observed_at` distinguishes those rows. Current entities and immutable entities whose `observation_key` is the source identifier have one row per source identifier. Campaign performance is unique on `marketing_campaign_id` plus `performance_date`.
- Identifier shape is not a rejection rule. HubSpot identifiers are expected to be numeric strings, DealHub identifiers prefixed strings, and Marketing and Product identifiers opaque strings. The contract accepts any non-empty source identifier.
- Null optional values, duplicate emails, duplicate domains, clicks above impressions, and an open `hubspot_lifecycle_stage` are valid. `hubspot_lifecycle_stage` is not limited to `prospect`, `customer`, or `former_customer`.
- Late `ingested_at` is valid. On a scenario dataset it equals the business timestamp, except `late_event_count` immutable rows, which may be campaign-day rows and are exactly `ingest_lag_days` later. A campaign-day business timestamp is `performance_date` at `00:00:00` UTC. One generate run emits one `delivery_id` and does not emit a second replay row.
- Bookings and subscription fees are different fields. `booking_amount` stays on the booking. `recurring_amount` and `billing_frequency` stay on the subscription. `seat_count` is not a user count. This suite does not compute ARR, retention, pipeline coverage, win rate, or an adoption score, and it does not annualize `recurring_amount`.
- Domain equality is not a contract rule. Equal `primary_domain` values are the only cross-system firm match, and the contracts do not require that match. Scenario customer journeys still match on `primary_domain` because DATA-004 says they do.
- A canceled subscription is `churned` with `subscription_churned`. There is no `canceled` status. A soft-deleted record stays in the extract as `inactive`, `disqualified`, `expired`, or `rejected`.
- The edge cases in the DATA-005 specification are intentional. They are not defects, and the suite does not drop those rows.
- `eve_data_generation.validate` is not the oracle. A stricter generator check, including identifier shape, is a recommendation when the emitted rows still satisfy the contract.
- The duplicate-email construction and the null-domain firm swap are recorded beside `duplicate_contact_email_rate` and `domain_match_rate`. A difference is a recommendation. It does not fail the suite.
- Apollo and Clay are outside this dataset. The suite does not generate those records and expects no Apollo or Clay files.
