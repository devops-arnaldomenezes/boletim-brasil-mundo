"""Síntese de voz (edge-tts, vozes neurais pt-BR gratuitas) e montagem do podcast com ffmpeg."""
from __future__ import annotations

import asyncio
import re
import subprocess
from pathlib import Path

from .util import log


def _ff(*args: str) -> None:
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", *args], check=True)


def duracao(arquivo: Path) -> float:
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of",
                          "default=nw=1:nk=1", str(arquivo)], capture_output=True, text=True, check=True)
    return float(out.stdout.strip())


def _ts(seg: float) -> str:
    h, r = divmod(seg, 3600)
    m, s = divmod(r, 60)
    return f"{int(h):02d}:{int(m):02d}:{s:06.3f}".replace(".", ",")


def _frases(texto: str) -> list[str]:
    partes = re.split(r"(?<=[.!?])\s+", texto.strip())
    out = []
    for p in partes:  # quebra frases longas para legenda
        palavras = p.split()
        while len(palavras) > 16:
            out.append(" ".join(palavras[:14]))
            palavras = palavras[14:]
        if palavras:
            out.append(" ".join(palavras))
    return out


async def _edge(texto: str, voz: str, mp3: Path) -> list[tuple[float, float, str]]:
    import edge_tts
    com = edge_tts.Communicate(texto, voz, rate="+5%", boundary="SentenceBoundary")
    cues = []
    with open(mp3, "wb") as f:
        async for chunk in com.stream():
            if chunk["type"] == "audio":
                f.write(chunk["data"])
            elif chunk["type"] in ("SentenceBoundary", "WordBoundary"):
                ini = chunk["offset"] / 1e7
                cues.append((ini, ini + chunk["duration"] / 1e7, chunk["text"]))
    return cues


def _cues_estimados(texto: str, total: float) -> list[tuple[float, float, str]]:
    frases = _frases(texto)
    pesos = [max(len(f.split()), 1) for f in frases]
    soma, t, cues = sum(pesos), 0.0, []
    for f, p in zip(frases, pesos):
        d = total * p / soma
        cues.append((t, t + d, f))
        t += d
    return cues


def sintetizar(texto: str, voz: str, mp3: Path, ppm: int = 150) -> list[tuple[float, float, str]]:
    """Gera MP3 do texto. Retorna legendas (inicio, fim, texto) em segundos."""
    try:
        cues = asyncio.run(_edge(texto, voz, mp3))
        if mp3.stat().st_size < 1000:
            raise RuntimeError("áudio vazio")
        # legendas de frase muito longas são re-fatiadas proporcionalmente
        finos = []
        for ini, fim, t in cues:
            sub = _cues_estimados(t, fim - ini)
            finos += [(ini + a, ini + b, s) for a, b, s in sub]
        return finos or _cues_estimados(texto, duracao(mp3))
    except Exception as e:  # noqa: BLE001
        log.warning("TTS indisponível (%s). Gerando áudio silencioso de contingência.", e)
        segundos = max(len(texto.split()) / ppm * 60, 3)
        _ff("-f", "lavfi", "-i", "anullsrc=r=24000:cl=mono", "-t", f"{segundos:.2f}", "-q:a", "6", str(mp3))
        return _cues_estimados(texto, segundos)


def vinheta(destino: Path, segundos: float = 3.0) -> None:
    """Pequena vinheta sonora gerada (sem direitos autorais) para transição entre seções."""
    _ff("-f", "lavfi", "-i", f"sine=f=660:d={segundos}", "-f", "lavfi", "-i", f"sine=f=990:d={segundos}",
        "-filter_complex", f"[0][1]amix=2,afade=t=in:d=0.05,afade=t=out:st={segundos-0.8}:d=0.8,volume=0.25,"
        "aresample=24000,pan=mono|c0=c0", "-q:a", "4", str(destino))


def montar_podcast(partes: list[Path], destino: Path, titulo: str, data: str) -> None:
    lista = destino.parent / "_concat.txt"
    lista.write_text("".join(f"file '{p.resolve()}'\n" for p in partes), encoding="utf-8")
    _ff("-f", "concat", "-safe", "0", "-i", str(lista), "-ar", "44100", "-ac", "1", "-b:a", "96k",
        "-metadata", f"title={titulo} - {data}", "-metadata", f"artist={titulo}", "-metadata", "genre=Podcast",
        str(destino))
    lista.unlink()


def escrever_srt(cues: list[tuple[float, float, str]], destino: Path) -> None:
    destino.write_text("".join(f"{i}\n{_ts(a)} --> {_ts(b)}\n{t}\n\n" for i, (a, b, t) in enumerate(cues, 1)),
                       encoding="utf-8")
