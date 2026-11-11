with source as (

    select
        dealhub_subscription_id,
        subscription_number,
        status,
        plan_code,
        seat_count,
        recurring_amount,
        billing_frequency,
        term_start,
        term_end,
        observed_at,
        emitted_event,
        dealhub_contract_id,
        hubspot_company_id,
        source_system,
        delivery_id,
        ingested_at
    from {{ source('dealhub', 'subscription') }}

)

select
    dealhub_subscription_id,
    subscription_number,
    status,
    plan_code,
    seat_count,
    recurring_amount,
    billing_frequency,
    term_start,
    term_end,
    observed_at,
    emitted_event,
    dealhub_contract_id,
    hubspot_company_id,
    source_system,
    delivery_id,
    ingested_at
from source
