-- One hop, no self link, the same surviving_account_id on every row of an account_id, and primary_domain unique among open surviving rows when present.
-- unique, not_null, accepted_values, and relationships cannot express this rule.

with violations as (

    select
        'self link' as violation,
        account_id as detail
    from {{ ref('int_account') }}
    where surviving_account_id = account_id

    union all

    select
        'survivor chain' as violation,
        child.account_id as detail
    from {{ ref('int_account') }} as child
    inner join {{ ref('int_account') }} as parent
        on parent.account_id = child.surviving_account_id
    where child.surviving_account_id is not null
        and parent.surviving_account_id is not null

    union all

    select
        'survivor link changes across versions' as violation,
        account_id as detail
    from {{ ref('int_account') }}
    group by account_id
    having count(distinct surviving_account_id) > 1
        or (
            count(*) filter (where surviving_account_id is null) > 0
            and count(*) filter (where surviving_account_id is not null) > 0
        )

    union all

    select
        'shared domain among open survivors' as violation,
        primary_domain as detail
    from {{ ref('int_account') }}
    where is_current
        and surviving_account_id is null
        and primary_domain is not null
    group by primary_domain
    having count(*) > 1

)

select violation, detail
from violations
