"""Prompt templates for LLM use cases."""

SQL_EXTRACTION_SYSTEM = """\
You are a Java/SQL expert. You analyze DAO (Data Access Object) Java classes \
and extract structured information about the SQL queries they execute.

You must output valid JSON only — no explanations, no markdown fences."""

SQL_EXTRACTION_PROMPT = """\
Analyze the following Java DAO class and extract all SQL queries executed by its public methods.

For each public method, provide:
1. The method name
2. The primary table being queried
3. All WHERE clause conditions with column, operator, value ("?" for parameterized, or the literal), and the corresponding DTO/parameter field name
4. Any JOIN conditions (left_table, left_column, right_table, right_column)
5. Any hardcoded literal values in the query (column, value)

**Important instructions:**
- Resolve all string constants — follow `private static final String` fields to get the actual SQL fragments
- Concatenate fragmented SQL strings into the full query
- For `findByVariables` / `findAllByVariables` calls, map the ConditionType enums:
  - EQUALS → "="
  - NOTEQUALS → "<>"
  - MORETHANEQUALS → ">="
  - LESSTHANEQUALS → "<="
  - LESSTHAN → "<"
  - MORETHAN → ">"
  - IN → "IN"
  - NOTIN → "NOT IN"
- For `String.format` calls, resolve the format string with its arguments
- Map SQL column names to DTO field names using camelCase conventions (e.g., INSPOL_STS_TAG → inspolStsTag)
- Only include public methods that execute SQL queries
- Skip private/helper methods unless they are called by a public method

Output a JSON array of objects with this schema:
[
  {{
    "method": "<method name>",
    "table": "<primary table>",
    "conditions": [
      {{
        "column": "<SQL column>",
        "operator": "<SQL operator>",
        "value": "<? or literal>",
        "dto_field": "<camelCase field>"
      }}
    ],
    "joins": [
      {{
        "left_table": "<table>",
        "left_column": "<column>",
        "right_table": "<table>",
        "right_column": "<column>"
      }}
    ],
    "hardcoded_values": [
      {{
        "column": "<column>",
        "value": "<literal value>"
      }}
    ]
  }}
]

---

Java DAO class:

{dao_source}"""

CONSTRAINT_SOLVING_SYSTEM = """\
You are a test data generation expert. Given a Java method signature and a \
set of constraints, you generate concrete input values that satisfy all \
constraints and cause the specified execution path to be taken.

You must output valid JSON only — no explanations, no markdown fences."""

CONSTRAINT_SOLVING_PROMPT = """\
Generate concrete input values for the following Java method that satisfy \
all constraints below.

**Method signature:**
{method_signature}

**Constraints to satisfy (all must hold simultaneously):**
{constraints}

**Variable types:**
{variable_types}

Output a JSON object mapping parameter names to concrete values:
{{
  "param1": <value>,
  "param2": <value>
}}

Values must be valid for their Java types. For strings, provide a realistic \
value that satisfies the constraint."""

VALIDATION_REPROMPT = """\
The values you generated did not produce the expected result.

**Expected path:** {expected_path}
**Actual result:** {actual_result}

Please try again with different values that satisfy ALL of these constraints:
{constraints}

Output a JSON object mapping parameter names to concrete values."""
