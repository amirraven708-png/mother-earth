from tld.core.ast_nodes import TLDAST, TLDNode, TLDEdge, TLDBox

class ASTBuilder:
    def __init__(self):
        self.ast = TLDAST()
        self._current_box = None

    def build(self, parse_tree):
        for stmt in parse_tree.children:
            self._process_stmt(stmt)
        return self.ast

    def _process_stmt(self, stmt):
        pass  # در parser.py تکمیل می‌شود
