-- Version bounds, tracked values, descriptive overlay, lifecycle-only changes adding no row, one open row per account_id, duplicate and Product-only collapse, and effective_start equal to the opening observed_at or the Product ingested_at.
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

history_input as (

    select
        company_observations.hubspot_company_id,
        company_observations.observed_at,
        company_observations.owner_name,
        company_observations.segment,
        company_observations.practice_focus,
        company_observations.icp_fit,
        company_observations.primary_domain,
        company_observations.firm_name,
        company_observations.state,
        company_observations.hubspot_lifecycle_stage
    from company_observations
    inner join company_identity
        on company_observations.hubspot_company_id = company_identity.hubspot_company_id
    where
        not company_identity.duplicate_from_first
        and (
            company_identity.became_duplicate_at is null
            or company_observations.observed_at <= company_identity.became_duplicate_at
        )

),

hubspot_versions as (

    {{ effective_date(
        'history_input',
        ['hubspot_company_id'],
        'observed_at',
        ['owner_name', 'segment', 'practice_focus', 'icp_fit', 'primary_domain']
    ) }}

),

violations as (

    select
        'version key' as violation,
        account_version_id as detail
    from {{ ref('int_account') }}
    where account_version_id is distinct from {{ dbt_utils.generate_surrogate_key(['account_id', 'effective_start']) }}

    union all

    select
        'open row' as violation,
        account_id as detail
    from {{ ref('int_account') }}
    group by account_id
    having count(*) filter (where is_current) <> 1
        or count(*) filter (where effective_end is null) <> 1

    union all

    select
        'version gap or overlap' as violation,
        account_id as detail
    from (
        select
            account_id,
            effective_end,
            lead(effective_start) over (
                partition by account_id
                order by effective_start
            ) as next_start
        from {{ ref('int_account') }}
    ) as spans
    where effective_end is distinct from next_start

    union all

    select
        'duplicate or product-only collapse' as violation,
        company_identity.hubspot_company_id as detail
    from company_identity
    left join (
        select hubspot_company_id, count(*) as row_count
        from {{ ref('int_account') }}
        group by hubspot_company_id
    ) as account_rows
        on account_rows.hubspot_company_id = company_identity.hubspot_company_id
    where company_identity.duplicate_from_first
        and account_rows.row_count is distinct from 1

    union all

    select
        'duplicate from first observation' as violation,
        account.account_version_id as detail
    from company_identity
    inner join company_created
        on company_created.hubspot_company_id = company_identity.hubspot_company_id
    inner join latest_company_observation
        on latest_company_observation.hubspot_company_id = company_identity.hubspot_company_id
    inner join {{ ref('int_account') }} as account
        on account.hubspot_company_id = company_identity.hubspot_company_id
    where company_identity.duplicate_from_first
        and (
            account.firm_name is distinct from latest_company_observation.firm_name
            or account.primary_domain is distinct from latest_company_observation.primary_domain
            or account.state is distinct from latest_company_observation.state
            or account.segment is distinct from latest_company_observation.segment
            or account.practice_focus is distinct from latest_company_observation.practice_focus
            or account.icp_fit is distinct from latest_company_observation.icp_fit
            or account.owner_name is distinct from latest_company_observation.owner_name
            or account.hubspot_lifecycle_stage is distinct from latest_company_observation.hubspot_lifecycle_stage
            or account.product_firm_id is not null
            or account.effective_start is distinct from company_created.first_observed_at
            or account.effective_end is not null
            or not account.is_current
        )

    union all

    select
        'version bounds' as violation,
        coalesce(hubspot_versions.hubspot_company_id, account.hubspot_company_id) as detail
    from hubspot_versions
    full outer join {{ ref('int_account') }} as account
        on account.hubspot_company_id = hubspot_versions.hubspot_company_id
        and account.effective_start = hubspot_versions.effective_start
    inner join company_identity
        on company_identity.hubspot_company_id = coalesce(
            hubspot_versions.hubspot_company_id,
            account.hubspot_company_id
        )
    where not company_identity.duplicate_from_first
        and (
            hubspot_versions.hubspot_company_id is null
            or account.hubspot_company_id is null
            or hubspot_versions.effective_end is distinct from account.effective_end
        )

    union all

    select
        'tracked value' as violation,
        account.account_version_id as detail
    from {{ ref('int_account') }} as account
    inner join company_identity
        on company_identity.hubspot_company_id = account.hubspot_company_id
    inner join company_observations
        on company_observations.hubspot_company_id = account.hubspot_company_id
        and company_observations.observed_at = account.effective_start
    where not company_identity.duplicate_from_first
        and (
            account.owner_name is distinct from company_observations.owner_name
            or account.segment is distinct from company_observations.segment
            or account.practice_focus is distinct from company_observations.practice_focus
            or account.icp_fit is distinct from company_observations.icp_fit
            or account.primary_domain is distinct from company_observations.primary_domain
        )

    union all

    select
        'descriptive overlay' as violation,
        account.account_version_id as detail
    from {{ ref('int_account') }} as account
    inner join company_identity
        on company_identity.hubspot_company_id = account.hubspot_company_id
    inner join (
        select
            account_version.account_version_id,
            observation.firm_name,
            observation.state,
            observation.hubspot_lifecycle_stage,
            row_number() over (
                partition by account_version.account_version_id
                order by observation.observed_at desc
            ) as descriptive_rank
        from {{ ref('int_account') }} as account_version
        inner join company_observations as observation
            on observation.hubspot_company_id = account_version.hubspot_company_id
            and observation.observed_at >= account_version.effective_start
            and (
                account_version.effective_end is null
                or observation.observed_at < account_version.effective_end
            )
    ) as descriptive
        on descriptive.account_version_id = account.account_version_id
        and descriptive.descriptive_rank = 1
    where not company_identity.duplicate_from_first
        and (
            account.firm_name is distinct from descriptive.firm_name
            or account.state is distinct from descriptive.state
            or account.hubspot_lifecycle_stage is distinct from descriptive.hubspot_lifecycle_stage
        )

    union all

    select
        'product firm on hubspot account' as violation,
        account.account_version_id as detail
    from {{ ref('int_account') }} as account
    inner join company_identity
        on company_identity.hubspot_company_id = account.hubspot_company_id
    left join product_identity
        on product_identity.source_system = 'hubspot'
        and product_identity.hubspot_company_id = account.hubspot_company_id
    where not company_identity.duplicate_from_first
        and account.product_firm_id is distinct from product_identity.product_firm_id

    union all

    select
        'product-only row' as violation,
        product_identity.product_firm_id as detail
    from product_identity
    inner join ordered_product_firms
        on ordered_product_firms.product_firm_id = product_identity.product_firm_id
    left join {{ ref('int_account') }} as account
        on account.product_firm_id = product_identity.product_firm_id
        and account.hubspot_company_id is null
    where product_identity.source_system = 'product'
        and (
            account.account_id is null
            or account.firm_name is distinct from ordered_product_firms.firm_name
            or account.primary_domain is distinct from ordered_product_firms.primary_domain
            or account.state is distinct from ordered_product_firms.state
            or account.segment is not null
            or account.practice_focus is not null
            or account.icp_fit is not null
            or account.owner_name is not null
            or account.hubspot_lifecycle_stage is not null
            or account.hubspot_company_id is not null
            or account.effective_start is distinct from ordered_product_firms.ingested_at
            or account.effective_end is not null
            or not account.is_current
            or (
                select count(*)
                from {{ ref('int_account') }} as product_rows
                where product_rows.product_firm_id = product_identity.product_firm_id
                    and product_rows.hubspot_company_id is null
            ) <> 1
        )

    union all

    select
        'column list' as violation,
        column_name as detail
    from information_schema.columns
    where table_schema = '{{ target.schema }}'
        and table_name = 'int_account'
        and column_name in (
            'commercial_status',
            'customer_converted',
            'adoption_reached',
            'pipeline_amount',
            'booking_amount',
            'arr'
        )

)

select violation, detail
from violations
