You are a senior Python performance engineer.

I want to build a production-ready Python script that:

1. Takes a .sql file as input.
2. Parses and splits the SQL script into individual executable statements.
3. Executes each SQL statement sequentially against a database.
4. Measures execution time of each statement precisely.
5. Prints:
   - Query number
   - Query text (trimmed)
   - Execution time in milliseconds
   - Rows affected (if applicable)
6. After executing each query, analyze it and suggest performance improvements.

Database support:
- PostgreSQL (primary)
- SQL Server (optional support via config)

Required Features:
- Use proper database connectors:
    - psycopg2 for PostgreSQL
    - pyodbc for SQL Server
- Use time.perf_counter() for precise timing
- Handle:
    - Transactions
    - Errors per query (should not stop entire execution)
    - Rollback on failure
- Pretty console output (use tabulate or rich library)

Performance Analysis Requirements:
For each SELECT query:
- Run EXPLAIN (or EXPLAIN ANALYZE optionally)
- Detect:
    - Sequential Scan
    - Missing index
    - High cost
    - Nested loop joins
    - Full table scan
- Suggest:
    - Add index on filtered columns
    - Avoid SELECT *
    - Add WHERE clause if missing
    - Use LIMIT if large dataset
    - Check join conditions

For INSERT/UPDATE/DELETE:
- Suggest:
    - Batch operations
    - Indexing on WHERE columns
    - Avoid unnecessary triggers
    - Check foreign key constraints

Output Format Example:

------------------------------------------------------------
Query #1
Execution Time: 145.32 ms
Rows Affected: 1200
Performance Warning:
- Sequential Scan detected on table users
Suggestion:
- Create index on users(email)
------------------------------------------------------------

Architecture Requirements:
- Modular structure:
    - load_sql_file()
    - split_queries()
    - execute_query()
    - analyze_query_plan()
    - generate_suggestions()
- Use argparse for CLI:
    python sql_analyzer.py --file script.sql --db postgres

Extra Features (Optional but preferred):
- Save report to JSON file
- Save report to CSV
- Colored output
- Logging support

Important:
- Handle multiline queries
- Handle semicolon splitting correctly
- Ignore comments in SQL file
- Make it production quality

Add advanced query plan parsing.

Parse EXPLAIN output and extract:
- Cost
- Actual time
- Rows
- Buffers
- Planning time
- Execution time

If execution time > 500ms, mark as SLOW QUERY.

Detect:
- Missing indexes
- Large sort operations
- Hash joins
- Bitmap heap scan
- Temporary disk usage

Generate a performance score from 1–10.

At the end print:
- Total execution time
- Top 3 slowest queries
- Optimization summary

Also create a performance report file: performance_report.json

After collecting EXPLAIN output, send it to OpenAI API and ask for performance improvement suggestions.

Integrate OpenAI API to generate smart optimization advice.

add requirement.txt all pip packaged 

Generate complete working code with comments.