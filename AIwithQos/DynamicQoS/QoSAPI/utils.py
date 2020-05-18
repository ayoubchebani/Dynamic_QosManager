import json

from QoSmonitor.models import application

from QoSmonitor.models import *
from datetime import timedelta, datetime
from mongoengine import Q


def output_references_device(device):
    device_dct = json.loads(device.to_json(indent=2))
    del (device_dct['_id'])
    device_dct["interfaces"] = [
        json.loads(interface.to_json(indent=2)) for interface in device.interfaces]
    for interf in device_dct["interfaces"]:
        del (interf['_id'])

    return json.dumps(device_dct, indent=4)


def output_references_link(link):
    link_dct = json.loads(link.to_json(indent=2))
    del (link_dct['_id'])
    link_dct["from_device"] = json.loads(output_references_device_brief(link.from_device))
    link_dct["to_interface"] = json.loads(link.to_interface.to_json(indent=2))
    del (link_dct["to_interface"]['_id'])
    link_dct["from_interface"] = json.loads(link.from_interface.to_json(indent=2))
    del (link_dct["from_interface"]['_id'])
    link_dct["to_device"] = json.loads(output_references_device_brief(link.to_device))

    return json.dumps(link_dct, indent=4)


def output_references_topology(topology):
    topology_dct = json.loads(topology.to_json(indent=2))
    del (topology_dct['_id'])
    topology_dct["devices"] = [
        json.loads(output_references_device(device)) for device in topology.devices
    ]

    topology_dct["links"] = [
        json.loads(output_references_link(link)) for link in topology.links
    ]

    return json.dumps(topology_dct, indent=4)


def output_references_topology_brief(topology):
    topology_dct = json.loads(topology.to_json(indent=2))
    del (topology_dct['_id'])
    del (topology_dct['devices'])
    del (topology_dct['links'])

    return json.dumps(topology_dct, indent=4)


def output_references_device_brief(device):
    device_dct = json.loads(device.to_json(indent=2))
    del (device_dct['_id'])
    device_dct["interfaces"] = [
        json.loads(interface.to_json(indent=2)) for interface in device.interfaces]
    del (device_dct['interfaces'])

    return json.dumps(device_dct, indent=4)


def output_references_ip_sla_info(ip_sla_info):
    ip_sla_info_dct = json.loads(ip_sla_info.to_json(indent=2))
    del (ip_sla_info_dct['_id'])
    del (ip_sla_info_dct['ip_sla_ref'])

    return json.dumps(ip_sla_info_dct, indent=4)


def output_references_ip_sla(ip_sla):
    ip_sla_dct = json.loads(ip_sla.to_json(indent=2))
    ip_sla_dct["sender_device_ref"] = json.loads(output_references_device_brief(ip_sla.sender_device_ref))
    ip_sla_dct["responder_device_ref"] = json.loads(output_references_device_brief(ip_sla.responder_device_ref))
    del (ip_sla_dct['_id'])

    return json.dumps(ip_sla_dct, indent=4)


def get_application_by_id(app_id):
    try:
        return application.objects.get(application_ID=app_id).application_NAME
    except:
        return str(app_id)


def output_references_flow_field(fl_field):
    flow_field_dct = json.loads(fl_field.to_json(indent=2))
    flow_field_dct["device_ref"] = json.loads(output_references_device_brief(fl_field.device_ref))
    flow_field_dct["input_int"] = str(fl_field.input_int.interface_name)
    flow_field_dct["output_int"] = str(fl_field.output_int.interface_name)
    del (flow_field_dct['_id'])
    del (flow_field_dct['flow_ref'])
    return json.dumps(flow_field_dct, indent=4)


def output_references_flow(fl, fl_fields):
    print(fl_fields)
    flow_dct = json.loads(fl.to_json(indent=2))
    flow_dct["ip_sla_ref"] = json.loads(output_references_ip_sla(fl.ip_sla_ref))
    flow_dct["application_ID"] = str(get_application_by_id(fl.application_ID))
    del (flow_dct['_id'])
    del (flow_dct['ip_sla_ref'])
    flow_dct["flow_fields"] = [
        json.loads(output_references_flow_field(fl_feild)) for fl_feild in fl_fields
    ]

    return json.dumps(flow_dct, indent=4)


def ouput_topology_id(topology):
    topology_dct = json.loads(topology.to_json(indent=2))

    topology_dct['id'] = topology_dct['_id']['$oid']
    del (topology_dct['_id'])
    del (topology_dct['devices'])
    del (topology_dct['links'])
    del (topology_dct['topology_desc'])

    return json.dumps(topology_dct, indent=4)


