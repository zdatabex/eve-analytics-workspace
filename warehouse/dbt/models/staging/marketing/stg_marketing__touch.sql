{{ config(materialized='view', tags=['marketing_staging']) }}

select
    marketing_touch_source_id,
    occurred_at,
    marketing_campaign_id,
    hubspot_contact_id,
    hubspot_lead_id,
    hubspot_company_id,
    source_system,
    delivery_id,
    ingested_at
from {{ source('marketing', 'touch') }}
