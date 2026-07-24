# Treinador de Corrida

Ferramentas em Python para geração de planos de treino e análise de corridas via Garmin Connect, integrado ao Claude Code via MCP.

---

## Estrutura do projeto

```
treinador/
├── auth.py              # autenticação compartilhada com o Garmin Connect
├── calculadora.py       # pace, tempo estimado, progressão de volume
├── gerador_plano.py     # distribuição semanal de treinos, fases e progressão
├── main.py              # CLI de geração do plano de treino
├── baixar_treinos.py    # download de corridas do Garmin Connect
├── baixar_tudo.py       # download completo: corridas + dados diários
├── relatorio_html.py    # relatórios HTML/PDF — análise e plano
├── requirements.txt     # dependências Python
├── dados/               # JSONs baixados do Garmin
└── planos/              # planos e relatórios gerados
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

### Instalar Chromium para geração de PDF (uma vez)

```bash
playwright install chromium
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
python baixar_treinos.py --inicio 2026-06-01 --fim 2026-06-30
python baixar_treinos.py --saida junho.json
```

### `baixar_tudo.py` — corridas + dados diários

```bash
python baixar_tudo.py                                       # últimos 30 dias
python baixar_tudo.py --dias 60
python baixar_tudo.py --inicio 2026-06-01
python baixar_tudo.py --inicio 2026-06-01 --fim 2026-06-30
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
# Parâmetros fixos definidos em main.py
python main.py

# Infere volume e pace dos dados do Garmin em dados/
python main.py --auto

# Personalizado
python main.py --prova-nome "Maratona Monumental 2026" --distancia 21 --semanas 17 \
               --data-inicio 2026-07-28 --data-prova 2026-11-22

python main.py --auto --prova-nome "5k do Parque" --distancia 5 --semanas 8
```

Com `--auto`, o script lê o `garmin_*.json` mais recente de `dados/` e calcula:
- **Volume semanal** — média de km/semana dos últimos 28 dias
- **Pace base** — média ponderada por distância das últimas 8 corridas

Parâmetros fixos (editáveis em `main.py`):

```python
VOLUME_ATUAL_KM = 7.0    # km/semana atual
PACE_BASE       = "8:10" # pace atual em min/km
SEMANAS         = 18     # semanas de preparação
PROVA_NOME      = "Minha Prova"
PROVA_DISTANCIA = 21.0
```

O plano é salvo em `planos/<slug-da-prova>.json` com metadados completos (nome, distância, semanas, datas). Cada semana inclui fase do plano, long run, foco da semana e período de datas.

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

Fases do plano geradas automaticamente conforme o número de semanas:

| Fase | % do plano | Foco |
|------|-----------|------|
| BASE | 30% | Adaptação, cadência, volume crescente |
| DESENVOLVIMENTO | 30% | Introdução do tempo run, long runs mais longos |
| PICO | 22% | Volume máximo, simulação de ritmo de prova |
| POLIMENTO | 18% | Taper progressivo, descanso final |

---

## Relatórios HTML/PDF

```bash
# Gera HTML + PDF (padrão)
python relatorio_html.py plano             # lê planos/*.json mais recente
python relatorio_html.py treinos           # lê dados/*.json mais recente

# Arquivo específico
python relatorio_html.py plano   planos/maratona_monumental_2026.json
python relatorio_html.py treinos dados/garmin_2026-06-01_2026-07-23.json

# Apenas HTML (sem conversão para PDF)
python relatorio_html.py plano --html-only
```

Os arquivos são salvos em `planos/` com timestamp no nome (`relatorio_plano_YYYYMMDD_HHMM.html/.pdf`).

### Relatório de plano

- Badge da prova com data e contagem regressiva
- KPIs: semanas de treino, corrida mais longa, pico semanal, pace alvo
- Barra de fases colorida (BASE → DESENVOLVIMENTO → PICO → POLIMENTO)
- Gráfico de progressão do long run com pontos coloridos por fase
- Tabela semana a semana: período, volume, long run, foco e badge de fase/recuperação
- Cards de referência de ritmos calculados do pace base
- Regras de ouro do treinamento

### Relatório de análise de treinos

- KPIs: km totais, kcal, FC média atual com delta, VO₂Max
- Gráfico de distância por sessão (azul = rua, cinza = esteira)
- Gráfico de FC com linha de tendência
- Barras de estimativa de tempo por zona de FC
- Cards de insights automáticos: tendência de FC, cadência, distribuição de zonas

> A conversão para PDF usa playwright/Chromium com `print_background: true`, preservando cores e gráficos. Requer conexão à internet para carregar o Chart.js.

---

## Fluxo completo

```bash
# 1. Baixar dados do Garmin
python baixar_tudo.py --dias 30

# 2. Gerar plano baseado nos dados reais
python main.py --auto --prova-nome "Maratona Monumental 2026" \
               --distancia 21 --semanas 17 \
               --data-inicio 2026-07-28 --data-prova 2026-11-22

# 3. Gerar relatórios HTML + PDF
python relatorio_html.py treinos
python relatorio_html.py plano
```
