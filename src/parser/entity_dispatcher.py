import re

from src.api.schemas import (
    BoundingBox,
    DimensionAnnotation,
    DrawingMetadata,
    DrawingSummary,
    GeometricEntity,
    TextAnnotation,
    UnsupportedEntityRecord,
)
from src.core.logging import get_logger
from src.models.internal import EntityHeader


from src.parser.entities.annotations import ANNOTATION_PARSERS
from src.parser.entities.dimensions import DIMENSION_PARSERS
from src.parser.entities.geometry import GEOMETRY_PARSERS

logger = get_logger(__name__)


def _extract_numeric(text: str) -> float | None:
    """Извлекает первое числовое значение из текста аннотации (например '12.5', 'R12', 'Ø 25.0')."""
    m = re.search(r"\d+(?:[.,]\d+)?", text)
    if m:
        try:
            return float(m.group(0).replace(",", "."))
        except ValueError:
            return None
    return None


class EntityDispatcher:
    """Маршрутизирует сущности P-секции по типу и собирает результат.

    Алгоритм работы:
    1. Собираем параметры каждой сущности из строк P-секции
       (строки одной сущности связаны указателем из Directory Entry)
    2. По entity_type из Directory Entry выбираем нужный парсер
    3. Если тип не поддерживается — пишем в unsupported (не ошибка)
    4. После диспетчеризации вычисляем сводку (bounding box, счётчики)

    Бизнес-цель: преобразовать все сырые IGES-данные в типизированные
    Python-объекты, готовые к сериализации в JSON для LLM.
    """

    def dispatch(
        self,
        p_lines: list[str],
        directory: dict[int, EntityHeader],
    ) -> tuple[
        list[GeometricEntity],
        list[DimensionAnnotation],
        list[TextAnnotation],
        list[UnsupportedEntityRecord],
    ]:
        """Разбирает P-секцию и распределяет сущности по категориям.

        P-секция организована так: каждая строка начинается с указателя
        на свою DE-запись (первые 7 символов — sequence_number, 8-й — пробел).
        Параметры одной сущности могут занимать несколько строк,
        последняя заканчивается точкой с запятой.
        """
        geometry: list[GeometricEntity] = []
        dimensions: list[DimensionAnnotation] = []
        annotations: list[TextAnnotation] = []
        unsupported_counts: dict[int, int] = {}

        # Для пост-обработки: индекс в списке + DE sequence_number связанного General Note
        dim_note_refs: list[tuple[int, int]] = []    # (index_in_dimensions, note_seq)
        label_note_refs: list[tuple[int, int]] = []  # (index_in_annotations, note_seq)

        # Группируем строки P-секции по sequence_number DE
        entity_params = self._collect_entity_params(p_lines)

        for seq_num, raw_params_str in entity_params.items():
            header = directory.get(seq_num)
            if header is None:
                continue

            entity_type = header.entity_type
            # Разбиваем параметры по запятой; первый — entity_type
            params = [p.rstrip(";").strip() for p in raw_params_str.split(",")]

            # T032: каждая сущность обрабатывается изолированно.
            # Повреждённые параметры одной сущности не ронят парсинг всего чертежа —
            # сущность пропускается с предупреждением, остальные продолжают обрабатываться.
            try:
                if entity_type in GEOMETRY_PARSERS:
                    name, parser_fn = GEOMETRY_PARSERS[entity_type]
                    coords = parser_fn(params)
                    geometry.append(GeometricEntity(
                        entity_type=entity_type,
                        entity_name=name,
                        sequence_number=seq_num,
                        layer=header.layer,
                        color=header.color,
                        line_weight=header.line_weight,
                        coordinates=coords,
                        raw_parameters=params,
                    ))

                elif entity_type in DIMENSION_PARSERS:
                    dim_type, parser_fn = DIMENSION_PARSERS[entity_type]
                    dim_data = parser_fn(params)
                    note_seq = dim_data.get("note_seq", 0)
                    if note_seq:
                        dim_note_refs.append((len(dimensions), note_seq))
                    dimensions.append(DimensionAnnotation(
                        entity_type=entity_type,
                        dimension_type=dim_type,
                        sequence_number=seq_num,
                        arrow_coordinates=dim_data.get("arrow_coordinates"),
                        raw_parameters=params,
                    ))

                elif entity_type in ANNOTATION_PARSERS:
                    name, parser_fn = ANNOTATION_PARSERS[entity_type]
                    ann_data = parser_fn(params)
                    # Type 210 (General Label) содержит ссылку на General Note — запоминаем
                    note_seq = ann_data.get("note_seq", 0)
                    if note_seq and entity_type == 210:
                        label_note_refs.append((len(annotations), note_seq))
                    annotations.append(TextAnnotation(
                        entity_type=entity_type,
                        entity_name=name,
                        sequence_number=seq_num,
                        content=ann_data.get("content", ""),
                        position_x=ann_data.get("position_x"),
                        position_y=ann_data.get("position_y"),
                        char_height=ann_data.get("char_height"),
                        raw_parameters=params,
                    ))

                else:
                    # Неизвестный тип — считаем, не ломаем парсинг
                    unsupported_counts[entity_type] = unsupported_counts.get(entity_type, 0) + 1

            except Exception as exc:
                # Повреждённая сущность пропускается — бизнес-решение: лучше вернуть
                # частичный результат, чем отказать в обработке всего чертежа.
                logger.warning(
                    "entity_parse_skipped",
                    entity_type=entity_type,
                    seq_num=seq_num,
                    reason=str(exc),
                )
                unsupported_counts[entity_type] = unsupported_counts.get(entity_type, 0) + 1
                continue

        # Разрешаем ссылки: заполняем text_display/value размеров и content меток
        # из уже распарсенных General Note (Type 212, entity_name="general_note")
        notes_by_seq = {
            ann.sequence_number: ann.content
            for ann in annotations
            if ann.entity_name == "general_note" and ann.content
        }
        for dim_idx, note_seq in dim_note_refs:
            text = notes_by_seq.get(note_seq, "")
            if text:
                dimensions[dim_idx] = dimensions[dim_idx].model_copy(
                    update={"text_display": text, "value": _extract_numeric(text)}
                )
        for ann_idx, note_seq in label_note_refs:
            text = notes_by_seq.get(note_seq, "")
            if text:
                annotations[ann_idx] = annotations[ann_idx].model_copy(update={"content": text})

        unsupported = [
            UnsupportedEntityRecord(entity_type=et, count=cnt)
            for et, cnt in sorted(unsupported_counts.items())
        ]

        return geometry, dimensions, annotations, unsupported

    def _collect_entity_params(self, p_lines: list[str]) -> dict[int, str]:
        """Группирует строки P-секции по DE sequence_number.

        Стандартный формат P-строки (IGES 5.3):
          Колонки  1-64  (0-based 0-63):  данные параметров
          Колонки 65-72  (0-based 64-71): указатель DE (right-justified int)
          Колонка  73    (0-based 72):    код секции 'P'
          Колонки 74-80  (0-based 73-79): номер строки P-секции

        Некоторые CAD-экспортёры создают строки длиной 79 символов — в этом
        случае код секции находится на позиции 71 (0-based), поэтому ищем 'P'
        сначала на 72, затем на 71.
        """
        entity_params: dict[int, str] = {}
        current_seq: int | None = None
        current_data: list[str] = []

        for line in p_lines:
            # Определяем позицию кода секции 'P' (72 для стандартных строк, 71 для 79-символьных)
            p_code_pos: int | None = None
            for check_pos in (72, 71):
                if len(line) > check_pos and line[check_pos] == "P":
                    p_code_pos = check_pos
                    break
            if p_code_pos is None:
                continue

            # В IGES 5.3 DE-указатель хранится в колонках 65-72 (8 символов перед 'P'),
            # но некоторые экспортёры (и наши минимальные фикстуры) пишут DE-указатель
            # в начале строки (первые 8 символов), а хвост 65-72 оставляют пустым.
            seq_num: int | None = None
            data_part: str = ""

            # Вариант A: стандартный хвостовой DE pointer (перед 'P')
            tail_seq_str = line[p_code_pos - 8 : p_code_pos].strip()
            if tail_seq_str:
                try:
                    seq_num = int(tail_seq_str)
                    data_part = line[0 : p_code_pos - 8].rstrip()
                except ValueError:
                    seq_num = None

            # Вариант B: DE pointer в начале строки (как в tests/fixtures/*.igs)
            if seq_num is None:
                head_seq_str = line[0:8].strip()
                try:
                    seq_num = int(head_seq_str)
                except ValueError:
                    continue
                # Полезные данные: между head pointer и хвостом секции
                data_part = line[8:p_code_pos].rstrip()

            if seq_num != current_seq:
                # Сохраняем предыдущую сущность
                if current_seq is not None and current_data:
                    entity_params[current_seq] = "".join(current_data)
                current_seq = seq_num
                current_data = [data_part]
            else:
                current_data.append(data_part)

        # Сохраняем последнюю сущность
        if current_seq is not None and current_data:
            entity_params[current_seq] = "".join(current_data)

        return entity_params

    def compute_summary(
        self,
        geometry: list[GeometricEntity],
        dimensions: list[DimensionAnnotation],
        annotations: list[TextAnnotation],
        metadata: DrawingMetadata,
    ) -> DrawingSummary:
        """Вычисляет сводку по всему чертежу.

        Bounding box рассчитывается по координатам геометрических сущностей.
        Если геометрии нет — bounding_box = None (пустой чертёж).
        entity_counts даёт LLM быстрый обзор состава чертежа без обхода списков.

        Бизнес-цель: LLM должна с первого взгляда понять габариты детали
        и состав чертежа, не обходя весь массив geometry.
        """
        entity_counts: dict[str, int] = {}

        # Считаем каждый тип
        for g in geometry:
            entity_counts[g.entity_name] = entity_counts.get(g.entity_name, 0) + 1
        for d in dimensions:
            key = f"{d.dimension_type}_dimension"
            entity_counts[key] = entity_counts.get(key, 0) + 1
        for a in annotations:
            entity_counts[a.entity_name] = entity_counts.get(a.entity_name, 0) + 1

        total = len(geometry) + len(dimensions) + len(annotations)

        # Bounding box: собираем все числовые координаты из geometry
        bbox = self._compute_bounding_box(geometry)

        return DrawingSummary(
            bounding_box=bbox,
            entity_counts=entity_counts,
            total_entities=total,
            units=metadata.unit,
        )

    def _compute_bounding_box(self, geometry: list[GeometricEntity]) -> BoundingBox | None:
        """Вычисляет минимальный описывающий прямоугольник по всей геометрии.

        Обходит поле coordinates каждой сущности в поисках x/y-значений.
        Рекурсивный обход словаря покрывает все вложенные структуры координат.
        Возвращает None если нет ни одной числовой координаты.
        """
        xs: list[float] = []
        ys: list[float] = []

        def collect(obj):
            if isinstance(obj, dict):
                if "x" in obj:
                    try:
                        xs.append(float(obj["x"]))
                    except (TypeError, ValueError):
                        pass
                if "y" in obj:
                    try:
                        ys.append(float(obj["y"]))
                    except (TypeError, ValueError):
                        pass
                for v in obj.values():
                    collect(v)
            elif isinstance(obj, list):
                for item in obj:
                    collect(item)

        for entity in geometry:
            collect(entity.coordinates)

        if not xs or not ys:
            return None

        return BoundingBox(min_x=min(xs), min_y=min(ys), max_x=max(xs), max_y=max(ys))
