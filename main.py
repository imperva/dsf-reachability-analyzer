import boto3
import time
import json
import getpass
import re

def init_client(access_key,secret_key,region):
    # Create a session with the specified AWS access key and secret key
    session = boto3.Session(
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
        region_name=region
    )
    client = session.client('ec2')
    return client

def create_network_insights_path(source, destination,port):
    response_create = client.create_network_insights_path(
        Source=source,
        Destination=destination,
        Protocol='tcp',
        DestinationPort=port,
         TagSpecifications=[
            {
                'ResourceType': 'network-insights-path',
                'Tags': [
                    {
                        'Key': 'Name',
                        'Value': source + "->" + destination + " :" + str(port)
                    }
                ]
            }]
    )
    network_insights_path_id = response_create['NetworkInsightsPath']['NetworkInsightsPathId']
    prints("Network Insight Path Created. NetworkInsightsPathId: " + network_insights_path_id)

    return response_create['NetworkInsightsPath']

def delete_all_network_insights_path():
    response = client.describe_network_insights_paths()
    paths = response['NetworkInsightsPaths']
    delete_network_insights_path(paths)

def delete_network_insights_path(paths):
    for path in paths:
        path_id = path['NetworkInsightsPathId']
        delete_single_network_insights_path(path_id)

def delete_single_network_insights_path(path_id):
        client.delete_network_insights_path(NetworkInsightsPathId=path_id)
        print(f'Deleted network insights path: {path_id}')

def delete_all_network_insights_analysis_and_paths():
    response = client.describe_network_insights_paths()
    paths = response['NetworkInsightsPaths']
    delete_network_insights_analysis(paths)
   
def delete_network_insights_analysis(paths):
    for path in paths:
        path_id = path['NetworkInsightsPathId']
        response_analysis = client.describe_network_insights_analyses(NetworkInsightsPathId=path_id)
        for analisy in response_analysis['NetworkInsightsAnalyses']:
            client.delete_network_insights_analysis(NetworkInsightsAnalysisId=analisy['NetworkInsightsAnalysisId'])           
        delete_single_network_insights_path(path_id)

def start_network_insights_analysis(network_insights_path_id):
    response_start = client.start_network_insights_analysis(NetworkInsightsPathId=network_insights_path_id)
    analysis_id = response_start['NetworkInsightsAnalysis']['NetworkInsightsAnalysisId']
    prints("Network Analisys Started. NetworkInsightsAnalysisId: " + analysis_id)

    return response_start['NetworkInsightsAnalysis']


def fetch_network_insights_analyses_result(analysis_id):    
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
    region = get_input("Please enter the AWS Region: ", "You didn't enter anything. Please try again", "^.+$")
    access_key = get_input("Please enter the AWS Access Key: ", "You didn't enter anything. Please try again", "^.+$")
    secret_key = get_input("Please enter the AWS Secret Key: ", "You didn't enter anything. Please try again", "^.+$", True)
    analyze_specific_ports = input("Analyze specific ports [22,8080,8443,3030,27117]: ") or "22,8080,8443,3030,27117"

    analyze_specific_ports_list = list(analyze_specific_ports.split(","))

    return {
        "analyze_specific_ports_list" : analyze_specific_ports_list,
        "region" : region,
        "access_key" : access_key,
        "secret_key" : secret_key
    }


def analyze(path, analyze_specific_ports_list):
    prints("Start analysis network connectivity of Subnet1 via: " + path["source"]["subnet"] + " --> to Subnet2 via " + path["destination"]["subnet"] + ", on ports: " + str(analyze_specific_ports_list))
    analysis_result = {
        "full_network_path_found" : True,
        "path_info" : [],
        "total_network_path_count": len(analyze_specific_ports_list),
        "valid_network_path_count": 0
    }
    for port in analyze_specific_ports_list:
        analyze_per_port(path["source"]["eni"], path["destination"]["eni"], analysis_result, port)
    return analysis_result

def analyze_per_port(subnet1_eni, subnet2_eni, analysis_result, port):
    port = int(port)
    prints("Analyzing port: " + str(port))

    create_network_insights_path_response = create_network_insights_path(subnet1_eni, subnet2_eni, port)
    start_network_insights_analysis_resposne = start_network_insights_analysis(create_network_insights_path_response["NetworkInsightsPathId"])
    fetch_network_insights_analyses_result_response = fetch_network_insights_analyses_result(start_network_insights_analysis_resposne["NetworkInsightsAnalysisId"])
    
    if analysis_result["full_network_path_found"] != False:
        analysis_result["full_network_path_found"] = fetch_network_insights_analyses_result_response["network_path_found"]

    analysis_result["valid_network_path_count"] = analysis_result["valid_network_path_count"] + 1 if fetch_network_insights_analyses_result_response["network_path_found"] else analysis_result["valid_network_path_count"]

    path_result = {
            "network_path_found" : fetch_network_insights_analyses_result_response["network_path_found"],
            "source": subnet1_eni,
            "destination": subnet2_eni,
            "port": port,
            "info": fetch_network_insights_analyses_result_response["info"],
            "insights_path_id" : create_network_insights_path_response["NetworkInsightsPathId"],
            "insights_analysis_id" : start_network_insights_analysis_resposne["NetworkInsightsAnalysisId"]
        }
    analysis_result["path_info"].append(path_result)
    print_header2("Analysis on port: " + str(port) + " completed")


