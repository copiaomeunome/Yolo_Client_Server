using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.Linq;
using System.Text.Json;
using System.Threading.Tasks;
using Classes.Events;
using Classes.Videos;
using ManagerApp.APIService;

namespace ManagerApp
{
    public static class Manager
    {
        private static readonly string RootDir = Directory.GetCurrentDirectory();
        private static readonly string PythonDir = Path.Combine(RootDir, "python");
        private static readonly string PythonScript = Path.Combine(PythonDir, "processPy", "Yolo_Inference.py");                                                                        //CAMINHO DA INFERÊNCIA
        private const string urlgetnextvd = "http://192.168.10.18:8000/pegatxt";                                                                                                        //URL DO GETNEXTVIDEOAVAILABLE
        private const string urlPrompt = "https://app2.globalcad.com.br/apiv1/InvokePublicFunc?formContract=2861&token=V15d30OASM4ifSys&uiculture=pt-BR&method=run_prompt";             //URL DO RUN_PROMPT
        private const string urlPromptState = "https://app2.globalcad.com.br/apiv1/InvokePublicFunc?formContract=2861&token=V15d30OASM4ifSys&uiculture=pt-BR&method=get_prompt_state";   //URL DO PROMPTSTATE
        private const string onProcessedUrl = "http://192.168.10.18:8000/onVideoProcessingFinished";                                                                                    //URL ONPROCESSEDVIDEO

        public static async Task<int> RunAsync(string[] args)
        {
            var response = CallAPIService.getNextVideoAvailable(urlgetnextvd);
            var jsonAPI = JsonDocument.Parse(response);

            string codigo = jsonAPI.RootElement.TryGetProperty("cSharpCode", out var codeProp)
                ? codeProp.GetString() ?? string.Empty
                : string.Empty;

            int videoID = jsonAPI.RootElement.TryGetProperty("videoId", out var videoIDProp)
                ? videoIDProp.GetInt32()
                : 0;

            int handlerID = jsonAPI.RootElement.TryGetProperty("handlerId", out var handlerIDProp)
                ? handlerIDProp.GetInt32()
                : 0;

            string videoURL = jsonAPI.RootElement.TryGetProperty("videoUrl", out var videoURLProp)
                ? videoURLProp.GetString() ?? string.Empty
                : string.Empty;

            string[] branches = jsonAPI.RootElement.TryGetProperty("branches", out var branchesProp)
                ? branchesProp
                    .EnumerateArray()
                    .Select(e => e.GetString() ?? string.Empty)
                    .Where(s => !string.IsNullOrWhiteSpace(s))
                    .ToArray()
                : Array.Empty<string>();

            string videoPath = !string.IsNullOrWhiteSpace(videoURL)
                ? Path.Combine("uploads", "carro.mp4")              //TROCAR AQUI
                : Path.Combine("uploads", "carro.mp4");
            string modelRepoPath = @"C:\Users\heito\OneDrive\Desktop\dev13\DataSetYolo";
            if (!Path.IsPathRooted(videoPath))
            {
                videoPath = Path.Combine(RootDir, videoPath);
            }

            try
            {
                string resultado = await RunPythonInferenceAsync(
                    videoPath,
                    modelRepoPath,
                    branches
                );

                Video? video = ParseVideo(resultado);
                if (video == null)
                {
                    Console.Error.WriteLine("Nao foi possivel interpretar a saida do Yolo_Inference.py como JSON de video.");
                    return 1;
                }

                var events = EventListBuilder.ListEvents(video, codigo);

                Console.WriteLine("Eventos detectados:");
                foreach (var ev in events)
                {
                    Console.WriteLine($"{ev.tInit:0.00}-{ev.tEnd:0.00} | {ev.name}");
                }
                var openAIResponse = await CallAPIService.CallOpenAIAsync(urlPrompt, handlerID, events, urlPromptState);

                using var timelineDoc = JsonDocument.Parse(openAIResponse);
                
                await CallAPIService.onVideoProcessingFinished(onProcessedUrl, videoID, timelineDoc.RootElement, "promptReset");
                return 0;
            }
            catch (Exception ex)
            {
                Console.Error.WriteLine($"Falha na execucao do Manager: {ex.Message}");
                return 1;
            }
        }

