-- The contact identity walk, surrogate contact_id, one contact per hubspot_contact_id, and blank emails staying apart.
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
-- Demoting a survivor re-points people that already linked to that person onto the earlier survivor.
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
                    when prepared.match_id is not null
                        and not c.is_survivor
                        and prepared.self_is_survivor
                        and prepared.self_rank < prepared.match_rank
                        and prepared.email_normalized is not null
                        and c.survivor_id = prepared.match_id
                        then struct_update(
                            c,
                            survivor_id := prepared.hubspot_contact_id
                        )
                    when prepared.match_id is not null
                        and not c.is_survivor
                        and prepared.self_is_survivor
                        and prepared.self_rank > prepared.match_rank
                        and prepared.email_normalized is not null
                        and c.survivor_id = prepared.hubspot_contact_id
                        then struct_update(
                            c,
                            survivor_id := prepared.match_id
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

expected_identity as (

    select
        contact_id,
        surviving_contact_id,
        hubspot_contact_id
    from contact_identity

),

actual_identity as (

    select distinct
        contact_id,
        surviving_contact_id,
        hubspot_contact_id
    from {{ ref('int_contact') }}

),

identity_difference as (

    select
        'missing identity' as violation,
        contact_id,
        hubspot_contact_id
    from expected_identity
    except
    select
        'missing identity' as violation,
        contact_id,
        hubspot_contact_id
    from actual_identity

    union all

    select
        'unexpected identity' as violation,
        contact_id,
        hubspot_contact_id
    from actual_identity
    except
    select
        'unexpected identity' as violation,
        contact_id,
        hubspot_contact_id
    from expected_identity

),

rule_violations as (

    select
        'surrogate contact_id' as violation,
        contact_id,
        hubspot_contact_id
    from {{ ref('int_contact') }}
    where contact_id is distinct from {{ dbt_utils.generate_surrogate_key(["'hubspot'", 'hubspot_contact_id']) }}

    union all

    select
        'one contact per hubspot contact' as violation,
        cast(null as varchar) as contact_id,
        staged.hubspot_contact_id
    from (
        select hubspot_contact_id
        from {{ ref('stg_hubspot__contact') }}
        group by hubspot_contact_id
    ) as staged
    left join (
        select hubspot_contact_id, count(distinct contact_id) as contacts
        from {{ ref('int_contact') }}
        group by hubspot_contact_id
    ) as conformed
        on conformed.hubspot_contact_id = staged.hubspot_contact_id
    where conformed.contacts is distinct from 1

    union all

    select
        'blank email matched' as violation,
        contact.contact_id,
        blank_contact.hubspot_contact_id
    from (
        select hubspot_contact_id
        from {{ ref('stg_hubspot__contact') }}
        group by hubspot_contact_id
        having count(*) filter (where email_normalized is not null) = 0
    ) as blank_contact
    inner join {{ ref('int_contact') }} as contact
        on contact.hubspot_contact_id = blank_contact.hubspot_contact_id
    where contact.surviving_contact_id is not null

    union all

    select
        'linked without a shared email' as violation,
        left_contact.contact_id,
        left_person.hubspot_contact_id
    from (
        select distinct hubspot_contact_id
        from {{ ref('stg_hubspot__contact') }}
    ) as left_person
    inner join (
        select distinct hubspot_contact_id
        from {{ ref('stg_hubspot__contact') }}
    ) as right_person
        on left_person.hubspot_contact_id < right_person.hubspot_contact_id
    inner join {{ ref('int_contact') }} as left_contact
        on left_contact.hubspot_contact_id = left_person.hubspot_contact_id
    inner join {{ ref('int_contact') }} as right_contact
        on right_contact.hubspot_contact_id = right_person.hubspot_contact_id
    where (
            left_contact.contact_id = right_contact.contact_id
            or left_contact.surviving_contact_id = right_contact.contact_id
            or right_contact.surviving_contact_id = left_contact.contact_id
        )
        and not exists (
            select 1
            from {{ ref('stg_hubspot__contact') }} as left_observation
            inner join {{ ref('stg_hubspot__contact') }} as right_observation
                on left_observation.email_normalized = right_observation.email_normalized
                and left_observation.email_normalized is not null
            where left_observation.hubspot_contact_id = left_person.hubspot_contact_id
                and right_observation.hubspot_contact_id = right_person.hubspot_contact_id
        )

    union all

    select
        'shared email among open survivors' as violation,
        cast(null as varchar) as contact_id,
        email_normalized as hubspot_contact_id
    from {{ ref('int_contact') }}
    where is_current
        and surviving_contact_id is null
        and email_normalized is not null
    group by email_normalized
    having count(*) > 1

)

select violation, contact_id, hubspot_contact_id
from identity_difference
union all
select violation, contact_id, hubspot_contact_id
from rule_violations
union all
select
    'survivor link' as violation,
    expected_identity.contact_id,
    expected_identity.hubspot_contact_id
from expected_identity
inner join actual_identity
    on actual_identity.contact_id = expected_identity.contact_id
    and actual_identity.hubspot_contact_id = expected_identity.hubspot_contact_id
where actual_identity.surviving_contact_id is distinct from expected_identity.surviving_contact_id
