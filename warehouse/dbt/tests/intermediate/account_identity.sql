-- The account identity walk, the Product attachment rules, surrogate account_id, one account per source identifier, no copied identifier, blank and unequal domains staying apart, and equal names staying apart.
-- unique, not_null, accepted_values, and relationships cannot express this rule.

with recursive company_observations as (

    select
        hubspot_company_id,
        observed_at,
        firm_name,
        primary_domain,
        state,
        segment,
        practice_focus,
        icp_fit,
        owner_name,
        hubspot_lifecycle_stage
    from {{ ref('stg_hubspot__company') }}

),

company_created as (

    select
        hubspot_company_id,
        min(observed_at) as first_observed_at,
        row_number() over (
            order by min(observed_at), hubspot_company_id
        ) as creation_rank
    from company_observations
    group by hubspot_company_id

),

ordered_company_observations as (

    select
        row_number() over (
            order by company_observations.observed_at, company_observations.hubspot_company_id
        ) as seq,
        company_observations.hubspot_company_id,
        company_observations.observed_at,
        company_observations.primary_domain,
        company_created.creation_rank
    from company_observations
    inner join company_created
        on company_observations.hubspot_company_id = company_created.hubspot_company_id

),

latest_company_observation as (

    select
        hubspot_company_id,
        firm_name,
        primary_domain,
        state,
        segment,
        practice_focus,
        icp_fit,
        owner_name,
        hubspot_lifecycle_stage
    from company_observations
    qualify row_number() over (
        partition by hubspot_company_id
        order by observed_at desc
    ) = 1

),

ordered_product_firms as (

    select
        row_number() over (order by product_firm_id) as seq,
        product_firm_id,
        firm_name,
        primary_domain,
        state,
        ingested_at
    from {{ ref('stg_product__firm') }}

),

-- Walk HubSpot observations in time order. A blank domain matches nothing.
-- Once a firm is a duplicate, a later domain change does not clear or move that link.
company_walk as (

    select
        0 as step,
        []::struct(
            company_id varchar,
            domain varchar,
            is_survivor boolean,
            survivor_id varchar,
            creation_rank bigint,
            became_duplicate_at timestamp,
            duplicate_from_first boolean
        )[] as companies

    union all

    select
        prepared.step + 1 as step,
        case
            when prepared.is_first
                and (
                    prepared.primary_domain is null
                    or prepared.match_id is null
                )
                then list_append(
                    prepared.companies,
                    struct_pack(
                        company_id := prepared.hubspot_company_id,
                        domain := prepared.primary_domain,
                        is_survivor := true,
                        survivor_id := prepared.hubspot_company_id,
                        creation_rank := prepared.creation_rank,
                        became_duplicate_at := null::timestamp,
                        duplicate_from_first := false
                    )
                )
            when prepared.is_first
                then list_append(
                    prepared.companies,
                    struct_pack(
                        company_id := prepared.hubspot_company_id,
                        domain := prepared.primary_domain,
                        is_survivor := false,
                        survivor_id := prepared.match_id,
                        creation_rank := prepared.creation_rank,
                        became_duplicate_at := prepared.observed_at,
                        duplicate_from_first := true
                    )
                )
            else list_transform(
                prepared.companies,
                lambda c: case
                    when c.company_id = prepared.hubspot_company_id then
                        case
                            when not c.is_survivor
                                then struct_update(c, domain := prepared.primary_domain)
                            when prepared.primary_domain is null
                                or prepared.match_id is null
                                then struct_update(c, domain := prepared.primary_domain)
                            when c.creation_rank > prepared.match_rank
                                then struct_pack(
                                    company_id := c.company_id,
                                    domain := prepared.primary_domain,
                                    is_survivor := false,
                                    survivor_id := prepared.match_id,
                                    creation_rank := c.creation_rank,
                                    became_duplicate_at := prepared.observed_at,
                                    duplicate_from_first := false
                                )
                            else struct_update(c, domain := prepared.primary_domain)
                        end
                    when prepared.match_id is not null
                        and c.company_id = prepared.match_id
                        and prepared.self_is_survivor
                        and prepared.self_rank < prepared.match_rank
                        and prepared.primary_domain is not null
                        then struct_pack(
                            company_id := c.company_id,
                            domain := c.domain,
                            is_survivor := false,
                            survivor_id := prepared.hubspot_company_id,
                            creation_rank := c.creation_rank,
                            became_duplicate_at := prepared.observed_at,
                            duplicate_from_first := false
                        )
                    else c
                end
            )
        end as companies
    from (
        select
            company_walk.step,
            company_walk.companies,
            ordered_company_observations.hubspot_company_id,
            ordered_company_observations.primary_domain,
            ordered_company_observations.observed_at,
            ordered_company_observations.creation_rank,
            not list_contains(
                list_transform(company_walk.companies, lambda c: c.company_id),
                ordered_company_observations.hubspot_company_id
            ) as is_first,
            (
                select match_row.company_id
                from unnest(list_filter(
                    company_walk.companies,
                    lambda c: c.is_survivor
                        and ordered_company_observations.primary_domain is not null
                        and c.domain = ordered_company_observations.primary_domain
                        and c.company_id <> ordered_company_observations.hubspot_company_id
                )) as match_row
                order by match_row.creation_rank
                limit 1
            ) as match_id,
            (
                select match_row.creation_rank
                from unnest(list_filter(
                    company_walk.companies,
                    lambda c: c.is_survivor
                        and ordered_company_observations.primary_domain is not null
                        and c.domain = ordered_company_observations.primary_domain
                        and c.company_id <> ordered_company_observations.hubspot_company_id
                )) as match_row
                order by match_row.creation_rank
                limit 1
            ) as match_rank,
            (
                select self_row.is_survivor
                from unnest(list_filter(
                    company_walk.companies,
                    lambda c: c.company_id = ordered_company_observations.hubspot_company_id
                )) as self_row
                limit 1
            ) as self_is_survivor,
            (
                select self_row.creation_rank
                from unnest(list_filter(
                    company_walk.companies,
                    lambda c: c.company_id = ordered_company_observations.hubspot_company_id
                )) as self_row
                limit 1
            ) as self_rank
        from company_walk
        inner join ordered_company_observations
            on ordered_company_observations.seq = company_walk.step + 1
    ) as prepared

),

