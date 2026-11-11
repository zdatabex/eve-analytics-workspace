with keys as (
    select
        {{ generate_surrogate_key(["'ab'", "'c'"]) }} as split_one,
        {{ generate_surrogate_key(["'a'", "'bc'"]) }} as split_two,
        {{ generate_surrogate_key(["null", "'value'"]) }} as null_key,
        {{ generate_surrogate_key(["''", "'value'"]) }} as empty_key,
        {{ generate_surrogate_key(["null", "'value'"]) }} as repeated_null_key
)

select *
from keys
where
    split_one = split_two
    or null_key = empty_key
    or null_key != repeated_null_key
