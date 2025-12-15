using System;
using System.Collections.Generic;
using System.Linq;
using Classes.Events;

namespace Detection
{
    public static class VideoEventDetectors
    {
        // ========= PUBLIC API =========

        public static List<Event> ListEvents(Video video)
        {
            var allEvents = new List<Event>();

            allEvents.AddRange(ObservaSinalVermelho(video));
            allEvents.AddRange(DetectaEntradasESaidas(video));
            allEvents.AddRange(DetectaAlinhamentos(video));
            allEvents.AddRange(DetectaOverlap(video));

            allEvents.Sort((a, b) => a.tInit.CompareTo(b.tInit));
            return allEvents;
        }

        // ========= DETECTORES =========

        private static List<Event> ObservaSinalVermelho(Video video)
        {
            var eventos = new List<Event>();

            var firstY = new Dictionary<int, double>();
            var prevY = new Dictionary<int, double>();
            var lastInfo = new Dictionary<int, (double t, double y1, double y2)>();
            var activeIds = new HashSet<int>();
            var emitted = new HashSet<int>();

            int minDelta = Math.Max((int)(video.Height * 0.05), 10);

            foreach (var frame in video.Frames)
            {
                double t = frame.Time;
                var frameIds = new HashSet<int>();

                foreach (var obj in frame.Objects)
                {
                    if (obj.Nome != "red") continue;

                    frameIds.Add(obj.Id);

                    if (!firstY.ContainsKey(obj.Id))
                        firstY[obj.Id] = obj.Y1;

                    if (lastInfo.ContainsKey(obj.Id))
                        prevY[obj.Id] = lastInfo[obj.Id].y1;

                    lastInfo[obj.Id] = (t, obj.Y1, obj.Y2);

                    if (obj.Y1 <= 0 && !emitted.Contains(obj.Id))
                    {
                        eventos.Add(new Event(t, t,
                            $"Sinal vermelho saiu pelo topo (ID {obj.Id})"));
                        emitted.Add(obj.Id);
                    }
                }

                var disappeared = activeIds.Except(frameIds);
                foreach (var oid in disappeared)
                {
                    if (emitted.Contains(oid)) continue;
                    if (!lastInfo.TryGetValue(oid, out var info)) continue;

                    bool movingUp =
                        prevY.ContainsKey(oid) && info.y1 < prevY[oid];

                    double deltaFirst =
                        firstY.GetValueOrDefault(oid, info.y1) - info.y1;

                    if (movingUp && deltaFirst >= minDelta)
                    {
                        eventos.Add(new Event(info.t, info.t,
                            $"Sinal vermelho saiu pelo topo (ID {oid})"));
                        emitted.Add(oid);
                    }
                }

                activeIds = frameIds;
            }

            return eventos;
        }

        private static List<Event> DetectaEntradasESaidas(Video video)
        {
            var eventos = new List<Event>();
            var firstSeen = new Dictionary<(string, int), double>();
            var lastSeen = new Dictionary<(string, int), double>();

            foreach (var frame in video.Frames)
            {
                double t = frame.Time;
                foreach (var obj in frame.Objects)
                {
                    var key = (obj.Nome, obj.Id);

                    if (!firstSeen.ContainsKey(key))
                        firstSeen[key] = t;

                    lastSeen[key] = t;
                }
            }

            foreach (var kv in firstSeen)
            {
                var (nome, id) = kv.Key;
                double start = kv.Value;
                double end = lastSeen.GetValueOrDefault(kv.Key, start);

                eventos.Add(new Event(start, end,
                    $"{nome} {id} tempo em cena"));
            }

            return eventos;
        }

        private static List<Event> DetectaAlinhamentos(Video video)
        {
            var eventos = new List<Event>();
            var prevAlign = new HashSet<(string, int, string, int)>();
            var alignStart = new Dictionary<(string, int, string, int), double>();

            foreach (var frame in video.Frames)
            {
                double t = frame.Time;
                var objs = frame.Objects;

                for (int i = 0; i < objs.Count; i++)
                {
                    for (int j = i + 1; j < objs.Count; j++)
                    {
                        var a = objs[i];
                        var b = objs[j];

                        if (HorizontallyAligned(a, b))
                        {
                            var key = NormalizePair(a, b);
                            if (!prevAlign.Contains(key))
                                alignStart[key] = t;
                        }
                    }
                }

                var current = new HashSet<(string, int, string, int)>(
                    alignStart.Keys
                );

                foreach (var pair in prevAlign.Except(current))
                {
                    eventos.Add(new Event(
                        alignStart[pair],
                        t,
                        $"{pair.Item1} {pair.Item2} tempo de alinhamento com {pair.Item3} {pair.Item4}"
                    ));
                    alignStart.Remove(pair);
                }

                prevAlign = current;
            }

            return eventos;
        }

        private static List<Event> DetectaOverlap(Video video)
        {
            var eventos = new List<Event>();
            var prevOver = new HashSet<(string, int, string, int)>();
            var overStart = new Dictionary<(string, int, string, int), double>();

            foreach (var frame in video.Frames)
            {
                double t = frame.Time;
                var objs = frame.Objects;

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

                var current = new HashSet<(string, int, string, int)>(
                    overStart.Keys
                );

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

        // ========= HELPERS =========

        private static bool BoxesOverlap(DetectedObject a, DetectedObject b)
        {
            return Math.Min(a.X2, b.X2) > Math.Max(a.X1, b.X1)
                && Math.Min(a.Y2, b.Y2) > Math.Max(a.Y1, b.Y1);
        }

        private static bool HorizontallyAligned(DetectedObject a, DetectedObject b, double tolerance = 0.2)
        {
            double ha = a.Y2 - a.Y1;
            double hb = b.Y2 - b.Y1;
            double refH = Math.Min(ha, hb);
            if (refH <= 0) return false;

            double cya = (a.Y1 + a.Y2) / 2;
            double cyb = (b.Y1 + b.Y2) / 2;

            return Math.Abs(cya - cyb) <= tolerance * refH;
        }

        private static (string, int, string, int) NormalizePair(DetectedObject a, DetectedObject b)
        {
            return string.Compare(a.Nome, b.Nome, StringComparison.Ordinal) <= 0
                ? (a.Nome, a.Id, b.Nome, b.Id)
                : (b.Nome, b.Id, a.Nome, a.Id);
        }
    }
}
