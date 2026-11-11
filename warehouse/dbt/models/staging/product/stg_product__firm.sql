with raw_data as (

    select * from {{ source('product', 'firm') }}

),

renamed as (

    select
        product_firm_id,
        firm_name,
        primary_domain,
        state,
        source_system,
        delivery_id,
        ingested_at
    from raw_data

)

select * from renamed
