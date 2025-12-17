using System;
using System.Collections.Generic;
using System.Linq;
using Classes.Events;
using Classes.Objs;
using Classes.Videos;

public static class ScriptDinamico
{
    // Entrada principal
    public static List<Event> funcPrincipal(Video video)
    {
        int passada = 1;
        return passada == 2
            ? PassadaDois(video)
            : PassadaUm(video);
    }

    // Passada 1
    private static List<Event> PassadaUm(Video video)
    {
        var eventos = new List<Event>();
        eventos.AddRange(EventoTempoEmCena(video));
        eventos.AddRange(EventoSobreposicao(video));
        eventos.AddRange(EventoSinalVermelhoSaiuTopo(video));
        eventos.AddRange(EventoFaixaContencaoSaiuBaixo(video));
        eventos.Sort((a, b) => a.tInit.CompareTo(b.tInit));
        return eventos;
    }

    // Passada 2
    private static List<Event> PassadaDois(Video video)
    {
        var baseEvents = PassadaUm(video);
        var eventos = new List<Event>(baseEvents);

        var vermelhos = baseEvents.Where(e => e.name.StartsWith("Sinal vermelho saiu pelo topo", StringComparison.OrdinalIgnoreCase)).ToList();
        var faixas = baseEvents.Where(e => e.name.StartsWith("Faixa de contencao saiu por baixo", StringComparison.OrdinalIgnoreCase)).ToList();

        if (vermelhos.Count == 0 && faixas.Count == 0)
            return eventos;

        foreach (var red in vermelhos)
        {
            var faixa = faixas.FirstOrDefault(f => f.tInit >= red.tInit) ?? faixas.FirstOrDefault();
            double start = red.tInit;
            double end = faixa != null ? Math.Max(red.tEnd, faixa.tEnd) : red.tEnd;

            var evidencias = new List<string> { red.name };
            if (faixa != null) evidencias.Add(faixa.name);

            eventos.Add(new Event(start, end, $"Provavel avanc o de sinal | evidencias: {string.Join(" ; ", evidencias)}"));
        }

        return eventos;
    }

    // Tempo em cena por objeto.
    private static List<Event> EventoTempoEmCena(Video video)
    {
        var eventos = new List<Event>();
        var firstSeen = new Dictionary<(string Nome, int Id), double>();
        var lastSeen = new Dictionary<(string Nome, int Id), double>();

        foreach (var frame in video.frames)
        {
            double t = frame.time;

            foreach (var obj in frame.objects)
            {
                var key = (obj.Nome ?? string.Empty, obj.Id);
                if (!firstSeen.ContainsKey(key)) firstSeen[key] = t;
                lastSeen[key] = t;
            }
        }

        foreach (var kv in firstSeen)
        {
            var (nome, id) = kv.Key;
            double start = kv.Value;
            double end = lastSeen.GetValueOrDefault(kv.Key, start);
            eventos.Add(new Event(start, end, $"{nome} {id} tempo em cena"));
        }

        return eventos;
    }

    // Tempo de sobreposicao entre pares.
    private static List<Event> EventoSobreposicao(Video video)
    {
        var eventos = new List<Event>();
        var prevOver = new HashSet<(string, int, string, int)>();
        var overStart = new Dictionary<(string, int, string, int), double>();

        foreach (var frame in video.frames)
        {
            double t = frame.time;
            var objs = frame.objects;

            for (int i = 0; i < objs.Count; i++)
            {
                for (int j = i + 1; j < objs.Count; j++)
                {
                    var a = objs[i];
                    var b = objs[j];

                    if (BoxesOverlap(a, b))
                    {
                        var key = NormalizePair(a, b);
                        if (!prevOver.Contains(key))
                            overStart[key] = t;
                    }
                }
            }

            var current = new HashSet<(string, int, string, int)>(overStart.Keys);

            foreach (var pair in prevOver.Except(current))
            {
                eventos.Add(new Event(
                    overStart[pair],
                    t,
                    $"{pair.Item1} {pair.Item2} tempo de sobreposicao com {pair.Item3} {pair.Item4}"
                ));
                overStart.Remove(pair);
            }

            prevOver = current;
        }

        return eventos;
    }

