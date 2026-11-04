import { defineRailway, github, postgres, preserve, project, service, volume } from "railway/iac";

export default defineRailway(() => {
  const LaunchScope = github("jems0906/LaunchScope");

  const Postgres = postgres("Postgres", { region: "us-west2" });
  Postgres.networking = { privateNetworkEndpoint: "postgres" };
  const postgresVolume = volume("postgres-volume", { alerts: { usage: { "100": {}, "80": {}, "95": {} } }, allowOnlineResize: true, region: "us-west2", sizeMB: 50000 });
  const api = service("api", {
    source: LaunchScope,
    healthcheck: "/api/health",
    replicas: { "us-west2": 1 },
    env: { DATABASE_URL: preserve(), PORT: preserve(), RAILWAY_DOCKERFILE_PATH: preserve(), SESSION_COOKIE_SECURE: preserve() },
  });
  const frontend = service("frontend", {
    source: LaunchScope,
    healthcheck: "/api/health",
    replicas: { "us-west2": 1 },
    env: { API_HOST: preserve(), PORT: preserve(), RAILWAY_DOCKERFILE_PATH: preserve() },
  });

  return project("LaunchScope", {
    resources: [api, Postgres, frontend, postgresVolume],
  });
});
