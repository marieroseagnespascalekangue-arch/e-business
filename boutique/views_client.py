from django.contrib import messages
from django.views.decorators.cache import never_cache
from django.contrib.auth import login
from django.contrib.auth.views import LoginView
from django.shortcuts import get_object_or_404, redirect, render, resolve_url
from django.utils.http import url_has_allowed_host_and_scheme

from .acces import client_requis
from .forms_client import InscriptionForm, ProfilForm
from .models import Client, Commande


class ConnexionVendeur(LoginView):
    """Connexion depuis la page vendeur : on arrive dans l'espace vendeur."""
    template_name = 'boutique/connexion.html'

    def get_default_redirect_url(self):
        return resolve_url('espace_vendeur')


def _suite(request):
    suite = request.POST.get('next') or request.GET.get('next') or ''
    if suite and url_has_allowed_host_and_scheme(
            suite, allowed_hosts={request.get_host()}, require_https=request.is_secure()):
        return suite
    return 'mon_compte'


def inscription(request):
    if request.user.is_authenticated:
        return redirect('mon_compte')
    if request.method == 'POST':
        form = InscriptionForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, 'Bienvenue ! Votre compte est créé.')
            return redirect(_suite(request))
    else:
        form = InscriptionForm()
    return render(request, 'boutique/inscription.html', {
        'form': form, 'next': request.GET.get('next', ''),
    })


@never_cache
@client_requis
def mon_compte(request):
    client, _ = Client.objects.get_or_create(user=request.user)
    if request.method == 'POST':
        form = ProfilForm(request.POST, instance=client)
        if form.is_valid():
            form.save()
            messages.success(request, 'Vos informations ont été mises à jour.')
            return redirect('mon_compte')
    else:
        form = ProfilForm(instance=client)
    commandes = (
        Commande.objects.filter(client=client)
        .prefetch_related('lignes').order_by('-cree_le')
    )
    return render(request, 'boutique/mon_compte.html', {
        'form': form, 'commandes': commandes,
    })


@never_cache
@client_requis
def suivi_commande(request, pk):
    client, _ = Client.objects.get_or_create(user=request.user)
    commande = get_object_or_404(
        Commande.objects.prefetch_related('lignes__produit__vendeur'),
        pk=pk, client=client,
    )
    return render(request, 'boutique/suivi_commande.html', {'commande': commande})