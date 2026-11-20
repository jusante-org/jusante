"""Ciclo de vida da Ordem de Serviço.

Esta é a ÚNICA forma de mudar o status de uma OS. Cada função:
  1. confere se a transição é permitida a partir do status atual;
  2. confere se o usuário tem o perfil necessário e é do mesmo município;
  3. confere os dados obrigatórios (ex.: fotos de antes e depois);
  4. aplica a mudança e registra um EventoOS.

Fluxo (docs/mvp-ordens-de-servico.md):

  Aberta → Triada → Programada → Em execução → Executada → Encerrada
                                       ↑              │
                                       └─ devolvida ──┤
                                                      └→ Aguardando reposição → Encerrada
  Aberta/Triada → Cancelada                                (quando a OS filha de reposição é encerrada)
"""
from __future__ import annotations

from decimal import Decimal

from django.contrib.gis.geos import Point
from django.db import transaction
from django.utils import timezone

from nucleo.models import Equipe, Perfil, Usuario

from .models import (
    EventoOS,
    MomentoFoto,
    OrdemServico,
    Prioridade,
    Solicitante,
    Status,
    TipoOS,
    TipoPavimento,
)


class ErroFluxo(Exception):
    """Erro de regra de negócio do fluxo da OS. A mensagem é exibível ao usuário."""


class TransicaoInvalida(ErroFluxo):
    pass


class PermissaoNegada(ErroFluxo):
    pass


class DadosIncompletos(ErroFluxo):
    pass


class ConfiguracaoIncompleta(ErroFluxo):
    pass


# --------------------------------------------------------------------------- utilitários

def _exigir_perfil(usuario: Usuario, *perfis: str) -> None:
    if not usuario.tem_perfil(*perfis):
        nomes = ", ".join(Perfil(p).label for p in perfis)
        raise PermissaoNegada(f"Ação permitida apenas para: {nomes}.")


def _exigir_municipio(usuario: Usuario, municipio) -> None:
    if usuario.is_superuser:
        return
    if usuario.municipio_id != municipio.pk:
        raise PermissaoNegada("Usuário não pertence ao município desta OS.")


def _exigir_status(os_: OrdemServico, *permitidos: str, acao: str) -> None:
    if os_.status not in permitidos:
        atual = Status(os_.status).label
        raise TransicaoInvalida(f"Não é possível {acao}: a OS está '{atual}'.")


def _travar(os_: OrdemServico) -> OrdemServico:
    """Recarrega a OS com trava de linha para evitar duas mudanças simultâneas."""
    return OrdemServico.objects.select_for_update().get(pk=os_.pk)


def _mudar_status(os_: OrdemServico, usuario: Usuario, novo: str, acao: str, observacao: str = "",
                  campos_extras: tuple[str, ...] = ()) -> None:
    anterior = os_.status
    os_.status = novo
    os_.save(update_fields=["status", *campos_extras])
    EventoOS.objects.create(
        os=os_, usuario=usuario, acao=acao,
        status_anterior=anterior, status_novo=novo, observacao=observacao,
    )


# --------------------------------------------------------------------------- abertura

@transaction.atomic
def abrir_os(
    usuario: Usuario,
    *,
    tipo: TipoOS,
    endereco: str,
    descricao: str,
    ponto_informado: Point | None = None,
    referencia: str = "",
    solicitante: Solicitante | None = None,
    prioridade: str | None = None,
) -> OrdemServico:
    _exigir_perfil(usuario, Perfil.ATENDENTE, Perfil.ENCARREGADO)
    _exigir_municipio(usuario, tipo.municipio)
    if not endereco.strip() or not descricao.strip():
        raise DadosIncompletos("Informe o endereço e a descrição do pedido.")
    if solicitante and solicitante.municipio_id != tipo.municipio_id:
        raise DadosIncompletos("Solicitante de outro município.")

    os_ = OrdemServico.objects.create(
        municipio=tipo.municipio,
        tipo=tipo,
        prioridade=prioridade or tipo.prioridade_padrao,
        solicitante=solicitante,
        endereco=endereco.strip(),
        referencia=referencia.strip(),
        descricao=descricao.strip(),
        ponto_informado=ponto_informado,
        aberta_por=usuario,
    )
    EventoOS.objects.create(os=os_, usuario=usuario, acao="abertura", status_novo=Status.ABERTA)
    return os_


# --------------------------------------------------------------------------- triagem e programação

