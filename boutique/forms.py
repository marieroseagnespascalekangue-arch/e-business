import re

from django import forms

from .models import Commande


def normaliser_numero(valeur):
    """Accepte 6XXXXXXXX, +237 6XX XX XX XX, etc. Renvoie 9 chiffres."""
    chiffres = re.sub(r'\D', '', valeur)
    if chiffres.startswith('237') and len(chiffres) == 12:
        chiffres = chiffres[3:]
    if not re.fullmatch(r'6\d{8}', chiffres):
        raise forms.ValidationError('Numéro invalide (exemple : 677 12 34 56).')
    return chiffres


class CommandeForm(forms.ModelForm):
    class Meta:
        model = Commande
        fields = ['nom_client', 'telephone', 'ville', 'adresse']
        labels = {
            'nom_client': 'Nom complet',
            'telephone': 'Téléphone',
            'ville': 'Ville',
            'adresse': 'Adresse / quartier de livraison',
        }
        widgets = {
            'telephone': forms.TextInput(attrs={'inputmode': 'tel', 'autocomplete': 'tel'}),
            'adresse': forms.Textarea(attrs={'rows': 3}),
        }

    def clean_telephone(self):
        return normaliser_numero(self.cleaned_data['telephone'])


class PaiementForm(forms.Form):
    operateur = forms.ChoiceField(
        choices=Commande.OPERATEURS, widget=forms.RadioSelect, label='Opérateur'
    )
    numero = forms.CharField(
        label='Numéro Mobile Money',
        widget=forms.TextInput(attrs={'inputmode': 'tel'}),
    )

    def clean_numero(self):
        return normaliser_numero(self.cleaned_data['numero'])