with source as (

    select
        product_workflow_id,
        workflow_code,
        workflow_name,
        source_system,
        delivery_id,
        ingested_at
    from {{ source('product', 'ai_workflow') }}

)

select
    product_workflow_id,
    workflow_code,
    workflow_name,
    source_system,
    delivery_id,
    ingested_at
from source
