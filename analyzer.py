import os
import ast
import re
from pathlib import Path
from collections import defaultdict
import json

def analyze_codebase(root_dir):
    report = {
        "files_analyzed": 0,
        "syntax_errors": [],
        "todos": [],
        "not_implemented": [],
        "hardcoded_values": [],
        "imports": defaultdict(list),
        "file_summaries": {}
    }

    # Regex patterns
    todo_pattern = re.compile(r'(?i)#\s*(todo|fixme)\b.*')
    hardcoded_pattern = re.compile(r'(?i)(api_key|password|secret|token)\s*=\s*[\'"][^\'"]+[\'"]')
    ip_pattern = re.compile(r'\b(?:\d{1,3}\.){3}\d{1,3}\b')
    url_pattern = re.compile(r'https?://[^\s\'"]+')

    for filepath in Path(root_dir).rglob("*.py"):
        if 'venv' in str(filepath) or '.venv' in str(filepath) or '__pycache__' in str(filepath):
            continue
        
        report["files_analyzed"] += 1
        rel_path = filepath.relative_to(root_dir)
        rel_path_str = str(rel_path)
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
                lines = content.split('\n')
        except Exception as e:
            report["syntax_errors"].append({"file": rel_path_str, "error": f"Failed to read file: {e}"})
            continue

        # AST Analysis for syntax errors and imports
        try:
            tree = ast.parse(content)
            
            # Find imports
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        report["imports"][rel_path_str].append(alias.name)
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        report["imports"][rel_path_str].append(node.module)
                        
        except SyntaxError as e:
            report["syntax_errors"].append({
                "file": rel_path_str,
                "line": e.lineno,
                "error": str(e)
            })

        # Regex Analysis line by line
        for i, line in enumerate(lines, 1):
            if todo_match := todo_pattern.search(line):
                report["todos"].append({"file": rel_path_str, "line": i, "content": todo_match.group(0).strip()})
            
            if 'NotImplementedError' in line or 'raise NotImplemented' in line:
                report["not_implemented"].append({"file": rel_path_str, "line": i, "content": line.strip()})
                
            if hardcoded_match := hardcoded_pattern.search(line):
                report["hardcoded_values"].append({"file": rel_path_str, "line": i, "type": "secret", "content": line.strip()})
                
            if ip_match := ip_pattern.search(line):
                # ignore 0.0.0.0 and 127.0.0.1 which are common defaults
                if ip_match.group(0) not in ('0.0.0.0', '127.0.0.1'):
                     report["hardcoded_values"].append({"file": rel_path_str, "line": i, "type": "ip", "content": line.strip()})
                     
            if url_match := url_pattern.search(line):
                 # ignore localhost urls and standard schemas
                 url = url_match.group(0)
                 if 'localhost' not in url and 'schema.org' not in url:
                     report["hardcoded_values"].append({"file": rel_path_str, "line": i, "type": "url", "content": url})

    return report

if __name__ == "__main__":
    report = analyze_codebase("/Users/subh/Documents/ModelX")
    
    with open("/Users/subh/Documents/ModelX/analysis_report.json", "w") as f:
         json.dump(report, f, indent=2)
    print("Analysis complete. Saved to analysis_report.json")
