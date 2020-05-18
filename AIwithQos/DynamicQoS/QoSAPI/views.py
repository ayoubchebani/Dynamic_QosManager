from datetime import datetime, timedelta
import json
from netaddr import *
from django.shortcuts import render
from rest_framework.decorators import permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from rest_framework.views import APIView
from rest_framework_mongoengine import generics
from rest_framework import generics, viewsets

from QoSmanager.models import *
from .serializers import *
from QoSmonitor.models import *
from napalm import get_network_driver
from rest_framework import status
from rest_framework.response import Response
from .utils import *
from QoSmonitor.tasks import *
from rest_framework import serializers as sr


class AddTopology(generics.CreateAPIView):
    serializer_class = topologySerializer
    queryset = topology.objects()

    def perform_create(self, serializer):
        topo_name = self.request.data.get("topology_name")
        topology_qs = topology.objects(topology_name=topo_name)
        if len(topology_qs) == 0:
            serializer.save()
        else:
            raise sr.ValidationError("topology name {} exists ! try another one.".format(topo_name))


class AddDevice(generics.CreateAPIView):
    serializer_class = deviceSerializer

    def perform_create(self, serializer):

        if self.request.data.get("management") == None:
            addr = self.request.data.get("management.management_address")
            user = self.request.data.get("management.username")
            passwd = self.request.data.get("management.password")
        else:
            addr = self.request.data.get("management")['management_address']
            user = self.request.data.get("management")['username']
            passwd = self.request.data.get("management")['password']
        driver = get_network_driver("ios")
        topo_name = self.request.data.get("topology_name")
        topology_qs = topology.objects(topology_name=topo_name)
        if len(topology_qs) == 0:
            raise sr.ValidationError("topology doesn't exists")
        else:

            device_connection = driver(addr, user, passwd, timeout=5)
            fqdn = None
            device_connection.open()
            fqdn = device_connection.get_facts()['fqdn']
            device_connection.close()
            device_serializer = serializer.save(hostname=fqdn)
            new_device = device.objects.get(id=device_serializer.id)
            other_list = [new_device]
            device_list = topology_qs[0].devices
            # for device_cursor in device_list:
            #     other_list.append(device.objects.get(id=device_cursor.id))
            topology_qs[0].update(add_to_set__devices=new_device)


class TopologyByName(APIView):

    def get(self, request):

        if len(request.query_params) == 0:
            result = {'topologies': []}
            topologies = topology.objects()
            for topo in topologies:
                result['topologies'].append(json.loads(output_references_topology_brief(topo)))
            return Response(result)
        else:
            topology_name = request.query_params.get("name")
            if topology_name == None:
                return Response({'error': 'specify a correct query'})
            topologies = topology.objects(topology_name=topology_name)
            if len(topologies) == 0:
                return Response({'error': 'topology does not exists'})
            else:

                for topo in topologies:
                    result = json.loads(output_references_topology(topo))
                return Response(result)


class preapare_environment(generics.CreateAPIView):
    serializer_class = preapare_envSerializer
    queryset = "Nothing to do here it is out of models"

    def get(self, request):
        return Response("Specify the topology to prepare the envirement")

    def create(self, serializer):
        topology_name = self.request.data.get("topology")
        try:
            topology_exist = topology.objects.get(topology_name=topology_name)
        except:
            raise sr.ValidationError("Topology '{}' doesn't exist".format(topology_name))
        try:
            topology_exist.configure_ntp()
            topology_exist.configure_scp()
            topology_exist.configure_snmp()
        except Exception as e:
            raise sr.ValidationError("ERROR : {}".format(e))
        return Response("the environment is preapared successfully")


class discover_network(generics.CreateAPIView):
    serializer_class = discover_networkSerializer
    queryset = "Nothing to do here it is out of models"

    def get(self, request):
        return Response("please specify the topology to discover")

    def create(self, serializer):
        topology_name = self.request.data.get("topology")
        try:
            topology_exist = topology.objects.get(topology_name=topology_name)
        except:
            raise sr.ValidationError("Topology '{}' doesn't exist".format(topology_name))

        try:
            topology_exist.get_networks()
        except Exception as e:
            raise sr.ValidationError("ERROR : {}".format(e))

        try:
            topo2 = topology.objects.get(topology_name=topology_name)
            topo2.create_links()
        except Exception as e:
            raise sr.ValidationError("ERROR : {}".format(e))

        return Response("Discovery is finish successfully")


