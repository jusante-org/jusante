# Jusante

**Plataforma open source, com inteligência artificial, para a gestão dos serviços de água e esgoto de municípios brasileiros de até 100 mil habitantes.**

Jusante é o lado da rede onde a água chega — onde estão as pessoas atendidas. O projeto olha para esse ponto: o município pequeno, o técnico do SAAE, o morador.

> **Status:** fase de fundação. Ainda não há versão utilizável. Acompanhe o [roadmap](#roadmap) e as [issues](https://github.com/jusante-org/jusante/issues).

## Por que existe

Municípios pequenos operam água e esgoto com pouca gente, pouco orçamento e pouca informação organizada:

- ordens de serviço no papel, no WhatsApp ou em ERPs difíceis de usar;
- redes sem cadastro ou com cadastro desatualizado;
- reposição de pavimento esquecida depois do reparo;
- sem fotos, sem registro de peças usadas, sem histórico;
- indicadores montados à mão para o SINISA.

O Jusante quer dar a qualquer município, sem custo de licença, as ferramentas que hoje só os grandes operadores têm.

## O que vem primeiro (MVP)

**Ordens de Serviço com mapa**, do pedido do morador até a reposição do pavimento:

- abertura de OS por endereço ou clique no mapa;
- triagem e programação das equipes;
- app de campo que funciona **sem internet**, com foto de antes e depois, peças usadas e dados de cadastro da rede;
- reposição de pavimento vinculada: a OS só se encerra quando a reposição é concluída;
- painel do gestor com atrasos, reposições pendentes e mapa de ocorrências.

Detalhes em [`docs/mvp-ordens-de-servico.md`](docs/mvp-ordens-de-servico.md).

## Arquitetura

Um núcleo comum (usuários, base geográfica, arquivos, auditoria) com módulos independentes — Serviços (OS), Cadastro, Hidráulica, Documentos e Indicadores — e uma camada de IA que consulta todos eles. Os dados entram e saem em formatos abertos (GeoPackage, EPANET `.inp`, CSV, padrões do SINISA).

| Camada | Tecnologia |
| --- | --- |
| Banco de dados | PostgreSQL + PostGIS |
| Backend / API | Python, Django (GeoDjango) |
| Painel web | React + TypeScript, MapLibre |
| App de campo | React Native (Expo), SQLite local, offline |
| Mapas offline | OpenStreetMap em PMTiles |
| Arquivos e fotos | MinIO (compatível com S3) |
| Instalação | Docker Compose |

## Estrutura do repositório

```
backend/   API e regras de negócio (Django)
web/       Painel web (React)
campo/     App de campo (React Native / Expo)
infra/     Docker Compose e configurações de implantação
docs/      Documentação do projeto
```

## Roadmap

1. **Fundação** — organização, licença, governança, stack, município piloto ← *estamos aqui*
2. **MVP** — núcleo comum + Ordens de Serviço com mapa
3. **Piloto** — uso real em um ou dois municípios
4. **Expansão** — cadastro, hidráulica, documentos, indicadores e IA

## Como contribuir

Engenheiros, técnicos de SAAE, gestores e desenvolvedores são bem-vindos — nem toda contribuição é código. Leia o [guia de contribuição](CONTRIBUTING.md) e o [código de conduta](CODE_OF_CONDUCT.md).

## Governança

O Jusante é mantido pela **Pazzi Soluções LTDA**, com liderança técnica do fundador do projeto. Veja [GOVERNANCE.md](GOVERNANCE.md).

## Licença

Código sob [GNU AGPL-3.0](LICENSE). Documentação sob [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/deed.pt_BR). O nome e o logo "Jusante" não são cobertos por essas licenças.
