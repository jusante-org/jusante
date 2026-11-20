from django import forms
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import Equipe, Municipio, Perfil, Usuario


@admin.register(Municipio)
class MunicipioAdmin(admin.ModelAdmin):
    list_display = ["nome", "uf", "codigo_ibge", "ativo"]
    list_filter = ["uf", "ativo"]
    search_fields = ["nome", "codigo_ibge"]


class UsuarioForm(forms.ModelForm):
    perfis = forms.MultipleChoiceField(
        choices=Perfil.choices, widget=forms.CheckboxSelectMultiple, required=False
    )

    class Meta:
        model = Usuario
        fields = "__all__"


@admin.register(Usuario)
class UsuarioAdmin(UserAdmin):
    form = UsuarioForm
    list_display = ["username", "first_name", "last_name", "municipio", "perfis", "is_active"]
    list_filter = ["municipio", "is_active"]
    fieldsets = UserAdmin.fieldsets + (
        ("Jusante", {"fields": ("municipio", "telefone", "perfis")}),
    )


@admin.register(Equipe)
class EquipeAdmin(admin.ModelAdmin):
    list_display = ["nome", "municipio", "especialidade", "ativa"]
    list_filter = ["municipio", "especialidade", "ativa"]
    filter_horizontal = ["membros"]
