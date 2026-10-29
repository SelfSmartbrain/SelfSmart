"""
Role: the plug-in contract. Every fixer edits files inside workdir and returns. It never
commits or pushes. That keeps all the dangerous steps in one reviewed place.
"""


class Fixer:
    name = 'base'

    def can_handle(self, failure):
        return False

    def fix(self, workdir, failure, feedback=''):
        raise NotImplementedError
