from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from . import paiement_service, panier
from .acces import client_requis, compte_vendeur_seul
from .forms import CommandeForm, PaiementForm
from .models import Categorie, Client, Commande, LigneCommande, ProduitArtisanal, Vendeur
from .paiement_service import ErreurPaiement, StockInsuffisant


def _entier(valeur, defaut):
    try:
        return int(valeur)
    except (TypeError, ValueError):
        return defaut


def _grouper(produits):
    """Un seul produit affiché par modèle (les autres couleurs sont regroupées)."""
    vus = {}
    for p in produits:
        cle = (p.vendeur_id, p.modele) if p.modele else p.pk
        if cle in vus:
            vus[cle].nb_couleurs += 1
        else:
            p.nb_couleurs = 1
            vus[cle] = p
    return list(vus.values())


def catalogue(request):
    categorie_active = _entier(request.GET.get('categorie'), None)
    recherche = request.GET.get('q', '').strip()[:80]
    produits = (
        ProduitArtisanal.objects
        .filter(actif=True, stock__gt=0)
        .select_related('vendeur')
        .order_by('-cree_le')
    )
    if categorie_active:
        produits = produits.filter(categorie_id=categorie_active)
    for mot in recherche.split():
        produits = produits.filter(
            Q(nom__icontains=mot) | Q(description__icontains=mot)
            | Q(modele__icontains=mot) | Q(couleur__icontains=mot)
            | Q(categorie__nom__icontains=mot)
            | Q(vendeur__nom_boutique__icontains=mot)
        )
    groupes = _grouper(produits)
    page = Paginator(groupes, 12).get_page(request.GET.get('page'))
    return render(request, 'boutique/catalogue.html', {
        'page': page,
        'categories': Categorie.objects.all(),
        'categorie_active': categorie_active,
        'recherche': recherche,
        'nb_resultats': len(groupes),
    })


def detail_produit(request, pk):
    produit = get_object_or_404(
        ProduitArtisanal.objects.select_related('vendeur', 'categorie'), pk=pk, actif=True
    )
    if produit.modele:
        variantes = list(
            ProduitArtisanal.objects
            .filter(actif=True, vendeur=produit.vendeur, modele=produit.modele)
            .order_by('couleur', 'pk')
        )
    else:
        variantes = []

    exclus = {produit.pk} | {v.pk for v in variantes}
    base = (
        ProduitArtisanal.objects
        .filter(actif=True, stock__gt=0)
        .select_related('vendeur')
        .exclude(pk__in=exclus)
        .order_by('-cree_le')
    )
    suggestions = []
    if produit.categorie_id:
        suggestions = _grouper(base.filter(categorie_id=produit.categorie_id))[:4]
    if len(suggestions) < 4:
        deja = {s.pk for s in suggestions}
        complement = [c for c in _grouper(base) if c.pk not in deja]
        suggestions += complement[:4 - len(suggestions)]

    return render(request, 'boutique/produit.html', {
        'produit': produit,
        'variantes': variantes,
        'suggestions': suggestions,
    })


def boutique_vendeur(request, pk):
    vendeur = get_object_or_404(Vendeur, pk=pk)
    produits = (
        ProduitArtisanal.objects
        .filter(vendeur=vendeur, actif=True, stock__gt=0)
        .order_by('-cree_le')
    )
    return render(request, 'boutique/vendeur.html', {
        'vendeur': vendeur,
        'produits': _grouper(produits),
    })


def voir_panier(request):
    lignes, total = panier.detail(request)
    return render(request, 'boutique/panier.html', {'lignes': lignes, 'total': total})


@require_POST
def ajouter_panier(request, pk):
    if compte_vendeur_seul(request.user):
        return render(request, 'boutique/compte_vendeur.html', status=403)
    produit = get_object_or_404(ProduitArtisanal, pk=pk, actif=True)
    quantite = max(_entier(request.POST.get('quantite'), 1), 1)
    panier.ajouter(request, produit, quantite)
    return redirect('panier')


@require_POST
def modifier_panier(request, pk):
    produit = get_object_or_404(ProduitArtisanal, pk=pk, actif=True)
    quantite = _entier(request.POST.get('quantite'), 1)
    panier.definir(request, produit, quantite)
    return redirect('panier')


