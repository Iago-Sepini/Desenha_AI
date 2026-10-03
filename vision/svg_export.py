import svgwrite


def gerar_svg(contornos, tamanho, caminho="desenho.svg"):
    dwg = svgwrite.Drawing(caminho, size=(f"{tamanho}px", f"{tamanho}px"),
                            viewBox=f"0 0 {tamanho} {tamanho}")
    for c in contornos:
        pontos = [(int(p[0][0]), int(p[0][1])) for p in c]
        if len(pontos) > 1:
            dwg.add(dwg.polyline(pontos, stroke="black", fill="none", stroke_width=2))
    dwg.save()
    return caminho