with source as (

    select
        dealhub_booking_id,
        booking_number,
        booking_type,
        booking_amount,
        booked_at,
        hubspot_company_id,
        hubspot_deal_id,
        dealhub_contract_id,
        dealhub_subscription_id,
        source_system,
        delivery_id,
        ingested_at
    from {{ source('dealhub', 'booking') }}

)

select
    dealhub_booking_id,
    booking_number,
    booking_type,
    booking_amount,
    booked_at,
    hubspot_company_id,
    hubspot_deal_id,
    dealhub_contract_id,
    dealhub_subscription_id,
    source_system,
    delivery_id,
    ingested_at
from source
