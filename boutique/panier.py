from .models import ProduitArtisanal


def lire(request):
    return request.session.get('panier', {})


def ajouter(request, produit, quantite=1):
    """Ajoute 'quantite' exemplaires, sans dépasser le stock."""
    contenu = lire(request)
    cle = str(produit.pk)
    contenu[cle] = min(contenu.get(cle, 0) + quantite, produit.stock)
    request.session['panier'] = contenu


def definir(request, produit, quantite):
    """Fixe la quantité exacte (0 ou moins = retirer l'article)."""
    contenu = lire(request)
    cle = str(produit.pk)
    if quantite <= 0:
        contenu.pop(cle, None)
    else:
        contenu[cle] = min(quantite, produit.stock)
    request.session['panier'] = contenu


def retirer(request, pk):
    contenu = lire(request)
    contenu.pop(str(pk), None)
    request.session['panier'] = contenu


def detail(request):
    """Renvoie la liste des lignes du panier et le total TTC."""
    contenu = lire(request)
    produits = ProduitArtisanal.objects.filter(pk__in=contenu.keys(), actif=True)
    lignes = []
    total = 0
    for p in produits:
        quantite = min(contenu[str(p.pk)], p.stock)
        if quantite <= 0:
            continue
        sous_total = p.prix_ttc * quantite
        lignes.append({'produit': p, 'quantite': quantite, 'sous_total': sous_total})
        total += sous_total
    return lignes, total