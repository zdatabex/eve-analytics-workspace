with source_columns as (

    select
        column_name,
        ordinal_position
    from information_schema.columns
    where table_schema = '{{ source('product', 'user').schema }}'
        and table_name = '{{ source('product', 'user').identifier }}'

),

staged_columns as (

    select
        column_name,
        ordinal_position
    from information_schema.columns
    where table_schema = '{{ ref('stg_product__user').schema }}'
        and table_name = '{{ ref('stg_product__user').identifier }}'

),

column_mismatch as (

    select
        column_name,
        ordinal_position
    from source_columns
    except
    select
        column_name,
        ordinal_position
    from staged_columns

    union all

    select
        column_name,
        ordinal_position
    from staged_columns
    except
    select
        column_name,
        ordinal_position
    from source_columns

),

source_rows as (

    select * from {{ source('product', 'user') }}

),

staged_rows as (

    select * from {{ ref('stg_product__user') }}

),

row_mismatch as (

    select * from (
        select * from source_rows
        except
        select * from staged_rows
    ) as missing_from_staged

    union all

    select * from (
        select * from staged_rows
        except
        select * from source_rows
    ) as extra_in_staged

)

select
    'column_mismatch' as difference_type,
    column_name,
    cast(ordinal_position as varchar) as ordinal_position,
    cast(null as varchar) as row_json
from column_mismatch

union all

select
    'row_mismatch' as difference_type,
    cast(null as varchar) as column_name,
    cast(null as varchar) as ordinal_position,
    to_json(row_mismatch) as row_json
from row_mismatch
