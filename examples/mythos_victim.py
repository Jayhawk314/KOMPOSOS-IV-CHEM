
import os
import subprocess

def user_task(cmd):
    """A standard user-level task."""
    print(f"Executing: {cmd}")
    # This call should be flagged by the Sink Sensor
    os.system(cmd)

def admin_root_handler(payload):
    """A privileged handler (inferred by name)."""
    # This call should be flagged by the Sink Sensor
    subprocess.Popen(payload, shell=True)

def bypass_logic(data):
    """
    Parallel paths:
    Path A: Calls user_task
    Path B: Calls admin_root_handler
    
    A 2-cell exists between these parallel calls. 
    Because B has 'root' in the name and uses subprocess, 
    and A uses os.system, the sensors should trigger 
    a Functor Escape or Privilege Non-Commute gap.
    """
    if len(data) > 10:
        user_task(data)
    else:
        admin_root_handler(data)
