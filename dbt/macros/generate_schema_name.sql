{#-
    Override dbt's default schema name behaviour. By default dbt concatenates the
    profile's schema with each model's +schema, giving names like 'cdm_cdm' and
    'cdm_etl_meta'. We want the custom schema used directly, so the CDM lives in 'cdm'
    and the ETL metadata in 'etl_meta' as declared in dbt_project.yml.

    Used by the Oxford OMOP Data Mapper and most mature OMOP projects for the same
    reason: standard-named schemas make the CDM look like the CDM.
-#}
{% macro generate_schema_name(custom_schema_name, node) -%}
    {%- if custom_schema_name is none -%}
        {{ target.schema }}
    {%- else -%}
        {{ custom_schema_name | trim }}
    {%- endif -%}
{%- endmacro %}
