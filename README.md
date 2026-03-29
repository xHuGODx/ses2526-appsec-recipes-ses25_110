# AppSec SES

Este repositório guarda apenas automação e configuração de segurança.

Conteúdo versionado:
- `dast/` com scripts, configuração e documentação DAST
- `.github/workflows/` com os pipelines de segurança

Conteúdo que não deve existir aqui de forma permanente:
- `backend/`
- `frontend/`
- `docker-compose.yml` da aplicação

Uso local:
- manter o software repo em `../ses`, ou
- definir `APP_REPO_DIR=/caminho/para/o/software-repo`

Entradas principais:
- `dast/scripts/run-all.sh`
- `dast/scripts/run-restler-nightly.sh`
- `dast/instructions.md`
