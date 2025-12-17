using Classes.Frames;

namespace Classes.Videos
{
    public class Video
    {
        public List<Frame> frames { get; set; } = new();
        public int width { get; set; }
        public int height { get; set; }

        // Construtor padrao para desserializacao
        public Video() { }

        public Video(List<Frame> frames, int height, int width)
        {
            this.height = height;
            this.width = width;
            this.frames = frames;
        }
    }
}
