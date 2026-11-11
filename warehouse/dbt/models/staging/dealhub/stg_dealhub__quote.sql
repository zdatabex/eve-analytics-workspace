with raw_data as (

    select * from {{ source('dealhub', 'quote') }}

),

renamed as (

    select
        dealhub_quote_id,
        observed_at,
        hubspot_deal_id,
        hubspot_company_id,
        quote_number,
        status,
        quoted_amount,
        source_system,
        delivery_id,
        ingested_at
    from raw_data

)

select * from renamed