@transaction.atomic
def triar(os_: OrdemServico, usuario: Usuario, *, equipe: Equipe, prioridade: str | None = None) -> OrdemServico:
    os_ = _travar(os_)
    _exigir_perfil(usuario, Perfil.ENCARREGADO)
    _exigir_municipio(usuario, os_.municipio)
    _exigir_status(os_, Status.ABERTA, acao="triar")
    if equipe.municipio_id != os_.municipio_id:
        raise DadosIncompletos("Equipe de outro município.")
    if prioridade is not None:
        if prioridade not in Prioridade.values:
            raise DadosIncompletos("Prioridade inválida.")
        os_.prioridade = prioridade
    os_.equipe = equipe
    os_.triada_em = timezone.now()
    _mudar_status(os_, usuario, Status.TRIADA, "triagem",
                  observacao=f"Equipe: {equipe} · Prioridade: {Prioridade(os_.prioridade).label}",
                  campos_extras=("equipe", "prioridade", "triada_em"))
    return os_


@transaction.atomic
def programar(os_: OrdemServico, usuario: Usuario, *, data) -> OrdemServico:
    os_ = _travar(os_)
    _exigir_perfil(usuario, Perfil.ENCARREGADO)
    _exigir_municipio(usuario, os_.municipio)
    _exigir_status(os_, Status.TRIADA, Status.PROGRAMADA, acao="programar")
    os_.data_programada = data
    os_.programada_em = timezone.now()
    acao = "reprogramação" if os_.status == Status.PROGRAMADA else "programação"
    _mudar_status(os_, usuario, Status.PROGRAMADA, acao, observacao=f"Data: {data:%d/%m/%Y}",
                  campos_extras=("data_programada", "programada_em"))
    return os_


# --------------------------------------------------------------------------- execução em campo

@transaction.atomic
def iniciar(os_: OrdemServico, usuario: Usuario) -> OrdemServico:
    os_ = _travar(os_)
    _exigir_perfil(usuario, Perfil.CAMPO, Perfil.ENCARREGADO)
    _exigir_municipio(usuario, os_.municipio)
    _exigir_status(os_, Status.PROGRAMADA, acao="iniciar a execução")
    if (not usuario.tem_perfil(Perfil.ENCARREGADO)
            and os_.equipe and not os_.equipe.membros.filter(pk=usuario.pk).exists()):
        raise PermissaoNegada("Esta OS está programada para outra equipe.")
    os_.iniciada_em = timezone.now()
    _mudar_status(os_, usuario, Status.EM_EXECUCAO, "início da execução", campos_extras=("iniciada_em",))
    return os_


@transaction.atomic
def concluir_execucao(
    os_: OrdemServico,
    usuario: Usuario,
    *,
    ponto_real: Point,
    encontrado: str,
    executado: str,
    precisa_reposicao: bool,
    reposicao_tipo: str = "",
    reposicao_area_m2: Decimal | None = None,
    observacao: str = "",
) -> OrdemServico:
    os_ = _travar(os_)
    _exigir_perfil(usuario, Perfil.CAMPO, Perfil.ENCARREGADO)
    _exigir_municipio(usuario, os_.municipio)
    _exigir_status(os_, Status.EM_EXECUCAO, acao="concluir a execução")

    faltando = []
    if ponto_real is None:
        faltando.append("local real do serviço")
    if not encontrado.strip():
        faltando.append("o que foi encontrado")
    if not executado.strip():
        faltando.append("o que foi feito")
    momentos = set(os_.fotos.values_list("momento", flat=True))
    if MomentoFoto.ANTES not in momentos:
        faltando.append("foto de antes")
    if MomentoFoto.DEPOIS not in momentos:
        faltando.append("foto de depois")
    if precisa_reposicao and reposicao_tipo not in TipoPavimento.values:
        faltando.append("tipo de pavimento a repor")
    if faltando:
        raise DadosIncompletos("Faltam: " + "; ".join(faltando) + ".")

    os_.ponto_real = ponto_real
    os_.encontrado = encontrado.strip()
    os_.executado = executado.strip()
    os_.observacao_campo = observacao.strip()
    os_.precisa_reposicao = precisa_reposicao
    os_.reposicao_tipo = reposicao_tipo if precisa_reposicao else ""
    os_.reposicao_area_m2 = reposicao_area_m2 if precisa_reposicao else None
    os_.executada_em = timezone.now()
    _mudar_status(
        os_, usuario, Status.EXECUTADA, "conclusão da execução", observacao=observacao,
        campos_extras=("ponto_real", "encontrado", "executado", "observacao_campo", "precisa_reposicao",
                       "reposicao_tipo", "reposicao_area_m2", "executada_em"),
    )
    return os_


