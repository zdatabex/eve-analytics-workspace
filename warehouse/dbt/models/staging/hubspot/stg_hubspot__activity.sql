with raw_data as (

    select * from {{ source('hubspot', 'activity') }}

),

renamed as (

    select
        hubspot_activity_id,
        hubspot_company_id,
        hubspot_contact_id,
        hubspot_lead_id,
        hubspot_deal_id,
        activity_type,
        subject,
        occurred_at,
        source_system,
        delivery_id,
        ingested_at
    from raw_data

)

select * from renamed
