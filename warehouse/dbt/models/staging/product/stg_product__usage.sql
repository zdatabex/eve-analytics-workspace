with raw_data as (

    select * from {{ source('product', 'usage') }}

),

renamed as (

    select
        product_usage_source_id,
        product_user_source_id,
        product_firm_id,
        product_workflow_id,
        work_unit_count,
        occurred_at,
        source_system,
        delivery_id,
        ingested_at
    from raw_data

)

select * from renamed
