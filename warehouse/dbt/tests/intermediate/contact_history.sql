-- Contact version bounds, tracked firm, role, and email, descriptive overlay, and duplicate collapse.
-- unique, not_null, accepted_values, and relationships cannot express this rule.

with recursive contact_observations as (

    select
        hubspot_contact_id,
        observed_at,
        hubspot_company_id,
        full_name,
        email_normalized,
        title,
        buying_role,
        case
            when hubspot_company_id is null then null
            else {{ dbt_utils.generate_surrogate_key(["'hubspot'", 'hubspot_company_id']) }}
        end as account_id
    from {{ ref('stg_hubspot__contact') }}

),

contact_created as (

    select
        hubspot_contact_id,
        min(observed_at) as first_observed_at,
        row_number() over (
            order by min(observed_at), hubspot_contact_id
        ) as creation_rank
    from contact_observations
    group by hubspot_contact_id

),

ordered_contact_observations as (

    select
        row_number() over (
            order by contact_observations.observed_at, contact_observations.hubspot_contact_id
        ) as seq,
        contact_observations.hubspot_contact_id,
        contact_observations.observed_at,
        contact_observations.email_normalized,
        contact_created.creation_rank
    from contact_observations
    inner join contact_created
        on contact_observations.hubspot_contact_id = contact_created.hubspot_contact_id

),

latest_contact_observation as (

    select
        hubspot_contact_id,
        account_id,
        full_name,
        email_normalized,
        title,
        buying_role
    from contact_observations
    qualify row_number() over (
        partition by hubspot_contact_id
        order by observed_at desc
    ) = 1

),

-- Walk contact observations in time order. A blank email matches nothing.
-- Once a person is a duplicate, a later email change does not clear or move that link.
contact_walk as (

    select
        0 as step,
        []::struct(
            hubspot_contact_id varchar,
            email varchar,
            is_survivor boolean,
            survivor_id varchar,
            creation_rank bigint,
            became_duplicate_at timestamp,
            duplicate_from_first boolean
        )[] as contacts

    union all

    select
        prepared.step + 1 as step,
        case
            when prepared.is_first
                and (
                    prepared.email_normalized is null
                    or prepared.match_id is null
                )
                then list_append(
                    prepared.contacts,
                    struct_pack(
                        hubspot_contact_id := prepared.hubspot_contact_id,
                        email := prepared.email_normalized,
                        is_survivor := true,
                        survivor_id := prepared.hubspot_contact_id,
                        creation_rank := prepared.creation_rank,
                        became_duplicate_at := null::timestamp,
                        duplicate_from_first := false
                    )
                )
            when prepared.is_first
                then list_append(
                    prepared.contacts,
                    struct_pack(
                        hubspot_contact_id := prepared.hubspot_contact_id,
                        email := prepared.email_normalized,
                        is_survivor := false,
                        survivor_id := prepared.match_id,
                        creation_rank := prepared.creation_rank,
                        became_duplicate_at := prepared.observed_at,
                        duplicate_from_first := true
                    )
                )
            else list_transform(
                prepared.contacts,
                lambda c: case
                    when c.hubspot_contact_id = prepared.hubspot_contact_id then
                        case
                            when not c.is_survivor
                                then struct_update(c, email := prepared.email_normalized)
                            when prepared.email_normalized is null
                                or prepared.match_id is null
                                then struct_update(c, email := prepared.email_normalized)
                            when c.creation_rank > prepared.match_rank
                                then struct_pack(
                                    hubspot_contact_id := c.hubspot_contact_id,
                                    email := prepared.email_normalized,
                                    is_survivor := false,
                                    survivor_id := prepared.match_id,
                                    creation_rank := c.creation_rank,
                                    became_duplicate_at := prepared.observed_at,
                                    duplicate_from_first := false
                                )
                            else struct_update(c, email := prepared.email_normalized)
                        end
                    when prepared.match_id is not null
                        and c.hubspot_contact_id = prepared.match_id
                        and prepared.self_is_survivor
                        and prepared.self_rank < prepared.match_rank
                        and prepared.email_normalized is not null
                        then struct_pack(
                            hubspot_contact_id := c.hubspot_contact_id,
                            email := c.email,
                            is_survivor := false,
                            survivor_id := prepared.hubspot_contact_id,
                            creation_rank := c.creation_rank,
                            became_duplicate_at := prepared.observed_at,
                            duplicate_from_first := false
                        )
                    else c
                end
            )
        end as contacts
    from (
        select
            contact_walk.step,
            contact_walk.contacts,
            ordered_contact_observations.hubspot_contact_id,
            ordered_contact_observations.email_normalized,
            ordered_contact_observations.observed_at,
            ordered_contact_observations.creation_rank,
            not list_contains(
                list_transform(contact_walk.contacts, lambda c: c.hubspot_contact_id),
                ordered_contact_observations.hubspot_contact_id
            ) as is_first,
            (
                select match_row.hubspot_contact_id
                from unnest(list_filter(
                    contact_walk.contacts,
                    lambda c: c.is_survivor
                        and ordered_contact_observations.email_normalized is not null
                        and c.email = ordered_contact_observations.email_normalized
                        and c.hubspot_contact_id <> ordered_contact_observations.hubspot_contact_id
                )) as match_row
                order by match_row.creation_rank
                limit 1
            ) as match_id,
            (
                select match_row.creation_rank
                from unnest(list_filter(
                    contact_walk.contacts,
                    lambda c: c.is_survivor
                        and ordered_contact_observations.email_normalized is not null
                        and c.email = ordered_contact_observations.email_normalized
                        and c.hubspot_contact_id <> ordered_contact_observations.hubspot_contact_id
                )) as match_row
                order by match_row.creation_rank
                limit 1
            ) as match_rank,
            (
                select self_row.is_survivor
                from unnest(list_filter(
                    contact_walk.contacts,
                    lambda c: c.hubspot_contact_id = ordered_contact_observations.hubspot_contact_id
                )) as self_row
                limit 1
            ) as self_is_survivor,
            (
                select self_row.creation_rank
                from unnest(list_filter(
                    contact_walk.contacts,
                    lambda c: c.hubspot_contact_id = ordered_contact_observations.hubspot_contact_id
                )) as self_row
                limit 1
            ) as self_rank
        from contact_walk
        inner join ordered_contact_observations
            on ordered_contact_observations.seq = contact_walk.step + 1
    ) as prepared

),

