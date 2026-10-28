// Development only: SameSite=Lax cookies cannot cross localhost/IP sites.
export function canonicalDevelopmentUrl(apiBaseUrl, host, path) {
  try {
    const api = new URL(apiBaseUrl);
    const frontend = new URL(`http://${host}`);
    if (api.protocol !== 'http:' || api.hostname !== '127.0.0.1' || frontend.hostname !== 'localhost' || !path.startsWith('/')) return null;
    return `http://127.0.0.1${frontend.port ? `:${frontend.port}` : ''}${path}`;
  } catch {
    return null;
  }
}

export function canonicalDevelopmentOrigin(apiBaseUrl) {
  return {
    name: 'sicam-canonical-development-origin',
    apply: 'serve',
    configureServer(server) {
      server.middlewares.use((request, response, next) => {
        if (server.config.server.https || !['GET', 'HEAD'].includes(request.method)) return next();
        const target = canonicalDevelopmentUrl(apiBaseUrl, request.headers.host, request.url);
        if (!target) return next();
        response.writeHead(307, {Location: target, 'Cache-Control': 'no-store'});
        response.end();
      });
    },
  };
}
