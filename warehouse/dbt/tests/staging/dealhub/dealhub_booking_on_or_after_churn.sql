-- subscription_churned occurs at most once per subscription, and no booking of that subscription has booked_at on or after that observation's observed_at. ingested_at stays out of the comparison.
-- unique, not_null, accepted_values, relationships, not_empty_string, accepted_range, and expression_is_true cannot express this rule.

-- For each subscription, subscription_churned occurs on at most one row, and
-- no booking of that subscription has booked_at on or after that row's
-- observed_at. ingested_at is not part of the comparison.

with churn_observations as (

    select
        dealhub_subscription_id,
        observed_at
    from {{ ref('stg_dealhub__subscription') }}
    where emitted_event = 'subscription_churned'

),

repeated_churn as (

    select
        dealhub_subscription_id,
        count(*) as churn_row_count
    from churn_observations
    group by dealhub_subscription_id
    having count(*) > 1

),

bookings_on_or_after_churn as (

    select
        booking.dealhub_booking_id,
        booking.booked_at,
        churn_observations.observed_at as churn_observed_at
    from {{ ref('stg_dealhub__booking') }} as booking
    inner join churn_observations
        on booking.dealhub_subscription_id = churn_observations.dealhub_subscription_id
        and booking.booked_at >= churn_observations.observed_at

)

select
    'repeated_subscription_churned' as check_name,
    repeated_churn.dealhub_subscription_id as detail
from repeated_churn

union all

select
    'booking_on_or_after_churn' as check_name,
    bookings_on_or_after_churn.dealhub_booking_id
        || ' booked_at=' || cast(bookings_on_or_after_churn.booked_at as varchar)
        || ' churn_observed_at=' || cast(bookings_on_or_after_churn.churn_observed_at as varchar) as detail
from bookings_on_or_after_churn
