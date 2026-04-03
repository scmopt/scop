import sys
import os
import json
import importlib.util

def load_scop_module(scop_path):
    spec = importlib.util.spec_from_file_location("scop", scop_path)
    scop = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(scop)
    return scop

def main():
    original_stdout = sys.stdout
    sys.stdout = open(os.devnull, 'w')
    
    if len(sys.argv) != 2:
        print("Usage: python run_scop_model.py <path_to_json>", file=original_stdout)
        sys.exit(1)
        sys.exit(1)
        
    json_path = sys.argv[1]
    with open(json_path, 'r') as f:
        data = json.load(f)
        
    # Find scop.py: inside the skill directory (.agents/skills/scop_optimizer/)
    script_dir = os.path.dirname(os.path.abspath(__file__))
    scop_path = os.path.abspath(os.path.join(script_dir, "..", "scop.py"))
    
    # fallback to CWD
    if not os.path.exists(scop_path):
        scop_path = os.path.join(os.getcwd(), "scop.py")
        
    if not os.path.exists(scop_path):
        print(json.dumps({"error": f"Could not find scop.py at {scop_path}"}), file=original_stdout)
        sys.exit(1)
        
    scop = load_scop_module(scop_path)
    
    model = scop.Model("scop_json_model")
    
    params = data.get("parameters", {})
    if "TimeLimit" in params:
        model.Params.TimeLimit = params["TimeLimit"]
    if "OutputFlag" in params:
        model.Params.OutputFlag = params["OutputFlag"]
    if "Initial" in params:
        model.Params.Initial = params["Initial"]
        
    variables_map = {}
    for v in data.get("variables", []):
        name = v.get("name")
        domain = v.get("domain", [])
        variables_map[name] = model.addVariable(name=name, domain=domain)
        
    for c_data in data.get("constraints", {}).get("linear", []):
        c = scop.Linear(name=c_data.get("name"), weight=c_data.get("weight", 1), rhs=c_data.get("rhs", 0), direction=c_data.get("direction", "<="))
        for term in c_data.get("terms", []):
            coeff = term["coeff"]
            var_name = term["var"]
            val = term["value"]
            if var_name not in variables_map:
                raise ValueError(f"Variable {var_name} not found")
            c.addTerms(coeff, variables_map[var_name], val)
        model.addConstraint(c)
        
    for c_data in data.get("constraints", {}).get("quadratic", []):
        c = scop.Quadratic(name=c_data.get("name"), weight=c_data.get("weight", 1), rhs=c_data.get("rhs", 0), direction=c_data.get("direction", "<="))
        for term in c_data.get("terms", []):
            coeff = term["coeff"]
            var1 = term["var1"]
            val1 = term["val1"]
            var2 = term["var2"]
            val2 = term["val2"]
            c.addTerms(coeff, variables_map[var1], val1, variables_map[var2], val2)
        model.addConstraint(c)
        
    for c_data in data.get("constraints", {}).get("alldiff", []):
        varlist_names = c_data.get("varlist", [])
        varlist = [variables_map[name] for name in varlist_names]
        c = scop.Alldiff(name=c_data.get("name"), varlist=varlist, weight=c_data.get("weight", 1))
        model.addConstraint(c)
        
    # Execute optimization
    # Must be run from a directory where scop_input.txt can be created and the binary exists
    # If the binary "scop-mac" is in the project root, CWD should be the project root
    original_cwd = os.getcwd()
    os.chdir(os.path.dirname(scop_path))
    
    try:
        sol, violated = model.optimize()
        result = {
            "status": model.Status,
            "solution": sol if sol else {},
            "violated": violated if violated else {}
        }
        print(json.dumps(result, indent=2, ensure_ascii=False), file=original_stdout)
    finally:
        os.chdir(original_cwd)

if __name__ == "__main__":
    main()
