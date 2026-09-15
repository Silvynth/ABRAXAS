import re

def process_git_workflow():
    filepath = "/home/silvynth/Development/Abraxas/core/git_workflow.py"
    with open(filepath, "r") as f:
        content = f.read()
    
    # We will split the file by 'try:' and 'except Exception' to analyze
    with open(filepath, "r") as f:
        lines = f.readlines()
        
    for i, line in enumerate(lines):
        if "except Exception" in line:
            # find corresponding try
            try_idx = -1
            indent = len(line) - len(line.lstrip())
            for j in range(i-1, -1, -1):
                if lines[j].strip() == "try:" and (len(lines[j]) - len(lines[j].lstrip())) == indent:
                    try_idx = j
                    break
            
            if try_idx == -1:
                print(f"Warning: could not find try for except at line {i+1}")
                continue
                
            try_block = "".join(lines[try_idx:i])
            
            exceptions = []
            
            # Check contents
            if "subprocess." in try_block:
                exceptions.extend(["subprocess.SubprocessError", "OSError"])
            if "json." in try_block:
                exceptions.append("json.JSONDecodeError")
            if "urllib." in try_block or "request." in try_block:
                exceptions.append("urllib.error.URLError")
            if "open(" in try_block or "os.remove(" in try_block or "os.path." in try_block or "shutil." in try_block or ".write(" in try_block or ".read(" in try_block:
                if "OSError" not in exceptions:
                    exceptions.append("OSError")
            if ".split(" in try_block or ".strip(" in try_block or "int(" in try_block or ".replace(" in try_block or "len(" in try_block or "datetime" in try_block:
                exceptions.extend(["ValueError", "IndexError"])
                
            # Fallback if no specific rule matched
            if not exceptions:
                exceptions.extend(["ValueError", "IndexError"])
                
            # Ensure unique
            unique_ex = []
            for ex in exceptions:
                if ex not in unique_ex:
                    unique_ex.append(ex)
                    
            ex_str = unique_ex[0] if len(unique_ex) == 1 else "(" + ", ".join(unique_ex) + ")"
            
            if "as e:" in line:
                lines[i] = line.replace("except Exception as e:", f"except {ex_str} as e:")
            else:
                lines[i] = line.replace("except Exception:", f"except {ex_str}:")
                
    # Also ensure imports
    imports_to_add = []
    if "import json" not in content: imports_to_add.append("import json")
    if "import urllib.error" not in content and "urllib" in content: imports_to_add.append("import urllib.error")
    # Actually, we don't know what imports are there, let's just prepend them if needed, but the prompt says they should already be there except maybe json/urllib. Let's just add them safely.
    
    with open(filepath, "w") as f:
        f.writelines(lines)
        
    print("Processed git_workflow.py")

process_git_workflow()
