with source as (

    select
        product_firm_id,
        firm_name,
        primary_domain,
        state,
        source_system,
        delivery_id,
        ingested_at
    from {{ source('product', 'firm') }}

)

select
    product_firm_id,
    firm_name,
    primary_domain,
    state,
    source_system,
    delivery_id,
    ingested_at
from source
