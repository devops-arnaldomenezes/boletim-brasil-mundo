"""Síntese de voz (edge-tts, vozes neurais pt-BR gratuitas) e montagem do podcast com ffmpeg."""
from __future__ import annotations

import asyncio
import re
import subprocess
import time
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


async def _edge(texto: str, voz: str, mp3: Path, rate: str) -> list[tuple[float, float, str]]:
    import edge_tts
    com = edge_tts.Communicate(texto, voz, rate=rate, boundary="SentenceBoundary")
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


def _cues_estimados_blocos(texto: str, total: float) -> list[tuple[float, float, str]]:
    bs = blocos(texto)
    pesos = [max(len(b.split()), 1) for b in bs]
    soma, t, out = sum(pesos), 0.0, []
    for b, p in zip(bs, pesos):
        out.append((t, t + total * p / soma, b))
        t += total * p / soma
    return out


def blocos(texto: str, max_palavras: int = 90) -> list[str]:
    """Divide o roteiro em blocos de respiração: um por parágrafo; parágrafos longos são agrupados por frases.
    Entre os blocos entra uma pausa curta, como um locutor que respira entre uma notícia e outra."""
    out = []
    for par in re.split(r"\n\s*\n|\n", texto.strip()):
        frases, atual = re.split(r"(?<=[.!?])\s+", par.strip()), []
        for f in frases:
            if not f:
                continue
            atual.append(f)
            if sum(len(x.split()) for x in atual) >= max_palavras:
                out.append(" ".join(atual))
                atual = []
        if atual:
            out.append(" ".join(atual))
    return out or [texto.strip()]


# Tratamento de locução: corta graves de ruído, comprime de leve e normaliza a -16 LUFS (padrão de podcast).
MASTER = ("highpass=f=70,acompressor=threshold=-20dB:ratio=2.5:attack=10:release=250:makeup=2,"
          "loudnorm=I=-16:TP=-1.5:LRA=9")


def _tts_bloco(texto: str, vozes: list[str], mp3: Path, rate: str) -> list[tuple[float, float, str]]:
    erro = None
    for voz in list(vozes):  # se a voz principal falhar, passa à reserva (e não insiste nela nos próximos blocos)
        for tentativa in range(3):
            try:
                cues = asyncio.run(_edge(texto, voz, mp3, rate))
                if mp3.stat().st_size < 1000:
                    raise RuntimeError("áudio vazio")
                return cues
            except Exception as e:  # noqa: BLE001
                erro = e
                log.warning("TTS falhou (%s, tentativa %d): %s", voz, tentativa + 1, str(e)[:150])
                time.sleep(2 * (tentativa + 1))
        if len(vozes) > 1:
            vozes.remove(voz)
    raise RuntimeError(f"TTS indisponível: {erro}")


def sintetizar(texto: str, voz: str, mp3: Path, ppm: int = 150, rate: str = "+0%", pausa: float = 0.5,
               voz_reserva: str | None = None, marcas: list | None = None) -> list[tuple[float, float, str]]:
    """Gera MP3 do texto (bloco a bloco, com pausas naturais e tratamento de voz).
    Retorna legendas (inicio, fim, texto) em segundos. Se `marcas` for uma lista, recebe (inicio, fim, texto) de
    cada bloco falado, medidos no áudio real: é o que sincroniza as manchetes do vídeo com a locução."""
    vozes = [voz] + ([voz_reserva] if voz_reserva and voz_reserva != voz else [])
    partes, cues, t = [], [], 0.0
    try:
        silencio = mp3.with_name(f"{mp3.stem}_pausa.mp3")
        _ff("-f", "lavfi", "-i", "anullsrc=r=24000:cl=mono", "-t", f"{pausa:.2f}", "-c:a", "libmp3lame",
            "-b:a", "48k", str(silencio))
        for i, b in enumerate(blocos(texto)):
            p = mp3.with_name(f"{mp3.stem}_{i:03d}.mp3")
            cb = _tts_bloco(b, vozes, p, rate)
            if partes:
                partes.append(silencio)
                t += pausa
            d = duracao(p)
            if marcas is not None:
                marcas.append((t, t + d, b))
            for ini, fim, frase in cb:  # legendas de frase muito longas são re-fatiadas proporcionalmente
                cues += [(t + ini + a, t + ini + z, s) for a, z, s in _cues_estimados(frase, fim - ini)]
            partes.append(p)
            t += d
        lista = mp3.with_name(f"{mp3.stem}_lista.txt")
        lista.write_text("".join(f"file '{x.resolve()}'\n" for x in partes), encoding="utf-8")
        _ff("-f", "concat", "-safe", "0", "-i", str(lista), "-af", MASTER, "-ar", "24000", "-ac", "1",
            "-c:a", "libmp3lame", "-b:a", "64k", str(mp3))
        for x in {*partes, silencio, lista}:
            x.unlink(missing_ok=True)
        if marcas and t > 0:  # corrige a deriva do encadeamento de MP3 pela duração final real
            k = duracao(mp3) / t
            marcas[:] = [(a * k, z * k, b) for a, z, b in marcas]
        return cues or _cues_estimados(texto, duracao(mp3))
    except Exception as e:  # noqa: BLE001
        log.warning("TTS indisponível (%s). Gerando áudio silencioso de contingência.", e)
        segundos = max(len(texto.split()) / ppm * 60, 3)
        if marcas is not None:  # sem áudio real, estima os blocos pelo número de palavras
            marcas.clear()
            marcas += _cues_estimados_blocos(texto, segundos)
        _ff("-f", "lavfi", "-i", "anullsrc=r=24000:cl=mono", "-t", f"{segundos:.2f}", "-q:a", "6", str(mp3))
        return _cues_estimados(texto, segundos)


def vinheta(destino: Path, segundos: float = 3.0) -> None:
    """Vinheta sonora gerada (sem direitos autorais) para transição entre seções: acorde suave com entrada
    gradual e cauda de eco, em vez de bipes."""
    notas = (261.63, 329.63, 392.0, 523.25)  # dó maior
    entradas = [x for f in notas for x in ("-f", "lavfi", "-i", f"sine=f={f}:d={segundos}")]
    _ff(*entradas, "-filter_complex",
        f"{''.join(f'[{i}]' for i in range(len(notas)))}amix={len(notas)},"
        f"afade=t=in:d=0.35,afade=t=out:st={segundos - 1.6}:d=1.6,aecho=0.8:0.5:90|180:0.25|0.15,"
        "volume=0.5,aresample=24000,pan=mono|c0=c0", "-t", f"{segundos}", "-c:a", "libmp3lame", "-b:a", "64k",
        str(destino))


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
