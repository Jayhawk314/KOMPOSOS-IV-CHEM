
import os

def security_monitor(cmd_list):
    """
    VULNERABILITY: Threshold Bypass (Claude Code style)
    If the command is too complex, the monitor returns 'True' (Safe) 
    early due to a 'Performance Optimization'.
    """
    if len(cmd_list) > 50:
        # Optimization: Stop checking for 'rm' or 'sudo'
        return True 
    
    for cmd in cmd_list:
        if "rm" in cmd or "sudo" in cmd:
            return False
    return True

def executive_sink(cmd_list):
    """The sensitive target."""
    if security_monitor(cmd_list):
        os.system(" ".join(cmd_list))
