import requests
import json

repos = {
    "main": "https://github.com/PortsMaster/PortMaster-New/releases/latest/download/ports.json",
    "multiverse": "https://github.com/PortsMaster-MV/PortMaster-MV-New/releases/latest/download/ports.json",
    }

def build_requirements(port_info, runtimes_info):
    """
    Matches hardware capabilities to port requirements.
    """
    requirements = port_info.get('attr', {}).get('reqs', [])[:]

    runtime = port_info.get('attr', {}).get('runtime', None)

    if runtime is not None:
        if isinstance(runtime, str):
            runtime = [runtime]

        for _runtime in runtime:
            if not _runtime.endswith('.squashfs'):
                _runtime += '.squashfs'

            requirements.append('|'.join(runtimes_info.get(_runtime, [])))

    else:
        arch = port_info.get('attr', {}).get('arch', [])

        if isinstance(arch, list) and len(arch) > 0:
            requirements.append('|'.join(arch))

    return requirements


def match_requirements(capabilities, requirements):
    """
    Matches hardware capabilities to port requirements.
    """
    if len(requirements) == 0:
        return True

    passed = True
    for requirement in requirements:
        match_not = True

        ## Fixes empty requirement bug
        if requirement == "":
            continue

        if requirement.startswith('!'):
            match_not = False
            requirement = requirement[1:]

        if '|' in requirement:
            passed = any(
                req in capabilities
                for req in requirement.split('|')) == match_not

        else:
            if requirement in capabilities:
                passed = match_not
            else:
                passed = not match_not

        if not passed:
            break

    return passed

def device_cfw_tag(port_info, device_info, runtimes_info):
    match_all = False

    avail_dev = []
    for device_name, cfw_info in device_info.items():

        match_cfw = True
        avail_cfw = []
        for cfw_name, device_cfw_info in cfw_info.items():
            device_tag = f"{device_cfw_info['device']}:{device_cfw_info['name']}"

            requirements = build_requirements(port_info, runtimes_info)

            if not match_requirements(device_cfw_info['capabilities'], requirements):
                match_cfw = False
                match_all = False
                continue

            avail_cfw.append(device_tag)

        if match_cfw:
            avail_cfw = [f"{device_cfw_info['device']}:ALL"]

        avail_dev.extend(avail_cfw)

    if match_all:
        avail_dev = ["ALL:ALL"]

    port_info["attr"]["avail"] = avail_dev


def main():
    ports = {"ports":{}}
    runtimes_info = {}

    with open('device_info.json', 'r') as fh:
        device_info = json.load(fh)

    devices = {}
    for device_name, cfw_info in device_info.items():
        for cfw_name, device_cfw_info in cfw_info.items():
            if device_cfw_info['device'] not in devices:
                devices[device_cfw_info['device']] = {
                    'name': device_name,
                    'manufacturer': device_cfw_info['manufacturer'],
                    'device': device_cfw_info['device'],
                    'cfw': {}
                    }

            devices[device_cfw_info['device']]['cfw'][device_cfw_info['name']] = {
                'name': cfw_name,
                }

    for repo in repos:
        r = requests.get(repos[repo])
        portsJson = r.json()

        for util_name, util_data in portsJson['utils'].items():
            if not util_name.endswith('.squashfs'):
                continue

            runtimes_info.setdefault(util_data["runtime_name"], []).append(util_data["runtime_arch"])

        for port in portsJson["ports"]:
            port_info = portsJson["ports"][port]
            port_info["source"]["repo"] = repo

            device_cfw_tag(port_info, device_info, runtimes_info)

            ports["ports"][port] = port_info

    with open("devices.json", "w", encoding="utf8") as outfile:
        outfile.write(json.dumps(devices, indent=2, sort_keys=True))

    with open("ports.json", "w", encoding="utf8") as outfile:
        outfile.write(json.dumps(ports, indent=2, sort_keys=True))


if __name__ == '__main__':
    main()
