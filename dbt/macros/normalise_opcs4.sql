{#-
    OPCS-4 codes are an uppercase letter followed by two digits, optionally ".xx".
    Strip whitespace and uppercase. Everything else stays verbatim, since OPCS mix of
    dots and no dots is unusual and the vocabulary stores both forms.
-#}
{% macro normalise_opcs4(col) %}
case when {{ col }} is null then null else trim(upper({{ col }})) end
{% endmacro %}
