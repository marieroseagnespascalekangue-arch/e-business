from io import BytesIO
from pathlib import Path

from django.contrib.auth.models import User
from django.core.files.base import ContentFile
from django.db import models
from PIL import Image

COULEURS = [
    ('Noir', '#222222'),
    ('Blanc', '#ffffff'),
    ('Beige', '#e8d8bd'),
    ('Marron', '#7b4a2a'),
    ('Rouge', '#c62828'),
    ('Orange', '#ef7d22'),
    ('Jaune', '#f4c430'),
    ('Vert', '#2e7d32'),
    ('Bleu', '#1e5aa8'),
    ('Violet', '#7b3fa0'),
    ('Rose', '#ec6fa0'),
    ('Gris', '#8a8a8a'),
    ('Multicolore', 'linear-gradient(135deg,#d33,#f4c430,#2e7d32,#1e5aa8)'),
]
FONDS_COULEURS = dict(COULEURS)


class Vendeur(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    nom_boutique = models.CharField(max_length=100)
    telephone = models.CharField(max_length=20)
    ville = models.CharField(max_length=60)

    def __str__(self):
        return self.nom_boutique


class Categorie(models.Model):
    nom = models.CharField(max_length=60)

    class Meta:
        ordering = ['nom']
        verbose_name = 'catégorie'
        verbose_name_plural = 'catégories'

    def __str__(self):
        return self.nom


class ProduitArtisanal(models.Model):
    vendeur = models.ForeignKey(Vendeur, on_delete=models.CASCADE)
    categorie = models.ForeignKey(
        Categorie, on_delete=models.SET_NULL, null=True, blank=True,
        verbose_name='catégorie',
    )
    nom = models.CharField(max_length=120)
    modele = models.CharField(
        'modèle', max_length=120, blank=True, default='',
        help_text="Même texte pour toutes les couleurs d'un même article (ex : Robe Wax Ankara).",
    )
    couleur = models.CharField(
        max_length=20, blank=True, default='',
        choices=[(nom, nom) for nom, _ in COULEURS],
    )
    description = models.TextField()
    prix = models.DecimalField(max_digits=10, decimal_places=0)  # en FCFA
    taux_tva = models.DecimalField(max_digits=5, decimal_places=2, default=19.25)
    stock = models.PositiveIntegerField(default=0)
    photo = models.ImageField(upload_to='produits/')
    actif = models.BooleanField(default=True)
    cree_le = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'produit artisanal'
        verbose_name_plural = 'produits artisanaux'

    def __str__(self):
        return self.nom_complet

    @property
    def nom_complet(self):
        return f'{self.nom} ({self.couleur})' if self.couleur else self.nom

    @property
    def fond_couleur(self):
        return FONDS_COULEURS.get(self.couleur, '#cccccc')

    @property
    def prix_ttc(self):
        return round(self.prix * (1 + self.taux_tva / 100))

    def save(self, *args, **kwargs):
        # Convertit la photo en WebP léger avant l'enregistrement
        if self.photo and not self.photo.name.lower().endswith('.webp'):
            image = Image.open(self.photo).convert('RGB')
            image.thumbnail((800, 800))
            tampon = BytesIO()
            image.save(tampon, format='WEBP', quality=75)
            nouveau_nom = Path(self.photo.name).stem + '.webp'
            self.photo.save(nouveau_nom, ContentFile(tampon.getvalue()), save=False)
        super().save(*args, **kwargs)


class Commande(models.Model):
    STATUTS = [
        ('attente', 'En attente de paiement'),
        ('payee', 'Payée'),
        ('livree', 'Livrée'),
        ('annulee', 'Annulée'),
    ]
    OPERATEURS = [
        ('mtn', 'MTN Mobile Money'),
        ('orange', 'Orange Money'),
    ]

    nom_client = models.CharField(max_length=100)
    telephone = models.CharField(max_length=20)
    ville = models.CharField(max_length=60)
    adresse = models.TextField()
    statut = models.CharField(max_length=10, choices=STATUTS, default='attente')
    operateur = models.CharField(max_length=10, choices=OPERATEURS, blank=True)
    numero_paiement = models.CharField(max_length=20, blank=True)
    reference_paiement = models.CharField(max_length=64, blank=True, default='')
    total = models.DecimalField(max_digits=12, decimal_places=0, default=0)
    client = models.ForeignKey('Client', on_delete=models.SET_NULL, null=True, blank=True, related_name='commandes')
    cree_le = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'Commande {self.pk} - {self.nom_client}'

    @property
    def tout_livre(self):
        lignes = list(self.lignes.all())
        return bool(lignes) and all(l.statut_livraison == 'livree' for l in lignes)


class LigneCommande(models.Model):
    ETAPES = [
        ('preparation', 'En préparation'),
        ('expediee', 'Expédiée'),
        ('livree', 'Livrée'),
    ]

    commande = models.ForeignKey(Commande, on_delete=models.CASCADE, related_name='lignes')
    produit = models.ForeignKey(ProduitArtisanal, on_delete=models.PROTECT)
    nom = models.CharField(max_length=120)  # copie du nom au moment de l'achat
    prix_unitaire = models.DecimalField(max_digits=10, decimal_places=0)  # TTC
    quantite = models.PositiveIntegerField()
    statut_livraison = models.CharField(max_length=12, choices=ETAPES, default='preparation')
    note_livraison = models.CharField(max_length=200, blank=True, default='')
    expediee_le = models.DateTimeField(null=True, blank=True)
    livree_le = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f'{self.quantite} x {self.nom}'

    @property
    def etape(self):
        return {'preparation': 1, 'expediee': 2, 'livree': 3}.get(self.statut_livraison, 1)


class Client(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    telephone = models.CharField(max_length=20, blank=True)
    ville = models.CharField(max_length=60, blank=True)
    adresse = models.TextField(blank=True)

    def __str__(self):
        return self.user.get_full_name() or self.user.username