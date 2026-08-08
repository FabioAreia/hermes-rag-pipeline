# Sampling / temperature — porquê os swipes do ST voltam idênticos

## Sintoma

No SillyTavern, fazer swipe devolve sempre o mesmo texto. O `finish_reason` é `stop`
(normal — a resposta completa), mas a geração **não varia** entre swipes. No
OpenRouter aparecem múltiplas chamadas com o mesmo padrão input/output.

## Causa raiz (verificada no código do Hermes)

O ST usa `/v1/chat/completions` do gateway Hermes. Factos confirmados:

1. `_handle_chat_completions` em `gateway/platforms/api_server.py` **não lê**
   `temperature`, `top_p` nem `seed` do body do request do ST — simplesmente ignora.
2. O campo Hermes-nativo `model_options` só processa `reasoning` e `service_tier`
   (`_runtime_options_from_model_options`) — **não `temperature`/`sampling`**.
3. O gerador principal usa a sua própria temperatura; modelos de *reasoning*
   (ex: `deepseek-v4-flash`) decodificam quase deterministicamente → mesmo input,
   mesmo output.
4. Não existe chave de config `model.temperature` / `agent.temperature` (o `hermes
   config set model.temperature` é inválido — o `hermes` bin nem está no PATH do
   shell do container; corre de `/opt/hermes/.venv/bin/hermes`).

## Pontos de código relevantes (para quem for modificar)

- `gateway/platforms/api_server.py::_handle_chat_completions` (monta o pedido;
   não referencia temperature/seed).
- `gateway/platforms/api_server.py::_request_agent_overrides` — passa `model_options`
  cru para o agente.
- `gateway/platforms/api_server.py::_runtime_options_from_model_options` — traduz
  `model_options`; só reasoning + service_tier.
- `agent/auxiliary_client.py::_fixed_temperature_for_model` — devolve None para a
  maioria dos modelos (não impõe override), mas a temperatura do ST nunca chega.
- `agent/oneshot.py` — o default `temperature=0.3` é só para tarefas one-shot
  (título/commit), não a geração de chat principal.

## Conclusão prática

Até a stack evoluir, os sliders de sampling do ST **não têm efeito**. Não é o RAG,
não é o canon, não é slicing de histórico — é o caminho do sampling que não existe.

## Vias de solução (risco crescente)

1. **Trocar de modelo** (seguro): modelo de *chat* puro (não-reasoning) varia melhor
   com swipes que modelos de reasoning determinísticos.
2. **Aceitar e variar por prompt**: pedir explicitamente "escreve diferente / muda a
   abordagem" em vez de contar com temperatura.
3. **Escrever suporte no gateway** (invasivo): fazer `_runtime_options_from_model_options`
   consumir `model_options.sampling.temperature`/`top_p`/`seed` e encaminhá-los ao
   provider na geração principal. Mexe no core em produção, requer rebuild/restart do
   container — só com justificação forte e autorização do user.
