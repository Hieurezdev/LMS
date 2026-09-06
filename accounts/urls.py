from django.urls import path, include
from .views import (
    profile,
    profile_single,
    admin_panel,
    profile_update,
    change_password,
    validate_username,
    RoleLoginView,
    register,
    create_cashier_account,
    backup_center,
    backup_download,
    backup_file_download,
    backup_restore,
)

urlpatterns = [
    path("login/", RoleLoginView.as_view(), name="login"),
    path("register/", register, name="register"),
    path("", include("django.contrib.auth.urls")),
    path("admin_panel/", admin_panel, name="admin_panel"),
    path("admin_panel/create-cashier/", create_cashier_account, name="create_cashier_account"),
    path("admin_panel/backups/", backup_center, name="backup_center"),
    path("admin_panel/backups/create/", backup_download, name="backup_download"),
    path("admin_panel/backups/restore/", backup_restore, name="backup_restore"),
    path("admin_panel/backups/<str:filename>/download/", backup_file_download, name="backup_file_download"),
    path("profile/", profile, name="profile"),
    path("profile/<int:id>/detail/", profile_single, name="profile_single"),
    path("setting/", profile_update, name="edit_profile"),
    path("change_password/", change_password, name="change_password"),
    path("ajax/validate-username/", validate_username, name="validate_username"),
]