# --------------------------------------------------------------------------- validação e encerramento

@transaction.atomic
def devolver(os_: OrdemServico, usuario: Usuario, *, motivo: str) -> OrdemServico:
    """O encarregado devolve a OS à equipe quando falta algo ou o serviço ficou mal feito."""
    os_ = _travar(os_)
    _exigir_perfil(usuario, Perfil.ENCARREGADO)
    _exigir_municipio(usuario, os_.municipio)
    _exigir_status(os_, Status.EXECUTADA, acao="devolver")
    if not motivo.strip():
        raise DadosIncompletos("Informe o motivo da devolução.")
    _mudar_status(os_, usuario, Status.PROGRAMADA, "devolução", observacao=motivo.strip())
    return os_


@transaction.atomic
def validar(os_: OrdemServico, usuario: Usuario, *, observacao: str = "") -> OrdemServico:
    """O encarregado confere o serviço executado.

    Sem reposição: a OS é encerrada.
    Com reposição: a OS fica 'Aguardando reposição' e uma OS filha de reposição é aberta.
    """
    os_ = _travar(os_)
    _exigir_perfil(usuario, Perfil.ENCARREGADO)
    _exigir_municipio(usuario, os_.municipio)
    _exigir_status(os_, Status.EXECUTADA, acao="validar")

    if os_.precisa_reposicao:
        _abrir_reposicao(os_, usuario)
        _mudar_status(os_, usuario, Status.AGUARDANDO_REPOSICAO, "validação", observacao=observacao)
        return os_

    os_.encerrada_em = timezone.now()
    _mudar_status(os_, usuario, Status.ENCERRADA, "encerramento", observacao=observacao,
                  campos_extras=("encerrada_em",))
    if os_.os_origem_id:
        _encerrar_origem_se_concluida(os_.os_origem, usuario)
    return os_


def _abrir_reposicao(origem: OrdemServico, usuario: Usuario) -> OrdemServico:
    tipo = TipoOS.objects.filter(municipio=origem.municipio, e_reposicao=True, ativo=True).first()
    if tipo is None:
        raise ConfiguracaoIncompleta(
            "Cadastre um tipo de OS marcado como 'tipo de reposição de pavimento' para este município."
        )
    area = f" — aprox. {origem.reposicao_area_m2} m²" if origem.reposicao_area_m2 else ""
    filha = OrdemServico.objects.create(
        municipio=origem.municipio,
        tipo=tipo,
        prioridade=Prioridade.NORMAL,
        endereco=origem.endereco,
        referencia=origem.referencia,
        descricao=(f"Reposição de {TipoPavimento(origem.reposicao_tipo).label.lower()}{area}. "
                   f"Origem: OS {origem.numero}."),
        ponto_informado=origem.ponto_real or origem.ponto_informado,
        os_origem=origem,
        aberta_por=usuario,
    )
    EventoOS.objects.create(os=filha, usuario=usuario, acao="abertura automática de reposição",
                            status_novo=Status.ABERTA, observacao=f"OS de origem: {origem.numero}")
    return filha


def _encerrar_origem_se_concluida(origem: OrdemServico, usuario: Usuario) -> None:
    origem = _travar(origem)
    if origem.status != Status.AGUARDANDO_REPOSICAO:
        return
    pendentes = origem.reposicoes.exclude(status__in=[Status.ENCERRADA, Status.CANCELADA])
    if pendentes.exists():
        return
    origem.encerrada_em = timezone.now()
    _mudar_status(origem, usuario, Status.ENCERRADA, "encerramento após reposição",
                  campos_extras=("encerrada_em",))


# --------------------------------------------------------------------------- cancelamento

@transaction.atomic
def cancelar(os_: OrdemServico, usuario: Usuario, *, justificativa: str) -> OrdemServico:
    os_ = _travar(os_)
    _exigir_perfil(usuario, Perfil.ATENDENTE, Perfil.ENCARREGADO)
    _exigir_municipio(usuario, os_.municipio)
    _exigir_status(os_, Status.ABERTA, Status.TRIADA, acao="cancelar")
    if not justificativa.strip():
        raise DadosIncompletos("Informe a justificativa do cancelamento.")
    os_.cancelada_em = timezone.now()
    _mudar_status(os_, usuario, Status.CANCELADA, "cancelamento", observacao=justificativa.strip(),
                  campos_extras=("cancelada_em",))
    return os_
