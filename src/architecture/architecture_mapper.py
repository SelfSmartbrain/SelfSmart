from __future__ import annotations

import ast
import os
from pathlib import Path
from typing import Dict, List, Set, Any
from src.config.logging import get_logger

logger = get_logger(__name__)

class ComponentVisitor(ast.NodeVisitor):
    def __init__(self):
        self.components = []
        self.imports = []

    def visit_ClassDef(self, node: ast.ClassDef):
        self.components.append({
            "name": node.name,
            "type": "class",
            "lineno": node.lineno
        })
        self.generic_visit(node)

    def visit_FunctionDef(self, node: ast.FunctionDef):
        self.components.append({
            "name": node.name,
            "type": "function",
            "lineno": node.lineno
        })
        self.generic_visit(node)
        
    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
        self.components.append({
            "name": node.name,
            "type": "async_function",
            "lineno": node.lineno
        })
        self.generic_visit(node)

    def visit_Import(self, node: ast.Import):
        for alias in node.names:
            self.imports.append(alias.name)
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom):
        if node.module:
            self.imports.append(node.module)
        self.generic_visit(node)


class ArchitectureMapper:
    def __init__(self, root_dir: str):
        self.root_dir = Path(root_dir)
        self.target_dirs = ["src/agents", "src/api", "src/tools"]

    async def scan(self) -> Dict[str, Any]:
        logger.info("Scanning architecture components...")
        graph = {
            "nodes": [],
            "edges": [],
            "stats": {
                "total_files": 0,
                "total_components": 0
            }
        }

        for target in self.target_dirs:
            target_path = self.root_dir / target
            if not target_path.exists():
                logger.warning(f"Target path does not exist: {target_path}")
                continue

            for root, _, files in os.walk(target_path):
                for file in files:
                    if file.endswith(".py"):
                        file_path = Path(root) / file
                        await self._process_file(file_path, graph)

        return graph

    async def _process_file(self, file_path: Path, graph: Dict[str, Any]) -> None:
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            tree = ast.parse(content, filename=str(file_path))
            visitor = ComponentVisitor()
            visitor.visit(tree)

            rel_path = str(file_path.relative_to(self.root_dir))
            
            for comp in visitor.components:
                graph["nodes"].append({
                    "id": f"{rel_path}:{comp['name']}",
                    "file_path": rel_path,
                    "name": comp["name"],
                    "type": comp["type"]
                })
            
            for imp in visitor.imports:
                graph["edges"].append({
                    "source": rel_path,
                    "target": imp,
                    "type": "import"
                })

            graph["stats"]["total_files"] += 1
            graph["stats"]["total_components"] += len(visitor.components)

        except SyntaxError as e:
            logger.error(f"Syntax error in {file_path}: {e}")
        except Exception as e:
            logger.error(f"Error processing {file_path}: {e}")
