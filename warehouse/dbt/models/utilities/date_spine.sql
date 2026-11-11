with date_spine as (

    {{
        dbt_utils.date_spine(
            datepart="day",
            start_date="cast('" ~ var("date_spine_start_date") ~ "' as date)",
            end_date="(cast('" ~ var("date_spine_end_date") ~ "' as date) + 1)"
        )
    }}

)

select cast(date_day as date) as date_day
from date_spine
