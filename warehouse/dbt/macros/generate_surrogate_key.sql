{% macro generate_surrogate_key(fields) -%}
    {%- if fields | length == 0 -%}
        {{ exceptions.raise_compiler_error("generate_surrogate_key requires at least one field") }}
    {%- endif -%}
    md5(
        concat(
            {%- for field in fields %}
            case
                when {{ field }} is null then '-1:'
                else concat(
                    length(cast({{ field }} as varchar)),
                    ':',
                    cast({{ field }} as varchar)
                )
            end
            {%- if not loop.last %}, {% endif -%}
            {%- endfor %}
        )
    )
{%- endmacro %}
