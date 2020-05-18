from threading import Thread

from mongoengine import *
import re
from netaddr import *
from jinja2 import Environment, FileSystemLoader
from napalm import get_network_driver
import random
import numpy as np
from netmiko import ConnectHandler
import os
from datetime import datetime
from DynamicQoS.settings import MEDIA_ROOT


class interface(DynamicDocument):
    interface_name = StringField(required=True)
    interface_index = IntField(required=True)
    interface_address = StringField(required=True)
    interface_prefixlen = IntField(required=True)
    interface_speed = IntField(required=True)
    ingress = BooleanField(default=False)

    def configure_netflow(self):
        output = ""
        ENV = Environment(loader=FileSystemLoader(str(MEDIA_ROOT[0]) + "/monitoring_conf/"))
        template = ENV.get_template("netflow_interface_config.j2")
        output = template.render(interface_name=self.interface_name)
        return output


class access(DynamicEmbeddedDocument):
    management_interface = StringField(required=True)
    management_address = StringField(required=True)
    username = StringField(required=True)
    password = StringField(required=True)


class device(DynamicDocument):
    hostname = StringField(required=False, unique=True)
    management = EmbeddedDocumentField(access)
    interfaces = ListField(ReferenceField(interface))
    is_responder = BooleanField(default=False)

    def netmiko_connect(self):
        return ConnectHandler(device_type="cisco_ios", ip=self.management.management_address,
                              username=self.management.username, password=self.management.password)

    def connect(self):
        driver = get_network_driver("ios")
        device = None
        try:
            device = driver(self.management.management_address, self.management.username,
                            self.management.password)
            device.open()
        except Exception as e:
            print(e)
        return device

    def get_fqdn(self):
        self.hostname = self.connect().get_facts()['fqdn']
        self.connect().close()

    def get_interface_by_index(self, index):
        for ins in self.interfaces:
            if (ins.interface_index == index):
                return ins
            else:
                pass
        return None

    def configure_netflow(self, destination):
        global_output = ""
        interfaces_output = ""
        ENV = Environment(loader=FileSystemLoader(str(MEDIA_ROOT[0]) + "/monitoring_conf/"))
        template = ENV.get_template("global_netflow_config.j2")
        global_output = template.render(destination=destination, source=self.management.management_interface)
        for interface in self.interfaces:
            interfaces_output += interface.configure_netflow()
        config = (global_output + interfaces_output)
        f = open("netflow_config", "a+")
        lines = config.splitlines()
        for line in lines:
            f.write("{} \n".format(line))
        f.close()
        connection = self.connect()
        try:
            connection.load_merge_candidate(filename="netflow_config")
            connection.commit_config()
            connection.close()
            os.remove("netflow_config")
            return True
        except Exception as e:
            print("here {}".format(e))
            connection.close()
            os.remove("netflow_config")
            return False

    def configure_ip_sla(self, operation, dst_address, TOS):
        ENV = Environment(loader=FileSystemLoader(str(MEDIA_ROOT[0]) + "/monitoring_conf/"))
        template = ENV.get_template("ip_sla.j2")
        output = template.render(operation=operation, dst_address=dst_address, TOS=TOS)
        connection = self.connect()
        try:
            connection.load_merge_candidate(config=output)
            connection.commit_config()
            connection.close()
            return True
        except Exception as e:
            print(e)
            connection.close()
            return False

    def configure_ip_sla_responder(self):
        connection = self.connect()
        try:
            connection.load_merge_candidate(config='ip sla responder')
            connection.commit_config()
            connection.close()
            return True
        except Exception as e:
            print(e)
            connection.close()
            return False

    def pull_ip_sla_stats(self, operation):
        jitter_cmd = "show ip sla statistics {} | include Destination to Source Jitter".format(str(operation))
        delay_cmd = "show ip sla statistics {} | include Destination to Source Latency".format(str(operation))
        packet_loss_ratio = "show ip sla statistics {} | include Loss Source to Destination".format(
            str(operation))  # TODO: get the packet loss ratio
        config = [jitter_cmd, delay_cmd, packet_loss_ratio]
        connection = self.connect()
        result = connection.cli(config)
        jitter = int(re.findall("\d+", result[jitter_cmd])[1])
        delay = int(re.findall("\d+", result[delay_cmd])[1])
        packet_loss = int(re.findall("\d+", result[packet_loss_ratio])[0])
        connection.close()
        return jitter, delay, packet_loss

    def get_cdp_neighbors(self):
        connection = self.connect()
        neighbors = connection.cli(
            ["show cdp neighbors detail | include Device ID", "show cdp neighbors detail | include Interface"])
        neighbor_devices = (neighbors["show cdp neighbors detail | include Device ID"]).splitlines()
        neighbor_interfaces = (neighbors["show cdp neighbors detail | include Interface"]).splitlines()
        cdp_devices = [x[x.find(":") + 2:] for x in neighbor_devices]
        cdp_interfaces = [{"from": x[x.find(":") + 2:x.find(",")], "to": x[x.find("):") + 3:]} for x in
                          neighbor_interfaces]
        res = []
        for i in range(len(cdp_devices)):
            res.append({"to_device": cdp_devices[i], "interfaces": cdp_interfaces[i]})
        connection.close()
        return {self.hostname: res}

    def get_interfaces_index(self):
        interfaces_f = {}
        connection = self.connect()
        interfaces_sh = connection.cli(["show snmp mib ifmib ifindex"])
        interfaces_sh_sp = (interfaces_sh["show snmp mib ifmib ifindex"]).splitlines()

        for intf in interfaces_sh_sp:
            parts = intf.split(': ')
            interfaces_f.update({parts[0]: int(parts[1].strip('Ifindex = '))})
        connection.close()
        return interfaces_f

    def configure_ntp(self, ntp_master):
        client_connection = self.netmiko_connect()
        client_connection.config_mode()
        client_connection.send_command("ntp server {}".format(ntp_master.management.management_address))
        client_connection.disconnect()

    def configure_scp(self):
        connection = self.netmiko_connect()
        connection.config_mode()
        connection.send_command("ip scp server enable")
        connection.disconnect()

    def configure_snmp(self):
        connection = self.netmiko_connect()
        connection.config_mode()
        connection.send_command("snmp-server community public RO")
        connection.send_command("snmp-server community private RW")
        connection.disconnect()

    def get_networks(self):
        connection = self.connect()
        ports = connection.get_interfaces_ip()
        interfaces_index = self.get_interfaces_index()
        speeds = connection.get_interfaces()
        interfaces_list = []
        for port in ports:
            port_speed = speeds[port]["speed"]
            for ip in ports[port]["ipv4"]:
                cidr = ports[port]["ipv4"][ip]["prefix_length"]
                interface_ins = interface(interface_name=port, interface_index=interfaces_index[port],
                                          interface_address=ip, interface_prefixlen=int(cidr),
                                          interface_speed=port_speed)
                interface_ins.save()
                interfaces_list.append(interface_ins)
        connection.close()
        self.update(set__interfaces=interfaces_list)


