# PowerShell / Python Execution Standing Rule

## Rule: Avoid Complex Inline `python -c "..."` Commands in PowerShell

### Context & Failure Mode
In Windows PowerShell environments, passing inline Python code containing single quotes (`'`), escaped quotes (`\'`), backslashes (`\`), or regular expression patterns causes PowerShell's token parser to misinterpret quotation boundaries. Because PowerShell escapes single quotes using `''` (not `\'`), unescaped quotes break the argument string and cause the interactive PowerShell parser to hang indefinitely waiting on `STDIN` for statement continuation, leading to background task deadlocks.

### Mandatory Guideline
1. **Never dispatch inline `python -c "..."` commands** via `run_command` if the Python snippet contains:
   - Single quotes or nested quotation marks
   - Backslashes (e.g. `\b`, `\s`, `\n`, `\d`)
   - Regex patterns or multi-line strings
2. **Standard Workflow**:
   - Write the Python code to a scratch script in the conversation scratch directory (e.g. `<artifactsDir>/scratch/verify_<name>.py`).
   - Execute the script using `run_command` with `python <path_to_script>.py`.
   - Read the output directly from execution.
