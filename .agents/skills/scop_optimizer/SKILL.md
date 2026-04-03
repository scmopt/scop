---
name: scop_optimizer
description: Generates a JSON model to solve complex constraint satisfaction and optimization problems using scop.py
---

# SCOP Optimizer Skill

This skill allows you to formulate an optimization model using a simple JSON format and solve it using the `scop.py` module in the `scop` (スコープ) repository.

## Capabilities
- Solves Constraint Satisfaction Problems (CSPs).
- Supports Variable domains (lists of items/integers).
- Supports Linear Constraints (sum of terms `<` `<=` `>` `>=` `=`).
- Supports Quadratic Constraints (product of two variables).
- Supports Alldiff Constraints (force a list of variables to take distinct values).

## How to use

1. Formulate your problem into the required JSON schema.
2. Save the JSON string out into a temporary file, e.g., `/tmp/scop_model.json`.
3. Use the `run_command` tool to run the provided adapter script:
   ```bash
   uv run python /Users/mikiokubo/Documents/dev/scop/.agents/skills/scop_optimizer/scripts/run_scop_model.py /tmp/scop_model.json
   ```
4. Read the stdout output, which contains the exact JSON response mapping variable names to their active values.

## JSON Schema Structure

```json
{
  "parameters": {
    "TimeLimit": 3,
    "OutputFlag": 0,
    "Initial": false
  },
  "variables": [
    {"name": "workerA", "domain": [0, 1, 2]},
    {"name": "workerB", "domain": [0, 1, 2]}
  ],
  "constraints": {
    "linear": [
      {
        "name": "objective",
        "weight": 1,
        "rhs": 0,
        "direction": "<=",
        "terms": [
          {"coeff": 15, "var": "workerA", "value": 0},
          {"coeff": 20, "var": "workerB", "value": 1}
        ]
      }
    ],
    "quadratic": [
      {
        "name": "conflict",
        "weight": 100,
        "rhs": 0,
        "direction": "=",
        "terms": [
          {"coeff": 1, "var1": "workerA", "val1": 0, "var2": "workerB", "val2": 0}
        ]
      }
    ],
    "alldiff": [
      {
        "name": "unique_assignments",
        "weight": "inf",
        "varlist": ["workerA", "workerB"]
      }
    ]
  }
}
```

- **weight**: Penalty applied for violating soft constraints. Can be an integer or `"inf"` for a hard constraint.
- **direction**: Should be one of `"&lt;="`, `">="`, `"="`.

## Example 1: Assignment Problem
Assign 3 workers (A,B,C) to 3 jobs (0,1,2). Each job must be uniquely assigned (`alldiff`).
```json
{
  "parameters": {
    "TimeLimit": 1
  },
  "variables": [
    {"name": "A", "domain": [0, 1, 2]},
    {"name": "B", "domain": [0, 1, 2]},
    {"name": "C", "domain": [0, 1, 2]}
  ],
  "constraints": {
    "alldiff": [
      {
        "name": "AD",
        "weight": "inf",
        "varlist": ["A", "B", "C"]
      }
    ],
    "linear": [
      {
        "name": "linear_constraint",
        "weight": 1,
        "rhs": 0,
        "direction": "<=",
        "terms": [
          {"coeff": 15, "var": "A", "value": 0},
          {"coeff": 20, "var": "A", "value": 1},
          {"coeff": 30, "var": "A", "value": 2},
          {"coeff": 7, "var": "B", "value": 0},
          {"coeff": 15, "var": "B", "value": 1},
          {"coeff": 12, "var": "B", "value": 2},
          {"coeff": 25, "var": "C", "value": 0},
          {"coeff": 10, "var": "C", "value": 1},
          {"coeff": 13, "var": "C", "value": 2}
        ]
      }
    ]
  }
}
```

## Example 2: Minimal Task Assignment with Conflicts
Workers A and B cannot both do Job 0 (quadratic conflict).
```json
{
  "variables": [
    {"name": "A", "domain": [0, 1]},
    {"name": "B", "domain": [0, 1]}
  ],
  "constraints": {
    "quadratic": [
      {
        "name": "conflict_job0",
        "weight": "inf",
        "rhs": 0,
        "direction": "=",
        "terms": [
          {"coeff": 1, "var1": "A", "val1": 0, "var2": "B", "val2": 0}
        ]
      }
    ],
    "linear": [
      {
        "name": "objective",
        "weight": 1,
        "rhs": 0,
        "direction": "<=",
        "terms": [
          {"coeff": 10, "var": "A", "value": 0},
          {"coeff": 20, "var": "B", "value": 1}
        ]
      }
    ]
  }
}
```
