with raw_data as (

    select * from {{ source('hubspot', 'lead') }}

),

renamed as (

    select
        hubspot_lead_id,
        observed_at,
        hubspot_company_id,
        hubspot_contact_id,
        hubspot_deal_id,
        marketing_campaign_id,
        status,
        emitted_event,
        created_at,
        source_system,
        delivery_id,
        ingested_at
    from raw_data

)

select * from renamed
