# Documento de fundação

> Versão de 19/11/2026. Resumo das decisões que deram origem ao projeto.

## Visão

Plataforma open source, com inteligência artificial, para a gestão dos serviços de água e esgoto de municípios brasileiros de até 100 mil habitantes. Dar a qualquer município pequeno, sem custo de licença, cadastro de redes confiável, ordens de serviço organizadas, cálculo hidráulico acessível, documentos encontráveis e indicadores para decidir.

## Princípios

1. **Simples antes de completo.** Se um técnico não aprende a usar em uma tarde, está complexo demais.
2. **Código próprio, padrões abertos.** Dados entram e saem em GeoPackage, PostGIS, EPANET `.inp` e CSV, seguindo as definições do SINISA.
3. **Os dados são do município.** Exportação completa, hospedagem local possível, respeito à LGPD.
4. **Feito para a realidade brasileira.** Português, normas ABNT, internet instável, computadores modestos.
5. **Modular.** O município adota um módulo por vez.
6. **IA como assistente, não como autoridade.** Cálculos são determinísticos e verificáveis; decisões são de pessoas.
7. **Engenharia validada.** Todo cálculo tem testes com casos de referência e revisão de engenheiro.

## Público

| Perfil | Necessidade |
| --- | --- |
| Gestor (diretor do SAAE, secretário, prefeito) | Saber o que acontece e onde investir |
| Engenheiro / técnico | Cadastro confiável, cálculos, projetos |
| Equipe de campo | Receber e fechar serviços sem burocracia |
| Atendimento | Registrar reclamações e acompanhar |
| Cidadão (futuro) | Avisar problemas e acompanhar |

## Papel da IA

Assistente do gestor, organização documental, apoio à digitalização do cadastro, triagem de OS, análise de perdas e rascunho de relatórios. Toda resposta mostra a origem dos dados; o provedor de modelo é substituível, inclusive por modelos locais.

## Decisões tomadas

| Tema | Decisão |
| --- | --- |
| Licença | AGPL-3.0 (código), CC BY 4.0 (documentação) |
| Governança | Líder fundador; Pazzi Soluções LTDA como mantenedora oficial |
| Primeiro módulo (MVP) | Ordens de Serviço com mapa |
| Stack | PostgreSQL/PostGIS, Django (GeoDjango), React + MapLibre, React Native (Expo) offline, PMTiles, MinIO, Docker Compose |

## Sustentabilidade

Software gratuito. A sustentação vem de serviços (implantação, migração de cadastro, hospedagem gerenciada, suporte), fomento (editais, BNDES, FINEP, universidades) e consórcios intermunicipais.

## Decisões em aberto

- [ ] Organização no GitHub: manter no nome do fundador ou transferir para a Pazzi
- [ ] DCO ou CLA para contribuições
- [ ] Registro da marca no INPI e domínios
- [ ] Município(s) piloto
- [ ] Revisão jurídica de licença, marca e relação com a Pazzi
