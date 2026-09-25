# SICAM Frontend — Vue 3 / Vite

Runtime validado: nvm, **Node 24.17.0**, **npm 11.13.0**, puerto **5173**.
Instalación completa: [guía WSL](../../../docs/developer_environment_setup_wsl.md).

## Instalar y arrancar

Con nvm instalado:

```bash
cd ~/repos/sicam-refactor/apps/web/Frontend
nvm use 24.17.0
npm ci
[ -f .env ] || cp .env.example .env
npm run dev -- --host 127.0.0.1 --port 5173
```

Revisar `.env`: `VITE_API_BASE_URL=http://127.0.0.1:8000`. Vite no carga el
archivo `.env.example` automáticamente; reiniciar si cambia `.env`.
Django debe estar disponible. Para decidir qué microservicios levantar, ver
[operación cotidiana](../../../docs/30_developer_startup_and_test_data.md).

El selector aparece sólo en SALIVA: Modelo SICAM (default) / Cellpose-SAM
alternativo. BLOOD no envía `segmentation_strategy`. El frontend llama sólo a
Django; método del resultado y estado editorial se presentan por separado.

## Validar

```bash
node --test tests/*.test.mjs
npm run build
```

No existe script `npm test`. La suite usa Node, Vue y Vite ya declarados; no
requiere instalar un framework. El smoke visual se realiza en navegador.

`npm run lint` usa `eslint . --fix --cache` y puede modificar archivos. Para
sólo comprobar: `node_modules/.bin/eslint .`. No ejecutar `npm audit fix` ni
instalar Axios aparte: ya está en el lockfile. No versionar `.env`,
`node_modules/` ni `dist/`.