@require_POST
def retirer_panier(request, pk):
    panier.retirer(request, pk)
    return redirect('panier')


@client_requis
def commander(request):
    client, _ = Client.objects.get_or_create(user=request.user)
    lignes, total = panier.detail(request)
    if not lignes:
        return redirect('panier')

    if request.method == 'POST':
        form = CommandeForm(request.POST)
        if form.is_valid():
            with transaction.atomic():
                commande = form.save(commit=False)
                commande.total = total
                commande.client = client
                client.telephone = commande.telephone
                client.ville = commande.ville
                client.adresse = commande.adresse
                client.save()
                commande.save()
                for l in lignes:
                    LigneCommande.objects.create(
                        commande=commande,
                        produit=l['produit'],
                        nom=l['produit'].nom_complet[:120],
                        prix_unitaire=l['produit'].prix_ttc,
                        quantite=l['quantite'],
                    )
            request.session['commande_id'] = commande.pk
            return redirect('paiement')
    else:
        form = CommandeForm(initial={
            'nom_client': request.user.get_full_name() or request.user.username,
            'telephone': client.telephone,
            'ville': client.ville,
            'adresse': client.adresse,
        })

    return render(request, 'boutique/commande.html',
                  {'form': form, 'lignes': lignes, 'total': total})


@client_requis
def paiement(request):
    client, _ = Client.objects.get_or_create(user=request.user)
    commande = Commande.objects.filter(
        pk=request.session.get('commande_id'), statut='attente', client=client
    ).first()
    if not commande:
        return redirect('catalogue')

    if request.method == 'POST':
        form = PaiementForm(request.POST)
        if form.is_valid():
            operateur = form.cleaned_data['operateur']
            numero = form.cleaned_data['numero']
            if paiement_service.mode_reel():
                try:
                    reference = paiement_service.demarrer_paiement(commande, numero)
                except ErreurPaiement as erreur:
                    form.add_error(None, str(erreur))
                else:
                    commande.reference_paiement = reference
                    commande.operateur = operateur
                    commande.numero_paiement = numero
                    commande.save(update_fields=['reference_paiement', 'operateur', 'numero_paiement'])
                    return redirect('paiement_attente')
            else:
                try:
                    paiement_service.finaliser_paiement(commande.pk, operateur, numero)
                except StockInsuffisant as erreur:
                    form.add_error(None, str(erreur))
                else:
                    request.session.pop('panier', None)
                    return redirect('confirmation')
    else:
        form = PaiementForm()

    return render(request, 'boutique/paiement.html', {
        'form': form, 'commande': commande, 'mode_reel': paiement_service.mode_reel(),
    })


@client_requis
def paiement_attente(request):
    """Page qui attend la confirmation du paiement sur le téléphone du client."""
    client, _ = Client.objects.get_or_create(user=request.user)
    commande = Commande.objects.filter(
        pk=request.session.get('commande_id'), client=client
    ).first()
    if not commande:
        return redirect('catalogue')
    if commande.statut in ('payee', 'livree'):
        return redirect('confirmation')
    if not commande.reference_paiement:
        return redirect('paiement')

    contexte = {'commande': commande, 'echec': False, 'erreur': ''}
    try:
        statut = paiement_service.statut_transaction(commande.reference_paiement)
    except ErreurPaiement:
        statut = 'PENDING'

    if statut == 'SUCCESSFUL':
        try:
            paiement_service.finaliser_paiement(
                commande.pk, commande.operateur, commande.numero_paiement)
        except StockInsuffisant as erreur:
            contexte['erreur'] = str(erreur)
        else:
            request.session.pop('panier', None)
            return redirect('confirmation')
    elif statut == 'FAILED':
        commande.reference_paiement = ''
        commande.save(update_fields=['reference_paiement'])
        contexte['echec'] = True

    return render(request, 'boutique/paiement_attente.html', contexte)


@client_requis
def confirmation(request):
    client, _ = Client.objects.get_or_create(user=request.user)
    commande = Commande.objects.filter(
        pk=request.session.get('commande_id'), statut__in=['payee', 'livree'], client=client
    ).first()
    if not commande:
        return redirect('catalogue')
    return render(request, 'boutique/confirmation.html', {'commande': commande})