contact_identity as (

    select
        contact.hubspot_contact_id,
        contact.is_survivor,
        contact.survivor_id as survivor_contact_id,
        contact.became_duplicate_at,
        contact.duplicate_from_first,
        {{ dbt_utils.generate_surrogate_key(["'hubspot'", 'contact.hubspot_contact_id']) }} as contact_id,
        case
            when contact.is_survivor then null
            else {{ dbt_utils.generate_surrogate_key(["'hubspot'", 'contact.survivor_id']) }}
        end as surviving_contact_id
    from contact_walk
    cross join unnest(contact_walk.contacts) as contact
    where contact_walk.step = (select max(step) from contact_walk)

),

history_input as (

    select
        contact_observations.hubspot_contact_id,
        contact_observations.observed_at,
        contact_observations.account_id,
        contact_observations.buying_role,
        contact_observations.email_normalized,
        contact_observations.full_name,
        contact_observations.title
    from contact_observations
    inner join contact_identity
        on contact_observations.hubspot_contact_id = contact_identity.hubspot_contact_id
    where
        not contact_identity.duplicate_from_first
        and (
            contact_identity.became_duplicate_at is null
            or contact_observations.observed_at <= contact_identity.became_duplicate_at
        )

),

contact_versions as (

    {{ effective_date(
        'history_input',
        ['hubspot_contact_id'],
        'observed_at',
        ['account_id', 'buying_role', 'email_normalized']
    ) }}

),

