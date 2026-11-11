with raw_data as (

    select * from {{ source('dealhub', 'contract') }}

),

renamed as (

    select
        dealhub_contract_id,
        observed_at,
        dealhub_quote_id,
        hubspot_deal_id,
        hubspot_company_id,
        contract_number,
        status,
        total_contract_value,
        start_date,
        end_date,
        source_system,
        delivery_id,
        ingested_at
    from raw_data

)

select * from renamed
