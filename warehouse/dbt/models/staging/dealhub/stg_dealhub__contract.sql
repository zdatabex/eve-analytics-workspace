with source as (

    select
        dealhub_contract_id,
        contract_number,
        status,
        total_contract_value,
        start_date,
        end_date,
        observed_at,
        dealhub_quote_id,
        hubspot_deal_id,
        hubspot_company_id,
        source_system,
        delivery_id,
        ingested_at
    from {{ source('dealhub', 'contract') }}

)

select
    dealhub_contract_id,
    contract_number,
    status,
    total_contract_value,
    start_date,
    end_date,
    observed_at,
    dealhub_quote_id,
    hubspot_deal_id,
    hubspot_company_id,
    source_system,
    delivery_id,
    ingested_at
from source
