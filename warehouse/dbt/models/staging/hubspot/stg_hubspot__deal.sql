with raw_data as (

    select * from {{ source('hubspot', 'deal') }}

),

renamed as (

    select
        hubspot_deal_id,
        observed_at,
        hubspot_company_id,
        hubspot_contact_id,
        hubspot_lead_id,
        dealhub_subscription_id,
        opportunity_name,
        opportunity_type,
        stage,
        owner_name,
        forecast_category,
        emitted_event,
        amount,
        expected_close_date,
        created_at,
        source_system,
        delivery_id,
        ingested_at
    from raw_data

)

select * from renamed