def ouput_device_id(device):
    device_dct = json.loads(device.to_json(indent=2))
    device_dct['id'] = device_dct['_id']['$oid']
    del (device_dct['_id'])
    del (device_dct['interfaces'])
    del (device_dct['management'])
    del (device_dct['is_responder'])

    return json.dumps(device_dct, indent=4)


def ouput_interface_id(interface):
    try:
        topo=topology.objects(topology_name="Hello")[0]
        topo.update(set__topology_desc="something")
        interface_dct = json.loads(interface.to_json(indent=2))
        interface_dct['id'] = interface_dct['_id']['$oid']
        del (interface_dct['_id'])
        del (interface_dct['interface_index'])
        del (interface_dct['interface_address'])
        del (interface_dct['interface_speed'])
        del (interface_dct['interface_prefixlen'])
        del (interface_dct['ingress'])
    except Exception as e :
        print(e) 


    return json.dumps(interface_dct, indent=4)


def output_flow_table_print(nt_field, ip_sla_i):
    rslt = []
    rslt.append(nt_field.flow_ref.flow_id)
    rslt.append(nt_field.device_ref.hostname)
    rslt.append(nt_field.input_int.interface_name)
    try:
        rslt.append(nt_field.output_int.interface_name)
    except:
        rslt.append("None")
    rslt.append(get_application_by_id(nt_field.flow_ref.application_ID))
    rslt.append(nt_field.flow_ref.ipv4_src_addr)
    rslt.append(nt_field.flow_ref.transport_src_port)
    rslt.append(nt_field.flow_ref.ipv4_dst_addr)
    rslt.append(nt_field.flow_ref.transport_dst_port)
    rslt.append(nt_field.flow_ref.type_of_service)
    rslt.append(nt_field.flow_ref.ipv4_protocol)
    rslt.append(nt_field.counter_bytes)
    rslt.append(nt_field.counter_pkts)
    rslt.append(nt_field.bandwidth)

    try:
        rslt.append(ip_sla_i.avg_delay)
    except:
        rslt.append('Not Available')
    try:
        rslt.append(ip_sla_i.avg_jitter)
    except:
        rslt.append('Not Available')
    try:
        rslt.append(ip_sla_i.packet_loss)
    except:
        rslt.append('Not Available')

    return json.dumps(rslt, indent=4)


def output_interfaces_flow(interface_ins):
    interface_dct = json.loads(interface_ins.to_json(indent=2))
    interface_dct['id'] = interface_dct['_id']['$oid']
    del (interface_dct['_id'])
    device_ins = device.objects(interfaces__contains=interface_ins)[0]
    input_topo = topology.objects(devices__contains=device_ins)[0]
    point = datetime.now() - timedelta(minutes=1.001)
    fields = netflow_fields.objects.filter((Q(first_switched__lte=point) & Q(last_switched__gte=point)) & (
                Q(input_int=interface) | Q(output_int=interface)))
    fields_picked = []

    for field in fields:
        topo = topology.objects(devices__contains=field.device_ref)
        if input_topo == topo[0]:
            fields_picked.append(field)

    interface_dct['flows'] = [
        json.loads(output_references_flow(field.flow_ref, field)) for field in fields_picked
    ]

    return json.dumps(interface_dct, indent=4)


def output_devices_flows(device):
    device_dct = json.loads(device.to_json(indent=2))
    device_dct['id'] = device_dct['_id']['$oid']
    del (device_dct['_id'])
    device_dct['interfaces'] = [
        json.loads(output_interfaces_flow(intf)) for intf in device.interfaces
    ]
    del (device_dct['management'])
    del (device_dct['is_responder'])
    return json.dumps(device_dct, indent=4)


def output_topology_level(topology):
    topology_dct = json.loads(topology.to_json(indent=2))
    topology_dct['id'] = topology_dct['_id']['$oid']
    del (topology_dct['_id'])
    topology_dct["devices"] = [
        json.loads(output_devices_flows(device_ins)) for device_ins in topology.devices
    ]
    del (topology_dct['links'])


def get_flow_statistics(topo_name, flow_id, point):
    result = {}
    result["labels"] = []
    result["bandwidth"] = []
    topo = topology.objects(topology_name=topo_name)[0]
    time_portion = (datetime.now() - point) / 30
    labels = []
    bandwidths = []
    for i in range(30):
        field = netflow_fields.objects()
        print(len(field))
        for f in field:
            topo2 = topology.objects(devices__contains=f.device_ref)[0]
            print
            if topo2 == topo:
                print("hhhhhhh")
                print(f.bandwidth)

        point = point + time_portion
        bandwidth = field.bandwidth
        labels.append(point.strftime("%H:%M:%S"))
        bandwidths.append(bandwidth)
        result["labels"] = {labels}
        result["bandwidth"] = {bandwidths}

    return json.dumps(result, indent=4)
