import math
import re
from dataclasses import dataclass

from src.api.schemas import DimensionAnnotation, DrawingMetadata, TextAnnotation


@dataclass
class Evidence:
    source_entity_ids: list[int]
    source_texts: list[str]
    source_region: str | None = None
    parser_stage: str | None = None


def _norm_space(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").strip())


def _parse_float_any(s: str) -> float | None:
    m = re.search(r"\d+(?:[.,]\d+)?", s)
    if not m:
        return None
    try:
        return float(m.group(0).replace(",", "."))
    except ValueError:
        return None


def _classify_text(text: str) -> str | None:
    t = text.lower()
    if "гост" in t and ("сталь" in t or "бронз" in t or "латун" in t):
        return "material"
    if re.search(r"\b\d+\.\.\.\d+\s*hrc\b", t) or re.search(r"\bhrc\b", t):
        return "hardness"
    if re.search(r"\bra\s*\d", t) or re.search(r"\brz\s*\d", t):
        return "roughness"
    if re.search(r"\bit\d+\b", t) or re.search(r"\bh\d+\b", t) or re.search(r"\bh\d+\s*h\d+\b", t):
        return "general_tolerance"
    return None


def _region_hint(x: float | None, y: float | None) -> str | None:
    # Очень простая эвристика: нижняя часть листа — штамп/техтребования.
    # Координатная система в IGES зависит от экспорта, поэтому без sheet bbox
    # это лишь подсказка для evidence_trace.
    if x is None or y is None:
        return None
    if y < 60:
        return "title_block"
    if y < 140:
        return "technical_requirements"
    return None


def build_normalized_layer(
    metadata: DrawingMetadata,
    dimensions: list[DimensionAnnotation],
    annotations: list[TextAnnotation],
) -> dict:
    # 1) Собираем general_note как основной источник текста
    notes = [a for a in annotations if a.entity_name == "general_note" and a.content]
    leaders = [a for a in annotations if a.entity_name == "leader_arrow"]

    # 2) Дедуп: одинаковый текст + близкие координаты (если есть)
    dedup_groups: list[dict] = []
    seen: dict[tuple[str, int, int], int] = {}
    canonical_for: dict[int, int] = {}
    for n in notes:
        key = (_norm_space(n.content), int((n.position_x or 0) / 2), int((n.position_y or 0) / 2))
        if key in seen:
            canonical = seen[key]
            canonical_for[n.sequence_number] = canonical
        else:
            seen[key] = n.sequence_number
            canonical_for[n.sequence_number] = n.sequence_number
    # инвертируем canonical→duplicates
    dup_map: dict[int, list[int]] = {}
    for seq, canon in canonical_for.items():
        if seq == canon:
            continue
        dup_map.setdefault(canon, []).append(seq)
    for canon, dups in dup_map.items():
        dedup_groups.append({"canonical_id": canon, "duplicate_ids": dups})

    # 3) Нормализованные аннотации и техтребования
    annotations_normalized: list[dict] = []
    technical_requirements: list[dict] = []
    surface_finish: list[dict] = []
    general_tolerances: dict = {"linear_class": None, "shaft_class": None, "angular": None, "other_text": None, "source_annotation_ids": []}

    title_block: dict = {
        "designation": None,
        "part_name": None,
        "material": None,
        "standard": None,
        "mass": None,
        "scale": None,
        "sheet_format": None,
        "sheet_number": None,
        "sheets_total": None,
        "organization": metadata.organization,
        "author_block_detected": False,
        "source_annotation_ids": [],
    }

    # Штамп: грубо берём самые "нижние" тексты и ищем сигнальные строки
    for n in sorted(notes, key=lambda a: (a.position_y or 0)):
        text = _norm_space(n.content)
        if not text:
            continue

        region = _region_hint(n.position_x, n.position_y)
        role = _classify_text(text)

        if region == "title_block":
            title_block["source_annotation_ids"].append(n.sequence_number)
            title_block["author_block_detected"] = True

            # Наименование детали — как правило одно слово/фраза без ГОСТ/цифр
            if title_block["part_name"] is None and ("гост" not in text.lower()) and not re.search(r"\bhrc\b", text.lower()):
                if re.search(r"[А-Яа-яA-Za-z]", text):
                    title_block["part_name"] = text

            if role == "material" and title_block["material"] is None:
                title_block["material"] = text
                m = re.search(r"(ГОСТ\s*\d+(?:[-–]\d+)*)", text, re.IGNORECASE)
                if m:
                    title_block["standard"] = m.group(1)

            # Обозначение часто похоже на номер (например 534) или 07-54-...
            if title_block["designation"] is None:
                if re.fullmatch(r"\d{2,6}", text) or re.search(r"\d{2}-\d{2}-\d{3}", text):
                    title_block["designation"] = text

        if region == "technical_requirements":
            if role in ("material", "hardness", "roughness", "general_tolerance"):
                technical_requirements.append({
                    "type": role,
                    "text": text,
                    "evidence_trace": {
                        "source_entity_ids": [n.sequence_number],
                        "source_texts": [text],
                        "source_region": region,
                        "parser_stage": "text_classification",
                    },
                    "confidence": 0.9,
                })

        if role:
            annotations_normalized.append({
                "type": role,
                "text": text,
                "source_annotation_id": n.sequence_number,
                "evidence_trace": {
                    "source_entity_ids": [n.sequence_number],
                    "source_texts": [text],
                    "source_region": region,
                    "parser_stage": "text_classification",
                },
                "confidence": 0.85 if region else 0.75,
            })

        if role == "roughness":
            # Нормализуем Ra/Rz
            m = re.search(r"\b(ra|rz)\s*([0-9]+(?:[.,][0-9]+)?)", text, re.IGNORECASE)
            if m:
                val = _parse_float_any(m.group(2))
                surface_finish.append({
                    "finish_id": f"sf_{n.sequence_number}",
                    "text": text,
                    "parameter": m.group(1).upper(),
                    "value": val,
                    "unit": "um",
                    "applies_to": [],
                    "scope": "general" if region == "technical_requirements" else "local",
                    "source_annotation_id": n.sequence_number,
                    "evidence_trace": {
                        "source_entity_ids": [n.sequence_number],
                        "source_texts": [text],
                        "source_region": region,
                        "parser_stage": "roughness_parse",
                    },
                    "confidence": 0.9,
                })

        if role == "general_tolerance":
            general_tolerances["source_annotation_ids"].append(n.sequence_number)
            # Пытаемся извлечь Hxx и hxx и ITxx
            m1 = re.search(r"\bH(\d+)\b", text)
            m2 = re.search(r"\bh(\d+)\b", text)
            if m1:
                general_tolerances["linear_class"] = f"H{m1.group(1)}"
            if m2:
                general_tolerances["shaft_class"] = f"h{m2.group(1)}"
            if general_tolerances["other_text"] is None:
                general_tolerances["other_text"] = text

    # 4) Нормализованные размеры: вытаскиваем display_text_exact, unit, tolerance_text
    unit = metadata.unit
    dimension_objects: list[dict] = []
    for d in dimensions:
        display = _norm_space(d.text_display or "")
        kind = d.dimension_type
        tol = None
        # Допуск часто идёт суффиксом: Ø70e8, 100±0,2, M8-7H
        m_tol = re.search(r"(±\s*\d+(?:[.,]\d+)?)|([A-Za-z]\d{1,2})$|(-\s*\d+[A-Za-z]\w*)$", display)
        if m_tol:
            tol = m_tol.group(0)
        dimension_objects.append({
            "dimension_id": f"dim_{d.sequence_number}",
            "kind": kind,
            "display_text": display or None,
            "normalized_text": _norm_space(display.replace("Ø", "Ø ").replace("R", "R ")),
            "numeric_value": d.value,
            "symbol_prefix": "Ø" if "Ø" in display else ("R" if display.strip().startswith("R") else None),
            "symbol_suffix": None,
            "tolerance_text": tol,
            "lower_dev": None,
            "upper_dev": None,
            "unit": unit,
            "view_id": None,
            "feature_ref": None,
            "leader_ref": None,
            "source_entity_id": d.sequence_number,
            "evidence_trace": {
                "source_entity_ids": [d.sequence_number],
                "source_texts": [display] if display else [],
                "source_region": None,
                "parser_stage": "dimension_normalize",
            },
            "confidence": 0.8 if display else 0.6,
        })

    # 5) Диагностика связей
    extraction_diagnostics = {
        "unsupported_entities": [],
        "unparsed_texts": [],
        "unlinked_dimensions": [f"dim_{d.sequence_number}" for d in dimensions if not (d.text_display or "").strip()],
        "unlinked_annotations": [],
        "ambiguous_links": [],
        "table_parse_errors": [],
        "view_segmentation_warnings": [],
    }

    # 6) Простые links: dimension -> note (через text_display совпадение) и leader -> ближайшая аннотация
    # Замечание: это эвристика. Настоящие DE-ссылки между 214/212 зависят от CAD-экспорта.
    dim_links: list[dict] = []
    for d in dimensions:
        if not (d.text_display or "").strip():
            continue
        dim_links.append({
            "from_id": f"dim_{d.sequence_number}",
            "to_id": None,
            "link_type": "dimension_text_resolved",
            "evidence_ids": [d.sequence_number],
            "confidence": 0.7,
        })

    leader_links: list[dict] = []
    for l in leaders:
        if l.position_x is None or l.position_y is None:
            continue
        # ближайшая general_note по расстоянию
        best = None
        best_d2 = None
        for n in notes:
            if n.position_x is None or n.position_y is None:
                continue
            dx = (n.position_x - l.position_x)
            dy = (n.position_y - l.position_y)
            d2 = dx * dx + dy * dy
            if best_d2 is None or d2 < best_d2:
                best_d2 = d2
                best = n
        if best is not None and best_d2 is not None:
            leader_links.append({
                "from_id": f"leader_{l.sequence_number}",
                "to_id": f"ann_{best.sequence_number}",
                "link_type": "leader_to_nearest_text",
                "evidence_ids": [l.sequence_number, best.sequence_number],
                "confidence": 0.6 if best_d2 > 100 else 0.75,
            })

    # 7) Таблицы: базовая заглушка + предупреждение, если много коротких подписей в одном регионе.
    # Восстановление таблиц требует кластеризации по Y/X и обычно сетки линий.
    tables: list[dict] = []
    # Если обнаружили "h*" или похожие заголовки — помечаем как потенциальную таблицу.
    if any(re.search(r"\bh\*\b", _norm_space(n.content)) for n in notes):
        extraction_diagnostics["view_segmentation_warnings"].append("table_candidates_detected")

    return {
        "title_block": title_block if title_block.get("author_block_detected") else None,
        "sheet_regions": None,
        "views": [],
        "features": [],
        "dimension_objects": dimension_objects,
        "annotations_normalized": annotations_normalized,
        "tables": tables,
        "surface_finish": surface_finish,
        "general_tolerances": general_tolerances if general_tolerances["source_annotation_ids"] else None,
        "technical_requirements": technical_requirements,
        "datums": [],
        "gdt": [],
        "hole_patterns": [],
        "links": {
            "dimension_to_feature": [],
            "annotation_to_feature": [],
            "leader_to_feature": [],
            "dimension_to_text": dim_links,
            "leader_to_annotation": leader_links,
        },
        "resolved_parameters": None,
        "extraction_diagnostics": extraction_diagnostics,
        "dedup_groups": dedup_groups,
    }

