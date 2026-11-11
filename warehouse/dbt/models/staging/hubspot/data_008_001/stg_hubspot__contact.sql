select
    hubspot_contact_id,
    full_name,
    email_normalized,
    title,
    buying_role,
    observed_at,
    hubspot_company_id,
    source_system,
    delivery_id,
    ingested_at
from {{ source('hubspot', 'contact') }}
