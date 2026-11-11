with outcome as (

    select
        product_outcome_source_id,
        occurred_at,
        product_usage_source_id,
        product_user_source_id,
        product_firm_id,
        product_workflow_id
    from {{ ref('stg_product__outcome') }}

),

usage as (

    select
        product_usage_source_id,
        occurred_at,
        product_user_source_id,
        product_firm_id,
        product_workflow_id
    from {{ ref('stg_product__usage') }}

)

select
    outcome.product_outcome_source_id,
    outcome.product_usage_source_id,
    outcome.occurred_at as outcome_occurred_at,
    usage.occurred_at as usage_occurred_at,
    outcome.product_user_source_id as outcome_user_source_id,
    usage.product_user_source_id as usage_user_source_id,
    outcome.product_firm_id as outcome_firm_id,
    usage.product_firm_id as usage_firm_id,
    outcome.product_workflow_id as outcome_workflow_id,
    usage.product_workflow_id as usage_workflow_id
from outcome
left join usage
    on outcome.product_usage_source_id = usage.product_usage_source_id
where usage.product_usage_source_id is null
    or outcome.product_user_source_id != usage.product_user_source_id
    or outcome.product_firm_id != usage.product_firm_id
    or outcome.product_workflow_id != usage.product_workflow_id
    or outcome.occurred_at < usage.occurred_at
