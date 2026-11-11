{% macro effective_date(relation, entity_key, observed_at, tracked_columns) %}
    {%- if entity_key | length == 0 -%}
        {{ exceptions.raise_compiler_error("effective_date requires at least one entity key") }}
    {%- endif -%}
    {%- if tracked_columns | length == 0 -%}
        {{ exceptions.raise_compiler_error("effective_date requires at least one tracked column") }}
    {%- endif -%}

    with ordered_observations as (
        select
            *,
            row_number() over (
                partition by
                    {%- for column in entity_key %}
                    {{ column }}{% if not loop.last %}, {% endif %}
                    {%- endfor %}
                order by {{ observed_at }}
            ) as _effective_row_number
            {%- for column in tracked_columns %},
            {{ column }} is distinct from lag({{ column }}) over (
                partition by
                    {%- for key_column in entity_key %}
                    {{ key_column }}{% if not loop.last %}, {% endif %}
                    {%- endfor %}
                order by {{ observed_at }}
            ) as _{{ loop.index }}_changed
            {%- endfor %}
        from {{ relation }}
    ),

    changed_observations as (
        select
            * exclude (
                _effective_row_number
                {%- for column in tracked_columns %},
                _{{ loop.index }}_changed
                {%- endfor %}
            )
        from ordered_observations
        where
            _effective_row_number = 1
            {%- for column in tracked_columns %}
            or _{{ loop.index }}_changed
            {%- endfor %}
    ),

    dated_observations as (
        select
            *,
            {{ observed_at }} as effective_start,
            lead({{ observed_at }}) over (
                partition by
                    {%- for column in entity_key %}
                    {{ column }}{% if not loop.last %}, {% endif %}
                    {%- endfor %}
                order by {{ observed_at }}
            ) as effective_end
        from changed_observations
    )

    select
        *,
        effective_end is null as is_current
    from dated_observations
{% endmacro %}
