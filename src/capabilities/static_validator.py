from __future__ import annotations
import ast
from src.config.logging import get_logger

logger = get_logger(__name__)

class StaticValidator:
    def __init__(self, forbidden_imports: list[str] | None = None) -> None:
        self.forbidden_imports = forbidden_imports or ["os", "sys", "subprocess", "socket", "builtins"]

    async def validate_code(self, code: str) -> tuple[bool, str]:
        """Parses Python code and rejects dangerous imports and syntax errors."""
        try:
            tree = ast.parse(code)
        except SyntaxError as e:
            msg = f"Syntax error: {e}"
            logger.error(msg)
            return False, msg

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name.split('.')[0] in self.forbidden_imports:
                        msg = f"Forbidden import detected: {alias.name}"
                        logger.error(msg)
                        return False, msg
            elif isinstance(node, ast.ImportFrom):
                if node.module and node.module.split('.')[0] in self.forbidden_imports:
                    msg = f"Forbidden import detected: {node.module}"
                    logger.error(msg)
                    return False, msg

        logger.info("Static validation passed.")
        return True, "Validation successful"