company_identity as (

    select
        company.company_id as hubspot_company_id,
        company.is_survivor,
        company.survivor_id as survivor_company_id,
        company.became_duplicate_at,
        company.duplicate_from_first,
        {{ dbt_utils.generate_surrogate_key(["'hubspot'", 'company.company_id']) }} as account_id,
        case
            when company.is_survivor then null
            else {{ dbt_utils.generate_surrogate_key(["'hubspot'", 'company.survivor_id']) }}
        end as surviving_account_id
    from company_walk
    cross join unnest(company_walk.companies) as company
    where company_walk.step = (select max(step) from company_walk)

),

-- Attach Product firms after the HubSpot walk, in product_firm_id order.
-- The match domain is the HubSpot company's latest observation.
product_walk as (

    select
        0 as step,
        coalesce(
            (
                select list(
                    struct_pack(
                        source_system := 'hubspot',
                        source_id := company_identity.hubspot_company_id,
                        domain := latest_company_observation.primary_domain,
                        is_survivor := true,
                        survivor_source := 'hubspot',
                        survivor_id := company_identity.hubspot_company_id,
                        product_firm_id := null::varchar,
                        hubspot_company_id := company_identity.hubspot_company_id
                    )
                    order by company_identity.hubspot_company_id
                )
                from company_identity
                inner join latest_company_observation
                    on latest_company_observation.hubspot_company_id = company_identity.hubspot_company_id
                where company_identity.is_survivor
            ),
            []::struct(
                source_system varchar,
                source_id varchar,
                domain varchar,
                is_survivor boolean,
                survivor_source varchar,
                survivor_id varchar,
                product_firm_id varchar,
                hubspot_company_id varchar
            )[]
        ) as accounts

    union all

    select
        prepared.step + 1 as step,
        case
            when prepared.primary_domain is null or prepared.match_id is null
                then list_append(
                    prepared.accounts,
                    struct_pack(
                        source_system := 'product',
                        source_id := prepared.product_firm_id,
                        domain := prepared.primary_domain,
                        is_survivor := true,
                        survivor_source := 'product',
                        survivor_id := prepared.product_firm_id,
                        product_firm_id := prepared.product_firm_id,
                        hubspot_company_id := null::varchar
                    )
                )
            when prepared.match_product_firm_id is null
                then list_transform(
                    prepared.accounts,
                    lambda account: case
                        when account.source_system = prepared.match_source
                            and account.source_id = prepared.match_id
                            then struct_update(
                                account,
                                product_firm_id := prepared.product_firm_id
                            )
                        else account
                    end
                )
            else list_append(
                prepared.accounts,
                struct_pack(
                    source_system := 'product',
                    source_id := prepared.product_firm_id,
                    domain := prepared.primary_domain,
                    is_survivor := false,
                    survivor_source := prepared.match_source,
                    survivor_id := prepared.match_id,
                    product_firm_id := prepared.product_firm_id,
                    hubspot_company_id := null::varchar
                )
            )
        end as accounts
    from (
        select
            product_walk.step,
            product_walk.accounts,
            ordered_product_firms.product_firm_id,
            ordered_product_firms.primary_domain,
            (
                select match_row.source_system
                from unnest(list_filter(
                    product_walk.accounts,
                    lambda account: account.is_survivor
                        and ordered_product_firms.primary_domain is not null
                        and account.domain = ordered_product_firms.primary_domain
                )) as match_row
                order by match_row.source_system, match_row.source_id
                limit 1
            ) as match_source,
            (
                select match_row.source_id
                from unnest(list_filter(
                    product_walk.accounts,
                    lambda account: account.is_survivor
                        and ordered_product_firms.primary_domain is not null
                        and account.domain = ordered_product_firms.primary_domain
                )) as match_row
                order by match_row.source_system, match_row.source_id
                limit 1
            ) as match_id,
            (
                select match_row.product_firm_id
                from unnest(list_filter(
                    product_walk.accounts,
                    lambda account: account.is_survivor
                        and ordered_product_firms.primary_domain is not null
                        and account.domain = ordered_product_firms.primary_domain
                )) as match_row
                order by match_row.source_system, match_row.source_id
                limit 1
            ) as match_product_firm_id
        from product_walk
        inner join ordered_product_firms
            on ordered_product_firms.seq = product_walk.step + 1
    ) as prepared

),

