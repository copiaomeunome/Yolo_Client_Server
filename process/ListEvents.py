from classes.Events import Event
def boxes_overlap(a, b):
    """
    Checks whether two axis-aligned rectangles overlap.
    a, b: (x1, y1, x2, y2)
    """
    ax1, ay1, ax2, ay2 = a
    bx1, by1, bx2, by2 = b

    inter_x1 = max(ax1, bx1)
    inter_y1 = max(ay1, by1)
    inter_x2 = min(ax2, bx2)
    inter_y2 = min(ay2, by2)

    return inter_x2 > inter_x1 and inter_y2 > inter_y1


def horizontally_aligned(a, b, tolerance=0.2):
    """
    Checks whether two boxes are horizontally aligned, based on the Y coordinate
    of their centers.

    We say they are aligned if the absolute difference between their center Y
    positions is less than or equal to `tolerance * min(height_a, height_b)`.
    """
    ax1, ay1, ax2, ay2 = a
    bx1, by1, bx2, by2 = b

    # Heights
    h_a = ay2 - ay1
    h_b = by2 - by1
    ref_h = min(h_a, h_b)

    if ref_h <= 0:
        return False

    # Center Y coordinates
    cy_a = (ay1 + ay2) / 2.0
    cy_b = (by1 + by2) / 2.0

    return abs(cy_a - cy_b) <= tolerance * ref_h

def funcObservaSinalVermelho(video):
    eventos = []

    for frame in video.frames:
        t = frame.time
        for obj in frame.objects:
            if obj.nome != "sinal_vermelho":
                continue

            # Quando o topo do objeto sai pela borda da tela
            if obj.y1 <= 0:
                eventos.append(Event(
                    tInit=t,
                    tEnd=t,
                    name=f"Sinal vermelho saiu pelo topo (ID {obj.id})"
                ))

    return eventos
def funcDetectaEntradasESaidas(video):
    eventos = []

    first_seen = {}
    last_seen = {}

    for frame in video.frames:
        t = frame.time
        for obj in frame.objects:
            key = (obj.nome, obj.id)
            if key not in first_seen:
                first_seen[key] = t
            last_seen[key] = t

    for (nome, oid), start in first_seen.items():
        end = last_seen.get((nome, oid), start)
        eventos.append(Event(start, end, f"{nome} {oid} tempo em cena"))

    return eventos
def funcDetectaAlinhamentos(video):
    eventos = []

    prev_align = set()
    align_start = {}

    for frame in video.frames:
        t = frame.time

        objs = frame.objects
        keys = [(obj.nome, obj.id) for obj in objs]
        boxes = { (obj.nome, obj.id): (obj.x1, obj.y1, obj.x2, obj.y2) for obj in objs }

        align = set()

        for i in range(len(keys)):
            for j in range(i + 1, len(keys)):
                k1 = keys[i]
                k2 = keys[j]

                if horizontally_aligned(boxes[k1], boxes[k2]):
                    align.add(frozenset((k1, k2)))

        for pair in align - prev_align:
            align_start[pair] = t

        for pair in prev_align - align:
            start_time = align_start.pop(pair, t)
            items = list(pair)
            if len(items) != 2:
                continue
            (cat1, id1), (cat2, id2) = sorted(items)
            eventos.append(Event(start_time, t, f"{cat1} {id1} tempo de alinhamento com {cat2} {id2}"))

        prev_align = align

    # Fecha alinhamentos em andamento ate o ultimo frame
    if video.frames:
        final_time = video.frames[-1].time
        for pair in prev_align:
            start_time = align_start.pop(pair, final_time)
            items = list(pair)
            if len(items) != 2:
                continue
            (cat1, id1), (cat2, id2) = sorted(items)
            eventos.append(Event(start_time, final_time, f"{cat1} {id1} tempo de alinhamento com {cat2} {id2}"))

    return eventos


def funcDetectaOverlap(video):
    eventos = []

    prev_over = set()
    overlap_start = {}

    for frame in video.frames:
        t = frame.time

        objs = frame.objects
        keys = [(obj.nome, obj.id) for obj in objs]
        boxes = { (obj.nome, obj.id): (obj.x1, obj.y1, obj.x2, obj.y2) for obj in objs }

        over = set()

        for i in range(len(keys)):
            for j in range(i + 1, len(keys)):
                k1 = keys[i]
                k2 = keys[j]

                if boxes_overlap(boxes[k1], boxes[k2]):
                    over.add(frozenset((k1, k2)))

        for pair in over - prev_over:
            overlap_start[pair] = t

        for pair in prev_over - over:
            start_time = overlap_start.pop(pair, t)
            items = list(pair)
            if len(items) != 2:
                continue
            (cat1, id1), (cat2, id2) = sorted(items)
            eventos.append(Event(start_time, t, f"{cat1} {id1} tempo de sobreposicao com {cat2} {id2}"))

        prev_over = over

    # Fecha sobreposicoes em andamento ate o ultimo frame
    if video.frames:
        final_time = video.frames[-1].time
        for pair in prev_over:
            start_time = overlap_start.pop(pair, final_time)
            items = list(pair)
            if len(items) != 2:
                continue
            (cat1, id1), (cat2, id2) = sorted(items)
            eventos.append(Event(start_time, final_time, f"{cat1} {id1} tempo de sobreposicao com {cat2} {id2}"))

    return eventos


def ListEvents(video):
    all_events = []

    # Cada função retorna uma lista de Event()
    all_events += funcObservaSinalVermelho(video)
    all_events += funcDetectaEntradasESaidas(video)
    all_events += funcDetectaAlinhamentos(video)
    all_events += funcDetectaOverlap(video)

    # Você pode adicionar mais funções aqui

    # Ordena todos os eventos pelo tempo inicial
    all_events.sort(key=lambda e: e.tInit)

    return all_events
