"""Testes do ciclo de vida da Ordem de Serviço (servicos.fluxo)."""
import datetime
from decimal import Decimal

from django.contrib.gis.geos import Point
from django.core.files.base import ContentFile
from django.test import TestCase, override_settings

from nucleo.models import Equipe, Municipio, Perfil, Usuario
from servicos import fluxo
from servicos.models import (
    EventoOS,
    Foto,
    MomentoFoto,
    OrdemServico,
    Prioridade,
    Sistema,
    Status,
    TipoOS,
    TipoPavimento,
)

PONTO = Point(-47.06, -22.90, srid=4326)


def _usuario(municipio, nome, *perfis):
    return Usuario.objects.create_user(username=nome, password="x", municipio=municipio, perfis=list(perfis))


@override_settings(MEDIA_ROOT="/tmp/jusante-testes-media")
class CicloDeVidaTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.municipio = Municipio.objects.create(nome="Exemplópolis", uf="SP", codigo_ibge="3599999")
        cls.outro_municipio = Municipio.objects.create(nome="Vizinha", uf="SP", codigo_ibge="3599998")
        cls.atendente = _usuario(cls.municipio, "atendente", Perfil.ATENDENTE)
        cls.encarregado = _usuario(cls.municipio, "encarregado", Perfil.ENCARREGADO)
        cls.campo = _usuario(cls.municipio, "campo", Perfil.CAMPO)
        cls.gestor = _usuario(cls.municipio, "gestor", Perfil.GESTOR)
        cls.equipe = Equipe.objects.create(municipio=cls.municipio, nome="Equipe Água 1")
        cls.equipe.membros.add(cls.campo)
        cls.tipo_vazamento = TipoOS.objects.create(
            municipio=cls.municipio, nome="Vazamento na rede", sistema=Sistema.AGUA,
            prioridade_padrao=Prioridade.ALTA, gera_reposicao=True,
        )
        cls.tipo_reposicao = TipoOS.objects.create(
            municipio=cls.municipio, nome="Reposição de pavimento", sistema=Sistema.APOIO, e_reposicao=True,
        )

    # ------------------------------------------------------------------ auxiliares

    def _abrir(self):
        return fluxo.abrir_os(
            self.atendente, tipo=self.tipo_vazamento, endereco="Rua das Flores, 100",
            descricao="Água minando na calçada", ponto_informado=PONTO,
        )

    def _fotos(self, os_):
        for momento in (MomentoFoto.ANTES, MomentoFoto.DEPOIS):
            Foto.objects.create(os=os_, momento=momento, enviada_por=self.campo,
                                arquivo=ContentFile(b"jpg", name=f"{momento}.jpg"))

    def _ate_em_execucao(self):
        os_ = self._abrir()
        fluxo.triar(os_, self.encarregado, equipe=self.equipe)
        fluxo.programar(os_, self.encarregado, data=datetime.date(2026, 11, 20))
        return fluxo.iniciar(os_, self.campo)

    def _concluir(self, os_, precisa_reposicao=False):
        return fluxo.concluir_execucao(
            os_, self.campo, ponto_real=PONTO, encontrado="Tubo rompido", executado="Troca de trecho",
            precisa_reposicao=precisa_reposicao,
            reposicao_tipo=TipoPavimento.ASFALTO if precisa_reposicao else "",
            reposicao_area_m2=Decimal("1.50") if precisa_reposicao else None,
        )

    # ------------------------------------------------------------------ abertura

    def test_abertura_numera_e_registra_evento(self):
        os_ = self._abrir()
        self.assertEqual(os_.status, Status.ABERTA)
        self.assertRegex(os_.numero, r"^\d{4}-000001$")
        self.assertEqual(os_.prioridade, Prioridade.ALTA)  # herdada do tipo
        self.assertEqual(os_.eventos.count(), 1)
        self.assertEqual(self._abrir().numero[-6:], "000002")

    def test_equipe_de_campo_nao_abre_os(self):
        with self.assertRaises(fluxo.PermissaoNegada):
            fluxo.abrir_os(self.campo, tipo=self.tipo_vazamento, endereco="Rua A", descricao="x")

    def test_usuario_de_outro_municipio_nao_abre_os(self):
        intruso = _usuario(self.outro_municipio, "intruso", Perfil.ATENDENTE)
        with self.assertRaises(fluxo.PermissaoNegada):
            fluxo.abrir_os(intruso, tipo=self.tipo_vazamento, endereco="Rua A", descricao="x")

    # ------------------------------------------------------------------ caminho sem reposição

    def test_caminho_completo_sem_reposicao(self):
        os_ = self._ate_em_execucao()
        self._fotos(os_)
        self._concluir(os_)
        fluxo.validar(os_, self.encarregado)
        os_.refresh_from_db()
        self.assertEqual(os_.status, Status.ENCERRADA)
        self.assertIsNotNone(os_.encerrada_em)
        acoes = list(os_.eventos.values_list("acao", flat=True))
        self.assertEqual(acoes, ["abertura", "triagem", "programação", "início da execução",
                                 "conclusão da execução", "encerramento"])

    # ------------------------------------------------------------------ fotos e dados obrigatórios

    def test_conclusao_sem_fotos_e_bloqueada(self):
        os_ = self._ate_em_execucao()
        with self.assertRaisesMessage(fluxo.DadosIncompletos, "foto de antes"):
            self._concluir(os_)
        os_.refresh_from_db()
        self.assertEqual(os_.status, Status.EM_EXECUCAO)

    def test_reposicao_exige_tipo_de_pavimento(self):
        os_ = self._ate_em_execucao()
        self._fotos(os_)
        with self.assertRaisesMessage(fluxo.DadosIncompletos, "tipo de pavimento"):
            fluxo.concluir_execucao(os_, self.campo, ponto_real=PONTO, encontrado="a", executado="b",
                                    precisa_reposicao=True)

    # ------------------------------------------------------------------ reposição

    def test_os_so_encerra_apos_reposicao(self):
        origem = self._ate_em_execucao()
        self._fotos(origem)
        self._concluir(origem, precisa_reposicao=True)
        fluxo.validar(origem, self.encarregado)
        origem.refresh_from_db()
        self.assertEqual(origem.status, Status.AGUARDANDO_REPOSICAO)

        filha = origem.reposicoes.get()
        self.assertEqual(filha.tipo, self.tipo_reposicao)
        self.assertEqual(filha.status, Status.ABERTA)
        self.assertIn(origem.numero, filha.descricao)

        # Reposição percorre o próprio fluxo
        fluxo.triar(filha, self.encarregado, equipe=self.equipe)
        fluxo.programar(filha, self.encarregado, data=datetime.date(2026, 11, 22))
        fluxo.iniciar(filha, self.campo)
        self._fotos(filha)
        self._concluir(filha)
        fluxo.validar(filha, self.encarregado)

        origem.refresh_from_db()
        self.assertEqual(origem.status, Status.ENCERRADA)
        self.assertTrue(origem.eventos.filter(acao="encerramento após reposição").exists())

    def test_reposicao_sem_tipo_configurado(self):
        self.tipo_reposicao.delete()
        os_ = self._ate_em_execucao()
        self._fotos(os_)
        self._concluir(os_, precisa_reposicao=True)
        with self.assertRaises(fluxo.ConfiguracaoIncompleta):
            fluxo.validar(os_, self.encarregado)
        os_.refresh_from_db()
        self.assertEqual(os_.status, Status.EXECUTADA)

    # ------------------------------------------------------------------ devolução, cancelamento, regras

    def test_devolucao_volta_para_programada(self):
        os_ = self._ate_em_execucao()
        self._fotos(os_)
        self._concluir(os_)
        fluxo.devolver(os_, self.encarregado, motivo="Foto de depois não mostra o reparo")
        os_.refresh_from_db()
        self.assertEqual(os_.status, Status.PROGRAMADA)

    def test_cancelamento_exige_justificativa_e_so_antes_de_programar(self):
        os_ = self._abrir()
        with self.assertRaises(fluxo.DadosIncompletos):
            fluxo.cancelar(os_, self.atendente, justificativa=" ")
        fluxo.cancelar(os_, self.atendente, justificativa="Duplicada da OS anterior")
        os_.refresh_from_db()
        self.assertEqual(os_.status, Status.CANCELADA)

        os2 = self._ate_em_execucao()
        with self.assertRaises(fluxo.TransicaoInvalida):
            fluxo.cancelar(os2, self.encarregado, justificativa="Tarde demais")

    def test_campo_de_outra_equipe_nao_inicia(self):
        os_ = self._abrir()
        fluxo.triar(os_, self.encarregado, equipe=self.equipe)
        fluxo.programar(os_, self.encarregado, data=datetime.date(2026, 11, 20))
        outro = _usuario(self.municipio, "outro_campo", Perfil.CAMPO)
        with self.assertRaises(fluxo.PermissaoNegada):
            fluxo.iniciar(os_, outro)

    def test_gestor_nao_altera_os(self):
        os_ = self._abrir()
        with self.assertRaises(fluxo.PermissaoNegada):
            fluxo.triar(os_, self.gestor, equipe=self.equipe)

    def test_transicao_fora_de_ordem(self):
        os_ = self._abrir()
        with self.assertRaises(fluxo.TransicaoInvalida):
            fluxo.iniciar(os_, self.campo)

    def test_eventos_sao_imutaveis(self):
        evento = self._abrir().eventos.first()
        evento.observacao = "adulterado"
        with self.assertRaises(ValueError):
            evento.save()
        with self.assertRaises(ValueError):
            evento.delete()
        self.assertEqual(EventoOS.objects.count(), 1)

    def test_status_nao_muda_por_fora_do_fluxo_no_admin(self):
        self.assertFalse(OrdemServico._meta.get_field("status").editable)
