from io import StringIO

from django.core.management import call_command
from django.test import TestCase

from nucleo.models import Municipio
from servicos.models import TipoOS


class CriarTiposPadraoTests(TestCase):
    def test_cria_tipos_uma_unica_vez(self):
        municipio = Municipio.objects.create(nome="Exemplópolis", uf="SP", codigo_ibge="3599999")
        call_command("criar_tipos_padrao", "3599999", stdout=StringIO())
        call_command("criar_tipos_padrao", "3599999", stdout=StringIO())
        self.assertEqual(TipoOS.objects.filter(municipio=municipio).count(), 10)
        self.assertEqual(TipoOS.objects.filter(municipio=municipio, e_reposicao=True).count(), 1)
