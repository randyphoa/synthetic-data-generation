# Synthetic Data Generator for Java Path Coverage

Generate synthetic test inputs that achieve **full path coverage** of Java methods — every execution path from method entry to leaf node is exercised by at least one generated row.

## Background

Path coverage is the strictest practical coverage criterion for acyclic control flow. It subsumes line and branch coverage by testing every unique sequence of decisions, catching bugs that only surface under specific combinations of conditions. For `if`/`else` trees without loops, paths are bounded by the branching structure, making full enumeration feasible.

Manually writing inputs to cover every path is tedious and error-prone. This tool automates it: parse Java source, build control flow graphs, enumerate all paths, and solve the constraints with Z3 to produce concrete input values. For constraints Z3 cannot handle (string methods, regex, object field access), an LLM generates valid values instead.

## Installation

Requires Python >= 3.11.

```bash
uv venv
uv pip install -e ".[dev]"
```

## Quick Start

```bash
synthetic-data MyService.java                    # analyze a single file
synthetic-data MyService.java -f json            # output as JSON
synthetic-data MyService.java -m classify        # analyze one method
synthetic-data src/main/java/com/example/        # process a directory
```

## How It Works

**Phase 1 — Parse & Build CFG.** Parses Java source with [tree-sitter](https://tree-sitter.github.io/tree-sitter/) and builds a Control Flow Graph per method. Branching becomes `DecisionNode`s, statements become `StatementNode`s, terminals (return/throw) become `LeafNode`s.

**Phase 2 — Enumerate Paths & Extract Conditions.** Traverses the CFG from entry to every leaf, collecting the conjunction of constraints for each path. Compound conditions (`&&`, `||`) are expanded into disjunctive normal form with short-circuit semantics. Each atomic condition is classified as **Z3-solvable** (numeric comparisons, booleans) or **LLM-required** (string methods, method calls, complex expressions).

**Phase 3 — Solve Constraints.** Z3 solves numeric/boolean constraints deterministically. An LLM fallback handles what Z3 cannot. Boundary values are generated at comparison thresholds (e.g., `x < 18` produces rows for `x=17` and `x=18`). Edge cases inject type-specific extremes (0, -1, MIN/MAX_VALUE, null, empty string). Dead paths are detected and reported.

**Phase 4 — Assemble Output.** Deduplicates and writes rows to CSV or JSON. Each row includes input values, expected output, path ID, and row type (path/boundary/edge).

## Example

```java
public class CustomerClassifier {
    public String classify(int age, double income, boolean isMember) {
        if (age < 18) {
            return "junior";
        } else if (age >= 65) {
            if (isMember) return "senior_member";
            else return "senior";
        } else {
            if (income > 50000 && isMember) return "premium";
            else if (income > 50000) return "standard_plus";
            else return "standard";
        }
    }
}
```

```bash
synthetic-data CustomerClassifier.java
```

```csv
age,income,isMember,expected_output,path_id,row_type
10,30000.0,false,junior,1,path
70,40000.0,true,senior_member,2,path
70,40000.0,false,senior,3,path
30,80000.0,true,premium,4,path
30,80000.0,false,standard_plus,5,path
30,30000.0,false,standard,6,path
17,30000.0,false,junior,1,boundary
18,30000.0,false,standard,6,boundary
0,30000.0,false,junior,1,edge
```

All 6 paths covered, plus boundary rows at `age=17/18/64/65` and `income=50000/50001`, plus edge cases for type extremes.

## CLI Reference

```
synthetic-data <source> [options]
```

| Option | Description | Default |
|--------|-------------|---------|
| `source` | `.java` file or directory | (required) |
| `-o, --output` | Output file path | `dataset.csv` / `dataset.json` |
| `-f, --format` | `csv` or `json` | `csv` |
| `-m, --method` | Analyze only this method | all |
| `--no-boundary` | Skip boundary values | off |
| `--no-edge-cases` | Skip edge cases | off |
| `--call-chain` | Inter-procedural call chain analysis | off |
| `--inline-depth N` | Max call inlining depth | `2` |
| `--max-paths N` | Max paths before stopping inlining | `256` |

## Call Chain Analysis

By default, methods are analyzed in isolation — calls to other methods in the same class are opaque. The `--call-chain` flag inlines callee CFGs into the caller before path enumeration:

- **Return values** — `boolean ok = validate(x)` + `if (ok)`: callee return paths constrain the caller
- **Field side effects** — `validateInput()` sets `this.isValidInput`, flowing into the caller's decisions
- **Conditional calls** — callees are only inlined on branches where they are actually called

```bash
synthetic-data MyService.java --call-chain
synthetic-data MyService.java --call-chain --inline-depth 3
synthetic-data MyService.java --call-chain --max-paths 512
```

**Out of scope:** object parameter internals, cross-class calls, loops, recursion.

## LLM Configuration

The LLM handles SQL extraction from DAO classes and serves as a fallback solver for constraints Z3 cannot handle. Uses IBM Watson Orchestrate with IAM token authentication.

```bash
export IBM_API_KEY=your-ibm-cloud-api-key
export LLM_ENDPOINT=https://api.us-south.watson-orchestrate.cloud.ibm.com/instances/<instance-id>/v1/orchestrate/gateway/model/chat/completions
export LLM_MODEL=groq/openai/gpt-oss-120b  # optional
```

