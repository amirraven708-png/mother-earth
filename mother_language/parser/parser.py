from lark import Lark, Transformer, v_args
import pkg_resources
from mother_language.core.ast_nodes import TLDNode, TLDEdge, TLDBox, TLDAST

class TLDTransformer(Transformer):
    def __init__(self):
        super().__init__()
        self.ast = TLDAST()

    def start(self, items):
        for item in items:
            if isinstance(item, (TLDNode, TLDEdge, TLDBox)):
                self.ast.elements.append(item)
        return self.ast

    @v_args(inline=True)
    def node(self, name, *attrs):
        node = TLDNode(name=str(name))
        return node

    @v_args(inline=True)
    def edge(self, source, arrow, target, *attrs):
        edge_type = "direct"
        if arrow == "-~>":
            edge_type = "fuzzy"
        elif arrow == "<->":
            edge_type = "identity"
        edge = TLDEdge(source=str(source), target=str(target), type=edge_type)
        return edge

    @v_args(inline=True)
    def box(self, *args):
        name = None
        elements = []
        for arg in args:
            if isinstance(arg, str) and arg.startswith('"'):
                name = arg.strip('"')
            elif isinstance(arg, (TLDNode, TLDEdge, TLDBox)):
                elements.append(arg)
        return TLDBox(name=name, elements=elements)

    def ESCAPED_STRING(self, tok):
        return tok.value.strip('"')

    def NUMBER(self, tok):
        return float(tok.value) if '.' in tok.value else int(tok.value)

def get_grammar():
    path = pkg_resources.resource_filename('mother_language', 'parser/grammar.lark')
    with open(path) as f:
        return f.read()

def parse(text: str) -> TLDAST:
    grammar = get_grammar()
    parser = Lark(grammar, start='start', parser='lalr', transformer=TLDTransformer())
    return parser.parse(text)
