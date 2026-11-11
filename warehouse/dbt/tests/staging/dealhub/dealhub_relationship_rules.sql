-- One quote is cited by one contract, one hubspot_deal_id is cited by one contract, one subscription keeps one dealhub_contract_id, and the company identifier agrees across the quote and citing contract, the contract and subscription, the contract and booking, and the subscription and booking.
-- relationships checks existence only, so unique, not_null, accepted_values, relationships, not_empty_string, accepted_range, and expression_is_true cannot express this rule.

-- DealHub relationship rules that a column test cannot express.
-- Parent existence is a relationships test. These checks cover citation
-- cardinality, a stable subscription contract, and one shared company
-- identifier across each named parent and child pair.

with quote_citations as (

    select
        dealhub_quote_id as detail
    from {{ ref('stg_dealhub__contract') }}
    group by dealhub_quote_id
    having count(distinct dealhub_contract_id) > 1

),

deal_citations as (

    select
        hubspot_deal_id as detail
    from {{ ref('stg_dealhub__contract') }}
    group by hubspot_deal_id
    having count(distinct dealhub_contract_id) > 1

),

subscription_contracts as (

    select
        dealhub_subscription_id as detail
    from {{ ref('stg_dealhub__subscription') }}
    group by dealhub_subscription_id
    having count(distinct dealhub_contract_id) > 1

),

contract_quote_companies as (

    select
        quote_row.dealhub_quote_id as cited_id,
        quote_row.hubspot_company_id
    from {{ ref('stg_dealhub__quote') }} as quote_row
    inner join (
        select distinct dealhub_quote_id
        from {{ ref('stg_dealhub__contract') }}
    ) as cited
        on quote_row.dealhub_quote_id = cited.dealhub_quote_id

    union all

    select
        dealhub_quote_id as cited_id,
        hubspot_company_id
    from {{ ref('stg_dealhub__contract') }}

),

subscription_contract_companies as (

    select
        contract_row.dealhub_contract_id as cited_id,
        contract_row.hubspot_company_id
    from {{ ref('stg_dealhub__contract') }} as contract_row
    inner join (
        select distinct dealhub_contract_id
        from {{ ref('stg_dealhub__subscription') }}
    ) as cited
        on contract_row.dealhub_contract_id = cited.dealhub_contract_id

    union all

    select
        dealhub_contract_id as cited_id,
        hubspot_company_id
    from {{ ref('stg_dealhub__subscription') }}

),

booking_contract_companies as (

    select
        contract_row.dealhub_contract_id as cited_id,
        contract_row.hubspot_company_id
    from {{ ref('stg_dealhub__contract') }} as contract_row
    inner join (
        select distinct dealhub_contract_id
        from {{ ref('stg_dealhub__booking') }}
    ) as cited
        on contract_row.dealhub_contract_id = cited.dealhub_contract_id

    union all

    select
        dealhub_contract_id as cited_id,
        hubspot_company_id
    from {{ ref('stg_dealhub__booking') }}

),

booking_subscription_companies as (

    select
        subscription_row.dealhub_subscription_id as cited_id,
        subscription_row.hubspot_company_id
    from {{ ref('stg_dealhub__subscription') }} as subscription_row
    inner join (
        select distinct dealhub_subscription_id
        from {{ ref('stg_dealhub__booking') }}
    ) as cited
        on subscription_row.dealhub_subscription_id = cited.dealhub_subscription_id

    union all

    select
        dealhub_subscription_id as cited_id,
        hubspot_company_id
    from {{ ref('stg_dealhub__booking') }}

),

failures as (

    select
        'quote_cited_by_many_contracts' as check_name,
        detail
    from quote_citations

    union all

    select
        'deal_cited_by_many_contracts' as check_name,
        detail
    from deal_citations

    union all

    select
        'subscription_contract_changed' as check_name,
        detail
    from subscription_contracts

    union all

    select
        'contract_quote_company' as check_name,
        cited_id as detail
    from contract_quote_companies
    group by cited_id
    having count(distinct hubspot_company_id) <> 1

    union all

    select
        'subscription_contract_company' as check_name,
        cited_id as detail
    from subscription_contract_companies
    group by cited_id
    having count(distinct hubspot_company_id) <> 1

    union all

    select
        'booking_contract_company' as check_name,
        cited_id as detail
    from booking_contract_companies
    group by cited_id
    having count(distinct hubspot_company_id) <> 1

    union all

    select
        'booking_subscription_company' as check_name,
        cited_id as detail
    from booking_subscription_companies
    group by cited_id
    having count(distinct hubspot_company_id) <> 1

)

select
    check_name,
    detail
from failures