class configure_monitoring(generics.CreateAPIView):
    serializer_class = configure_monitoringSerializer
    queryset = "Nothing to do here it is out of models"

    def get(self, request):
        return Response("please specify the topology name and destination of collector")

    def create(self, serializer):
        collector = self.request.data.get("destination")
        topology_name = self.request.data.get("topology")
        try:
            IPAddress(collector)
        except:
            raise sr.ValidationError(" '{}' is not a valide ip address".format(collector))
        try:
            topology_exist = topology.objects.get(topology_name=topology_name)
        except:
            raise sr.ValidationError("Topology '{}' doesn't exist".format(topology_name))
        if topology_exist.monitoring_enabled == True:
            raise sr.ValidationError("Topology '{}' is already configured".format(topology_name))

        """monitors = topology_exist.get_monitors()
		for monitor in monitors:
			try:
				monitor.configure_netflow(destination = collector)
			except Exception as e:
				raise sr.ValidationError("ERROR : {}".format(e))"""

        for monitor in topology_exist.devices:
            try:
                monitor.configure_netflow(destination=collector)
            except Exception as e:
                raise sr.ValidationError("ERROR : {}".format(e))

        topology_exist.monitoring_enabled = True
        topology_exist.update(set__monitoring_enabled=True)
        return Response("Monitoring is configured successfully")


class start_monitoring(generics.CreateAPIView):
    serializer_class = start_monitoringSerializer
    queryset = "Nothing to do here it is out of models"

    def get(self, request):
        return Response("please specify the topology to start monitoring")

    def create(self, serializer):
        topology_name = self.request.data.get("topology")
        try:
            topology_exist = topology.objects.get(topology_name=topology_name)
        except:
            raise sr.ValidationError("Topology '{}' doesn't exist".format(topology_name))

        # if topology_exist.monitoring_activated == True:
        #	raise sr.ValidationError("Topology '{}' is already monitored".format(topology_name))

        sniff_back(topology_name)

        topology_exist.monitoring_activated = True
        topology_exist.update(set__monitoring_activated=True)
        return Response("Monitoring is starting successfully")


"""class stop_monitoring(generics.CreateAPIView):
	serializer_class =  start_monitoringSerializer
	queryset = "Nothing to do here it is out of models"
"""


class FlowTable(APIView):
    def get(self, request):

        if len(request.query_params) == 0:
            return Response({'error': 'specify a correct query'})
        else:

            topo_name = request.query_params.get("topology")
            # time = request.query_params.get("time")
            input_topo = topology.objects(topology_name=topo_name)[0]
            point = datetime.now() - timedelta(minutes=1.001)
            print(point)
            fields = netflow_fields.objects(first_switched__lte=point, last_switched__gte=point)
            fields_picked = []
            print(len(fields))
            for field in fields:
                topo = topology.objects(devices__contains=field.device_ref)
                if input_topo == topo[0]:
                    fields_picked.append(field)

            print(fields_picked)
            result_tuple = []
            for field in fields_picked:

                related_ip_sla = ip_sla_info.objects(timestamp=field.collection_time,
                                                     ip_sla_ref=field.flow_ref.ip_sla_ref)
                if len(related_ip_sla) != 0:
                    result_tuple.append({'netflow_field': field, 'sla_info': related_ip_sla[0]})
                else:
                    result_tuple.append({'netflow_field': field})

            print(result_tuple)
            result = {'data': []}
            for entry in result_tuple:
                if 'sla_info' in entry:
                    result['data'].append(
                        json.loads(output_flow_table_print(entry['netflow_field'], entry['sla_info'])))
                else:
                    result['data'].append(json.loads(output_flow_table_print(entry['netflow_field'], None)))

            return Response(result)


class FlowTableTwoRates(APIView):
    def get(self, request):

        if len(request.query_params) == 0:
            return Response({'error': 'specify a correct query'})
        else:

            topo_name = request.query_params.get("topology")
            time_start = request.query_params.get("time_start")
            time_start = datetime.strptime(time_start, "%Y-%m-%d %H:%M:%S")
            time_end = request.query_params.get("time_end")
            time_end = datetime.strptime(time_end, "%Y-%m-%d %H:%M:%S")
            input_topo = topology.objects(topology_name=topo_name)[0]
            print(time_start)
            print(time_end)
            fields = netflow_fields.objects(first_switched__gte=time_start, last_switched__lte=time_end)
            fields_picked = []
            print(len(fields))
            for field in fields:
                topo = topology.objects(devices__contains=field.device_ref)
                if input_topo == topo[0]:
                    fields_picked.append(field)

            print(fields_picked)
            result_tuple = []
            for field in fields_picked:

                related_ip_sla = ip_sla_info.objects(timestamp=field.collection_time,
                                                     ip_sla_ref=field.flow_ref.ip_sla_ref)
                if len(related_ip_sla) != 0:
                    result_tuple.append({'netflow_field': field, 'sla_info': related_ip_sla[0]})
                else:
                    result_tuple.append({'netflow_field': field})

            print(result_tuple)
            result = {'data': []}
            for entry in result_tuple:
                if 'sla_info' in entry:
                    result['data'].append(
                        json.loads(output_flow_table_print(entry['netflow_field'], entry['sla_info'])))
                else:
                    result['data'].append(json.loads(output_flow_table_print(entry['netflow_field'], None)))

            return Response(result)


