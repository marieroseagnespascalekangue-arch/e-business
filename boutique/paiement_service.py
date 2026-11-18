import json
import logging
import os
import urllib.error
import urllib.request

from django.db import transaction

from .models import Commande, ProduitArtisanal

journal = logging.getLogger(__name__)


class ErreurPaiement(Exception):
    pass


class StockInsuffisant(Exception):
    pass


def mode_reel():
    """Vrai si la variable PAIEMENT_MODE vaut 'campay' (sinon : simulation)."""
    return os.environ.get('PAIEMENT_MODE', 'simulation') == 'campay'


def _base_url():
    if os.environ.get('CAMPAY_ENV', 'DEV').upper() == 'PROD':
        return 'https://www.campay.net/api'
    return 'https://demo.campay.net/api'


def _appeler(chemin, donnees=None):
    jeton = os.environ.get('CAMPAY_TOKEN', '')
    if not jeton:
        raise ErreurPaiement("Le paiement n'est pas encore configuré.")
    requete = urllib.request.Request(
        _base_url() + chemin,
        data=json.dumps(donnees).encode() if donnees is not None else None,
        headers={'Authorization': 'Token ' + jeton, 'Content-Type': 'application/json'},
        method='POST' if donnees is not None else 'GET',
    )
    try:
        with urllib.request.urlopen(requete, timeout=20) as reponse:
            return json.loads(reponse.read().decode())
    except urllib.error.HTTPError as erreur:
        try:
            detail = json.loads(erreur.read().decode())
        except Exception:
            detail = {}
        journal.warning('Campay HTTP %s : %s', erreur.code, detail)
        raise ErreurPaiement(detail.get('message') or 'Le paiement a été refusé.')
    except Exception:
        journal.exception('Campay injoignable')
        raise ErreurPaiement('Impossible de joindre le service de paiement. Réessayez dans un instant.')


def demarrer_paiement(commande, numero):
    """Envoie la demande de paiement au téléphone du client. Renvoie la référence."""
    reponse = _appeler('/collect/', {
        'amount': str(int(commande.total)),
        'currency': 'XAF',
        'from': '237' + numero,
        'description': f'Commande {commande.pk}',
        'external_reference': str(commande.pk),
    })
    reference = reponse.get('reference')
    if not reference:
        raise ErreurPaiement('Réponse inattendue du service de paiement.')
    return reference


def statut_transaction(reference):
    """Renvoie PENDING, SUCCESSFUL ou FAILED."""
    reponse = _appeler(f'/transaction/{reference}/')
    return reponse.get('status', 'PENDING')


def finaliser_paiement(commande_pk, operateur, numero):
    """Marque la commande payée et décompte le stock (sans effet si déjà fait)."""
    with transaction.atomic():
        commande = Commande.objects.select_for_update().get(pk=commande_pk)
        if commande.statut in ('payee', 'livree'):
            return commande
        for ligne in commande.lignes.all():
            produit = ProduitArtisanal.objects.select_for_update().get(pk=ligne.produit_id)
            if produit.stock < ligne.quantite:
                raise StockInsuffisant(f'Stock insuffisant pour « {produit.nom_complet} ».')
            produit.stock -= ligne.quantite
            produit.save(update_fields=['stock'])
        commande.statut = 'payee'
        commande.operateur = operateur
        commande.numero_paiement = numero
        commande.save()
    return commande