from django.conf import settings
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme

from wagtail import hooks
from wagtail.forms import PasswordViewRestrictionForm
from wagtail.models import Page, PageViewRestriction, Site


def serve(request, path):
    site = Site.find_for_request(request)
    if not site:
        raise Http404

    path_components = [component for component in path.split("/") if component]
    page, args, kwargs = get_page_for_path(site, request, path_components)

    for fn in hooks.get_hooks("before_serve_page"):
        result = fn(page, request, args, kwargs)
        if isinstance(result, HttpResponse):
            return result

    return serve_page(request, page, *args, **kwargs)


def get_page_for_path(site, request, path_components):
    return site.root_page.localized.specific.route(request, path_components)


def serve_page(request, page, *args, **kwargs):
    return page.serve(request, *args, **kwargs)


def authenticate_with_password(request, page_view_restriction_id, page_id):
    restriction = get_object_or_404(PageViewRestriction, id=page_view_restriction_id)
    page = get_object_or_404(Page, id=page_id).specific

    if request.method == "POST":
        form = PasswordViewRestrictionForm(request.POST, instance=restriction)
        if form.is_valid():
            return handle_valid_password(request, form, restriction, page)
    else:
        form = PasswordViewRestrictionForm(instance=restriction)

    action_url = reverse("wagtailcore_authenticate_with_password", args=[restriction.id, page.id])
    return page.serve_password_required_response(request, form, action_url)


def handle_valid_password(request, form, restriction, page):
    return_url = form.cleaned_data["return_url"]

    if not url_has_allowed_host_and_scheme(return_url, request.get_host(), request.is_secure()):
        return_url = settings.LOGIN_REDIRECT_URL

    restriction.mark_as_passed(request)
    return redirect(return_url)
