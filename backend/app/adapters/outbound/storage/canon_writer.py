"""Renderiza canon.md a partir del Canon estructurado, siguiendo el mismo
esqueleto que assets/canon_template.md del skill historias-fantasia -- para
que un canon.md generado por la web se vea identico a uno escrito a mano por
la skill, y las secciones 4/5 (linea de tiempo, tracker de personajes, que
todavia no genera la IA) queden con su tabla vacia lista para completarse
capitulo a capitulo mas adelante."""
from __future__ import annotations

from app.domain.story.entities import Canon, Project


def render_canon_markdown(project: Project, canon: Canon) -> str:
    temporada_rows = "\n".join(
        f"| {ep.numero} | {ep.resumen} | {ep.cliffhanger} |" for ep in canon.temporada
    ) or "| | | |"

    return f"""# CANON — {project.name}

> Biblia de continuidad de UNA SOLA temporada ({len(canon.temporada) or project.num_episodios or "N"} episodios). No es canon compartido entre historias.
> Una vez cerrada la temporada, este archivo se congela y solo se reabre si se produce una secuela/precuela/cameo.

---

## 1. Logline y premisa

**Logline (1-2 líneas):**
{canon.logline}

**Premisa:**
{canon.premisa}

---

## 2. Reglas del sistema

> La sección más importante. Define los límites explícitos del poder/magia/sistema.

{canon.reglas_sistema}

---

## 3. Glosario de términos inventados

{canon.glosario or "_(sin términos todavía)_"}

---

## 4. Línea de tiempo

> Cuánto tiempo del mundo transcurre por capítulo. Se completa capítulo a capítulo.

| Capítulo | Tiempo transcurrido (mundo) | Fecha/marca narrativa |
|---|---|---|

---

## 5. Estado de personajes (tracker)

> Tracker corto, NO ficha completa (eso vive en personajes.json). Se actualiza capítulo a capítulo.

| Personaje | Estado (vivo/muerto/etc.) | Ubicación actual | Nivel/poder actual | Última aparición |
|---|---|---|---|---|

---

## 6. Esqueleto del arco de temporada

> Una línea por capítulo, decidida antes de escribir prosa.

| Cap. | Resumen en una línea | Cliffhanger |
|---|---|---|
{temporada_rows}

---

## 7. Tono / rating

**Modo:** {project.tono.value}

---

## Notas para secuela/precuela/cameo

> Completar solo si esta historia da pie a otra.
"""
