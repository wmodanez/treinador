# Treinador de Corrida

Ferramentas em Python para geração de planos de treino e análise de corridas via Garmin Connect, integrado ao Claude Code via MCP.

**Meta atual:** 21 km — Maratona Monumental de Brasília, 22/11/2026.

---

## Estrutura do projeto

```
treinador/
├── auth.py                 # autenticação compartilhada com o Garmin Connect
├── calculadora.py          # pace, tempo estimado, progressão de volume
├── gerador_plano.py        # distribuição semanal de treinos por tipo
├── main.py                 # geração do plano de treino
├── baixar_treinos.py       # download de corridas do Garmin Connect
├── baixar_tudo.py          # download completo: corridas + dados diários
├── relatorio.py            # geração de relatórios PDF
├── requirements.txt        # dependências Python
├── dados/                  # JSONs baixados do Garmin
└── planos/                 # planos gerados e relatórios PDF
```

---

## Pré-requisitos

| Ferramenta  | Versão mínima | Instalação |
|-------------|---------------|------------|
| Python      | 3.11+         | [python.org](https://www.python.org/downloads/) |
| uv / uvx    | qualquer      | `pip install uv` ou [docs.astral.sh/uv](https://docs.astral.sh/uv/getting-started/installation/) |
| Claude Code | qualquer      | `npm install -g @anthropic-ai/claude-code` |

### Instalar dependências Python

```bash
python -m venv venv
venv\Scripts\activate      # Windows
pip install -r requirements.txt
```

---

## Configuração do MCP Garmin

O MCP permite que o Claude acesse treinos e métricas diretamente do Garmin Connect dentro da conversa.

### 1. Registrar o servidor MCP no Claude Code

Execute uma vez no terminal:

```bash
claude mcp add garmin-mcp -- uvx --python 3.12 --from git+https://github.com/Taxuspt/garmin_mcp garmin-mcp
```

### 2. Autenticar no Garmin Connect

Na primeira vez que o Claude invocar o MCP, ele pedirá as credenciais. Para autenticar manualmente antes de usar:

```bash
uvx --python 3.12 --from git+https://github.com/Taxuspt/garmin_mcp garmin-mcp
```

As credenciais ficam salvas em `~/.garminconnect` após a primeira autenticação.

### 3. Verificar se está funcionando

No Claude Code, dentro da pasta do projeto:

```
Quais foram minhas últimas 5 corridas no Garmin?
```

---

## Download de dados do Garmin

### `baixar_treinos.py` — somente corridas

```bash
python baixar_treinos.py                                    # últimas 20 corridas
python baixar_treinos.py --limite 50                        # últimas 50 corridas
python baixar_treinos.py --dias 30                          # últimos 30 dias
python baixar_treinos.py --inicio 2026-06-01                # de uma data até hoje
python baixar_treinos.py --inicio 2026-06-01 --fim 2026-06-30  # período específico
python baixar_treinos.py --saida junho.json                 # arquivo de saída personalizado
```

### `baixar_tudo.py` — corridas + dados diários

Baixa tudo de uma vez: corridas, sono, HRV, body battery, estresse, FC de repouso e prontidão para treino.

```bash
python baixar_tudo.py                                       # últimos 30 dias
python baixar_tudo.py --dias 60                             # últimos 60 dias
python baixar_tudo.py --inicio 2026-06-01                   # de uma data até hoje
python baixar_tudo.py --inicio 2026-06-01 --fim 2026-06-30  # período específico
python baixar_tudo.py --forcar                              # re-baixa datas já salvas
```

Dados coletados por dia:

| Tipo | Campos |
|------|--------|
| Sono | total, profundo, leve, REM, acordado, SpO2, respiração, score |
| HRV | última noite, pico 5 min, média semanal, baseline |
| Body battery | início, fim, mínimo e máximo do dia |
| Estresse | média e máximo do dia |
| FC de repouso | valor do dia |
| Prontidão | score e nível (GOOD / POOR / etc.) |
| Resumo diário | passos, calorias, distância, FC máxima |
| Corridas | distância, pace, duração, FC média, cadência, VO2Max |

### Autenticação

Na primeira execução o script pede e-mail, senha e código MFA (se ativado). O token de sessão é salvo em `~/.garminconnect` e reutilizado automaticamente. Credenciais via variáveis de ambiente:

```bash
set GARMIN_EMAIL=seu@email.com
set GARMIN_PASSWORD=suasenha
```

> **Erro 429:** Garmin bloqueia o IP após várias tentativas de login em sequência. Aguarde 30–60 minutos antes de tentar novamente.

Execuções repetidas **mesclam** os dados sem duplicar (deduplica por ID de atividade ou data).

---

## Geração de plano

```bash
python main.py                                              # usa parâmetros fixos definidos no arquivo
python main.py --auto                                       # infere volume e pace dos dados em dados/
python main.py --auto --semanas 16                          # idem com número de semanas personalizado
python main.py --auto --arquivo dados/garmin_2026-06-01_2026-07-23.json
python main.py --prova-nome "Maratona de SP" --distancia 42.195 --semanas 18
python main.py --auto --prova-nome "5k do Parque" --distancia 5 --semanas 8
```

Com `--auto`, o script lê o arquivo `garmin_*.json` mais recente de `dados/` e calcula:
- **Volume semanal** — média de km/semana dos últimos 28 dias
- **Pace base** — média ponderada por distância das últimas 8 corridas

Parâmetros fixos (editáveis em `main.py`):

```python
VOLUME_ATUAL_KM = 7.0    # km/semana atual
PACE_BASE       = "8:10" # pace atual em min/km
SEMANAS         = 18     # semanas de preparação
```

O plano é impresso no terminal e salvo em `planos/<slug-da-prova>.json` (ex.: `planos/maratona_de_sp.json`). O arquivo JSON inclui um bloco `metadata` com nome, distância e número de semanas da prova.

---

## Relatórios PDF

```bash
python relatorio.py plano    # relatório do plano de treino (lê planos/*.json mais recente)
python relatorio.py treinos  # análise de corridas (lê dados/*.json mais recente)

# Arquivo específico:
python relatorio.py plano   planos/maratona_de_sp.json
python relatorio.py treinos dados/garmin_2026-06-01_2026-07-23.json
```

Os PDFs são salvos em `planos/` com timestamp no nome. O subtítulo do relatório de plano é preenchido automaticamente a partir da metadata do JSON (nome e distância da prova). O relatório de treinos aceita tanto o formato do `baixar_treinos.py` (lista de corridas) quanto o do `baixar_tudo.py` (dict com corridas e dados diários).

---

## Tipos de treino gerados

| Tipo  | Fator de pace | Descrição                      |
|-------|---------------|--------------------------------|
| leve  | pace + 15%    | Recuperação ativa              |
| base  | pace + 5%     | Aeróbio fácil                  |
| alvo  | pace exato    | Ritmo da prova                 |
| tempo | pace − 5%     | Limiar (tempo run)             |
| longo | pace + 10%    | Corrida longa de fim de semana |

Distribuição semanal: Terça (base), Quinta (tempo), Sábado (leve), Domingo (longo).

Progressão de volume: +10% por semana, com semana de recuperação (−20%) a cada 4ª semana.

---

## Fluxo completo

```bash
# 1. Baixar dados do Garmin
python baixar_tudo.py --dias 30

# 2. Gerar plano baseado nos dados reais
python main.py --auto

# 3. Gerar relatório PDF
python relatorio.py treinos
python relatorio.py plano
```
