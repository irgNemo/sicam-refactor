from django.shortcuts import get_object_or_404
from rest_framework.permissions import BasePermission
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.exceptions import ValidationError, PermissionDenied
from .access import operational, scoped
from .services.lifecycle import model_for, inspect_lifecycle, execute_lifecycle, is_admin


class LifecyclePermission(BasePermission):
    def has_permission(self, request, view):
        return operational(request.user)


class LifecycleView(APIView):
    permission_classes = [LifecyclePermission]

    def target(self, request, resource, pk):
        if resource in ('users', 'institutions') and not is_admin(request.user):
            raise PermissionDenied()
        model = model_for(resource)
        return get_object_or_404(scoped(model.objects.all(), request.user), pk=pk)

    def get(self, request, resource, pk):
        return Response(inspect_lifecycle(self.target(request, resource, pk), request.user))

    def post(self, request, resource, pk):
        target = self.target(request, resource, pk)
        if request.data.get('confirm') is not True:
            raise ValidationError({'confirm': 'Confirme explícitamente el impacto de la acción.'})
        return Response(execute_lifecycle(target, request.user, request.data.get('action'), request.data.get('reason')))
