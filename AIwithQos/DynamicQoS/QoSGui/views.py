import json
import os

from django.core.files import File
from django.shortcuts import render

# Create your views here.
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseRedirect, HttpResponse
from django.urls import reverse
from mongoengine import *
from django.shortcuts import render, redirect
from QoSmonitor.models import *
from QoSmanager.models import *
from threading import Thread
import requests
# Create your views here.

from QoSGui.forms import *

from QoSmonitor.models import *

from DynamicQoS.settings import MEDIA_ROOT

from QoSmonitor.utils import check_if_exists

from QoSmonitor.tasks import *

from QoSmonitor.models import access

from QoSmonitor.tasks import add_device_api_call1


@login_required(login_url='/login/')
def home(request):
    publish(topic="LimitBreach/J", payload="Jitter Limit breach", qos=1, retain=False)
    ctx = {}
    return render(request, 'home.html', context=ctx)


def drag_drop(request, topo_id):
    if os.path.isfile(str(MEDIA_ROOT[0]) + "/topologies/" + str(topo_id) + ".json"):
        with open(str(MEDIA_ROOT[0]) + "/topologies/" + str(topo_id) + ".json", 'r') as file:
            data = file.read().replace('\n', '')
            print(data)
            JsonFile = GetJsonFile(initial={'Text': data})
    else:

        JsonFile = GetJsonFile(initial={'Text': """{ "class": "go.GraphLinksModel",
                   "copiesArrays": true,
                   "copiesArrayObjects": true,
                   "linkFromPortIdProperty": "fromPort",
                   "linkToPortIdProperty": "toPort",
                   "nodeDataArray": [],
                   "linkDataArray": []}"""})

    ctx = {'json': JsonFile, 'id': topo_id}
    return render(request, 'dragndrop.html', context=ctx)


def add_topology(request):
    TopoForm = AddTopologyForm(request.POST)
    if TopoForm.is_valid():
        tp = topology(topology_name=request.POST['Name'], topology_desc=request.POST['TopologyDesc'])
        tp.save()
    return HttpResponseRedirect(reverse('Topologies', kwargs={}))


@login_required(login_url='/login/')
def topologies(request):
    TopoForm = AddTopologyForm()
    topologies = topology.objects
    ctx = {'topology': TopoForm, 'topologies': topologies}
    return render(request, 'draw.html', context=ctx)

#to comment

     #untill here
def add_device_api_call(topology_name, management_interface, management_address, username, password):
    json_data = {"management": {"management_interface": management_interface, "management_address": management_address,
                                "username": username, "password": password}, "topology_name": topology_name}
    print(topology_name, management_address, management_interface, username, password)
    api_url = "http://localhost:8000/api/v1/add-device"
    response = requests.post(url=api_url, json=json_data)
    print(response.status_code)
    print(response.content)

    return response.content


