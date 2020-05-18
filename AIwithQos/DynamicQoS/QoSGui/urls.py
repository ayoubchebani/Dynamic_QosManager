from django.urls import path
from django.contrib.auth import views as loginview
from QoSGui.forms import LoginForm
from . import views

urlpatterns = [
    path('login/', loginview.login, {'authentication_form': LoginForm}),
    path('', views.home, name='Home'),
    path('topologies/', views.topologies, name='Topologies'),
    path('addtopology/', views.add_topology, name='AddTopology'),
    path('drag_drop/<topo_id>', views.drag_drop, name='drag_drop'),
    path('saveTopology/<topo_id>', views.save_json_topology, name='SaveTopology'),
    path('flow_table/', views.flow_table_view, name='FlowTable'),
    path('charts', views.charts_test, name='Charts'),
    path('test_back', views.test_background, name='tesback'),
    path('topology_discovery/<topo_name>',views.discover_topology, name="discover_topology"),
    path('perepare_environment/<topo_name>',views.prepare_environement, name="prepare_environement"),
    path('configure_monitoring/<topo_name>/<collector>',views.configure_monitoring, name="configure_monitoring"),
    path('start_monitoring/<topo_name>', views.start_monitoring, name="start_monitoring"),
    path('configure_m', views.configure_m, name="configure_m"),
    path('start_m/<topo_id>', views.start_m, name="start_m"),
    path('delete_topology/<topo_id>', views.delete_topology, name="delete_topology"),
]

