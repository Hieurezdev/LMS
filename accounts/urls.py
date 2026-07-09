from django.urls import path, include
from .views import (
    profile,
    profile_single,
    admin_panel,
    profile_update,
    change_password,
    validate_username,
)

urlpatterns = [
    path("", include("django.contrib.auth.urls")),
    path("admin_panel/", admin_panel, name="admin_panel"),
    path("profile/", profile, name="profile"),
    path("profile/<int:id>/detail/", profile_single, name="profile_single"),
    path("setting/", profile_update, name="edit_profile"),
    path("change_password/", change_password, name="change_password"),
    path("ajax/validate-username/", validate_username, name="validate_username"),
]
