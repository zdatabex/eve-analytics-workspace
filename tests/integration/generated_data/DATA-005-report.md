# DATA-005 data-quality report

This report records the validation of the four committed synthetic datasets. It has no wall-clock timestamp.

## Datasets

### data-generation/config/default.yaml

- Population: baseline
- Seed: 1003
- Window: 2024-01-01 through 2025-07-01
- Delivery id: dlv_1003
- Load schema: dev_data_003
- Generate command: `python3 -m eve_data_generation generate --config data-generation/config/default.yaml --output <temp directory>`

| Entity | Rows |
| --- | --- |
| dealhub.booking | 12 |
| dealhub.contract | 12 |
| dealhub.quote | 6 |
| dealhub.subscription | 14 |
| hubspot.activity | 12 |
| hubspot.company | 15 |
| hubspot.contact | 24 |
| hubspot.deal | 82 |
| hubspot.lead | 57 |
| marketing.campaign | 3 |
| marketing.campaign_performance | 1644 |
| marketing.touch | 8 |
| product.ai_workflow | 3 |
| product.firm | 6 |
| product.outcome | 12 |
| product.usage | 24 |
| product.user | 12 |

### data-generation/config/test.yaml

- Population: baseline
- Seed: 7
- Window: 2024-03-01 through 2024-04-14
- Delivery id: dlv_7
- Load schema: dev_data_003
- Generate command: `python3 -m eve_data_generation generate --config data-generation/config/test.yaml --output <temp directory>`

| Entity | Rows |
| --- | --- |
| dealhub.booking | 8 |
| dealhub.contract | 8 |
| dealhub.quote | 4 |
| dealhub.subscription | 10 |
| hubspot.activity | 4 |
| hubspot.company | 10 |
| hubspot.contact | 16 |
| hubspot.deal | 53 |
| hubspot.lead | 38 |
| marketing.campaign | 2 |
| marketing.campaign_performance | 90 |
| marketing.touch | 3 |
| product.ai_workflow | 3 |
| product.firm | 4 |
| product.outcome | 8 |
| product.usage | 16 |
| product.user | 8 |

### data-generation/config/scenarios.yaml

- Population: scenario
- Seed: 1004
- Window: 2024-01-01 through 2025-07-01
- Delivery id: dlv_1004
- Load schema: dev_data_004
- Generate command: `python3 -m eve_data_generation generate --config data-generation/config/scenarios.yaml --output <temp directory>`

| Entity | Rows |
| --- | --- |
| dealhub.booking | 7 |
| dealhub.contract | 8 |
| dealhub.quote | 21 |
| dealhub.subscription | 13 |
| hubspot.activity | 3 |
| hubspot.company | 14 |
| hubspot.contact | 8 |
| hubspot.deal | 45 |
| hubspot.lead | 30 |
| marketing.campaign | 1 |
| marketing.campaign_performance | 548 |
| marketing.touch | 7 |
| product.ai_workflow | 7 |
| product.firm | 5 |
| product.outcome | 3 |
| product.usage | 9 |
| product.user | 4 |

### data-generation/config/scenarios-test.yaml

- Population: scenario
- Seed: 4004
- Window: 2024-01-01 through 2025-01-31
- Delivery id: dlv_4004
- Load schema: dev_data_004
- Generate command: `python3 -m eve_data_generation generate --config data-generation/config/scenarios-test.yaml --output <temp directory>`

| Entity | Rows |
| --- | --- |
| dealhub.booking | 7 |
| dealhub.contract | 8 |
| dealhub.quote | 21 |
| dealhub.subscription | 13 |
| hubspot.activity | 3 |
| hubspot.company | 14 |
| hubspot.contact | 8 |
| hubspot.deal | 45 |
| hubspot.lead | 30 |
| marketing.campaign | 1 |
| marketing.campaign_performance | 397 |
| marketing.touch | 7 |
| product.ai_workflow | 7 |
| product.firm | 5 |
| product.outcome | 3 |
| product.usage | 9 |
| product.user | 4 |


## 1. Schema compliance

| Configuration | Result | Failures |
| --- | --- | --- |
| data-generation/config/default.yaml | pass | 0 |
| data-generation/config/test.yaml | pass | 0 |
| data-generation/config/scenarios.yaml | pass | 0 |
| data-generation/config/scenarios-test.yaml | pass | 0 |

### Defects

No defects.

## 2. Primary key uniqueness

