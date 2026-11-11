{{ config(materialized='view', tags=['marketing_staging']) }}

select
    marketing_campaign_id,
    campaign_code,
    campaign_name,
    channel,
    source_system,
    delivery_id,
    ingested_at
from {{ source('marketing', 'campaign') }}
