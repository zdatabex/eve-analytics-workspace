-- When an activity names a firm, another parent constrains that firm only from
-- the parent observation in effect at occurred_at. A deal has a company, so a
-- missing in-effect deal observation fails. A contact or a lead constrains the
-- activity only when that in-effect observation has a firm. A parent with no
-- firm does not constrain the activity.

with activity as (

    select
        hubspot_activity_id,
        occurred_at,
        hubspot_company_id,
        hubspot_contact_id,
        hubspot_lead_id,
        hubspot_deal_id
    from {{ ref('stg_hubspot__activity') }}
    where hubspot_company_id is not null

),

deal_in_effect as (

    select
        activity.hubspot_activity_id,
        activity.hubspot_company_id as activity_company_id,
        deal.hubspot_company_id as parent_company_id,
        deal.observed_at as parent_observed_at
    from activity
    left join {{ ref('stg_hubspot__deal') }} as deal
        on activity.hubspot_deal_id = deal.hubspot_deal_id
        and deal.observed_at <= activity.occurred_at
    where activity.hubspot_deal_id is not null
    qualify row_number() over (
        partition by activity.hubspot_activity_id
        order by deal.observed_at desc nulls last
    ) = 1

),

contact_in_effect as (

    select
        activity.hubspot_activity_id,
        activity.hubspot_company_id as activity_company_id,
        contact.hubspot_company_id as parent_company_id
    from activity
    inner join {{ ref('stg_hubspot__contact') }} as contact
        on activity.hubspot_contact_id = contact.hubspot_contact_id
        and contact.observed_at <= activity.occurred_at
    where activity.hubspot_contact_id is not null
    qualify row_number() over (
        partition by activity.hubspot_activity_id
        order by contact.observed_at desc
    ) = 1

),

lead_in_effect as (

    select
        activity.hubspot_activity_id,
        activity.hubspot_company_id as activity_company_id,
        lead.hubspot_company_id as parent_company_id
    from activity
    inner join {{ ref('stg_hubspot__lead') }} as lead
        on activity.hubspot_lead_id = lead.hubspot_lead_id
        and lead.observed_at <= activity.occurred_at
    where activity.hubspot_lead_id is not null
    qualify row_number() over (
        partition by activity.hubspot_activity_id
        order by lead.observed_at desc
    ) = 1

),

failures as (

    select
        hubspot_activity_id,
        'deal' as parent
    from deal_in_effect
    where parent_observed_at is null
        or parent_company_id is distinct from activity_company_id

    union all

    select
        hubspot_activity_id,
        'contact' as parent
    from contact_in_effect
    where parent_company_id is not null
        and parent_company_id <> activity_company_id

    union all

    select
        hubspot_activity_id,
        'lead' as parent
    from lead_in_effect
    where parent_company_id is not null
        and parent_company_id <> activity_company_id

)

select
    hubspot_activity_id,
    parent
from failures
