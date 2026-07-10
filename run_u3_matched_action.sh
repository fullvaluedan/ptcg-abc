#!/bin/bash
cd /c/Users/danom/ptcg-abc
"/c/Users/danom/ptcg-abc/.venv/Scripts/python.exe" -u analysis/matched_action_extraction.py > analysis/u3_matched_action_run.log 2>&1 < /dev/null
echo "DONE_EXIT=$?" >> analysis/u3_matched_action_run.log
