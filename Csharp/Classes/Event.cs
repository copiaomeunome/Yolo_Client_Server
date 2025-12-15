namespace Classes.Events
{
    public class Event
    {
        public double tInit { get; set; }
        public double tEnd { get; set; }
        public string name { get; set; }

        public Event(double tInit, double tEnd, string name)
        {
            this.tInit = tInit;
            this.tEnd = tEnd;
            this.name = name;
        }
    }
}
