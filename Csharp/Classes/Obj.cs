using Classes.Points;
using System.Collections.Generic;
using System.Text.Json.Serialization;

namespace Classes.Objs
{
    public class Obj
    {
        public int id { get; set; }
        public string name { get; set; }
        public Point topLeft { get; set; }
        public Point bottomRight { get; set; }
        
        public List<Point> points { get; set; } // Lista vazia caso seja apenas a bounding box

        public Obj()
        {
            name = string.Empty;
            points = new List<Point>();
            topLeft = new Point(0, 0);
            bottomRight = new Point(0, 0);
        }

        public Obj(string name, int id, List<Point> points, Point topLeft, Point bottomRight)
        {
            this.name = name;
            this.points = points;
            this.id = id;
            this.bottomRight = bottomRight;
            this.topLeft = topLeft;
        }

        // Propriedades auxiliares para compatibilidade com detectores existentes
        [JsonIgnore] public int Id => id;
        [JsonIgnore] public string Nome => name;
        [JsonIgnore] public double X1 => topLeft?.x ?? 0;
        [JsonIgnore] public double Y1 => topLeft?.y ?? 0;
        [JsonIgnore] public double X2 => bottomRight?.x ?? 0;
        [JsonIgnore] public double Y2 => bottomRight?.y ?? 0;
    }
}