violations as (

    select
        'version key' as violation,
        contact_version_id as detail
    from {{ ref('int_contact') }}
    where contact_version_id is distinct from {{ dbt_utils.generate_surrogate_key(['contact_id', 'effective_start']) }}

    union all

    select
        'open row' as violation,
        contact_id as detail
    from {{ ref('int_contact') }}
    group by contact_id
    having count(*) filter (where is_current) <> 1
        or count(*) filter (where effective_end is null) <> 1

    union all

    select
        'version gap or overlap' as violation,
        contact_id as detail
    from (
        select
            contact_id,
            effective_end,
            lead(effective_start) over (
                partition by contact_id
                order by effective_start
            ) as next_start
        from {{ ref('int_contact') }}
    ) as spans
    where effective_end is distinct from next_start

    union all

    select
        'duplicate collapse' as violation,
        contact_identity.hubspot_contact_id as detail
    from contact_identity
    left join (
        select hubspot_contact_id, count(*) as row_count
        from {{ ref('int_contact') }}
        group by hubspot_contact_id
    ) as contact_rows
        on contact_rows.hubspot_contact_id = contact_identity.hubspot_contact_id
    where contact_identity.duplicate_from_first
        and contact_rows.row_count is distinct from 1

    union all

    select
        'duplicate from first observation' as violation,
        contact.contact_version_id as detail
    from contact_identity
    inner join contact_created
        on contact_created.hubspot_contact_id = contact_identity.hubspot_contact_id
    inner join latest_contact_observation
        on latest_contact_observation.hubspot_contact_id = contact_identity.hubspot_contact_id
    inner join {{ ref('int_contact') }} as contact
        on contact.hubspot_contact_id = contact_identity.hubspot_contact_id
    where contact_identity.duplicate_from_first
        and (
            contact.full_name is distinct from latest_contact_observation.full_name
            or contact.email_normalized is distinct from latest_contact_observation.email_normalized
            or contact.title is distinct from latest_contact_observation.title
            or contact.buying_role is distinct from latest_contact_observation.buying_role
            or contact.account_id is distinct from latest_contact_observation.account_id
            or contact.effective_start is distinct from contact_created.first_observed_at
            or contact.effective_end is not null
            or not contact.is_current
        )

    union all

    select
        'version bounds' as violation,
        coalesce(contact_versions.hubspot_contact_id, contact.hubspot_contact_id) as detail
    from contact_versions
    full outer join {{ ref('int_contact') }} as contact
        on contact.hubspot_contact_id = contact_versions.hubspot_contact_id
        and contact.effective_start = contact_versions.effective_start
    inner join contact_identity
        on contact_identity.hubspot_contact_id = coalesce(
            contact_versions.hubspot_contact_id,
            contact.hubspot_contact_id
        )
    where not contact_identity.duplicate_from_first
        and (
            contact_versions.hubspot_contact_id is null
            or contact.hubspot_contact_id is null
            or contact_versions.effective_end is distinct from contact.effective_end
        )

    union all

    select
        'tracked firm, role, and email' as violation,
        contact.contact_version_id as detail
    from {{ ref('int_contact') }} as contact
    inner join contact_identity
        on contact_identity.hubspot_contact_id = contact.hubspot_contact_id
    inner join contact_observations
        on contact_observations.hubspot_contact_id = contact.hubspot_contact_id
        and contact_observations.observed_at = contact.effective_start
    where not contact_identity.duplicate_from_first
        and (
            contact.account_id is distinct from contact_observations.account_id
            or contact.buying_role is distinct from contact_observations.buying_role
            or contact.email_normalized is distinct from contact_observations.email_normalized
        )

    union all

    select
        'descriptive overlay' as violation,
        contact.contact_version_id as detail
    from {{ ref('int_contact') }} as contact
    inner join contact_identity
        on contact_identity.hubspot_contact_id = contact.hubspot_contact_id
    inner join (
        select
            contact_version.contact_version_id,
            observation.full_name,
            observation.title,
            row_number() over (
                partition by contact_version.contact_version_id
                order by observation.observed_at desc
            ) as descriptive_rank
        from {{ ref('int_contact') }} as contact_version
        inner join contact_observations as observation
            on observation.hubspot_contact_id = contact_version.hubspot_contact_id
            and observation.observed_at >= contact_version.effective_start
            and (
                contact_version.effective_end is null
                or observation.observed_at < contact_version.effective_end
            )
    ) as descriptive
        on descriptive.contact_version_id = contact.contact_version_id
        and descriptive.descriptive_rank = 1
    where not contact_identity.duplicate_from_first
        and (
            contact.full_name is distinct from descriptive.full_name
            or contact.title is distinct from descriptive.title
        )

    union all

    select
        'column list' as violation,
        column_name as detail
    from information_schema.columns
    where table_schema = '{{ target.schema }}'
        and table_name = 'int_contact'
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
