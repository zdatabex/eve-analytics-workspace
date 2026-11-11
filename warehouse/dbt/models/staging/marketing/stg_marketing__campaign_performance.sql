with raw_data as (

    select * from {{ source('marketing', 'campaign_performance') }}

),

renamed as (

    select
        marketing_campaign_id,
        performance_date,
        spend_amount,
        impression_count,
        click_count,
        source_system,
        delivery_id,
        ingested_at
    from raw_data

)

select * from renamed
