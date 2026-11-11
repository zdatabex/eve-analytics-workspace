with raw_data as (

    select * from {{ source('marketing', 'campaign') }}

),

renamed as (

    select
        marketing_campaign_id,
        campaign_code,
        campaign_name,
        channel,
        source_system,
        delivery_id,
        ingested_at
    from raw_data

)

select * from renamed
