from rest_framework import generics
from rest_framework.permissions import BasePermission
from rest_framework.exceptions import ValidationError
from django.contrib.auth import get_user_model

from .serializers import UserSerializer


class IsLMSAdmin(BasePermission):
    """Allow only active users with the application's administrator role."""

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.is_active
            and request.user.is_admin
        )


class UserListAPIView(generics.ListAPIView):
    lookup_field = "id"
    serializer_class = UserSerializer
    permission_classes = [IsLMSAdmin]

    def get_queryset(self):
        queryset = get_user_model().objects.all()
        query = self.request.query_params.get("q")
        if query is not None:
            query = query.strip()
            if len(query) > 150:
                raise ValidationError({"q": "Search text must be 150 characters or fewer."})
            queryset = queryset.filter(username__iexact=query)
        return queryset


class UserDetailView(generics.RetrieveAPIView):
    User = get_user_model()
    lookup_field = "id"
    queryset = User.objects.all()
    model = User
    permission_classes = [IsLMSAdmin]
