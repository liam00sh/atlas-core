"""Formato y fragmentacion conservadora de respuestas Telegram."""

from __future__ import annotations

import re


TELEGRAM_SAFE_CHUNK = 3900
_MARKDOWN_V2_SPECIAL = re.compile(r"([_\*\[\]()~`>#+\-=|{}.!\\])")


def escape_markdown_v2(text: str) -> str:
    return _MARKDOWN_V2_SPECIAL.sub(r"\\\1", text)


def split_message(text: str, *, limit: int = TELEGRAM_SAFE_CHUNK) -> list[str]:
    clean = str(text).strip()
    if not clean:
        return ["Atlas no ha generado una respuesta."]
    if limit < 64:
        raise ValueError("El limite de fragmentacion es demasiado pequeno.")
    chunks: list[str] = []
    remaining = clean
    while len(remaining) > limit:
        split_at = max(
            remaining.rfind("\n\n", 0, limit),
            remaining.rfind("\n", 0, limit),
            remaining.rfind(" ", 0, limit),
        )
        if split_at < limit // 3:
            split_at = limit
        chunks.append(remaining[:split_at].rstrip())
        remaining = remaining[split_at:].lstrip()
    if remaining:
        chunks.append(remaining)
    # Si un corte cae dentro de un bloque de codigo, se cierra el bloque en
    # ese mensaje y se reabre en el siguiente. Telegram no recibe Markdown
    # sintacticamente incompleto y el contenido sigue siendo legible.
    fenced: list[str] = []
    inside_fence = False
    fence_language = ""
    for chunk in chunks:
        prefix = f"```{fence_language}\n" if inside_fence else ""
        if chunk.count("```") % 2:
            if not inside_fence:
                opening = chunk.split("```", 1)[1].splitlines()[0].strip()
                fence_language = opening[:32] if opening and " " not in opening else ""
            inside_fence = not inside_fence
        suffix = "\n```" if inside_fence else ""
        fenced.append(prefix + chunk + suffix)
    chunks = fenced
    if len(chunks) == 1:
        return chunks
    total = len(chunks)
    return [f"[{index}/{total}]\n{chunk}" for index, chunk in enumerate(chunks, 1)]