class link(DynamicDocument):
    from_device = ReferenceField(device)
    from_interface = ReferenceField(interface)
    to_device = ReferenceField(device)
    to_interface = ReferenceField(interface)
    link_speed = IntField(required=False)

    def calculate_speed(self):
        if self.from_interface.interface_speed >= self.to_interface.interface_speed:
            self.link_speed = self.to_interface.interface_speed
        elif self.to_interface.interface_speed >= self.from_interface.interface_speed:
            self.link_speed = self.from_interface.interface_speed

    def compare(self, clink):
        if (
                self.from_device == clink.from_device and self.from_interface == clink.from_interface and self.to_device == clink.to_device and self.to_interface == clink.to_interface):
            return True
        elif (
                self.from_device == clink.to_device and self.from_interface == clink.to_interface and self.to_device == clink.from_device and self.to_interface == clink.from_interface):
            return True
        else:
            return False


def valid_cover(graph, cover):
    valid = True
    num_edge = [0] * len(graph)
    for i in range(0, len(graph)):
        for j in range(i, len(graph)):
            if graph[i][j] == 1:
                if (i not in cover) and (j not in cover):
                    valid = False
                    num_edge[i] += 1
                    num_edge[j] += 1
    return valid, num_edge


class topology(DynamicDocument):
    topology_name = StringField(required=True, unique=True)
    topology_desc = StringField(required=False)
    devices = ListField(ReferenceField(device))
    links = ListField(ReferenceField(link))
    monitoring_enabled = BooleanField(default=False)
    monitoring_activated = BooleanField(default=False)

    def get_monitors(self):
        devices_num = len(self.devices)
        matrix = np.zeros(shape=(devices_num, devices_num))
        for link in self.links:
            row_index = self.devices.index(to_device)
            column_index = self.devices.index(from_device)
            matrix[row_index][column_index] = 1
        cover = []

        valid, num_edge = valid_cover(matrix, cover)
        while not valid:
            m = [x for x in range(0, len(num_edge)) if num_edge[x] == max(num_edge)][0]
            cover.append(m)
            valid, num_edge = valid_cover(matrix, cover)

        monitors = []
        for i in cover:
            monitors.append(self.devices[i])

        return monitors

    def get_ip_sla_devices(self, record):
        src_ip = IPAddress(record.IPV4_SRC_ADDR)
        dst_ip = IPAddress(record.IPV4_DST_ADDR)
        src_device = None
        dst_device = None
        for device_cursor in self.devices:
            for interface in device_cursor.interfaces:
                network = IPNetwork(interface.interface_address)
                network.prefixlen = interface.interface_prefixlen
                if src_ip in network:
                    src_device = device_cursor

                if dst_ip in network:
                    dst_device = device_cursor

        if dst_device == None:
            for device_cursor in self.devices:
                if device_cursor.hostname == "Wan.cisco":
                    dst_device = device_cursor

        if src_device == None:
            for device_cursor in self.devices:
                if device_cursor.hostname == "Wan.cisco":
                    src_device = device_cursor

        return src_device, dst_device

    def get_networks(self):
        print("get networks")
        threads = []
        for device in self.devices:
            threads.append(Thread(target=device.get_networks, args=[]))
        for th in threads:
            print("start thread")
            th.start()
        for th in threads:
            th.join()
            # connection = device.connect()
            # ports = connection.get_interfaces_ip()
            # interfaces_index = device.get_interfaces_index()
            # speeds = connection.get_interfaces()
            # interfaces_list = []
            # for port in ports:
            #     port_speed = speeds[port]["speed"]
            #     for ip in ports[port]["ipv4"]:
            #         cidr = ports[port]["ipv4"][ip]["prefix_length"]
            #         interface_ins = interface(interface_name=port, interface_index=interfaces_index[port],
            #                                   interface_address=ip, interface_prefixlen=int(cidr),
            #                                   interface_speed=port_speed)
            #         interface_ins.save()
            #         interfaces_list.append(interface_ins)
            # connection.close()
            # device.update(set__interfaces=interfaces_list)

    def create_links(self):
        for device in self.devices:
            neighbors = device.get_cdp_neighbors()
            neighbors = neighbors[device.hostname]
            devicef = device
            link_ins = None
            for neighbor in neighbors:
                interfacef = None
                devicet = None
                interfacet = None
                interface_list = devicef.interfaces
                for inter in interface_list:
                    print(inter.interface_name)

                for interface in devicef.interfaces:
                    if interface.interface_name == neighbor["interfaces"]["from"]:
                        interfacef = interface

                for d in self.devices:
                    if d.hostname == neighbor["to_device"]:
                        devicet = d

                try:
                    for interface in devicet.interfaces:
                        if interface.interface_name == neighbor["interfaces"]["to"]:
                            interfacet = interface
                except Exception as e:
                    print(e)
                    print("Unable to connect device in phb behavior or cisco device from another entity")
                if len(self.links) == 0:
                    link_ins = link(from_device=devicef, from_interface=interfacef, to_device=devicet,
                                    to_interface=interfacet)
                    link_ins.calculate_speed()
                    link_ins.save()
                    self.links.append(link_ins)

                link_ins = link(from_device=devicef, from_interface=interfacef, to_device=devicet,
                                to_interface=interfacet)
                exist = False
                for lk in self.links:
                    if lk.compare(link_ins):
                        exist = True
                        break
                if not exist:
                    link_ins.calculate_speed()
                    link_ins.save()
                    self.links.append(link_ins)
            self.update(set__links=self.links)

    def configure_ntp(self):
        print("start ntp ")
        configured_time = datetime.now()
        ntp_master = random.choice(self.devices)
        ntp_master_connection = ntp_master.netmiko_connect()
        ntp_master_connection.send_command("clock set {}".format(configured_time.strftime("%H:%M:%S %d %B %Y")))
        ntp_master_connection.config_mode()
        ntp_master_connection.send_command("ntp master")
        print("master sucss")
        ntp_master_connection.disconnect()
        threads = []
        for device in self.devices:
            if device != ntp_master:
                threads.append(Thread(target=device.configure_ntp, args=[ntp_master]))
        for th in threads:
            print("start thread")
            th.start()
        for th in threads:
            th.join()

            # client_connection = device.netmiko_connect()
            # client_connection.config_mode()
            # client_connection.send_command("ntp server {}".format(ntp_master.management.management_address))
            # client_connection.disconnect()

    def configure_scp(self):
        print("start scp ")
        threads = []
        for device in self.devices:
            threads.append(Thread(target=device.configure_scp, args=[]))
        for th in threads:
            print("start thread")
            th.start()
        for th in threads:
            th.join()
            # connection = device.netmiko_connect()
            # connection.config_mode()
            # connection.send_command("ip scp server enable")
            # connection.disconnect()

    def configure_snmp(self):
        print("start snmp ")
        threads = []
        for device in self.devices:
            threads.append(Thread(target=device.configure_snmp, args=[]))
        for th in threads:
            print("start thread")
            th.start()
        for th in threads:
            th.join()
            # connection = device.netmiko_connect()
            # connection.config_mode()
            # connection.send_command("snmp-server community public RO")
            # connection.send_command("snmp-server community private RW")
            # connection.disconnect()


