select
    hubspot_lead_id,
    status,
    created_at,
    observed_at,
    emitted_event,
    hubspot_company_id,
    hubspot_contact_id,
    marketing_campaign_id,
    hubspot_deal_id,
    source_system,
    delivery_id,
    ingested_at
from {{ source('hubspot', 'lead') }}
