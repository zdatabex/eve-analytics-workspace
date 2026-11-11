-- Compares observations of one deal: created_at and hubspot_company_id are stable, hubspot_lead_id does not change within the deal, one opportunity_opened row is discovery at created_at, a stage change carries the matching emitted_event, won and lost occur at most once and not together, and one lead belongs to one deal.
-- unique, not_null, accepted_values, relationships, not_empty_string, accepted_range, and expression_is_true cannot express this comparison across observations.

-- Deal rules that compare observations of one hubspot_deal_id, plus the rule
-- that one lead identifier belongs to one deal. A violating row stays in the
-- model. This check only reports it.

with deal as (

    select * from {{ ref('stg_hubspot__deal') }}

),

ordered as (

    select
        hubspot_deal_id,
        observed_at,
        stage,
        emitted_event,
        lag(stage) over (
            partition by hubspot_deal_id
            order by observed_at
        ) as prior_stage
    from deal

),

by_deal as (

    select
        hubspot_deal_id,
        count(distinct created_at) as created_at_values,
        count(distinct hubspot_company_id) as company_values,
        count(distinct hubspot_lead_id) as lead_values,
        count(*) filter (where emitted_event = 'opportunity_opened') as opened_count,
        count(*) filter (where emitted_event = 'opportunity_won') as won_count,
        count(*) filter (where emitted_event = 'opportunity_lost') as lost_count
    from deal
    group by hubspot_deal_id

),

lead_owners as (

    select
        hubspot_lead_id,
        count(distinct hubspot_deal_id) as deal_count
    from deal
    where hubspot_lead_id is not null
    group by hubspot_lead_id

),

failures as (

    select
        hubspot_deal_id,
        cast(null as varchar) as observed_at,
        'created_at_or_company_changes' as violation
    from by_deal
    where created_at_values > 1
        or company_values > 1

    union all

    select
        hubspot_deal_id,
        cast(null as varchar) as observed_at,
        'lead_changes_within_deal' as violation
    from by_deal
    where lead_values > 1

    union all

    select
        hubspot_deal_id,
        cast(null as varchar) as observed_at,
        'opportunity_opened_count' as violation
    from by_deal
    where opened_count <> 1

    union all

    select
        hubspot_deal_id,
        cast(observed_at as varchar) as observed_at,
        'opportunity_opened_is_not_discovery_at_created_at' as violation
    from deal
    where emitted_event = 'opportunity_opened'
        and (
            stage <> 'discovery'
            or observed_at <> created_at
        )

    union all

    select
        hubspot_deal_id,
        cast(observed_at as varchar) as observed_at,
        'stage_change_signal' as violation
    from ordered
    where prior_stage is not null
        and (
            (stage = prior_stage and emitted_event is not null)
            or (
                stage <> prior_stage
                and stage in ('evaluation', 'proposal', 'negotiation')
                and emitted_event is distinct from 'opportunity_stage_changed'
            )
            or (
                stage <> prior_stage
                and stage = 'closed_won'
                and emitted_event is distinct from 'opportunity_won'
            )
            or (
                stage <> prior_stage
                and stage = 'closed_lost'
                and emitted_event is distinct from 'opportunity_lost'
            )
        )

    union all

    select
        hubspot_deal_id,
        cast(null as varchar) as observed_at,
        'won_and_lost' as violation
    from by_deal
    where won_count > 1
        or lost_count > 1
        or (won_count > 0 and lost_count > 0)

    union all

    select
        hubspot_lead_id as hubspot_deal_id,
        cast(null as varchar) as observed_at,
        'lead_belongs_to_more_than_one_deal' as violation
    from lead_owners
    where deal_count > 1

)

select
    hubspot_deal_id,
    observed_at,
    violation
from failures
