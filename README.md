# SRE Captura Física e Digital — Monorepo & Documentation Hub

Repositório central da equipe de **SRE Captura Física e Digital**, reunindo agentes de IA, automações multi-cloud, scripts operacionais, observabilidade (Dynatrace/Alerts) e o **Documentation Hub** publicado via **GitHub Pages (Static HTML By GitHub Actions)**.

---

## Estrutura do Repositório

```text
├── .github/
│   └── workflows/
│       └── deploy-pages.yml          # Workflow Static HTML (By GitHub Actions) + indexação Python
├── agents/                           # Agentes de IA, Chatbots operacionais e integrações Copilot
│   ├── chatbot/
│   ├── copilot/
│   └── ai-assistants/
├── automations/                      # Automações declarativas e workflows operacionais
│   ├── azure/
│   ├── aws/
│   ├── kubernetes/
│   └── examples/
├── scripts/                          # Tooling e scripts de automação/infraestrutura
│   ├── powershell/
│   ├── bash/
│   ├── python/
│   ├── terraform/
│   └── examples/
├── monitoring/                       # Observabilidade, SLOs, Synthetic checks e regras de alerta
│   ├── dynatrace/
│   ├── alerts/
│   └── examples/
├── docs/                             # Escopo publicado no GitHub Pages (Static HTML)
│   ├── .nojekyll                     # Desativa processamento Jekyll
│   ├── index.html                    # Portal SRE Captura Física e Digital (busca full-text + filtros)
│   ├── generate_index.py             # Indexador Python (gera docs/docs.json)
│   ├── docs.json                     # Catálogo gerado com metadados, datas Git e índice de busca
│   ├── arquiteturas/                 # Relatórios executivos de capacidade, resiliência e arquitetura
│   ├── runbooks/                     # Runbooks operacionais de resposta a incidentes
│   ├── procedimentos/                # Procedimentos operacionais padrão (POPs) e guias de onboarding
│   └── apresentacoes/                # Apresentações técnicas em HTML (slides interativos)
└── README.md
```

---

## Configuração no GitHub Pages (Static HTML By GitHub Actions)

1. No repositório GitHub, acesse **Settings → Pages**.
2. Em **Build and deployment → Source**, selecione **GitHub Actions** (opção **Static HTML — By GitHub Actions**).
3. Como este repositório já inclui o workflow `.github/workflows/deploy-pages.yml` configurado para o modo **Static HTML** (`actions/configure-pages@v5`, `actions/upload-pages-artifact@v3` com `path: './docs'` e `actions/deploy-pages@v4`), basta fazer `push` para `main` (ou acionar manualmente em **Actions → Deploy SRE Docs Hub to GitHub Pages → Run workflow**).
