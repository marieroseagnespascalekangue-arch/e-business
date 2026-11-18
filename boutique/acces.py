from functools import wraps

from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from .models import Vendeur


def compte_vendeur_seul(user):
    """Vrai pour un vendeur qui n'est pas administrateur."""
    return (user.is_authenticated and not user.is_staff
            and Vendeur.objects.filter(user=user).exists())


def client_requis(vue):
    """Page réservée aux clients connectés (pas aux comptes vendeurs)."""
    @wraps(vue)
    def enveloppe(request, *args, **kwargs):
        if compte_vendeur_seul(request.user):
            return render(request, 'boutique/compte_vendeur.html', status=403)
        return vue(request, *args, **kwargs)
    return login_required(enveloppe, login_url='connexion_client')