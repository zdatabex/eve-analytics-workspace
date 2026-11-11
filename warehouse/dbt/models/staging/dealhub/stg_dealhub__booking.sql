with raw_data as (

    select * from {{ source('dealhub', 'booking') }}

),

renamed as (

    select
        dealhub_booking_id,
        dealhub_contract_id,
        dealhub_subscription_id,
        hubspot_company_id,
        hubspot_deal_id,
        booking_number,
        booking_type,
        booking_amount,
        booked_at,
        source_system,
        delivery_id,
        ingested_at
    from raw_data

)

select * from renamed
