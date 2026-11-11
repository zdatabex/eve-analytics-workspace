with observations(entity_id, status, observed_at) as (
    values
        ('entity_1', 'prospect', timestamp '2024-01-01 00:00:00'),
        ('entity_1', 'prospect', timestamp '2024-01-15 00:00:00'),
        ('entity_1', 'customer', timestamp '2024-02-01 00:00:00')
),

effective as (
    {{ effective_date(
        'observations',
        ['entity_id'],
        'observed_at',
        ['status']
    ) }}
),

entity_checks as (
    select entity_id
    from effective
    group by entity_id
    having
        count(*) != 2
        or sum(case when is_current then 1 else 0 end) != 1
),

range_checks as (
    select entity_id
    from effective
    where
        (
            status = 'prospect'
            and (
                effective_start != timestamp '2024-01-01 00:00:00'
                or effective_end != timestamp '2024-02-01 00:00:00'
                or is_current
            )
        )
        or (
            status = 'customer'
            and (
                effective_start != timestamp '2024-02-01 00:00:00'
                or effective_end is not null
                or not is_current
            )
        )
)

select * from entity_checks
union all
select * from range_checks