def create_eni(subnetId, securityGroupId=None):
    prints("Creating eni in Subnet: " + subnetId)
    response = client.create_network_interface(
        Description='eDSF Sonar Network Analyzer Tool - ' + subnetId,
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

def delete_eni(eni_id):
    prints("Deleting eni: " + eni_id)
    response = client.delete_network_interface(NetworkInterfaceId=eni_id)

def create_network_endpoints(subnet1,sg1,subnet2,sg2):
    prints("Start creating Networking Endpoints")
    subnet1_eni = create_eni(subnet1,sg1)
    subnet2_eni = create_eni(subnet2,sg2)
    return {
        "subnet1_eni" : subnet1_eni,
        "subnet2_eni" : subnet2_eni
    }
def delete_network_endpoints(eni1_id,eni2_id):
    prints("Start deleting Networking Endpoints")
    delete_eni(eni1_id)
    delete_eni(eni2_id)

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

def print_links_to_console(region, analysis_result):
    prints("Full info analysis can be found in AWS Console:")
    for path_info in analysis_result["path_info"]:
        prints("   - For '" +  path_info["insights_path_id"] + "' https://" + region + ".console.aws.amazon.com/vpc/home?region=" + region + "#NetworkPath:pathId=" + path_info["insights_path_id"])


def parse_plan(data):
    # Create empty list and set to store the combinations
    combinations = []
    combination_set = set()

    # Iterate over the hub list
    for hub in data["hub"]:
        # Iterate over the hub list again to find other hubs with the same hapairid
        for other_hub in data["hub"]:
            if hub["hapairid"] == other_hub["hapairid"] and hub["friendlyname"] != other_hub["friendlyname"]:
                subnet_tuple = (hub["subnet"], other_hub["subnet"])
                subnet_tuple2 = (other_hub["subnet"], hub["subnet"])

                if subnet_tuple not in combination_set and subnet_tuple2 not in combination_set:
                    combination_set.add(subnet_tuple)
                    combination_set.add(subnet_tuple2)
                
                    combinations.append({"source": hub, "destination": other_hub})
                    combinations.append({"source": other_hub, "destination": hub})
                    
        # Iterate over the gws list
        for gw in data["gw"]:
            subnet_tuple = (hub["subnet"], gw["subnet"])
            if subnet_tuple not in combination_set:
                # Add the combination to the set
                combination_set.add(subnet_tuple)
                # Add the combination of subnets to the list, with the hub as "source" and gw as "destination"
                combinations.append({"source": hub, "destination": gw})
                
    for gw in data["gw"]:
         for other_gw in data["gw"]:
            if gw["hapairid"] == other_gw["hapairid"] and gw["friendlyname"] != other_gw["friendlyname"]:
                subnet_tuple = (gw["subnet"], other_gw["subnet"])
                subnet_tuple2 = (other_gw["subnet"], gw["subnet"])
                if subnet_tuple not in combination_set and subnet_tuple2 not in combination_set:
                   combination_set.add(subnet_tuple)
                   combination_set.add(subnet_tuple2)
                   combinations.append({"source": gw, "destination": other_gw})
                   combinations.append({"source": other_gw, "destination": gw})
    return combinations

def load_plan():
    data = read_plan()
    plan = parse_plan(data)
    print_header1("Plan:")
    prints(json.dumps(plan, indent=4, sort_keys=True, default=str))
    proceed = get_input("Do you wish to continue ? (y/n): ", "You didn't type y or n. Please try again", "^(y|n)$")
    if proceed.lower() != "y":
        exit(1)
    return plan


def execute_plan(plan):
    for path in plan:
        source = path["source"]
        destination = path["destination"]

        source_subnet_id = source["subnet"]
        source_sg = source["securitygroupid"]
        destination_subnet_id = destination["subnet"]
        destination_sg = destination["securitygroupid"]

        endpoints = create_network_endpoints(source_subnet_id, source_sg,destination_subnet_id,destination_sg)
        source["eni"] = endpoints["subnet1_eni"]
        destination["eni"] = endpoints["subnet2_eni"]

        analysis_result = analyze(path,inputs["analyze_specific_ports_list"])

        delete_network_endpoints(source["eni"],destination["eni"])
        print_header1("Analysis completed. " + str(analysis_result["valid_network_path_count"]) + " valid network path found out of " + str(analysis_result["total_network_path_count"]) + " total network path")
        write_analysis_to_disk(analysis_result)
        print_links_to_console(inputs["region"], analysis_result)

if __name__ == '__main__':
    print_header1("eDSF Sonar Network Analyzer Tool")
    inputs = get_inputs()
    client = init_client(inputs["access_key"], inputs["secret_key"], inputs["region"])
    delete_all_network_insights_analysis_and_paths()
    print_header2("Analysis Started")
    plan = load_plan()
    execute_plan(plan)