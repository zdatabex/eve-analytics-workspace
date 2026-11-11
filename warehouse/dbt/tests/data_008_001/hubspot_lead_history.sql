-- Lead rules that compare observations of one hubspot_lead_id.
-- A violating row stays in the model. This check only reports it.

with lead as (

    select * from {{ ref('stg_hubspot__lead') }}

),

by_lead as (

    select
        hubspot_lead_id,
        count(distinct created_at) as created_at_values,
        count(*) filter (where emitted_event = 'lead_created') as lead_created_count,
        count(*) filter (where status = 'qualified') as qualified_count,
        count(*) filter (where status = 'disqualified') as disqualified_count,
        count(*) filter (where status = 'converted') as converted_count,
        max(case when emitted_event = 'lead_qualified' then observed_at end) as qualified_at,
        min(case when emitted_event = 'lead_converted' then observed_at end) as converted_at
    from lead
    group by hubspot_lead_id

),

failures as (

    select
        hubspot_lead_id,
        'created_at_changes_across_observations' as violation
    from by_lead
    where created_at_values > 1

    union all

    select
        hubspot_lead_id,
        'lead_created_count' as violation
    from by_lead
    where lead_created_count <> 1

    union all

    select
        hubspot_lead_id,
        'lead_created_is_not_new_at_created_at' as violation
    from lead
    where emitted_event = 'lead_created'
        and (
            status <> 'new'
            or observed_at <> created_at
        )

    union all

    select
        hubspot_lead_id,
        'terminal_status_repeats' as violation
    from by_lead
    where qualified_count > 1
        or disqualified_count > 1
        or converted_count > 1

    union all

    select
        hubspot_lead_id,
        'qualified_and_disqualified' as violation
    from by_lead
    where qualified_count > 0
        and disqualified_count > 0

    union all

    select
        hubspot_lead_id,
        'lead_converted_before_lead_qualified' as violation
    from by_lead
    where converted_at is not null
        and (
            qualified_at is null
            or converted_at < qualified_at
        )

)

select
    hubspot_lead_id,
    violation
from failures