class ListTopologiesBrief(APIView):

    def get(self, request):
        topologies = topology.objects()

        result = [
            json.loads(ouput_topology_id(topo)) for topo in topologies
        ]

        return Response(result)


class ListDevicesBrief(APIView):
    def get(self, request):

        topology_id = request.query_params.get("id")
        print(topology_id)
        try:
            tp = topology.objects.get(id=topology_id)
        except:
            pass
        devices_list = tp.devices

        result = [
            json.loads(ouput_device_id(dv)) for dv in devices_list
        ]

        return Response(result)


class ListInterfacesBrief(APIView):
    def get(self, request):

        device_id = request.query_params.get("id")
        try:
            dv = device.objects.get(id=device_id)
        except:
            pass
        interface_list = dv.interfaces

        result = [
            json.loads(ouput_interface_id(intf)) for intf in interface_list
        ]

        return Response(result)


class CurrentFlowsInterface(APIView):
    def get(self, request):
        result = {'topologies': []}
        topologies = topology.objects()
        for topo in topologies:
            result['topologies'].append(json.loads(output_topology_level(topo)))
        return Response(result)


class FlowCharts(APIView):

    def get(self, request):
        flow_id = request.query_params.get("flow")
        topology_name = request.query_params.get("topology")
        point = request.query_params.get("points")
        point = datetime.now() - timedelta(minutes=2)
        flow_ins = flow.objects()[0]
        result = json.loads(get_flow_statistics(topology_name, 'df54d54q324v2c1g53z45t4', point))
        return Response(result)


class FlowsInterface(APIView):
    def get(self, request):

        if len(request.query_params) == 0:
            return Response({'error': 'specify a correct query'})
        else:

            topo_name = request.query_params.get("topology")
            # time = request.query_params.get("time")
            input_topo = topology.objects(topology_name=topo_name)[0]
            point = datetime.now() - timedelta(minutes=1.001)
            fields = netflow_fields.objects(first_switched__lte=point, last_switched__gte=point)
            fields_picked = []
            print(len(fields))
            for field in fields:
                topo = topology.objects(devices__contains=field.device_ref)
                if input_topo == topo[0]:
                    fields_picked.append(field)

            print(fields_picked)
            result_tuple = []
            for field in fields_picked:

                related_ip_sla = ip_sla_info.objects(timestamp=field.collection_time,
                                                     ip_sla_ref=field.flow_ref.ip_sla_ref)
                if len(related_ip_sla) != 0:
                    result_tuple.append({'netflow_field': field, 'sla_info': related_ip_sla[0]})
                else:
                    result_tuple.append({'netflow_field': field})

            print(result_tuple)
            result = {'data': []}
            for entry in result_tuple:
                if 'sla_info' in entry:

                    result['data'].append(
                        json.loads(output_references_flow(entry['netflow_field'].flow_ref, [entry['netflow_field']])))
                else:
                    result['data'].append(
                        json.loads(output_references_flow(entry['netflow_field'].flow_ref, [entry['netflow_field']])))

            return Response(result)


class UserViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows users to be viewed or edited.
    """
    queryset = User.objects.all().order_by('-date_joined')
    serializer_class = UserSerializer


class GroupViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows groups to be viewed or edited.
    """
    queryset = Group.objects.all()
    serializer_class = GroupSerializer


class ApplicationViewSet(viewsets.ModelViewSet):
    """
        API endpoint that allows groups to be viewed or edited.
        """

    serializer_class = ApplicationSerializer

    def get_queryset(self):
        """
            This view should return a list of all the purchases
            for the currently authenticated user.
            """
        policy = self.request.query_params.get('policy_id', None)
        print(type(policy))
        # print(policyins)
        # policy_in =PolicyIn.objects.get(policy_ref=policyins)
        if policy == None:
            return Application.objects.all()
        return Application.objects.filter(policy_in=policy)


class DeviceViewSet(viewsets.ModelViewSet):
    """
        API endpoint that allows groups to be viewed or edited.
        """

    serializer_class = DeviceSerializer

    def get_queryset(self):
        """
            This view should return a list of all the purchases
            for the currently authenticated user.
            """
        policy = self.request.query_params.get('policy_id', None)
        if policy == None:
            return Device.objects.all()
        return Device.objects.filter(policy_ref=policy)


class TuningViewSet(viewsets.ModelViewSet):
    """
        API endpoint that allows groups to be viewed or edited.
        """

    serializer_class = TuningSerializer

    def get_queryset(self):
        """
            This view should return a list of all the purchases
            for the currently authenticated user.
            """
        policy = self.request.query_params.get('policy_id', None)
        if policy == None:
            return TuningHistory.objects.all()
        return TuningHistory.objects.filter(policy_ref=policy)
