with source as (

    select
        product_usage_source_id,
        occurred_at,
        work_unit_count,
        product_user_source_id,
        product_firm_id,
        product_workflow_id,
        source_system,
        delivery_id,
        ingested_at
    from {{ source('product', 'usage') }}

)

select
    product_usage_source_id,
    occurred_at,
    work_unit_count,
    product_user_source_id,
    product_firm_id,
    product_workflow_id,
    source_system,
    delivery_id,
    ingested_at
from source
