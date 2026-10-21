from django.urls import path
from .views import (
    RegisterView, CustomObtainAuthToken, EventListCreateView, EventDetailView,
    StageListCreateView, StageDetailView, AttributeListCreateView, AttributeDetailView,
    EventAttributeValueListCreateView, EventAttributeValueDetailView, RegistrationListCreateView,
    EventParticipantsView, FeedbackListCreateView, ResultListCreateView,
)

urlpatterns = [
    path("register/", RegisterView.as_view(), name="register"),
    path("login/", CustomObtainAuthToken.as_view(), name="login"),
    path("events/", EventListCreateView.as_view(), name="event-list-create"),
    path("events/<int:pk>/", EventDetailView.as_view(), name="event-detail"),
    path("events/<int:event_pk>/stages/", StageListCreateView.as_view(), name="event-stages"),
    path("stages/<int:pk>/", StageDetailView.as_view(), name="stage-detail"),
    path("attributes/", AttributeListCreateView.as_view(), name="attribute-list-create"),
    path("attributes/<int:pk>/", AttributeDetailView.as_view(), name="attribute-detail"),
    path("events/<int:event_pk>/attributes/", EventAttributeValueListCreateView.as_view(), name="event-attribute-values"),
    path("event-attribute-values/<int:pk>/", EventAttributeValueDetailView.as_view(), name="event-attribute-value-detail"),
    path("registrations/", RegistrationListCreateView.as_view(), name="registration-list-create"),
    path("events/<int:event_pk>/participants/", EventParticipantsView.as_view(), name="event-participants"),
    path("feedback/", FeedbackListCreateView.as_view(), name="feedback-list-create"),
    path("results/", ResultListCreateView.as_view(), name="result-list-create"),
]
