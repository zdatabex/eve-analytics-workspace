-- One quote, contract, or subscription identifier has one document number across observations, and one document number belongs to one identifier.
-- unique on the number would fail repeated observations. Booking stays out of this test because booking_number already has unique. unique, not_null, accepted_values, relationships, not_empty_string, accepted_range, and expression_is_true cannot express this rule.

-- One source identifier has one document number, and one document number
-- belongs to one source identifier. Booking numbers are unique on the model.

with failures as (

    select
        'quote' as entity,
        'identifier_has_many_document_numbers' as check_name,
        dealhub_quote_id as detail
    from {{ ref('stg_dealhub__quote') }}
    group by dealhub_quote_id
    having count(distinct quote_number) > 1

    union all

    select
        'quote' as entity,
        'document_number_shared_by_identifiers' as check_name,
        quote_number as detail
    from {{ ref('stg_dealhub__quote') }}
    group by quote_number
    having count(distinct dealhub_quote_id) > 1

    union all

    select
        'contract' as entity,
        'identifier_has_many_document_numbers' as check_name,
        dealhub_contract_id as detail
    from {{ ref('stg_dealhub__contract') }}
    group by dealhub_contract_id
    having count(distinct contract_number) > 1

    union all

    select
        'contract' as entity,
        'document_number_shared_by_identifiers' as check_name,
        contract_number as detail
    from {{ ref('stg_dealhub__contract') }}
    group by contract_number
    having count(distinct dealhub_contract_id) > 1

    union all

    select
        'subscription' as entity,
        'identifier_has_many_document_numbers' as check_name,
        dealhub_subscription_id as detail
    from {{ ref('stg_dealhub__subscription') }}
    group by dealhub_subscription_id
    having count(distinct subscription_number) > 1

    union all

    select
        'subscription' as entity,
        'document_number_shared_by_identifiers' as check_name,
        subscription_number as detail
    from {{ ref('stg_dealhub__subscription') }}
    group by subscription_number
    having count(distinct dealhub_subscription_id) > 1

)

select
    entity,
    check_name,
    detail
from failures
