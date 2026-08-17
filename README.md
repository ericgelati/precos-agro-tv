# Painel de preços — Dólar, Soja e Milho (para TV do escritório)

Painel web que mostra, em telão, a cotação do dólar (USD/BRL) e dos futuros de
soja e milho da bolsa de Chicago (CBOT), atualizando sozinho o dia inteiro.

## Como funciona

- Um **GitHub Action** roda em segundo plano, a cada ~5 minutos, busca os
  preços atuais e grava em `data.json` dentro deste mesmo repositório.
- O **GitHub Pages** publica os arquivos (`index.html` + `data.json`) numa URL
  pública gratuita.
- A página `index.html` relê o `data.json` a cada 1 minuto e atualiza a tela
  sozinha — não precisa apertar F5.

> **Sobre a frequência:** você pediu atualização a cada 1 minuto. O
> agendamento gratuito do GitHub Actions não é confiável abaixo de ~5 minutos
> (o próprio GitHub pode atrasar execuções em horários de pico). Os dados em
> si são renovados a cada 5 minutos, e a tela verifica novidade a cada 1
> minuto — mas o GitHub Pages também tem um cache próprio (CDN) que, na
> prática, pode levar mais alguns minutos para refletir o `data.json` mais
> recente. No total, espere o preço na tela mudar com um atraso de
> aproximadamente 5–10 minutos em relação ao mercado, não em tempo real
> segundo a segundo.

> **Fonte dos dados:** Yahoo Finance (mesma base que alimenta finance.yahoo.com),
> símbolos `BRL=X` (dólar), `ZS=F` (soja CBOT) e `ZC=F` (milho CBOT). Não
> precisa de chave/cadastro. Se o Yahoo ficar fora do ar por um instante, o
> painel mantém o último preço válido e avisa que está desatualizado, em vez
> de mostrar erro.

## Passo 1 — Publicar no GitHub

1. Crie um repositório novo e **público** no GitHub (ex: `precos-agro-tv`).
   Público é importante: em repositórios privados o GitHub Actions gratuito
   tem cota limitada de minutos/mês, e rodar a cada 5 minutos estoura essa
   cota rapidamente. Como são só preços públicos, não há problema de
   privacidade em deixá-lo público.
2. Suba todos os arquivos desta pasta para o repositório (pela interface web
   do GitHub, arrastando os arquivos, ou via `git push` se preferir linha de
   comando).
3. Vá em **Settings → Pages** do repositório, em "Build and deployment"
   escolha **Deploy from a branch**, branch `main`, pasta `/ (root)`, e
   salve. Em alguns minutos o GitHub mostrará a URL pública, algo como:
   `https://SEU-USUARIO.github.io/precos-agro-tv/`
4. Vá em **Settings → Actions → General**, em "Workflow permissions" marque
   **Read and write permissions** e salve — é isso que permite o robô
   commitar o `data.json` atualizado automaticamente.
5. Vá na aba **Actions** do repositório, clique no workflow "Atualizar
   preços (dólar, soja, milho)" e depois em **Run workflow** para disparar a
   primeira atualização manualmente (não precisa esperar os 5 minutos). Depois
   disso ele passa a rodar sozinho no horário programado.

## Passo 2 — Configurar o PC/mini-PC ligado à TV

A ideia é o computador abrir o navegador direto na URL do painel, em tela
cheia, assim que ligar — sem ninguém precisar mexer.

**Google Chrome / Edge em modo kiosk (recomendado):**

Crie um atalho (ou script) que chama o navegador com a flag `--kiosk`:

```
chrome --kiosk --incognito "https://SEU-USUARIO.github.io/precos-agro-tv/"
```

- Windows: crie um atalho na pasta **Inicializar** (`shell:startup`) com o
  destino acima (ajustando o caminho do `chrome.exe`), para abrir sozinho ao
  ligar o PC.
- Sair do modo kiosk: `Alt+F4` (Windows) ou `Cmd+Q` (Mac).

Se preferir não usar kiosk mode, basta abrir a URL numa aba normal e
apertar **F11** para tela cheia.

## Personalizações fáceis

- **Cores / layout:** edite `index.html` (tudo em um arquivo só, CSS no
  topo).
- **Trocar a fonte dos dados:** edite `update_prices.py`.
- **Mudar o intervalo do robô:** edite o `cron` em
  `.github/workflows/update-prices.yml` (mínimo prático recomendado: 5
  minutos).
- **Preço em reais (CEPEA/ESALQ) em vez de futuro CBOT:** se depois quiser
  trocar para a referência do mercado físico brasileiro, é só avisar — a
  estrutura do painel já está pronta para isso, só muda a fonte de dados.

## Arquivos

| Arquivo | Função |
|---|---|
| `index.html` | O painel em si (o que aparece na TV) |
| `data.json` | Os preços mais recentes (gerado automaticamente) |
| `update_prices.py` | Script que busca os preços |
| `.github/workflows/update-prices.yml` | Agendamento automático (GitHub Actions) |