product_identity as (

    select
        account.source_system,
        account.source_id,
        account.is_survivor,
        account.survivor_source,
        account.survivor_id,
        account.product_firm_id,
        account.hubspot_company_id
    from product_walk
    cross join unnest(product_walk.accounts) as account
    where product_walk.step = (select max(step) from product_walk)

),

expected_identity as (

    select
        company_identity.account_id,
        company_identity.surviving_account_id,
        company_identity.hubspot_company_id,
        cast(null as varchar) as product_firm_id
    from company_identity
    where company_identity.duplicate_from_first

    union all

    select
        company_identity.account_id,
        company_identity.surviving_account_id,
        company_identity.hubspot_company_id,
        product_identity.product_firm_id
    from company_identity
    left join product_identity
        on product_identity.source_system = 'hubspot'
        and product_identity.hubspot_company_id = company_identity.hubspot_company_id
    where not company_identity.duplicate_from_first

    union all

    select
        {{ dbt_utils.generate_surrogate_key(["'product'", 'product_identity.product_firm_id']) }} as account_id,
        case
            when product_identity.is_survivor then null
            when product_identity.survivor_source = 'hubspot'
                then {{ dbt_utils.generate_surrogate_key(["'hubspot'", 'product_identity.survivor_id']) }}
            else {{ dbt_utils.generate_surrogate_key(["'product'", 'product_identity.survivor_id']) }}
        end as surviving_account_id,
        cast(null as varchar) as hubspot_company_id,
        product_identity.product_firm_id
    from product_identity
    where product_identity.source_system = 'product'

),

actual_identity as (

    select distinct
        account_id,
        surviving_account_id,
        hubspot_company_id,
        product_firm_id
    from {{ ref('int_account') }}

),

identity_difference as (

    select
        'missing identity' as violation,
        account_id,
        hubspot_company_id,
        product_firm_id
    from expected_identity
    except
    select
        'missing identity' as violation,
        account_id,
        hubspot_company_id,
        product_firm_id
    from actual_identity

    union all

    select
        'unexpected identity' as violation,
        account_id,
        hubspot_company_id,
        product_firm_id
    from actual_identity
    except
    select
        'unexpected identity' as violation,
        account_id,
        hubspot_company_id,
        product_firm_id
    from expected_identity

),

