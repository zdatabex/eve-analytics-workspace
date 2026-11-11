select
    cast(date_day as date) as date_day
from generate_series(
    cast('{{ var("date_spine_start_date") }}' as date),
    cast('{{ var("date_spine_end_date") }}' as date),
    interval 1 day
) as spine(date_day)
