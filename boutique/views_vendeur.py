from functools import wraps

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from .forms_vendeur import ProduitForm
from .models import COULEURS, LigneCommande, ProduitArtisanal, Vendeur

STATUTS_PAYES = ['payee', 'livree']
CHOIX_COULEURS = [{'nom': n, 'fond': f} for n, f in COULEURS]


def vendeur_requis(vue):
    """Réserve la page aux utilisateurs connectés qui ont une boutique."""
    @wraps(vue)
    def enveloppe(request, *args, **kwargs):
        vendeur = Vendeur.objects.filter(user=request.user).first()
        if vendeur is None:
            return render(request, 'boutique/pas_vendeur.html', status=403)
        return vue(request, vendeur, *args, **kwargs)
    return login_required(enveloppe, login_url='connexion')


def _page_formulaire(request, vendeur, form, titre, aide=''):
    return render(request, 'boutique/espace_produit.html', {
        'vendeur': vendeur, 'form': form, 'titre': titre,
        'aide': aide, 'couleurs': CHOIX_COULEURS,
    })


@vendeur_requis
def espace_vendeur(request, vendeur):
    produits = ProduitArtisanal.objects.filter(vendeur=vendeur).order_by('-cree_le')
    lignes = LigneCommande.objects.filter(
        produit__vendeur=vendeur, commande__statut__in=STATUTS_PAYES
    )
    return render(request, 'boutique/espace_accueil.html', {
        'vendeur': vendeur,
        'produits': produits,
        'ventes': sum(l.quantite for l in lignes),
        'chiffre': sum(l.prix_unitaire * l.quantite for l in lignes),
    })


@vendeur_requis
def ajouter_produit(request, vendeur):
    if request.method == 'POST':
        form = ProduitForm(request.POST, request.FILES)
        if form.is_valid():
            produit = form.save(commit=False)
            produit.vendeur = vendeur
            produit.save()
            messages.success(request, f'« {produit.nom_complet} » a été ajouté.')
            return redirect('espace_vendeur')
    else:
        form = ProduitForm()
    return _page_formulaire(request, vendeur, form, 'Ajouter un produit')


@vendeur_requis
def modifier_produit(request, vendeur, pk):
    produit = get_object_or_404(ProduitArtisanal, pk=pk, vendeur=vendeur)
    if request.method == 'POST':
        form = ProduitForm(request.POST, request.FILES, instance=produit)
        if form.is_valid():
            form.save()
            messages.success(request, f'« {produit.nom_complet} » a été mis à jour.')
            return redirect('espace_vendeur')
    else:
        form = ProduitForm(instance=produit)
    return _page_formulaire(request, vendeur, form, f'Modifier « {produit.nom} »')


@vendeur_requis
def ajouter_couleur(request, vendeur, pk):
    source = get_object_or_404(ProduitArtisanal, pk=pk, vendeur=vendeur)
    modele = source.modele or source.nom
    if request.method == 'POST':
        form = ProduitForm(request.POST, request.FILES)
        if form.is_valid():
            modele_final = form.cleaned_data['modele'] or modele
            if not source.modele:
                source.modele = modele_final
                source.save(update_fields=['modele'])
            produit = form.save(commit=False)
            produit.vendeur = vendeur
            produit.modele = modele_final
            produit.save()
            messages.success(request, f'La couleur « {produit.couleur or "sans nom"} » a été ajoutée.')
            return redirect('espace_vendeur')
    else:
        form = ProduitForm(initial={
            'categorie': source.categorie_id,
            'nom': source.nom,
            'modele': modele,
            'description': source.description,
            'prix': source.prix,
            'stock': 1,
            'actif': True,
        })
    return _page_formulaire(
        request, vendeur, form, f'Nouvelle couleur pour « {source.nom} »',
        'Choisissez la nouvelle couleur, ajoutez sa photo et indiquez son stock.',
    )


@vendeur_requis
def commandes_vendeur(request, vendeur):
    lignes = list(
        LigneCommande.objects
        .filter(produit__vendeur=vendeur, commande__statut__in=STATUTS_PAYES)
        .select_related('commande')
        .order_by('-commande__cree_le')
    )
    for l in lignes:
        l.montant = l.prix_unitaire * l.quantite
    return render(request, 'boutique/espace_commandes.html', {
        'vendeur': vendeur, 'lignes': lignes, 'etapes': LigneCommande.ETAPES,
    })


@vendeur_requis
def maj_livraison(request, vendeur, pk):
    """Le vendeur fait avancer la livraison d'un de ses articles."""
    if request.method != 'POST':
        return redirect('commandes_vendeur')
    ligne = get_object_or_404(
        LigneCommande.objects.select_related('commande'),
        pk=pk, produit__vendeur=vendeur, commande__statut__in=STATUTS_PAYES,
    )
    statut = request.POST.get('statut')
    if statut in dict(LigneCommande.ETAPES):
        maintenant = timezone.now()
        ligne.statut_livraison = statut
        if statut == 'preparation':
            ligne.expediee_le = None
            ligne.livree_le = None
        else:
            ligne.expediee_le = ligne.expediee_le or maintenant
            ligne.livree_le = (ligne.livree_le or maintenant) if statut == 'livree' else None
        ligne.note_livraison = request.POST.get('note', '').strip()[:200]
        ligne.save()
        commande = ligne.commande
        if commande.tout_livre and commande.statut == 'payee':
            commande.statut = 'livree'
            commande.save(update_fields=['statut'])
        elif not commande.tout_livre and commande.statut == 'livree':
            commande.statut = 'payee'
            commande.save(update_fields=['statut'])
        messages.success(request, f'Livraison de « {ligne.nom} » : {ligne.get_statut_livraison_display()}.')
    return redirect('commandes_vendeur')