# Wolff Security Scan GAN

Ferramenta de detecção de vulnerabilidades de SQL Injection em APIs REST utilizando payloads gerados por uma GAN baseada em LSTM.

A ferramenta analisa a especificação Swagger/OpenAPI da API alvo, gera payloads de SQL Injection contextualizados para cada endpoint e parâmetro, executa os ataques e classifica os resultados automaticamente.

## Integração com CI/CD

### Uso como GitHub Action

Adicione ao workflow do seu repositório:

```yaml
- name: Wolff Security Scan GAN
  id: wolff-report
  uses: pedroulissespu/wolff-security-scan@v1.0.1
  with:
    swagger-url: "docs/swagger.yaml"       # Caminho local ou URL do Swagger
    base-url: "http://localhost:8000"       # URL da API alvo
    num-payloads: "200"                     # Payloads por endpoint (padrão: 200)
    temperature: "0.7"                      # Variação dos payloads (padrão: 0.7)
    report-path: "reports/scan_report.json" # Caminho do relatório
    auth-token: ${{ secrets.API_TOKEN }}    # Token de autenticação (opcional)
    fail-on-vuln: "true"                   # Falhar pipeline se vulnerável (padrão: true)
```

#### Inputs

| Input | Obrigatório | Padrão | Descrição |
|-------|-------------|--------|-----------|
| `swagger-url` | Sim | — | URL ou caminho do arquivo Swagger/OpenAPI |
| `base-url` | Sim | — | URL base da API alvo |
| `num-payloads` | Não | `200` | Número de payloads por endpoint |
| `temperature` | Não | `0.7` | Temperatura da geração (0.1 a 1.0) |
| `report-path` | Não | `reports/scan_report.json` | Caminho do relatório |
| `auth-token` | Não | — | Token de autenticação (ex: `Bearer abc123`) |
| `fail-on-vuln` | Não | `true` | Falhar o pipeline se vulnerabilidades forem detectadas |
| `python-version` | Não | `3.11` | Versão do Python |

#### Outputs

| Output | Descrição |
|--------|-----------|
| `vulnerable` | `true` / `false` |
| `total-attacks` | Total de payloads enviados |
| `true-positives` | Número de verdadeiros positivos |
| `precision` | VP / (VP + FP) |
| `efficacy` | VP / total de ataques |
| `execution-time` | Tempo em segundos |
| `report-path` | Caminho do relatório gerado |

### Integração automática

Quando executado em ambiente GitHub Actions (variável `GITHUB_OUTPUT` presente), o comando `scan` exporta automaticamente as seguintes outputs:

- `vulnerable` — `true` / `false`
- `total-attacks`
- `true-positives`
- `precision`
- `efficacy`
- `execution-time`
- `report-path`

O processo retorna código de saída `1` se vulnerabilidades forem encontradas, permitindo falhar o pipeline automaticamente.

---

> A sessão a seguir é para aqueles que pretendem rodar localmente e/ou possuem interesse em contribuir com o treinamento ou até mesmo encontrar e realizar melhorias na ferramenta, sinta-se a vontade.

## Requisitos

- Python 3.10+
- CUDA (opcional, recomendado para treinamento)

## Instalação

```bash
pip install -r requirements.txt
```

Dependências principais:
- `torch` >= 2.0.0
- `numpy` >= 1.24.0
- `pandas` >= 2.0.0
- `requests` >= 2.31.0
- `pyyaml` >= 6.0
- `colorama` >= 0.4.6

## Uso

A ferramenta possui dois comandos: `train` e `scan`.

```bash
python main.py <comando> [opções]
```

---

### `train` — Treinar o modelo GAN

Treina a GAN nos datasets de SQL Injection disponíveis no diretório `datasets/`.

```bash
python main.py train [opções]
```

#### Parâmetros

| Parâmetro | Padrão | Descrição |
|-----------|--------|-----------|
| `--datasets-dir` | `datasets` | Diretório contendo os datasets CSV/TXT |
| `--output-dir` | `models` | Diretório para salvar o modelo treinado |
| `--epochs` | `500` | Número de épocas de treinamento |
| `--batch-size` | `256` | Tamanho do batch |
| `--resume` | — | Caminho de um checkpoint para continuar o treinamento |
| `--train-ratio` | `0.7` | Proporção do conjunto de treino |
| `--val-ratio` | `0.15` | Proporção do conjunto de validação |
| `--test-ratio` | `0.15` | Proporção do conjunto de teste |
| `--split-seed` | `42` | Semente aleatória da divisão treino/validação/teste |
| `--validation-max-batches` | `8` | Máximo de batches usados na validação por época |
| `--test-max-batches` | — | Máximo de batches usados no teste final |

#### Exemplos

```bash
# Treinar com configuração padrão
python main.py train

# Treinar com parâmetros customizados
python main.py train --epochs 300 --batch-size 128

# Continuar treinamento a partir de um checkpoint
python main.py train --resume models/checkpoint_epoch_200.pt
```

#### Configuração interna do modelo