rule_violations as (

    select
        'surrogate account_id' as violation,
        account_id,
        hubspot_company_id,
        product_firm_id
    from {{ ref('int_account') }}
    where account_id is distinct from case
        when hubspot_company_id is not null
            then {{ dbt_utils.generate_surrogate_key(["'hubspot'", 'hubspot_company_id']) }}
        else {{ dbt_utils.generate_surrogate_key(["'product'", 'product_firm_id']) }}
    end

    union all

    select
        'one account per hubspot company' as violation,
        cast(null as varchar) as account_id,
        staged.hubspot_company_id,
        cast(null as varchar) as product_firm_id
    from (
        select hubspot_company_id
        from {{ ref('stg_hubspot__company') }}
        group by hubspot_company_id
    ) as staged
    left join (
        select hubspot_company_id, count(distinct account_id) as accounts
        from {{ ref('int_account') }}
        where hubspot_company_id is not null
        group by hubspot_company_id
    ) as conformed
        on conformed.hubspot_company_id = staged.hubspot_company_id
    where conformed.accounts is distinct from 1

    union all

    select
        'one account per product firm' as violation,
        cast(null as varchar) as account_id,
        cast(null as varchar) as hubspot_company_id,
        staged.product_firm_id
    from (
        select product_firm_id
        from {{ ref('stg_product__firm') }}
        group by product_firm_id
    ) as staged
    left join (
        select product_firm_id, count(distinct account_id) as accounts
        from {{ ref('int_account') }}
        where product_firm_id is not null
        group by product_firm_id
    ) as conformed
        on conformed.product_firm_id = staged.product_firm_id
    where conformed.accounts is distinct from 1

    union all

    select
        'account without a firm source identifier' as violation,
        account_id,
        hubspot_company_id,
        product_firm_id
    from {{ ref('int_account') }}
    where hubspot_company_id is null
        and product_firm_id is null

    union all

    select
        'copied identifier' as violation,
        duplicate_account.account_id,
        duplicate_account.hubspot_company_id,
        duplicate_account.product_firm_id
    from {{ ref('int_account') }} as duplicate_account
    inner join {{ ref('int_account') }} as survivor_account
        on survivor_account.account_id = duplicate_account.surviving_account_id
    where (
            duplicate_account.hubspot_company_id is not null
            and duplicate_account.hubspot_company_id = survivor_account.hubspot_company_id
        )
        or (
            duplicate_account.product_firm_id is not null
            and duplicate_account.product_firm_id = survivor_account.product_firm_id
        )
        or (
            duplicate_account.hubspot_company_id is not null
            and duplicate_account.product_firm_id is not null
            and duplicate_account.surviving_account_id is not null
        )

    union all

    select
        'blank domain matched' as violation,
        account.account_id,
        blank_company.hubspot_company_id,
        account.product_firm_id
    from (
        select hubspot_company_id
        from {{ ref('stg_hubspot__company') }}
        group by hubspot_company_id
        having count(*) filter (where primary_domain is not null) = 0
    ) as blank_company
    inner join {{ ref('int_account') }} as account
        on account.hubspot_company_id = blank_company.hubspot_company_id
    where account.surviving_account_id is not null

    union all

    select
        'linked without a shared domain' as violation,
        left_account.account_id,
        left_company.hubspot_company_id,
        right_company.hubspot_company_id as product_firm_id
    from (
        select distinct hubspot_company_id, firm_name
        from {{ ref('stg_hubspot__company') }}
    ) as left_company
    inner join (
        select distinct hubspot_company_id, firm_name
        from {{ ref('stg_hubspot__company') }}
    ) as right_company
        on left_company.hubspot_company_id < right_company.hubspot_company_id
    inner join {{ ref('int_account') }} as left_account
        on left_account.hubspot_company_id = left_company.hubspot_company_id
    inner join {{ ref('int_account') }} as right_account
        on right_account.hubspot_company_id = right_company.hubspot_company_id
    where (
            left_account.account_id = right_account.account_id
            or left_account.surviving_account_id = right_account.account_id
            or right_account.surviving_account_id = left_account.account_id
        )
        and not exists (
            select 1
            from {{ ref('stg_hubspot__company') }} as left_observation
            inner join {{ ref('stg_hubspot__company') }} as right_observation
                on left_observation.primary_domain = right_observation.primary_domain
                and left_observation.primary_domain is not null
            where left_observation.hubspot_company_id = left_company.hubspot_company_id
                and right_observation.hubspot_company_id = right_company.hubspot_company_id
        )

    union all

    select
        'blank product domain is not its own survivor' as violation,
        cast(null as varchar) as account_id,
        cast(null as varchar) as hubspot_company_id,
        firm.product_firm_id
    from {{ ref('stg_product__firm') }} as firm
    where firm.primary_domain is null
        and not exists (
            select 1
            from {{ ref('int_account') }} as account
            where account.product_firm_id = firm.product_firm_id
                and account.hubspot_company_id is null
                and account.surviving_account_id is null
        )

)

select violation, account_id, hubspot_company_id, product_firm_id
from identity_difference
union all
select violation, account_id, hubspot_company_id, product_firm_id
from rule_violations
union all
select
    'survivor link' as violation,
    expected_identity.account_id,
    expected_identity.hubspot_company_id,
    expected_identity.product_firm_id
from expected_identity
inner join actual_identity
    on actual_identity.account_id = expected_identity.account_id
    and actual_identity.hubspot_company_id is not distinct from expected_identity.hubspot_company_id
    and actual_identity.product_firm_id is not distinct from expected_identity.product_firm_id
where actual_identity.surviving_account_id is distinct from expected_identity.surviving_account_id
