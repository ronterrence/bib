from datetime import date, timedelta

from django.core.paginator import Paginator
from django.db.models import Case, CharField, IntegerField, Prefetch, Q, Value, When
from django.db.models.functions import Coalesce, Lower
from django.shortcuts import render
from django.urls import reverse

from circulation.models import Pret

from .models import Document, StatutDocument


DOCUMENT_TYPES = {
    "livres": "livre",
    "journaux": "journal",
    "cdroms": "cdrom",
    "microfilms": "microfilm",
}

SORTS = {
    "titre": (Lower("titre"), "cote"),
    "auteur": ("auteur_manquant", Lower("auteur_tri"), Lower("titre")),
    "cote": ("cote",),
    "date": ("date_manquante", "-journal__date_parution", Lower("titre")),
}


def _url_with(request, **changes):
    params = request.GET.copy()
    params.pop("page", None)
    for key, value in changes.items():
        if value:
            params[key] = value
        else:
            params.pop(key, None)
    query = params.urlencode()
    url = reverse("catalogue:liste")
    return f"{url}?{query}" if query else url


def liste(request):
    documents = Document.objects.select_related(
        "livre", "journal", "cdrom", "microfilm"
    ).prefetch_related(
        Prefetch(
            "prets",
            queryset=Pret.objects.filter(date_restitution__isnull=True).order_by(
                "-date_emprunt"
            ),
            to_attr="prets_actifs",
        )
    )

    titre = request.GET.get("titre", "").strip()
    auteur = request.GET.get("auteur", "").strip()
    cote = request.GET.get("cote", "").strip()
    date_document = request.GET.get("date", "").strip()
    document_type = request.GET.get("type", "tous")
    tri = request.GET.get("tri", "titre")

    if titre:
        documents = documents.filter(titre__icontains=titre)
    if auteur:
        documents = documents.filter(
            Q(livre__auteur__icontains=auteur)
            | Q(cdrom__auteur_ou_editeur__icontains=auteur)
        )
    if cote:
        if cote.isdigit():
            documents = documents.filter(cote=int(cote))
        else:
            documents = documents.none()
    if date_document:
        try:
            date_recherche = date.fromisoformat(date_document)
        except ValueError:
            documents = documents.none()
        else:
            documents = documents.filter(
                Q(journal__date_parution=date_recherche)
                | Q(date_acquisition=date_recherche)
            )
    if document_type in DOCUMENT_TYPES:
        documents = documents.filter(**{f"{DOCUMENT_TYPES[document_type]}__isnull": False})
    else:
        document_type = "tous"

    documents = documents.annotate(
        auteur_tri=Coalesce(
            "livre__auteur",
            "cdrom__auteur_ou_editeur",
            Value(""),
            output_field=CharField(),
        ),
        auteur_manquant=Case(
            When(Q(livre__isnull=False) | Q(cdrom__isnull=False), then=Value(0)),
            default=Value(1),
            output_field=IntegerField(),
        ),
        date_manquante=Case(
            When(journal__isnull=False, then=Value(0)),
            default=Value(1),
            output_field=IntegerField(),
        ),
    ).order_by(*SORTS.get(tri, SORTS["titre"]))
    if tri not in SORTS:
        tri = "titre"

    page_obj = Paginator(documents, 15).get_page(request.GET.get("page"))
    for document in page_obj.object_list:
        document.pret_actif = document.prets_actifs[0] if document.prets_actifs else None
        document.retour_prevu = (
            document.pret_actif.date_emprunt + timedelta(days=28)
            if document.pret_actif
            else None
        )
        document.localisation = (
            "Au guichet"
            if hasattr(document, "cdrom") or hasattr(document, "microfilm")
            else "En rayon"
        )

    tabs = [
        ("tous", "Tous"),
        ("livres", "Livres"),
        ("journaux", "Journaux"),
        ("cdroms", "CD-ROM"),
        ("microfilms", "Microfilms"),
    ]
    context = {
        "page_obj": page_obj,
        "type_actif": document_type,
        "tabs": [(value, label, _url_with(request, type=value)) for value, label in tabs],
        "tri": tri,
        "filtres": {
            "titre": titre,
            "auteur": auteur,
            "cote": cote,
            "date": date_document,
        },
        "pagination_query": _url_with(request).partition("?")[2],
    }
    return render(request, "catalogue/liste.html", context)
