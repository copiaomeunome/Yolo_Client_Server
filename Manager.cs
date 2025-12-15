using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.Net.Http;
using System.Net.Http.Headers;
using System.Text.Json;
using System.Threading.Tasks;
using Classes.Events;
using Detection;

namespace ManagerApp
{
    public static class Manager
    {
        private static readonly string RootDir = Directory.GetCurrentDirectory();
        private static readonly string PythonDir = Path.Combine(RootDir, "python");
        private static readonly string PythonScript = Path.Combine(PythonDir, "processPy", "Yolo_Inference.py");

        public static async Task<int> RunAsync(string[] args)
        {
            LoadEnvFromFile();
            string videoPath = args.Length > 0 ? args[0] : Path.Combine("uploads", "carro.mp4");
            if (!Path.IsPathRooted(videoPath))
            {
                videoPath = Path.Combine(RootDir, videoPath);
            }

            try
            {
                string raw = await RunPythonInferenceAsync(videoPath);
                var video = ParseVideo(raw);
                if (video == null)
                {
                    Console.Error.WriteLine("Nao foi possivel interpretar a saida do Yolo_Inference.py como JSON de video.");
                    return 1;
                }

                var events = VideoEventDetectors.ListEvents(video);

                Console.WriteLine("Eventos detectados:");
                foreach (var ev in events)
                {
                    Console.WriteLine($"{ev.tInit:0.00}-{ev.tEnd:0.00} | {ev.name}");
                }

                await CallOpenAIAsync(events);
                return 0;
            }
            catch (Exception ex)
            {
                Console.Error.WriteLine($"Falha na execucao do Manager: {ex.Message}");
                return 1;
            }
        }

        private static async Task CallOpenAIAsync(List<Event> events)
        {
            string apiKey = (Environment.GetEnvironmentVariable("OPENAI_API_KEY") ?? string.Empty).Trim().Trim('\"').Trim('\'');
            if (string.IsNullOrWhiteSpace(apiKey))
            {
                Console.Error.WriteLine("OPENAI_API_KEY nao configurada no ambiente.");
                return;
            }

            var payload = BuildPayload(events);

            using var http = new HttpClient();
            http.DefaultRequestHeaders.Authorization = new AuthenticationHeaderValue("Bearer", apiKey);

            var json = JsonSerializer.Serialize(payload);
            var content = new StringContent(json, System.Text.Encoding.UTF8, "application/json");

            var response = await http.PostAsync("https://api.openai.com/v1/chat/completions", content);
            var responseJson = await response.Content.ReadAsStringAsync();

            Console.WriteLine("Resposta do modelo:");
            Console.WriteLine(responseJson);
        }

        /// <summary>
        /// Le um arquivo .env na raiz e preenche o ambiente se as chaves nao estiverem definidas.
        /// Suporta linhas no formato KEY=VALUE.
        /// </summary>
        private static void LoadEnvFromFile()
        {
            string envPath = Path.Combine(RootDir, ".env");
            if (!File.Exists(envPath))
            {
                return;
            }

            foreach (var line in File.ReadAllLines(envPath))
            {
                if (string.IsNullOrWhiteSpace(line) || line.TrimStart().StartsWith("#"))
                    continue;

                int idx = line.IndexOf('=');
                if (idx <= 0) continue;

                string key = line[..idx].Trim();
                string value = line[(idx + 1)..].Trim().Trim('\"').Trim('\'');

                if (string.IsNullOrEmpty(key)) continue;

                // So define se ainda nao existir
                if (string.IsNullOrWhiteSpace(Environment.GetEnvironmentVariable(key)))
                {
                    Environment.SetEnvironmentVariable(key, value);
                }
            }
        }