        // Roda uma unica inferencia passando todos os modelos (troca de branch apenas para coletar os pesos)
        private static async Task<string> RunPythonInferenceAsync(
            string videoPath,
            string modelRepoPath,
            string[] branches
        )
        {
            var modelPaths = new List<string>();
            var worktreesToRemove = new List<string>();
            var existingWorktrees = await GetWorktreesByBranchAsync(modelRepoPath);

            if (branches.Length == 0)
            {
                string modelPath = Path.Combine(
                    modelRepoPath,
                    "runs", "detect", "train", "weights", "best.pt"
                );
                modelPaths.Add(modelPath);
            }
            else
            {
                foreach (var branch in branches)
                {
                    Console.WriteLine($"Preparando modelo da branch: {branch}");

                    string worktreeDir;
                    if (existingWorktrees.TryGetValue(branch, out var existingDir))
                    {
                        worktreeDir = existingDir;
                        Console.WriteLine($"Reutilizando worktree existente para {branch} em {worktreeDir}");
                    }
                    else
                    {
                        worktreeDir = await RunGitWorktreeAddAsync(modelRepoPath, branch);
                        worktreesToRemove.Add(worktreeDir);
                    }

                    string modelPath = Path.Combine(worktreeDir, "runs", "detect", "train", "weights", "best.pt");
                    if (!File.Exists(modelPath))
                    {
                        throw new FileNotFoundException($"Modelo nao encontrado na branch {branch}", modelPath);
                    }

                    modelPaths.Add(modelPath);
                }
            }

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
            foreach (var modelPath in modelPaths)
            {
                psi.ArgumentList.Add(modelPath);
            }

            var proc = Process.Start(psi)
                ?? throw new InvalidOperationException("Nao foi possivel iniciar processo do Python.");

            string stdout = await proc.StandardOutput.ReadToEndAsync();
            string stderr = await proc.StandardError.ReadToEndAsync();
            await proc.WaitForExitAsync();

            if (!string.IsNullOrWhiteSpace(stderr))
            {
                Console.Error.WriteLine($"[Python] {stderr}");
            }

            if (proc.ExitCode != 0)
            {
                throw new InvalidOperationException("Yolo_Inference.py falhou.");
            }

            // Limpa worktrees criadas
            foreach (var wt in worktreesToRemove)
            {
                try
                {
                    await RunGitWorktreeRemoveAsync(modelRepoPath, wt);
                }
                catch (Exception ex)
                {
                    Console.Error.WriteLine($"Aviso: falha ao remover worktree {wt}: {ex.Message}");
                }
            }

            return stdout;
        }

        private static async Task<Dictionary<string, string>> GetWorktreesByBranchAsync(string repoPath)
        {
            var map = new Dictionary<string, string>(StringComparer.OrdinalIgnoreCase);

            var psi = new ProcessStartInfo
            {
                FileName = "git",
                Arguments = "worktree list --porcelain",
                WorkingDirectory = repoPath,
                RedirectStandardOutput = true,
                RedirectStandardError = true,
                UseShellExecute = false,
                CreateNoWindow = true
            };

            var proc = Process.Start(psi)
                ?? throw new InvalidOperationException("Nao foi possivel executar git.");

            string stdout = await proc.StandardOutput.ReadToEndAsync();
            await proc.WaitForExitAsync();

            string currentPath = string.Empty;
            foreach (var line in stdout.Split(new[] { '\r', '\n' }, StringSplitOptions.RemoveEmptyEntries))
            {
                if (line.StartsWith("worktree ", StringComparison.OrdinalIgnoreCase))
                {
                    currentPath = line.Substring("worktree ".Length).Trim();
                }
                else if (line.StartsWith("branch ", StringComparison.OrdinalIgnoreCase))
                {
                    var branchRef = line.Substring("branch ".Length).Trim();
                    const string prefix = "refs/heads/";
                    if (branchRef.StartsWith(prefix, StringComparison.OrdinalIgnoreCase))
                    {
                        string branchName = branchRef[prefix.Length..];
                        if (!string.IsNullOrEmpty(currentPath))
                        {
                            map[branchName] = currentPath;
                        }
                    }
                }
            }

            return map;
        }

        private static async Task<string> RunGitWorktreeAddAsync(string repoPath, string branch)
        {
            string worktreeDir = Path.Combine(Path.GetTempPath(), $"model_{branch}_{Guid.NewGuid():N}");

            var psi = new ProcessStartInfo
            {
                FileName = "git",
                Arguments = $"worktree add \"{worktreeDir}\" {branch}",
                WorkingDirectory = repoPath,
                RedirectStandardOutput = true,
                RedirectStandardError = true,
                UseShellExecute = false,
                CreateNoWindow = true
            };

            var proc = Process.Start(psi)
                ?? throw new InvalidOperationException("Nao foi possivel executar git.");

            string stderr = await proc.StandardError.ReadToEndAsync();
            await proc.WaitForExitAsync();

            if (proc.ExitCode != 0)
            {
                throw new InvalidOperationException($"Erro ao preparar worktree para branch {branch}: {stderr}");
            }

            return worktreeDir;
        }

        private static async Task RunGitWorktreeRemoveAsync(string repoPath, string worktreeDir)
        {
            var psi = new ProcessStartInfo
            {
                FileName = "git",
                Arguments = $"worktree remove --force \"{worktreeDir}\"",
                WorkingDirectory = repoPath,
                RedirectStandardOutput = true,
                RedirectStandardError = true,
                UseShellExecute = false,
                CreateNoWindow = true
            };

            var proc = Process.Start(psi)
                ?? throw new InvalidOperationException("Nao foi possivel executar git.");

            string stderr = await proc.StandardError.ReadToEndAsync();
            await proc.WaitForExitAsync();

            if (proc.ExitCode != 0)
            {
                throw new InvalidOperationException($"Erro ao remover worktree {worktreeDir}: {stderr}");
            }
        }

        private static Video? ParseVideo(string json)
        {
            var options = new JsonSerializerOptions
            {
                PropertyNameCaseInsensitive = true,
                IncludeFields = true
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
    }
}