| Configuration | Result | Failures |
| --- | --- | --- |
| data-generation/config/default.yaml | pass | 0 |
| data-generation/config/test.yaml | pass | 0 |
| data-generation/config/scenarios.yaml | pass | 0 |
| data-generation/config/scenarios-test.yaml | pass | 0 |

### Defects

No defects.

## 3. Foreign key relationships

| Configuration | Result | Failures |
| --- | --- | --- |
| data-generation/config/default.yaml | pass | 0 |
| data-generation/config/test.yaml | pass | 0 |
| data-generation/config/scenarios.yaml | pass | 0 |
| data-generation/config/scenarios-test.yaml | pass | 0 |

### Defects

No defects.

## 4. Required field completeness

| Configuration | Result | Failures |
| --- | --- | --- |
| data-generation/config/default.yaml | pass | 0 |
| data-generation/config/test.yaml | pass | 0 |
| data-generation/config/scenarios.yaml | pass | 0 |
| data-generation/config/scenarios-test.yaml | pass | 0 |

### Defects

No defects.

## 5. Lifecycle transitions

| Configuration | Result | Failures |
| --- | --- | --- |
| data-generation/config/default.yaml | pass | 0 |
| data-generation/config/test.yaml | pass | 0 |
| data-generation/config/scenarios.yaml | pass | 0 |
| data-generation/config/scenarios-test.yaml | pass | 0 |

### Defects

No defects.

## 6. Temporal consistency

| Configuration | Result | Failures |
| --- | --- | --- |
| data-generation/config/default.yaml | pass | 0 |
| data-generation/config/test.yaml | pass | 0 |
| data-generation/config/scenarios.yaml | pass | 0 |
| data-generation/config/scenarios-test.yaml | pass | 0 |

### Defects

No defects.

## 7. Bookings, contracts, and subscriptions

| Configuration | Result | Failures |
| --- | --- | --- |
| data-generation/config/default.yaml | pass | 0 |
| data-generation/config/test.yaml | pass | 0 |
| data-generation/config/scenarios.yaml | pass | 0 |
| data-generation/config/scenarios-test.yaml | pass | 0 |

### Defects

No defects.

## 8. Product usage relationships

| Configuration | Result | Failures |
| --- | --- | --- |
| data-generation/config/default.yaml | pass | 0 |
| data-generation/config/test.yaml | pass | 0 |
| data-generation/config/scenarios.yaml | pass | 0 |
| data-generation/config/scenarios-test.yaml | pass | 0 |

### Defects

No defects.

## 9. Reproducibility

| Configuration | Result | Failures |
| --- | --- | --- |
| data-generation/config/default.yaml | pass | 0 |
| data-generation/config/test.yaml | pass | 0 |
| data-generation/config/scenarios.yaml | pass | 0 |
| data-generation/config/scenarios-test.yaml | pass | 0 |

### Defects

No defects.

## 10. Distributions and edge cases

| Configuration | Result | Failures |
| --- | --- | --- |
| data-generation/config/default.yaml | pass | 0 |
| data-generation/config/test.yaml | pass | 0 |
| data-generation/config/scenarios.yaml | pass | 0 |
| data-generation/config/scenarios-test.yaml | pass | 0 |

### Distributions

#### data-generation/config/default.yaml

| Count | Expected | Observed |
| --- | --- | --- |
| HubSpot companies | 12 | 12 |
| Contacts | 24 | 24 |
| Leads | 24 | 24 |
| Campaigns | 3 | 3 |
| Activities | 12 | 12 |
| Touches | 8 | 8 |
| Product firms | 6 | 6 |
| Product users | 12 | 12 |
| Usage rows | 24 | 24 |
| Campaign-day rows | 1644 | 1644 |

| Rate | Population | Population size | share_count | Observed | Fails when different |
| --- | --- | --- | --- | --- | --- |
| renewal_rate | Subscriptions | 6 | 4 | 4 | yes |
| expansion_rate | Subscriptions | 6 | 2 | 2 | yes |
| churn_rate | Subscriptions | 6 | 2 | 2 | yes |
| outcome_rate | Usage rows | 24 | 12 | 12 | yes |
| null_company_domain_rate | Companies | 12 | 1 | 1 | yes |
| orphan_lead_rate | Leads | 24 | 2 | 2 | yes |
| null_deal_amount_rate | Deals | 18 | 3 | 3 | yes |
| single_parent_activity_rate | Activities | 12 | 3 | 3 | yes |
| null_performance_measure_rate | Campaign-day rows | 1644 | 82 | 82 | yes |
| clicks_exceed_impressions_rate | Campaign-day rows | 1644 | 82 | 82 | yes |
| null_user_email_rate | Product users | 12 | 1 | 1 | yes |
| company_change_rate | Companies | 12 | 3 | 3 | yes |
| duplicate_contact_email_rate | Contacts | 24 | 2 | 3 | no |
| domain_match_rate | Product firms | 6 | 3 | 3 | no |

