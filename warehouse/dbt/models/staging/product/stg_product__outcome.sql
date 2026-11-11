with source as (

    select
        product_outcome_source_id,
        occurred_at,
        outcome_type,
        product_usage_source_id,
        product_user_source_id,
        product_firm_id,
        product_workflow_id,
        source_system,
        delivery_id,
        ingested_at
    from {{ source('product', 'outcome') }}

)

select
    product_outcome_source_id,
    occurred_at,
    outcome_type,
    product_usage_source_id,
    product_user_source_id,
    product_firm_id,
    product_workflow_id,
    source_system,
    delivery_id,
    ingested_at
from source
