-- Reconcile each staged HubSpot model to its landed source table.
-- The approved exception set is empty: a difference in row count, unique key,
-- column set, or any contracted column value fails this check.

{% set entities = [
    {
        "name": "company",
        "model": "stg_hubspot__company",
        "key_columns": ["hubspot_company_id", "observed_at"],
        "columns": [
            "hubspot_company_id",
            "firm_name",
            "primary_domain",
            "state",
            "segment",
            "practice_focus",
            "icp_fit",
            "owner_name",
            "hubspot_lifecycle_stage",
            "observed_at",
            "source_system",
            "delivery_id",
            "ingested_at",
        ],
    },
    {
        "name": "contact",
        "model": "stg_hubspot__contact",
        "key_columns": ["hubspot_contact_id", "observed_at"],
        "columns": [
            "hubspot_contact_id",
            "full_name",
            "email_normalized",
            "title",
            "buying_role",
            "observed_at",
            "hubspot_company_id",
            "source_system",
            "delivery_id",
            "ingested_at",
        ],
    },
    {
        "name": "lead",
        "model": "stg_hubspot__lead",
        "key_columns": ["hubspot_lead_id", "observed_at"],
        "columns": [
            "hubspot_lead_id",
            "status",
            "created_at",
            "observed_at",
            "emitted_event",
            "hubspot_company_id",
            "hubspot_contact_id",
            "marketing_campaign_id",
            "hubspot_deal_id",
            "source_system",
            "delivery_id",
            "ingested_at",
        ],
    },
    {
        "name": "deal",
        "model": "stg_hubspot__deal",
        "key_columns": ["hubspot_deal_id", "observed_at"],
        "columns": [
            "hubspot_deal_id",
            "opportunity_name",
            "opportunity_type",
            "stage",
            "amount",
            "expected_close_date",
            "owner_name",
            "forecast_category",
            "created_at",
            "observed_at",
            "emitted_event",
            "hubspot_company_id",
            "hubspot_contact_id",
            "hubspot_lead_id",
            "dealhub_subscription_id",
            "source_system",
            "delivery_id",
            "ingested_at",
        ],
    },
    {
        "name": "activity",
        "model": "stg_hubspot__activity",
        "key_columns": ["hubspot_activity_id"],
        "columns": [
            "hubspot_activity_id",
            "activity_type",
            "subject",
            "occurred_at",
            "hubspot_company_id",
            "hubspot_contact_id",
            "hubspot_lead_id",
            "hubspot_deal_id",
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
    {% set key_detail %}
        concat_ws(
            '|',
            {% for key in entity.key_columns %}
            coalesce(cast({{ key }} as varchar), '<null>'){% if not loop.last %},{% endif %}
            {% endfor %}
        )
    {% endset %}

    select
        '{{ entity.name }}' as entity,
        'column_set' as check_name,
        column_name as detail
    from (
        (
            select lower(column_name) as column_name
            from (describe select * from {{ ref(entity.model) }})
            except
            select lower(column_name) as column_name
            from (describe select * from {{ source('hubspot', entity.name) }})
        )
        union all
        (
            select lower(column_name) as column_name
            from (describe select * from {{ source('hubspot', entity.name) }})
            except
            select lower(column_name) as column_name
            from (describe select * from {{ ref(entity.model) }})
        )
    ) as column_diff

    union all

    select
        '{{ entity.name }}' as entity,
        'row_count' as check_name,
        'staged=' || cast(staged_count as varchar)
            || ' source=' || cast(source_count as varchar) as detail
    from (
        select
            (select count(*) from {{ ref(entity.model) }}) as staged_count,
            (select count(*) from {{ source('hubspot', entity.name) }}) as source_count
    ) as counts
    where staged_count <> source_count

    union all

    select
        '{{ entity.name }}' as entity,
        'unique_key' as check_name,
        {{ key_detail }} as detail
    from (
        (
            select {{ key_sql }}
            from {{ ref(entity.model) }}
            except all
            select {{ key_sql }}
            from {{ source('hubspot', entity.name) }}
        )
        union all
        (
            select {{ key_sql }}
            from {{ source('hubspot', entity.name) }}
            except all
            select {{ key_sql }}
            from {{ ref(entity.model) }}
        )
    ) as key_diff

    union all

    select
        '{{ entity.name }}' as entity,
        'column_value' as check_name,
        cast(to_json(value_diff) as varchar) as detail
    from (
        (
            select {{ column_sql }}
            from {{ ref(entity.model) }}
            except all
            select {{ column_sql }}
            from {{ source('hubspot', entity.name) }}
        )
        union all
        (
            select {{ column_sql }}
            from {{ source('hubspot', entity.name) }}
            except all
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
