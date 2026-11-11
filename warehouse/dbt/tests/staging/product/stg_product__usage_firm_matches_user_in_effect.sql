-- The user observation in effect at the usage occurred_at has the usage product_firm_id. No in-effect observation fails the test. The test does not add effective_start, effective_end, or is_current.
-- relationships does not choose an as-of row, so unique, not_null, accepted_values, relationships, not_empty_string, accepted_range, and expression_is_true cannot express this rule.

with usage as (

    select
        product_usage_source_id,
        product_user_source_id,
        product_firm_id,
        occurred_at
    from {{ ref('stg_product__usage') }}

),

users as (

    select
        product_user_source_id,
        product_firm_id,
        observed_at
    from {{ ref('stg_product__user') }}

),

candidates as (

    select
        usage.product_usage_source_id,
        usage.product_user_source_id,
        usage.product_firm_id as usage_firm_id,
        usage.occurred_at,
        users.product_firm_id as user_firm_id,
        users.observed_at
    from usage
    left join users
        on usage.product_user_source_id = users.product_user_source_id
        and users.observed_at <= usage.occurred_at

),

ranked as (

    select
        product_usage_source_id,
        product_user_source_id,
        usage_firm_id,
        occurred_at,
        user_firm_id,
        observed_at,
        max(observed_at) over (
            partition by product_usage_source_id
        ) as in_effect_observed_at
    from candidates

),

in_effect as (

    select
        product_usage_source_id,
        product_user_source_id,
        usage_firm_id,
        occurred_at,
        user_firm_id,
        observed_at,
        count(*) over (
            partition by product_usage_source_id
        ) as in_effect_row_count
    from ranked
    where observed_at = in_effect_observed_at
        or in_effect_observed_at is null

)

select
    product_usage_source_id,
    product_user_source_id,
    usage_firm_id,
    occurred_at,
    user_firm_id,
    observed_at,
    in_effect_row_count
from in_effect
where in_effect_row_count != 1
    or user_firm_id is null
    or user_firm_id != usage_firm_id
