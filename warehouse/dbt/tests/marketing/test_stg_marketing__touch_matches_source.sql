{{ config(tags=['marketing_staging']) }}

-- Exact reconciliation to raw_marketing.touch. Fails when row counts differ,
-- a marketing_touch_source_id exists on only one side, either side has more
-- than one row for that key, or a contract column differs. Comparison uses
-- the documented warehouse types. No exception allowlist.
with source_rows as (

    select
        cast(marketing_touch_source_id as varchar) as marketing_touch_source_id,
        cast(occurred_at as timestamp) as occurred_at,
        cast(marketing_campaign_id as varchar) as marketing_campaign_id,
        cast(hubspot_contact_id as varchar) as hubspot_contact_id,
        cast(hubspot_lead_id as varchar) as hubspot_lead_id,
        cast(hubspot_company_id as varchar) as hubspot_company_id,
        cast(source_system as varchar) as source_system,
        cast(delivery_id as varchar) as delivery_id,
        cast(ingested_at as timestamp) as ingested_at
    from {{ source('marketing', 'touch') }}

),

staged_rows as (

    select
        cast(marketing_touch_source_id as varchar) as marketing_touch_source_id,
        cast(occurred_at as timestamp) as occurred_at,
        cast(marketing_campaign_id as varchar) as marketing_campaign_id,
        cast(hubspot_contact_id as varchar) as hubspot_contact_id,
        cast(hubspot_lead_id as varchar) as hubspot_lead_id,
        cast(hubspot_company_id as varchar) as hubspot_company_id,
        cast(source_system as varchar) as source_system,
        cast(delivery_id as varchar) as delivery_id,
        cast(ingested_at as timestamp) as ingested_at
    from {{ ref('stg_marketing__touch') }}

),

source_only as (

    select * from source_rows
    except all
    select * from staged_rows

),

staged_only as (

    select * from staged_rows
    except all
    select * from source_rows

),

duplicate_source_keys as (

    select marketing_touch_source_id
    from source_rows
    group by marketing_touch_source_id
    having count(*) > 1

),

duplicate_staged_keys as (

    select marketing_touch_source_id
    from staged_rows
    group by marketing_touch_source_id
    having count(*) > 1

)

select marketing_touch_source_id
from source_only
union
select marketing_touch_source_id
from staged_only
union
select marketing_touch_source_id
from duplicate_source_keys
union
select marketing_touch_source_id
from duplicate_staged_keys
