select
    hubspot_activity_id,
    activity_type,
    subject,
    occurred_at,
    hubspot_company_id,
    hubspot_contact_id,
    hubspot_lead_id,
    hubspot_deal_id,
    source_system,
    delivery_id,
    ingested_at
from {{ source('hubspot', 'activity') }}