class ip_sla(Document):
    operation = SequenceField()
    type_of_service = IntField(required=True)
    sender_device_ref = ReferenceField(device)
    responder_device_ref = ReferenceField(device)


class notification(Document):
    message = StringField(required=True)
    timestamp = StringField(required=True)


class flow(DynamicDocument):
    flow_id = StringField(primary_key=True)
    ipv4_src_addr = StringField(required=True)
    ipv4_dst_addr = StringField(required=True)
    ipv4_protocol = IntField(required=True)
    transport_src_port = IntField(required=True)
    transport_dst_port = IntField(required=True)
    type_of_service = IntField(required=True)
    application_ID = IntField(required=True)
    ip_sla_ref = ReferenceField(ip_sla)


class netflow_fields(DynamicDocument):
    # Real time information about flow in the monitor.
    counter_bytes = IntField(required=True)
    counter_pkts = IntField(required=True)
    first_switched = ComplexDateTimeField(required=True)
    last_switched = ComplexDateTimeField(required=True)
    # QoS parameters
    bandwidth = FloatField(required=False)
    # =======================================
    # Device related Information
    collection_time = ComplexDateTimeField(required=True)
    input_int = ReferenceField(interface)
    output_int = ReferenceField(interface)
    device_ref = ReferenceField(device)
    flow_ref = ReferenceField(flow)
    # =======================================


class ip_sla_info(Document):
    avg_jitter = IntField(required=True)
    avg_delay = IntField(required=True)
    packet_loss = IntField(required=False)  # For the moment it is false because i dont know how to get it
    timestamp = ComplexDateTimeField(
        required=False)  # temporary false until see how the netflow is sniffing the timestamp to combine it with ip sla
    ip_sla_ref = ReferenceField(ip_sla)


class application(Document):
    application_ID = IntField(primary_key=True)
    application_NAME = StringField(required=True)
