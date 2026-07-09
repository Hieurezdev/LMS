from django.contrib.auth import get_user_model, login

User = get_user_model()

class AutoLoginMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Automatically login as superuser if not authenticated
        if not hasattr(request, 'user') or not request.user.is_authenticated:
            user = User.objects.filter(is_superuser=True).first()
            if not user:
                user = User.objects.first()
            if not user:
                # Create default admin user if database is clean
                user = User.objects.create_superuser(
                    username='admin',
                    email='admin@example.com',
                    password='admin'
                )
            
            # Specify the authentication backend to avoid ModelBackend requirement issues
            user.backend = 'django.contrib.auth.backends.ModelBackend'
            login(request, user)
            
        response = self.get_response(request)
        return response
