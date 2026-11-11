with source as (

    select
        product_user_source_id,
        email_normalized,
        status,
        observed_at,
        product_firm_id,
        source_system,
        delivery_id,
        ingested_at
    from {{ source('product', 'user') }}

)

select
    product_user_source_id,
    email_normalized,
    status,
    observed_at,
    product_firm_id,
    source_system,
    delivery_id,
    ingested_at
from source
