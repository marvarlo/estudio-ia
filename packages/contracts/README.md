# packages/contracts/

Placeholder para el contrato compartido `timeline.json` entre el backend
Python y el sidecar Remotion (seccion 7 del doc de arquitectura), y para los
tipos TypeScript generados desde el OpenAPI del backend (seccion 4,
"contratos compartidos").

Nada que generar todavia en la fase 0: el frontend usa tipos escritos a mano
en `frontend/src/api/client.ts`, sincronizados manualmente con
`backend/app/adapters/inbound/api/schemas.py`. Cuando eso empiece a doler
(muchos endpoints, deriva frecuente), generar aca con `openapi-typescript`
contra `http://localhost:8000/openapi.json`.
