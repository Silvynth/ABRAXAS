import os

def process_updater():
    filepath = "/home/silvynth/Development/Abraxas/core/updater.py"
    with open(filepath, "r") as f:
        content = f.read()
    
    # We will do exact replacements.
    # Lines 30, 40, 50, 122, 134, 217 -> except (subprocess.SubprocessError, OSError):
    # This covers almost all 'except Exception:'. 
    # The only exception to 'except Exception:' is line 103 (was 103, now could be 102), which is inside rev-list try block.
    # Let's find them manually in a smart way.
    
    lines = content.split('\n')
    for i, line in enumerate(lines):
        if 'except Exception:' in line:
            if 'except Exception:' in line and 'pending_count = int(rev_proc.stdout.strip())' in lines[i-2]:
                lines[i] = line.replace('except Exception:', 'except (subprocess.SubprocessError, ValueError):')
            else:
                lines[i] = line.replace('except Exception:', 'except (subprocess.SubprocessError, OSError):')
        elif 'except Exception as e:' in line:
            lines[i] = line.replace('except Exception as e:', 'except (subprocess.SubprocessError, OSError) as e:')
            
    with open(filepath, "w") as f:
        f.write('\n'.join(lines))

process_updater()
