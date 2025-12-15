using System.Collections.Generic;
using System.Text.Json.Serialization;

namespace Detection
{
    public class DetectedObject
    {
        [JsonPropertyName("id")]
        public int Id { get; set; }

        [JsonPropertyName("x1")]
        public double X1 { get; set; }

        [JsonPropertyName("y1")]
        public double Y1 { get; set; }

        [JsonPropertyName("x2")]
        public double X2 { get; set; }

        [JsonPropertyName("y2")]
        public double Y2 { get; set; }

        [JsonPropertyName("nome")]
        public string Nome { get; set; } = string.Empty;
    }

    public class Frame
    {
        [JsonPropertyName("time")]
        public double Time { get; set; }

        [JsonPropertyName("objects")]
        public List<DetectedObject> Objects { get; set; } = new();
    }

    public class Video
    {
        [JsonPropertyName("frames")]
        public List<Frame> Frames { get; set; } = new();

        [JsonPropertyName("width")]
        public int Width { get; set; }

        [JsonPropertyName("height")]
        public int Height { get; set; }
    }
}
