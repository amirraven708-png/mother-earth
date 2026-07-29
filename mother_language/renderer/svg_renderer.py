from mother_language.core.ast_nodes import TLDAST, TLDNode, TLDEdge, TLDBox

class SVGRenderer:
    def render(self, ast: TLDAST) -> str:
        elements_svg = []
        width, height = 800, 600
        x, y = 50, 50
        for elem in ast.elements:
            if isinstance(elem, TLDNode):
                elements_svg.append(f'<text x="{x}" y="{y}" font-family="monospace">{elem.name}</text>')
                x += 100
            elif isinstance(elem, TLDEdge):
                elements_svg.append(f'<line x1="50" y1="30" x2="150" y2="30" stroke="black"/><text x="100" y="20">{elem.label or ""}</text>')
            elif isinstance(elem, TLDBox):
                elements_svg.append(f'<rect x="10" y="10" width="200" height="100" fill="none" stroke="black"/><text x="20" y="30">{elem.name or "Box"}</text>')
        svg = f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}">{chr(10)}{"".join(elements_svg)}{chr(10)}</svg>'
        return svg
