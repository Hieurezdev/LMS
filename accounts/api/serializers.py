from rest_framework import serializers
from django.contrib.auth import get_user_model


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = get_user_model()
        # Never expose password hashes or permission M2M relations through the API.
        fields = (
            "id",
            "username",
            "first_name",
            "last_name",
            "email",
            "phone",
            "address",
            "gender",
            "role",
            "is_approved",
            "is_student",
            "is_lecturer",
            "is_parent",
            "is_dep_head",
            "picture",
            "date_joined",
        )
