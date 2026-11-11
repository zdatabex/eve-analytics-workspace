with raw_data as (

    select * from {{ source('product', 'ai_workflow') }}

),

renamed as (

    select
        product_workflow_id,
        workflow_code,
        workflow_name,
        source_system,
        delivery_id,
        ingested_at
    from raw_data

)

select * from renamed
