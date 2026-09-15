import os

def process_updater():
    filepath = "/home/silvynth/Development/Abraxas/core/updater.py"
    with open(filepath, "r") as f:
        lines = f.readlines()
    
    for i, line in enumerate(lines):
        line_num = i + 1
        if line_num in [30, 40, 50, 122, 134, 217]:
            lines[i] = line.replace("except Exception:", "except (subprocess.SubprocessError, OSError):")
        elif line_num in [83, 174, 194, 208]:
            lines[i] = line.replace("except Exception as e:", "except (subprocess.SubprocessError, OSError) as e:")
        elif line_num == 103:
            lines[i] = line.replace("except Exception:", "except (subprocess.SubprocessError, ValueError):")
            
    with open(filepath, "w") as f:
        f.writelines(lines)

def process_git_workflow():
    filepath = "/home/silvynth/Development/Abraxas/core/git_workflow.py"
    with open(filepath, "r") as f:
        content = f.read()

    # We need to analyze git_workflow.py and replace Exception appropriately.
    # Wait, the prompt says: "Lee el archivo completo, identifica TODOS los bloques..."
    pass

process_updater()
