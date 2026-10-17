# Recursive Agents Hackathon — projeto do Pedro

Conversar com o usuário em **português**. Código, README, UI e vídeo de demo em **inglês** (jurados são de SF).

## Evento
- **The Recursive Agents Hackathon** — Crusoe x Cerebral Valley, sábado **17/out/2026**, San Francisco (durante a PyTorch Conference). Evento 9h–22h PDT.
- **Prazo de submissão: 17:00 PDT de hoje.** O computador já está em horário do Pacífico.
- Equipe: Pedro + um amigo (máx. 4). Mesma organização Crusoe, uma Intelligence API Key para cada um, mesmo repo.
- Prêmios: US$ 25 mil + NVIDIA RTX 5090. US$ 50 de créditos Crusoe na organização (cartão cadastrado → limites altos: 600 RPM / 2M TPM por modelo).
- **Tema:** "build a team of agents you can walk away from" — o agente recebe um objetivo, planeja, cria sub-agentes, delega, agentes se comunicam, checam o próprio progresso, se recuperam de falhas e continuam até terminar. Loops persistentes, não one-shot.

### Os três desafios (escolher UM)
Fonte: resumo do ChatGPT a partir das fotos dos slides (as imagens originais não vieram no link).
| # | Nome | O que demonstrar |
|---|---|---|
| 01 | **Done Means Done** | Agentes executam, verificam se concluíram de verdade, corrigem falhas e sabem parar |
| 02 | **Shared Brain** | Vários agentes compartilham memória persistente e reutilizam conhecimento |
| 03 | **Version N+1** | Agentes aprendem com as próprias execuções e mostram melhoria mensurável |

### Requisitos de entrega
- Usar **Crusoe Managed Inference** (obrigatório).
- Código **open source**, feito durante o evento, em **repositório GitHub público**.
- **Vídeo de 1 minuto** mostrando funcionalidades e código.
- Submissão com links públicos e todos os integrantes adicionados.
- O que pontua: autonomia, comunicação entre agentes, verificação de resultados, recuperação de falhas.

## Status
- [x] Conta Crusoe, créditos e Intelligence API Key (chave apareceu num print no ChatGPT — usuário optou por manter; recomendado revogar e gerar outra)
- [x] Ambiente local: `.venv`, dependências, `core/crusoe_client.py`, `check_crusoe.py`
- [ ] Chave colada no `.env` e `python check_crusoe.py` passando
- [ ] Repo GitHub público criado e amigo adicionado como colaborador
- [ ] **Escolher o desafio e a ideia** ← próximo passo
- [ ] MVP → testes (cenário normal + falha induzida + recuperação) → vídeo → submissão

Cronograma sugerido: até 12:15 ideia definida · 12:15–15:00 build · 15:00–16:00 testes/polimento · 16:00–16:45 vídeo + README · **16:45 submeter** (margem antes das 17:00).

## Crusoe Managed Inference
- Endpoint OpenAI-compatible: `https://api.inference.crusoecloud.com/v1`. Referência completa: skill `.claude/skills/crusoe-hackathon/SKILL.md` (arquivo oficial da Crusoe) — consultar antes de qualquer dúvida sobre modelos, parâmetros e erros.
- IDs são **case-sensitive**; a verdade é `GET /v1/models` (rodar `python check_crusoe.py`). Ex.: `deepseek-ai/Deepseek-V4-Flash` (com "s" minúsculo).
- **Não usar** `meta-llama/Llama-3.3-70B-Instruct` (descontinuado) nem hostnames antigos (`api.crusoe.ai`).
- Modelos por papel em `core/crusoe_client.py` (`MODELS`, sobrescrevíveis via `.env`):
  - `planner` → `nvidia/NVIDIA-Nemotron-3-Super-120B-A12B` (agentes colaborativos, tool use)
  - `worker` → `nvidia/Nemotron-3.5-Lightning-30B-A3B` (sub-agentes de longa duração, barato)
  - `fast` → `deepseek-ai/Deepseek-V4-Flash` (alto volume, barato)
  - `tools` → `openai/gpt-oss-120b` (tool calling mais confiável)
- Modelos de raciocínio gastam `max_tokens` pensando: usar ≥1024; `content` vazio + `finish_reason=length` = faltou token.
- Prefix caching: manter system prompt e tools byte-idênticos e histórico append-only (mais barato e rápido).
- Tool calling: anexar a mensagem do assistant com `tool_calls` **antes** das mensagens `role: "tool"`.

## Convenções
- Todas as chamadas de modelo passam por `core.crusoe_client.chat()` (backoff, roteamento, contagem de tokens).
- Todo loop de agente tem limites explícitos: máx. de iterações, tempo e tokens. Nada de loop infinito.
- Stack: Python 3.14 (`.venv`), `openai` SDK, Streamlit para a demo, SQLite para memória/estado. Nada de Kubernetes, fine-tuning ou frameworks pesados sem necessidade.
- Segurança: nunca commitar `.env`, nunca imprimir a chave, chave entre aspas simples no `.env` (pode conter `$`).
- Rodar comandos Python com `.venv/Scripts/python.exe` (Windows).