| Parâmetro | Valor |
|-----------|-------|
| `embed_dim` | 128 |
| `hidden_dim` | 512 |
| `num_layers` | 3 |
| `max_len` | 256 |
| `lr_gen` | 1e-4 |
| `lr_disc` | 3e-4 |
| `teacher_forcing_ratio` | 0.5 |

Checkpoints são salvos automaticamente a cada 50 épocas em `<output-dir>/checkpoint_epoch_<N>.pt`. O modelo final é salvo como `<output-dir>/gan_sqli.pt`.

---

### `scan` — Executar scan de vulnerabilidades

Escaneia uma API REST usando payloads gerados pela GAN treinada.

```bash
python main.py scan --swagger <caminho> [opções]
```

#### Parâmetros

| Parâmetro | Padrão | Descrição |
|-----------|--------|-----------|
| `--swagger` | **(obrigatório)** | Caminho do arquivo Swagger/OpenAPI (YAML ou JSON) |
| `--base-url` | extraído do Swagger | URL base da API (sobrescreve o valor do Swagger) |
| `--model-path` | `models/gan_sqli.pt` | Caminho do modelo GAN treinado |
| `--num-payloads` | `200` | Número de payloads a gerar por endpoint |
| `--temperature` | `0.7` | Temperatura da geração (maior = mais variação) |
| `--output` | `reports/scan_report.json` | Caminho do relatório JSON de saída |
| `--auth-token` | — | Token de autenticação (ex: `Token abc123` ou `Bearer xyz`) |

#### Exemplos

```bash
# Scan básico
python main.py scan --swagger docs/api-swagger.yaml

# Scan com autenticação e URL customizada
python main.py scan \
  --swagger docs/api-swagger.yaml \
  --base-url http://localhost:8000/api \
  --auth-token "Token meu_token_aqui"

# Scan com mais payloads e maior variação
python main.py scan \
  --swagger docs/api-swagger.yaml \
  --num-payloads 500 \
  --temperature 0.9

# Scan usando modelo específico
python main.py scan \
  --swagger docs/api-swagger.yaml \
  --model-path models/checkpoint_epoch_300.pt
```

---

## Pipeline de Execução

```
1. Swagger/OpenAPI  →  Parser extrai endpoints e parâmetros
2. GAN treinada     →  Gera payloads SQLi contextualizados por tipo de parâmetro
3. Attacker         →  Injeta payloads via path, query, body e headers
4. Analyzer         →  Classifica respostas (VP, FP, FALHA, ERRO)
5. Report           →  Gera relatório JSON com métricas
```

### Classificação de resultados

| Sigla | Significado | Descrição |
|-------|-------------|-----------|
| VP | Verdadeiro Positivo | Vulnerabilidade de SQLi detectada (erros de DB, vazamento de dados, stack traces) |
| FP | Falso Positivo | Resposta suspeita, mas sem indicadores concretos |
| FALHA | Falha | O servidor rejeitou o payload (sem vulnerabilidade) |
| ERRO | Erro | Erro de conexão ou timeout |

### Métricas do relatório

- **precision** — VP / (VP + FP)
- **efficacy** — VP / total de ataques
- **total_attacks** — total de payloads enviados
- **true_positives** / **false_positives** / **failures** / **errors**
- **execution_time_seconds**

---

## Datasets

O diretório `datasets/` deve conter arquivos CSV com payloads de SQL Injection. Formatos suportados:

| Arquivo | Formato |
|---------|---------|
| `*_payload_full.csv` | Colunas: `payload`, `attack_type` (`sqli` / `norm`) |
| `SQLI_Dataset.csv` | Colunas: `Query`, `Label` (`1` = malicioso) |
| `sqli-extended.csv` | Colunas: `Query`, `Label` |
| `*.txt` | Um payload por linha (todos tratados como maliciosos) |

---

## Estrutura do Projeto

```
Wolff Security Scan GAN/
├── main.py                  # CLI principal (train / scan)
├── requirements.txt         # Dependências Python
├── datasets/                # Datasets de SQL Injection
├── models/                  # Modelos treinados e checkpoints
├── reports/                 # Relatórios de scan gerados
└── scanner/
    ├── __init__.py
    ├── analyzer.py          # Classificação de respostas HTTP
    ├── attacker.py          # Execução dos ataques nos endpoints
    ├── payloads.py          # Carregamento e geração de payloads
    ├── report.py            # Geração de relatórios JSON
    ├── swagger_parser.py    # Parser de Swagger/OpenAPI
    └── gan/
        ├── __init__.py
        ├── models.py        # Arquiteturas Generator e Discriminator (LSTM)
        ├── preprocessing.py # Limpeza e encoding dos datasets
        ├── train.py         # Loop de treinamento da GAN
        └── generate.py      # Geração de payloads com o Generator treinado
```

---

> Caso queira entrar em contato para falar sobre algo relacionado à ferramenta ou outros assuntos, sinta-se a vontade em me chamar nos seguintes e-mails:\
**E-mail pessoal**: ```pedro.ulisses2011@gmail.com```\
**E-mail profissional**: ```pedro.maia@maplink.global```
