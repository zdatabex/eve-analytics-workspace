select
    hubspot_company_id,
    firm_name,
    primary_domain,
    state,
    segment,
    practice_focus,
    icp_fit,
    owner_name,
    hubspot_lifecycle_stage,
    observed_at,
    source_system,
    delivery_id,
    ingested_at
from {{ source('hubspot', 'company') }}
