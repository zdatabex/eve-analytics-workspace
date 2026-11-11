-- When a deal cites a contact, the contact observation in effect at the deal
-- observed_at has the same hubspot_company_id. No in-effect observation fails
-- the check. The observation in effect is the latest observed_at at or before
-- the deal timestamp.

with deal as (

    select
        hubspot_deal_id,
        observed_at,
        hubspot_company_id,
        hubspot_contact_id
    from {{ ref('stg_hubspot__deal') }}
    where hubspot_contact_id is not null

),

in_effect as (

    select
        deal.hubspot_deal_id,
        deal.observed_at,
        deal.hubspot_company_id as deal_company_id,
        contact.hubspot_company_id as contact_company_id,
        contact.observed_at as contact_observed_at
    from deal
    left join {{ ref('stg_hubspot__contact') }} as contact
        on deal.hubspot_contact_id = contact.hubspot_contact_id
        and contact.observed_at <= deal.observed_at
    qualify row_number() over (
        partition by deal.hubspot_deal_id, deal.observed_at
        order by contact.observed_at desc nulls last
    ) = 1

)

select
    hubspot_deal_id,
    observed_at,
    deal_company_id,
    contact_company_id
from in_effect
where contact_observed_at is null
    or contact_company_id is distinct from deal_company_id