##### Lead status

| Label | Weight | Allocated | Observed |
| --- | --- | --- | --- |
| converted | 4 | 12 | 12 |
| disqualified | 1 | 3 | 3 |
| new | 1 | 3 | 3 |
| qualified | 1 | 3 | 3 |
| working | 1 | 3 | 3 |

##### New-business stage

| Label | Weight | Allocated | Observed |
| --- | --- | --- | --- |
| closed_lost | 4 | 3 | 3 |
| closed_won | 8 | 6 | 6 |
| discovery | 1 | 1 | 1 |
| evaluation | 1 | 1 | 1 |
| negotiation | 1 | 1 | 1 |
| proposal | 1 | 0 | 0 |

##### Campaign channel

| Label | Weight | Allocated | Observed |
| --- | --- | --- | --- |
| email | 2 | 1 | 1 |
| outbound | 1 | 0 | 0 |
| paid_search | 3 | 1 | 1 |
| paid_social | 2 | 1 | 1 |
| partner | 1 | 0 | 0 |
| webinar | 1 | 0 | 0 |

| Emitted event | Status |
| --- | --- |
| lead_created | present |
| lead_qualified | present |
| lead_disqualified | present |
| lead_converted | present |
| opportunity_opened | present |
| opportunity_stage_changed | present |
| opportunity_won | present |
| opportunity_lost | present |
| subscription_renewed | present |
| subscription_expanded | present |
| subscription_churned | present |

`duplicate_contact_email_rate` and `domain_match_rate` are recorded beside `share_count` and do not fail the suite by themselves.

#### data-generation/config/test.yaml

| Count | Expected | Observed |
| --- | --- | --- |
| HubSpot companies | 8 | 8 |
| Contacts | 16 | 16 |
| Leads | 16 | 16 |
| Campaigns | 2 | 2 |
| Activities | 4 | 4 |
| Touches | 3 | 3 |
| Product firms | 4 | 4 |
| Product users | 8 | 8 |
| Usage rows | 16 | 16 |
| Campaign-day rows | 90 | 90 |

| Rate | Population | Population size | share_count | Observed | Fails when different |
| --- | --- | --- | --- | --- | --- |
| renewal_rate | Subscriptions | 4 | 2 | 2 | yes |
| expansion_rate | Subscriptions | 4 | 2 | 2 | yes |
| churn_rate | Subscriptions | 4 | 2 | 2 | yes |
| outcome_rate | Usage rows | 16 | 8 | 8 | yes |
| null_company_domain_rate | Companies | 8 | 1 | 1 | yes |
| orphan_lead_rate | Leads | 16 | 2 | 2 | yes |
| null_deal_amount_rate | Deals | 12 | 2 | 2 | yes |
| single_parent_activity_rate | Activities | 4 | 1 | 1 | yes |
| null_performance_measure_rate | Campaign-day rows | 90 | 5 | 5 | yes |
| clicks_exceed_impressions_rate | Campaign-day rows | 90 | 5 | 5 | yes |
| null_user_email_rate | Product users | 8 | 2 | 2 | yes |
| company_change_rate | Companies | 8 | 2 | 2 | yes |
| duplicate_contact_email_rate | Contacts | 16 | 2 | 3 | no |
| domain_match_rate | Product firms | 4 | 2 | 2 | no |

##### Lead status

| Label | Weight | Allocated | Observed |
| --- | --- | --- | --- |
| converted | 4 | 8 | 8 |
| disqualified | 1 | 2 | 2 |
| new | 1 | 2 | 2 |
| qualified | 1 | 2 | 2 |
| working | 1 | 2 | 2 |

##### New-business stage

| Label | Weight | Allocated | Observed |
| --- | --- | --- | --- |
| closed_lost | 4 | 2 | 2 |
| closed_won | 8 | 4 | 4 |
| discovery | 1 | 1 | 1 |
| evaluation | 1 | 1 | 1 |
| negotiation | 1 | 0 | 0 |
| proposal | 1 | 0 | 0 |

##### Campaign channel

| Label | Weight | Allocated | Observed |
| --- | --- | --- | --- |
| email | 1 | 1 | 1 |
| outbound | 1 | 1 | 1 |
| paid_search | 1 | 0 | 0 |
| paid_social | 1 | 0 | 0 |
| partner | 1 | 0 | 0 |
| webinar | 1 | 0 | 0 |

