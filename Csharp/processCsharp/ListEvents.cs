using System;
using System.Collections.Generic;
using System.Linq;
using Classes.Events;

public static class EventListBuilder
{
    public static List<Event> ListEvents(Video video)
    {
        var allEvents = new List<Event>();

        allEvents.AddRange(VideoEventDetectors.FuncObservaSinalVermelho(video));
        allEvents.AddRange(VideoEventDetectors.FuncDetectaEntradasESaidas(video));
        allEvents.AddRange(VideoEventDetectors.FuncDetectaAlinhamentos(video));
        allEvents.AddRange(VideoEventDetectors.FuncDetectaOverlap(video));

        allEvents.Sort((a, b) => a.tInit.CompareTo(b.tInit));

        return allEvents;
    }
}
