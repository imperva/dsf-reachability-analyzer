import boto3
import time
import json
import getpass
import re
from plan_parser import validate_plan, parse_plan

def init_client(access_key,secret_key,regions):
    # Create a session with the specified AWS access key and secret key
    clients = {}
    for region in regions:
        session = boto3.Session(
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            region_name=region
        )
        clients[region] = session.client('ec2')
    return clients

def create_network_insights_path(source, destination, port, client):
    params = {
        'Source': source,
        'Destination': destination,
        'Protocol': 'tcp',
        'TagSpecifications': [
            {
                'ResourceType': 'network-insights-path',
                'Tags': [
                    {
                        'Key': 'Name',
                        'Value': f"{source}->{destination}:{port}" if port > -1 else f"{source}->{destination}"
                    }
                ]
            }
        ]
    }
    if port > -1:
        params['DestinationPort'] = port

    response_create = client.create_network_insights_path(**params)
    network_insights_path_id = response_create['NetworkInsightsPath']['NetworkInsightsPathId']
    prints("Network Insight Path Created. NetworkInsightsPathId: " + network_insights_path_id)

    return response_create['NetworkInsightsPath']

def delete_network_insights_path(paths, client):
    for path in paths:
        path_id = path['NetworkInsightsPathId']
        delete_single_network_insights_path(path_id, client)

def delete_single_network_insights_path(path_id, client):
        client.delete_network_insights_path(NetworkInsightsPathId=path_id)
        print(f'Deleted network insights path: {path_id}')

def delete_all_network_insights_analysis_and_paths(clients):
    for client in clients.values():
        response = client.describe_network_insights_paths()
        paths = response['NetworkInsightsPaths']
        delete_network_insights_analysis(paths, client)
   
def delete_network_insights_analysis(paths, client):
    for path in paths:
        path_id = path['NetworkInsightsPathId']
        response_analysis = client.describe_network_insights_analyses(NetworkInsightsPathId=path_id)
        for analisy in response_analysis['NetworkInsightsAnalyses']:
            client.delete_network_insights_analysis(NetworkInsightsAnalysisId=analisy['NetworkInsightsAnalysisId'])           
        delete_single_network_insights_path(path_id, client)

def start_network_insights_analysis(network_insights_path_id, client):
    response_start = client.start_network_insights_analysis(NetworkInsightsPathId=network_insights_path_id)
    analysis_id = response_start['NetworkInsightsAnalysis']['NetworkInsightsAnalysisId']
    prints("Network Analisys Started. NetworkInsightsAnalysisId: " + analysis_id)

    return response_start['NetworkInsightsAnalysis']


def fetch_network_insights_analyses_result(analysis_id, client):    
    response_describe = None
    status = None
    while True:
        response_describe = client.describe_network_insights_analyses(
            NetworkInsightsAnalysisIds=[
                analysis_id,
            ])
        status = response_describe['NetworkInsightsAnalyses'][0]['Status']
        prints("Waiting for Analysis completion. Status: "  + status)
        time.sleep(5)
        if status != 'running':
            break
    
    full_info = response_describe['NetworkInsightsAnalyses'][0]
    network_path_found = full_info['NetworkPathFound']
    return {
        "status" : status,
        "network_path_found" : network_path_found,
        "info" : full_info
    } 

def get_input(message, error_message, regex, is_secured=False):
    value = None
    while not value:
        value = getpass.getpass(message) if is_secured else input(message)
        if not value or not re.match(regex, value.strip(), re.IGNORECASE):
            print(error_message)
            value = None
    return value

def get_inputs():
    access_key = get_input("Please enter the AWS Access Key: ", "You didn't enter anything. Please try again", "^.+$")
    secret_key = get_input("Please enter the AWS Secret Key: ", "You didn't enter anything. Please try again", "^.+$", True)
    analyze_specific_ports = input("Analyze specific ports [22,8080,8443,3030,27117]: ") or "22,8080,8443,3030,27117"

    analyze_specific_ports_list = list(analyze_specific_ports.split(","))

    return {
        "analyze_specific_ports_list" : analyze_specific_ports_list,
        "access_key" : access_key,
        "secret_key" : secret_key
    }


