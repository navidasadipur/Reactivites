# ---------- Stage 1: build the React client ----------
# Node 20: react-scripts 5.0.1 is not compatible with current Node releases.
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
RUN dotnet publish "API/API.csproj" -c Release -o out

# ---------- Stage 3: runtime image ----------
FROM mcr.microsoft.com/dotnet/aspnet:7.0
WORKDIR /app
COPY --from=build-env /app/out .

# the SQLite file lives here; mount a volume on it so data survives a redeploy
RUN mkdir -p /app/data

# the .NET 7 aspnet image listens on port 80 by default
EXPOSE 80

ENTRYPOINT [ "dotnet", "API.dll" ]
