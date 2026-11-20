# Como contribuir com o Jusante

Obrigado pelo interesse! O Jusante é construído por quem vive os problemas do saneamento em municípios pequenos. Você não precisa programar para ajudar.

## Formas de contribuir

| Você é... | Pode ajudar com... |
| --- | --- |
| Técnico ou engenheiro de SAAE | Relatar como o trabalho funciona de verdade, revisar fluxos, validar cálculos e termos técnicos, testar em campo |
| Gestor público | Dizer quais informações faltam para decidir, testar o painel |
| Desenvolvedor(a) | Código, testes, revisão de Pull Requests |
| Qualquer pessoa | Documentação, tradução de termos, correção de textos, sugestões |

## Antes de começar

1. Procure nas [issues](https://github.com/jusante-org/jusante/issues) se o assunto já está sendo discutido.
2. Para mudanças grandes, abra uma issue primeiro e descreva a proposta. Isso evita trabalho perdido.
3. Issues marcadas com `boa primeira issue` são um bom ponto de partida.

## Passo a passo para propor uma mudança

1. Faça um **fork** do repositório.
2. Crie um branch com nome descritivo: `feat/fila-de-reposicao`, `fix/foto-sem-coordenada`, `docs/glossario`.
3. Faça as alterações com commits pequenos e mensagens claras, em português.
4. Garanta que os testes passam.
5. Abra um **Pull Request** para o branch `main`, explicando o quê e por quê. Relacione a issue (`Resolve #12`).
6. Um mantenedor vai revisar. Pode haver pedidos de ajuste — faz parte.

## Regras de qualidade

- **Cálculos de engenharia** (hidráulica, perdas, dimensionamento) precisam de testes com casos de referência e revisão de um engenheiro.
- **Dados pessoais** de moradores seguem a LGPD: colete só o necessário.
- **Funcionar sem internet** é requisito do app de campo, não detalhe.
- Código, comentários, mensagens e documentação em **português**. Nomes técnicos de bibliotecas e padrões podem ficar em inglês.

## Padrão de commits

Usamos o formato `tipo: descrição curta`:

- `feat:` nova funcionalidade
- `fix:` correção de erro
- `docs:` documentação
- `test:` testes
- `refactor:` mudança de código sem alterar comportamento
- `chore:` manutenção, configuração, dependências

## Licença das contribuições

Ao contribuir, você concorda que sua contribuição seja distribuída sob a [AGPL-3.0](LICENSE) (código) e CC BY 4.0 (documentação). O uso de DCO (assinatura de commits) ou de acordo de contribuição (CLA) ainda está em discussão e será definido em [GOVERNANCE.md](GOVERNANCE.md).

## Dúvidas

Abra uma issue com a etiqueta `dúvida`. Não existe pergunta boba.
