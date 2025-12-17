using Classes.Objs;

namespace Classes.Frames
{
    public class Frame
    {
        public List<Obj> objects { get; set; } = new();
        public double time { get; set; }

        // Construtor padrao para desserializacao
        public Frame() { }

        public Frame(List<Obj> objects, double time)
        {
            this.objects = objects;
            this.time = time;
        }
    }
}