def analyze(path, analyze_specific_ports_list, type, clients):
    if type == "REGULAR":
        prints("Start analysis network connectivity of Subnet1 via: " + path["source"]["subnet"] + " --> to Subnet2 via " + path["destination"]["subnet"] + ", on ports: " + str(analyze_specific_ports_list))
    if type == "NAT_GATEWAY":
        prints("Start analysis network connectivity of Subnet1 via: " + path["source"]["subnet"] + " --> to Nat Gateway " + path["destination"]["id"])

    is_peering_connection = "region" in path["source"] and "region" in path["destination"] and path["source"]["region"] != path["destination"]["region"] and path["source"]["peering_connection_id"] == path["destination"]["peering_connection_id"]
    total_network_path_count = len(analyze_specific_ports_list) * 2 if is_peering_connection else len(analyze_specific_ports_list)
    total_network_path_count = total_network_path_count if total_network_path_count > 0 else 1

    analysis_result = {
        "full_network_path_found" : True,
        "path_info" : [],
        "total_network_path_count": total_network_path_count,
        "valid_network_path_count": 0
    }
    if type == "REGULAR":
        for port in analyze_specific_ports_list:
            if is_peering_connection:
                analyze_per_port(path["source"]["eni"], path["source"]["peering_connection_id"], analysis_result, type, clients[path["source"]["region"]], port)
                analyze_per_port(path["destination"]["peering_connection_id"], path["destination"]["eni"], analysis_result, type, clients[path["destination"]["region"]], port)
            else:
                analyze_per_port(path["source"]["eni"], path["destination"]["eni"], analysis_result, type, clients[path["source"]["region"]], port)
    else:
        analyze_per_port(path["source"]["eni"], path["destination"]["id"], analysis_result, type, clients[path["source"]["region"]])
    return analysis_result

def analyze_per_port(subnet1_eni, dest_id, analysis_result, type, client, port=None):
    portInt = -1
    additional_info = None

    if port:
        portInt = int(port)
        print(f"Analyzing port: {portInt}")

    if type == "NAT_GATEWAY":
        nat_gateway_details = get_nat_gateway_enis(dest_id, client)
        additional_info = {"nat_gw_id": dest_id}
        if nat_gateway_details:
            dest_id = nat_gateway_details[0]
        else:
            dest_id = None

    path_result = {
        "network_path_found": False,
        "source": subnet1_eni,
        "destination": dest_id,
        "port": portInt if portInt > -1 else None,
        "info": None,
        "insights_path_id": None,
        "insights_analysis_id": None,
        "region": client.meta.config.region_name,
    }

    if dest_id:
        create_and_fetch_insights(subnet1_eni, dest_id, portInt, client, path_result)
        analysis_result["full_network_path_found"] = path_result["network_path_found"]
        analysis_result["valid_network_path_count"] = analysis_result["valid_network_path_count"] + 1 if path_result["network_path_found"] else analysis_result["valid_network_path_count"]

    if type == "NAT_GATEWAY":
        path_result["additional_info"] = {"NatGateway": additional_info["nat_gw_id"]}
        if not dest_id:
            path_result["additional_info"]["Error"] = f"Nat gateway {additional_info['nat_gw_id']} is invalid"

    analysis_result["path_info"].append(path_result)

    if port:
        print_header2(f"Analysis on port: {portInt} completed")


def create_and_fetch_insights(subnet1_eni, dest_id, portInt, client, path_result):
    create_network_insights_path_response = create_network_insights_path(subnet1_eni, dest_id, portInt, client)
    start_network_insights_analysis_resposne = start_network_insights_analysis(
        create_network_insights_path_response["NetworkInsightsPathId"], client
    )
    fetch_network_insights_analyses_result_response = fetch_network_insights_analyses_result(
        start_network_insights_analysis_resposne["NetworkInsightsAnalysisId"], client
    )

    path_result.update(
        {
            "network_path_found": fetch_network_insights_analyses_result_response["network_path_found"],
            "info": fetch_network_insights_analyses_result_response["info"],
            "insights_path_id": create_network_insights_path_response["NetworkInsightsPathId"],
            "insights_analysis_id": start_network_insights_analysis_resposne["NetworkInsightsAnalysisId"],
        }
    )



def create_eni(subnetId, client, securityGroupId=None):
    prints(f"Creating eni in region: {client.meta.config.region_name} and in Subnet: {subnetId}")
    response = client.create_network_interface(
        Description='DSF Reachability Validator Tool - ' + subnetId,
        SubnetId = subnetId, 
        Groups=[securityGroupId] if securityGroupId else None,
        TagSpecifications=[
            {
                'ResourceType': 'network-interface',
                'Tags': [
                    {
                        'Key': 'project',
                        'Value': 'dsf'
                    }
                ]
            }])
    eniId = response["NetworkInterface"]["NetworkInterfaceId"]
    if securityGroupId:
        current_sg = client.describe_network_interfaces(NetworkInterfaceIds=[eniId])['NetworkInterfaces'][0]['Groups'][0]['GroupId']
        if current_sg != securityGroupId:
            client.modify_network_interface_attribute(NetworkInterfaceId=eniId, Groups=[securityGroupId])
            prints("Security group modified to " + securityGroupId)
    prints("eni created: " + eniId)
    return eniId

