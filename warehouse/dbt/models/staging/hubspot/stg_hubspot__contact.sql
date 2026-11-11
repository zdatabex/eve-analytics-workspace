with raw_data as (

    select * from {{ source('hubspot', 'contact') }}

),

renamed as (

    select
        hubspot_contact_id,
        observed_at,
        hubspot_company_id,
        full_name,
        email_normalized,
        title,
        buying_role,
        source_system,
        delivery_id,
        ingested_at
    from raw_data

)

select * from renamed
