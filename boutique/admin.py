from django.contrib import admin

from .models import Categorie, Client, Commande, LigneCommande, ProduitArtisanal, Vendeur


@admin.register(Categorie)
class CategorieAdmin(admin.ModelAdmin):
    list_display = ('nom',)


@admin.register(Vendeur)
class VendeurAdmin(admin.ModelAdmin):
    list_display = ('nom_boutique', 'ville', 'telephone')


@admin.register(ProduitArtisanal)
class ProduitAdmin(admin.ModelAdmin):
    # Bouton « Enregistrer en tant que nouveau » : permet de créer
    # une autre couleur en copiant un produit existant.
    save_as = True
    list_display = ('nom', 'couleur', 'modele', 'categorie', 'vendeur', 'prix', 'stock', 'actif')
    list_filter = ('actif', 'categorie', 'vendeur')
    search_fields = ('nom', 'modele')


class LigneInline(admin.TabularInline):
    model = LigneCommande
    extra = 0
    fields = ('produit', 'nom', 'prix_unitaire', 'quantite', 'statut_livraison', 'note_livraison')
    readonly_fields = ('produit', 'nom', 'prix_unitaire', 'quantite')


@admin.register(Commande)
class CommandeAdmin(admin.ModelAdmin):
    list_display = ('id', 'nom_client', 'telephone', 'ville', 'total', 'statut', 'cree_le')
    list_filter = ('statut',)
    inlines = [LigneInline]


@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = ('user', 'telephone', 'ville')