"""Cenas Manim das vinhetas animadas (abertura e transições de seção).

Renderizado por boletim/vinhetas.py. Parâmetros chegam pela variável de ambiente BOLETIM_VINHETA (JSON).
Cada cena dura exatamente DURACAO segundos, para casar com a vinheta sonora.
"""
import json
import os

import numpy as np

from manim import (DOWN, LEFT, ORIGIN, RIGHT, UP, Circle, Create, Dot, Ellipse, FadeIn, FadeOut, LaggedStart,
                   Line, Rectangle, Rotate, Scene, Text, VGroup, Write, config, rate_functions)

P = json.loads(os.environ.get("BOLETIM_VINHETA", "{}"))
DURACAO = float(P.get("duracao", 3.0))
FONTE = "DejaVu Sans"


def globo(raio=1.3, cor="#FFFFFF"):
    g = VGroup(Circle(radius=raio, color=cor, stroke_width=4))
    for k in (0.35, 0.7):
        g.add(Ellipse(width=2 * raio * k, height=2 * raio, color=cor, stroke_width=2, stroke_opacity=0.7))
    for y in (-0.5, 0, 0.5):
        largura = 2 * raio * (1 - y * y) ** 0.5
        g.add(Line(LEFT * largura / 2, RIGHT * largura / 2, color=cor, stroke_width=2, stroke_opacity=0.7)
              .shift(UP * y * raio))
    return g


class Abertura(Scene):
    def construct(self):
        self.camera.background_color = P.get("cor", "#0B3D91")
        g = globo().shift(LEFT * 4)
        titulo = Text(P.get("titulo", "BRASIL E MUNDO HOJE").upper(), font=FONTE, weight="BOLD", font_size=44)
        titulo.next_to(g, RIGHT, buff=0.8).shift(UP * 0.45)
        data = Text(P.get("data", ""), font=FONTE, font_size=26, color="#E3F2FD").next_to(titulo, DOWN, buff=0.3)
        data.align_to(titulo, LEFT)
        regioes = VGroup(*[Text(r, font=FONTE, font_size=22, color=P.get("cor2", "#90CAF9"), weight="BOLD")
                           for r in ("BRASIL", "EUROPA", "EUA", "ÁSIA")]).arrange(RIGHT, buff=0.6)
        regioes.next_to(data, DOWN, buff=0.45).align_to(titulo, LEFT)
        pontos = VGroup(*[Dot(g.get_center() + 1.3 * np.array(v), radius=0.07, color=P.get("cor2", "#90CAF9"))
                          for v in ((-0.3, 0.2, 0), (0.25, 0.55, 0), (-0.55, 0.45, 0), (0.6, 0.1, 0))])
        bloco = VGroup(g, titulo, data, regioes, pontos)
        if bloco.width > config.frame_width * 0.9:
            bloco.scale_to_fit_width(config.frame_width * 0.9)
        bloco.move_to(ORIGIN)
        t = DURACAO
        self.play(Create(g), Write(titulo), run_time=t * 0.35)
        self.play(FadeIn(data, shift=UP * 0.2), LaggedStart(*[FadeIn(p, scale=3) for p in pontos], lag_ratio=0.3),
                  Rotate(g[1:3], angle=0.6, about_point=g.get_center()), run_time=t * 0.3)
        self.play(LaggedStart(*[FadeIn(r, shift=UP * 0.2) for r in regioes], lag_ratio=0.25), run_time=t * 0.25)
        self.wait(t * 0.1)


class Transicao(Scene):
    def construct(self):
        self.camera.background_color = P.get("cor", "#0B3D91")
        cor2 = P.get("cor2", "#1E88E5")
        w, h = config.frame_width, config.frame_height
        faixas = VGroup(*[Rectangle(width=w * 1.6, height=0.35 + 0.25 * i, fill_color=cor2, fill_opacity=0.55 - 0.12 * i,
                                    stroke_width=0).rotate(0.35).shift(DOWN * (1.6 - 1.1 * i)) for i in range(4)])
        for f in faixas:
            f.shift(LEFT * w * 1.6)
        titulo = Text(P.get("titulo", "").upper(), font=FONTE, weight="BOLD", font_size=60)
        if titulo.width > w * 0.85:
            titulo.scale_to_fit_width(w * 0.85)
        barra = Line(LEFT, RIGHT, color="#FFFFFF", stroke_width=6).set_width(titulo.width * 0.4)
        barra.next_to(titulo, DOWN, buff=0.35)
        marca = Text(P.get("marca", "BRASIL E MUNDO HOJE"), font=FONTE, font_size=20, color="#FFFFFF")
        marca.set_opacity(0.8).to_corner(UP + LEFT, buff=0.4)
        t = DURACAO
        self.add(marca)
        self.play(LaggedStart(*[f.animate.shift(RIGHT * w * 1.6) for f in faixas], lag_ratio=0.15),
                  run_time=t * 0.4, rate_func=rate_functions.ease_out_cubic)
        self.play(Write(titulo), Create(barra), run_time=t * 0.35)
        self.wait(t * 0.1)
        self.play(FadeOut(faixas, shift=RIGHT), run_time=t * 0.15)
