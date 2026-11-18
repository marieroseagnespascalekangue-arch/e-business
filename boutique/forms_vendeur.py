from django import forms

from .models import ProduitArtisanal


class ProduitForm(forms.ModelForm):
    class Meta:
        model = ProduitArtisanal
        fields = ['categorie', 'nom', 'modele', 'couleur', 'description',
                  'prix', 'stock', 'photo', 'actif']
        labels = {
            'categorie': 'Catégorie',
            'nom': 'Nom du produit',
            'modele': 'Modèle (regroupe les couleurs)',
            'description': 'Description',
            'prix': 'Prix en FCFA (hors TVA)',
            'stock': 'Quantité en stock',
            'photo': 'Photo',
            'actif': 'Visible dans la boutique',
        }
        help_texts = {
            'modele': "Même texte pour toutes les couleurs d'un article (ex : Robe Wax). Laissez vide si une seule couleur.",
            'prix': 'La TVA de 19,25 % est ajoutée automatiquement.',
        }
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4}),
            'photo': forms.FileInput(attrs={'accept': 'image/*'}),
        }

    def clean_prix(self):
        prix = self.cleaned_data['prix']
        if prix <= 0:
            raise forms.ValidationError('Le prix doit être supérieur à 0.')
        return prix

    def clean_photo(self):
        photo = self.cleaned_data.get('photo')
        # Limite la taille des nouvelles photos envoyées (5 Mo)
        if photo and hasattr(photo, 'content_type') and photo.size > 5 * 1024 * 1024:
            raise forms.ValidationError('Photo trop lourde (5 Mo maximum).')
        return photo