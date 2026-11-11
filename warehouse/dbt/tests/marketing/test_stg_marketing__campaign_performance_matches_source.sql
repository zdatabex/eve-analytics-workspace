{{ config(tags=['marketing_staging']) }}

-- Exact reconciliation to raw_marketing.campaign_performance. Fails when row
-- counts differ, a campaign-day key exists on only one side, either side has
-- more than one row for that key, or a contract column differs. Comparison
-- uses the documented warehouse types. No exception allowlist.
with source_rows as (

    select
        cast(marketing_campaign_id as varchar) as marketing_campaign_id,
        cast(performance_date as date) as performance_date,
        cast(spend_amount as decimal(18, 2)) as spend_amount,
        cast(impression_count as bigint) as impression_count,
        cast(click_count as bigint) as click_count,
        cast(source_system as varchar) as source_system,
        cast(delivery_id as varchar) as delivery_id,
        cast(ingested_at as timestamp) as ingested_at
    from {{ source('marketing', 'campaign_performance') }}

),

staged_rows as (

    select
        cast(marketing_campaign_id as varchar) as marketing_campaign_id,
        cast(performance_date as date) as performance_date,
        cast(spend_amount as decimal(18, 2)) as spend_amount,
        cast(impression_count as bigint) as impression_count,
        cast(click_count as bigint) as click_count,
        cast(source_system as varchar) as source_system,
        cast(delivery_id as varchar) as delivery_id,
        cast(ingested_at as timestamp) as ingested_at
    from {{ ref('stg_marketing__campaign_performance') }}

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

    select
        marketing_campaign_id,
        performance_date
    from source_rows
    group by marketing_campaign_id, performance_date
    having count(*) > 1

),

duplicate_staged_keys as (

    select
        marketing_campaign_id,
        performance_date
    from staged_rows
    group by marketing_campaign_id, performance_date
    having count(*) > 1

)

select
    marketing_campaign_id,
    performance_date
from source_only
union
select
    marketing_campaign_id,
    performance_date
from staged_only
union
select
    marketing_campaign_id,
    performance_date
from duplicate_source_keys
union
select
    marketing_campaign_id,
    performance_date
from duplicate_staged_keys
