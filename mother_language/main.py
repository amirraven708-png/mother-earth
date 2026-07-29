import argparse
from mother_language.parser.parser import parse
from mother_language.renderer.svg_renderer import SVGRenderer

def main():
    parser = argparse.ArgumentParser(description="TLD Compiler")
    parser.add_argument("input", help="Input .tld file")
    parser.add_argument("-o", "--output", default="output.svg", help="Output SVG file")
    parser.add_argument("-f", "--format", choices=["svg", "dot"], default="svg")
    args = parser.parse_args()

    with open(args.input, encoding="utf-8") as f:
        source = f.read()
    ast = parse(source)
    if args.format == "svg":
        renderer = SVGRenderer()
        svg = renderer.render(ast)
        with open(args.output, "w") as f:
            f.write(svg)
        print(f"Diagram saved to {args.output}")

if __name__ == "__main__":
    main()
