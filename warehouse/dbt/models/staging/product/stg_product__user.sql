with raw_data as (

    select * from {{ source('product', 'user') }}

),

renamed as (

    select
        product_user_source_id,
        observed_at,
        product_firm_id,
        email_normalized,
        status,
        source_system,
        delivery_id,
        ingested_at
    from raw_data

)

select * from renamed