| Emitted event | Status |
| --- | --- |
| lead_created | present |
| lead_qualified | present |
| lead_disqualified | present |
| lead_converted | present |
| opportunity_opened | present |
| opportunity_stage_changed | present |
| opportunity_won | present |
| opportunity_lost | present |
| subscription_renewed | present |
| subscription_expanded | present |
| subscription_churned | present |

`duplicate_contact_email_rate` and `domain_match_rate` are recorded beside `share_count` and do not fail the suite by themselves.

#### data-generation/config/scenarios.yaml

Baseline count and rate keys are not applied to this file as population targets.

| Journey | Expected | Observed |
| --- | --- | --- |
| new_business_conversion | 1 | 1 |
| expansion | 1 | 1 |
| renewal | 1 | 1 |
| churn | 1 | 1 |
| lost_opportunity | 1 | 1 |
| stage_regression | 1 | 1 |
| low_adoption | 1 | 1 |
| domain twin | 1 | 1 |

#### data-generation/config/scenarios-test.yaml

Baseline count and rate keys are not applied to this file as population targets.

| Journey | Expected | Observed |
| --- | --- | --- |
| new_business_conversion | 1 | 1 |
| expansion | 1 | 1 |
| renewal | 1 | 1 |
| churn | 1 | 1 |
| lost_opportunity | 1 | 1 |
| stage_regression | 1 | 1 |
| low_adoption | 1 | 1 |
| domain twin | 1 | 1 |


### Edge cases

#### data-generation/config/default.yaml

| Case | Status |
| --- | --- |
| company with a null primary_domain | present |
| two contacts with the same email and different contact ids | present |
| lead with a null company and a null contact | present |
| deal with a null amount | present |
| activity with exactly one parent | present |
| activity with a null deal and activity that cites a deal | present |
| campaign-day row with a null spend_amount | present |
| campaign-day row whose clicks exceed impressions | present |
| one product firm domain matching a company and one that does not | present |
| product user with a null email | present |
| active subscription renewal or expansion | present |
| churned subscription with no booking at or after churn | present |
| lifecycle stage outside prospect, customer, and former_customer | present |
| two observations of one company | present |

#### data-generation/config/test.yaml

| Case | Status |
| --- | --- |
| company with a null primary_domain | present |
| two contacts with the same email and different contact ids | present |
| lead with a null company and a null contact | present |
| deal with a null amount | present |
| activity with exactly one parent | present |
| activity with a null deal and activity that cites a deal | present |
| campaign-day row with a null spend_amount | present |
| campaign-day row whose clicks exceed impressions | present |
| one product firm domain matching a company and one that does not | present |
| product user with a null email | present |
| active subscription renewal or expansion | present |
| churned subscription with no booking at or after churn | present |
| lifecycle stage outside prospect, customer, and former_customer | present |
| two observations of one company | present |

#### data-generation/config/scenarios.yaml

| Case | Status |
| --- | --- |
| Duplicate contacts | present |
| Merged accounts | present |
| Repeated stage changes | present |
| Late-arriving events | present |
| Contract amendments | present |
| Canceled subscriptions | present |
| Soft-deleted records | present |
| Low or declining adoption | present |

#### data-generation/config/scenarios-test.yaml

| Case | Status |
| --- | --- |
| Duplicate contacts | present |
| Merged accounts | present |
| Repeated stage changes | present |
| Late-arriving events | present |
| Contract amendments | present |
| Canceled subscriptions | present |
| Soft-deleted records | present |
| Low or declining adoption | present |


### Defects

No defects.

## 11. Load read-back

| Configuration | Result | Failures |
| --- | --- | --- |
| data-generation/config/default.yaml | pass | 0 |
| data-generation/config/test.yaml | pass | 0 |
| data-generation/config/scenarios.yaml | pass | 0 |
| data-generation/config/scenarios-test.yaml | pass | 0 |

### Defects

No defects.

## Recommendations

- `data-generation/config/default.yaml`: duplicate_contact_email_rate share_count is 2 and 3 contacts share an email. Duplicate contacts are produced by copying one source email onto the selected recipients, so the contacts that share an email include that source when the source was not selected.
- `data-generation/config/test.yaml`: duplicate_contact_email_rate share_count is 2 and 3 contacts share an email. Duplicate contacts are produced by copying one source email onto the selected recipients, so the contacts that share an email include that source when the source was not selected.
