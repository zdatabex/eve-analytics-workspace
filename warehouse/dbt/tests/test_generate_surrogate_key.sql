with keys as (
    select
        {{ dbt_utils.generate_surrogate_key(["'ab'", "'c'"]) }} as split_one,
        {{ dbt_utils.generate_surrogate_key(["'a'", "'bc'"]) }} as split_two,
        {{ dbt_utils.generate_surrogate_key(["'left'", "'right'"]) }} as ordered_one,
        {{ dbt_utils.generate_surrogate_key(["'right'", "'left'"]) }} as ordered_two,
        {{ dbt_utils.generate_surrogate_key(["null", "'value'"]) }} as null_key,
        {{ dbt_utils.generate_surrogate_key(["''", "'value'"]) }} as empty_key,
        {{ dbt_utils.generate_surrogate_key(["null", "'value'"]) }} as repeated_null_key
)

select *
from keys
where
    split_one = split_two
    or ordered_one = ordered_two
    or null_key = empty_key
    or null_key is null
    or null_key != repeated_null_key
