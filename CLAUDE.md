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

## Projeto escolhido: CampusLoop AI (desafio 01 — Done Means Done)
Decidido em 17/out ~13:00 PDT. Origem: conversa no ChatGPT + `Ideia Revenda Estados Unidos.pptx` (plano de negócio de revenda universitária; local, não vai para o GitHub).
- **Negócio (futuro):** recompra de itens no move-out de universitários (mini-fridge, microondas, mesa, cadeira...), montagem de kits e revenda no move-in. Modelo B = parceria com prédios de apartamentos universitários, piloto perto da NC State (Raleigh, NC). Slogan: "turn student move-out waste into affordable move-in solutions".
- **O que construímos hoje:** só o **motor de agentes**, não o marketplace. Nada de pagamento, entrega, login ou app mobile. Ofertas são simulações, com catálogo de teste de 10–20 itens.
- **Agentes:** Inventory (classifica itens/condição) · Pricing (oferta e margem) · Kit (monta 2–3 kits por demanda) · Verification (confere estoque, margem, restrições, recalls) · **Recursive Controller** (válido → finaliza; erro corrigível → replaneja e repete; precisa de aprovação → pede humano; limite de tentativas → para).
- **Momento-chave da demo:** o Kit Agent monta um kit de ~US$ 200 incluindo um frigobar já reservado para outro comprador; o Verification Agent detecta o conflito, o sistema NÃO declara concluído, volta ao planejador, troca o item, recalcula a margem e valida. Isso é o "Done Means Done".
- **Regra de design:** LLM (Crusoe) decide e raciocina; cálculos financeiros, checagem de estoque e regras de segurança são **código determinístico** (confiável e testável).
- **UI:** Streamlit mostrando decisões, custos, histórico de tentativas/correções.
- Alternativa descartada por ora: OneEntity AI (unificar cadastros de empresas dos EUA com dados públicos SEC/GLEIF).
- Pitch para mentor (EN): ver conversa do ChatGPT; pergunta final ao mentor: "scalable model — focus first on apartment partnerships or on the AI tech?".

## Status
- [x] Conta Crusoe, créditos e Intelligence API Key
- [x] Ambiente local: `.venv`, dependências, `core/crusoe_client.py`, `check_crusoe.py` — conexão testada, 4 modelos OK
- [x] Repo GitHub **público**: https://github.com/pedronasci1707-ship-it/recursive-agents-hackathon (amigo adicionado como colaborador)
- [x] Desafio e ideia escolhidos (CampusLoop AI)
- [x] Tarefas do amigo enviadas (Word local `CampusLoop - Tarefas do amigo.docx`): ele faz `app.py` (Streamlit), README em inglês e vídeo
- [x] Motor pronto e testado ao vivo (~12 s, 3/3 kits): `campusloop/engine.py` (controller), `agents.py` (Intake=DeepSeek Flash, Kit=Nemotron Super sem thinking, Reporter=Nemotron Lightning), `rules.py` (verificação determinística). Contrato motor↔UI em `docs/CONTRACT.md`; exemplo em `demo/sample_run.json` (`python -m campusloop.engine --save` regenera)
- [x] 11 testes offline (`python -m pytest`)
- [x] Site (Streamlit multipage, `app.py` + `ui/`): clientes (Ana/Marcus/Priya = estudantes, Jake = vendedor) veem só a loja com nav no topo: `ui/pages/student.py` (montar kit, trocar/remover item, resumo, agendar entrega), `shop.py` (catálogo + adicionar ao kit, re-verificado por `ui/store.py`), `seller.py` (foto via Gemma 4 vision ou texto → oferta → retirada). **Raciocínio dos agentes só para admin** (`admin@campusloop.ai`): `live.py` (tela dividida p/ vídeo) e `operations.py` (painel do Augusto). Design: `ui/components.py` (Inter, Material Symbols), `.streamlit/config.toml`, `assets/logo.svg`
- [ ] Deploy no Streamlit Community Cloud (usuário loga e cola a chave em Secrets: `CRUSOE_API_KEY = '...'`)
- **Divisão de arquivos:** Augusto mexe em `README.md` e no vídeo; nós em todo o resto (inclusive `app.py` e `ui/`)
- [x] Testes (cenário normal + falha induzida + recuperação)
- [ ] Vídeo de 1 min (EN) + README final (EN)
- [ ] Submeter até 16:45 PDT (prazo 17:00)

Cronograma: 13:15–15:30 build · 15:30–16:15 testes/polimento · 16:15–16:45 vídeo + README + submissão.

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