        private static async Task<string> RunPythonInferenceAsync(string videoPath)
        {
            var psi = new ProcessStartInfo
            {
                FileName = "python",
                RedirectStandardOutput = true,
                RedirectStandardError = true,
                UseShellExecute = false,
                WorkingDirectory = PythonDir,
            };

            psi.Environment["PYTHONPATH"] = PythonDir;
            psi.ArgumentList.Add(PythonScript);
            psi.ArgumentList.Add(videoPath);

            var proc = Process.Start(psi) ?? throw new InvalidOperationException("Nao foi possivel iniciar processo do Python.");

            string stdout = await proc.StandardOutput.ReadToEndAsync();
            string stderr = await proc.StandardError.ReadToEndAsync();
            await proc.WaitForExitAsync();

            if (!string.IsNullOrWhiteSpace(stderr))
            {
                Console.Error.WriteLine(stderr);
            }

            if (proc.ExitCode != 0)
            {
                throw new InvalidOperationException($"Yolo_Inference.py retornou codigo {proc.ExitCode}.");
            }

            return stdout;
        }

        private static Video? ParseVideo(string json)
        {
            var options = new JsonSerializerOptions
            {
                PropertyNameCaseInsensitive = true
            };

            try
            {
                return JsonSerializer.Deserialize<Video>(json, options);
            }
            catch (Exception ex)
            {
                Console.Error.WriteLine($"Erro ao desserializar o JSON do video: {ex.Message}");
                return null;
            }
        }

        private static object BuildPayload(List<Event> events)
        {
            var logStruct = new List<object>();

            foreach (var ev in events)
            {
                logStruct.Add(new
                {
                    tInit = Math.Round(ev.tInit, 2),
                    tEnd = Math.Round(ev.tEnd, 2),
                    name = ev.name
                });
            }

            string logAsText = JsonSerializer.Serialize(logStruct, new JsonSerializerOptions
            {
                WriteIndented = true,
                Encoder = System.Text.Encodings.Web.JavaScriptEncoder.UnsafeRelaxedJsonEscaping
            });

            string systemPrompt = """
            Voce e um analista de transito.

            Objetivo: Dado um log JSON de eventos (nomes em portugues), decidir para cada veiculo se ele atravessou um sinal vermelho. Use apenas as evidencias no log. Sempre responda somente com um array JSON; nenhum texto extra.

            EVENTOS IMPORTANTES (nomes aparecem exatamente como no log):
            - "<obj> <id> tempo em cena" -> objeto esteve presente de tInit ate tEnd.
            - "<objA> <idA> tempo de alinhamento com <objB> <idB>" ou "tempo de sobreposicao" -> centro alinhado ou caixas sobrepostas entre os objetos.
            - "Sinal vermelho saiu pelo topo (ID X)" -> o semaforo vermelho X desapareceu pelo topo do quadro; use como evidencia de que o sinal vermelho foi ultrapassado naquele momento.

            REGRAS DE INTERPRETACAO:
            1) Veiculos costumam aparecer como "carro", "car", "veiculo" (ou similares) seguidos de um id.
            2) Se um veiculo esta em cena quando ocorre "Sinal vermelho saiu pelo topo", considere forte evidencia de que ele avancou o sinal. Se o veiculo surge imediatamente antes e permanece enquanto o evento ocorre, trate como violacao.
            3) Se o veiculo entra apenas depois que o vermelho ja saiu ha algum tempo, marque como "inconclusivo" (nao e possivel afirmar).
            4) Caso nao haja qualquer evento de vermelho, devolva "inconclusivo" para todos.
            5) Sempre liste as evidencias como as strings de evento originais, em ordem cronologica, e use "inconclusivo" quando faltarem dados claros.

            FORMATO DE SAIDA (array JSON):
            - "veiculo": nome/id do veiculo (ex.: "carro 3").
            - "passou_sinal_vermelho": true | false | "inconclusivo".
            - "evidencias": lista minima de strings do log que sustentam a conclusao, em ordem temporal.
            - "notas": justificativa curta em uma frase.

            Nenhum outro texto alem do array JSON.
            """;

            string userMessage = $"""
            Aqui esta o log de eventos extraido do video (array JSON).
            Decida, seguindo as regras acima, se algum veiculo avancou o sinal vermelho e responda somente com o array JSON.

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
    }
}
