# ---------- Stage 1: build the React client ----------
# Preserve the existing toolchain for this rehearsal. Runtime upgrades are tracked
# in deploy/PLAN.md and are required before public production use.
FROM node:20-alpine AS client-build
WORKDIR /src/client-app

# restore dependencies first, so this layer is cached until package.json changes
COPY client-app/package.json client-app/package-lock.json ./
RUN npm ci

COPY client-app/ ./
# client-app/.env.production sets BUILD_PATH=../API/wwwroot
RUN mkdir -p /src/API/wwwroot && npm run build

# ---------- Stage 2: build and publish the API ----------
FROM mcr.microsoft.com/dotnet/sdk:7.0 AS build-env
WORKDIR /app

# copy .csproj and restore as distinct layers
COPY "Reactivites.sln" "Reactivites.sln"
COPY "API/API.csproj" "API/API.csproj"
COPY "Application/Application.csproj" "Application/Application.csproj"
COPY "Persistence/Persistence.csproj" "Persistence/Persistence.csproj"
COPY "Domain/Domain.csproj" "Domain/Domain.csproj"
COPY "Infrastructure/Infrastructure.csproj" "Infrastructure/Infrastructure.csproj"

RUN dotnet restore "Reactivites.sln"

# copy everything else and build
COPY . .
# the freshly built client, not whatever happens to be committed in the repo
COPY --from=client-build /src/API/wwwroot API/wwwroot
RUN dotnet publish "API/API.csproj" -c Release -o out --no-restore

# ---------- Stage 3: runtime image ----------
FROM mcr.microsoft.com/dotnet/aspnet:7.0
WORKDIR /app
RUN adduser --system --group --no-create-home --uid 10001 appuser
COPY --from=build-env /app/out .
COPY deploy/http-liveness.sh /app/http-liveness.sh

# the SQLite file lives here; mount a volume on it so data survives a redeploy
RUN mkdir -p /app/data && chown -R appuser:appuser /app

ENV ASPNETCORE_ENVIRONMENT=Production \
    ASPNETCORE_URLS=http://+:8080

USER appuser
EXPOSE 8080

# HTTP liveness only: this does not establish database readiness.
HEALTHCHECK --interval=15s --timeout=5s --start-period=60s --retries=3 \
    CMD ["bash", "/app/http-liveness.sh"]

ENTRYPOINT [ "dotnet", "API.dll" ]
