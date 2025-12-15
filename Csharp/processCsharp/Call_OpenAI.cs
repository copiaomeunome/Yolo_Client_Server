using System;
using System.Collections.Generic;
using System.Text.Json;
using System.Text.Json.Serialization;
using System.Net.Http;
using System.Net.Http.Headers;
using System.Threading.Tasks;
using Classes.Events;

class Program
{
    static readonly string OpenAiApiKey = 
        Environment.GetEnvironmentVariable("OPENAI_API_KEY");

    static async Task Main(string[] args)
    {
        var exemplo = new List<Event>
        {
            new Event(0.00, 10.00, "trabalhador 1 tempo em cena"),
            new Event(0.00, 8.00, "capacete 1 tempo em cena"),
            new Event(0.50, 0.50, "trabalhador 1 sobrepos capacete 1"),
            new Event(5.00, 5.00, "trabalhador 1 alinhado com capacete 1"),
        };

        // await CallOpenAI(exemplo);
    }

    /// <summary>
    /// Converte a lista de objetos Event em um JSON simples
    /// </summary>
    static List<object> ConvertEventsToJson(List<Event> events)
    {
        var converted = new List<object>();

        foreach (var ev in events)
        {
            converted.Add(new
            {
                tInit = Math.Round(ev.tInit, 2),
                tEnd = Math.Round(ev.tEnd, 2),
                name = ev.name
            });
        }

        return converted;
    }

    /// <summary>
    /// Monta o payload a ser enviado para a API
    /// </summary>
    static object BuildPayload(List<Event> events)
    {
        var logStruct = ConvertEventsToJson(events);

        var jsonOptions = new JsonSerializerOptions
        {
            WriteIndented = true,
            Encoder = System.Text.Encodings.Web.JavaScriptEncoder.UnsafeRelaxedJsonEscaping
        };

        string logAsText = JsonSerializer.Serialize(logStruct, jsonOptions);

        Console.WriteLine(logAsText);

        string systemPrompt = """
        Voce e um analista de transito.

        Objetivo: Dado um log JSON de eventos (nomes em portugues), decidir para cada veiculo se ele atravessou um sinal vermelho. Use apenas as evidencias no log. Sempre responda somente com um array JSON; nenhum texto extra.

        EVENTOS IMPORTANTES (nomes aparecem exatamente como no log):
        - "<obj> <id> tempo em cena"
        - "<objA> <idA> tempo de alinhamento com <objB> <idB>" ou "tempo de sobreposicao"
        - "Sinal vermelho saiu pelo topo (ID X)"

        REGRAS DE INTERPRETACAO:
        1) Veiculos costumam aparecer como "carro", "car", "veiculo".
        2) Se um veiculo esta em cena quando ocorre "Sinal vermelho saiu pelo topo", considere violacao.
        3) Se entrar depois, marque "inconclusivo".
        4) Se nao houver vermelho, tudo inconclusivo.
        5) Liste evidencias cronologicamente.

        FORMATO DE SAIDA:
        - veiculo
        - passou_sinal_vermelho
        - evidencias
        - notas

        Nenhum texto fora do JSON.
        """;

        string userMessage = $"""
        Aqui esta o log de eventos extraido do video (array JSON).
        Decida se algum veiculo avancou o sinal vermelho.

        Log:
        {logAsText}
        """;

        return new
        {
            model = "gpt-4.1-mini",
            messages = new[]
            {
                new { role = "system", content = systemPrompt },
                new { role = "user", content = userMessage }
            },
            temperature = 0.0,
            max_tokens = 1000
        };
    }

    /// <summary>
    /// Chamada à API OpenAI
    /// </summary>
    static async Task CallOpenAI(List<Event> events)
    {
        try
        {
            var payload = BuildPayload(events);

            using var http = new HttpClient();
            http.DefaultRequestHeaders.Authorization =
                new AuthenticationHeaderValue("Bearer", OpenAiApiKey);

            var content = new StringContent(
                JsonSerializer.Serialize(payload),
                System.Text.Encoding.UTF8,
                "application/json"
            );

            var response = await http.PostAsync(
                "https://api.openai.com/v1/chat/completions",
                content
            );

            var responseJson = await response.Content.ReadAsStringAsync();

            Console.WriteLine("Resposta do modelo:");
            Console.WriteLine(responseJson);
        }
        catch (Exception ex)
        {
            Console.WriteLine("Erro ao chamar a API:");
            Console.WriteLine(ex.Message);
        }
    }
}
