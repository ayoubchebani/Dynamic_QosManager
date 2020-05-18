from django.urls import path, include
from rest_framework import routers

from .views import *

router = routers.DefaultRouter()
router.register(r'users', UserViewSet)
router.register(r'groups', GroupViewSet)
router.register(r'applications', ApplicationViewSet, basename='application')
router.register(r'devices', DeviceViewSet, basename='devices')
router.register(r'tuning', TuningViewSet, basename='tuning')

urlpatterns = [
    path('add-device', AddDevice.as_view(), name="add-device"),
    path('add-topology', AddTopology.as_view(), name="add-topology"),
    path('topology', TopologyByName.as_view(), name="topology-by-name"),
    path('preapare-env', preapare_environment.as_view(), name="preapare-environment"),
    path('discover-network', discover_network.as_view(), name="discover-network"),
    path('configure-monitoring', configure_monitoring.as_view(), name="configure-monitoring"),
    path('start-monitoring', start_monitoring.as_view(), name="start-monitoring"),
    path('topologiesbrief', ListTopologiesBrief.as_view(), name="topologies"),
    path('devicesbrief', ListDevicesBrief.as_view(), name="devices"),
    path('interfacesbrief', ListInterfacesBrief.as_view(), name="interfaces"),
    path('flowtable', FlowTable.as_view(), name="flowtable"),
    path('flowtabletworates', FlowTableTwoRates.as_view(), name="flowtabletworates"),
    path('current-flows', FlowsInterface.as_view(), name="currentflows"),
    path('flow-charts', FlowCharts.as_view(), name="flow-charts"),
    path('', include(router.urls)),

]
app_name = 'APIv1'
