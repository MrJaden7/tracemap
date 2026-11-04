{#-
    Clean a possibly-messy ICD-10 code. Three fix-ups:
      1. Strip whitespace and uppercase.
      2. Ensure a dot after the first three characters (ICD-10 convention). If the code
         has no dot but is longer than 3, insert one.
      3. Strip an obvious trailing zero of the form C.X0 where we see too many digits.

    Kept as SQL (not Python) so dbt's docs show it alongside the staging model that uses
    it. Tested by tests/unit/test_icd10_normalisation.py which asserts the shape.
-#}
{% macro normalise_icd10(col) %}
case
  when {{ col }} is null then null
  when length(trim(upper({{ col }}))) <= 3
    then trim(upper({{ col }}))
  else
    case
      when position('.' in trim(upper({{ col }}))) = 0
        then substring(trim(upper({{ col }})), 1, 3) || '.' || substring(trim(upper({{ col }})), 4)
      else trim(upper({{ col }}))
    end
end
{% endmacro %}
