-- Reconcile each staged DealHub model to its landed source table.
-- No exception set is approved. The test fails when an observation key is
-- missing, duplicated, or present on only one side, when the column set
-- differs, or when any contracted column on that key differs.
-- Null matches null. Amounts, dates, and timestamps are compared as stored.

{% set entities = [
    {
        "name": "quote",
        "model": "stg_dealhub__quote",
        "key_columns": ["dealhub_quote_id", "observed_at"],
        "columns": [
            "dealhub_quote_id",
            "quote_number",
            "status",
            "quoted_amount",
            "observed_at",
            "hubspot_deal_id",
            "hubspot_company_id",
            "source_system",
            "delivery_id",
            "ingested_at",
        ],
    },
    {
        "name": "contract",
        "model": "stg_dealhub__contract",
        "key_columns": ["dealhub_contract_id", "observed_at"],
        "columns": [
            "dealhub_contract_id",
            "contract_number",
            "status",
            "total_contract_value",
            "start_date",
            "end_date",
            "observed_at",
            "dealhub_quote_id",
            "hubspot_deal_id",
            "hubspot_company_id",
            "source_system",
            "delivery_id",
            "ingested_at",
        ],
    },
    {
        "name": "subscription",
        "model": "stg_dealhub__subscription",
        "key_columns": ["dealhub_subscription_id", "observed_at"],
        "columns": [
            "dealhub_subscription_id",
            "subscription_number",
            "status",
            "plan_code",
            "seat_count",
            "recurring_amount",
            "billing_frequency",
            "term_start",
            "term_end",
            "observed_at",
            "emitted_event",
            "dealhub_contract_id",
            "hubspot_company_id",
            "source_system",
            "delivery_id",
            "ingested_at",
        ],
    },
    {
        "name": "booking",
        "model": "stg_dealhub__booking",
        "key_columns": ["dealhub_booking_id"],
        "columns": [
            "dealhub_booking_id",
            "booking_number",
            "booking_type",
            "booking_amount",
            "booked_at",
            "hubspot_company_id",
            "hubspot_deal_id",
            "dealhub_contract_id",
            "dealhub_subscription_id",
            "source_system",
            "delivery_id",
            "ingested_at",
        ],
    },
] %}

with failures as (

    {% for entity in entities %}
    {% set column_sql = entity.columns | join(", ") %}
    {% set key_sql = entity.key_columns | join(", ") %}

    select
        '{{ entity.name }}' as entity,
        'column_set' as check_name,
        column_name || ':' || column_type as detail
    from (
        (
            select
                lower(column_name) as column_name,
                lower(column_type) as column_type
            from (describe select * from {{ ref(entity.model) }})
            except
            select
                lower(column_name) as column_name,
                lower(column_type) as column_type
            from (describe select * from {{ source('dealhub', entity.name) }})
        )
        union all
        (
            select
                lower(column_name) as column_name,
                lower(column_type) as column_type
            from (describe select * from {{ source('dealhub', entity.name) }})
            except
            select
                lower(column_name) as column_name,
                lower(column_type) as column_type
            from (describe select * from {{ ref(entity.model) }})
        )
    ) as column_diff

    union all

    select
        '{{ entity.name }}' as entity,
        'observation_key' as check_name,
        concat_ws(
            '|',
            {% for key in entity.key_columns %}
            coalesce(
                cast(coalesce(staged.{{ key }}, landed.{{ key }}) as varchar),
                '<null>'
            ){% if not loop.last %},{% endif %}
            {% endfor %}
        )
            || ' staged=' || cast(coalesce(staged.staged_count, 0) as varchar)
            || ' landed=' || cast(coalesce(landed.landed_count, 0) as varchar) as detail
    from (
        select
            {{ key_sql }},
            count(*) as staged_count
        from {{ ref(entity.model) }}
        group by {{ key_sql }}
    ) as staged
    full outer join (
        select
            {{ key_sql }},
            count(*) as landed_count
        from {{ source('dealhub', entity.name) }}
        group by {{ key_sql }}
    ) as landed
        on {% for key in entity.key_columns %}
            staged.{{ key }} is not distinct from landed.{{ key }}
            {% if not loop.last %}and{% endif %}
        {% endfor %}
    where coalesce(staged.staged_count, 0) <> 1
        or coalesce(landed.landed_count, 0) <> 1

    union all

    select
        '{{ entity.name }}' as entity,
        'column_value' as check_name,
        cast(to_json(value_diff) as varchar) as detail
    from (
        (
            select {{ column_sql }}
            from {{ ref(entity.model) }}
            except
            select {{ column_sql }}
            from {{ source('dealhub', entity.name) }}
        )
        union all
        (
            select {{ column_sql }}
            from {{ source('dealhub', entity.name) }}
            except
            select {{ column_sql }}
            from {{ ref(entity.model) }}
        )
    ) as value_diff

    {% if not loop.last %}
    union all
    {% endif %}
    {% endfor %}

)

select
    entity,
    check_name,
    detail
from failures
