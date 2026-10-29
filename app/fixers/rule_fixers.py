"""
Role: fixes that need no LLM. The RULES list is checked in order. Add a new class for each
recurring error you see.
"""

import os
try:
    import sandbox
    from fixers.base import Fixer
except ImportError:
    from app import sandbox
    from app.fixers.base import Fixer


class RuffFixer(Fixer):
    name = 'ruff'

    def can_handle(self, f):
        return f.kind == 'lint'

    def fix(self, workdir, f, feedback=''):
        sandbox.run(workdir, 'pip install -q --user ruff && ruff check --fix . ; ruff format .', network=True)


class MissingModuleFixer(Fixer):
    name = 'missing-module'
    KNOWN = {'yaml': 'pyyaml', 'cv2': 'opencv-python', 'PIL': 'pillow', 'sklearn': 'scikit-learn'}

    def can_handle(self, f):
        return f.kind == 'import'

    def fix(self, workdir, f, feedback=''):
        pkg = self.KNOWN.get(f.message, f.message)
        req_path = os.path.join(workdir, 'requirements.txt')
        prefix = ''
        if os.path.exists(req_path):
            content = open(req_path, 'r', encoding='utf-8').read()
            if content and not content.endswith('\n'):
                prefix = '\n'
        with open(req_path, 'a', encoding='utf-8') as fh:
            fh.write(prefix + pkg + '\n')


RULES = [RuffFixer(), MissingModuleFixer()]
