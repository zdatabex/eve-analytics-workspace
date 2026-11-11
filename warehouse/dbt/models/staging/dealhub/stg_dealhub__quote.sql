with source as (

    select
        dealhub_quote_id,
        quote_number,
        status,
        quoted_amount,
        observed_at,
        hubspot_deal_id,
        hubspot_company_id,
        source_system,
        delivery_id,
        ingested_at
    from {{ source('dealhub', 'quote') }}

)

select
    dealhub_quote_id,
    quote_number,
    status,
    quoted_amount,
    observed_at,
    hubspot_deal_id,
    hubspot_company_id,
    source_system,
    delivery_id,
    ingested_at
from source
