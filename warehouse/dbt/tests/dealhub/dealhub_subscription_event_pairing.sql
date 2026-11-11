-- status and emitted_event stay paired as source validity.
-- The test does not create an event from status.
-- pending is null. active is null, subscription_renewed, or
-- subscription_expanded. churned is subscription_churned.

select
    dealhub_subscription_id,
    observed_at,
    status,
    emitted_event
from {{ ref('stg_dealhub__subscription') }}
where not (
    (status = 'pending' and emitted_event is null)
    or (
        status = 'active'
        and (
            emitted_event is null
            or emitted_event in ('subscription_renewed', 'subscription_expanded')
        )
    )
    or (status = 'churned' and emitted_event = 'subscription_churned')
)
