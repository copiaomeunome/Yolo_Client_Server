using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Net.Http;
using System.Reflection;
using System.Runtime.Loader;
using Classes.Events;
using Classes.Videos;
using Microsoft.CodeAnalysis;
using Microsoft.CodeAnalysis.CSharp;

public static class EventListBuilder
{
    public static List<Event> ListEvents(Video video, string codigoFonte)
    {
        Assembly assembly = CompilarCodigo(codigoFonte);
        return ExecutarScript(assembly, video);
    }

    private static Assembly CompilarCodigo(string codigoFonte)
    {
        var syntaxTree = CSharpSyntaxTree.ParseText(codigoFonte);

        var references = AppDomain.CurrentDomain.GetAssemblies()
            .Where(a => !a.IsDynamic && !string.IsNullOrEmpty(a.Location))
            .Select(a => MetadataReference.CreateFromFile(a.Location))
            .Cast<MetadataReference>();

        var compilation = CSharpCompilation.Create(
            "CodigoDinamico",
            new[] { syntaxTree },
            references,
            new CSharpCompilationOptions(OutputKind.DynamicallyLinkedLibrary)
        );

        using var ms = new MemoryStream();
        var result = compilation.Emit(ms);

        if (!result.Success)
        {
            var erros = string.Join(Environment.NewLine, result.Diagnostics);
            throw new InvalidOperationException("Erro ao compilar codigo dinamico:" + Environment.NewLine + erros);
        }

        ms.Seek(0, SeekOrigin.Begin);
        return AssemblyLoadContext.Default.LoadFromStream(ms);
    }

    private static List<Event> ExecutarScript(Assembly assembly, Video video)
    {
        const string tipoNome = "ScriptDinamico";
        const string metodoNome = "funcPrincipal";

        var tipo = assembly.GetType(tipoNome)
                   ?? throw new InvalidOperationException($"Tipo '{tipoNome}' nao encontrado no script.");

        var metodo = tipo.GetMethod(metodoNome, BindingFlags.Public | BindingFlags.Static)
                     ?? throw new InvalidOperationException($"Metodo '{metodoNome}' nao encontrado no script.");

        var retorno = metodo.Invoke(null, new object[] { video });
        if (retorno is List<Event> eventos)
        {
            return eventos;
        }

        throw new InvalidOperationException($"Metodo '{metodoNome}' retornou tipo inesperado: {retorno?.GetType().FullName ?? "null"}");
    }
}
