from django.contrib.auth import views as auth_views
from django.urls import path

from . import views, views_client, views_vendeur

urlpatterns = [
    path('', views.catalogue, name='catalogue'),
    path('produit/<int:pk>/', views.detail_produit, name='produit'),
    path('boutique/<int:pk>/', views.boutique_vendeur, name='vendeur'),
    path('panier/', views.voir_panier, name='panier'),
    path('panier/ajouter/<int:pk>/', views.ajouter_panier, name='ajouter_panier'),
    path('panier/modifier/<int:pk>/', views.modifier_panier, name='modifier_panier'),
    path('panier/retirer/<int:pk>/', views.retirer_panier, name='retirer_panier'),
    path('commander/', views.commander, name='commander'),
    path('paiement/', views.paiement, name='paiement'),
    path('paiement/attente/', views.paiement_attente, name='paiement_attente'),
    path('confirmation/', views.confirmation, name='confirmation'),

    # Compte client
    path('compte/', views_client.mon_compte, name='mon_compte'),
    path('compte/commande/<int:pk>/', views_client.suivi_commande, name='suivi_commande'),
    path('compte/inscription/', views_client.inscription, name='inscription'),
    path('compte/connexion/', auth_views.LoginView.as_view(
        template_name='boutique/connexion_client.html'), name='connexion_client'),

    # Espace vendeur
    path('vendeur/', views_vendeur.espace_vendeur, name='espace_vendeur'),
    path('vendeur/connexion/', views_client.ConnexionVendeur.as_view(), name='connexion'),
    path('deconnexion/', auth_views.LogoutView.as_view(), name='deconnexion'),
    path('vendeur/produits/ajouter/', views_vendeur.ajouter_produit, name='ajouter_produit'),
    path('vendeur/produits/<int:pk>/modifier/', views_vendeur.modifier_produit, name='modifier_produit'),
    path('vendeur/produits/<int:pk>/couleur/', views_vendeur.ajouter_couleur, name='ajouter_couleur'),
    path('vendeur/commandes/', views_vendeur.commandes_vendeur, name='commandes_vendeur'),
    path('vendeur/livraison/<int:pk>/', views_vendeur.maj_livraison, name='maj_livraison'),
]