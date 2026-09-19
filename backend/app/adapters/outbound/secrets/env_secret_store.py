"""SecretStorePort minimo para la fase 0: lee de variables de entorno.

La seccion 9 del doc de arquitectura pide Windows Credential Manager via
`keyring` para la version final del panel -- se deja como
CredentialManagerSecretStore mas adelante (no instalado todavia: `keyring`
no esta en el entorno segun se verifico el 2026-09-18). Esta clase cumple el
mismo contrato para que el cambio futuro sea de una linea en config/settings.py.
"""
from __future__ import annotations

import os


class EnvSecretStore:
    def get(self, key: str) -> str | None:
        return os.environ.get(key) or None
