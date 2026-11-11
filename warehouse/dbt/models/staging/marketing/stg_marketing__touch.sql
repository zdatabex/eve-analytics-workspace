with raw_data as (

    select * from {{ source('marketing', 'touch') }}

),

renamed as (

    select
        marketing_touch_source_id,
        marketing_campaign_id,
        hubspot_contact_id,
        hubspot_lead_id,
        hubspot_company_id,
        occurred_at,
        source_system,
        delivery_id,
        ingested_at
    from raw_data

)

select * from renamed
