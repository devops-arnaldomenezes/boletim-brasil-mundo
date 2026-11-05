"""Cenas Manim das vinhetas animadas (abertura e transições de seção).

Renderizado por boletim/vinhetas.py. Parâmetros chegam pela variável de ambiente BOLETIM_VINHETA (JSON).
Cada cena dura exatamente DURACAO segundos, para casar com a vinheta sonora.
"""
import json
import os

import numpy as np

from manim import (DOWN, LEFT, ORIGIN, PI, RIGHT, UP, Arc, Circle, Create, Dot, Ellipse, FadeIn, Group, ImageMobject, FadeOut, LaggedStart,
                   Line, Rectangle, Rotate, Scene, Text, VGroup, Write, config, rate_functions)

P = json.loads(os.environ.get("BOLETIM_VINHETA", "{}"))
DURACAO = float(P.get("duracao", 3.0))
FONTE = P.get("fonte", "DejaVu Sans")
AMBAR = P.get("ambar", "#F5A623")
NOITE = P.get("noite", "#0B1F3A")
VERDE = P.get("verde", "#00A86B")


def globo(raio=1.3, cor="#FFFFFF"):
    g = VGroup(Circle(radius=raio, color=cor, stroke_width=9))
    g.add(Ellipse(width=2 * raio * 0.44, height=2 * raio, color=cor, stroke_width=6))
    g.add(Line(LEFT * raio, RIGHT * raio, color=cor, stroke_width=6))
    for y in (-0.55, 0.55):
        largura = 2 * raio * (1 - y * y) ** 0.5
        g.add(Line(LEFT * largura / 2, RIGHT * largura / 2, color=cor, stroke_width=5, stroke_opacity=0.8)
              .shift(UP * y * raio))
    return g


def simbolo(raio=1.3):
    """Símbolo da marca: globo + órbita âmbar (relógio) que termina no sol das 6h."""
    g = globo(raio)
    r = raio * 1.5
    orbita = Arc(radius=r, start_angle=PI, angle=-(1.5 * PI - 0.21), color=AMBAR, stroke_width=14)
    sol = Dot(DOWN * r, radius=raio * 0.25, color=AMBAR)
    brasil = Dot(np.array([-0.32 * raio, -0.31 * raio, 0]), radius=raio * 0.11, color=VERDE)
    return VGroup(orbita, g, brasil, sol)


class Abertura(Scene):
    def construct(self):
        self.camera.background_color = NOITE
        s = simbolo().shift(LEFT * 4)
        nome = Text("BRASIL E MUNDO", font=FONTE, weight="BOLD", font_size=48)
        hoje = Text("HOJE", font=FONTE, weight="BOLD", font_size=48, color=AMBAR)
        titulo = VGroup(nome, hoje).arrange(RIGHT, buff=0.25)
        titulo.next_to(s, RIGHT, buff=0.9).shift(UP * 0.5)
        data = Text(P.get("data", ""), font=FONTE, font_size=26, color="#DCE3EE").next_to(titulo, DOWN, buff=0.3)
        data.align_to(titulo, LEFT)
        regioes = VGroup(*[Text(r, font=FONTE, font_size=22, color=AMBAR, weight="BOLD")
                           for r in ("BRASIL", "EUROPA", "EUA", "ÁSIA")]).arrange(RIGHT, buff=0.6)
        regioes.next_to(data, DOWN, buff=0.45).align_to(titulo, LEFT)
        bloco = VGroup(s, titulo, data, regioes)
        if bloco.width > config.frame_width * 0.9:
            bloco.scale_to_fit_width(config.frame_width * 0.9)
        bloco.move_to(ORIGIN)
        orbita, g, brasil, sol = s
        t = DURACAO
        self.play(Create(g), Create(orbita), Write(titulo), run_time=t * 0.38, rate_func=rate_functions.ease_out_cubic)
        self.play(FadeIn(sol, scale=2.5), FadeIn(brasil, scale=3), FadeIn(data, shift=UP * 0.2), run_time=t * 0.27)
        self.play(LaggedStart(*[FadeIn(r, shift=UP * 0.2) for r in regioes], lag_ratio=0.25), run_time=t * 0.25)
        self.wait(t * 0.1)


class Transicao(Scene):
    def construct(self):
        self.camera.background_color = P.get("cor", NOITE)
        cor2 = P.get("cor2", "#1F4E8C")
        w, h = config.frame_width, config.frame_height
        faixas = VGroup(*[Rectangle(width=w * 1.6, height=0.35 + 0.25 * i, fill_color=cor2, fill_opacity=0.55 - 0.12 * i,
                                    stroke_width=0).rotate(0.35).shift(DOWN * (1.6 - 1.1 * i)) for i in range(4)])
        faixas.add(Rectangle(width=w * 1.6, height=0.08, fill_color=AMBAR, fill_opacity=1, stroke_width=0)
                   .rotate(0.35).shift(DOWN * 2.3))
        for f in faixas:
            f.shift(LEFT * w * 1.6)
        titulo = Text(P.get("titulo", "").upper(), font=FONTE, weight="BOLD", font_size=60)
        if titulo.width > w * 0.85:
            titulo.scale_to_fit_width(w * 0.85)
        barra = Line(LEFT, RIGHT, color=AMBAR, stroke_width=8).set_width(titulo.width * 0.4)
        barra.next_to(titulo, DOWN, buff=0.35)
        png = P.get("simbolo_png")
        mini = ImageMobject(png).set_height(0.75) if png and os.path.exists(png) else simbolo(0.22)
        nome = Text("BRASIL E MUNDO", font=FONTE, weight="BOLD", font_size=20)
        hoje = Text("HOJE", font=FONTE, weight="BOLD", font_size=20, color=AMBAR)
        texto = VGroup(nome, hoje).arrange(RIGHT, buff=0.12)
        marca = Group(mini, texto).arrange(RIGHT, buff=0.25)
        marca.to_corner(UP + LEFT, buff=0.4)
        t = DURACAO
        self.add(marca)
        self.play(LaggedStart(*[f.animate.shift(RIGHT * w * 1.6) for f in faixas], lag_ratio=0.12),
                  run_time=t * 0.4, rate_func=rate_functions.ease_out_cubic)
        self.play(Write(titulo), Create(barra), run_time=t * 0.35)
        self.wait(t * 0.1)
        self.play(FadeOut(faixas, shift=RIGHT), run_time=t * 0.15)