@login_required(login_url='/login/')
def save_json_topology(request, topo_id):
    JsonFile = GetJsonFile(request.POST)
    if JsonFile.is_valid:
        topology_json = request.POST['Text']
        data = json.loads(topology_json)
        file_url = (str(MEDIA_ROOT[0]) + "/topologies/" + str(topo_id) + ".json")
        with open(file_url, "w") as f:
            myfile = File(f)
            myfile.write(request.POST['Text'])

        topology_ins = topology.objects.get(id=topo_id)
        threads = []
        devices_list = []
        for device_str in data['nodeDataArray']:
            """
               getting nodes data
            """
            if not (device_str['category'] == 'cloud') and not (device_str['category'] == 'L3Switch'):

                try:
                    location = device_str['Location']
                except KeyError:
                    location = ''
                try:
                    address = device_str['Address']
                except KeyError:
                    address = ''

                try:
                    username = device_str['Username']
                except KeyError:
                    username = ''
                try:
                    password = device_str['Password']
                except KeyError:
                    password = ''
                try:
                    secret = device_str['Secret']
                except KeyError:
                    secret = ''

                """
                creating the devices
                """
                print(address + ' ' + location + ' ' + username + ' ' + password + ' ' + secret)
                # add_device_api_call(topology_name=topology_ins.topology_name,management_interface="lo0",management_address=address,username=username,password=password)
                threads.append(Thread(target=add_device_api_call,
                                      args=(topology_ins.topology_name, "lo0", address, username, password)))
        for th in threads:
            print("start thread")
            th.start()

        for th in threads:
            th.join()
        print("prepare invo")
        prepare_env_api_call(topology_ins.topology_name)
        print("discover")
        discover_network_api_call(topology_ins.topology_name)
        url = "http://127.0.0.1:8000/api/v1/topology"
        r = requests.get(url)
        # # #
        topologies = (r.json())
        for topo in topologies['topologies']:
            top = Topology.objects.create(topology_name=topo['topology_name'], topology_desc=topo['topology_desc'])
            url = "http://127.0.0.1:8000/api/v1/topology?name=" + topo['topology_name']
            r = requests.get(url)
            devices = (r.json())
            for device in devices['devices']:
                man = device['management']
                mana = Access.objects.create(management_interface=man['management_interface'],
                                             management_address=man['management_address'],
                                             username=man['username'],
                                             password=man['password'])
                dev = Device.objects.create(hostname=device['hostname'], topology_ref=top, management=mana)

                interfaces = device['interfaces']
                for interface in interfaces:
                    if interface['interface_name'] != "Loopback0":
                        Interface.objects.create(device_ref=dev,
                                                 interface_name=interface['interface_name'],
                                                 egress=True)
            devices = Device.objects.filter(topology_ref=top)
            for device in devices:
                connection = device.connect()
                interfaces = connection.get_interfaces()
                for interface in interfaces:
                    print(interface)
                    print(interfaces[interface]['description'])
                    if interfaces[interface]['description'] == "#ingress":
                        inter = Interface.objects.filter(device_ref=device, interface_name=interface)
                        if len(inter) != 0:
                            i = Interface.objects.get(device_ref=device, interface_name=interface)
                            i.ingress = True
                            i.egress = False
                            i.save()
                        else:
                            Interface.objects.create(device_ref=device,
                                                     interface_name=interface,
                                                     ingress=True)
                    if interfaces[interface]['description'] == "#wan":
                        inter = Interface.objects.filter(device_ref=device, interface_name=interface)
                        if len(inter) != 0:
                            i = Interface.objects.get(device_ref=device, interface_name=interface)
                            i.wan = True
                            i.egress = False
                            i.save()
                        else:
                            Interface.objects.create(device_ref=device,
                                                     interface_name=interface,
                                                     wan=True)

                connection.close()

    return HttpResponseRedirect(reverse('Topologies', kwargs={}))


def flow_table_view(request):
    ctx = {}
    return render(request, 'flowtable.html', context=ctx)


@login_required(login_url='/login/')
def charts_test(request, topo_id):
    ctx = {}
    return render(request, 'charts.html', context=ctx)


@login_required(login_url='/login/')
def charts_view(request, topo_id):
    ctx = {}
    return render(request, 'ChartsPage.html', context=ctx)


def test_background(request):
    topo = topology.objects()[0]
    sniff_back(topo.topology_name)

    return HttpResponse("Started")


def discover_topology(request, topo_name):
    topo = topology.objects(topology_name=topo_name)
    try:
        topo.get_networks()
        topo.create_links()

    except Exception as e:
        print(e)

    return HttpResponseRedirect(reverse('Topologies', kwargs={}))


def prepare_environement(request, topo_name):
    topo = topology.objects(topology_name=topo_name)
    try:
        topo.configure_ntp()
        topo.configure_scp()
        topo.configure_snmp()
    except Exception as e:
        print(e)
    return HttpResponseRedirect(reverse('Topologies', kwargs={}))


def configure_monitoring(request, topo_name, collector):
    topo = topology.objects(topology_name=topo_name)
    for dv in topo.devices:
        try:
            dv.configure_netflow(destination=collector)
        except Exception as e:
            print(e)

    return HttpResponseRedirect(reverse('Topologies', kwargs={}))


def start_monitoring(request, topo_name):
    sniff_back(topo_name)

    return HttpResponseRedirect(reverse('Topologies', kwargs={}))


def configure_m(request):
    topo_id = request.POST['topo_idk']
    print('yoooo')
    print(topo_id)

    destination = request.POST['destination']

    print('yoooo')
    print(destination)
    topology_ins = topology.objects.get(id=topo_id)
    configure_monitoring_api_call(topology_ins.topology_name, destination)
    return HttpResponseRedirect(reverse('Topologies', kwargs={}))


def start_m(request, topo_id):
    topology_ins = topology.objects.get(id=topo_id)
    start_monitoring_api_call(topology_ins.topology_name)
    return HttpResponseRedirect(reverse('Topologies', kwargs={}))


def delete_topology(request, topo_id):
    topology_ins = topology.objects.get(id=topo_id)
    topology_manager = Topology.objects.filter(topology_name=topology_ins.topology_name)
    if len(topology_manager) != 0:
        for topo in topology_manager:
            topo.delete()
    for device in topology_ins.devices:
        for interface in device.interfaces:
            interface.delete()
        device.delete()
    for link in topology_ins.links:
        link.delete()
    topology_ins.delete()
    return HttpResponseRedirect(reverse('Topologies', kwargs={}))