    // Sinal vermelho saiu pelo topo
    private static List<Event> EventoSinalVermelhoSaiuTopo(Video video)
    {
        var eventos = new List<Event>();
        var firstY = new Dictionary<int, double>();
        var prevY = new Dictionary<int, double>();
        var lastInfo = new Dictionary<int, (double t, double y1, double y2)>();
        var activeIds = new HashSet<int>();
        var emitted = new HashSet<int>();

        int minDelta = Math.Max((int)(video.height * 0.05), 10);

        foreach (var frame in video.frames)
        {
            double t = frame.time;
            var frameIds = new HashSet<int>();

            foreach (var obj in frame.objects)
            {
                if (!string.Equals(obj.Nome, "red", StringComparison.OrdinalIgnoreCase)) continue;

                frameIds.Add(obj.Id);

                if (!firstY.ContainsKey(obj.Id))
                    firstY[obj.Id] = obj.Y1;

                if (lastInfo.ContainsKey(obj.Id))
                    prevY[obj.Id] = lastInfo[obj.Id].y1;

                lastInfo[obj.Id] = (t, obj.Y1, obj.Y2);

                if (obj.Y1 <= 0 && !emitted.Contains(obj.Id))
                {
                    eventos.Add(new Event(t, t, $"Sinal vermelho saiu pelo topo (ID {obj.Id})"));
                    emitted.Add(obj.Id);
                }
            }

            var disappeared = activeIds.Except(frameIds);
            foreach (var oid in disappeared)
            {
                if (emitted.Contains(oid)) continue;
                if (!lastInfo.TryGetValue(oid, out var info)) continue;

                bool movingUp = prevY.ContainsKey(oid) && info.y1 < prevY[oid];
                double deltaFirst = firstY.GetValueOrDefault(oid, info.y1) - info.y1;

                if (movingUp && deltaFirst >= minDelta)
                {
                    eventos.Add(new Event(info.t, info.t, $"Sinal vermelho saiu pelo topo (ID {oid})"));
                    emitted.Add(oid);
                }
            }

            activeIds = frameIds;
        }

        return eventos;
    }

    // Faixa de contencao saiu por baixo
    private static List<Event> EventoFaixaContencaoSaiuBaixo(Video video)
    {
        var eventos = new List<Event>();
        var firstY = new Dictionary<int, double>();
        var prevY = new Dictionary<int, double>();
        var lastInfo = new Dictionary<int, (double t, double y1, double y2)>();
        var activeIds = new HashSet<int>();
        var emitted = new HashSet<int>();

        int minDelta = Math.Max((int)(video.height * 0.05), 10);

        foreach (var frame in video.frames)
        {
            double t = frame.time;
            var frameIds = new HashSet<int>();

            foreach (var obj in frame.objects)
            {
                if (!IsFaixa(obj.Nome)) continue;

                frameIds.Add(obj.Id);

                if (!firstY.ContainsKey(obj.Id))
                    firstY[obj.Id] = obj.Y2;

                if (lastInfo.ContainsKey(obj.Id))
                    prevY[obj.Id] = lastInfo[obj.Id].y2;

                lastInfo[obj.Id] = (t, obj.Y1, obj.Y2);

                if (obj.Y2 >= video.height && !emitted.Contains(obj.Id))
                {
                    eventos.Add(new Event(t, t, $"Faixa de contencao saiu por baixo (ID {obj.Id})"));
                    emitted.Add(obj.Id);
                }
            }

            var disappeared = activeIds.Except(frameIds);
            foreach (var oid in disappeared)
            {
                if (emitted.Contains(oid)) continue;
                if (!lastInfo.TryGetValue(oid, out var info)) continue;

                bool movingDown = prevY.ContainsKey(oid) && info.y2 > prevY[oid];
                double deltaFirst = info.y2 - firstY.GetValueOrDefault(oid, info.y2);

                if (movingDown && deltaFirst >= minDelta)
                {
                    eventos.Add(new Event(info.t, info.t, $"Faixa de contencao saiu por baixo (ID {oid})"));
                    emitted.Add(oid);
                }
            }

            activeIds = frameIds;
        }

        return eventos;
    }

    private static bool BoxesOverlap(Obj a, Obj b)
    {
        return Math.Min(a.X2, b.X2) > Math.Max(a.X1, b.X1)
            && Math.Min(a.Y2, b.Y2) > Math.Max(a.Y1, b.Y1);
    }

    private static (string, int, string, int) NormalizePair(Obj a, Obj b)
    {
        return string.Compare(a.Nome, b.Nome, StringComparison.Ordinal) <= 0
            ? (a.Nome, a.Id, b.Nome, b.Id)
            : (b.Nome, b.Id, a.Nome, a.Id);
    }

    private static bool IsFaixa(string nome)
    {
        if (string.IsNullOrWhiteSpace(nome)) return false;
        nome = nome.ToLowerInvariant();
        return nome.Contains("faixa") || nome.Contains("contencao");
    }
}
