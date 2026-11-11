with raw_data as (

    select * from {{ source('dealhub', 'subscription') }}

),

renamed as (

    select
        dealhub_subscription_id,
        observed_at,
        dealhub_contract_id,
        hubspot_company_id,
        subscription_number,
        status,
        plan_code,
        billing_frequency,
        emitted_event,
        seat_count,
        recurring_amount,
        term_start,
        term_end,
        source_system,
        delivery_id,
        ingested_at
    from raw_data

)

select * from renamed
