{{ config(materialized='view', tags=['marketing_staging']) }}

select
    marketing_campaign_id,
    performance_date,
    spend_amount,
    impression_count,
    click_count,
    source_system,
    delivery_id,
    ingested_at
from {{ source('marketing', 'campaign_performance') }}
