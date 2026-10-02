using System.Net.Http.Json;
using System.Text.Json.Serialization;

var builder = WebApplication.CreateBuilder(args);

builder.Services.AddCors(options =>
{
    options.AddPolicy("frontend", policy =>
        policy.WithOrigins("http://localhost:4200")
            .AllowAnyHeader()
            .AllowAnyMethod());
});
builder.Services.AddHttpClient<PythonReviewClient>(client =>
{
    var baseUrl = builder.Configuration["PythonService:BaseUrl"] ?? "http://127.0.0.1:8001";
    client.BaseAddress = new Uri(baseUrl.TrimEnd('/') + "/");
    client.Timeout = TimeSpan.FromSeconds(35);
});

var app = builder.Build();
app.UseCors("frontend");

app.MapGet("/health", () => Results.Ok(new { status = "ok" }));

app.MapPost("/api/reviews", async (
    ReviewRequest request,
    PythonReviewClient reviewClient,
    CancellationToken cancellationToken) =>
{
    if (string.IsNullOrWhiteSpace(request.Code))
    {
        return Results.ValidationProblem(new Dictionary<string, string[]>
        {
            ["code"] = ["Informe o código que deseja revisar."]
        });
    }

    if (request.Code.Length > 20_000)
    {
        return Results.ValidationProblem(new Dictionary<string, string[]>
        {
            ["code"] = ["O código deve ter no máximo 20.000 caracteres."]
        });
    }

    if (string.IsNullOrWhiteSpace(request.Language) || request.Language.Length > 40)
    {
        return Results.ValidationProblem(new Dictionary<string, string[]>
        {
            ["language"] = ["Informe uma linguagem com até 40 caracteres."]
        });
    }

    if (request.UseAi && request.Provider is not ("openrouter" or "gemini"))
    {
        return Results.ValidationProblem(new Dictionary<string, string[]>
        {
            ["provider"] = ["Selecione OpenRouter ou Gemini para a análise por IA."]
        });
    }

    try
    {
        var result = await reviewClient.ReviewAsync(request, cancellationToken);
        return Results.Ok(result);
    }
    catch (PythonReviewException exception)
    {
        return Results.Problem(
            title: "Falha na análise",
            detail: exception.Message,
            statusCode: (int)exception.StatusCode);
    }
    catch (HttpRequestException)
    {
        return Results.Problem(
            title: "Serviço de análise indisponível",
            detail: "Não foi possível conectar ao serviço Python. Verifique se ele está em execução.",
            statusCode: StatusCodes.Status503ServiceUnavailable);
    }
    catch (TaskCanceledException) when (!cancellationToken.IsCancellationRequested)
    {
        return Results.Problem(
            title: "Tempo limite da análise excedido",
            detail: "O serviço de análise demorou demais para responder.",
            statusCode: StatusCodes.Status504GatewayTimeout);
    }
})
.WithName("CreateReview");

app.Run();

public sealed record ReviewRequest(
    [property: JsonPropertyName("code")] string Code,
    [property: JsonPropertyName("language")] string Language,
    [property: JsonPropertyName("useAi")] bool UseAi = false,
    [property: JsonPropertyName("provider")] string Provider = "openrouter");

public sealed record ReviewFinding(
    string Title,
    string Severity,
    int Line,
    string Evidence,
    string Description,
    string Suggestion,
    string Category);

public sealed record ReviewResponse(
    string Summary,
    IReadOnlyList<ReviewFinding> Findings,
    string Provider);

public sealed record PythonErrorResponse(System.Text.Json.JsonElement? Detail);

public sealed class PythonReviewException(
    System.Net.HttpStatusCode statusCode,
    string message) : Exception(message)
{
    public System.Net.HttpStatusCode StatusCode { get; } = statusCode;
}

public sealed class PythonReviewClient(HttpClient httpClient)
{
    public async Task<ReviewResponse> ReviewAsync(
        ReviewRequest request,
        CancellationToken cancellationToken)
    {
        using var response = await httpClient.PostAsJsonAsync(
            "review",
            request,
            cancellationToken);
        if (!response.IsSuccessStatusCode)
        {
            var error = await response.Content.ReadFromJsonAsync<PythonErrorResponse>(
                cancellationToken: cancellationToken);
            var detail = error?.Detail is { ValueKind: System.Text.Json.JsonValueKind.String } value
                ? value.GetString()
                : null;
            throw new PythonReviewException(
                response.StatusCode,
                detail ?? $"O serviço Python retornou HTTP {(int)response.StatusCode}.");
        }

        return await response.Content.ReadFromJsonAsync<ReviewResponse>(
                   cancellationToken: cancellationToken)
               ?? throw new HttpRequestException("O serviço Python retornou uma resposta vazia.");
    }
}