def delete_eni(eni_id, client):
    prints(f"Deleting eni: {eni_id} in region: {client.meta.config.region_name}")
    response = client.delete_network_interface(NetworkInterfaceId=eni_id)

def create_network_endpoints(subnet1, sg1, source_client, subnet2=None, sg2=None, destination_client=None):
    prints("Start creating Networking Endpoints")
    subnet1_eni = create_eni(subnet1, source_client, sg1)
    subnet2_eni = create_eni(subnet2, destination_client, sg2) if subnet2 is not None else None
    return {
        "subnet1_eni" : subnet1_eni,
        "subnet2_eni" : subnet2_eni
    }

def delete_network_endpoints(eni1_id, source_client, eni2_id=None, destination_client=None):
    prints("Start deleting Networking Endpoints")
    delete_eni(eni1_id, source_client)
    if eni2_id:
        delete_eni(eni2_id, destination_client)


def print_header1(text):
    print("")
    print('*********************************************************')
    print('************ ' + text + " ")
    print('*********************************************************')
    print("")
    print("")

def print_header2(text):
    print("")
    print('************ ' + text)
    print("")

def prints(text):
    print(text)


def read_plan():
    with open("plan.json", "r") as json_file:
        data = json.load(json_file)
    return data

def write_analysis_to_disk(analysis_result):
    file_name=str(int(time.time())) + "-" + str(analysis_result["full_network_path_found"]) + ".json"
    text_file = open(file_name, "w")
    n = text_file.write(json.dumps(analysis_result, indent=4, sort_keys=True, default=str))
    text_file.close()

    prints("Full info printed in file: " + file_name)

def print_links_to_console(analysis_result):
    prints("Full info analysis can be found in AWS Console:")
    for path_info in analysis_result["path_info"]:
        if path_info["insights_path_id"]:
            prints("   - For '" +  path_info["insights_path_id"] + "' https://" + path_info["region"] + ".console.aws.amazon.com/vpc/home?region=" + path_info["region"] + "#NetworkPath:pathId=" + path_info["insights_path_id"])


def load_plan():
    data = read_plan()
    validate_plan(data)
    result = parse_plan(data)
    print_header1("Plan:")
    prints(json.dumps(result["plan"], indent=4, sort_keys=True, default=str))
    proceed = get_input("Do you wish to continue ? (y/n): ", "You didn't type y or n. Please try again", "^(y|n)$")
    if proceed.lower() != "y":
        exit(1)
    return result


def execute_plan(plan, clients):
    for path in plan:
        source = path["source"]
        destination = path["destination"]

        source_subnet_id = source["subnet"]
        source_sg = source["security_group_id"]
        source_client = clients[source["region"]]
        destination_subnet_id = destination["subnet"] if "subnet" in destination else None
        destination_sg = destination["security_group_id"] if "security_group_id" in destination else None
        destination_client = clients[destination["region"]] if "region" in destination else None

        endpoints = create_network_endpoints(source_subnet_id, source_sg, source_client, destination_subnet_id, destination_sg, destination_client)
        source["eni"] = endpoints["subnet1_eni"]
        destination["eni"] = endpoints["subnet2_eni"]

        analysis_result = analysis_result = analyze(path, [], destination["type"], clients) if "type" in destination and destination["type"] == "NAT_GATEWAY" else analyze(path, inputs["analyze_specific_ports_list"], "REGULAR", clients)

        delete_network_endpoints(source["eni"], source_client, destination["eni"], destination_client)

        print_header1("Analysis completed. " + str(analysis_result["valid_network_path_count"]) + " valid network path found out of " + str(analysis_result["total_network_path_count"]) + " total network path")
        write_analysis_to_disk(analysis_result)
        print_links_to_console(analysis_result)


def get_nat_gateway_enis(nat_gateway_id, client):
    enis = []
    try:
        response = client.describe_nat_gateways(NatGatewayIds=[nat_gateway_id])
        for nat_gateway in response['NatGateways']:
            for network_gateway_address in nat_gateway['NatGatewayAddresses']:
                enis.append(network_gateway_address["NetworkInterfaceId"])
        prints(f"Found the following enis {', '.join(enis)} attached to NAT Gateway: {nat_gateway_id}")
    except Exception as e:
        prints(f"An exception occurred: {str(e)}")
    return enis


if __name__ == '__main__':
    print_header1("DSF Reachability Validator Tool")
    inputs = get_inputs()
    result = load_plan()
    clients = init_client(inputs["access_key"], inputs["secret_key"], result["regions"])

    delete_all_network_insights_analysis_and_paths(clients)
    print_header2("Analysis Started")
    execute_plan(result["plan"], clients)