from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User

from .forms import normaliser_numero
from .models import Client


class InscriptionForm(UserCreationForm):
    nom_complet = forms.CharField(label='Nom complet', max_length=150)
    telephone = forms.CharField(
        label='Téléphone (Mobile Money)',
        widget=forms.TextInput(attrs={'inputmode': 'tel', 'autocomplete': 'tel'}),
    )
    field_order = ['username', 'nom_complet', 'telephone', 'password1', 'password2']

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ('username',)

    def clean_telephone(self):
        return normaliser_numero(self.cleaned_data['telephone'])

    def save(self, commit=True):
        user = super().save(commit=False)
        user.first_name = self.cleaned_data['nom_complet']
        user.save()
        Client.objects.create(user=user, telephone=self.cleaned_data['telephone'])
        return user


class ProfilForm(forms.ModelForm):
    class Meta:
        model = Client
        fields = ['telephone', 'ville', 'adresse']
        labels = {'telephone': 'Téléphone', 'ville': 'Ville',
                  'adresse': 'Adresse / quartier de livraison'}
        widgets = {
            'telephone': forms.TextInput(attrs={'inputmode': 'tel'}),
            'adresse': forms.Textarea(attrs={'rows': 3}),
        }

    def clean_telephone(self):
        valeur = self.cleaned_data['telephone']
        return normaliser_numero(valeur) if valeur else valeur