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
-- Demoting a survivor re-points firms that already linked to it onto the earlier survivor.
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
                    when prepared.match_id is not null
                        and not c.is_survivor
                        and prepared.self_is_survivor
                        and prepared.self_rank < prepared.match_rank
                        and prepared.primary_domain is not null
                        and c.survivor_id = prepared.match_id
                        then struct_update(
                            c,
                            survivor_id := prepared.hubspot_company_id
                        )
                    when prepared.match_id is not null
                        and not c.is_survivor
                        and prepared.self_is_survivor
                        and prepared.self_rank > prepared.match_rank
                        and prepared.primary_domain is not null
                        and c.survivor_id = prepared.hubspot_company_id
                        then struct_update(
                            c,
                            survivor_id := prepared.match_id
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

version_descriptive as (

    select
        hubspot_versions.hubspot_company_id,
        hubspot_versions.effective_start,
        company_observations.firm_name,
        company_observations.state,
        company_observations.hubspot_lifecycle_stage,
        row_number() over (
            partition by hubspot_versions.hubspot_company_id, hubspot_versions.effective_start
            order by company_observations.observed_at desc
        ) as descriptive_rank
    from hubspot_versions
    inner join company_observations
        on company_observations.hubspot_company_id = hubspot_versions.hubspot_company_id
        and company_observations.observed_at >= hubspot_versions.effective_start
        and (
            hubspot_versions.effective_end is null
            or company_observations.observed_at < hubspot_versions.effective_end
        )

),

versioned_hubspot_rows as (

    select
        {{ dbt_utils.generate_surrogate_key(['company_identity.account_id', 'hubspot_versions.effective_start']) }} as account_version_id,
        company_identity.account_id,
        company_identity.surviving_account_id,
        hubspot_versions.hubspot_company_id,
        product_identity.product_firm_id,
        version_descriptive.firm_name,
        hubspot_versions.primary_domain,
        version_descriptive.state,
        hubspot_versions.segment,
        hubspot_versions.practice_focus,
        hubspot_versions.icp_fit,
        hubspot_versions.owner_name,
        version_descriptive.hubspot_lifecycle_stage,
        hubspot_versions.effective_end is null as is_current,
        hubspot_versions.effective_start,
        hubspot_versions.effective_end
    from hubspot_versions
    inner join company_identity
        on company_identity.hubspot_company_id = hubspot_versions.hubspot_company_id
    inner join version_descriptive
        on version_descriptive.hubspot_company_id = hubspot_versions.hubspot_company_id
        and version_descriptive.effective_start = hubspot_versions.effective_start
        and version_descriptive.descriptive_rank = 1
    left join product_identity
        on product_identity.hubspot_company_id = hubspot_versions.hubspot_company_id
        and product_identity.source_system = 'hubspot'

),

from_first_duplicate_rows as (

    select
        {{ dbt_utils.generate_surrogate_key(['company_identity.account_id', 'company_created.first_observed_at']) }} as account_version_id,
        company_identity.account_id,
        company_identity.surviving_account_id,
        company_identity.hubspot_company_id,
        cast(null as varchar) as product_firm_id,
        latest_company_observation.firm_name,
        latest_company_observation.primary_domain,
        latest_company_observation.state,
        latest_company_observation.segment,
        latest_company_observation.practice_focus,
        latest_company_observation.icp_fit,
        latest_company_observation.owner_name,
        latest_company_observation.hubspot_lifecycle_stage,
        true as is_current,
        company_created.first_observed_at as effective_start,
        cast(null as timestamp) as effective_end
    from company_identity
    inner join company_created
        on company_created.hubspot_company_id = company_identity.hubspot_company_id
    inner join latest_company_observation
        on latest_company_observation.hubspot_company_id = company_identity.hubspot_company_id
    where company_identity.duplicate_from_first

),

product_rows as (

    select
        {{ dbt_utils.generate_surrogate_key(['product_account_id', 'ordered_product_firms.ingested_at']) }} as account_version_id,
        product_account_id as account_id,
        surviving_account_id,
        cast(null as varchar) as hubspot_company_id,
        ordered_product_firms.product_firm_id,
        ordered_product_firms.firm_name,
        ordered_product_firms.primary_domain,
        ordered_product_firms.state,
        cast(null as varchar) as segment,
        cast(null as varchar) as practice_focus,
        cast(null as varchar) as icp_fit,
        cast(null as varchar) as owner_name,
        cast(null as varchar) as hubspot_lifecycle_stage,
        true as is_current,
        ordered_product_firms.ingested_at as effective_start,
        cast(null as timestamp) as effective_end
    from (
        select
            product_identity.product_firm_id,
            {{ dbt_utils.generate_surrogate_key(["'product'", 'product_identity.product_firm_id']) }} as product_account_id,
            case
                when product_identity.is_survivor then null
                when product_identity.survivor_source = 'hubspot'
                    then {{ dbt_utils.generate_surrogate_key(["'hubspot'", 'product_identity.survivor_id']) }}
                else {{ dbt_utils.generate_surrogate_key(["'product'", 'product_identity.survivor_id']) }}
            end as surviving_account_id
        from product_identity
        where product_identity.source_system = 'product'
    ) as product_accounts
    inner join ordered_product_firms
        on ordered_product_firms.product_firm_id = product_accounts.product_firm_id

),

account_rows as (

    select * from versioned_hubspot_rows
    union all
    select * from from_first_duplicate_rows
    union all
    select * from product_rows

)

select
    account_version_id,
    account_id,
    surviving_account_id,
    hubspot_company_id,
    product_firm_id,
    firm_name,
    primary_domain,
    state,
    segment,
    practice_focus,
    icp_fit,
    owner_name,
    hubspot_lifecycle_stage,
    is_current,
    effective_start,
    effective_end
from account_rows
