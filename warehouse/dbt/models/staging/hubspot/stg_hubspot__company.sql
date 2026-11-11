with raw_data as (

    select * from {{ source('hubspot', 'company') }}

),

renamed as (

    select
        hubspot_company_id,
        observed_at,
        firm_name,
        primary_domain,
        state,
        segment,
        practice_focus,
        icp_fit,
        owner_name,
        hubspot_lifecycle_stage,
        source_system,
        delivery_id,
        ingested_at
    from raw_data

)

select * from renamed
