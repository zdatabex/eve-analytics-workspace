with raw_data as (

    select * from {{ source('product', 'outcome') }}

),

renamed as (

    select
        product_outcome_source_id,
        product_usage_source_id,
        product_user_source_id,
        product_firm_id,
        product_workflow_id,
        outcome_type,
        occurred_at,
        source_system,
        delivery_id,
        ingested_at
    from raw_data

)

select * from renamed
