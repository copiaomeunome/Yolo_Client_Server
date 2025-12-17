using System;
using System.Collections.Generic;
using System.Net.Http;
using System.Net.Http.Headers;
using System.Text;
using System.Text.Json;
using System.Threading.Tasks;
using Classes.Events;

namespace ManagerApp.APIService
{
    public static class CallAPIService
    {
        public static async Task<string> CallOpenAIAsync(string urlRunPrompt, int handlerID, List<Event> events, string urlPromptState)
        {
            using var http = new HttpClient();
            string eventsJson = JsonSerializer.Serialize(events);

            // Dispara o prompt
            var payloadRun = new
            {
                secret = "DKa0123Ddjslbb__s91hgISAj",
                handlerId = handlerID,
                input = eventsJson,
                async = "true"
            };

            var contentRun = new StringContent(JsonSerializer.Serialize(payloadRun), Encoding.UTF8, "application/json");
            var responseRun = await http.PostAsync(urlRunPrompt, contentRun);
            responseRun.EnsureSuccessStatusCode();

            string runBody = await responseRun.Content.ReadAsStringAsync();
            using var runDoc = JsonDocument.Parse(runBody);
            string promptID = ExtractString(runDoc.RootElement, "executeprompt_process_id");
            if (string.IsNullOrWhiteSpace(promptID))
            {
                throw new InvalidOperationException("Nao foi possivel obter executeprompt_process_id do retorno do prompt.");
            }

            // Loop de verificacao
            const int maxTentativas = 60;
            for (int i = 0; i < maxTentativas; i++)
            {
                var status = await VerificaPrompt(urlPromptState, handlerID, promptID);
                if (status.StatusCode.Equals("Finished", StringComparison.OrdinalIgnoreCase))
                {
                    return status.Response ?? status.RawResponse;
                }
                if (status.StatusCode.Equals("Canceled", StringComparison.OrdinalIgnoreCase))
                {
                    throw new InvalidOperationException("Prompt foi cancelado ao consultar status.");
                }

                await Task.Delay(1000);
            }

            throw new TimeoutException("Timeout aguardando prompt finalizar.");
        }

        public static string getNextVideoAvailable(string url)
        {
            using var http = new HttpClient();
            string response = http.GetStringAsync(url).GetAwaiter().GetResult();
            if (string.IsNullOrWhiteSpace(response))
            {
                throw new InvalidOperationException("A API retornou vazio.");
            }
            return response;
        }

        // Notifica que o video foi processado via POST com o JSON do timeline e promptReset.
        public static async Task onVideoProcessingFinished(string onProcessedUrl, int videoID, JsonElement timelineJson, string promptReset)
        {
            using var http = new HttpClient();
            var payload = new
            {
                videoID,
                timeline = timelineJson,
                promptReset
            };

            var content = new StringContent(JsonSerializer.Serialize(payload), Encoding.UTF8, "application/json");
            var response = await http.PostAsync(onProcessedUrl, content);
            response.EnsureSuccessStatusCode();
        }

        private static async Task<PromptStatus> VerificaPrompt(string urlPromptState, int handlerID, string promptID)
        {
            using var http = new HttpClient();
            var payload = new
            {
                secret = "DKa0123Ddjslbb__s91hgISAj",
                handlerId = handlerID,
                executeprompt_process_id = promptID,
                getlog = false
            };

            var content = new StringContent(JsonSerializer.Serialize(payload), Encoding.UTF8, "application/json");
            var response = await http.PostAsync(urlPromptState, content);
            response.EnsureSuccessStatusCode();

            string body = await response.Content.ReadAsStringAsync();
            using var doc = JsonDocument.Parse(body);
            string statusCode = ExtractString(doc.RootElement, "status_code");
            string? resposta = null;
            if (doc.RootElement.TryGetProperty("response", out var respProp))
            {
                resposta = respProp.GetRawText();
            }

            return new PromptStatus
            {
                StatusCode = statusCode,
                Response = resposta,
                RawResponse = body
            };
        }

        private static string ExtractString(JsonElement root, string propertyName)
        {
            if (root.ValueKind == JsonValueKind.Object && root.TryGetProperty(propertyName, out var prop))
            {
                return prop.ValueKind switch
                {
                    JsonValueKind.String => prop.GetString() ?? string.Empty,
                    JsonValueKind.Number => prop.GetRawText(),
                    _ => prop.GetRawText()
                };
            }
            return string.Empty;
        }

        private class PromptStatus
        {
            public string StatusCode { get; set; } = string.Empty;
            public string? Response { get; set; }
            public string RawResponse { get; set; } = string.Empty;
        }
    }
}
